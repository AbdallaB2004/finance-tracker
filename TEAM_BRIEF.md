# Team Brief — FinTrack (SWE5303)

Read this end-to-end before the kick-off call. Ten minutes — means we don't waste time covering basics on the call.

## What we're building

FinTrack — a personal finance web app. A user registers, adds their accounts (Cash, Lloyds Current, Credit Card, etc.), categorises income and expenses (Food, Rent, Salary…), logs transactions, and sees a dashboard with balance, monthly totals and an expenses-by-category chart.

It runs locally on a laptop. No deployment, no hosting, no costs. We screen-share the demo over Teams.

The marker cares more about the **SRS document** than the demo. A working app that lets us write a strong SRS beats a flashy app with no docs every time. Keep that in mind whenever you're tempted to gold-plate something.

## Stack (already set up)

Python 3.11+, Flask, SQLite, Flask-Login, Werkzeug for hashing, Bootstrap 5 and Chart.js from a CDN. You don't install Bootstrap or Chart.js — they load from a CDN at runtime. The only thing you `pip install` is on the Python side.

## Timeline

We have around 2 weeks of dev time before SRS-heavy week. Five mini-sprints — match what the SRS Methodology section commits to:

| Sprint | Days | What ships |
| --- | --- | --- |
| 1 | 1–2 | Environment, schema, register/login/logout (already in skeleton, polish + test) |
| 2 | 3–5 | Accounts and Categories CRUD |
| 3 | 6–8 | Transactions CRUD |
| 4 | 9–11 | Dashboard calculations, doughnut chart, monthly totals |
| 5 | 12–14 | Session timeout polish, UI tidy-up, demo data, screenshots |

After sprint 5, dev work is effectively done. The last block is SRS heavy push, UML diagrams, demo dry-run.

If your section ships early, ask A what to pick up next — don't sit idle. Bonus points for whoever bashes through their list first.

## Who's doing what

Letter labels (A, B, C, D) are just for tidy docs. They map to the section headers in `app.py`.

**Person A — Lead / Scrum Master (Abdalla)**
- GitHub repo, branch protection, PR reviews
- `schema.sql` + database helpers + auth (register, login, logout — already in skeleton, verify and tidy)
- The shared `base.html` template (sets the standard everyone copies)
- SRS sections: Methodology (sprints, why agile), Class diagram, ER diagram
- Backstop for anyone stuck

**Person B — Transactions + Dashboard (Cirja)**
- Transactions CRUD: routes, list and form templates
- Dashboard route calculations (total balance, monthly income, monthly expenses, recent transactions, expense breakdown)
- Chart.js doughnut on the dashboard
- SRS sections: Functional requirements, Use case diagram, Transactions activity diagram
- Seed demo data script for the demo (around 40 transactions across 8 weeks)

**Person C — Categories** (naima)
- Categories CRUD: routes, list and form templates
- Default categories are seeded on registration (already in `app.py`) — C owns the user-facing CRUD
- SRS sections: Non-functional requirements, Edit-accounts activity diagram, Risk assessment table
- Gantt chart (mermaid.live works fine — paste into the SRS as a screenshot)

**Person D — Accounts**
- Accounts CRUD: routes, list and form templates
- Navbar + footer polish, app branding
- SRS sections: Registration activity diagram, Level 1 DFD, References (15–20 Harvard sources, 2 academic journals + 4 academic books minimum), Glossary
- Chase up each person's 250-word self-reflection at the end

## Communication

- **GitHub** — code, PRs, issues
- **Discord (or WhatsApp)** — chat. Link in the kick-off email. Pinned messages: the GitHub repo, the SRS Google Doc.
- **Daily standup in #standups** — three lines. Yesterday / Today / Blockers. Two minutes. Non-negotiable. Also doubles as the evidence we followed Agile, which the SRS Methodology section can point at.

Stuck for more than an hour? Post in #dev-help with what you tried. Don't suffer in silence — we have a short runway and we can't afford lost days.

## What "done" looks like

For each feature:

- Code runs without errors locally
- You've used it manually — added a record, edited it, deleted it, all working
- Every function has a short docstring saying what it does
- PR opened, A has reviewed and approved, merged into `main`

"It works on my machine but I haven't pushed yet" is not done.

## House rules (the boring but important bit)

These are the things the marker will look for and that catch most bugs:

1. **Parameterised SQL.** Always `?` placeholders, never f-strings or `%` on user input. See `app.py` auth section for the pattern.
2. **Hashed passwords.** `werkzeug.security.generate_password_hash` only. Plaintext never gets stored.
3. **Authorisation at both layers.** Every route that touches user data needs `@login_required` **and** the SQL ends with `WHERE user_id = ?`. Both.
4. **Pull `main` before starting a branch.** Stops most merge conflicts before they happen.
5. **Commit messages: lowercase, present tense, under 60 chars.** `add accounts list view` not `Added Accounts List View Functionality`.
6. **No pushing to `main` directly.** Open a PR, A reviews, then merge.
7. **No `.db` files committed.** `.gitignore` excludes them already.

## Git workflow (the short version)

```bash
# always start fresh
git checkout main
git pull

# branch named after your feature
git checkout -b feature/accounts-list

# work, save files
git add .
git commit -m "add accounts list view"
git push -u origin feature/accounts-list

# go to GitHub, "Compare & pull request", assign A as reviewer
```

When A approves, merge through the GitHub UI. Delete the branch.

If your branch gets behind `main`:

```bash
git checkout main
git pull
git checkout your-branch
git merge main
# resolve any conflicts, commit, push
```

`DEV_SETUP.md` has the longer walkthrough with the env-setup, troubleshooting and the "every time you sit down to work" loop.

## How to add a feature (the pattern)

Every CRUD module is the same shape. Read the auth section in `app.py` and copy the pattern:

1. Add the route under your section heading in `app.py`. `@login_required` decorator. Parameterised SQL. Filter by `user_id`.
2. Add the template in `templates/<your-module>/{list,form}.html`. Extend `base.html`. Use Bootstrap classes, don't write CSS.
3. Test it manually — add, edit, delete, error case.
4. Commit. Push. PR. Merged.

If you're stuck on the pattern, ask A — they own the example (auth) and will pair with you for a session.

## Before the kick-off call

Each person:

- Accept the GitHub invite (check email)
- Install Python 3.11+ (python.org — tick "Add Python to PATH" on Windows)
- Install Git (git-scm.com, accept defaults)
- Install VS Code (code.visualstudio.com)
- Read this brief
- Skim `DEV_SETUP.md`

If something doesn't work, flag it in #dev-help **before** the meeting so we debug together rather than burning call time on it.

That's the lot. See everyone on the call.
