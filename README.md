# Finance Tracker — SWE5303

A personal finance web app built with Flask, SQLite and Bootstrap 5. Group project for SWE5303.

## What the app does

A logged-in user can:

- Register and sign in
- Manage multiple financial accounts (cash, bank, credit, savings)
- Create income and expense categories
- Record transactions (date, amount, category, account, description)
- View a dashboard with total balance, monthly income, monthly expenses, and an expense breakdown chart

## Quick start

### 1. Set up your environment (first time only)

```bash
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Create the database (first time only)

```bash
python init_db.py
```

This creates `finance.db` from `schema.sql`.

### 3. Run the app

```bash
python app.py
```

Open `http://localhost:5000`.

## Project files

- `app.py` — Flask application, split into ownership sections
- `schema.sql` — database design (4 tables)
- `init_db.py` — creates the SQLite database from the schema
- `requirements.txt` — Python dependencies
- `templates/` — Jinja HTML templates
- `static/css/`, `static/js/` — front-end assets

## Workflow at a glance

1. `git checkout -b feature/your-feature-name`
2. Code your section
3. Test locally
4. `git commit -m "short, clear message"`
5. `git push origin feature/your-feature-name`
6. Open a PR on GitHub and request a review
7. Once approved, merge into `main`

## Code rules

- **SQL:** always use `?` placeholders, never f-strings or `%` formatting on user input
- **Passwords:** always hash with Werkzeug, never store plaintext
- **Auth:** every route that touches user data needs `@login_required` plus `WHERE user_id = ?` in the query
- **Style:** PEP 8 — 4-space indent, snake_case, short docstrings on functions

## Team

- Person A (Lead, Auth + DB):
- Person B (Transactions + Dashboard):
- Person C (Categories):
- Person D (Accounts):

## More documentation

- `DEV_SETUP.md` — full environment setup walkthrough
- `REQUIREMENTS.md` — functional and non-functional requirements
- `WORKFLOW_CHECKLIST.md` — daily / weekly checklists
