import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import boards  # noqa: E402


def fixture(name):
    with open(os.path.join(HERE, 'fixtures', name), encoding='utf-8') as f:
        return json.load(f)


KEYS = {'id', 'board', 'company', 'title', 'team', 'locations', 'remote', 'pay_min',
        'pay_max', 'pay_text', 'posted_date', 'url', 'description_text'}


class NormalizeTest(unittest.TestCase):
    def check_shape(self, posts, prefix):
        self.assertTrue(posts)
        for p in posts:
            self.assertEqual(set(p), KEYS)
            self.assertTrue(p['id'].startswith(prefix))
            self.assertTrue(p['title'])
            self.assertTrue(p['url'].startswith('https://'))
            self.assertIsInstance(p['locations'], list)

    def test_ashby(self):
        posts = boards.normalize_ashby(fixture('ashby.json'), 'Weave', 'weave-os')
        self.check_shape(posts, 'ashby:weave-os:')
        ml = next(p for p in posts if p['title'] == 'Founding ML Engineer')
        self.assertEqual((ml['pay_min'], ml['pay_max']), (150000, 200000))
        self.assertIn('San Francisco, California, United States', ml['locations'])
        self.assertRegex(ml['posted_date'], r'^\d{4}-\d{2}-\d{2}$')

    def test_greenhouse(self):
        posts = boards.normalize_greenhouse(fixture('greenhouse.json'), 'Anthropic', 'anthropic')
        self.check_shape(posts, 'greenhouse:anthropic:')
        self.assertNotIn('&lt;', posts[0]['description_text'])

    def test_lever(self):
        posts = boards.normalize_lever(fixture('lever.json'), 'Palantir', 'palantir')
        self.check_shape(posts, 'lever:palantir:')
        self.assertRegex(posts[0]['posted_date'], r'^\d{4}-\d{2}-\d{2}$')

    def test_workday_nvidia(self):
        path = '/job/US-CA-Santa-Clara/Developer-Relations-Manager--Local-AI-Ecosystem_JR2021035'
        p = boards.normalize_workday(fixture('workday-detail-nvidia.json'), 'NVIDIA', 'nvidia', path)
        self.check_shape([p], 'workday:nvidia:/job/')
        self.assertEqual(p['title'], 'Developer Relations Manager, Local AI Ecosystem')
        self.assertEqual((p['pay_min'], p['pay_max']), (184000, 356500))

    def test_workday_salesforce(self):
        path = '/job/California---San-Francisco/Lead-Technical-Writer_JR360438'
        p = boards.normalize_workday(fixture('workday-detail-salesforce.json'), 'Salesforce',
                                     'salesforce', path)
        self.assertEqual((p['pay_min'], p['pay_max']), (143400, 236700))


class FakeHttp:
    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def get_json(self, url):
        self.calls.append(('GET', url))
        for key, val in self.routes.items():
            if key in url:
                if isinstance(val, Exception):
                    raise val
                return val
        raise AssertionError('unexpected GET ' + url)

    def post_json(self, url, body):
        self.calls.append(('POST', url, body.get('offset')))
        return self.routes['POST ' + url]


class FetchTest(unittest.TestCase):
    def test_fetch_ashby(self):
        http = FakeHttp({'job-board/weave-os': fixture('ashby.json')})
        entry = {'name': 'Weave', 'board': 'ashby', 'board_id': 'weave-os'}
        live, posts = boards.fetch_board(entry, http, set(), {})
        self.assertEqual(live, {p['id'] for p in posts})
        self.assertEqual(boards.board_prefix(entry), 'ashby:weave-os:')

    def test_fetch_workday_skips_seen_and_caps(self):
        base = 'https://nvidia.wd5.myworkdayjobs.com/wday/cxs/nvidia/NVIDIAExternalCareerSite'
        listing = fixture('workday-list.json')
        detail = fixture('workday-detail-nvidia.json')
        http = FakeHttp({'POST ' + base + '/jobs': listing, base + '/job/': detail})
        entry = {'name': 'NVIDIA', 'board': 'workday', 'host': 'nvidia.wd5.myworkdayjobs.com',
                 'tenant': 'nvidia', 'site': 'NVIDIAExternalCareerSite',
                 'search_terms': ['developer relations']}
        paths = [r['externalPath'] for r in listing['jobPostings']]
        seen = {'workday:nvidia:' + paths[0]}
        live, posts = boards.fetch_board(entry, http, seen,
                                         {'locations': {'keep': []}, 'workday': {'detail_cap': 1}})
        self.assertEqual(live, {'workday:nvidia:' + p for p in paths})
        self.assertEqual(len(posts), 1)
        self.assertNotIn(('GET', base + paths[0]), http.calls)
        self.assertEqual(boards.board_prefix(entry), 'workday:nvidia:')

    def test_unsupported_board(self):
        with self.assertRaises(ValueError):
            boards.fetch_board({'name': 'X', 'board': 'smartrecruiters'}, FakeHttp({}), set(), {})


if __name__ == '__main__':
    unittest.main()
