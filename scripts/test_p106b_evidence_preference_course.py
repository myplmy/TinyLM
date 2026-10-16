#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import unittest
from scripts import diag_p106b_evidence_preference_course as c


class Course(unittest.TestCase):
    def test_exact_parent_and_counts(self):
        r=c.info();self.assertEqual(r['parent_sha256'],'E9707AA2ABB55054DA226A6303A0EEAD8BA0B653029E24AFAD2A63D86E729E42')
        self.assertEqual((r['rows'],r['passes'],r['updates'],r['micro_bs'],r['accum']),(8192,1,64,8,16))

    def test_namespace_independent(self):
        self.assertNotEqual(c.TAG,c.upstream.TAG);self.assertNotEqual(c.PARENT,c.upstream.PARENT)
        self.assertFalse(c.info()['student_mtp']);self.assertEqual(c.info()['pairs_per_update'],16)

    def test_producer_signature_alias(self):
        import inspect
        src=inspect.getsource(c.freeze);self.assertIn('upstream.conversation_signature',src)
        self.assertIn("r['pairs_manifest']",inspect.getsource(c.read_course))

    def test_own_function_alias_not_self_recursion(self):
        self.assertIs(c.upstream_runtime.course,c.upstream);self.assertIsNot(c.upstream_runtime,c)


if __name__=='__main__':unittest.main()
