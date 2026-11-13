"""CPU guards for empty-startup evidence and real shard closure."""
from pathlib import Path
import tempfile
import unittest

from scripts.diag_p106b_nov05_completeness import CUE, close_attempt, make_payload
from scripts.p106b_shards import ShardWriter, verify


class ClosureTests(unittest.TestCase):
    def test_empty_attempt_is_not_published_as_corpus(self):
        with tempfile.TemporaryDirectory(prefix='p106b_completeness_') as name:
            directory = Path(name)
            writer = ShardWriter(directory, 'empty')
            result = close_attempt(writer, directory, {'input': 'test'})
            self.assertEqual(result['schema'], 'P106B_EMPTY_ATTEMPT_V1')
            self.assertEqual(result['rows'], 0)
            self.assertEqual(list(directory.iterdir()), [])

    def test_real_written_row_is_closed_and_verified(self):
        with tempfile.TemporaryDirectory(prefix='p106b_completeness_') as name:
            directory = Path(name)
            writer = ShardWriter(directory, 'raw')
            writer.append({'attempt': 1, 'structural_reason': 'test only'})
            result = close_attempt(writer, directory, {'input': 'test'})
            verify(directory, result)
            self.assertEqual(result['rows'], 1)
            self.assertEqual(len(result['shards']), 1)

    def test_only_suffix_changes_and_source_stays_immutable(self):
        source = {'messages': [{'role': 'user', 'content': 'source'}]}
        case = dict(source=source, language='ko', question='질문')
        seen = []
        def original(row, language, task, seed, **kwargs):
            seen.append((row, language, task, seed, kwargs))
            return dict(messages=[dict(role='system', content='control'),
                                  dict(role='user', content='source')], seed=seed,
                        temperature=1.0, thinking_budget_tokens=1024)
        a = make_payload(original, case, 7, False)
        b = make_payload(original, case, 7, True)
        self.assertEqual(b['messages'][0]['content'], a['messages'][0]['content'] + CUE)
        self.assertEqual(a['messages'][1:], b['messages'][1:])
        self.assertEqual(seen[0], seen[1])
        self.assertEqual(source['messages'][0]['content'], 'source')
        self.assertEqual(seen[0][-1]['fixed_question'], '질문')


if __name__ == '__main__':
    unittest.main()
