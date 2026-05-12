"""FinTrack — Flask application.

Run with:
    python app.py

Then open http://localhost:5000

Sections below are split by owner (A/B/C/D). Edit your own section. If you
have to touch app.py outside your section (e.g. registering a new template
helper), flag it in the team chat first so we don't all clash on this file.
"""

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
# FR-11: session times out after 30 minutes of inactivity. Refreshed on each
# request below.
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to continue.'
login_manager.login_message_category = 'warning'


@app.before_request
def make_session_permanent():
    """Slide the 30-minute idle timeout forward on every request (FR-11)."""
    session.permanent = True


# ============================================================================
# 1. DATABASE HELPERS  (Person A)
# ============================================================================

def get_db():
    """Return the SQLite connection for this request (lazily opened)."""
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON;')
    return g.db


@app.teardown_appcontext
def close_db(exception):
    """Close the request's database connection if one was opened."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def query_db(query, args=(), one=False):
    """Run a SELECT and return rows (or a single row when one=True)."""
    cur = get_db().execute(query, args)
    rows = cur.fetchall()
    cur.close()
    return (rows[0] if rows else None) if one else rows


def execute_db(query, args=()):
    """Run an INSERT / UPDATE / DELETE and commit. Returns the new row id."""
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
    """Insert the starter set of categories for a brand-new user."""
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
    """Wraps a row from the users table for Flask-Login."""

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
    """Register a new user account and seed their default categories."""
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
    """Authenticate a user and start a session."""
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
    """End the current session."""
    logout_user()
    flash('Logged out.', 'success')
    return redirect(url_for('login'))


# ============================================================================
# 3. ACCOUNTS CRUD  (Person D)
# ----------------------------------------------------------------------------
# Follow the pattern from auth above:
#   - parameterised SQL (? placeholders), always
#   - filter every query by user_id = current_user.id
#   - flash() messages on success and failure
#   - POST-only delete routes
# Templates go in templates/accounts/{list,form}.html.
# ============================================================================

@app.route('/accounts')
@login_required
def accounts_list():
    """Show all accounts belonging to the current user."""
    # TODO query: SELECT * FROM accounts WHERE user_id = ? ORDER BY name
    # TODO render templates/accounts/list.html with accounts=rows
    return render_template_placeholder('Accounts list', 'accounts/list.html')


@app.route('/accounts/add', methods=['GET', 'POST'])
@login_required
def accounts_add():
    """Create a new account."""
    if request.method == 'POST':
        # TODO read: name, type, starting_balance from request.form
        # TODO validate (name non-empty, type in cash/bank/credit/savings, balance is a number)
        # TODO INSERT INTO accounts (user_id, name, type, starting_balance) VALUES (?, ?, ?, ?)
        # TODO flash success, redirect to accounts_list
        pass
    # TODO render templates/accounts/form.html with account=None (add mode)
    return render_template_placeholder('Add account', 'accounts/form.html')


@app.route('/accounts/<int:account_id>/edit', methods=['GET', 'POST'])
@login_required
def accounts_edit(account_id):
    """Edit an existing account (only if it belongs to the current user)."""
    # TODO fetch row WHERE id = ? AND user_id = ? — return 404 / redirect if None
    # TODO POST: UPDATE accounts SET ... WHERE id = ? AND user_id = ?
    # TODO render templates/accounts/form.html with account=row (edit mode)
    return render_template_placeholder('Edit account', 'accounts/form.html')


@app.route('/accounts/<int:account_id>/delete', methods=['POST'])
@login_required
def accounts_delete(account_id):
    """Delete an account belonging to the current user."""
    # TODO DELETE FROM accounts WHERE id = ? AND user_id = ?
    # TODO flash success, redirect
    return redirect(url_for('accounts_list'))


# ============================================================================
# 4. CATEGORIES CRUD  (Person C)
# ----------------------------------------------------------------------------
# Same pattern as accounts. Default categories are seeded at registration
# in seed_default_categories() — the user can edit / delete / add their own.
# ============================================================================

@app.route('/categories')
@login_required
def categories_list():
    """Show all categories belonging to the current user."""
    # TODO SELECT id, name, type, color FROM categories WHERE user_id = ? ORDER BY type, name
    return render_template_placeholder('Categories list', 'categories/list.html')


@app.route('/categories/add', methods=['GET', 'POST'])
@login_required
def categories_add():
    """Create a new category."""
    if request.method == 'POST':
        # TODO read: name, type ('income'/'expense'), color (hex)
        # TODO validate (name non-empty, type valid, color matches #RRGGBB)
        # TODO INSERT INTO categories ...
        pass
    return render_template_placeholder('Add category', 'categories/form.html')


@app.route('/categories/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
def categories_edit(category_id):
    """Edit an existing category."""
    # TODO fetch + validate ownership
    # TODO POST: UPDATE categories SET ...
    return render_template_placeholder('Edit category', 'categories/form.html')


@app.route('/categories/<int:category_id>/delete', methods=['POST'])
@login_required
def categories_delete(category_id):
    """Delete a category."""
    # TODO DELETE FROM categories WHERE id = ? AND user_id = ?
    # NB: schema uses ON DELETE CASCADE so deleting a category removes the
    # transactions tied to it. Decide as a team whether to warn the user first.
    return redirect(url_for('categories_list'))


# ============================================================================
# 5. TRANSACTIONS CRUD  (Person B)
# ----------------------------------------------------------------------------
# Each transaction belongs to one account and one category. Both must belong
# to the same user — check this in the route before INSERT / UPDATE.
# ============================================================================

@app.route('/transactions')
@login_required
def transactions_list():
    """List the user's transactions, newest first."""
    # TODO JOIN accounts and categories so the list page can show names + colours
    #   SELECT t.*, a.name AS account_name, c.name AS category_name, c.color
    #   FROM transactions t
    #   JOIN accounts a   ON a.id = t.account_id
    #   JOIN categories c ON c.id = t.category_id
    #   WHERE t.user_id = ?
    #   ORDER BY t.date DESC, t.id DESC
    return render_template_placeholder('Transactions', 'transactions/list.html')


@app.route('/transactions/add', methods=['GET', 'POST'])
@login_required
def transactions_add():
    """Create a new transaction."""
    if request.method == 'POST':
        # TODO read: amount, type, date, account_id, category_id, description
        # TODO validate (amount > 0, date parses, account & category owned by user)
        # TODO INSERT INTO transactions ...
        pass
    # GET: load the user's accounts and categories so the dropdowns can render.
    # TODO accounts = SELECT id, name FROM accounts WHERE user_id = ?
    # TODO categories = SELECT id, name, type FROM categories WHERE user_id = ?
    return render_template_placeholder('Add transaction', 'transactions/form.html')


@app.route('/transactions/<int:transaction_id>/edit', methods=['GET', 'POST'])
@login_required
def transactions_edit(transaction_id):
    """Edit an existing transaction."""
    # TODO fetch by id AND user_id
    # TODO POST: UPDATE transactions SET ...
    return render_template_placeholder('Edit transaction', 'transactions/form.html')


@app.route('/transactions/<int:transaction_id>/delete', methods=['POST'])
@login_required
def transactions_delete(transaction_id):
    """Delete a transaction."""
    # TODO DELETE FROM transactions WHERE id = ? AND user_id = ?
    return redirect(url_for('transactions_list'))


# ============================================================================
# 6. DASHBOARD  (Person B)
# ----------------------------------------------------------------------------
# These four helpers map 1:1 onto the Dashboard class in the SRS class
# diagram (getTotalBalance / getMonthlyIncome / getMonthlyExpense /
# getExpensesByCategory). Keep the names in sync so the diagram still
# matches the code at submission.
# ============================================================================

def get_total_balance(user_id):
    """Total balance = sum of starting balances + income - expenses."""
    # TODO query: SUM(starting_balance) FROM accounts WHERE user_id = ?
    # TODO query: SUM(amount) FROM transactions WHERE user_id=? AND type='income'
    # TODO query: SUM(amount) FROM transactions WHERE user_id=? AND type='expense'
    # TODO return balance + income - expense (handle None when there are no rows)
    return 0.0


def get_monthly_income(user_id, month_start):
    """Total income recorded since the first of the current month."""
    # TODO SUM(amount) FROM transactions WHERE user_id=? AND type='income' AND date >= ?
    return 0.0


def get_monthly_expense(user_id, month_start):
    """Total expenses recorded since the first of the current month."""
    # TODO SUM(amount) FROM transactions WHERE user_id=? AND type='expense' AND date >= ?
    return 0.0


def get_expenses_by_category(user_id, month_start):
    """Return [{name, color, total}, ...] for the dashboard doughnut chart."""
    # TODO SELECT c.name, c.color, SUM(t.amount) AS total
    #      FROM transactions t JOIN categories c ON c.id = t.category_id
    #      WHERE t.user_id = ? AND t.type = 'expense' AND t.date >= ?
    #      GROUP BY c.id ORDER BY total DESC
    return []


def get_recent_transactions(user_id, limit=5):
    """Return the user's N most recent transactions joined with names/colours."""
    # TODO same JOIN as transactions_list, ORDER BY date DESC LIMIT ?
    return []


@app.route('/')
@login_required
def dashboard():
    """Summary view: balance, monthly totals, breakdown chart, recent activity."""
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
    """Tiny helper used while features are still being built out.

    Tries the real template first; if it doesn't exist yet, falls back to a
    generic 'not built yet' page so the navigation links don't 500 on day 1.
    Delete this once every feature has its own templates.
    """
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


# ============================================================================
# RUN
# ============================================================================

if __name__ == '__main__':
    app.run(debug=True, port=5000)
