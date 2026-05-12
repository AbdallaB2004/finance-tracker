# Requirements

What FinTrack must do. Use this list as the spec when implementing features and when filling in the Requirement Analysis section of the SRS.

Numbering matches the assignment brief (FR-01 to FR-11). If the brief itself has duplicate numbers or contradictions, use the corrected list below — it's been deduplicated.

## Functional Requirements

| ID | Requirement |
| --- | --- |
| FR-01 | New users shall register with a unique username (min. 3 characters) and a password (min. 8 characters). |
| FR-02 | Users shall log in with their username and password, with a secure session created on success. |
| FR-03 | Authenticated users shall log out, ending the active session. |
| FR-04 | Users shall create, read, update and delete financial accounts (name, type, starting balance). |
| FR-05 | Users shall create, read, update and delete categories (income or expense). A small default set is seeded on registration. |
| FR-06 | Users shall create, read, update and delete transactions (amount, type, date, account, category, description). |
| FR-07 | The dashboard shall display total balance, monthly income, monthly expenses, and an expense breakdown by category. |
| FR-08 | All forms shall be validated on both client-side (HTML5 attributes) and server-side (Python). |
| FR-09 | Access control: users shall only view or modify their own data. |
| FR-10 | The system shall give users immediate feedback after each action via flash messages. |
| FR-11 | User sessions shall be managed automatically and shall time out after 30 minutes of inactivity. |

## Non-functional Requirements

### Security

- All passwords are hashed with PBKDF2 (via Werkzeug) before being stored. Plaintext passwords are never logged or persisted.
- All SQL queries use parameterised binding (`?`) — no string concatenation, no f-strings on user input.
- Sessions are managed by Flask-Login using HTTP-only cookies with `SameSite=Lax`.
- Every route that reads or writes user data uses `@login_required` **and** filters every database query by `user_id`.

### Usability

- The UI is responsive between mobile (375px) and desktop (1280px+) using the Bootstrap 5 grid.
- All form inputs have visible labels and inline HTML5 validation (`required`, `minlength`, `step`, etc.).
- Destructive actions (deleting an account or transaction) require explicit confirmation via `confirm()` on the form.
- Flash messages clearly distinguish success (green), warning (amber) and error (red).
- A consistent top navbar provides links to all main sections.

### Performance

- The dashboard renders within 1 second on a modern laptop.
- Dashboard calculations complete within 300ms for up to 1,000 transactions.
- The expense breakdown chart renders within 500ms via Chart.js.

### Reliability

- All write operations (INSERT, UPDATE, DELETE) are wrapped in transactions and committed atomically.
- Foreign keys (with `PRAGMA foreign_keys = ON`) prevent orphaned rows. Cascading deletes remove dependent transactions when a parent account or category is deleted.
- Errors (missing data, invalid IDs, permission denied) are handled with a redirect plus a flash message rather than a 500 page.

### Maintainability

- `app.py` is split into clearly marked sections per feature, each with a header showing the owner (Person A/B/C/D).
- Every route and helper has a short docstring.
- Names are descriptive (`transactions_list`, not `tl`; `user_id`, not `uid`).
- Code follows PEP 8 — 4-space indents, `snake_case`, imports grouped (stdlib / third-party / local).

### Portability

- Runs on Python 3.11+, any modern browser (Chrome, Firefox, Safari, Edge), and Flask installed via `pip`.
- The database is a single SQLite file (`finance.db`) that can be moved between machines.
- No platform-specific dependencies beyond the standard library, Flask, Werkzeug and Flask-Login.
- Runs unchanged on Windows, macOS and Linux.
