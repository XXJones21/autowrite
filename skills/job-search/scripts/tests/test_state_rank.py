import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import rank  # noqa: E402
import recheck  # noqa: E402
from state import close_missing, record_postings, to_judge, write_json  # noqa: E402


def post(pid, posted='2026-09-20', company='Co', title='Role'):
    return {'id': pid, 'board': 'ashby', 'company': company, 'title': title, 'team': '',
            'locations': ['San Francisco, CA'], 'remote': False, 'pay_min': None,
            'pay_max': None, 'pay_text': '', 'posted_date': posted,
            'url': 'https://jobs.ashbyhq.com/co/' + pid, 'description_text': 'desc'}


def verdict(pid, family='core', passed=3, total=3, failed=(), unverified=(), questions=()):
    checks = [{'requirement': 'r%d' % i, 'passed': i < passed, 'quote': 'q'} for i in range(total)]
    gates = ([{'gate': g, 'status': 'failed', 'note': ''} for g in failed]
             + [{'gate': g, 'status': 'unverified', 'note': ''} for g in unverified])
    return {'id': pid, 'role_family': family, 'checks': checks, 'gates': gates,
            'candidate_questions': list(questions)}


class StateTest(unittest.TestCase):
    def test_record_close_judge(self):
        seen = {}
        record_postings(seen, [post('a'), post('b')], '2026-09-24')
        self.assertEqual({p['id'] for p in to_judge(seen)}, {'a', 'b'})
        self.assertEqual(close_missing(seen, '', {'a'}, '2026-09-25'), ['b'])
        record_postings(seen, [post('b')], '2026-09-26')
        self.assertEqual(seen['b']['status'], 'open')
        self.assertEqual(seen['b']['first_seen'], '2026-09-24')


class RankTest(unittest.TestCase):
    def test_sort_order(self):
        seen = {}
        record_postings(seen, [post('gate', '2026-09-23'), post('adj', '2026-09-22'),
                               post('core-old', '2026-09-01'), post('core-new', '2026-09-21'),
                               post('weak', '2026-09-23'), post('tw', '2026-09-23')],
                        '2026-09-24')
        n = rank.merge_verdicts(seen, [
            verdict('gate', failed=['degree']), verdict('adj', family='adjacent'),
            verdict('core-old'), verdict('core-new'), verdict('weak', passed=1),
            verdict('tw', family='downweight'), verdict('unknown-id')], '2026-09-24')
        self.assertEqual(n, 6)
        rows = rank.build(seen, '2026-09-24')
        self.assertEqual([r['id'] for r in rows],
                         ['core-new', 'core-old', 'adj', 'weak', 'gate', 'tw'])
        self.assertEqual([r['rank'] for r in rows], [1, 2, 3, 4, 5, 6])
        self.assertEqual(rows[4]['gates_failed'], ['degree'])

    def test_render(self):
        seen = {}
        record_postings(seen, [post('a'), post('t')], '2026-09-24')
        rank.merge_verdicts(seen, [verdict('a', unverified=['degree'], questions=['Q1?']),
                                   verdict('t', family='downweight')], '2026-09-24')
        rows = rank.build(seen, '2026-09-24')
        md = rank.render_md(rows, '2026-09-24',
                            {'mode': 'daily', 'filtered_out': {'pay': 2},
                             'boards_not_checked': [{'company': 'X', 'board': 'lever',
                                                     'error': 'TimeoutError'}]},
                            {'cases': [{'company': 'Hidden Co', 'paragraph': 'Case.',
                                        'sources': ['https://src']}]},
                            {'deferred': ['z']})
        for needle in ('## Ranked roles', '## New since yesterday',
                       '## Technical writing (downweighted)', 'unverified: degree',
                       '## Hidden market', 'Hidden Co', 'https://src', '## Questions for you',
                       'Q1?', '## Boards not checked', 'X (lever)', 'not listed',
                       '1 postings deferred'):
            self.assertIn(needle, md)


class PipelineAndUnverifiedTest(unittest.TestCase):
    def test_unverified_breaks_ties(self):
        seen = {}
        record_postings(seen, [post('clean', '2026-09-01'), post('open', '2026-09-23')], '2026-09-24')
        rank.merge_verdicts(seen, [verdict('clean'), verdict('open', unverified=['spanish'])],
                            '2026-09-24')
        self.assertEqual([r['id'] for r in rank.build(seen, '2026-09-24')], ['clean', 'open'])

    def test_pipeline_rows_split_out(self):
        root = tempfile.mkdtemp()
        try:
            d = os.path.join(root, 'applications', 'co', 'role')
            os.makedirs(d)
            with open(os.path.join(d, 'job-posting.md'), 'w', encoding='utf-8') as f:
                f.write('URL: https://jobs.ashbyhq.com/co/abc-123' + chr(10))
            with open(os.path.join(root, 'applications', 'Tracker.csv'), 'w', encoding='utf-8') as f:
                f.write('Co,Role,https://job-boards.greenhouse.io/co/jobs/555' + chr(10))
            tokens = rank.pipeline_tokens(root)
            p1, p2, p3 = (post('ashby:co:abc-123'), post('greenhouse:co:555'),
                          post('ashby:co:new-1', title='Brand New Role'))
            self.assertTrue(rank.in_pipeline(p1, tokens))
            self.assertTrue(rank.in_pipeline(p2, tokens))
            self.assertFalse(rank.in_pipeline(p3, tokens))
            with open(os.path.join(root, 'applications', 'Job Tracker.csv'), 'w', encoding='utf-8') as f:
                f.write('Anthropic,Developer Relations (Claude Code),https://www.anthropic.com/jobs' + chr(10))
                f.write('NVIDIA,Developer Relations Manager,notes mention Ollama' + chr(10))
            tokens = rank.pipeline_tokens(root)
            self.assertTrue(rank.in_pipeline(post('greenhouse:anthropic:9', company='Anthropic',
                                                  title='Developer Relations'), tokens))
            self.assertFalse(rank.in_pipeline(post('greenhouse:anthropic:8', company='Anthropic',
                                                   title='Forward Deployed Engineer'), tokens))
            self.assertFalse(rank.in_pipeline(post('ashby:ollama:1', company='Ollama',
                                                   title='Developer Relations'), tokens))
            seen = {}
            record_postings(seen, [p1, p3], '2026-09-24')
            rank.merge_verdicts(seen, [verdict(p1['id']), verdict(p3['id'])], '2026-09-24')
            rows = rank.build(seen, '2026-09-24', tokens)
            self.assertEqual([(r['id'], r['in_pipeline']) for r in rows],
                             [(p3['id'], False), (p1['id'], True)])
            md = rank.render_md(rows, '2026-09-24', {}, None, None)
            self.assertIn('## Already in your pipeline', md)
        finally:
            shutil.rmtree(root)


class CopyDupesTest(unittest.TestCase):
    def test_copy(self):
        seen = {}
        record_postings(seen, [post('a'), post('b')], '2026-09-24')
        rank.merge_verdicts(seen, [verdict('a')], '2026-09-24')
        n = rank.copy_duplicate_verdicts(seen, {'a': ['b', 'missing']}, '2026-09-24')
        self.assertEqual(n, 1)
        self.assertEqual(seen['b']['verdict']['id'], 'b')
        self.assertEqual(seen['b']['verdict']['checks'], seen['a']['verdict']['checks'])


class RecheckTest(unittest.TestCase):
    def test_write_posting(self):
        root = tempfile.mkdtemp()
        try:
            path = recheck.write_posting(root, post('a', company='Weave Inc.', title='Founding DevRel'))
            self.assertTrue(path.endswith(os.path.join('applications', 'weave-inc',
                                                       'founding-devrel', 'job-posting.md')))
            with open(path, encoding='utf-8') as f:
                text = f.read()
            self.assertIn('https://jobs.ashbyhq.com/co/a', text)
            self.assertIn('desc', text)
            second = recheck.write_posting(root, post('a', company='Weave Inc.',
                                                      title='Founding DevRel'))
            self.assertNotEqual(second, path)
        finally:
            shutil.rmtree(root)

    def test_run_marks_closed(self):
        root = tempfile.mkdtemp()
        try:
            from companies import save_yaml
            from state import load_seen, save_seen
            save_yaml(root, 'companies.yaml', {'companies': [
                {'name': 'Co', 'board': 'ashby', 'board_id': 'co'}]})
            seen = {}
            record_postings(seen, [post('ashby:co:1'), post('ashby:co:2')], '2026-09-24')
            save_seen(root, seen)
            write_json(os.path.join(root, 'search', '2026-09-24', 'ranked.json'), {'rows': [
                {'rank': 1, 'id': 'ashby:co:1', 'company': 'Co'},
                {'rank': 2, 'id': 'ashby:co:2', 'company': 'Co'}]})

            class Http:
                def get_json(self, url):
                    return {'jobs': [{'id': '1', 'title': 'Role', 'jobUrl': 'https://j/1',
                                      'descriptionPlain': 'live desc'}]}
            out = recheck.run(root, '2026-09-24', [1, 2], Http())
            self.assertEqual([o[1] for o in out], ['live', 'closed'])
            self.assertEqual(load_seen(root)['ashby:co:2']['status'], 'closed')
        finally:
            shutil.rmtree(root)


if __name__ == '__main__':
    unittest.main()
