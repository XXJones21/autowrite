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
