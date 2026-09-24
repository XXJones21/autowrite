import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import fetch_boards  # noqa: E402
import make_batches  # noqa: E402
from companies import load_yaml, save_yaml  # noqa: E402
from state import load_seen, read_json  # noqa: E402


def fixture(name):
    with open(os.path.join(HERE, 'fixtures', name), encoding='utf-8') as f:
        return json.load(f)


class FakeHttp:
    def __init__(self, ashby):
        self.ashby = ashby

    def get_json(self, url):
        if 'weave-os' in url:
            return self.ashby
        raise TimeoutError('board timed out')

    def post_json(self, url, body):
        raise TimeoutError('board timed out')


class RunTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        save_yaml(self.root, 'config.yaml', {
            'locations': {'keep': ['bay-area', 'us-remote']}, 'pay': {'base_floor_usd': 0},
            'titles': {'include': [], 'exclude': []}, 'daily': {'max_judge_batches': 5}})
        save_yaml(self.root, 'companies.yaml', {'companies': [
            {'name': 'Weave', 'board': 'ashby', 'board_id': 'weave-os'},
            {'name': 'Broken', 'board': 'greenhouse', 'board_id': 'broken', 'failures': 2},
            {'name': 'Skipped', 'board': 'none'}]})
        self.ashby = fixture('ashby.json')

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_full_then_daily(self):
        r = fetch_boards.run(self.root, '2026-09-24', False, FakeHttp(self.ashby))
        self.assertTrue(r['postings'])
        self.assertEqual([b['company'] for b in r['boards_not_checked']], ['Broken'])
        self.assertEqual(r['flagged_companies'], ['Broken'])
        cs = load_yaml(self.root, 'companies.yaml', {})['companies']
        self.assertEqual(cs[1]['failures'], 3)
        self.assertEqual(cs[0]['failures'], 0)
        seen = load_seen(self.root)
        self.assertEqual(len(seen), len(r['postings']))

        # next day: nothing new, one posting vanished
        gone = self.ashby['jobs'][0]['id']
        self.ashby['jobs'] = self.ashby['jobs'][1:]
        r2 = fetch_boards.run(self.root, '2026-09-25', True, FakeHttp(self.ashby))
        self.assertEqual(r2['postings'], [])
        self.assertEqual(r2['closed'], ['ashby:weave-os:' + gone])
        self.assertEqual(load_seen(self.root)['ashby:weave-os:' + gone]['status'], 'closed')

    def test_refilter_drops_unjudged(self):
        fetch_boards.run(self.root, '2026-09-24', False, FakeHttp(self.ashby))
        before = load_seen(self.root)
        self.assertTrue(before)
        save_yaml(self.root, 'config.yaml', {
            'locations': {'keep': []}, 'pay': {'base_floor_usd': 0},
            'titles': {'include': ['no title matches this'], 'exclude': []}})
        r = fetch_boards.run(self.root, '2026-09-24', False, FakeHttp(self.ashby))
        self.assertEqual(load_seen(self.root), {})
        self.assertEqual(len(r['dropped_unjudged']), len(before))

    def test_batches_and_cap(self):
        fetch_boards.run(self.root, '2026-09-24', False, FakeHttp(self.ashby))
        names, deferred = make_batches.run(self.root, '2026-09-24', batch_size=1,
                                           max_batches=1, stamp='t1')
        self.assertEqual(names, ['batch-t1-01'])
        self.assertEqual(len(deferred), len(load_seen(self.root)) - 1)
        b = read_json(os.path.join(self.root, 'search', '2026-09-24', 'batches',
                                   'batch-t1-01.json'), {})
        self.assertEqual(set(b['postings'][0]), {'id', 'company', 'title', 'locations', 'remote',
                                                 'pay_text', 'url', 'description_text'})
        idx = read_json(os.path.join(self.root, 'search', '2026-09-24', 'batches',
                                     'index.json'), {})
        self.assertEqual(idx['batches'], ['batch-t1-01'])


class PriorityTest(unittest.TestCase):
    def test_priority_then_date(self):
        ps = [{'id': 'a', 'title': 'Solutions Architect', 'posted_date': '2026-09-23'},
              {'id': 'b', 'title': 'Developer Relations Lead', 'posted_date': '2026-09-01'},
              {'id': 'c', 'title': 'Staff Engineer, Agents', 'posted_date': '2026-09-20'},
              {'id': 'd', 'title': 'Developer Relations Engineer', 'posted_date': '2026-09-22'},
              {'id': 'e', 'title': 'Unmatched', 'posted_date': '2026-09-24'}]
        order = make_batches.prioritize(ps, ['developer relations', 'agent', 'solutions architect'])
        self.assertEqual([p['id'] for p in order], ['d', 'b', 'c', 'a', 'e'])


class DedupeTest(unittest.TestCase):
    def test_group_duplicates(self):
        base = {'company': 'Databricks', 'title': 'Sr. FDE - Retail', 'description_text': 'same jd'}
        ps = [dict(base, id='1'), dict(base, id='2'), dict(base, id='3', title='Sr. FDE - Retail '),
              dict(base, id='4', description_text='other jd')]
        reps, dupes = make_batches.dedupe(ps)
        self.assertEqual([p['id'] for p in reps], ['1', '4'])
        self.assertEqual(dupes, {'1': ['2', '3']})


if __name__ == '__main__':
    unittest.main()
