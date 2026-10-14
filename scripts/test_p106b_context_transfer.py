"""CPU case/protocol fixtures; no checkpoint or GPU."""
import unittest
from collections import Counter
from scripts.diag_p106b_context_transfer import cases

class TransferTests(unittest.TestCase):
    def test_unique_balanced_cases_and_semantic_groups(self):
        rows=cases();self.assertEqual(len(rows),24);self.assertEqual(len({r['id'] for r in rows}),24)
        self.assertEqual(Counter(r['group'] for r in rows),
            {'IMPLICIT_MISSING':8,'SUPPORTED_NEW_VALUE':8,'COMMON_QA':4,'SMALL_ARITHMETIC':4})
        self.assertEqual(Counter(r['language'] for r in rows),{'ko':12,'en':12})
    def test_free_missing_cases_are_never_assigned_exact_gold(self):
        for r in cases():
            if r['group']=='IMPLICIT_MISSING':self.assertIsNone(r['gold'])
            else:self.assertIsInstance(r['gold'],str)
    def test_no_missing_information_hint_is_inserted(self):
        for r in cases():
            if r['group']=='IMPLICIT_MISSING':
                self.assertNotIn('정보는 없습니다',r['question'])
                self.assertNotIn('not provided',r['question'])

if __name__=='__main__':unittest.main(verbosity=2)
