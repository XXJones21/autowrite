"""Find public job boards (Ashby, Greenhouse, Lever) for company names and add them to
search/companies.yaml. Tries slug variants of each name; keeps a board only when it lists jobs."""
import argparse
import re

from boards import Http
from companies import COMPANIES_HEADER, load_yaml, merge_companies, save_yaml

URLS = [('ashby', 'https://api.ashbyhq.com/posting-api/job-board/%s'),
        ('greenhouse', 'https://boards-api.greenhouse.io/v1/boards/%s/jobs'),
        ('lever', 'https://api.lever.co/v0/postings/%s?mode=json')]
SUFFIXES = {'ai', 'inc', 'labs', 'lab', 'technologies', 'technology', 'hq', 'io', 'co', 'corp'}


def slug_variants(name):
    words = re.findall(r'[a-z0-9]+', (name or '').lower())
    out = []

    def add(ws):
        for sep in ('', '-', '_'):
            s = sep.join(ws)
            if s and s not in out:
                out.append(s)
    add(words)
    if '&' in (name or ''):
        add(re.findall(r'[a-z0-9]+', name.lower().replace('&', ' and ')))
    trimmed = [w for w in words if w not in SUFFIXES]
    if trimmed and trimmed != words:
        add(trimmed)
    return out


def find_board(name, http):
    for slug in slug_variants(name):
        for board, url in URLS:
            try:
                data = http.get_json(url % slug)
            except Exception:
                continue
            n = len(data) if isinstance(data, list) else len(data.get('jobs') or [])
            if n:
                return {'board': board, 'board_id': slug, 'jobs': n}
    return None


def run(root, names, http, from_list=False):
    data = load_yaml(root, 'companies.yaml', {'companies': []})
    companies = data.get('companies') or []
    targets = list(names)
    if from_list:
        targets += [c['name'] for c in companies
                    if c.get('board') in (None, 'none') and not c.get('disabled')]
    found, missing = [], []
    for name in targets:
        hit = find_board(name, http)
        if hit is None:
            missing.append(name)
            continue
        merge_companies(companies, [{'name': name, 'board': hit['board'],
                                     'board_id': hit['board_id']}])
        found.append(name)
    save_yaml(root, 'companies.yaml', {'companies': companies}, header=COMPANIES_HEADER)
    return found, missing


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', required=True)
    ap.add_argument('--names', nargs='*', default=[], help='company names to look up')
    ap.add_argument('--from-list', action='store_true',
                    help='also look up every board-less company already in companies.yaml')
    a = ap.parse_args(argv)
    found, missing = run(a.root, a.names, Http(timeout=15), from_list=a.from_list)
    print('boards found: %s' % (', '.join(found) or 'none'))
    print('no public board found: %s' % (', '.join(missing) or 'none'))


if __name__ == '__main__':
    main()
