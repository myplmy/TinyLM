"""CPU boundaries for the English-source production fork."""
import copy
import unittest
from unittest.mock import patch

from scripts import diag_p106b_nov05_english_production as fork


class EnglishForkTests(unittest.TestCase):
    def test_only_exact_management_example_is_removed(self):
        payload = dict(messages=[dict(role='system', content='control ' + fork.EXAMPLE + ' visible source instruction'),
                                 dict(role='user', content='source Example: remains')],
                       temperature=1.0, thinking_budget_tokens=1024)
        before = copy.deepcopy(payload)
        result = fork.without_example(payload)
        self.assertEqual(result['messages'][1:], before['messages'][1:])
        self.assertEqual(result['temperature'], before['temperature'])
        self.assertEqual(result['thinking_budget_tokens'], before['thinking_budget_tokens'])
        self.assertNotIn(fork.EXAMPLE, result['messages'][0]['content'])
        self.assertTrue(result['messages'][0]['content'].startswith('control '))
        self.assertTrue(result['messages'][0]['content'].endswith(' visible source instruction'))

    def test_duplicate_management_example_is_rejected(self):
        with self.assertRaises(ValueError):
            fork.without_example(dict(messages=[dict(role='system', content=fork.EXAMPLE * 2)]))

    def test_changed_example_fails_instead_of_broad_text_replacement(self):
        with self.assertRaises(ValueError):
            fork.without_example(dict(messages=[dict(role='system', content='another template')]))

    def test_unapproved_source_is_not_opened(self):
        def forbidden(_):
            raise AssertionError('unapproved source opened')
        self.assertEqual(list(fork.english_rows({'path': 'other'}, forbidden, {'approved'})), [])

    def test_exact_source_rows_keep_their_order_and_objects(self):
        items = [dict(meta=dict(language='en'), value=k) for k in (8, 12, 19)]
        result = list(fork.english_rows({'path': 'approved'}, lambda _: iter(items), {'approved'}))
        self.assertEqual([r['value'] for r in result], [8, 12, 19])
        self.assertTrue(all(a is b for a, b in zip(items, result)))

    def test_non_english_metadata_is_rejected(self):
        with self.assertRaises(ValueError):
            list(fork.english_rows({'path': 'approved'},
                 lambda _: iter([dict(meta=dict(language='ko'))]), {'approved'}))

    def test_parent_batch_count_mismatch_precedes_new_replay(self):
        info = dict(ancestor_cursor=[1, 1], prior_visible_batch_count=7)
        with patch.object(fork.supported, 'replay', return_value=(object(), (1, 2), 8)):
            with self.assertRaisesRegex(ValueError, 'prior V3 batch count'):
                fork.replay_new(object(), object(), object(), object(), info)

    def test_new_input_mismatch_precedes_any_candidate_admission(self):
        info = dict(ancestor_cursor=[1, 1], prior_visible_batch_count=7)
        with patch.object(fork.supported, 'replay', return_value=(object(), (1, 2), 7)), \
             patch.object(fork.supported, 'batches', return_value=[(None, dict(input=dict(other=1)))]):
            with self.assertRaisesRegex(ValueError, 'new fork input contract'):
                fork.replay_new(object(), object(), object(), object(), info)


if __name__ == '__main__':
    unittest.main()
