# Job Search Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `job-search` skill to the autowrite plugin that fetches postings from public job boards, filters and judges them against the candidate's factual library, scouts unposted targets, and writes a ranked list the candidate picks from.

**Architecture:** Deterministic Python scripts (standard library only) do fetching, filtering, state, batching, ranking, and re-checking. Two subagent prompts do the judgment: a fit judge per batch of postings and a hidden-market scout. `SKILL.md` orchestrates full, daily, first-run, and hand-off modes. All candidate data lives under `<resume-parent-dir>/search/`.

**Tech Stack:** Python 3.10+ standard library (`urllib`, `json`, `re`, `html`, `unittest`), Claude Code skills and Agent subagents.

**Spec:** `docs/superpowers/specs/2026-09-24-job-search-design.md`

## Global Constraints

- Python standard library only; no third-party packages, no API keys.
- Every script takes `--root <resume-parent-dir>` and reads and writes only under `<root>/search/` (plus `<root>/applications/` for hand-off output and seeding reads).
- Posting IDs: `ashby:<org>:<id>`, `greenhouse:<token>:<id>`, `lever:<handle>:<id>`, `workday:<tenant>:<externalPath>`.
- Pay is only what the posting states; never estimated.
- One bad board never stops a run; it is reported under `boards_not_checked`.
- Nothing is sent, submitted, or posted.
- No em-dashes in prompt or doc text.
- Code blocks in this plan are preceded by a `File:` line naming the exact path; create the file with exactly that content.

## File Structure

```
skills/job-search/
  SKILL.md                         # orchestration: first run, full run, daily run, hand-off, scheduling
  references/
    fit-judge-prompt.md            # subagent prompt: judge one batch against the library
    scout-prompt.md                # subagent prompt: hidden-market companies and cases
  scripts/
    yaml_lite.py                   # minimal YAML subset load/dump
    state.py                       # paths, JSON io, seen.json operations
    filters.py                     # pay parsing, location/title/pay filters
    boards.py                      # HTTP client, per-board normalizers, fetch_board
    companies.py                   # config/companies yaml io, board detection, merge
    init_search.py                 # CLI: first run (config + seeded companies)
    fetch_boards.py                # CLI: fetch, filter, update seen, write postings.json
    make_batches.py                # CLI: split unjudged postings into judge batches
    rank.py                        # CLI: merge verdicts, rank, write ranked.md/json
    recheck.py                     # CLI: re-fetch picked rows, write job-posting.md
    merge_scout.py                 # CLI: add scout companies to companies.yaml
    tests/
      fixtures/                    # trimmed real board responses
      test_yaml_lite.py
      test_filters.py
      test_boards.py
      test_state_rank.py
      test_fetch_and_batches.py
```

Run all tests from the repo root with:
`python -m unittest discover -s skills/job-search/scripts/tests -v`

---

### Task 1: YAML subset and state helpers

**Files:**
- Create: `skills/job-search/scripts/yaml_lite.py`
- Create: `skills/job-search/scripts/state.py`
- Test: `skills/job-search/scripts/tests/test_yaml_lite.py`

**Interfaces:**
- Produces: `yaml_lite.load(text) -> dict|list`, `yaml_lite.dump(obj: dict) -> str`, `yaml_lite.scalar(s) -> value`.
- Produces: `state.search_dir(root)`, `state.run_dir(root, date)`, `state.read_json(path, default)`, `state.write_json(path, obj)`, `state.load_seen(root) -> dict`, `state.save_seen(root, seen)`, `state.record_postings(seen, postings, date)`, `state.close_missing(seen, prefix, live_ids, date) -> list[str]`, `state.to_judge(seen) -> list[dict]`.

- [ ] **Step 1: Write the failing tests**

File: `skills/job-search/scripts/tests/test_yaml_lite.py`
```python
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml_lite  # noqa: E402


CONFIG = """
# comment line
locations:
  keep: [bay-area, us-remote]   # trailing comment
pay:
  base_floor_usd: 180000
titles:
  include: ["developer relations", "solutions engineer"]
  exclude: []
contract_roles: false
judge_model: opus
note: "has: colon # and hash"
"""

COMPANIES = """
companies:
  - name: Weave
    board: ashby
    board_id: weave-os
  - name: NVIDIA
    board: workday
    host: nvidia.wd5.myworkdayjobs.com
    tenant: nvidia
    site: NVIDIAExternalCareerSite
    search_terms: [developer relations, solutions architect]
    failures: 0
  - name: Acme
    board: none
"""


class YamlLiteTest(unittest.TestCase):
    def test_config(self):
        d = yaml_lite.load(CONFIG)
        self.assertEqual(d['locations']['keep'], ['bay-area', 'us-remote'])
        self.assertEqual(d['pay']['base_floor_usd'], 180000)
        self.assertEqual(d['titles']['include'], ['developer relations', 'solutions engineer'])
        self.assertEqual(d['titles']['exclude'], [])
        self.assertIs(d['contract_roles'], False)
        self.assertEqual(d['judge_model'], 'opus')
        self.assertEqual(d['note'], 'has: colon # and hash')

    def test_companies(self):
        d = yaml_lite.load(COMPANIES)
        cs = d['companies']
        self.assertEqual(len(cs), 3)
        self.assertEqual(cs[0], {'name': 'Weave', 'board': 'ashby', 'board_id': 'weave-os'})
        self.assertEqual(cs[1]['search_terms'], ['developer relations', 'solutions architect'])
        self.assertEqual(cs[1]['failures'], 0)
        self.assertEqual(cs[2]['board'], 'none')

    def test_round_trip(self):
        for text in (CONFIG, COMPANIES):
            d = yaml_lite.load(text)
            self.assertEqual(yaml_lite.load(yaml_lite.dump(d)), d)

    def test_dump_quotes_urls_and_keywords(self):
        out = yaml_lite.dump({'a': 'https://x.y/z', 'b': 'true', 'c': '123', 'd': 'San Francisco'})
        d = yaml_lite.load(out)
        self.assertEqual(d, {'a': 'https://x.y/z', 'b': 'true', 'c': '123', 'd': 'San Francisco'})

    def test_bad_indent_raises(self):
        with self.assertRaises(ValueError):
            yaml_lite.load('a: 1\n    b: 2\n')


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m unittest discover -s skills/job-search/scripts/tests -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'yaml_lite'`

- [ ] **Step 3: Implement**

File: `skills/job-search/scripts/yaml_lite.py`
```python
"""Minimal YAML subset for job-search config files. Standard library only.

Supported: nested mappings with space indentation, block lists of scalars or
of flat mappings, flow lists of scalars ([a, "b"]), scalars (str, int, float,
true/false, null), and # comments. Anything else raises ValueError.
"""
import json
import re

_KEY = re.compile(r'^([A-Za-z0-9_\-]+):(?:\s+(.*))?$')
_PLAIN = re.compile(r'^[A-Za-z0-9_./@+\-][A-Za-z0-9_./@+\- ]*$')
_NUMBER = re.compile(r'^-?\d+(\.\d+)?$')


def _strip_comment(line):
    out, quote = [], None
    for i, ch in enumerate(line):
        if quote:
            out.append(ch)
            if ch == quote and line[i - 1] != '\\':
                quote = None
            continue
        if ch in ('"', "'"):
            quote = ch
        elif ch == '#' and (i == 0 or line[i - 1] in ' \t'):
            break
        out.append(ch)
    return ''.join(out).rstrip()


def _lines(text):
    result = []
    for raw in text.splitlines():
        line = _strip_comment(raw)
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(' '))
        result.append([indent, line.strip()])
    return result


def _split_flow(inner):
    items, buf, quote = [], [], None
    for ch in inner:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
        elif ch in ('"', "'"):
            quote = ch
            buf.append(ch)
        elif ch == ',':
            items.append(''.join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    tail = ''.join(buf).strip()
    if tail:
        items.append(tail)
    return items


def scalar(s):
    s = s.strip()
    if s.startswith('[') and s.endswith(']'):
        return [scalar(x) for x in _split_flow(s[1:-1])]
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return json.loads(s)
    if len(s) >= 2 and s[0] == "'" and s[-1] == "'":
        return s[1:-1].replace("''", "'")
    low = s.lower()
    if low == 'true':
        return True
    if low == 'false':
        return False
    if low in ('null', '~'):
        return None
    if re.fullmatch(r'-?\d+', s):
        return int(s)
    if re.fullmatch(r'-?\d+\.\d+', s):
        return float(s)
    return s


def _is_item(content):
    return content == '-' or content.startswith('- ')


def _parse_block(lines, i, indent):
    if _is_item(lines[i][1]):
        return _parse_list(lines, i, indent)
    return _parse_map(lines, i, indent)


def _parse_map(lines, i, indent):
    obj = {}
    while i < len(lines) and lines[i][0] == indent and not _is_item(lines[i][1]):
        m = _KEY.match(lines[i][1])
        if not m:
            raise ValueError('expected "key: value", got: %r' % lines[i][1])
        key, rest = m.group(1), m.group(2)
        i += 1
        if rest:
            obj[key] = scalar(rest)
        elif i < len(lines) and lines[i][0] > indent:
            obj[key], i = _parse_block(lines, i, lines[i][0])
        elif i < len(lines) and lines[i][0] == indent and _is_item(lines[i][1]):
            obj[key], i = _parse_list(lines, i, indent)
        else:
            obj[key] = None
    if i < len(lines) and lines[i][0] > indent:
        raise ValueError('unexpected indent at: %r' % lines[i][1])
    return obj, i


def _parse_list(lines, i, indent):
    items = []
    while i < len(lines) and lines[i][0] == indent and _is_item(lines[i][1]):
        rest = lines[i][1][1:].strip()
        if not rest:
            i += 1
            if i < len(lines) and lines[i][0] > indent:
                item, i = _parse_block(lines, i, lines[i][0])
            else:
                item = None
        elif _KEY.match(rest):
            lines[i] = [indent + 2, rest]
            item, i = _parse_map(lines, i, indent + 2)
        else:
            item = scalar(rest)
            i += 1
        items.append(item)
    return items, i


def load(text):
    lines = _lines(text)
    if not lines:
        return {}
    obj, i = _parse_block(lines, 0, lines[0][0])
    if i != len(lines):
        raise ValueError('could not parse line: %r' % lines[i][1])
    return obj


def _fmt(v):
    if v is None:
        return 'null'
    if v is True:
        return 'true'
    if v is False:
        return 'false'
    if isinstance(v, (int, float)):
        return repr(v)
    s = str(v)
    if (_PLAIN.match(s) and s == s.strip() and not _NUMBER.match(s)
            and s.lower() not in ('true', 'false', 'null', '~')):
        return s
    return json.dumps(s, ensure_ascii=False)


def _flow(values):
    return '[%s]' % ', '.join(_fmt(x) for x in values)


def dump(obj, indent=0):
    pad = ' ' * indent
    out = []
    for key, val in obj.items():
        if isinstance(val, dict):
            out.append('%s%s:' % (pad, key))
            if val:
                out.append(dump(val, indent + 2))
        elif isinstance(val, list) and all(not isinstance(x, (dict, list)) for x in val):
            out.append('%s%s: %s' % (pad, key, _flow(val)))
        elif isinstance(val, list):
            out.append('%s%s:' % (pad, key))
            for item in val:
                if not isinstance(item, dict) or not item:
                    raise ValueError('block lists must hold non-empty flat mappings')
                for n, (k2, v2) in enumerate(item.items()):
                    prefix = pad + ('  - ' if n == 0 else '    ')
                    if isinstance(v2, dict):
                        raise ValueError('nested mapping inside a list item is not supported')
                    shown = _flow(v2) if isinstance(v2, list) else _fmt(v2)
                    out.append('%s%s: %s' % (prefix, k2, shown))
        else:
            out.append('%s%s: %s' % (pad, key, _fmt(val)))
    return '\n'.join(out)
```

File: `skills/job-search/scripts/state.py`
```python
"""Paths, JSON io, and seen.json operations for job-search."""
import json
import os


def search_dir(root):
    return os.path.join(root, 'search')


def run_dir(root, date):
    return os.path.join(search_dir(root), date)


def read_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def load_seen(root):
    return read_json(os.path.join(search_dir(root), 'seen.json'), {})


def save_seen(root, seen):
    write_json(os.path.join(search_dir(root), 'seen.json'), seen)


def record_postings(seen, postings, date):
    """Add unseen postings as open and unjudged; refresh stored data for known ones."""
    for p in postings:
        rec = seen.get(p['id'])
        if rec is None:
            seen[p['id']] = {'first_seen': date, 'judged': None, 'status': 'open',
                             'closed_on': None, 'verdict': None, 'posting': p}
        else:
            rec['posting'] = p
            if rec['status'] == 'closed':
                rec['status'], rec['closed_on'] = 'open', None


def close_missing(seen, prefix, live_ids, date):
    """Mark open postings under this board prefix that the board no longer lists."""
    closed = []
    for pid, rec in seen.items():
        if pid.startswith(prefix) and rec['status'] == 'open' and pid not in live_ids:
            rec['status'], rec['closed_on'] = 'closed', date
            closed.append(pid)
    return closed


def to_judge(seen):
    return [rec['posting'] for rec in seen.values()
            if rec['status'] == 'open' and rec['judged'] is None]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest discover -s skills/job-search/scripts/tests -v`
Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add skills/job-search/scripts/yaml_lite.py skills/job-search/scripts/state.py skills/job-search/scripts/tests/test_yaml_lite.py
git commit -m "job-search: YAML subset and state helpers"
```

---

### Task 2: Filters

**Files:**
- Create: `skills/job-search/scripts/filters.py`
- Test: `skills/job-search/scripts/tests/test_filters.py`

**Interfaces:**
- Produces: `filters.parse_pay(text) -> (int, int) | None`, `filters.location_ok(locations: list[str], remote: bool, keep: list[str]) -> bool`, `filters.title_ok(title, include, exclude) -> bool`, `filters.apply_filters(postings, config) -> (kept: list, stats: dict)`. `apply_filters` sets `pay_listed` on kept postings. An empty `keep` list disables the location filter.

- [ ] **Step 1: Write the failing tests**

File: `skills/job-search/scripts/tests/test_filters.py`
```python
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from filters import apply_filters, location_ok, parse_pay, title_ok  # noqa: E402

KEEP = ['bay-area', 'us-remote']


def posting(title='Developer Relations Manager', locations=('Santa Clara, CA',), remote=False,
            pay_max=None):
    return {'id': 'x', 'title': title, 'locations': list(locations), 'remote': remote,
            'pay_min': None, 'pay_max': pay_max}


class PayTest(unittest.TestCase):
    def test_workday_levels(self):
        text = ('The base salary range is 184,000 USD - 287,500 USD for Level 4, and '
                '224,000 USD - 356,500 USD for Level 5.')
        self.assertEqual(parse_pay(text), (184000, 356500))

    def test_k_and_en_dash(self):
        self.assertEqual(parse_pay('$150K \u2013 $200K \u2022 0.1% \u2013 0.2%'), (150000, 200000))

    def test_dollar_commas(self):
        self.assertEqual(parse_pay('range is $143,400 - $216,900 annually ... $172,200 - $236,700'),
                         (143400, 236700))

    def test_ignores_hourly_years_and_phones(self):
        self.assertIsNone(parse_pay('$20 - $30 per hour, 2015 - 2019, call 317-385-1198'))

    def test_html_entities(self):
        self.assertEqual(parse_pay('$180,000&nbsp;-&nbsp;$220,000'), (180000, 220000))


class LocationTest(unittest.TestCase):
    def test_bay_area_workday_format(self):
        self.assertTrue(location_ok(['US, CA, Santa Clara'], False, KEEP))
        self.assertTrue(location_ok(['US-CA-Santa-Clara'], False, KEEP))
        self.assertTrue(location_ok(['San Francisco, CA | Seattle, WA'], False, KEEP))

    def test_non_bay_onsite_dropped(self):
        self.assertFalse(location_ok(['New York, NY'], False, KEEP))
        self.assertFalse(location_ok(['Tel Aviv, Israel'], False, KEEP))

    def test_us_remote(self):
        self.assertTrue(location_ok(['Remote - US'], False, KEEP))
        self.assertTrue(location_ok(['Remote'], False, KEEP))
        self.assertTrue(location_ok(['New York, NY'], True, KEEP))

    def test_non_us_remote_dropped(self):
        self.assertFalse(location_ok(['Remote - Canada'], False, KEEP))
        self.assertFalse(location_ok(['London, UK'], True, KEEP))

    def test_bay_only_keep(self):
        self.assertFalse(location_ok(['Remote - US'], False, ['bay-area']))


class TitleTest(unittest.TestCase):
    def test_include_exclude(self):
        self.assertTrue(title_ok('Senior Developer Relations Engineer', ['developer relations'], []))
        self.assertFalse(title_ok('Account Executive', ['developer relations'], []))
        self.assertFalse(title_ok('Developer Relations Intern', ['developer relations'], ['intern']))
        self.assertTrue(title_ok('Anything', [], []))


class ApplyTest(unittest.TestCase):
    CONFIG = {'locations': {'keep': KEEP}, 'pay': {'base_floor_usd': 180000},
              'titles': {'include': ['developer relations'], 'exclude': []}}

    def test_apply(self):
        ps = [posting(),                                       # kept, no pay
              posting(pay_max=170000),                         # pay drop
              posting(pay_max=200000),                         # kept
              posting(locations=['Tel Aviv, Israel']),         # location drop
              posting(title='Account Executive')]              # title drop
        kept, stats = apply_filters(ps, self.CONFIG)
        self.assertEqual(len(kept), 2)
        self.assertEqual(stats, {'title': 1, 'location': 1, 'pay': 1})
        self.assertFalse(kept[0]['pay_listed'])
        self.assertTrue(kept[1]['pay_listed'])

    def test_empty_keep_disables_location_filter(self):
        kept, _ = apply_filters([posting(locations=['Tel Aviv, Israel'])],
                                {'locations': {'keep': []}, 'pay': {}, 'titles': {}})
        self.assertEqual(len(kept), 1)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m unittest discover -s skills/job-search/scripts/tests -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'filters'`

- [ ] **Step 3: Implement**

File: `skills/job-search/scripts/filters.py`
```python
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


def title_ok(title, include, exclude):
    t = (title or '').lower()
    if any(x.lower() in t for x in exclude or []):
        return False
    if not include:
        return True
    return any(x.lower() in t for x in include)


def apply_filters(postings, config):
    keep = (config.get('locations') or {}).get('keep') or []
    floor = (config.get('pay') or {}).get('base_floor_usd') or 0
    titles = config.get('titles') or {}
    include, exclude = titles.get('include') or [], titles.get('exclude') or []
    kept, stats = [], {'title': 0, 'location': 0, 'pay': 0}
    for p in postings:
        if not title_ok(p.get('title'), include, exclude):
            stats['title'] += 1
        elif not location_ok(p.get('locations') or [], p.get('remote'), keep):
            stats['location'] += 1
        elif p.get('pay_max') is not None and p['pay_max'] < floor:
            stats['pay'] += 1
        else:
            p['pay_listed'] = p.get('pay_max') is not None
            kept.append(p)
    return kept, stats
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest discover -s skills/job-search/scripts/tests -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add skills/job-search/scripts/filters.py skills/job-search/scripts/tests/test_filters.py
git commit -m "job-search: pay, location, and title filters"
```

---

### Task 3: Board normalizers and fetch

**Files:**
- Create: `skills/job-search/scripts/boards.py`
- Create: `skills/job-search/scripts/tests/fixtures/` (ashby.json, greenhouse.json, lever.json, workday-list.json, workday-detail-nvidia.json, workday-detail-salesforce.json)
- Test: `skills/job-search/scripts/tests/test_boards.py`

**Interfaces:**
- Consumes: `filters.parse_pay`, `filters.title_ok`, `filters.location_ok`.
- Produces: `boards.Http` with `get_json(url)` and `post_json(url, body)`; `boards.html_to_text(s)`; `boards.normalize_ashby(data, company, org)`, `normalize_greenhouse(data, company, token)`, `normalize_lever(data, company, handle)`, `normalize_workday(detail, company, tenant, external_path)`, each returning posting dicts with keys `id, board, company, title, team, locations, remote, pay_min, pay_max, pay_text, posted_date, url, description_text`; `boards.board_prefix(entry) -> str`; `boards.fetch_board(entry, http, seen_ids: set, config) -> (live_ids: set, postings: list)`.

- [ ] **Step 1: Capture fixtures from the live boards**

Run from the repo root:
```bash
mkdir -p skills/job-search/scripts/tests/fixtures && cd skills/job-search/scripts/tests/fixtures
curl -s "https://api.ashbyhq.com/posting-api/job-board/weave-os?includeCompensation=true" -o ashby-full.json
curl -s "https://boards-api.greenhouse.io/v1/boards/anthropic/jobs?content=true" -o gh-full.json
curl -s "https://api.lever.co/v0/postings/palantir?mode=json" -o lever-full.json
curl -s -X POST "https://nvidia.wd5.myworkdayjobs.com/wday/cxs/nvidia/NVIDIAExternalCareerSite/jobs" -H "Content-Type: application/json" -H "Accept: application/json" -d '{"appliedFacets":{},"limit":20,"offset":0,"searchText":"developer relations"}' -o workday-list.json
curl -s "https://nvidia.wd5.myworkdayjobs.com/wday/cxs/nvidia/NVIDIAExternalCareerSite/job/US-CA-Santa-Clara/Developer-Relations-Manager--Local-AI-Ecosystem_JR2021035" -H "Accept: application/json" -o workday-detail-nvidia.json
curl -s "https://salesforce.wd12.myworkdayjobs.com/wday/cxs/salesforce/External_Career_Site/job/California---San-Francisco/Lead-Technical-Writer_JR360438" -H "Accept: application/json" -o workday-detail-salesforce.json
python -c "
import json
a=json.load(open('ashby-full.json',encoding='utf-8')); a['jobs']=[j for j in a['jobs'] if j['title']=='Founding ML Engineer'][:1]+[j for j in a['jobs'] if j['title']!='Founding ML Engineer'][:1]; json.dump(a,open('ashby.json','w',encoding='utf-8'))
g=json.load(open('gh-full.json',encoding='utf-8')); g['jobs']=g['jobs'][:2]; json.dump(g,open('greenhouse.json','w',encoding='utf-8'))
l=json.load(open('lever-full.json',encoding='utf-8')); json.dump(l[:2],open('lever.json','w',encoding='utf-8'))
w=json.load(open('workday-list.json',encoding='utf-8')); w['jobPostings']=w['jobPostings'][:3]; w.pop('facets',None); json.dump(w,open('workday-list.json','w',encoding='utf-8'))
"
rm ashby-full.json gh-full.json lever-full.json
```
Expected: six JSON files in `fixtures/`. If a posting used in the tests has closed, the tests in Step 2 name the fields to re-check; replace the specific assertions with the values in the fresh fixture.

- [ ] **Step 2: Write the failing tests**

File: `skills/job-search/scripts/tests/test_boards.py`
```python
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import boards  # noqa: E402


def fixture(name):
    with open(os.path.join(HERE, 'fixtures', name), encoding='utf-8') as f:
        return json.load(f)


KEYS = {'id', 'board', 'company', 'title', 'team', 'locations', 'remote', 'pay_min',
        'pay_max', 'pay_text', 'posted_date', 'url', 'description_text'}


class NormalizeTest(unittest.TestCase):
    def check_shape(self, posts, prefix):
        self.assertTrue(posts)
        for p in posts:
            self.assertEqual(set(p), KEYS)
            self.assertTrue(p['id'].startswith(prefix))
            self.assertTrue(p['title'])
            self.assertTrue(p['url'].startswith('https://'))
            self.assertIsInstance(p['locations'], list)

    def test_ashby(self):
        posts = boards.normalize_ashby(fixture('ashby.json'), 'Weave', 'weave-os')
        self.check_shape(posts, 'ashby:weave-os:')
        ml = next(p for p in posts if p['title'] == 'Founding ML Engineer')
        self.assertEqual((ml['pay_min'], ml['pay_max']), (150000, 200000))
        self.assertIn('San Francisco, California, United States', ml['locations'])
        self.assertRegex(ml['posted_date'], r'^\d{4}-\d{2}-\d{2}$')

    def test_greenhouse(self):
        posts = boards.normalize_greenhouse(fixture('greenhouse.json'), 'Anthropic', 'anthropic')
        self.check_shape(posts, 'greenhouse:anthropic:')
        self.assertNotIn('&lt;', posts[0]['description_text'])

    def test_lever(self):
        posts = boards.normalize_lever(fixture('lever.json'), 'Palantir', 'palantir')
        self.check_shape(posts, 'lever:palantir:')
        self.assertRegex(posts[0]['posted_date'], r'^\d{4}-\d{2}-\d{2}$')

    def test_workday_nvidia(self):
        path = '/job/US-CA-Santa-Clara/Developer-Relations-Manager--Local-AI-Ecosystem_JR2021035'
        p = boards.normalize_workday(fixture('workday-detail-nvidia.json'), 'NVIDIA', 'nvidia', path)
        self.check_shape([p], 'workday:nvidia:/job/')
        self.assertEqual(p['title'], 'Developer Relations Manager, Local AI Ecosystem')
        self.assertEqual((p['pay_min'], p['pay_max']), (184000, 356500))

    def test_workday_salesforce(self):
        path = '/job/California---San-Francisco/Lead-Technical-Writer_JR360438'
        p = boards.normalize_workday(fixture('workday-detail-salesforce.json'), 'Salesforce',
                                     'salesforce', path)
        self.assertEqual((p['pay_min'], p['pay_max']), (143400, 236700))


class FakeHttp:
    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def get_json(self, url):
        self.calls.append(('GET', url))
        for key, val in self.routes.items():
            if key in url:
                if isinstance(val, Exception):
                    raise val
                return val
        raise AssertionError('unexpected GET ' + url)

    def post_json(self, url, body):
        self.calls.append(('POST', url, body.get('offset')))
        return self.routes['POST ' + url]


class FetchTest(unittest.TestCase):
    def test_fetch_ashby(self):
        http = FakeHttp({'job-board/weave-os': fixture('ashby.json')})
        entry = {'name': 'Weave', 'board': 'ashby', 'board_id': 'weave-os'}
        live, posts = boards.fetch_board(entry, http, set(), {})
        self.assertEqual(live, {p['id'] for p in posts})
        self.assertEqual(boards.board_prefix(entry), 'ashby:weave-os:')

    def test_fetch_workday_skips_seen_and_caps(self):
        base = 'https://nvidia.wd5.myworkdayjobs.com/wday/cxs/nvidia/NVIDIAExternalCareerSite'
        listing = fixture('workday-list.json')
        detail = fixture('workday-detail-nvidia.json')
        http = FakeHttp({'POST ' + base + '/jobs': listing, base + '/job/': detail})
        entry = {'name': 'NVIDIA', 'board': 'workday', 'host': 'nvidia.wd5.myworkdayjobs.com',
                 'tenant': 'nvidia', 'site': 'NVIDIAExternalCareerSite',
                 'search_terms': ['developer relations']}
        paths = [r['externalPath'] for r in listing['jobPostings']]
        seen = {'workday:nvidia:' + paths[0]}
        live, posts = boards.fetch_board(entry, http, seen,
                                         {'locations': {'keep': []}, 'workday': {'detail_cap': 1}})
        self.assertEqual(live, {'workday:nvidia:' + p for p in paths})
        self.assertEqual(len(posts), 1)
        self.assertNotIn(('GET', base + paths[0]), http.calls)
        self.assertEqual(boards.board_prefix(entry), 'workday:nvidia:')

    def test_unsupported_board(self):
        with self.assertRaises(ValueError):
            boards.fetch_board({'name': 'X', 'board': 'smartrecruiters'}, FakeHttp({}), set(), {})


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 3: Run to verify failure**

Run: `python -m unittest discover -s skills/job-search/scripts/tests -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'boards'`

- [ ] **Step 4: Implement**

File: `skills/job-search/scripts/boards.py`
```python
"""Public job-board clients and normalizers. Every posting becomes one flat dict."""
import datetime
import html
import json
import re
import urllib.request

from filters import location_ok, parse_pay, title_ok

UA = 'autowrite-job-search/0.1'


class Http:
    def __init__(self, timeout=30):
        self.timeout = timeout

    def _open(self, req):
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.loads(r.read().decode('utf-8'))

    def get_json(self, url):
        return self._open(urllib.request.Request(
            url, headers={'User-Agent': UA, 'Accept': 'application/json'}))

    def post_json(self, url, body):
        return self._open(urllib.request.Request(
            url, data=json.dumps(body).encode('utf-8'), method='POST',
            headers={'User-Agent': UA, 'Accept': 'application/json',
                     'Content-Type': 'application/json'}))


def html_to_text(s):
    s = html.unescape(html.unescape(s or ''))
    s = re.sub(r'<(br|/p|/li|/h\d|/div)[^>]*>', '\n', s, flags=re.I)
    s = re.sub(r'<li[^>]*>', '\n- ', s, flags=re.I)
    s = re.sub(r'<[^>]+>', '', s)
    s = re.sub(r'[ \t\xa0]+', ' ', s)
    return re.sub(r'\n\s*\n+', '\n\n', s).strip()


def _posting(**kw):
    base = {'id': '', 'board': '', 'company': '', 'title': '', 'team': '', 'locations': [],
            'remote': False, 'pay_min': None, 'pay_max': None, 'pay_text': '',
            'posted_date': None, 'url': '', 'description_text': ''}
    base.update(kw)
    return base


def _pay_from_text(text):
    pay = parse_pay(text)
    if not pay:
        return None, None, ''
    return pay[0], pay[1], '$%s - $%s' % (format(pay[0], ','), format(pay[1], ','))


def normalize_ashby(data, company, org):
    out = []
    for j in data.get('jobs', []):
        if j.get('isListed') is False:
            continue
        locs = [j.get('location') or '']
        locs += [s.get('location') or '' for s in (j.get('secondaryLocations') or [])]
        addr = (j.get('address') or {}).get('postalAddress') or {}
        joined = ', '.join(x for x in (addr.get('addressLocality'), addr.get('addressRegion'),
                                       addr.get('addressCountry')) if x)
        if joined:
            locs.append(joined)
        desc = j.get('descriptionPlain') or html_to_text(j.get('descriptionHtml'))
        comp = j.get('compensation') or {}
        salary = [c for c in comp.get('summaryComponents') or []
                  if c.get('compensationType') == 'Salary'
                  and c.get('interval') in (None, '1 YEAR')
                  and c.get('currencyCode') in (None, 'USD') and c.get('maxValue')]
        if salary:
            lo, hi = salary[0].get('minValue'), salary[0]['maxValue']
            pay_min, pay_max = (int(lo) if lo else None), int(hi)
            pay_text = (comp.get('scrapeableCompensationSalarySummary')
                        or comp.get('compensationTierSummary') or '')
        else:
            pay_min, pay_max, pay_text = _pay_from_text(desc)
        out.append(_posting(
            id='ashby:%s:%s' % (org, j['id']), board='ashby', company=company,
            title=j.get('title', ''), team=j.get('team') or j.get('department') or '',
            locations=[x for x in locs if x],
            remote=bool(j.get('isRemote')) or j.get('workplaceType') == 'Remote',
            pay_min=pay_min, pay_max=pay_max, pay_text=pay_text,
            posted_date=(j.get('publishedAt') or '')[:10] or None,
            url=j.get('jobUrl', ''), description_text=desc))
    return out


def normalize_greenhouse(data, company, token):
    out = []
    for j in data.get('jobs', []):
        desc = html_to_text(j.get('content'))
        locs = [(j.get('location') or {}).get('name') or '']
        locs += [o.get('location') or o.get('name') or '' for o in (j.get('offices') or [])]
        depts = j.get('departments') or []
        pay_min, pay_max, pay_text = _pay_from_text(desc)
        out.append(_posting(
            id='greenhouse:%s:%s' % (token, j['id']), board='greenhouse', company=company,
            title=j.get('title', ''), team=depts[0].get('name', '') if depts else '',
            locations=[x for x in locs if x],
            remote='remote' in ' '.join(locs).lower(),
            pay_min=pay_min, pay_max=pay_max, pay_text=pay_text,
            posted_date=(j.get('first_published') or j.get('updated_at') or '')[:10] or None,
            url=j.get('absolute_url', ''), description_text=desc))
    return out


def normalize_lever(data, company, handle):
    out = []
    for j in data or []:
        cats = j.get('categories') or {}
        locs = cats.get('allLocations') or [cats.get('location') or '']
        lists = '\n'.join('%s\n%s' % (x.get('text', ''), html_to_text(x.get('content')))
                          for x in j.get('lists') or [])
        desc = '\n\n'.join(x for x in (j.get('descriptionPlain') or '', lists,
                                       j.get('additionalPlain') or '') if x)
        sal = j.get('salaryRange') or {}
        if (sal.get('max') and sal.get('interval') in (None, 'per-year-salary')
                and sal.get('currency') in (None, 'USD')):
            pay_min, pay_max = (int(sal['min']) if sal.get('min') else None), int(sal['max'])
            pay_text = '$%s - $%s' % (format(pay_min or 0, ','), format(pay_max, ','))
        else:
            pay_min, pay_max, pay_text = _pay_from_text(desc)
        created = j.get('createdAt')
        posted = (datetime.datetime.fromtimestamp(int(created) / 1000, datetime.timezone.utc)
                  .strftime('%Y-%m-%d') if created else None)
        out.append(_posting(
            id='lever:%s:%s' % (handle, j['id']), board='lever', company=company,
            title=j.get('text', ''), team=cats.get('team') or '',
            locations=[x for x in locs if x], remote=(j.get('workplaceType') == 'remote'),
            pay_min=pay_min, pay_max=pay_max, pay_text=pay_text,
            posted_date=posted, url=j.get('hostedUrl', ''), description_text=desc))
    return out


def normalize_workday(detail, company, tenant, external_path):
    info = detail.get('jobPostingInfo') or {}
    desc = html_to_text(info.get('jobDescription'))
    locs = [info.get('location') or ''] + list(info.get('additionalLocations') or [])
    pay_min, pay_max, pay_text = _pay_from_text(desc)
    return _posting(
        id='workday:%s:%s' % (tenant, external_path), board='workday', company=company,
        title=info.get('title', ''), locations=[x for x in locs if x],
        remote='remote' in ((info.get('remoteType') or '') + ' ' + ' '.join(locs)).lower(),
        pay_min=pay_min, pay_max=pay_max, pay_text=pay_text,
        posted_date=info.get('startDate'), url=info.get('externalUrl', ''),
        description_text=desc)


def board_prefix(entry):
    if entry['board'] == 'workday':
        return 'workday:%s:' % entry['tenant']
    return '%s:%s:' % (entry['board'], entry['board_id'])


def workday_base(entry):
    return 'https://%s/wday/cxs/%s/%s' % (entry['host'], entry['tenant'], entry['site'])


def _fetch_workday(entry, http, seen_ids, config):
    base = workday_base(entry)
    titles = config.get('titles') or {}
    terms = entry.get('search_terms') or titles.get('include') or ['']
    keep = (config.get('locations') or {}).get('keep') or []
    cap = (config.get('workday') or {}).get('detail_cap', 40)
    items = {}
    for term in terms:
        offset = 0
        while offset < 100:
            page = http.post_json(base + '/jobs', {'appliedFacets': {}, 'limit': 20,
                                                   'offset': offset, 'searchText': term})
            rows = page.get('jobPostings') or []
            for r in rows:
                if r.get('externalPath'):
                    items.setdefault(r['externalPath'], r)
            if len(rows) < 20:
                break
            offset += 20
    tenant = entry['tenant']
    live = {'workday:%s:%s' % (tenant, path) for path in items}
    posts = []
    for path, r in items.items():
        pid = 'workday:%s:%s' % (tenant, path)
        if pid in seen_ids or len(posts) >= cap:
            continue
        if not title_ok(r.get('title'), titles.get('include'), titles.get('exclude')):
            continue
        loc_text = r.get('locationsText') or ''
        if (loc_text and not re.match(r'^\d+ Locations$', loc_text)
                and not location_ok([loc_text], False, keep)):
            continue
        posts.append(normalize_workday(http.get_json(base + path), entry['name'], tenant, path))
    return live, posts


def fetch_board(entry, http, seen_ids, config):
    """Return (live_ids, postings). live_ids covers every listed posting, before filters."""
    board, name = entry.get('board'), entry.get('name')
    if board == 'ashby':
        data = http.get_json('https://api.ashbyhq.com/posting-api/job-board/%s'
                             '?includeCompensation=true' % entry['board_id'])
        posts = normalize_ashby(data, name, entry['board_id'])
    elif board == 'greenhouse':
        data = http.get_json('https://boards-api.greenhouse.io/v1/boards/%s/jobs?content=true'
                             % entry['board_id'])
        posts = normalize_greenhouse(data, name, entry['board_id'])
    elif board == 'lever':
        data = http.get_json('https://api.lever.co/v0/postings/%s?mode=json' % entry['board_id'])
        posts = normalize_lever(data, name, entry['board_id'])
    elif board == 'workday':
        return _fetch_workday(entry, http, seen_ids, config)
    else:
        raise ValueError('unsupported board: %s' % board)
    return {p['id'] for p in posts}, posts
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m unittest discover -s skills/job-search/scripts/tests -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add skills/job-search/scripts/boards.py skills/job-search/scripts/tests/test_boards.py skills/job-search/scripts/tests/fixtures
git commit -m "job-search: board clients and normalizers with real fixtures"
```

---

### Task 4: Companies, first run, and scout merge

**Files:**
- Create: `skills/job-search/scripts/companies.py`
- Create: `skills/job-search/scripts/init_search.py`
- Create: `skills/job-search/scripts/merge_scout.py`
- Test: `skills/job-search/scripts/tests/test_companies.py`

**Interfaces:**
- Consumes: `yaml_lite.load/dump`, `state.search_dir/run_dir/read_json`.
- Produces: `companies.load_yaml(root, name, default)`, `companies.save_yaml(root, name, obj, header='')`, `companies.COMPANIES_HEADER`, `companies.CONFIG_HEADER`, `companies.detect_board(url) -> dict|None`, `companies.merge_companies(existing, new) -> list[str]`, `init_search.DEFAULT_CONFIG`, `init_search.seed_companies(root) -> list[dict]`, `init_search.run(root, locations, pay_floor)`, `merge_scout.run(root, date) -> list[str]`.

- [ ] **Step 1: Write the failing tests**

File: `skills/job-search/scripts/tests/test_companies.py`
```python
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import companies  # noqa: E402
import init_search  # noqa: E402
import merge_scout  # noqa: E402
from state import write_json  # noqa: E402


class DetectTest(unittest.TestCase):
    def test_patterns(self):
        self.assertEqual(companies.detect_board(
            'https://jobs.ashbyhq.com/weave-os/e8e1010b-ff04'), {'board': 'ashby', 'board_id': 'weave-os'})
        self.assertEqual(companies.detect_board(
            'https://job-boards.greenhouse.io/anthropic/jobs/5421031008'),
            {'board': 'greenhouse', 'board_id': 'anthropic'})
        self.assertEqual(companies.detect_board('https://jobs.lever.co/palantir/6ed7'),
                         {'board': 'lever', 'board_id': 'palantir'})
        self.assertEqual(companies.detect_board(
            'https://salesforce.wd12.myworkdayjobs.com/en-US/External_Career_Site/job/x'),
            {'board': 'workday', 'host': 'salesforce.wd12.myworkdayjobs.com',
             'tenant': 'salesforce', 'site': 'External_Career_Site'})
        self.assertEqual(companies.detect_board(
            'https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite/job/US-CA/x')['site'],
            'NVIDIAExternalCareerSite')
        self.assertIsNone(companies.detect_board(
            'https://nvidia.wd5.myworkdayjobs.com/wday/cxs/nvidia/Site/jobs'))
        self.assertIsNone(companies.detect_board('https://example.com/careers'))


class MergeTest(unittest.TestCase):
    def test_merge(self):
        existing = [{'name': 'Weave', 'board': 'ashby', 'board_id': 'weave-os'},
                    {'name': 'Acme', 'board': 'none'}]
        added = companies.merge_companies(existing, [
            {'name': 'Weave Inc', 'board': 'ashby', 'board_id': 'WEAVE-OS'},   # duplicate board
            {'name': 'acme', 'board': 'greenhouse', 'board_id': 'acme'},      # upgrades Acme
            {'name': 'Acme', 'board': 'none'},                                # duplicate name
            {'name': 'New Co', 'board': 'lever', 'board_id': 'newco'}])
        self.assertEqual(added, ['acme', 'New Co'])
        self.assertEqual(existing[1], {'name': 'Acme', 'board': 'greenhouse', 'board_id': 'acme'})
        self.assertEqual(len(existing), 3)


class InitTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        app = os.path.join(self.root, 'applications', 'weave')
        os.makedirs(app)
        with open(os.path.join(app, 'company-facts.md'), 'w', encoding='utf-8') as f:
            f.write('Role: https://jobs.ashbyhq.com/weave-os/e8e1010b-ff04 posted.\n')
        prof = os.path.join(self.root, 'profiles')
        os.makedirs(prof)
        with open(os.path.join(prof, 'acme.md'), 'w', encoding='utf-8') as f:
            f.write('---\nname: acme\ncompany: Acme Robotics\n---\n# Acme\n')

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_first_run(self):
        init_search.run(self.root, ['bay-area', 'us-remote'], 180000)
        cfg = companies.load_yaml(self.root, 'config.yaml', None)
        self.assertEqual(cfg['locations']['keep'], ['bay-area', 'us-remote'])
        self.assertEqual(cfg['pay']['base_floor_usd'], 180000)
        cs = companies.load_yaml(self.root, 'companies.yaml', {})['companies']
        self.assertIn({'name': 'Weave', 'board': 'ashby', 'board_id': 'weave-os'}, cs)
        self.assertIn({'name': 'Acme Robotics', 'board': 'none'}, cs)
        init_search.run(self.root, [], 0)   # second run keeps config
        cfg2 = companies.load_yaml(self.root, 'config.yaml', None)
        self.assertEqual(cfg2['pay']['base_floor_usd'], 180000)

    def test_merge_scout(self):
        init_search.run(self.root, [], 0)
        write_json(os.path.join(self.root, 'search', '2026-09-24', 'scout.json'), {
            'companies': [{'name': 'Newco', 'board_url': 'https://jobs.lever.co/newco/abc',
                           'signal': 'Series A', 'source_url': 'https://x'},
                          {'name': 'Quietco', 'board_url': '', 'signal': 'launch',
                           'source_url': 'https://y'}],
            'cases': []})
        added = merge_scout.run(self.root, '2026-09-24')
        self.assertEqual(added, ['Newco', 'Quietco'])
        cs = companies.load_yaml(self.root, 'companies.yaml', {})['companies']
        newco = next(c for c in cs if c['name'] == 'Newco')
        self.assertEqual((newco['board'], newco['board_id'], newco['hidden']), ('lever', 'newco', True))


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m unittest discover -s skills/job-search/scripts/tests -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'companies'`

- [ ] **Step 3: Implement**

File: `skills/job-search/scripts/companies.py`
```python
"""Config and company-list io, board detection from URLs, and list merging."""
import os
import re

import yaml_lite
from state import search_dir

CONFIG_HEADER = ('# job-search configuration. Edit freely; the scripts reread it every run.\n'
                 '# locations.keep: bay-area, us-remote (empty list keeps every location).\n')
COMPANIES_HEADER = ('# job-search company list. board: ashby | greenhouse | lever | workday | none.\n'
                    '# Set disabled: true to skip a company. Workday entries take search_terms.\n')

_PATTERNS = [
    (re.compile(r'(?:jobs|api)\.ashbyhq\.com/(?:posting-api/job-board/)?([A-Za-z0-9._\-]+)'),
     'ashby'),
    (re.compile(r'(?:job-)?boards(?:-api)?\.greenhouse\.io/(?:v1/boards/)?([A-Za-z0-9_\-]+)'),
     'greenhouse'),
    (re.compile(r'jobs\.lever\.co/([A-Za-z0-9_\-]+)'), 'lever'),
    (re.compile(r'([a-z0-9\-]+)\.(wd\d+)\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?'
                r'([A-Za-z0-9_\-]+)'), 'workday'),
]


def _path(root, name):
    return os.path.join(search_dir(root), name)


def load_yaml(root, name, default):
    p = _path(root, name)
    if not os.path.exists(p):
        return default
    with open(p, encoding='utf-8') as f:
        return yaml_lite.load(f.read()) or default


def save_yaml(root, name, obj, header=''):
    p = _path(root, name)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        f.write(header + yaml_lite.dump(obj) + '\n')


def detect_board(url):
    for rx, board in _PATTERNS:
        m = rx.search(url or '')
        if not m:
            continue
        if board == 'workday':
            tenant, wd, site = m.groups()
            if site in ('wday', 'job'):
                return None
            return {'board': 'workday', 'host': '%s.%s.myworkdayjobs.com' % (tenant, wd),
                    'tenant': tenant, 'site': site}
        if m.group(1) in ('embed', 'v1'):
            return None
        return {'board': board, 'board_id': m.group(1)}
    return None


def _key(c):
    board = c.get('board')
    if board == 'workday':
        return ('workday', (c.get('tenant') or '').lower())
    if board in ('ashby', 'greenhouse', 'lever'):
        return (board, (c.get('board_id') or '').lower())
    return ('none', (c.get('name') or '').lower())


def merge_companies(existing, new):
    """Append companies not already present. A board-less entry is upgraded in place
    when a new entry with the same name has a board. Returns the names added or upgraded."""
    keys = {_key(c) for c in existing}
    added = []
    for c in new:
        k = _key(c)
        if k in keys:
            continue
        name = (c.get('name') or '').lower()
        same_name = [e for e in existing if (e.get('name') or '').lower() == name]
        if k[0] == 'none' and same_name:
            continue
        boardless = next((e for e in same_name if e.get('board') in (None, 'none')), None)
        if boardless is not None:
            boardless.update({k2: v for k2, v in c.items() if k2 != 'name'})
        else:
            existing.append(c)
        keys.add(k)
        added.append(c.get('name'))
    return added
```

File: `skills/job-search/scripts/init_search.py`
```python
"""First run: write search/config.yaml (if absent) and seed search/companies.yaml."""
import argparse
import copy
import os
import re

from companies import (COMPANIES_HEADER, CONFIG_HEADER, detect_board, load_yaml,
                       merge_companies, save_yaml)
from state import search_dir

DEFAULT_CONFIG = {
    'locations': {'keep': []},
    'pay': {'base_floor_usd': 0},
    'titles': {'include': [], 'exclude': []},
    'role_families': {'core': [], 'adjacent': [], 'downweight': []},
    'contract_roles': False,
    'daily': {'max_judge_batches': 5},
    'workday': {'detail_cap': 40},
    'judge_model': 'opus',
}

URL_RX = re.compile(r'https?://[^\s)\]>"\'`|,]+')


def _title(slug):
    return ' '.join(w.capitalize() for w in re.split(r'[-_ ]+', slug) if w)


def _profile_company(path):
    with open(path, encoding='utf-8', errors='ignore') as f:
        head = f.read(2000)
    m = re.search(r'^company:\s*(.+)$', head, re.M)
    return m.group(1).strip().strip('"') if m else None


def seed_companies(root):
    """Company-folder names win over names derived from board IDs in root-level trackers."""
    found, loose = [], []
    apps = os.path.join(root, 'applications')
    for dirpath, _dirs, files in os.walk(apps):
        rel = os.path.relpath(dirpath, apps)
        company_dir = '' if rel == '.' else rel.split(os.sep)[0]
        for fn in files:
            if not fn.endswith(('.md', '.json', '.csv')):
                continue
            try:
                with open(os.path.join(dirpath, fn), encoding='utf-8', errors='ignore') as f:
                    text = f.read()
            except OSError:
                continue
            for url in URL_RX.findall(text):
                board = detect_board(url)
                if board:
                    name = company_dir or board.get('board_id') or board.get('tenant')
                    (found if company_dir else loose).append(dict({'name': _title(name)}, **board))
    found += loose
    prof = os.path.join(root, 'profiles')
    if os.path.isdir(prof):
        for fn in sorted(os.listdir(prof)):
            if fn.endswith('.md'):
                name = _profile_company(os.path.join(prof, fn)) or _title(fn[:-3])
                found.append({'name': name, 'board': 'none'})
    return found


def run(root, locations, pay_floor):
    cfg_path = os.path.join(search_dir(root), 'config.yaml')
    if os.path.exists(cfg_path):
        print('config.yaml exists; left unchanged')
    else:
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg['locations']['keep'] = list(locations)
        cfg['pay']['base_floor_usd'] = int(pay_floor)
        save_yaml(root, 'config.yaml', cfg, header=CONFIG_HEADER)
        print('wrote', cfg_path)
    data = load_yaml(root, 'companies.yaml', {'companies': []})
    companies = data.get('companies') or []
    added = merge_companies(companies, seed_companies(root))
    save_yaml(root, 'companies.yaml', {'companies': companies}, header=COMPANIES_HEADER)
    boarded = sum(1 for c in companies if c.get('board') not in (None, 'none'))
    print('companies: %d total, %d with a board, %d added this run'
          % (len(companies), boarded, len(added)))
    return companies


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', required=True, help='directory holding the resume, bullets/, profiles/')
    ap.add_argument('--locations', nargs='*', default=[], help='bay-area and/or us-remote')
    ap.add_argument('--pay-floor', type=int, default=0, help='minimum posted max base, USD')
    a = ap.parse_args(argv)
    run(a.root, a.locations, a.pay_floor)


if __name__ == '__main__':
    main()
```

File: `skills/job-search/scripts/merge_scout.py`
```python
"""Add the scout's companies from search/<date>/scout.json to search/companies.yaml."""
import argparse
import datetime
import os

from companies import COMPANIES_HEADER, detect_board, load_yaml, merge_companies, save_yaml
from state import read_json, run_dir


def run(root, date):
    scout = read_json(os.path.join(run_dir(root, date), 'scout.json'), None)
    if not scout:
        print('no scout.json for', date)
        return []
    new = []
    for c in scout.get('companies') or []:
        entry = {'name': c['name'], 'board': 'none'}
        board = detect_board(c.get('board_url') or '')
        if board:
            entry.update(board)
        entry['hidden'] = True
        new.append(entry)
    data = load_yaml(root, 'companies.yaml', {'companies': []})
    companies = data.get('companies') or []
    added = merge_companies(companies, new)
    save_yaml(root, 'companies.yaml', {'companies': companies}, header=COMPANIES_HEADER)
    print('scout companies added:', ', '.join(added) if added else 'none')
    return added


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', required=True)
    ap.add_argument('--date', default=datetime.date.today().isoformat())
    a = ap.parse_args(argv)
    run(a.root, a.date)


if __name__ == '__main__':
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest discover -s skills/job-search/scripts/tests -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add skills/job-search/scripts/companies.py skills/job-search/scripts/init_search.py skills/job-search/scripts/merge_scout.py skills/job-search/scripts/tests/test_companies.py
git commit -m "job-search: company list, board detection, first run, scout merge"
```

---

### Task 5: Fetch run and judge batches

**Files:**
- Create: `skills/job-search/scripts/fetch_boards.py`
- Create: `skills/job-search/scripts/make_batches.py`
- Test: `skills/job-search/scripts/tests/test_fetch_and_batches.py`

**Interfaces:**
- Consumes: `boards.fetch_board`, `boards.board_prefix`, `boards.Http`, `filters.apply_filters`, `companies.load_yaml/save_yaml/COMPANIES_HEADER`, `state.*`.
- Produces: `fetch_boards.run(root, date, daily, http) -> dict` writing `search/<date>/postings.json` with keys `date, mode, postings, boards_not_checked, flagged_companies, filtered_out, closed`; `make_batches.run(root, date, batch_size=10, max_batches=None, stamp=None) -> (names, deferred)` writing `search/<date>/batches/<name>.json` (`{batch, postings:[{id, company, title, locations, remote, pay_text, url, description_text}]}`) and `batches/index.json` (`{batches, deferred}`).

- [ ] **Step 1: Write the failing tests**

File: `skills/job-search/scripts/tests/test_fetch_and_batches.py`
```python
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import fetch_boards  # noqa: E402
import make_batches  # noqa: E402
from companies import load_yaml, save_yaml  # noqa: E402
from state import load_seen, read_json  # noqa: E402


def fixture(name):
    with open(os.path.join(HERE, 'fixtures', name), encoding='utf-8') as f:
        return json.load(f)


class FakeHttp:
    def __init__(self, ashby):
        self.ashby = ashby

    def get_json(self, url):
        if 'weave-os' in url:
            return self.ashby
        raise TimeoutError('board timed out')

    def post_json(self, url, body):
        raise TimeoutError('board timed out')


class RunTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        save_yaml(self.root, 'config.yaml', {
            'locations': {'keep': ['bay-area', 'us-remote']}, 'pay': {'base_floor_usd': 0},
            'titles': {'include': [], 'exclude': []}, 'daily': {'max_judge_batches': 5}})
        save_yaml(self.root, 'companies.yaml', {'companies': [
            {'name': 'Weave', 'board': 'ashby', 'board_id': 'weave-os'},
            {'name': 'Broken', 'board': 'greenhouse', 'board_id': 'broken', 'failures': 2},
            {'name': 'Skipped', 'board': 'none'}]})
        self.ashby = fixture('ashby.json')

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_full_then_daily(self):
        r = fetch_boards.run(self.root, '2026-09-24', False, FakeHttp(self.ashby))
        self.assertTrue(r['postings'])
        self.assertEqual([b['company'] for b in r['boards_not_checked']], ['Broken'])
        self.assertEqual(r['flagged_companies'], ['Broken'])
        cs = load_yaml(self.root, 'companies.yaml', {})['companies']
        self.assertEqual(cs[1]['failures'], 3)
        self.assertEqual(cs[0]['failures'], 0)
        seen = load_seen(self.root)
        self.assertEqual(len(seen), len(r['postings']))

        # next day: nothing new, one posting vanished
        gone = self.ashby['jobs'][0]['id']
        self.ashby['jobs'] = self.ashby['jobs'][1:]
        r2 = fetch_boards.run(self.root, '2026-09-25', True, FakeHttp(self.ashby))
        self.assertEqual(r2['postings'], [])
        self.assertEqual(r2['closed'], ['ashby:weave-os:' + gone])
        self.assertEqual(load_seen(self.root)['ashby:weave-os:' + gone]['status'], 'closed')

    def test_batches_and_cap(self):
        fetch_boards.run(self.root, '2026-09-24', False, FakeHttp(self.ashby))
        names, deferred = make_batches.run(self.root, '2026-09-24', batch_size=1,
                                           max_batches=1, stamp='t1')
        self.assertEqual(names, ['batch-t1-01'])
        self.assertEqual(len(deferred), len(load_seen(self.root)) - 1)
        b = read_json(os.path.join(self.root, 'search', '2026-09-24', 'batches',
                                   'batch-t1-01.json'), {})
        self.assertEqual(set(b['postings'][0]), {'id', 'company', 'title', 'locations', 'remote',
                                                 'pay_text', 'url', 'description_text'})
        idx = read_json(os.path.join(self.root, 'search', '2026-09-24', 'batches',
                                     'index.json'), {})
        self.assertEqual(idx['batches'], ['batch-t1-01'])


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m unittest discover -s skills/job-search/scripts/tests -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'fetch_boards'`

- [ ] **Step 3: Implement**

File: `skills/job-search/scripts/fetch_boards.py`
```python
"""Fetch every board in search/companies.yaml, filter, update seen.json, write postings.json."""
import argparse
import datetime
import os

from boards import Http, board_prefix, fetch_board
from companies import COMPANIES_HEADER, load_yaml, save_yaml
from filters import apply_filters
from state import (close_missing, load_seen, record_postings, run_dir, save_seen,
                   write_json)


def run(root, date, daily, http):
    config = load_yaml(root, 'config.yaml', None)
    if config is None:
        raise SystemExit('search/config.yaml not found; run init_search.py first')
    data = load_yaml(root, 'companies.yaml', {'companies': []})
    companies = data.get('companies') or []
    seen = load_seen(root)
    out, not_checked, closed = [], [], []
    filtered = {'title': 0, 'location': 0, 'pay': 0}
    for c in companies:
        if c.get('disabled') or c.get('board') in (None, 'none'):
            continue
        try:
            live, posts = fetch_board(c, http, set(seen), config)
        except Exception as e:  # one bad board never stops the run
            c['failures'] = int(c.get('failures') or 0) + 1
            not_checked.append({'company': c.get('name'), 'board': c.get('board'),
                                'error': ('%s: %s' % (type(e).__name__, e))[:200],
                                'failures': c['failures']})
            continue
        c['failures'] = 0
        closed += close_missing(seen, board_prefix(c), live, date)
        kept, stats = apply_filters(posts, config)
        for k, v in stats.items():
            filtered[k] += v
        record_postings(seen, kept, date)
        out += [p for p in kept if not daily or seen[p['id']]['first_seen'] == date]
    result = {'date': date, 'mode': 'daily' if daily else 'full', 'postings': out,
              'boards_not_checked': not_checked,
              'flagged_companies': [c.get('name') for c in companies
                                    if int(c.get('failures') or 0) >= 3],
              'filtered_out': filtered, 'closed': closed}
    write_json(os.path.join(run_dir(root, date), 'postings.json'), result)
    save_yaml(root, 'companies.yaml', {'companies': companies}, header=COMPANIES_HEADER)
    save_seen(root, seen)
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', required=True)
    ap.add_argument('--date', default=datetime.date.today().isoformat())
    ap.add_argument('--daily', action='store_true', help='pass forward only postings new today')
    a = ap.parse_args(argv)
    r = run(a.root, a.date, a.daily, Http())
    print('%s run %s: %d postings passed filters, %d boards not checked, %d closed, '
          'filtered out %s' % (r['mode'], r['date'], len(r['postings']),
                               len(r['boards_not_checked']), len(r['closed']), r['filtered_out']))
    for b in r['boards_not_checked']:
        print('  not checked: %s (%s) %s' % (b['company'], b['board'], b['error']))


if __name__ == '__main__':
    main()
```

File: `skills/job-search/scripts/make_batches.py`
```python
"""Split unjudged open postings into fit-judge batches under search/<date>/batches/."""
import argparse
import datetime
import os

from companies import load_yaml
from state import load_seen, run_dir, to_judge, write_json

FIELDS = ('id', 'company', 'title', 'locations', 'remote', 'pay_text', 'url')


def run(root, date, batch_size=10, max_batches=None, stamp=None):
    stamp = stamp or datetime.datetime.now().strftime('%H%M%S')
    pending = sorted(to_judge(load_seen(root)), key=lambda p: p.get('posted_date') or '',
                     reverse=True)
    batches = [pending[i:i + batch_size] for i in range(0, len(pending), batch_size)]
    deferred = []
    if max_batches is not None and len(batches) > max_batches:
        deferred = [p['id'] for b in batches[max_batches:] for p in b]
        batches = batches[:max_batches]
    bdir = os.path.join(run_dir(root, date), 'batches')
    names = []
    for n, batch in enumerate(batches, 1):
        name = 'batch-%s-%02d' % (stamp, n)
        rows = []
        for p in batch:
            row = {k: p.get(k) for k in FIELDS}
            row['description_text'] = (p.get('description_text') or '')[:8000]
            rows.append(row)
        write_json(os.path.join(bdir, name + '.json'), {'batch': name, 'postings': rows})
        names.append(name)
    write_json(os.path.join(bdir, 'index.json'), {'batches': names, 'deferred': deferred})
    return names, deferred


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', required=True)
    ap.add_argument('--date', default=datetime.date.today().isoformat())
    ap.add_argument('--daily', action='store_true', help='apply daily.max_judge_batches')
    a = ap.parse_args(argv)
    cap = None
    if a.daily:
        cap = ((load_yaml(a.root, 'config.yaml', {}) or {}).get('daily') or {}).get(
            'max_judge_batches', 5)
    names, deferred = run(a.root, a.date, max_batches=cap)
    print('%d batches written, %d postings deferred' % (len(names), len(deferred)))
    for n in names:
        print('  ' + os.path.join(run_dir(a.root, a.date), 'batches', n + '.json'))


if __name__ == '__main__':
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest discover -s skills/job-search/scripts/tests -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add skills/job-search/scripts/fetch_boards.py skills/job-search/scripts/make_batches.py skills/job-search/scripts/tests/test_fetch_and_batches.py
git commit -m "job-search: fetch run with daily delta and judge batching"
```

---

### Task 6: Ranker and hand-off re-check

**Files:**
- Create: `skills/job-search/scripts/rank.py`
- Create: `skills/job-search/scripts/recheck.py`
- Test: `skills/job-search/scripts/tests/test_state_rank.py`

**Interfaces:**
- Consumes: `state.*`, `boards.fetch_board/normalize_workday/workday_base/board_prefix/Http`, `companies.load_yaml`.
- Produces: `rank.merge_verdicts(seen, verdicts, date) -> int`, `rank.build(seen, date) -> list[row]`, `rank.render_md(rows, date, meta, scout, index) -> str`, `rank.run(root, date) -> list[row]`; row keys `rank, id, company, title, locations, pay_text, pay_listed, family, checks_passed, checks_total, gates_failed, gates_unverified, posted_date, first_seen, url, verdict`. `recheck.slug(s)`, `recheck.write_posting(root, posting) -> path`, `recheck.run(root, date, ranks, http) -> list[(rank, status, detail)]`.
- Verdict JSON (written by the fit judge, one file per batch at `batches/<name>.verdicts.json`): `{"verdicts": [{"id", "role_family": "core"|"adjacent"|"downweight", "checks": [{"requirement", "passed", "quote"}], "gates": [{"gate", "status": "passed"|"failed"|"unverified", "note"}], "candidate_questions": [str]}]}`.

- [ ] **Step 1: Write the failing tests**

File: `skills/job-search/scripts/tests/test_state_rank.py`
```python
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import rank  # noqa: E402
import recheck  # noqa: E402
from state import close_missing, record_postings, to_judge, write_json  # noqa: E402


def post(pid, posted='2026-09-20', company='Co', title='Role'):
    return {'id': pid, 'board': 'ashby', 'company': company, 'title': title, 'team': '',
            'locations': ['San Francisco, CA'], 'remote': False, 'pay_min': None,
            'pay_max': None, 'pay_text': '', 'posted_date': posted,
            'url': 'https://jobs.ashbyhq.com/co/' + pid, 'description_text': 'desc'}


def verdict(pid, family='core', passed=3, total=3, failed=(), unverified=(), questions=()):
    checks = [{'requirement': 'r%d' % i, 'passed': i < passed, 'quote': 'q'} for i in range(total)]
    gates = ([{'gate': g, 'status': 'failed', 'note': ''} for g in failed]
             + [{'gate': g, 'status': 'unverified', 'note': ''} for g in unverified])
    return {'id': pid, 'role_family': family, 'checks': checks, 'gates': gates,
            'candidate_questions': list(questions)}


class StateTest(unittest.TestCase):
    def test_record_close_judge(self):
        seen = {}
        record_postings(seen, [post('a'), post('b')], '2026-09-24')
        self.assertEqual({p['id'] for p in to_judge(seen)}, {'a', 'b'})
        self.assertEqual(close_missing(seen, '', {'a'}, '2026-09-25'), ['b'])
        record_postings(seen, [post('b')], '2026-09-26')
        self.assertEqual(seen['b']['status'], 'open')
        self.assertEqual(seen['b']['first_seen'], '2026-09-24')


class RankTest(unittest.TestCase):
    def test_sort_order(self):
        seen = {}
        record_postings(seen, [post('gate', '2026-09-23'), post('adj', '2026-09-22'),
                               post('core-old', '2026-09-01'), post('core-new', '2026-09-21'),
                               post('weak', '2026-09-23'), post('tw', '2026-09-23')],
                        '2026-09-24')
        n = rank.merge_verdicts(seen, [
            verdict('gate', failed=['degree']), verdict('adj', family='adjacent'),
            verdict('core-old'), verdict('core-new'), verdict('weak', passed=1),
            verdict('tw', family='downweight'), verdict('unknown-id')], '2026-09-24')
        self.assertEqual(n, 6)
        rows = rank.build(seen, '2026-09-24')
        self.assertEqual([r['id'] for r in rows],
                         ['core-new', 'core-old', 'adj', 'weak', 'gate', 'tw'])
        self.assertEqual([r['rank'] for r in rows], [1, 2, 3, 4, 5, 6])
        self.assertEqual(rows[4]['gates_failed'], ['degree'])

    def test_render(self):
        seen = {}
        record_postings(seen, [post('a'), post('t')], '2026-09-24')
        rank.merge_verdicts(seen, [verdict('a', unverified=['degree'], questions=['Q1?']),
                                   verdict('t', family='downweight')], '2026-09-24')
        rows = rank.build(seen, '2026-09-24')
        md = rank.render_md(rows, '2026-09-24',
                            {'mode': 'daily', 'filtered_out': {'pay': 2},
                             'boards_not_checked': [{'company': 'X', 'board': 'lever',
                                                     'error': 'TimeoutError'}]},
                            {'cases': [{'company': 'Hidden Co', 'paragraph': 'Case.',
                                        'sources': ['https://src']}]},
                            {'deferred': ['z']})
        for needle in ('## Ranked roles', '## New since yesterday',
                       '## Technical writing (downweighted)', 'unverified: degree',
                       '## Hidden market', 'Hidden Co', 'https://src', '## Questions for you',
                       'Q1?', '## Boards not checked', 'X (lever)', 'not listed',
                       '1 postings deferred'):
            self.assertIn(needle, md)


class RecheckTest(unittest.TestCase):
    def test_write_posting(self):
        root = tempfile.mkdtemp()
        try:
            path = recheck.write_posting(root, post('a', company='Weave Inc.', title='Founding DevRel'))
            self.assertTrue(path.endswith(os.path.join('applications', 'weave-inc',
                                                       'founding-devrel', 'job-posting.md')))
            with open(path, encoding='utf-8') as f:
                text = f.read()
            self.assertIn('https://jobs.ashbyhq.com/co/a', text)
            self.assertIn('desc', text)
            second = recheck.write_posting(root, post('a', company='Weave Inc.',
                                                      title='Founding DevRel'))
            self.assertNotEqual(second, path)
        finally:
            shutil.rmtree(root)

    def test_run_marks_closed(self):
        root = tempfile.mkdtemp()
        try:
            from companies import save_yaml
            from state import load_seen, save_seen
            save_yaml(root, 'companies.yaml', {'companies': [
                {'name': 'Co', 'board': 'ashby', 'board_id': 'co'}]})
            seen = {}
            record_postings(seen, [post('ashby:co:1'), post('ashby:co:2')], '2026-09-24')
            save_seen(root, seen)
            write_json(os.path.join(root, 'search', '2026-09-24', 'ranked.json'), {'rows': [
                {'rank': 1, 'id': 'ashby:co:1', 'company': 'Co'},
                {'rank': 2, 'id': 'ashby:co:2', 'company': 'Co'}]})

            class Http:
                def get_json(self, url):
                    return {'jobs': [{'id': '1', 'title': 'Role', 'jobUrl': 'https://j/1',
                                      'descriptionPlain': 'live desc'}]}
            out = recheck.run(root, '2026-09-24', [1, 2], Http())
            self.assertEqual([o[1] for o in out], ['live', 'closed'])
            self.assertEqual(load_seen(root)['ashby:co:2']['status'], 'closed')
        finally:
            shutil.rmtree(root)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m unittest discover -s skills/job-search/scripts/tests -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'rank'`

- [ ] **Step 3: Implement**

File: `skills/job-search/scripts/rank.py`
```python
"""Merge fit-judge verdicts, rank open roles, and write ranked.md and ranked.json."""
import argparse
import datetime
import os

from state import load_seen, read_json, run_dir, save_seen, write_json

FAMILY_ORDER = {'core': 0, 'adjacent': 1, 'downweight': 2}


def merge_verdicts(seen, verdicts, date):
    n = 0
    for v in verdicts:
        rec = seen.get(v.get('id'))
        if rec is None:
            continue
        rec['verdict'], rec['judged'] = v, date
        n += 1
    return n


def _summary(v):
    checks = v.get('checks') or []
    passed = sum(1 for c in checks if c.get('passed'))
    gates = v.get('gates') or []
    failed = [g.get('gate', '') for g in gates if g.get('status') == 'failed']
    unverified = [g.get('gate', '') for g in gates if g.get('status') == 'unverified']
    return passed, len(checks), failed, unverified


def _sort(recs):
    recs = sorted(recs, key=lambda r: r['posting'].get('posted_date') or '', reverse=True)

    def key(r):
        passed, total, failed, _ = _summary(r['verdict'])
        return (1 if failed else 0, -passed, -(passed / total if total else 0),
                FAMILY_ORDER.get(r['verdict'].get('role_family'), 3))
    return sorted(recs, key=key)


def build(seen, date):
    judged = [r for r in seen.values() if r['status'] == 'open' and r.get('verdict')]
    main = _sort([r for r in judged if r['verdict'].get('role_family') != 'downweight'])
    down = _sort([r for r in judged if r['verdict'].get('role_family') == 'downweight'])
    rows = []
    for n, r in enumerate(main + down, 1):
        p, v = r['posting'], r['verdict']
        passed, total, failed, unverified = _summary(v)
        rows.append({'rank': n, 'id': p['id'], 'company': p['company'], 'title': p['title'],
                     'locations': p.get('locations') or [], 'pay_text': p.get('pay_text') or '',
                     'pay_listed': p.get('pay_max') is not None,
                     'family': v.get('role_family'), 'checks_passed': passed,
                     'checks_total': total, 'gates_failed': failed,
                     'gates_unverified': unverified, 'posted_date': p.get('posted_date'),
                     'first_seen': r['first_seen'], 'url': p.get('url', ''), 'verdict': v})
    return rows


def _cell(s):
    return str(s).replace('|', '/').replace('\n', ' ')


def _gates(row):
    if row['gates_failed']:
        return 'failed: ' + ', '.join(row['gates_failed'])
    if row['gates_unverified']:
        return 'unverified: ' + ', '.join(row['gates_unverified'])
    return 'clear'


def _loc(row):
    locs = row['locations'] or ['']
    return locs[0] + (' (+%d)' % (len(locs) - 1) if len(locs) > 1 else '')


def _table(rows):
    lines = ['| # | Company | Role | Location | Base pay | Family | Checks | Gates | Posted |',
             '|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        lines.append('| %d | %s | [%s](%s) | %s | %s | %s | %d/%d | %s | %s |' % (
            r['rank'], _cell(r['company']), _cell(r['title']), r['url'], _cell(_loc(r)),
            _cell(r['pay_text'] or 'not listed'), r['family'], r['checks_passed'],
            r['checks_total'], _cell(_gates(r)), r['posted_date'] or 'no date'))
    return lines


def render_md(rows, date, meta, scout, index):
    meta = meta or {}
    mode = meta.get('mode', 'full')
    filtered = ', '.join('%s %d' % kv for kv in sorted((meta.get('filtered_out') or {}).items()))
    out = ['# Job search: %s' % date, '',
           '%s run. %d open roles ranked. Filtered out before judging: %s.'
           % (mode.capitalize(), len(rows), filtered or 'none'), '']
    main = [r for r in rows if r['family'] != 'downweight']
    down = [r for r in rows if r['family'] == 'downweight']
    out += ['## Ranked roles', ''] + (_table(main) if main else ['None yet.']) + ['']
    if mode == 'daily':
        new = [r for r in rows if r['first_seen'] == date]
        out += ['## New since yesterday', ''] + (_table(new) if new else ['None.']) + ['']
    if down:
        out += ['## Technical writing (downweighted)', ''] + _table(down) + ['']
    cases = (scout or {}).get('cases') or []
    if cases:
        out += ['## Hidden market', '']
        for c in cases:
            out += ['**%s.** %s' % (c.get('company', ''), c.get('paragraph', '')),
                    'Sources: ' + ', '.join(c.get('sources') or []), '']
    questions = sorted({q for r in rows for q in (r['verdict'].get('candidate_questions') or [])})
    if questions:
        out += ['## Questions for you', ''] + ['- ' + q for q in questions] + ['']
    not_checked = meta.get('boards_not_checked') or []
    if not_checked:
        out += ['## Boards not checked', ''] + ['- %s (%s): %s' % (b['company'], b['board'],
                                                                   b['error'])
                                                for b in not_checked] + ['']
    if meta.get('flagged_companies'):
        out += ['Boards failing 3 or more runs in a row: ' + ', '.join(meta['flagged_companies']),
                '']
    deferred = (index or {}).get('deferred') or []
    if deferred:
        out += ['%d postings deferred to the next run by the daily judge cap.' % len(deferred), '']
    return '\n'.join(out)


def run(root, date):
    seen = load_seen(root)
    rdir = run_dir(root, date)
    bdir = os.path.join(rdir, 'batches')
    verdicts = []
    if os.path.isdir(bdir):
        for fn in sorted(os.listdir(bdir)):
            if fn.endswith('.verdicts.json'):
                verdicts += read_json(os.path.join(bdir, fn), {}).get('verdicts') or []
    merge_verdicts(seen, verdicts, date)
    rows = build(seen, date)
    meta = read_json(os.path.join(rdir, 'postings.json'), {})
    scout = read_json(os.path.join(rdir, 'scout.json'), None)
    index = read_json(os.path.join(bdir, 'index.json'), None)
    write_json(os.path.join(rdir, 'ranked.json'), {'date': date, 'rows': rows})
    with open(os.path.join(rdir, 'ranked.md'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(render_md(rows, date, meta, scout, index) + '\n')
    save_seen(root, seen)
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', required=True)
    ap.add_argument('--date', default=datetime.date.today().isoformat())
    a = ap.parse_args(argv)
    rows = run(a.root, a.date)
    print('%d roles ranked -> %s' % (len(rows), os.path.join(run_dir(a.root, a.date),
                                                             'ranked.md')))


if __name__ == '__main__':
    main()
```

File: `skills/job-search/scripts/recheck.py`
```python
"""Re-fetch picked rows from ranked.json; write job-posting.md for live ones, close the rest."""
import argparse
import datetime
import os
import re
import urllib.error

from boards import Http, board_prefix, fetch_board, normalize_workday, workday_base
from companies import load_yaml
from state import load_seen, read_json, run_dir, save_seen


def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', (s or '').lower()).strip('-')


def write_posting(root, p):
    d = os.path.join(root, 'applications', slug(p['company']), slug(p['title']))
    os.makedirs(d, exist_ok=True)
    today = datetime.date.today().isoformat()
    path = os.path.join(d, 'job-posting.md')
    if os.path.exists(path):
        path = os.path.join(d, 'job-posting-%s.md' % today)
    body = ['# %s, %s' % (p['company'], p['title']), '',
            '- **URL:** %s' % p['url'],
            '- **Location:** %s' % '; '.join(p.get('locations') or []),
            '- **Pay:** %s' % (p.get('pay_text') or 'not listed'),
            '- **Posted:** %s' % (p.get('posted_date') or 'no date'),
            '- **Source:** %s board, re-fetched %s by job-search.' % (p['board'], today),
            '', '---', '', p.get('description_text') or '', '']
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(body))
    return path


def _entry_for(pid, companies):
    return next((c for c in companies if c.get('board') not in (None, 'none')
                 and pid.startswith(board_prefix(c))), None)


def recheck_posting(row, entry, http):
    """Return a fresh posting dict, or None when the role is gone."""
    pid = row['id']
    if pid.startswith('workday:'):
        path = pid.split(':', 2)[2]
        try:
            detail = http.get_json(workday_base(entry) + path)
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                return None
            raise
        info = detail.get('jobPostingInfo') or {}
        if not info or info.get('canApply') is False:
            return None
        return normalize_workday(detail, row['company'], entry['tenant'], path)
    _live, posts = fetch_board(entry, http, set(), {})
    return next((p for p in posts if p['id'] == pid), None)


def run(root, date, ranks, http):
    ranked = read_json(os.path.join(run_dir(root, date), 'ranked.json'), {'rows': []})
    by_rank = {r['rank']: r for r in ranked['rows']}
    companies = (load_yaml(root, 'companies.yaml', {}) or {}).get('companies') or []
    seen = load_seen(root)
    results = []
    for n in ranks:
        row = by_rank.get(n)
        if row is None:
            results.append((n, 'missing', 'no row %d in ranked.json' % n))
            continue
        entry = _entry_for(row['id'], companies)
        if entry is None:
            results.append((n, 'missing', 'no company entry for ' + row['id']))
            continue
        fresh = recheck_posting(row, entry, http)
        if fresh is None:
            if row['id'] in seen:
                seen[row['id']]['status'] = 'closed'
                seen[row['id']]['closed_on'] = datetime.date.today().isoformat()
            results.append((n, 'closed', row['id']))
        else:
            results.append((n, 'live', write_posting(root, fresh)))
    save_seen(root, seen)
    return results


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', required=True)
    ap.add_argument('--date', default=datetime.date.today().isoformat())
    ap.add_argument('--rows', type=int, nargs='+', required=True)
    a = ap.parse_args(argv)
    for n, status, detail in run(a.root, a.date, a.rows, Http()):
        print('#%d %s: %s' % (n, status.upper(), detail))


if __name__ == '__main__':
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest discover -s skills/job-search/scripts/tests -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add skills/job-search/scripts/rank.py skills/job-search/scripts/recheck.py skills/job-search/scripts/tests/test_state_rank.py
git commit -m "job-search: ranker, report, and hand-off re-check"
```

---

### Task 7: Subagent prompts and SKILL.md

**Files:**
- Create: `skills/job-search/references/fit-judge-prompt.md`
- Create: `skills/job-search/references/scout-prompt.md`
- Create: `skills/job-search/SKILL.md`
- Modify: `README.md` (add a job-search section), `.claude-plugin/plugin.json` (version 0.6.0, description mentions job-search)

**Interfaces:**
- Consumes: every script's CLI from Tasks 1 to 6; verdict JSON schema from Task 6; scout JSON read by `merge_scout.py` and `rank.py`: `{"companies": [{"name", "board_url", "signal", "source_url"}], "cases": [{"company", "paragraph", "sources": [url]}]}`.

- [ ] **Step 1: Write the fit-judge prompt**

File: `skills/job-search/references/fit-judge-prompt.md`
````markdown
# Fit judge subagent prompt

Spawn one fit-judge subagent per batch file listed in `search/<date>/batches/index.json`, in parallel, one message with several Agent calls.

- `subagent_type`: `general-purpose` (it writes one file)
- `model`: the `judge_model` value from `search/config.yaml`, the same for every batch in a run, so verdicts stay comparable across days
- `description`: `Judge job batch <batch name>`

`prompt`:

```
You are screening job postings for one candidate. For each posting in the batch, decide which role family it belongs to and check the posting's stated hard requirements against the candidate's factual library. You are not writing a resume or giving advice.

Batch file: [ABSOLUTE PATH TO batches/<name>.json]
Write your result to: [ABSOLUTE PATH TO batches/<name>.verdicts.json]

Candidate's role families (from search/config.yaml):
- core: [CORE LIST]
- adjacent: [ADJACENT LIST]
- downweight: [DOWNWEIGHT LIST]

Candidate's factual library (every file below is a fact the candidate has confirmed; nothing else is a fact):
<<<LIBRARY BEGIN>>>
[EVERY .md FILE FROM bullets/, interview-notes/, narratives/, context/, EACH PREFIXED WITH "--- <relative path> ---"]
<<<LIBRARY END>>>

For each posting:
1. role_family: core, adjacent, or downweight, by what the job does day to day, not by title words alone.
2. checks: 3 to 5 of the posting's stated hard requirements (skills, experience, domain), each with passed true or false and a quote copied verbatim from the library that supports a pass. A pass needs a quote. When no quote supports it, it fails.
3. gates: every stated knockout (degree, minimum years, clearance, work authorization, location or onsite days, certification). status is passed, failed, or unverified. Use unverified whenever the library does not settle it. When the library says the candidate has no degree and the posting requires one without an equivalent-experience clause, the degree gate is failed; with an equivalent-experience clause it is unverified and the note says no degree is on file.
4. candidate_questions: requirements that would pass only with a fact not in the library, phrased as a question to the candidate.

Never add a skill, number, or experience the library does not state. Do not soften a failed check.

Write this JSON to the output path and nothing else:
{"verdicts": [{"id": "<posting id>", "role_family": "core|adjacent|downweight", "checks": [{"requirement": "...", "passed": true, "quote": "..."}], "gates": [{"gate": "...", "status": "passed|failed|unverified", "note": "..."}], "candidate_questions": ["..."]}]}

Every posting in the batch gets exactly one verdict. Then reply with one line: the output path and the count of verdicts written.
```
````

- [ ] **Step 2: Write the scout prompt**

File: `skills/job-search/references/scout-prompt.md`
````markdown
# Hidden-market scout subagent prompt

Spawn one scout subagent per full run.

- `subagent_type`: `general-purpose` (it needs WebSearch and WebFetch, and writes one file)
- `model`: the `judge_model` value from `search/config.yaml`
- `description`: `Scout hidden-market companies`

`prompt`:

```
You are finding companies where this candidate could create value, whether or not they have posted a matching job. Output feeds a founder-outreach flow the candidate reviews; nothing you write is sent.

Candidate edge (their words):
[EDGE STATEMENT FROM outreach/positioning-brief.md, OR THE RESUME SUMMARY IF THAT FILE IS ABSENT]

Candidate evidence (factual library excerpts):
[THE LIBRARY FILES MOST RELEVANT TO THE EDGE, EACH PREFIXED WITH "--- <relative path> ---"]

Already on the company list (skip these): [COMMA-SEPARATED NAMES FROM search/companies.yaml]
Location constraint: [LOCATIONS FROM config.yaml]

Search recent funding announcements, product launches, open-source releases, and hiring posts from the last 6 months for companies whose product sits where the candidate's edge applies. Prefer companies of 10 to 500 people, where a founder or team lead is reachable. Verify each company with at least one source you fetched.

Write JSON to [ABSOLUTE PATH TO search/<date>/scout.json]:
{"companies": [{"name": "...", "board_url": "<careers or job-board URL, or empty>", "signal": "<one line: the funding, launch, or hiring signal>", "source_url": "<URL you fetched that shows the signal>"}],
 "cases": [{"company": "...", "paragraph": "<one paragraph: what they are building, the specific thing they appear to be missing, where that has worked elsewhere, roughly what it would change for them, and the candidate's matching evidence with its result, quoted from the library>", "sources": ["<URL>", "..."]}]}

List 10 to 20 companies. Write cases for the 5 strongest only. Every case cites at least one source you fetched. Drop any case you cannot source, and drop any claim about the candidate that is not in the library. Then reply with one line: the path and the counts.
```
````

- [ ] **Step 3: Write SKILL.md**

File: `skills/job-search/SKILL.md`
````markdown
---
name: job-search
description: "Find and rank job openings and unposted targets for a candidate. Fetches postings from public job boards (Ashby, Greenhouse, Lever, Workday) for a maintained company list, filters by location and pay, judges fit against the candidate's factual library with quoted evidence, scouts hidden-market companies with sourced outreach cases, and writes a ranked list the candidate picks from. Use when: job search, find jobs, find me roles, what should I apply to, daily job check, search openings, hidden market. Hands picks to autowrite for packets."
---

# Job search

Finds openings the candidate has not seen, ranks them against what the candidate has actually done, and stops at a ranked list. The candidate picks; only picks get packets.

Scripts live in this skill's `scripts/` directory. Run them with `python <skill-dir>/scripts/<name>.py --root <resume-parent-dir>`, where `<resume-parent-dir>` is the directory holding the candidate's resume, `bullets/`, and `profiles/`. Every output lands in `<resume-parent-dir>/search/`.

## Modes

Read the invocation: `daily` means the daily run, a list of row numbers ("build 2, 5, 9") means hand-off, anything else is a full run. If `search/config.yaml` is missing, do the first run before anything else.

## First run

1. Ask the candidate, in one `AskUserQuestion` call: which locations to keep (`bay-area`, `us-remote`, or both), and the base-pay floor in USD. Postings with no listed pay are always kept and flagged.
2. Run `init_search.py --root <dir> --locations <...> --pay-floor <n>`. It writes `search/config.yaml` and seeds `search/companies.yaml` from job-board URLs in `applications/` and company names in `profiles/`.
3. Read the resume and library, then propose `role_families` (core, adjacent, downweight) and `titles.include` / `titles.exclude` keyword lists for `config.yaml`. Title keywords are lowercase substrings; include should cover every core and adjacent family, and exclude should drop obvious misses (intern, sales, recruiter, and similar). Show the proposal and the seeded company list, and apply the candidate's corrections. Set `disabled: true` on any company the candidate rules out.
4. For companies seeded with `board: none`, look up their careers page. When it is on Ashby, Greenhouse, Lever, or Workday, fill in the board fields (Workday needs `host`, `tenant`, `site`, and `search_terms`). Otherwise leave `board: none`.
5. Continue with a full run.

## Full run

1. **Scout.** Spawn the scout per `references/scout-prompt.md`. Then run `merge_scout.py --root <dir>`.
2. **Fetch.** Run `fetch_boards.py --root <dir>`. Relay any boards not checked.
3. **Batch.** Run `make_batches.py --root <dir>`.
4. **Judge.** For every batch listed in `search/<date>/batches/index.json`, spawn a fit judge per `references/fit-judge-prompt.md`, all in one message. Load the library once and pass it inline to each. When a judge fails or its verdicts file is missing, re-spawn it once; if it fails again, leave that batch unjudged (its postings stay pending for the next run) and say so.
5. **Rank.** Run `rank.py --root <dir>`.
6. **Report.** In chat: counts (ranked, filtered out, boards not checked, closed), the top 10 rows (rank, company, role, pay, checks, gates), the hidden-market company names, and the path to `ranked.md`. Then stop and let the candidate pick.

## Daily run

Run `fetch_boards.py --root <dir> --daily`, then `make_batches.py --root <dir> --daily`, judge the listed batches as in the full run, then `rank.py --root <dir>`. No scout. The report's "New since yesterday" section lists the new rows. Keep the chat summary to counts and the new rows.

## Hand-off

1. Run `recheck.py --root <dir> --rows <n ...>` with the candidate's picks. It re-fetches each posting, writes `applications/<company>/<role>/job-posting.md` for live ones, and closes the rest. Tell the candidate which picks closed.
2. For each live pick, hand the posting to autowrite's secondary loop (Step 6b onward) with the saved `job-posting.md` as the JD source, so autowrite skips discovery.
3. For a hidden-market pick, hand its case paragraph and sources to the outreach flow (the high-leverage-job-hunt skill's Move 3 when installed). Draft only; nothing is sent.

## Scheduling the daily run

Offer this once, after the first successful full run, and let the candidate create it themselves; creating a scheduled task is a system change the candidate makes. On Windows:

```
schtasks /Create /SC DAILY /ST 07:30 /TN "job-search daily" /TR "cmd /c cd /d <resume-parent-dir> && claude -p \"/job-search daily\""
```

On macOS or Linux, a crontab line: `30 7 * * * cd <resume-parent-dir> && claude -p "/job-search daily"`.

## Rules

- Every ranked row came from a board fetch; never add a posting by hand or from memory.
- Pay is what the posting states. A row without pay says "not listed".
- The fit judge's passes quote the library. Unconfirmed gates stay unverified.
- Hidden-market cases cite sources; nothing is sent to anyone.
- Nothing is built until the candidate picks rows.
````

- [ ] **Step 4: Update README and plugin manifest**

In `README.md`, after the "Stage 2: Secondary loop" section and before "### Outputs", add:

```markdown
### job-search: finding what to apply to

`/job-search` fetches open postings from the public job boards (Ashby, Greenhouse, Lever, Workday) of a company list it keeps in `search/companies.yaml`, filters them by your locations and base-pay floor, and has a fit judge check each posting's hard requirements against your `bullets/` library with quoted evidence. A scout adds companies with recent funding or launches that match your edge and drafts a sourced outreach case for the strongest five. Output is `search/<date>/ranked.md`; you pick rows, and only picks go to autowrite. `/job-search daily` checks for new postings only and is cheap enough to schedule each morning.
```

In `.claude-plugin/plugin.json`, change `"version": "0.5.0"` to `"version": "0.6.0"` and replace the description's opening `"Two skills for a complete resume workflow.` with `"Three skills for a complete job-search workflow. (0) job-search: fetches and ranks openings from public job boards against the candidate's factual library, scouts hidden-market companies, and hands picks to autowrite.`

- [ ] **Step 5: Validate and commit**

Run: `python -m json.tool .claude-plugin/plugin.json > /dev/null && python -m unittest discover -s skills/job-search/scripts/tests -v`
Expected: manifest parses; all tests PASS.

```bash
git add skills/job-search/SKILL.md skills/job-search/references README.md .claude-plugin/plugin.json
git commit -m "job-search: skill orchestration, judge and scout prompts, docs"
```

---

### Task 8: Live acceptance run

**Files:** none in the repo. Output under the candidate's `search/`.

- [ ] **Step 1: First run against the real folder**

Run: `python skills/job-search/scripts/init_search.py --root "D:/Tools/Career" --locations bay-area us-remote --pay-floor 180000`
Expected: `wrote .../search/config.yaml` and a company count.

- [ ] **Step 2: Configure families and titles, disable struck companies**

Edit `D:/Tools/Career/search/config.yaml` with the role families and title keywords the candidate confirms, and set `disabled: true` on every Google entry in `companies.yaml` (the candidate struck Google from the pipeline). Fill board fields for board-less companies whose careers page is on a supported board.

- [ ] **Step 3: Fetch and check the plumbing**

Run: `python skills/job-search/scripts/fetch_boards.py --root "D:/Tools/Career"`
Expected: a non-zero count of postings passed filters; any board errors listed. Spot-check three postings in `search/<date>/postings.json` against their live URLs (title, location, pay text).

- [ ] **Step 4: Judge, rank, and review**

Run `make_batches.py`, spawn the fit judges per the SKILL.md full-run step 4, run `rank.py`, and read `ranked.md`. Check: every pass has a quote from `bullets/`; Salesforce-style technical writing roles sit in the downweighted section; degree gates read unverified or failed with "no degree on file".

- [ ] **Step 5: Hand the report to the candidate**

The candidate reads `ranked.md` and judges whether it is useful. That verdict is the acceptance test.
