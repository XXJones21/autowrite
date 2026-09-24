import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml_lite  # noqa: E402


CONFIG = """
# comment line
locations:
  keep: [bay-area, us-remote]   # trailing comment
pay:
  base_floor_usd: 180000
titles:
  include: ["developer relations", "solutions engineer"]
  exclude: []
contract_roles: false
judge_model: opus
note: "has: colon # and hash"
"""

COMPANIES = """
companies:
  - name: Weave
    board: ashby
    board_id: weave-os
  - name: NVIDIA
    board: workday
    host: nvidia.wd5.myworkdayjobs.com
    tenant: nvidia
    site: NVIDIAExternalCareerSite
    search_terms: [developer relations, solutions architect]
    failures: 0
  - name: Acme
    board: none
"""


class YamlLiteTest(unittest.TestCase):
    def test_config(self):
        d = yaml_lite.load(CONFIG)
        self.assertEqual(d['locations']['keep'], ['bay-area', 'us-remote'])
        self.assertEqual(d['pay']['base_floor_usd'], 180000)
        self.assertEqual(d['titles']['include'], ['developer relations', 'solutions engineer'])
        self.assertEqual(d['titles']['exclude'], [])
        self.assertIs(d['contract_roles'], False)
        self.assertEqual(d['judge_model'], 'opus')
        self.assertEqual(d['note'], 'has: colon # and hash')

    def test_companies(self):
        d = yaml_lite.load(COMPANIES)
        cs = d['companies']
        self.assertEqual(len(cs), 3)
        self.assertEqual(cs[0], {'name': 'Weave', 'board': 'ashby', 'board_id': 'weave-os'})
        self.assertEqual(cs[1]['search_terms'], ['developer relations', 'solutions architect'])
        self.assertEqual(cs[1]['failures'], 0)
        self.assertEqual(cs[2]['board'], 'none')

    def test_round_trip(self):
        for text in (CONFIG, COMPANIES):
            d = yaml_lite.load(text)
            self.assertEqual(yaml_lite.load(yaml_lite.dump(d)), d)

    def test_dump_quotes_urls_and_keywords(self):
        out = yaml_lite.dump({'a': 'https://x.y/z', 'b': 'true', 'c': '123', 'd': 'San Francisco'})
        d = yaml_lite.load(out)
        self.assertEqual(d, {'a': 'https://x.y/z', 'b': 'true', 'c': '123', 'd': 'San Francisco'})

    def test_bad_indent_raises(self):
        with self.assertRaises(ValueError):
            yaml_lite.load('a: 1\n    b: 2\n')


if __name__ == '__main__':
    unittest.main()
