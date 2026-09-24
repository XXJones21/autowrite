import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import companies  # noqa: E402
import init_search  # noqa: E402
import merge_scout  # noqa: E402
from state import write_json  # noqa: E402


class DetectTest(unittest.TestCase):
    def test_patterns(self):
        self.assertEqual(companies.detect_board(
            'https://jobs.ashbyhq.com/weave-os/e8e1010b-ff04'), {'board': 'ashby', 'board_id': 'weave-os'})
        self.assertEqual(companies.detect_board(
            'https://job-boards.greenhouse.io/anthropic/jobs/5421031008'),
            {'board': 'greenhouse', 'board_id': 'anthropic'})
        self.assertEqual(companies.detect_board('https://jobs.lever.co/palantir/6ed7'),
                         {'board': 'lever', 'board_id': 'palantir'})
        self.assertEqual(companies.detect_board(
            'https://salesforce.wd12.myworkdayjobs.com/en-US/External_Career_Site/job/x'),
            {'board': 'workday', 'host': 'salesforce.wd12.myworkdayjobs.com',
             'tenant': 'salesforce', 'site': 'External_Career_Site'})
        self.assertEqual(companies.detect_board(
            'https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite/job/US-CA/x')['site'],
            'NVIDIAExternalCareerSite')
        self.assertIsNone(companies.detect_board(
            'https://nvidia.wd5.myworkdayjobs.com/wday/cxs/nvidia/Site/jobs'))
        self.assertIsNone(companies.detect_board('https://example.com/careers'))


class MergeTest(unittest.TestCase):
    def test_merge(self):
        existing = [{'name': 'Weave', 'board': 'ashby', 'board_id': 'weave-os'},
                    {'name': 'Acme', 'board': 'none'}]
        added = companies.merge_companies(existing, [
            {'name': 'Weave Inc', 'board': 'ashby', 'board_id': 'WEAVE-OS'},   # duplicate board
            {'name': 'acme', 'board': 'greenhouse', 'board_id': 'acme'},      # upgrades Acme
            {'name': 'Acme', 'board': 'none'},                                # duplicate name
            {'name': 'New Co', 'board': 'lever', 'board_id': 'newco'}])
        self.assertEqual(added, ['acme', 'New Co'])
        self.assertEqual(existing[1], {'name': 'Acme', 'board': 'greenhouse', 'board_id': 'acme'})
        self.assertEqual(len(existing), 3)


class InitTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        app = os.path.join(self.root, 'applications', 'weave')
        os.makedirs(app)
        with open(os.path.join(app, 'company-facts.md'), 'w', encoding='utf-8') as f:
            f.write('Role: https://jobs.ashbyhq.com/weave-os/e8e1010b-ff04 posted.\n')
        prof = os.path.join(self.root, 'profiles')
        os.makedirs(prof)
        with open(os.path.join(prof, 'acme.md'), 'w', encoding='utf-8') as f:
            f.write('---\nname: acme\ncompany: Acme Robotics\n---\n# Acme\n')

    def tearDown(self):
        shutil.rmtree(self.root)

    def test_first_run(self):
        init_search.run(self.root, ['bay-area', 'us-remote'], 180000)
        cfg = companies.load_yaml(self.root, 'config.yaml', None)
        self.assertEqual(cfg['locations']['keep'], ['bay-area', 'us-remote'])
        self.assertEqual(cfg['pay']['base_floor_usd'], 180000)
        cs = companies.load_yaml(self.root, 'companies.yaml', {})['companies']
        self.assertIn({'name': 'Weave', 'board': 'ashby', 'board_id': 'weave-os'}, cs)
        self.assertIn({'name': 'Acme Robotics', 'board': 'none'}, cs)
        init_search.run(self.root, [], 0)   # second run keeps config
        cfg2 = companies.load_yaml(self.root, 'config.yaml', None)
        self.assertEqual(cfg2['pay']['base_floor_usd'], 180000)

    def test_merge_scout(self):
        init_search.run(self.root, [], 0)
        write_json(os.path.join(self.root, 'search', '2026-09-24', 'scout.json'), {
            'companies': [{'name': 'Newco', 'board_url': 'https://jobs.lever.co/newco/abc',
                           'signal': 'Series A', 'source_url': 'https://x'},
                          {'name': 'Quietco', 'board_url': '', 'signal': 'launch',
                           'source_url': 'https://y'}],
            'cases': []})
        added = merge_scout.run(self.root, '2026-09-24')
        self.assertEqual(added, ['Newco', 'Quietco'])
        cs = companies.load_yaml(self.root, 'companies.yaml', {})['companies']
        newco = next(c for c in cs if c['name'] == 'Newco')
        self.assertEqual((newco['board'], newco['board_id'], newco['hidden']), ('lever', 'newco', True))


if __name__ == '__main__':
    unittest.main()
