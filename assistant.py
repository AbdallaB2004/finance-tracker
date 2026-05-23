"""Finance assistant: turns plain-language questions into safe read-only queries.

The model only ever decides *what* to look up (a small JSON intent). The SQL is
built here with parameters and is always scoped to the logged-in user, so the
model never touches the database directly.
"""

import json
import os
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from difflib import get_close_matches


def _load_env():
    path = os.path.join(os.path.dirname(__file__), '.env')
    if not os.path.exists(path):
        return
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, _, value = line.partition('=')
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env()

API_KEY = os.environ.get('AI_API_KEY', '').strip()
API_BASE = os.environ.get('AI_BASE_URL', 'https://api.openai.com/v1').rstrip('/')
MODEL = os.environ.get('AI_MODEL', 'gpt-4o-mini').strip()

METRICS = {
    'sum', 'count', 'average', 'breakdown',
    'top_category', 'top_account', 'balance', 'list',
}

SUGGESTIONS = [
    'How much did I spend last week?',
    'How much did I earn this month?',
    'Show my spending by category this month',
    'What account had the most spending?',
    'How much did I spend on essentials this year?',
]


def is_configured():
    return bool(API_KEY)


# ---------------------------------------------------------------------------
# Step 1: ask the model to read the question into a small structured intent
# ---------------------------------------------------------------------------

def _system_prompt(categories, accounts, today):
    cat_names = ', '.join(c['name'] for c in categories) or 'none yet'
    acc_names = ', '.join(a['name'] for a in accounts) or 'none yet'
    return (
        "You convert a personal-finance question into a small JSON object. "
        "Reply with JSON only, no prose.\n"
        f"Today is {today.isoformat()} (week starts Monday). Currency is GBP.\n"
        f"The user's categories: {cat_names}.\n"
        f"The user's accounts: {acc_names}.\n\n"
        "Fields:\n"
        "  supported: true if the question is about this user's money/transactions, else false.\n"
        "  message: short friendly reply ONLY when supported is false.\n"
        "  metric: one of sum, count, average, breakdown, top_category, top_account, balance, list.\n"
        "  txn_type: \"income\", \"expense\", or null for both.\n"
        "  categories: list of category names from the list above to include (or []).\n"
        "  exclude_categories: list of category names to leave out (or []).\n"
        "  account: an account name from the list above, or null for all accounts.\n"
        "  period: today, yesterday, this_week, last_week, this_month, last_month, "
        "this_year, last_year, last_n_days, or all.\n"
        "  n_days: integer when period is last_n_days, else null.\n\n"
        "Guidance: match vague wording to the closest categories "
        "(e.g. 'fun'/'leisure' -> Entertainment; 'essentials'/'necessary'/'bills' -> Rent, Utilities; "
        "'eating out'/'groceries' -> Food). Correct obvious typos. "
        "Use metric balance for 'how much do I have' style questions. "
        "Use breakdown for 'by category'. Default period to all when none is implied, "
        "but use this_month for current-month phrasing. If the question is not about the "
        "user's finances, set supported to false with a brief, friendly message."
    )


def parse_question(question, categories, accounts, today=None):
    """Call the model and return a parsed intent dict (or an unsupported intent)."""
    today = today or date.today()
    payload = {
        'model': MODEL,
        'temperature': 0,
        'max_tokens': 250,
        'response_format': {'type': 'json_object'},
        'messages': [
            {'role': 'system', 'content': _system_prompt(categories, accounts, today)},
            {'role': 'user', 'content': question.strip()[:500]},
        ],
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        f'{API_BASE}/chat/completions',
        data=data,
        headers={
            'Authorization': f'Bearer {API_KEY}',
            'Content-Type': 'application/json',
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = json.loads(resp.read().decode('utf-8'))

    content = body['choices'][0]['message']['content'].strip()
    if content.startswith('```'):
        content = content.strip('`')
        content = content[content.find('{'):]
    intent = json.loads(content)
    return _clean_intent(intent)


def _clean_intent(intent):
    metric = (intent.get('metric') or 'sum')
    if metric not in METRICS:
        metric = 'sum'
    txn_type = intent.get('txn_type')
    if txn_type not in ('income', 'expense'):
        txn_type = None
    return {
        'supported': bool(intent.get('supported', True)),
        'message': (intent.get('message') or '').strip(),
        'metric': metric,
        'txn_type': txn_type,
        'categories': intent.get('categories') or [],
        'exclude_categories': intent.get('exclude_categories') or [],
        'account': intent.get('account'),
        'period': intent.get('period') or 'all',
        'n_days': intent.get('n_days'),
    }


# ---------------------------------------------------------------------------
# Step 2: turn the intent into a safe, parameterised query
# ---------------------------------------------------------------------------

def _resolve_period(period, n_days, today):
    """Return (date_from, date_to, label) as ISO strings, or (None, None, label)."""
    if period == 'today':
        return today.isoformat(), today.isoformat(), 'today'
    if period == 'yesterday':
        y = today - timedelta(days=1)
        return y.isoformat(), y.isoformat(), 'yesterday'
    if period == 'this_week':
        start = today - timedelta(days=today.weekday())
        return start.isoformat(), today.isoformat(), 'this week'
    if period == 'last_week':
        this_start = today - timedelta(days=today.weekday())
        start = this_start - timedelta(days=7)
        end = this_start - timedelta(days=1)
        return start.isoformat(), end.isoformat(), 'last week'
    if period == 'this_month':
        start = today.replace(day=1)
        return start.isoformat(), today.isoformat(), 'this month'
    if period == 'last_month':
        first = today.replace(day=1)
        end = first - timedelta(days=1)
        start = end.replace(day=1)
        return start.isoformat(), end.isoformat(), 'last month'
    if period == 'this_year':
        start = today.replace(month=1, day=1)
        return start.isoformat(), today.isoformat(), 'this year'
    if period == 'last_year':
        year = today.year - 1
        return f'{year}-01-01', f'{year}-12-31', 'last year'
    if period == 'last_n_days':
        n = n_days if isinstance(n_days, int) and n_days > 0 else 30
        start = today - timedelta(days=n)
        return start.isoformat(), today.isoformat(), f'over the last {n} days'
    return None, None, 'all time'


def _match_categories(names, categories):
    by_name = {c['name'].lower(): c['id'] for c in categories}
    all_names = list(by_name.keys())
    ids, labels = [], []
    for raw in names:
        key = (raw or '').strip().lower()
        if not key:
            continue
        cid = by_name.get(key)
        if cid is None:
            close = get_close_matches(key, all_names, n=1, cutoff=0.6)
            if not close:
                close = [n for n in all_names if key in n or n in key][:1]
            if close:
                cid = by_name[close[0]]
                key = close[0]
        if cid is not None and cid not in ids:
            ids.append(cid)
            labels.append(next(c['name'] for c in categories if c['id'] == cid))
    return ids, labels


def _match_account(name, accounts):
    if not name:
        return None, None
    key = name.strip().lower()
    for a in accounts:
        if a['name'].lower() == key:
            return a['id'], a['name']
    names = [a['name'].lower() for a in accounts]
    close = get_close_matches(key, names, n=1, cutoff=0.6)
    if close:
        a = next(a for a in accounts if a['name'].lower() == close[0])
        return a['id'], a['name']
    return None, None


def build_query(intent, user_id, categories, accounts, today=None):
    """Build (sql, params, plan). Plan carries labels used to phrase the answer."""
    today = today or date.today()
    metric = intent['metric']

    if metric == 'balance':
        sql = (
            "SELECT "
            "(SELECT COALESCE(SUM(starting_balance), 0) FROM accounts WHERE user_id = ?) "
            "+ (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE user_id = ? AND type = 'income') "
            "- (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE user_id = ? AND type = 'expense') "
            "AS total"
        )
        return sql, (user_id, user_id, user_id), {'shape': 'balance'}

    where = ['t.user_id = ?']
    params = [user_id]

    if intent['txn_type']:
        where.append('t.type = ?')
        params.append(intent['txn_type'])

    date_from, date_to, period_label = _resolve_period(
        intent['period'], intent.get('n_days'), today)
    if date_from:
        where.append('t.date >= ?')
        params.append(date_from)
    if date_to:
        where.append('t.date <= ?')
        params.append(date_to)

    cat_ids, cat_labels = _match_categories(intent['categories'], categories)
    if cat_ids:
        where.append(f"t.category_id IN ({','.join('?' * len(cat_ids))})")
        params.extend(cat_ids)

    excl_ids, _ = _match_categories(intent['exclude_categories'], categories)
    if excl_ids:
        where.append(f"t.category_id NOT IN ({','.join('?' * len(excl_ids))})")
        params.extend(excl_ids)

    account_id, account_label = _match_account(intent['account'], accounts)
    if account_id:
        where.append('t.account_id = ?')
        params.append(account_id)

    clause = ' AND '.join(where)
    plan = {
        'shape': metric,
        'period_label': period_label,
        'category_labels': cat_labels,
        'account_label': account_label,
        'txn_type': intent['txn_type'],
    }

    if metric in ('sum', 'count', 'average'):
        sql = (
            "SELECT COALESCE(SUM(t.amount), 0) AS total, "
            "COALESCE(AVG(t.amount), 0) AS average, COUNT(*) AS n "
            f"FROM transactions t WHERE {clause}"
        )
        return sql, tuple(params), plan

    if metric in ('breakdown', 'top_category'):
        limit = ' LIMIT 1' if metric == 'top_category' else ''
        sql = (
            "SELECT c.name AS name, c.color AS color, COALESCE(SUM(t.amount), 0) AS total "
            "FROM transactions t JOIN categories c ON c.id = t.category_id "
            f"WHERE {clause} GROUP BY c.id ORDER BY total DESC{limit}"
        )
        return sql, tuple(params), plan

    if metric == 'top_account':
        sql = (
            "SELECT a.name AS name, COALESCE(SUM(t.amount), 0) AS total "
            "FROM transactions t JOIN accounts a ON a.id = t.account_id "
            f"WHERE {clause} GROUP BY a.id ORDER BY total DESC LIMIT 1"
        )
        return sql, tuple(params), plan

    sql = (
        "SELECT t.date AS date, t.amount AS amount, t.type AS type, t.description AS description, "
        "c.name AS category, a.name AS account "
        "FROM transactions t JOIN categories c ON c.id = t.category_id "
        "JOIN accounts a ON a.id = t.account_id "
        f"WHERE {clause} ORDER BY t.date DESC, t.created_at DESC LIMIT 10"
    )
    return sql, tuple(params), plan


# ---------------------------------------------------------------------------
# Step 3: phrase the result as a friendly, exact answer
# ---------------------------------------------------------------------------

def _money(value):
    return f'£{float(value or 0):,.2f}'


def _filters_text(plan):
    parts = []
    cats = plan.get('category_labels')
    if cats:
        parts.append('on ' + _join(cats))
    if plan.get('account_label'):
        parts.append('in ' + plan['account_label'])
    label = plan.get('period_label')
    if label and label != 'all time':
        parts.append(label if label.startswith(('over', 'this', 'last')) else 'on ' + label)
    elif label == 'all time':
        parts.append('all time')
    return (' ' + ' '.join(parts)) if parts else ''


def _join(items):
    items = list(items)
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f'{items[0]} and {items[1]}'
    return ', '.join(items[:-1]) + f', and {items[-1]}'


def _verb(plan):
    return 'earned' if plan.get('txn_type') == 'income' else 'spent'


def format_answer(rows, plan):
    shape = plan['shape']

    if shape == 'balance':
        total = rows[0]['total'] if rows else 0
        return f'Your total balance across all accounts is {_money(total)}.'

    if shape in ('sum', 'count', 'average'):
        row = rows[0] if rows else {'total': 0, 'average': 0, 'n': 0}
        n = row['n']
        if not n:
            return f"I couldn't find any matching transactions{_filters_text(plan)}."
        if shape == 'count':
            return f'You have {n} transaction{"s" if n != 1 else ""}{_filters_text(plan)}.'
        if shape == 'average':
            return (f'Your average transaction{_filters_text(plan)} is '
                    f'{_money(row["average"])}, across {n} of them.')
        return (f'You {_verb(plan)} {_money(row["total"])}{_filters_text(plan)} '
                f'({n} transaction{"s" if n != 1 else ""}).')

    if shape == 'breakdown':
        if not rows:
            return f"I couldn't find any matching transactions{_filters_text(plan)}."
        lines = '\n'.join(f'• {r["name"]}: {_money(r["total"])}' for r in rows)
        return f'Here is the breakdown{_filters_text(plan)}:\n{lines}'

    if shape == 'top_category':
        if not rows:
            return f"I couldn't find any matching transactions{_filters_text(plan)}."
        r = rows[0]
        return f'Your top category{_filters_text(plan)} is {r["name"]} at {_money(r["total"])}.'

    if shape == 'top_account':
        if not rows:
            return f"I couldn't find any matching transactions{_filters_text(plan)}."
        r = rows[0]
        return f'{r["name"]} had the most activity{_filters_text(plan)}, at {_money(r["total"])}.'

    if not rows:
        return f"I couldn't find any matching transactions{_filters_text(plan)}."
    lines = '\n'.join(
        f'• {r["date"]} — {r["category"]} — {_money(r["amount"])}'
        + (f' ({r["description"]})' if r["description"] else '')
        for r in rows
    )
    return f'Here are the latest matching transactions{_filters_text(plan)}:\n{lines}'
