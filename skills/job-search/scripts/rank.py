"""Merge fit-judge verdicts, rank open roles, and write ranked.md and ranked.json."""
import argparse
import datetime
import os
import re

from state import load_seen, read_json, run_dir, save_seen, write_json

FAMILY_ORDER = {'core': 0, 'adjacent': 1, 'downweight': 2}
URL_RX = re.compile(r'https?://[^\s)\]>"\'`|,]+')


def pipeline_tokens(root):
    """URL path pieces from every tracker and packet under applications/, used to spot
    postings the candidate already applied to or built a packet for."""
    tokens = set()
    apps = os.path.join(root, 'applications')
    for dirpath, _dirs, files in os.walk(apps):
        for fn in files:
            if not fn.endswith(('.md', '.csv', '.json', '.txt')):
                continue
            try:
                with open(os.path.join(dirpath, fn), encoding='utf-8', errors='ignore') as f:
                    text = f.read()
            except OSError:
                continue
            for url in URL_RX.findall(text):
                tokens.update(t for t in re.split(r'[/?=&_#.]', url) if len(t) >= 3)
            if fn.endswith('.csv'):
                for line in text.splitlines():
                    first = line.split(',', 1)[0].strip().strip('"').lower()
                    if first:
                        tokens.add('row:%s' + chr(9) + '%s' % (first, line.lower()))
    return tokens


def in_pipeline(posting, tokens):
    native = posting['id'].split(':', 2)[-1]
    last = native.rstrip('/').split('/')[-1]
    if native in tokens or last in tokens or last.split('_')[-1] in tokens:
        return True
    company = (posting.get('company') or '').lower()
    title = (posting.get('title') or '').lower().strip()
    if not (company and title):
        return False
    for t in tokens:
        if not t.startswith('row:'):
            continue
        first, _, line = t[4:].partition('	')
        if (first == company or company in first or first in company) and title in line:
            return True
    return False


def merge_verdicts(seen, verdicts, date):
    n = 0
    for v in verdicts:
        rec = seen.get(v.get('id'))
        if rec is None:
            continue
        rec['verdict'], rec['judged'] = v, date
        n += 1
    return n


def copy_duplicate_verdicts(seen, duplicates, date):
    """Give each duplicate posting its representative's verdict (same company, title,
    and description). Returns the number of postings updated."""
    n = 0
    for rep, dups in (duplicates or {}).items():
        v = (seen.get(rep) or {}).get('verdict')
        if not v:
            continue
        for d in dups:
            if d in seen:
                seen[d]['verdict'], seen[d]['judged'] = dict(v, id=d), date
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
        passed, total, failed, unverified = _summary(r['verdict'])
        return (1 if failed else 0, -passed, -(passed / total if total else 0),
                len(unverified), FAMILY_ORDER.get(r['verdict'].get('role_family'), 3))
    return sorted(recs, key=key)


def build(seen, date, tokens=None):
    judged = [r for r in seen.values() if r['status'] == 'open' and r.get('verdict')]
    piped = [r for r in judged if tokens and in_pipeline(r['posting'], tokens)]
    fresh = [r for r in judged if r not in piped]
    main = _sort([r for r in fresh if r['verdict'].get('role_family') != 'downweight'])
    down = _sort([r for r in fresh if r['verdict'].get('role_family') == 'downweight'])
    rows = []
    for n, r in enumerate(main + down + _sort(piped), 1):
        p, v = r['posting'], r['verdict']
        passed, total, failed, unverified = _summary(v)
        rows.append({'rank': n, 'id': p['id'], 'company': p['company'], 'title': p['title'],
                     'locations': p.get('locations') or [], 'pay_text': p.get('pay_text') or '',
                     'pay_listed': p.get('pay_max') is not None,
                     'family': v.get('role_family'), 'checks_passed': passed,
                     'checks_total': total, 'gates_failed': failed,
                     'gates_unverified': unverified, 'posted_date': p.get('posted_date'),
                     'first_seen': r['first_seen'], 'url': p.get('url', ''),
                     'in_pipeline': r in piped, 'verdict': v})
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
    main = [r for r in rows if r['family'] != 'downweight' and not r.get('in_pipeline')]
    down = [r for r in rows if r['family'] == 'downweight' and not r.get('in_pipeline')]
    piped = [r for r in rows if r.get('in_pipeline')]
    out += ['## Ranked roles', ''] + (_table(main) if main else ['None yet.']) + ['']
    if mode == 'daily':
        new = [r for r in rows if r['first_seen'] == date]
        out += ['## New since yesterday', ''] + (_table(new) if new else ['None.']) + ['']
    if down:
        out += ['## Technical writing (downweighted)', ''] + _table(down) + ['']
    if piped:
        out += ['## Already in your pipeline', '',
                'Postings whose link already appears in a tracker or packet under applications/.',
                ''] + _table(piped) + ['']
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
    index = read_json(os.path.join(bdir, 'index.json'), None)
    copy_duplicate_verdicts(seen, (index or {}).get('duplicates'), date)
    rows = build(seen, date, pipeline_tokens(root))
    meta = read_json(os.path.join(rdir, 'postings.json'), {})
    scout = read_json(os.path.join(rdir, 'scout.json'), None)
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
