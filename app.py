"""Finance Tracker Flask application.

Run with:
    python app.py

Then open http://localhost:5000
"""

import sqlite3

from flask import Flask, redirect, render_template, request, session, url_for
from flask_login import LoginManager, login_required

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-change-in-production'
app.config['DATABASE'] = 'finance.db'

login_manager = LoginManager(app)
login_manager.login_view = 'login'


# ============================================================================
# 1. DATABASE HELPERS  (Person A)
# ============================================================================

def get_db():
    """Open a connection to the SQLite database."""
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn


def query_db(query, args=(), one=False):
    """Run a SELECT query and return rows (or a single row)."""
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


# ============================================================================
# 2. AUTH ROUTES  (Person A)
# ============================================================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Register a new user account."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        password_confirm = request.form.get('password_confirm', '').strip()

        if not username or len(username) < 3:
            return redirect(url_for('register'))
        if not password or len(password) < 8:
            return redirect(url_for('register'))
        if password != password_confirm:
            return redirect(url_for('register'))

        # TODO hash password with werkzeug.security.generate_password_hash
        # TODO check if username already exists
        # TODO INSERT new user into the users table
        # TODO seed default categories for this user
        # TODO redirect to login with a success flash message

        return redirect(url_for('login'))

    return "TODO: register.html form"


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Authenticate a user and start a session."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        # TODO look up user by username (parameterised query)
        # TODO compare password with werkzeug.security.check_password_hash
        # TODO on success, log in via Flask-Login and redirect to dashboard
        # TODO on failure, flash an error and stay on the login page

        return redirect(url_for('dashboard'))

    return "TODO: login.html form"


@app.route('/logout')
@login_required
def logout():
    """End the current user session."""
    # TODO call Flask-Login logout_user()
    # TODO redirect to login page
    return redirect(url_for('login'))


# ============================================================================
# 3. ACCOUNTS CRUD  (Person D)
# ============================================================================

@app.route('/accounts')
@login_required
def accounts_list():
    """Show all accounts belonging to the current user."""
    # TODO SELECT all accounts WHERE user_id = current_user.id
    # TODO render accounts_list.html
    return "TODO: accounts_list.html"


@app.route('/accounts/add', methods=['GET', 'POST'])
@login_required
def accounts_add():
    """Create a new account."""
    if request.method == 'POST':
        # TODO read form fields (name, type, starting_balance)
        # TODO validate inputs
        # TODO INSERT into accounts table
        # TODO redirect to accounts_list
        pass
    return "TODO: accounts_form.html (add)"


@app.route('/accounts/<int:account_id>/edit', methods=['GET', 'POST'])
@login_required
def accounts_edit(account_id):
    """Edit an existing account."""
    # TODO fetch account by id AND user_id
    # TODO 404 / redirect if not owned
    # TODO GET: prefill the form
    # TODO POST: UPDATE the row
    return "TODO: accounts_form.html (edit)"


@app.route('/accounts/<int:account_id>/delete', methods=['POST'])
@login_required
def accounts_delete(account_id):
    """Delete an account."""
    # TODO confirm ownership (id AND user_id)
    # TODO DELETE FROM accounts
    return redirect(url_for('accounts_list'))


# ============================================================================
# 4. CATEGORIES CRUD  (Person C)
# ============================================================================

@app.route('/categories')
@login_required
def categories_list():
    """Show all categories belonging to the current user."""
    # TODO SELECT all categories WHERE user_id = current_user.id
    return "TODO: categories_list.html"


@app.route('/categories/add', methods=['GET', 'POST'])
@login_required
def categories_add():
    """Create a new category."""
    if request.method == 'POST':
        # TODO read form fields (name, type income/expense, color)
        # TODO validate
        # TODO INSERT into categories
        pass
    return "TODO: categories_form.html (add)"


@app.route('/categories/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
def categories_edit(category_id):
    """Edit an existing category."""
    # TODO fetch category by id AND user_id
    # TODO GET: prefill the form
    # TODO POST: UPDATE the row
    return "TODO: categories_form.html (edit)"


@app.route('/categories/<int:category_id>/delete', methods=['POST'])
@login_required
def categories_delete(category_id):
    """Delete a category."""
    # TODO confirm ownership (id AND user_id)
    # TODO DELETE FROM categories
    return redirect(url_for('categories_list'))


# ============================================================================
# 5. TRANSACTIONS CRUD  (Person B)
# ============================================================================

@app.route('/transactions')
@login_required
def transactions_list():
    """Show all transactions belonging to the current user."""
    # TODO SELECT all transactions WHERE user_id = current_user.id
    # TODO ORDER BY date DESC
    return "TODO: transactions_list.html"


@app.route('/transactions/add', methods=['GET', 'POST'])
@login_required
def transactions_add():
    """Create a new transaction."""
    if request.method == 'POST':
        # TODO read form fields (amount, type, date, account_id, category_id, description)
        # TODO validate (amount > 0, date valid, account and category belong to user)
        # TODO INSERT into transactions
        pass
    # GET: load user's accounts and categories so the dropdowns can render
    return "TODO: transactions_form.html (add)"


@app.route('/transactions/<int:transaction_id>/edit', methods=['GET', 'POST'])
@login_required
def transactions_edit(transaction_id):
    """Edit an existing transaction."""
    # TODO fetch transaction by id AND user_id
    # TODO GET: prefill the form
    # TODO POST: UPDATE the row
    return "TODO: transactions_form.html (edit)"


@app.route('/transactions/<int:transaction_id>/delete', methods=['POST'])
@login_required
def transactions_delete(transaction_id):
    """Delete a transaction."""
    # TODO confirm ownership (id AND user_id)
    # TODO DELETE FROM transactions
    return redirect(url_for('transactions_list'))


# ============================================================================
# 6. DASHBOARD  (Person B)
# ============================================================================

@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    """Summary view: balance, monthly totals, chart, recent transactions."""
    # TODO total balance = sum(starting_balance) + sum(income) - sum(expense)
    # TODO month income = SUM(amount) WHERE type='income' AND date in current month
    # TODO month expenses = SUM(amount) WHERE type='expense' AND date in current month
    # TODO recent 5 transactions ORDER BY date DESC LIMIT 5
    # TODO expense breakdown by category (for the chart)
    return "TODO: dashboard.html"


@app.route('/api/dashboard-chart-data')
@login_required
def dashboard_chart_data():
    """Return expense breakdown by category as JSON for Chart.js."""
    # TODO query categories joined with SUM(transactions.amount)
    # TODO filter: current user, current month, type='expense'
    # TODO return list of {name, value, color}
    return "TODO: return JSON"


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(e):
    return "404 Not Found", 404


@app.errorhandler(500)
def server_error(e):
    return "500 Server Error", 500


# ============================================================================
# RUN
# ============================================================================

if __name__ == '__main__':
    app.run(debug=True, port=5000)
