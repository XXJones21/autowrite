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
