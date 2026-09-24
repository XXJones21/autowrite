"""Split unjudged open postings into fit-judge batches under search/<date>/batches/."""
import argparse
import datetime
import hashlib
import os
import re

from companies import load_yaml
from state import load_seen, run_dir, to_judge, write_json

FIELDS = ('id', 'company', 'title', 'locations', 'remote', 'pay_text', 'url')


def prioritize(postings, include):
    """Order by the first matching title keyword's position in titles.include (so the
    candidate's list order is the judging priority), then newest first."""
    keys = [k.lower() for k in include or []]

    def rank(p):
        t = (p.get('title') or '').lower()
        return next((i for i, k in enumerate(keys) if k in t), len(keys))
    by_date = sorted(postings, key=lambda p: p.get('posted_date') or '', reverse=True)
    return sorted(by_date, key=rank)


def _dupe_key(p):
    title = re.sub(r'\s+', ' ', (p.get('title') or '').strip().lower())
    desc = re.sub(r'\s+', ' ', (p.get('description_text') or '')[:6000]).strip()
    return ((p.get('company') or '').lower(), title,
            hashlib.sha1(desc.encode('utf-8')).hexdigest())


def dedupe(postings):
    """Keep the first posting of each (company, title, description) group. Returns the
    representatives and {representative_id: [duplicate_ids]} so one verdict covers all."""
    reps, groups, first = [], {}, {}
    for p in postings:
        k = _dupe_key(p)
        if k in first:
            groups.setdefault(first[k], []).append(p['id'])
        else:
            first[k] = p['id']
            reps.append(p)
    return reps, groups


def run(root, date, batch_size=10, max_batches=None, stamp=None):
    stamp = stamp or datetime.datetime.now().strftime('%H%M%S')
    include = ((load_yaml(root, 'config.yaml', {}) or {}).get('titles') or {}).get('include')
    pending, dupes = dedupe(prioritize(to_judge(load_seen(root)), include))
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
    judged_now = {p['id'] for b in batches for p in b}
    write_json(os.path.join(bdir, 'index.json'), {
        'batches': names, 'deferred': deferred,
        'duplicates': {k: v for k, v in dupes.items() if k in judged_now}})
    return names, deferred


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', required=True)
    ap.add_argument('--date', default=datetime.date.today().isoformat())
    ap.add_argument('--daily', action='store_true', help='apply daily.max_judge_batches')
    ap.add_argument('--max-batches', type=int, default=None,
                    help='judge at most this many batches now; the rest wait for later runs')
    ap.add_argument('--batch-size', type=int, default=None)
    a = ap.parse_args(argv)
    daily_cfg = (load_yaml(a.root, 'config.yaml', {}) or {}).get('daily') or {}
    cap = a.max_batches
    if a.daily and cap is None:
        cap = daily_cfg.get('max_judge_batches', 5)
    size = a.batch_size or daily_cfg.get('batch_size', 10)
    names, deferred = run(a.root, a.date, batch_size=size, max_batches=cap)
    print('%d batches written, %d postings deferred' % (len(names), len(deferred)))
    for n in names:
        print('  ' + os.path.join(run_dir(a.root, a.date), 'batches', n + '.json'))


if __name__ == '__main__':
    main()
