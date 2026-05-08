# Requirements

What the team is building. Use this list as the spec when implementing features and when writing the SRS.

## Functional Requirements

| ID | Requirement |
| --- | --- |
| FR-01 | New users shall be able to register with a unique username (min. 3 characters) and a password (min. 8 characters). |
| FR-02 | Users shall be able to log in with their username and password, with a secure session being created on success. |
| FR-03 | Authenticated users shall be able to log out, ending the active session. |
| FR-04 | Users shall be able to create, read, update and delete financial accounts (name, type, starting balance). |
| FR-05 | Users shall be able to create, read, update and delete categories (income or expense). A small default set shall be seeded on registration. |
| FR-06 | Users shall be able to create, read, update and delete transactions (amount, type, date, account, category, description). |
| FR-07 | The dashboard shall display total balance, monthly income, monthly expenses, and an expense breakdown by category. |
| FR-08 | All forms shall be validated on both client and server. |
| FR-09 | Access control: users shall only be able to view or modify their own data. |
| FR-10 | The system shall give users immediate feedback after each action via flash messages. |
| FR-11 | User sessions shall be managed automatically and shall time out for security. |

## Non-functional Requirements

### Security

- All passwords are hashed with PBKDF2 (via Werkzeug) before being stored. Plaintext passwords are never logged or persisted.
- All SQL queries use parameterised binding (`?`) — no string concatenation, no f-strings on user input.
- Sessions are managed by Flask-Login using HTTP-only cookies.
- Every route that reads or writes user data uses `@login_required` **and** filters every database query by `user_id`.
- Login compares against the stored hash; the plaintext password is never reused after the request.

### Usability

- The UI is responsive between mobile (375px) and desktop (1280px+) using the Bootstrap 5 grid.
- All form inputs have visible labels and inline HTML5 validation (`required`, `minlength`, `step`, etc.).
- Destructive actions (deleting an account or transaction) require explicit confirmation via modal or `confirm()`.
- Flash messages clearly distinguish success (green), warning (amber) and error (red), with text and an icon.
- A consistent top navbar provides links to all main sections.

### Performance

- The dashboard renders within 1 second on a modern laptop (4-core CPU, 8 GB RAM).
- Queries for a user with up to 1,000 transactions return within 200 ms.
- The expense breakdown chart renders within 500 ms via Chart.js.

### Reliability

- All write operations (INSERT, UPDATE, DELETE) are wrapped in transactions and committed atomically.
- Foreign keys prevent orphaned rows.
- Errors (missing data, invalid IDs, permission denied) are handled with a redirect plus a flash message rather than a 500 page.

### Maintainability

- `app.py` is split into clearly marked sections per feature, each with a header showing the owner (Person A/B/C/D).
- Every route and helper has a short docstring.
- Names are descriptive (`transaction_list`, not `tl`; `user_id`, not `uid`).
- Code follows PEP 8 — 4-space indents, `snake_case`.

### Portability

- Runs on Python 3.11+, any modern browser (Chrome, Firefox, Safari, Edge), and Flask installed from `pip`.
- The database is a single SQLite file (`finance.db`) that can be moved between machines.
- No platform-specific dependencies beyond the standard library, Flask, Werkzeug and Flask-Login.
- Runs unchanged on Windows, macOS and Linux.
