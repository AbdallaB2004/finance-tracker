# FinTrack — SWE5303

Personal finance web app. Built with Flask, SQLite and Bootstrap 5 as the SWE5303 group project (assessment 2).

A logged-in user can register, add their accounts, set income and expense categories, log transactions, and see a dashboard with balance, monthly totals and an expense-by-category chart. No bank integration, no cloud — everything sits in a local SQLite file. We're treating local-only as a feature, not a limitation; there's a longer argument for it in the SRS lit review.

## Quick start

```bash
# 1. virtual environment (first time only)
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# 2. dependencies (first time only)
pip install -r requirements.txt

# 3. database (first time only)
python init_db.py

# 4. run
python app.py
```

Open `http://localhost:5000`. You should see the login page. Register a user, log in, you're on the dashboard.

If anything goes wrong, the troubleshooting table in `DEV_SETUP.md` covers most of it. If your problem isn't there, post in `#dev-help`.

## Where to read what

| Doc | What's in it |
| --- | --- |
| `README.md` | This page — orientation |
| `TEAM_BRIEF.md` | Who's doing what, ground rules, communication, timeline |
| `DEV_SETUP.md` | Step-by-step environment setup and Git workflow |
| `REQUIREMENTS.md` | The 11 functional and 6 non-functional requirements (from the brief) |

Read `TEAM_BRIEF.md` first — it's the shortest and tells you which section is yours. Then `DEV_SETUP.md` when you sit down to code.

## Stack

| What | Why |
| --- | --- |
| Python 3.11+ | Standard language for the module |
| Flask 3 | Smallest web framework, easy to explain in the SRS |
| SQLite | Single file, no server, standard SQL |
| Flask-Login | Session cookies handled for us |
| Werkzeug | Password hashing (ships with Flask) |
| Bootstrap 5 (CDN) | UI looks fine without us having to design anything |
| Chart.js (CDN) | One doughnut chart on the dashboard |

Bootstrap and Chart.js load from a CDN at runtime — nothing to install for the frontend. The only `pip install` is on the Python side.

## Project layout

```
finance-tracker-swe5303/
├── app.py              # Flask app — sections split by owner (A/B/C/D)
├── schema.sql          # 4 tables: users, accounts, categories, transactions
├── init_db.py          # builds finance.db from schema.sql
├── requirements.txt    # pip dependencies
├── templates/          # Jinja HTML
│   ├── base.html       # shared layout + navbar
│   ├── dashboard.html
│   ├── auth/{login,register}.html
│   ├── accounts/       # built by Person D
│   ├── categories/     # built by Person C
│   ├── transactions/   # built by Person B
│   ├── _placeholder.html
│   └── _error.html
└── static/
    ├── css/custom.css
    └── js/             # add charts.js etc. as needed
```

## House rules

A few non-negotiables. Everything else is style.

- **Parameterised SQL.** Always `?` placeholders, never f-strings on user input. The auth section in `app.py` shows the pattern.
- **Hashed passwords.** Always `werkzeug.security.generate_password_hash`. Never store the plaintext.
- **Ownership at the data layer.** Every query that touches user data ends with `WHERE user_id = ?` plus the route has `@login_required`. Both, not either-or.
- **No direct pushes to `main`.** Open a PR. Someone else reviews. Then merge.
- **No `.db` files committed.** `.gitignore` already excludes them. If you somehow add one, remove it before pushing.

Read `TEAM_BRIEF.md` for the full list.

## Team

| Letter | Name | Section |
| --- | --- | --- |
| A | Abdalla Bakr (HE26492) | Lead, database helpers, auth |
| B | Cirja Petru (HE25237) | Transactions + dashboard |
| C | Naima Islam (HE30646)| Categories |
| D | _to fill in_ | Accounts |

A/B/C/D is just a tidy way to map people to sections in `app.py`. Fill in C and D's names once we lock them in.
