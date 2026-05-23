"""Finance assistant: turns plain-language questions into safe read-only queries.

A question is read into a small structured intent (locally by default, or with a
model if a key is set). The SQL is then built here with parameters and always
scoped to the logged-in user, so the query layer never runs anything the user
didn't ask for and only ever reads.
"""

import json
import os
import re
import urllib.request
from datetime import date, timedelta
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
        "  categories: category names chosen FROM the user's list above that fit the question (or []).\n"
        "  exclude_categories: category names from the list to leave out (or []).\n"
        "  keywords: words likely to appear in a transaction's description for this topic (or []).\n"
        "  account: an account name from the list above, or null for all accounts.\n"
        "  period: today, yesterday, this_week, last_week, this_month, last_month, "
        "this_year, last_year, last_n_days, or all.\n"
        "  n_days: integer when period is last_n_days, else null.\n\n"
        "Guidance: for vague topics, look at the user's actual categories above and pick "
        "every one that reasonably fits, then add a few description keywords so entries that "
        "sit under a generic category are still caught. For example 'fun stuff' might map to "
        "categories like Entertainment plus keywords such as movie, cinema, game, night out. "
        "Pick accounts the same way, from the user's list. Correct obvious typos. "
        "Use metric balance for 'how much do I have' style questions. "
        "Use breakdown for 'by category'. Default period to all when none is implied, "
        "but use this_month for current-month phrasing. If the question is not about the "
        "user's finances, set supported to false with a brief, friendly message."
    )


def parse_question(question, categories, accounts, today=None):
    """Return a parsed intent. Uses the model if a key is set, otherwise the
    local parser. Falls back to the local parser if the model call fails, so a
    sensible answer is always produced."""
    today = today or date.today()
    if not API_KEY:
        return local_parse(question, categories, accounts, today)
    try:
        return _model_parse(question, categories, accounts, today)
    except Exception:
        return local_parse(question, categories, accounts, today)


def _model_parse(question, categories, accounts, today):
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
        'keywords': intent.get('keywords') or [],
        'account': intent.get('account'),
        'period': intent.get('period') or 'all',
        'n_days': intent.get('n_days'),
    }


# ---------------------------------------------------------------------------
# Local fallback: understands the common questions with no API key at all,
# so the feature works for everyone out of the box. The model (if a key is
# set) only ever improves on this; it is never required.
# ---------------------------------------------------------------------------

TOPICS = {
    'fun': (['entertainment'],
            ['movie', 'cinema', 'game', 'concert', 'party', 'netflix', 'night out']),
    'leisure': (['entertainment'], ['movie', 'cinema', 'game', 'concert']),
    'entertainment': (['entertainment'], ['movie', 'cinema', 'game', 'concert']),
    'essentials': (['rent', 'utilities'], ['rent', 'electric', 'water', 'gas', 'bill']),
    'essential': (['rent', 'utilities'], ['rent', 'electric', 'water', 'gas', 'bill']),
    'necessary': (['rent', 'utilities'], ['rent', 'bill']),
    'necessities': (['rent', 'utilities'], ['rent', 'bill']),
    'bills': (['utilities', 'rent'], ['electric', 'water', 'gas', 'bill']),
    'food': (['food'], ['restaurant', 'grocery', 'groceries', 'lunch', 'dinner', 'coffee', 'takeaway']),
    'groceries': (['food'], ['grocery', 'groceries', 'supermarket']),
    'eating': (['food'], ['restaurant', 'lunch', 'dinner', 'takeaway']),
    'dining': (['food'], ['restaurant', 'lunch', 'dinner']),
    'transport': (['transport'], ['uber', 'taxi', 'bus', 'train', 'fuel', 'petrol']),
    'travel': (['transport'], ['uber', 'taxi', 'bus', 'train', 'flight']),
    'commute': (['transport'], ['bus', 'train', 'fuel', 'petrol']),
}

FINANCE_WORDS = (
    'spend', 'spent', 'spending', 'earn', 'earned', 'income', 'cost', 'paid',
    'pay', 'balance', 'transaction', 'transactions', 'money', 'account',
    'accounts', 'category', 'categories', 'save', 'saving', 'savings',
    'expense', 'expenses', 'received', 'salary', 'much', 'many',
)


def _find_category(word, cat_names):
    """Map a single word to one of the user's category names, allowing typos."""
    word = word.strip().lower()
    if word in cat_names:
        return cat_names[word]
    for low, name in cat_names.items():
        if word in low or low in word:
            return name
    close = get_close_matches(word, list(cat_names.keys()), n=1, cutoff=0.82)
    return cat_names[close[0]] if close else None


def local_parse(question, categories, accounts, today=None):
    """Rule-based parser used when no model key is configured."""
    today = today or date.today()
    q = ' ' + question.lower().strip() + ' '
    signal = False
    cat_names = {c['name'].lower(): c['name'] for c in categories}

    exclude = []
    for m in re.finditer(r'(?:non[- ]|not |excluding |except |without )([a-z]+)', q):
        word = m.group(1)
        match = _find_category(word, cat_names)
        if match and match not in exclude:
            exclude.append(match)
            signal = True

    txn_type = None
    if any(w in q for w in (' earn', 'income', 'received', 'made ', ' paid in')):
        txn_type, signal = 'income', True
    elif any(w in q for w in ('spend', 'spent', 'spending', 'expense', ' cost', ' pay ', ' paid ')):
        txn_type, signal = 'expense', True

    if 'balance' in q or 'how much do i have' in q or 'net worth' in q or 'how much money do i have' in q:
        metric = 'balance'
        signal = True
    elif 'by category' in q or 'per category' in q or 'each category' in q or 'breakdown' in q:
        metric = 'breakdown'
        signal = True
    elif 'which account' in q or 'what account' in q or ('account' in q and 'most' in q):
        metric, signal = 'top_account', True
    elif 'which category' in q or 'what category' in q or 'top category' in q or 'biggest category' in q:
        metric, signal = 'top_category', True
    elif 'how many' in q or 'number of' in q or ' count ' in q:
        metric, signal = 'count', True
    elif 'average' in q or ' avg ' in q or ' mean ' in q:
        metric, signal = 'average', True
    elif 'list ' in q or 'show ' in q or 'recent' in q:
        metric, signal = 'list', True
    else:
        metric = 'sum'

    period, n_days = _local_period(q)

    acct_words = set(re.findall(r'([a-z]+)\s+account', q))

    cats, keywords = [], []
    for low, name in cat_names.items():
        if low in acct_words:
            continue
        if re.search(r'\b' + re.escape(low) + r'\b', q) and name not in exclude:
            cats.append(name)
            signal = True
    for word, (hints, kws) in TOPICS.items():
        if word in q:
            signal = True
            for hint in hints:
                for low, name in cat_names.items():
                    if hint in low and name not in cats:
                        cats.append(name)
            keywords.extend(kws)

    tokens = [t for t in re.findall(r'[a-z]+', q) if len(t) >= 4 and t not in acct_words]
    if not cats:
        for tok in tokens:
            close = get_close_matches(tok, list(cat_names.keys()), n=1, cutoff=0.82)
            if close:
                name = cat_names[close[0]]
                if name not in cats and name not in exclude:
                    cats.append(name)
                    signal = True
    for tok in tokens:
        close = get_close_matches(tok, list(TOPICS.keys()), n=1, cutoff=0.85)
        if close:
            hints, kws = TOPICS[close[0]]
            signal = True
            for hint in hints:
                for low, name in cat_names.items():
                    if hint in low and name not in cats:
                        cats.append(name)
            keywords.extend(kws)

    cats = [c for c in cats if c not in exclude]

    negated = set(re.findall(r'(?:non[- ]|not |excluding |except |without )([a-z]+)', q))
    account = None
    for a in accounts:
        name = a['name'].lower()
        if not re.search(r'\b' + re.escape(name) + r'\b', q):
            continue
        if any(name.startswith(n) or n.startswith(name) for n in negated):
            continue
        if name in cat_names and 'account' not in q:
            continue
        account = a['name']
        signal = True
        break

    if not signal and not any(w in q for w in FINANCE_WORDS):
        return _clean_intent({
            'supported': False,
            'message': "I can help with your spending, income, accounts and "
                       "categories. Try \"How much did I spend last week?\"",
        })

    return _clean_intent({
        'supported': True,
        'metric': metric,
        'txn_type': txn_type,
        'categories': cats,
        'exclude_categories': exclude,
        'keywords': keywords,
        'account': account,
        'period': period,
        'n_days': n_days,
    })


def _local_period(q):
    if 'today' in q:
        return 'today', None
    if 'yesterday' in q:
        return 'yesterday', None
    if 'last week' in q or 'past week' in q:
        return 'last_week', None
    if 'this week' in q:
        return 'this_week', None
    if 'last month' in q or 'past month' in q:
        return 'last_month', None
    if 'this month' in q:
        return 'this_month', None
    if 'last year' in q or 'past year' in q:
        return 'last_year', None
    if 'this year' in q:
        return 'this_year', None
    m = re.search(r'(\d+)\s*(day|week|month)', q)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        return 'last_n_days', n * (7 if unit == 'week' else 30 if unit == 'month' else 1)
    return 'all', None


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
    keywords = [k.strip().lower() for k in intent.get('keywords', []) if k and k.strip()]
    topic = []
    if cat_ids:
        topic.append(f"t.category_id IN ({','.join('?' * len(cat_ids))})")
        params.extend(cat_ids)
    for kw in keywords:
        topic.append('LOWER(t.description) LIKE ?')
        params.append(f'%{kw}%')
    if topic:
        where.append('(' + ' OR '.join(topic) + ')')

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
    if label:
        parts.append(label)
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
