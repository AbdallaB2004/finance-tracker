"""FinTrack Flask app. Run: python app.py"""

import sqlite3
from datetime import datetime, timedelta

from flask import (
    Flask, flash, g, redirect, render_template, request, session, url_for,
)
from flask_login import (
    LoginManager, UserMixin, current_user, login_required, login_user,
    logout_user,
)
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-change-in-production'
app.config['DATABASE'] = 'finance.db'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to continue.'
login_manager.login_message_category = 'warning'


@app.before_request
def make_session_permanent():
    session.permanent = True


# ============================================================================
# 1. DATABASE HELPERS  (Person A)
# ============================================================================

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON;')
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rows = cur.fetchall()
    cur.close()
    return (rows[0] if rows else None) if one else rows


def execute_db(query, args=()):
    conn = get_db()
    cur = conn.execute(query, args)
    conn.commit()
    last_id = cur.lastrowid
    cur.close()
    return last_id


DEFAULT_CATEGORIES = [
    ('Salary',         'income',  '#198754'),
    ('Other income',   'income',  '#20c997'),
    ('Food',           'expense', '#fd7e14'),
    ('Transport',      'expense', '#0d6efd'),
    ('Rent',           'expense', '#6f42c1'),
    ('Utilities',      'expense', '#d63384'),
    ('Entertainment',  'expense', '#ffc107'),
    ('Other',          'expense', '#6c757d'),
]


def seed_default_categories(user_id):
    conn = get_db()
    conn.executemany(
        "INSERT INTO categories (user_id, name, type, color) VALUES (?, ?, ?, ?)",
        [(user_id, name, kind, color) for name, kind, color in DEFAULT_CATEGORIES],
    )
    conn.commit()


# ============================================================================
# 2. AUTH  (Person A)
# ============================================================================

class User(UserMixin):
    def __init__(self, row):
        self.id = row['id']
        self.username = row['username']
        self.password_hash = row['password_hash']


@login_manager.user_loader
def load_user(user_id):
    row = query_db("SELECT * FROM users WHERE id = ?", (user_id,), one=True)
    return User(row) if row else None


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')

        if len(username) < 3:
            flash('Username must be at least 3 characters.', 'danger')
            return render_template('auth/register.html', username=username)

        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'danger')
            return render_template('auth/register.html', username=username)

        if password != password_confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html', username=username)

        existing = query_db(
            "SELECT id FROM users WHERE username = ?",
            (username,),
            one=True,
        )

        if existing:
            flash('That username is taken.', 'danger')
            return render_template('auth/register.html', username=username)

        user_id = execute_db(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, generate_password_hash(password)),
        )

        seed_default_categories(user_id)

        flash('Account created. Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('auth/register.html', username='')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        row = query_db(
            "SELECT * FROM users WHERE username = ?",
            (username,),
            one=True,
        )

        if row and check_password_hash(row['password_hash'], password):
            login_user(User(row))
            return redirect(url_for('dashboard'))

        flash('Wrong username or password.', 'danger')
        return render_template('auth/login.html', username=username)

    return render_template('auth/login.html', username='')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out.', 'success')
    return redirect(url_for('login'))


# ============================================================================
# 3. ACCOUNTS CRUD  (Person D)
# ============================================================================

@app.route('/accounts')
@login_required
def accounts_list():
    accounts = query_db(
        """
        SELECT *
        FROM accounts
        WHERE user_id = ?
        ORDER BY name
        """,
        (current_user.id,)
    )

    return render_template('accounts/list.html', accounts=accounts)


@app.route('/accounts/add', methods=['GET', 'POST'])
@login_required
def accounts_add():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        account_type = request.form.get('type', '').strip()
        starting_balance = request.form.get('starting_balance', '0').strip()

        if not name or not account_type:
            flash('Account name and type are required.', 'danger')
            return redirect(url_for('accounts_add'))

        try:
            starting_balance = float(starting_balance)
        except ValueError:
            flash('Starting balance must be a number.', 'danger')
            return redirect(url_for('accounts_add'))

        if starting_balance < 0:
            flash('Starting balance cannot be negative.', 'danger')
            return redirect(url_for('accounts_add'))

        execute_db(
            """
            INSERT INTO accounts (user_id, name, type, starting_balance)
            VALUES (?, ?, ?, ?)
            """,
            (current_user.id, name, account_type, starting_balance)
        )

        flash('Account added successfully.', 'success')
        return redirect(url_for('accounts_list'))

    return render_template('accounts/form.html', account=None)


@app.route('/accounts/<int:account_id>/edit', methods=['GET', 'POST'])
@login_required
def accounts_edit(account_id):
    account = query_db(
        """
        SELECT *
        FROM accounts
        WHERE id = ? AND user_id = ?
        """,
        (account_id, current_user.id),
        one=True
    )

    if account is None:
        flash('Account not found.', 'danger')
        return redirect(url_for('accounts_list'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        account_type = request.form.get('type', '').strip()
        starting_balance = request.form.get('starting_balance', '0').strip()

        if not name or not account_type:
            flash('Account name and type are required.', 'danger')
            return redirect(url_for('accounts_edit', account_id=account_id))

        try:
            starting_balance = float(starting_balance)
        except ValueError:
            flash('Starting balance must be a number.', 'danger')
            return redirect(url_for('accounts_edit', account_id=account_id))

        if starting_balance < 0:
            flash('Starting balance cannot be negative.', 'danger')
            return redirect(url_for('accounts_edit', account_id=account_id))

        execute_db(
            """
            UPDATE accounts
            SET name = ?, type = ?, starting_balance = ?
            WHERE id = ? AND user_id = ?
            """,
            (name, account_type, starting_balance, account_id, current_user.id)
        )

        flash('Account updated successfully.', 'success')
        return redirect(url_for('accounts_list'))

    return render_template('accounts/form.html', account=account)


@app.route('/accounts/<int:account_id>/delete', methods=['POST'])
@login_required
def accounts_delete(account_id):
    account = query_db(
        """
        SELECT id
        FROM accounts
        WHERE id = ? AND user_id = ?
        """,
        (account_id, current_user.id),
        one=True
    )

    if account is None:
        flash('Account not found.', 'danger')
        return redirect(url_for('accounts_list'))

    linked_transaction = query_db(
        """
        SELECT id
        FROM transactions
        WHERE account_id = ? AND user_id = ?
        LIMIT 1
        """,
        (account_id, current_user.id),
        one=True
    )

    if linked_transaction and linked_transaction['count'] > 0:
        flash(
            'This account cannot be deleted because it is linked to existing transactions.',
            'warning'
        )
        return redirect(url_for('accounts_list'))

    execute_db(
        """
        DELETE FROM accounts
        WHERE id = ? AND user_id = ?
        """,
        (account_id, current_user.id)
    )

    flash('Account deleted successfully.', 'success')
    return redirect(url_for('accounts_list'))

# ============================================================================
# 4. CATEGORIES CRUD  (Person C)
# ============================================================================

CATEGORY_TYPES = ['income', 'expense']

DEFAULT_COLOR_PALETTE = [
    '#198754', '#0d6efd', '#6f42c1', '#d63384',
    '#fd7e14', '#20c997', '#ffc107', '#6c757d'
]


def _color_distance(c1, c2):
    def hex_to_rgb(h):
        h = h.lstrip('#')
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    r1, g1, b1 = hex_to_rgb(c1)
    r2, g2, b2 = hex_to_rgb(c2)

    return abs(r1 - r2) + abs(g1 - g2) + abs(b1 - b2)


def get_next_color(user_id):
    used = query_db(
        "SELECT color FROM categories WHERE user_id = ?",
        (user_id,)
    ) or []

    used_colors = [c['color'] for c in used]

    for color in DEFAULT_COLOR_PALETTE:
        if all(_color_distance(color, u) > 120 for u in used_colors):
            return color

    return DEFAULT_COLOR_PALETTE[0]


@app.route('/categories')
@login_required
def categories_list():
    categories = query_db(
        """
        SELECT id, name, type, color,
        (SELECT COUNT(*) FROM transactions t WHERE t.category_id = categories.id) as usage_count
        FROM categories
        WHERE user_id = ?
        ORDER BY type, name
        """,
        (current_user.id,),
    )

    return render_template('categories/list.html', categories=categories)


@app.route('/categories/add', methods=['GET', 'POST'])
@login_required
def categories_add():
    categories = query_db(
        "SELECT name, color FROM categories WHERE user_id = ?",
        (current_user.id,),
    )

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        type_ = request.form.get('type', '').strip()

        color = request.form.get('color')
        if not color or color.strip() == '':
            color = get_next_color(current_user.id)

        if not name:
            flash('Category name is required.', 'danger')
            return render_template(
                'categories/form.html',
                category=None,
                types=CATEGORY_TYPES,
                categories=categories
            )

        if type_ not in CATEGORY_TYPES:
            flash('Type must be income or expense.', 'danger')
            return render_template(
                'categories/form.html',
                category=None,
                types=CATEGORY_TYPES,
                categories=categories
            )

        existing = query_db(
            "SELECT id FROM categories WHERE user_id = ? AND LOWER(name) = LOWER(?)",
            (current_user.id, name),
            one=True,
        )

        if existing:
            flash('Category already exists.', 'danger')
            return render_template(
                'categories/form.html',
                category=None,
                types=CATEGORY_TYPES,
                categories=categories
            )

        execute_db(
            "INSERT INTO categories (user_id, name, type, color) VALUES (?, ?, ?, ?)",
            (current_user.id, name, type_, color),
        )

        flash('Category added.', 'success')
        return redirect(url_for('categories_list'))

    return render_template(
        'categories/form.html',
        category=None,
        types=CATEGORY_TYPES,
        categories=categories
    )


@app.route('/categories/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
def categories_edit(category_id):
    category = query_db(
        """
        SELECT id, user_id, name, type, color,
        (SELECT COUNT(*) FROM transactions t WHERE t.category_id = categories.id) as usage_count
        FROM categories 
        WHERE id = ? AND user_id = ?
        """,
        (category_id, current_user.id),
        one=True,
    )

    if not category:
        flash('Category not found.', 'danger')
        return redirect(url_for('categories_list'))

    categories = query_db(
        "SELECT name, color FROM categories WHERE user_id = ?",
        (current_user.id,),
    )

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        type_ = request.form.get('type', '').strip()

        color = request.form.get('color')
        if not color or color.strip() == '':
            color = get_next_color(current_user.id)

        if not name:
            flash('Category name is required.', 'danger')
            return render_template(
                'categories/form.html',
                category=category,
                types=CATEGORY_TYPES,
                categories=categories
            )

        if type_ not in CATEGORY_TYPES:
            flash('Type must be income or expense.', 'danger')
            return render_template(
                'categories/form.html',
                category=category,
                types=CATEGORY_TYPES,
                categories=categories
            )

        if type_ != category['type'] and category['usage_count'] > 0:
            flash('Cannot change category type while transactions are tied to it.', 'danger')
            return render_template(
                'categories/form.html',
                category=category,
                types=CATEGORY_TYPES,
                categories=categories
            )

        existing = query_db(
            "SELECT id FROM categories WHERE user_id = ? AND LOWER(name) = LOWER(?) AND id != ?",
            (current_user.id, name, category_id),
            one=True,
        )

        if existing:
            flash('Category already exists.', 'danger')
            return render_template(
                'categories/form.html',
                category=category,
                types=CATEGORY_TYPES,
                categories=categories
            )

        execute_db(
            "UPDATE categories SET name = ?, type = ?, color = ? WHERE id = ? AND user_id = ?",
            (name, type_, color, category_id, current_user.id),
        )

        flash('Category updated.', 'success')
        return redirect(url_for('categories_list'))

    return render_template(
        'categories/form.html',
        category=category,
        types=CATEGORY_TYPES,
        categories=categories
    )


@app.route('/categories/<int:category_id>/delete', methods=['POST'])
@login_required
def categories_delete(category_id):
    usage = query_db(
        "SELECT COUNT(*) as count FROM transactions WHERE category_id = ? AND user_id = ?",
        (category_id, current_user.id),
        one=True,
    )

    if usage and usage['count'] > 0:
        flash('Cannot delete category with associated transactions.', 'danger')
        return redirect(url_for('categories_list'))

    execute_db(
        "DELETE FROM categories WHERE id = ? AND user_id = ?",
        (category_id, current_user.id),
    )

    flash('Category deleted.', 'success')
    return redirect(url_for('categories_list'))


# ============================================================================
# 5. TRANSACTIONS CRUD  (Person B)
# ============================================================================

@app.route('/transactions')
@login_required
def transactions_list():
    # TODO JOIN accounts + categories so names and colours show on the list
    return render_template_placeholder(
        'Transactions',
        'transactions/list.html'
    )


@app.route('/transactions/add', methods=['GET', 'POST'])
@login_required
def transactions_add():
    if request.method == 'POST':
        # TODO validate (amount > 0, account + category owned by user)
        # TODO INSERT INTO transactions
        pass

    # TODO load accounts + categories for dropdowns
    return render_template_placeholder(
        'Add transaction',
        'transactions/form.html'
    )


@app.route('/transactions/<int:transaction_id>/edit', methods=['GET', 'POST'])
@login_required
def transactions_edit(transaction_id):
    # TODO fetch by id AND user_id
    # TODO POST: UPDATE transactions SET ...
    return render_template_placeholder(
        'Edit transaction',
        'transactions/form.html'
    )


@app.route('/transactions/<int:transaction_id>/delete', methods=['POST'])
@login_required
def transactions_delete(transaction_id):
    # TODO DELETE FROM transactions WHERE id = ? AND user_id = ?
    return redirect(url_for('transactions_list'))


# ============================================================================
# 6. DASHBOARD  (Person B)
# ============================================================================

def get_total_balance(user_id):
    # TODO SUM(starting_balance) + SUM(income) - SUM(expenses)
    return 0.0


def get_monthly_income(user_id, month_start):
    # TODO SUM(amount) WHERE type='income' AND date >= month_start
    return 0.0


def get_monthly_expense(user_id, month_start):
    # TODO SUM(amount) WHERE type='expense' AND date >= month_start
    return 0.0


def get_expenses_by_category(user_id, month_start):
    # TODO GROUP BY category for the doughnut chart
    return []


def get_recent_transactions(user_id, limit=5):
    # TODO same JOIN as transactions_list, LIMIT ?
    return []


@app.route('/')
@login_required
def dashboard():
    today = datetime.today()
    month_start = today.replace(day=1).strftime('%Y-%m-%d')

    return render_template(
        'dashboard.html',
        total_balance=get_total_balance(current_user.id),
        month_income=get_monthly_income(current_user.id, month_start),
        month_expenses=get_monthly_expense(current_user.id, month_start),
        recent_transactions=get_recent_transactions(current_user.id, limit=5),
        expense_breakdown=get_expenses_by_category(current_user.id, month_start),
    )


# ============================================================================
# HELPERS / ERROR HANDLERS
# ============================================================================

def render_template_placeholder(title, template_path):
    try:
        return render_template(template_path)
    except Exception:
        return render_template('_placeholder.html', title=title)


@app.errorhandler(404)
def not_found(e):
    return render_template(
        '_error.html',
        code=404,
        message='Page not found.'
    ), 404


@app.errorhandler(500)
def server_error(e):
    return render_template(
        '_error.html',
        code=500,
        message='Something broke.'
    ), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
