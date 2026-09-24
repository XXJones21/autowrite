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
    index = read_json(os.path.join(bdir, 'index.json'), None)
    copy_duplicate_verdicts(seen, (index or {}).get('duplicates'), date)
    rows = build(seen, date)
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
