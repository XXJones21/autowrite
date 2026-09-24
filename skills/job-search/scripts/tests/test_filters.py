import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from filters import apply_filters, location_ok, parse_pay, title_ok  # noqa: E402

KEEP = ['bay-area', 'us-remote']


def posting(title='Developer Relations Manager', locations=('Santa Clara, CA',), remote=False,
            pay_max=None):
    return {'id': 'x', 'title': title, 'locations': list(locations), 'remote': remote,
            'pay_min': None, 'pay_max': pay_max}


class PayTest(unittest.TestCase):
    def test_workday_levels(self):
        text = ('The base salary range is 184,000 USD - 287,500 USD for Level 4, and '
                '224,000 USD - 356,500 USD for Level 5.')
        self.assertEqual(parse_pay(text), (184000, 356500))

    def test_k_and_en_dash(self):
        self.assertEqual(parse_pay('$150K \u2013 $200K \u2022 0.1% \u2013 0.2%'), (150000, 200000))

    def test_dollar_commas(self):
        self.assertEqual(parse_pay('range is $143,400 - $216,900 annually ... $172,200 - $236,700'),
                         (143400, 236700))

    def test_ignores_hourly_years_and_phones(self):
        self.assertIsNone(parse_pay('$20 - $30 per hour, 2015 - 2019, call 317-385-1198'))

    def test_html_entities(self):
        self.assertEqual(parse_pay('$180,000&nbsp;-&nbsp;$220,000'), (180000, 220000))


class LocationTest(unittest.TestCase):
    def test_bay_area_workday_format(self):
        self.assertTrue(location_ok(['US, CA, Santa Clara'], False, KEEP))
        self.assertTrue(location_ok(['US-CA-Santa-Clara'], False, KEEP))
        self.assertTrue(location_ok(['San Francisco, CA | Seattle, WA'], False, KEEP))

    def test_non_bay_onsite_dropped(self):
        self.assertFalse(location_ok(['New York, NY'], False, KEEP))
        self.assertFalse(location_ok(['Tel Aviv, Israel'], False, KEEP))

    def test_us_remote(self):
        self.assertTrue(location_ok(['Remote - US'], False, KEEP))
        self.assertTrue(location_ok(['Remote'], False, KEEP))
        self.assertTrue(location_ok(['New York, NY'], True, KEEP))

    def test_non_us_remote_dropped(self):
        self.assertFalse(location_ok(['Remote - Canada'], False, KEEP))
        self.assertFalse(location_ok(['London, UK'], True, KEEP))

    def test_bay_only_keep(self):
        self.assertFalse(location_ok(['Remote - US'], False, ['bay-area']))


class TitleTest(unittest.TestCase):
    def test_include_exclude(self):
        self.assertTrue(title_ok('Senior Developer Relations Engineer', ['developer relations'], []))
        self.assertFalse(title_ok('Account Executive', ['developer relations'], []))
        self.assertFalse(title_ok('Developer Relations Intern', ['developer relations'], ['intern']))
        self.assertTrue(title_ok('Anything', [], []))

    def test_qualified_terms(self):
        q = {'terms': ['product manager', 'technical program manager'],
             'with': ['developer', 'platform', 'api', 'ai', 'agent', 'tools']}
        inc = ['product manager', 'technical program manager', 'developer relations']
        self.assertTrue(title_ok('Product Manager, Developer Platform', inc, [], q))
        self.assertTrue(title_ok('Product Manager, AI Agents', inc, [], q))
        self.assertFalse(title_ok('Product Manager, Cybersecurity', inc, [], q))
        self.assertFalse(title_ok('Technical Program Manager, Rapid Prototyping', inc, [], q))
        self.assertFalse(title_ok('Product Manager, Maintenance', inc, [], q))
        self.assertTrue(title_ok('Developer Relations Engineer', inc, [], q))


class ApplyTest(unittest.TestCase):
    CONFIG = {'locations': {'keep': KEEP}, 'pay': {'base_floor_usd': 180000},
              'titles': {'include': ['developer relations'], 'exclude': []}}

    def test_apply(self):
        ps = [posting(),                                       # kept, no pay
              posting(pay_max=170000),                         # pay drop
              posting(pay_max=200000),                         # kept
              posting(locations=['Tel Aviv, Israel']),         # location drop
              posting(title='Account Executive')]              # title drop
        kept, stats = apply_filters(ps, self.CONFIG)
        self.assertEqual(len(kept), 2)
        self.assertEqual(stats, {'title': 1, 'location': 1, 'pay': 1})
        self.assertFalse(kept[0]['pay_listed'])
        self.assertTrue(kept[1]['pay_listed'])

    def test_apply_uses_qualify(self):
        cfg = {'locations': {'keep': []}, 'pay': {}, 'titles': {
            'include': ['product manager'], 'exclude': [],
            'qualify': {'terms': ['product manager'], 'with': ['api']}}}
        kept, stats = apply_filters([posting(title='Product Manager, API'),
                                     posting(title='Product Manager, Payroll')], cfg)
        self.assertEqual([p['title'] for p in kept], ['Product Manager, API'])
        self.assertEqual(stats['title'], 1)

    def test_empty_keep_disables_location_filter(self):
        kept, _ = apply_filters([posting(locations=['Tel Aviv, Israel'])],
                                {'locations': {'keep': []}, 'pay': {}, 'titles': {}})
        self.assertEqual(len(kept), 1)


if __name__ == '__main__':
    unittest.main()
