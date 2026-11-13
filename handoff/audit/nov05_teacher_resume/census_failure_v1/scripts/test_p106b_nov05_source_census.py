"""Cursor and actual quota function contracts; no corpus or GPU."""
import unittest
from types import SimpleNamespace
from collections import Counter
from scripts import diag_p106b_nov05_source_census as census


class CensusTests(unittest.TestCase):
    def test_cursor_is_original_source_and_original_iterator_position(self):
        self.assertFalse(census.after_cursor(8,44459,[8,44459]))
        self.assertFalse(census.after_cursor(7,999999,[8,44459]))
        self.assertTrue(census.after_cursor(8,44460,[8,44459]))
        self.assertTrue(census.after_cursor(9,0,[8,44459]))

    def test_boolean_or_untyped_cursor_is_not_an_ordinal(self):
        with self.assertRaises(ValueError):
            census.after_cursor(True,0,[8,44459])

    def test_original_quota_policy_is_reused_without_admission(self):
        q = SimpleNamespace(goal=10000,seen=set(),validation=SimpleNamespace(probes=set()),
            tokens=Counter(),family=Counter(),task=Counter(),
            quota=lambda split:10000 if split=='train' else 526)
        before=(dict(q.tokens),dict(q.family),dict(q.task),set(q.seen))
        key='00'*16
        self.assertIsNotNone(census.NATIVE_PROFILE(q,'train','en','Flan-Coqa',key))
        self.assertEqual(before,(dict(q.tokens),dict(q.family),dict(q.task),set(q.seen)))
        q.seen.add((key,'en'))
        self.assertIsNone(census.NATIVE_PROFILE(q,'train','en','Flan-Coqa',key))

    def test_duplicate_occurrences_keep_their_original_positions(self):
        output, counts, keys, articles = [], Counter(), set(), set()
        writer=SimpleNamespace(append=output.append)
        row=dict(original_concept_id='key',original_ordinal=7,split='train',
            article_tokens=10,source_view_trace=dict(passage_sha256='article'))
        self.assertTrue(census.retain_occurrence(writer,row,counts,keys,articles))
        self.assertFalse(census.retain_occurrence(writer,dict(row,original_ordinal=19),counts,keys,articles))
        self.assertEqual([r['original_ordinal'] for r in output],[7,19])
        self.assertEqual(counts['unique_original_concept_rows'],1)
        self.assertEqual(counts['retained_original_occurrences'],2)
        self.assertEqual(counts['duplicate_exact_original_concept'],1)


if __name__ == '__main__':
    unittest.main()
