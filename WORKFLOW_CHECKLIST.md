# Workflow Checklist

Use this as your day-to-day reference. Print it if it helps.

---

## Day 1 — Environment setup (every developer)

- [ ] Clone the repo: `git clone https://github.com/YOUR_USERNAME/finance-tracker-swe5303.git`
- [ ] `cd finance-tracker-swe5303`
- [ ] Create the virtual environment: `python -m venv venv`
- [ ] Activate it
  - Windows: `venv\Scripts\activate`
  - macOS / Linux: `source venv/bin/activate`
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Build the database: `python init_db.py`
- [ ] Run the app: `python app.py`
- [ ] Open `http://localhost:5000` (placeholder pages — that's fine)
- [ ] Stop with `Ctrl+C`

---

## Every day — start of work

- [ ] Activate the virtual environment
- [ ] `git pull origin main`
- [ ] `git branch` — check which branch you are on
- [ ] If you don't have a branch yet, create one: `git checkout -b feature/your-feature-name`

---

## While coding

A typical loop:

1. Pick a small piece of work (one route, one form, one query).
2. Edit `app.py` or a template.
3. Run the app: `python app.py`. Click through it in the browser.
4. Stage and commit:
   ```bash
   git add .
   git commit -m "short clear description"
   ```
5. Push: `git push origin feature/your-feature-name`
6. Open a Pull Request on GitHub. Use a title like *"Implement transactions list and query"*. In the description, list:
   - what you added
   - any decisions worth flagging
   - anything you'd like the reviewer to check carefully
7. Person A (or another team member) reviews. Address any change requests, push again, the PR updates automatically.
8. Merge once approved.

---

## Daily standup (about 15 minutes)

Quick update in the team chat:

```
Yesterday: ...
Today: ...
Blockers: ...
```

If you're blocked, say so. Don't sit on it for a day.

---

## Week 1 — foundation

**Person A**

- [ ] Set up the GitHub repo and branch protection
- [ ] Review every PR within 24 hours
- [ ] Run daily standups
- [ ] Implement database helpers and the auth flow (register, login, logout)
- [ ] Verify auth end to end: register → login → session → logout

**Person B**

- [ ] Implement transactions CRUD routes
- [ ] Stub the dashboard route and chart API endpoint
- [ ] Verify add / view / edit / delete transactions

**Person C**

- [ ] Implement categories CRUD routes
- [ ] Verify add / view / edit / delete categories

**Person D**

- [ ] Implement accounts CRUD routes
- [ ] Verify add / view / edit / delete accounts

**By end of week 1**

- [ ] All CRUD modules merged into `main`
- [ ] App runs without errors
- [ ] Each developer can perform their assigned operations

---

## Week 2 — features and SRS begins

- [ ] Continue daily standups
- [ ] Person A keeps reviewing PRs
- [ ] Person B finishes transactions and dashboard, including templates
- [ ] Person C builds category templates
- [ ] Person D builds account templates and starts collecting references for the SRS
- [ ] Everyone writes at least one paragraph of their SRS section this week

**By end of week 2**

- [ ] All feature code merged and working
- [ ] At least one SRS paragraph per person
- [ ] References being collected

---

## Week 3 — SRS and demo prep

- [ ] Code freeze on day 3 — no major changes after that
- [ ] Standups shortened to about 5 minutes
- [ ] Heavy SRS push: complete all sections, four UML diagrams, ~12 screenshots, Gantt chart, risk table
- [ ] Each person writes a 250-word self-reflection
- [ ] Person B seeds demo data (sample user with ~40 transactions)
- [ ] Person C verifies every requirement in `REQUIREMENTS.md` is met and checks word count (2,500 ±10%)
- [ ] Person D compiles 10–15 references in Harvard style and a glossary
- [ ] Run a demo dry run as if presenting

**The day before submission**

- [ ] SRS document assembled with all sections, diagrams and screenshots
- [ ] Code freeze (no more `app.py` changes)
- [ ] Turnitin check (if required)
- [ ] Spelling and grammar pass
- [ ] All team members sign off

**Submission**

- [ ] Upload the SRS (`.docx`) to Moodle
- [ ] Upload the code (zip of repo or GitHub link) if required

---

## Pre-commit checklist

Before every `git push`, confirm:

- [ ] Code follows PEP 8 (4-space indent, `snake_case`, docstrings)
- [ ] All SQL queries use `?` placeholders
- [ ] All passwords are hashed with Werkzeug — never plaintext
- [ ] All routes that touch user data have `@login_required` **and** `WHERE user_id = ?`
- [ ] You ran the app locally and it didn't error
- [ ] Commit message is clear and under 60 characters
- [ ] No `.db` files staged
- [ ] No `__pycache__/`, `.vscode/`, `.idea/` staged
- [ ] No commented-out code left behind

---

## Git troubleshooting

| Problem | Solution |
| --- | --- |
| `fatal: not a git repository` | You are in the wrong folder. `cd finance-tracker-swe5303`. |
| `fatal: Could not read from remote repository` | Wrong URL or no access. `git remote -v` to check. |
| `you need to resolve your current index before you can commit` | Merge conflict. Open the files, fix the `<<<<<<<` markers, then `git add` and commit. |
| `Your branch is behind by N commits` | `git pull origin main`. |
| `refusing to merge unrelated histories` | You probably ran `git init` inside an already-cloned repo. Re-clone fresh. |
| Detached HEAD | `git checkout main` then `git checkout -b feature/your-name`. |

---

## Communication

- **#general** — announcements, general chat
- **#standups** — daily standup posts
- **#dev-help** — code questions and blockers
- **#srs-progress** — SRS writing progress

When stuck, post in `#dev-help` with: what you were trying to do, the exact error, what you've already tried. Ask early.

---

## Reminders

- Test often — don't go four hours without running the app.
- Small wins count. Every working feature is progress.
- Ask questions early. Confusion grows over time.
- Code review is how the team levels up. Be kind, be specific.
