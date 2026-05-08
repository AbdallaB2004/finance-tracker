# Developer Setup

Follow this once when you first clone the repo.

## 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/finance-tracker-swe5303.git
cd finance-tracker-swe5303
```

## 2. Create a virtual environment

A virtual environment keeps this project's Python packages separate from anything else on your machine.

**Windows (Command Prompt):**

```bash
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux (Terminal):**

```bash
python -m venv venv
source venv/bin/activate
```

You should see `(venv)` at the start of your prompt. That means it's active.

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

That installs Flask, Flask-Login and Werkzeug.

## 4. Create the database

```bash
python init_db.py
```

This creates `finance.db` (a SQLite file). It is in `.gitignore`, so it stays local — every dev has their own copy.

## 5. Run the app

```bash
python app.py
```

You should see something like:

```
Running on http://127.0.0.1:5000
```

Open the URL in a browser. You will see placeholder pages — that's expected at this stage.

## 6. Stop the app

`Ctrl+C` in the terminal.

---

## Every time you sit down to work

1. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS / Linux: `source venv/bin/activate`
2. Pull the latest code:
   ```bash
   git pull origin main
   ```
3. Switch to (or create) your feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. Run the app:
   ```bash
   python app.py
   ```

---

## Project structure

- `app.py` — main Flask app, with sections marked by owner:
  - Person A: database helpers + auth
  - Person B: transactions + dashboard
  - Person C: categories
  - Person D: accounts
- `schema.sql` — database design (read-only reference)
- `init_db.py` — builds `finance.db` from `schema.sql`
- `requirements.txt` — Python packages
- `templates/` — HTML files (you will add these as you build pages):
  - `base.html` — base template (navbar, layout)
  - `login.html`, `register.html` — auth pages
  - `dashboard.html` — home page
  - `accounts_list.html`, `accounts_form.html` — account pages
  - `categories_list.html`, `categories_form.html` — category pages
  - `transactions_list.html`, `transactions_form.html` — transaction pages
- `static/css/` — stylesheets
- `static/js/` — front-end JavaScript

---

## Git workflow

1. Create a branch from up-to-date `main`:
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/your-feature-name
   ```
2. Edit your section in `app.py` (and templates as needed).
3. Test locally with `python app.py`.
4. Stage and commit:
   ```bash
   git add .
   git commit -m "short clear description of the change"
   ```
5. Push to GitHub:
   ```bash
   git push origin feature/your-feature-name
   ```
6. Open a Pull Request on GitHub and request a review from Person A.
7. Once approved, merge into `main` (use the GitHub UI).

---

## Code rules — read before you commit

**SQL — always use `?` placeholders:**

```python
# correct
query_db("SELECT * FROM users WHERE username = ?", (username,))

# wrong — SQL injection risk
query_db(f"SELECT * FROM users WHERE username = '{username}'")
```

**Passwords — always hash, never plaintext:**

```python
from werkzeug.security import generate_password_hash, check_password_hash

password_hash = generate_password_hash(password)
# later, on login:
if check_password_hash(stored_hash, password):
    ...
```

**Auth — every route that reads user data needs both guards:**

```python
@app.route('/accounts')
@login_required
def accounts_list():
    rows = query_db(
        "SELECT * FROM accounts WHERE user_id = ?",
        (current_user.id,),
    )
    ...
```

**Style — PEP 8:**

- 4-space indentation
- `snake_case` for functions and variables
- short docstrings on routes and helpers
- descriptive names (`transaction_list`, not `tl`)

---

## Where to look for what

- **What is the project?** — `README.md`
- **What am I building?** — `REQUIREMENTS.md`
- **What do I do day to day?** — `WORKFLOW_CHECKLIST.md`

If you are stuck for more than an hour or two, post in the team chat. Don't sit on a blocker.
