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
