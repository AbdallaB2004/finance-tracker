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
            "SELECT id FROM users WHERE username = ?", (username,), one=True,
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
            "SELECT * FROM users WHERE username = ?", (username,), one=True,
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
    # TODO SELECT * FROM accounts WHERE user_id = ? ORDER BY name
    # TODO render templates/accounts/list.html
    return render_template_placeholder('Accounts', 'accounts/list.html')


@app.route('/accounts/add', methods=['GET', 'POST'])
@login_required
def accounts_add():
    if request.method == 'POST':
        # TODO read + validate name, type, starting_balance
        # TODO INSERT INTO accounts (user_id, name, type, starting_balance)
        # TODO flash + redirect to accounts_list
        pass
    return render_template_placeholder('Add account', 'accounts/form.html')


@app.route('/accounts/<int:account_id>/edit', methods=['GET', 'POST'])
@login_required
def accounts_edit(account_id):
    # TODO fetch WHERE id = ? AND user_id = ?
    # TODO POST: UPDATE accounts SET ... WHERE id = ? AND user_id = ?
    return render_template_placeholder('Edit account', 'accounts/form.html')


@app.route('/accounts/<int:account_id>/delete', methods=['POST'])
@login_required
def accounts_delete(account_id):
    # TODO DELETE FROM accounts WHERE id = ? AND user_id = ?
    return redirect(url_for('accounts_list'))


# ============================================================================
# 4. CATEGORIES CRUD  (Person C)
# ============================================================================

@app.route('/categories')
@login_required
def categories_list():
    # TODO SELECT id, name, type, color FROM categories WHERE user_id = ?
    return render_template_placeholder('Categories', 'categories/list.html')


@app.route('/categories/add', methods=['GET', 'POST'])
@login_required
def categories_add():
    if request.method == 'POST':
        # TODO read + validate name, type, color
        # TODO INSERT INTO categories
        pass
    return render_template_placeholder('Add category', 'categories/form.html')


@app.route('/categories/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
def categories_edit(category_id):
    # TODO fetch + check ownership
    # TODO POST: UPDATE categories SET ...
    return render_template_placeholder('Edit category', 'categories/form.html')


@app.route('/categories/<int:category_id>/delete', methods=['POST'])
@login_required
def categories_delete(category_id):
    # TODO DELETE FROM categories WHERE id = ? AND user_id = ?
    return redirect(url_for('categories_list'))


# ============================================================================
# 5. TRANSACTIONS CRUD  (Person B)
# ============================================================================

@app.route('/transactions')
@login_required
def transactions_list():
    # TODO JOIN accounts + categories so names and colours show on the list
    return render_template_placeholder('Transactions', 'transactions/list.html')


@app.route('/transactions/add', methods=['GET', 'POST'])
@login_required
def transactions_add():
    if request.method == 'POST':
        # TODO validate (amount > 0, account + category owned by user)
        # TODO INSERT INTO transactions
        pass
    # TODO load accounts + categories for dropdowns
    return render_template_placeholder('Add transaction', 'transactions/form.html')


@app.route('/transactions/<int:transaction_id>/edit', methods=['GET', 'POST'])
@login_required
def transactions_edit(transaction_id):
    # TODO fetch by id AND user_id
    # TODO POST: UPDATE transactions SET ...
    return render_template_placeholder('Edit transaction', 'transactions/form.html')


@app.route('/transactions/<int:transaction_id>/delete', methods=['POST'])
@login_required
def transactions_delete(transaction_id):
    # TODO DELETE FROM transactions WHERE id = ? AND user_id = ?
    return redirect(url_for('transactions_list'))


# ============================================================================
# 6. DASHBOARD  (Person B)
# Names map to the SRS class diagram: getTotalBalance, getMonthlyIncome,
# getMonthlyExpense, getExpensesByCategory.
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
    return render_template('_error.html', code=404, message='Page not found.'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('_error.html', code=500, message='Something broke.'), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
