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
        board_id = m.group(1).rstrip('.')
        if board_id in ('embed', 'v1', ''):
            return None
        return {'board': board, 'board_id': board_id}
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
