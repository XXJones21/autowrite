import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import discover_boards  # noqa: E402
from companies import load_yaml, save_yaml  # noqa: E402


class SlugTest(unittest.TestCase):
    def test_variants(self):
        v = discover_boards.slug_variants('Weights & Biases')
        self.assertEqual(v[:3], ['weightsbiases', 'weights-biases', 'weights_biases'])
        self.assertIn('weightsandbiases', v)
        self.assertEqual(discover_boards.slug_variants('Retell AI')[:2], ['retellai', 'retell-ai'])
        self.assertIn('retell', discover_boards.slug_variants('Retell AI'))


class FakeHttp:
    def __init__(self, live):
        self.live = live

    def get_json(self, url):
        for key, n in self.live.items():
            if url.endswith(key) or ('/' + key + '/') in url or url.endswith(key + '?mode=json'):
                return {'jobs': [{}] * n}
        raise OSError('404')


class DiscoverTest(unittest.TestCase):
    def test_find_and_merge(self):
        http = FakeHttp({'job-board/retell-ai': 3, 'boards/figma/jobs': 5})
        self.assertEqual(discover_boards.find_board('Retell AI', http),
                         {'board': 'ashby', 'board_id': 'retell-ai', 'jobs': 3})
        self.assertEqual(discover_boards.find_board('Figma', http),
                         {'board': 'greenhouse', 'board_id': 'figma', 'jobs': 5})
        self.assertIsNone(discover_boards.find_board('Nowhere Inc', http))
        root = tempfile.mkdtemp()
        try:
            save_yaml(root, 'companies.yaml', {'companies': [
                {'name': 'Figma', 'board': 'none'}, {'name': 'Nowhere Inc', 'board': 'none'}]})
            found, missing = discover_boards.run(root, [], http, from_list=True)
            self.assertEqual(found, ['Figma'])
            self.assertEqual(missing, ['Nowhere Inc'])
            cs = load_yaml(root, 'companies.yaml', {})['companies']
            self.assertEqual(cs[0], {'name': 'Figma', 'board': 'greenhouse', 'board_id': 'figma'})
            found2, _ = discover_boards.run(root, ['Retell AI'], http)
            self.assertEqual(found2, ['Retell AI'])
            self.assertEqual(len(load_yaml(root, 'companies.yaml', {})['companies']), 3)
        finally:
            shutil.rmtree(root)


if __name__ == '__main__':
    unittest.main()
