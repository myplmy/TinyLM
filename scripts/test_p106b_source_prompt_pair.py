"""CPU counter contract regression; no model or source-data reads."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import unittest
from scripts.diag_p106b_source_prompt_pair import summarize

class PromptCounterTests(unittest.TestCase):
    def row(self,reason):return dict(subject='test',group='NATURAL',answer='5',gold='5',generation=dict(finish_reason=reason))
    def test_real_finish_reason(self):
        r=summarize([self.row('MAX_NEW'),self.row('STOP_SEQUENCE')])['test:NATURAL']
        self.assertEqual(r,dict(cases=2,literal_agreement=2,empty=0,max_new=1))
    def test_eos_disabled_cap_is_also_cap(self):self.assertEqual(summarize([self.row('MAX_NEW_EOS_DISABLED')])['test:NATURAL']['max_new'],1)
    def test_missing_reason_never_silently_zero(self):
        r=self.row('MAX_NEW');r['generation']={'stop_reason':'MAX_NEW'}
        with self.assertRaises(KeyError):summarize([r])
    def test_empty_and_agreement_are_distinct(self):
        r=self.row('EOS');r['answer']=''
        self.assertEqual(summarize([r])['test:NATURAL'],dict(cases=1,literal_agreement=0,empty=1,max_new=0))

if __name__=='__main__':unittest.main()
