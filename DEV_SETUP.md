# Developer Setup

Follow this once when you first clone the repo. Keep it open the first day, you'll come back to it.

## 1. Clone the repo

```bash
git clone https://github.com/Abdalla2004-collab/finance-tracker-swe5303.git
cd finance-tracker-swe5303
```

## 2. Create a virtual environment

A virtual environment keeps this project's Python packages separate from anything else on your machine.

**Windows (Command Prompt):**

```bash
python -m venv venv
venv\Scripts\activate
```

**Windows (PowerShell):**

```bash
python -m venv venv
venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
python -m venv venv
source venv/bin/activate
```

You should see `(venv)` at the start of your prompt. That means it's active. Activate the venv every time you open a new terminal for this project. It's the most common gotcha.

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

That installs Flask, Flask-Login and Werkzeug.

## 4. Create the database

```bash
python init_db.py
```

This creates `finance.db`, a SQLite file. It's in `.gitignore` so every dev has their own local copy. If you ever need to wipe your data, delete the file and re-run.

## 5. Run the app

```bash
python app.py
```

You should see:

```
 * Running on http://127.0.0.1:5000
```

Open it. You'll see the login page. Click Register, create a test account (`testuser` / `password123`), log in. If that works, your environment is set up.

## 6. Stop the app

`Ctrl+C` in the terminal.

---

## Every time you sit down to work

```bash
# 1. activate the venv
source venv/bin/activate   # or venv\Scripts\activate on Windows

# 2. pull the latest main
git checkout main
git pull

# 3. branch for your work
git checkout -b feature/your-feature-name

# 4. run the app to confirm everything still works
python app.py
```

---

## Git workflow

We use GitHub Flow. Simple, no rebase, no force-push.

```bash
# branch
git checkout main
git pull
git checkout -b feature/accounts-list

# work, save files, then:
git add .
git commit -m "add accounts list view"
git push -u origin feature/accounts-list
```

Go to GitHub. There'll be a yellow "Compare & pull request" banner. Click it. Write a short description (what you did, anything reviewers should check carefully). Assign A as reviewer. Open the PR.

A reviews, leaves comments if needed. You push more commits to the same branch to address them, and the PR updates automatically. When approved, A clicks merge.

**Branch naming:** `feature/<short-name>` or `fix/<short-name>`. Lowercase, hyphens.

**Commit messages:** lowercase, present tense, under 60 chars. `add budget filter` not `Updated Stuff` or `WIP final final FINAL`.

**Delete your branch after merge.** GitHub gives you a button on the PR.

---

## Code rules: the things that bite you

### SQL: always parameterise

```python
# right
query_db("SELECT * FROM users WHERE username = ?", (username,))

# wrong: SQL injection risk
query_db(f"SELECT * FROM users WHERE username = '{username}'")
```

### Passwords: always hash

```python
from werkzeug.security import generate_password_hash, check_password_hash

password_hash = generate_password_hash(password)
# later, on login:
if check_password_hash(stored_hash, password):
    ...
```

### Auth: both guards on every protected route

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

`@login_required` stops unauthenticated requests. The `WHERE user_id = ?` stops authenticated users from seeing each other's data. You need both.

### Style: PEP 8

- 4-space indentation, never tabs
- `snake_case` for functions and variables, `PascalCase` for classes
- Short docstrings on every route and helper
- Descriptive names (`transactions_list`, not `tl`; `user_id`, not `uid`)
- Imports grouped: stdlib, third-party, local (blank line between groups)
- No `import *`

---

## Project structure

```
finance-tracker-swe5303/
├── app.py              # Flask app, sections split by owner
├── schema.sql          # 4 tables: users, accounts, categories, transactions
├── init_db.py          # builds finance.db from schema.sql
├── requirements.txt
├── templates/          # Jinja HTML
│   ├── base.html       # shared layout, owned by A
│   ├── dashboard.html
│   ├── auth/{login,register}.html      # owned by A
│   ├── accounts/{list,form}.html       # owned by D
│   ├── categories/{list,form}.html     # owned by C
│   └── transactions/{list,form}.html   # owned by B
└── static/
    ├── css/custom.css
    └── js/
```

`app.py` is split into 6 sections:

1. Database helpers (A)
2. Auth (A)
3. Accounts CRUD (D)
4. Categories CRUD (C)
5. Transactions CRUD (B)
6. Dashboard (B)

Edit your own section. If you have to touch outside it, flag in the chat first.

---

## Common errors and fixes

| Error | Likely cause | Fix |
| --- | --- | --- |
| `python: command not found` | Python not on PATH | Reinstall with "Add Python to PATH" ticked, restart terminal |
| `ModuleNotFoundError: No module named 'flask'` | Venv not active, or didn't `pip install` | Activate venv, then `pip install -r requirements.txt` |
| `Address already in use` on port 5000 | Another instance is running | Close the other terminal, or change port in `app.py` to 5001 |
| `OperationalError: no such table` | Forgot to init the DB | `python init_db.py` |
| `jinja2.exceptions.TemplateNotFound` | Wrong template path | Path matches `render_template()`. `'accounts/list.html'` not `'list.html'` |
| `werkzeug.routing.exceptions.BuildError` | `url_for()` with wrong endpoint | Endpoint is the function name, e.g. `'accounts_list'` |
| Form data missing on POST | `name` attribute missing on the `<input>` | Every input needs `name="..."` matching `request.form['...']` |
| Static files (CSS/JS) not loading | Wrong URL | Use `{{ url_for('static', filename='css/custom.css') }}` |
| Database changes not showing up | Forgot `db.commit()` | After any INSERT/UPDATE/DELETE, commit |
| Transaction wrote to wrong user | Didn't filter by user_id | Every model query must `WHERE user_id = ?` |
| `git push` rejected, asks for password | GitHub doesn't accept passwords any more | Use a Personal Access Token (Settings → Developer settings → Tokens classic → tick `repo` scope) |

---

## Where to look for what

- **What is the project?** `README.md`
- **What's my section / who's doing what?** `TEAM_BRIEF.md`
- **What am I building specifically?** `REQUIREMENTS.md`

If you're stuck for more than an hour, post in the team chat with the full error message and what you've already tried. Don't sit on it.
