"""Small CPU fixtures for paired-root readback; no experiment files or models."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import copy
import unittest
from scripts import summarize_p106b_learning_pair as code


def cases(correct):
    return [dict(messages=[dict(role='user',content=f'root{root} view{view}')],gold='red',
        answer='red' if correct else 'blue',exact_code_contract=correct,
        generation=dict(finish_reason='STOP'),meta=dict(language='en',kind='binding_color',
        semantic_root_id=str(root),first_value='red' if view%2==0 else 'blue'))
        for root in range(2) for view in range(4)]


class Readback(unittest.TestCase):
    def test_counts_and_quadruples(self):
        result=code.summarize(cases(True))['counts']
        self.assertEqual(result['exact'],8);self.assertEqual(result['all4_exact_roots'],2)
        self.assertEqual(result['first_value_baseline_binding'],4)
        with self.assertRaises(ValueError):code.summarize(cases(True)[:-1])

    def test_identical_and_total_gain(self):
        equal=code.paired_interval(cases(True),cases(True),100)
        gain=code.paired_interval(cases(False),cases(True),100)
        self.assertEqual(equal['ci95'],[0.,0.]);self.assertEqual(gain['ci95'],[1.,1.])
        self.assertEqual(gain['right_minus_left'],1.)

    def test_mismatch_and_unscored_rejected(self):
        a=cases(True);b=copy.deepcopy(a);b[0]['gold']='different'
        with self.assertRaises(ValueError):code.paired_interval(a,b,100)
        a[0]['exact_code_contract']=None
        with self.assertRaises(ValueError):code.summarize(a)


if __name__=='__main__':unittest.main()
