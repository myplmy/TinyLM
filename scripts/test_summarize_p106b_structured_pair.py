from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import copy
import unittest
from scripts import summarize_p106b_structured_pair as code


class Roots(unittest.TestCase):
    def test_bilingual_root_opposing_deltas_are_not_independent(self):
        a=[];b=[]
        for root in range(2):
            for lang in ('ko','en'):
                correct=(root==0)==(lang=='ko')
                row=dict(messages=[dict(role='user',content=f'{root}:{lang}')],gold='5',answer='5',exact_code_contract=correct,
                    meta=dict(kind='addition',language=lang,semantic_root_id=str(root)),generation=dict(finish_reason='STOP'))
                other=copy.deepcopy(row);other['exact_code_contract']=not correct;a.append(row);b.append(other)
        result=code.paired_roots(a,b,200)
        self.assertEqual(result['right_minus_left'],0.);self.assertEqual(result['ci95'],[0.,0.]);self.assertEqual(result['root_groups'],2)

    def test_mismatch_or_unscored_cases_rejected(self):
        a=[dict(messages=['a'],gold='5',answer='5',exact_code_contract=True,
            meta=dict(kind='addition',language='en',semantic_root_id='r'),generation=dict(finish_reason='STOP'))]
        b=copy.deepcopy(a);b[0]['gold']='6'
        with self.assertRaises(ValueError):code.paired_roots(a,b,10)
        a[0]['exact_code_contract']=None
        with self.assertRaises(ValueError):code.summary(a)


if __name__=='__main__':unittest.main()
