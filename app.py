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

from datetime import datetime

from flask import (
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from flask_login import (
    login_required,
    current_user
)


# ============================================================================
# ACCOUNTS MODULE
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
