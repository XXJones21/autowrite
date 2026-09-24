"""Pay parsing and location, title, and pay filters. Pay is only what a posting states."""
import html
import re

BAY_AREA = ['san francisco', 'santa clara', 'san jose', 'sunnyvale', 'mountain view',
            'palo alto', 'menlo park', 'cupertino', 'redwood city', 'san mateo',
            'foster city', 'burlingame', 'south san francisco', 'oakland', 'berkeley',
            'emeryville', 'fremont', 'milpitas', 'los gatos', 'campbell', 'san carlos',
            'bay area', 'sf bay']
NON_US = ['canada', 'toronto', 'vancouver', 'united kingdom', 'uk', 'london', 'europe',
          'eu', 'emea', 'apac', 'india', 'bangalore', 'bengaluru', 'germany', 'berlin',
          'france', 'paris', 'ireland', 'dublin', 'japan', 'tokyo', 'singapore',
          'australia', 'sydney', 'israel', 'tel aviv', 'mexico', 'brazil', 'poland',
          'netherlands', 'amsterdam', 'spain', 'switzerland', 'zurich', 'korea', 'seoul',
          'china', 'taiwan', 'latam', 'argentina', 'colombia', 'sweden', 'denmark']
US_MARKERS = ['us', 'usa', 'u s', 'united states', 'north america', 'americas']

_NUM = r'\$?\s?\d[\d,]*(?:\.\d+)?\s?[kK]?(?:\s?USD)?'
_RANGE = re.compile('(' + _NUM + r')\s*(?:-|\u2013|\u2014|to)\s*(' + _NUM + ')')


def _money(tok):
    has_unit = '$' in tok or 'USD' in tok.upper()
    t = tok.upper().replace('USD', '').replace('$', '').replace(',', '').strip()
    mult = 1000 if t.endswith('K') else 1
    t = t.rstrip('K').strip()
    try:
        return float(t) * mult, has_unit
    except ValueError:
        return None, has_unit


def parse_pay(text):
    """Return (min, max) annual base across every stated USD range, or None."""
    text = html.unescape(text or '').replace('\xa0', ' ')
    best = None
    for a, b in _RANGE.findall(text):
        lo, unit_a = _money(a)
        hi, unit_b = _money(b)
        if lo is None or hi is None or not (unit_a or unit_b):
            continue
        if lo < 20000 or hi > 2000000 or lo > hi:
            continue
        best = (lo, hi) if best is None else (min(best[0], lo), max(best[1], hi))
    if best is None:
        return None
    return int(best[0]), int(best[1])


def _norm(s):
    s = (s or '').lower()
    s = re.sub(r'[\-_,/|().:;]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def _has(text, words):
    return any(re.search(r'(?<![a-z])' + re.escape(w) + r'(?![a-z])', text) for w in words)


def location_ok(locations, remote, keep):
    if not keep:
        return True
    text = ' | '.join(_norm(x) for x in locations if x)
    if 'bay-area' in keep and _has(text, BAY_AREA):
        return True
    if 'us-remote' in keep and (remote or _has(text, ['remote'])):
        if _has(text, US_MARKERS) or not _has(text, NON_US):
            return True
    return False


def title_ok(title, include, exclude, qualify=None):
    """Include/exclude are lowercase substrings. A title matched only by a qualify term
    (for example "product manager") also needs one of qualify['with'] as a whole word."""
    t = (title or '').lower()
    if any(x.lower() in t for x in exclude or []):
        return False
    if not include:
        return True
    hits = [x.lower() for x in include if x.lower() in t]
    if not hits:
        return False
    terms = [x.lower() for x in (qualify or {}).get('terms') or []]
    if terms and all(h in terms for h in hits):
        return _has(_norm(t), [w.lower() for w in (qualify or {}).get('with') or []])
    return True


def apply_filters(postings, config):
    keep = (config.get('locations') or {}).get('keep') or []
    floor = (config.get('pay') or {}).get('base_floor_usd') or 0
    titles = config.get('titles') or {}
    include, exclude = titles.get('include') or [], titles.get('exclude') or []
    kept, stats = [], {'title': 0, 'location': 0, 'pay': 0}
    for p in postings:
        if not title_ok(p.get('title'), include, exclude, titles.get('qualify')):
            stats['title'] += 1
        elif not location_ok(p.get('locations') or [], p.get('remote'), keep):
            stats['location'] += 1
        elif p.get('pay_max') is not None and p['pay_max'] < floor:
            stats['pay'] += 1
        else:
            p['pay_listed'] = p.get('pay_max') is not None
            kept.append(p)
    return kept, stats
