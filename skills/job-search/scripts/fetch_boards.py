"""Fetch every board in search/companies.yaml, filter, update seen.json, write postings.json."""
import argparse
import datetime
import os

from boards import Http, board_prefix, fetch_board
from companies import COMPANIES_HEADER, load_yaml, save_yaml
from filters import apply_filters
from state import (close_missing, load_seen, record_postings, run_dir, save_seen,
                   write_json)


def _drop_refiltered(seen, prefix, config):
    """Remove unjudged postings under this board that no longer pass the current filters,
    so a narrowed config takes effect before judging."""
    pending = [rec['posting'] for pid, rec in seen.items()
               if pid.startswith(prefix) and rec['judged'] is None]
    kept_ids = {p['id'] for p in apply_filters([dict(p) for p in pending], config)[0]}
    gone = [p['id'] for p in pending if p['id'] not in kept_ids]
    for pid in gone:
        del seen[pid]
    return gone


def run(root, date, daily, http):
    config = load_yaml(root, 'config.yaml', None)
    if config is None:
        raise SystemExit('search/config.yaml not found; run init_search.py first')
    data = load_yaml(root, 'companies.yaml', {'companies': []})
    companies = data.get('companies') or []
    seen = load_seen(root)
    out, not_checked, closed, dropped = [], [], [], []
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
        prefix = board_prefix(c)
        closed += close_missing(seen, prefix, live, date)
        dropped += _drop_refiltered(seen, prefix, config)
        kept, stats = apply_filters(posts, config)
        for k, v in stats.items():
            filtered[k] += v
        record_postings(seen, kept, date)
        out += [p for p in kept if not daily or seen[p['id']]['first_seen'] == date]
    result = {'date': date, 'mode': 'daily' if daily else 'full', 'postings': out,
              'boards_not_checked': not_checked,
              'flagged_companies': [c.get('name') for c in companies
                                    if int(c.get('failures') or 0) >= 3],
              'filtered_out': filtered, 'closed': closed, 'dropped_unjudged': dropped}
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
