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
