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


@app.route("/")
def splash():
    return render_template("splash.html")

@app.route("/welcome")
def welcome():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    return render_template("welcome.html")

@app.route("/goals", methods=["GET", "POST"])
def goals():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        goal = request.form.get("goal")
        session["goal"] = goal
        return redirect(url_for("register"))

    return render_template("goals.html")


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    selected_goal = session.get("goal", "")

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')

        if len(username) < 3:
            flash('Username must be at least 3 characters.', 'danger')
            return render_template(
                'auth/register.html',
                username=username,
                selected_goal=selected_goal
            )

        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'danger')
            return render_template(
                'auth/register.html',
                username=username,
                selected_goal=selected_goal
            )

        if password != password_confirm:
            flash('Passwords do not match.', 'danger')
            return render_template(
                'auth/register.html',
                username=username,
                selected_goal=selected_goal
            )

        existing = query_db(
            "SELECT id FROM users WHERE username = ?",
            (username,),
            one=True,
        )

        if existing:
            flash('That username is taken.', 'danger')
            return render_template(
                'auth/register.html',
                username=username,
                selected_goal=selected_goal
            )

        user_id = execute_db(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, generate_password_hash(password)),
        )

        seed_default_categories(user_id)

        session.pop("goal", None)

        flash('Account created. Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template(
        'auth/register.html',
        username='',
        selected_goal=selected_goal
    )


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

    for account in accounts:
        usage = query_db(
            "SELECT COUNT(*) as count FROM transactions WHERE account_id = ? AND user_id = ?",
            (account['id'], current_user.id),
            one=True,
        )
        account['usage_count'] = usage['count'] if usage else 0

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

    if linked_transaction is not None:
        flash(
            'This account cannot be deleted because it is linked to existing transactions.',
            'danger'
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

# This route shows the full list of transactions for the logged-in user.
# @app.route tells Flask: when someone visits /transactions, run this function.
# @login_required means: if the user is not logged in, redirect them to login first.
@app.route('/transactions')
@login_required
def transactions_list():
    """Show all transactions for the logged-in user, newest first."""

    # Go into the database and fetch all transactions that belong to the logged-in user.
    # We also JOIN with the accounts and categories tables so we get the account name
    # and category name/colour — otherwise we would only get ID numbers.
    # ORDER BY date DESC means newest transactions appear at the top.
    transactions = query_db(
        """
        SELECT t.id, t.amount, t.type, t.date, t.description,
               a.name AS account_name,
               c.name AS category_name,
               c.color AS category_color
        FROM transactions t
        JOIN accounts a ON a.id = t.account_id
        JOIN categories c ON c.id = t.category_id
        WHERE t.user_id = ?
        ORDER BY t.date DESC, t.created_at DESC
        """,
        (current_user.id,),
    )

    # Send the list of transactions to the HTML template so it can display them.
    return render_template('transactions/list.html', transactions=transactions)


# This route handles the Add Transaction page.
# methods=['GET', 'POST'] means it handles two situations:
#   GET  = user just opened the form (show the empty form)
#   POST = user filled in the form and clicked submit (save the data)
@app.route('/transactions/add', methods=['GET', 'POST'])
@login_required
def transactions_add():
    """Show the add-transaction form (GET) and save a new transaction (POST)."""

    # Load the user's accounts from the database so we can show them in a dropdown.
    accounts = query_db(
        "SELECT id, name FROM accounts WHERE user_id = ? ORDER BY name",
        (current_user.id,),
    )

    # Load the user's categories from the database so we can show them in a dropdown.
    categories = query_db(
        "SELECT id, name, type FROM categories WHERE user_id = ? ORDER BY type, name",
        (current_user.id,),
    )

    # Only run the code below if the user actually submitted the form (clicked the button).
    if request.method == 'POST':

        # Read each field the user typed or selected in the form.
        # .strip() removes any accidental spaces at the start or end.
        amount_raw = request.form.get('amount', '').strip()
        type_ = request.form.get('type', '').strip()
        date = request.form.get('date', '').strip()
        account_id_raw = request.form.get('account_id', '').strip()
        category_id_raw = request.form.get('category_id', '').strip()
        description = request.form.get('description', '').strip()

        # --- Validation: check the data before saving anything ---

        # Start with no error.
        error = None

        # Check the amount field is not empty.
        if not amount_raw:
            error = 'Amount is required.'
        else:
            # Try to convert the amount to a decimal number.
            # If the user typed letters, float() will fail and we catch it with ValueError.
            try:
                amount = float(amount_raw)
                if amount <= 0:
                    error = 'Amount must be greater than zero.'
            except ValueError:
                error = 'Amount must be a number.'

        # Check the type is exactly 'income' or 'expense' — nothing else is allowed.
        if not error and type_ not in ('income', 'expense'):
            error = 'Type must be income or expense.'

        # Check the date field is not empty.
        if not error and not date:
            error = 'Date is required.'

        # Security check: make sure the chosen account actually belongs to this user.
        # This stops someone from manually sending a different user's account ID.
        if not error:
            account = query_db(
                "SELECT id FROM accounts WHERE id = ? AND user_id = ?",
                (account_id_raw, current_user.id),
                one=True,
            )
            if not account:
                error = 'Invalid account.'

        # Security check: same thing for the category.
        if not error:
            category = query_db(
                "SELECT id FROM categories WHERE id = ? AND user_id = ?",
                (category_id_raw, current_user.id),
                one=True,
            )
            if not category:
                error = 'Invalid category.'

        # If any validation check above found a problem, show the error message
        # and send the user back to the form so they can fix it.
        if error:
            flash(error, 'danger')
            return render_template(
                'transactions/form.html',
                transaction=None,
                accounts=accounts,
                categories=categories,
            )

        # All checks passed — save the new transaction to the database.
        execute_db(
            """
            INSERT INTO transactions
                (user_id, account_id, category_id, amount, type, date, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (current_user.id, int(account_id_raw), int(category_id_raw),
             amount, type_, date, description),
        )

        # Show a green success message and send the user back to the transactions list.
        flash('Transaction added.', 'success')
        return redirect(url_for('transactions_list'))

    # If the user just opened the page (GET), show the empty form.
    return render_template(
        'transactions/form.html',
        transaction=None,
        accounts=accounts,
        categories=categories,
    )


# This route handles the Edit Transaction page.
# <int:transaction_id> means the URL contains the ID of the transaction to edit,
# for example: /transactions/3/edit
@app.route('/transactions/<int:transaction_id>/edit', methods=['GET', 'POST'])
@login_required
def transactions_edit(transaction_id):
    """Show the edit form pre-filled with existing data (GET) and save changes (POST)."""

    # Fetch the transaction we want to edit.
    # We check BOTH the transaction ID and the user_id so a user
    # cannot edit another user's transactions by changing the URL.
    transaction = query_db(
        "SELECT * FROM transactions WHERE id = ? AND user_id = ?",
        (transaction_id, current_user.id),
        one=True,
    )

    # If the transaction does not exist or belongs to someone else, show an error
    # and send the user back to the list.
    if not transaction:
        flash('Transaction not found.', 'danger')
        return redirect(url_for('transactions_list'))

    # Load accounts and categories for the dropdowns (same as the add form).
    accounts = query_db(
        "SELECT id, name FROM accounts WHERE user_id = ? ORDER BY name",
        (current_user.id,),
    )
    categories = query_db(
        "SELECT id, name, type FROM categories WHERE user_id = ? ORDER BY type, name",
        (current_user.id,),
    )

    # Only run the code below if the user submitted the form.
    if request.method == 'POST':

        # Read the updated values from the form.
        amount_raw = request.form.get('amount', '').strip()
        type_ = request.form.get('type', '').strip()
        date = request.form.get('date', '').strip()
        account_id_raw = request.form.get('account_id', '').strip()
        category_id_raw = request.form.get('category_id', '').strip()
        description = request.form.get('description', '').strip()

        # --- Validation: same checks as the add form ---
        error = None

        if not amount_raw:
            error = 'Amount is required.'
        else:
            try:
                amount = float(amount_raw)
                if amount <= 0:
                    error = 'Amount must be greater than zero.'
            except ValueError:
                error = 'Amount must be a number.'

        if not error and type_ not in ('income', 'expense'):
            error = 'Type must be income or expense.'

        if not error and not date:
            error = 'Date is required.'

        if not error:
            account = query_db(
                "SELECT id FROM accounts WHERE id = ? AND user_id = ?",
                (account_id_raw, current_user.id),
                one=True,
            )
            if not account:
                error = 'Invalid account.'

        if not error:
            category = query_db(
                "SELECT id FROM categories WHERE id = ? AND user_id = ?",
                (category_id_raw, current_user.id),
                one=True,
            )
            if not category:
                error = 'Invalid category.'

        # If any check failed, show the error and send the user back to the form.
        if error:
            flash(error, 'danger')
            return render_template(
                'transactions/form.html',
                transaction=transaction,
                accounts=accounts,
                categories=categories,
            )

        # All checks passed — update the existing transaction in the database.
        # UPDATE overwrites the old values with the new ones.
        # WHERE id = ? AND user_id = ? is a final security check.
        execute_db(
            """
            UPDATE transactions
            SET account_id = ?, category_id = ?, amount = ?,
                type = ?, date = ?, description = ?
            WHERE id = ? AND user_id = ?
            """,
            (int(account_id_raw), int(category_id_raw), amount,
             type_, date, description, transaction_id, current_user.id),
        )

        # Show a green success message and send the user back to the list.
        flash('Transaction updated.', 'success')
        return redirect(url_for('transactions_list'))

    # If the user just opened the page (GET), show the form pre-filled
    # with the existing transaction data.
    return render_template(
        'transactions/form.html',
        transaction=transaction,
        accounts=accounts,
        categories=categories,
    )


# This route deletes a transaction.
# methods=['POST'] means it only accepts a form submission — NOT a URL visit.
# This prevents accidental deletion if someone just opens a link.
@app.route('/transactions/<int:transaction_id>/delete', methods=['POST'])
@login_required
def transactions_delete(transaction_id):
    """Delete a transaction belonging to the logged-in user."""

    # Delete the transaction from the database.
    # WHERE id = ? AND user_id = ? makes sure users can only delete their own transactions.
    execute_db(
        "DELETE FROM transactions WHERE id = ? AND user_id = ?",
        (transaction_id, current_user.id),
    )

    # Show a green success message and send the user back to the transactions list.
    flash('Transaction deleted.', 'success')
    return redirect(url_for('transactions_list'))


# ============================================================================
# 6. DASHBOARD  (Person B)
# ============================================================================

def get_total_balance(user_id):
    """Calculate the user's total balance across all accounts.

    Formula: sum of all account starting balances + all income ever - all expenses ever.
    """

    # Add up the starting balance of every account the user has.
    # COALESCE(..., 0) means: if there are no rows, return 0 instead of NULL.
    base = query_db(
        "SELECT COALESCE(SUM(starting_balance), 0) AS total FROM accounts WHERE user_id = ?",
        (user_id,),
        one=True,
    )

    # Add up every income transaction the user has ever logged.
    income = query_db(
        "SELECT COALESCE(SUM(amount), 0) AS total FROM transactions WHERE user_id = ? AND type = 'income'",
        (user_id,),
        one=True,
    )

    # Add up every expense transaction the user has ever logged.
    expense = query_db(
        "SELECT COALESCE(SUM(amount), 0) AS total FROM transactions WHERE user_id = ? AND type = 'expense'",
        (user_id,),
        one=True,
    )

    # Return: starting balances + all income - all expenses = current total balance.
    return (base['total'] or 0.0) + (income['total'] or 0.0) - (expense['total'] or 0.0)


def get_monthly_income(user_id, month_start):
    """Return the total income for the current month only.

    month_start is the first day of the current month, e.g. '2026-05-01'.
    Only transactions on or after that date are counted.
    """

    # Sum all income transactions from the start of this month onwards.
    row = query_db(
        """
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM transactions
        WHERE user_id = ? AND type = 'income' AND date >= ?
        """,
        (user_id, month_start),
        one=True,
    )
    return row['total'] if row else 0.0


def get_monthly_expense(user_id, month_start):
    """Return the total expenses for the current month only.

    month_start is the first day of the current month, e.g. '2026-05-01'.
    Only transactions on or after that date are counted.
    """

    # Sum all expense transactions from the start of this month onwards.
    row = query_db(
        """
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM transactions
        WHERE user_id = ? AND type = 'expense' AND date >= ?
        """,
        (user_id, month_start),
        one=True,
    )
    return row['total'] if row else 0.0


def get_expenses_by_category(user_id, month_start):
    """Return this month's expenses grouped by category for the doughnut chart.

    Each row contains the category name, its colour, and the total spent in it.
    """

    # GROUP BY c.id groups all transactions under the same category together
    # and adds up their amounts into one total per category.
    # ORDER BY total DESC puts the biggest spending category first in the chart.
    return query_db(
        """
        SELECT c.name, c.color, COALESCE(SUM(t.amount), 0) AS total
        FROM transactions t
        JOIN categories c ON c.id = t.category_id
        WHERE t.user_id = ? AND t.type = 'expense' AND t.date >= ?
        GROUP BY c.id
        ORDER BY total DESC
        """,
        (user_id, month_start),
    )


def get_recent_transactions(user_id, limit=5):
    """Return the most recent transactions for the dashboard preview table.

    limit=5 means only the last 5 transactions are returned by default.
    """

    # Same query as transactions_list but LIMIT restricts it to the last few rows.
    return query_db(
        """
        SELECT t.id, t.amount, t.type, t.date, t.description,
               a.name AS account_name,
               c.name AS category_name,
               c.color AS category_color
        FROM transactions t
        JOIN accounts a ON a.id = t.account_id
        JOIN categories c ON c.id = t.category_id
        WHERE t.user_id = ?
        ORDER BY t.date DESC, t.created_at DESC
        LIMIT ?
        """,
        (user_id, limit),
    )


# This is the main dashboard page — the first thing users see after logging in.
# @app.route('/dashboard') means it runs when someone visits the dashboard URL.
@app.route('/dashboard')
@login_required
def dashboard():
    """Show the dashboard with balance summary, chart and recent transactions."""

    # Get today's date and calculate the first day of the current month.
    # For example: if today is 16 May 2026, month_start becomes '2026-05-01'.
    # This is passed to the helper functions so they only count this month's data.
    today = datetime.today()
    month_start = today.replace(day=1).strftime('%Y-%m-%d')

    # Call each helper function to get the numbers,
    # then pass them all to the dashboard HTML template to display on the page.
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
