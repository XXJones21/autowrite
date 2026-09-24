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
