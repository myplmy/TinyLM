"""CPU-only strict dev gate and fresh question contracts."""
import unittest
from scripts.diag_p108_wsp_partial_head import eligible,fresh_test


class PartialTests(unittest.TestCase):
    def test_joint_gate_rejects_echo_loop_empty_and_protected_regressions(self):
        base=dict(exact=5,protected_exact=1,loop_indicators=20,question_echoes=0,empty=0)
        good=dict(base,exact=6,loop_indicators=15)
        self.assertTrue(eligible(good,base));self.assertFalse(eligible(base,base))
        for field,value in (('question_echoes',1),('empty',1),('loop_indicators',21),('protected_exact',0)):
            with self.subTest(field=field):self.assertFalse(eligible(dict(good,**{field:value}),base))

    def test_heldout_counts_languages_and_protected_tasks(self):
        rows=fresh_test()
        self.assertEqual(len(rows),64);self.assertEqual(len({r['question'] for r in rows}),64)
        self.assertEqual(sum(r['language']=='ko' for r in rows),32)
        self.assertEqual(sum(r['protected'] for r in rows),24)
        self.assertTrue(all(r['expected'] for r in rows))


if __name__=='__main__':unittest.main()
