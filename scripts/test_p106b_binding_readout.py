from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import copy
import unittest
from scripts import diag_p106b_binding_readout as code


class Paired(unittest.TestCase):
    def test_bit_requires_known_code_mapping_and_actual_gold(self):
        from scripts.p106b_retention_course import binding_rows
        rows=binding_rows('test',1);self.assertEqual(sum(code.known_bit(r) for r in rows),8)
        bad=copy.deepcopy(rows[0]);bad['messages'][-1]['content'][0]['text']='forged'
        with self.assertRaises(ValueError):code.known_bit(bad)
        bad=copy.deepcopy(rows[0]);bad['meta']['kind']='public_qa'
        with self.assertRaises(ValueError):code.known_bit(bad)

    def test_paired_cases_do_not_equate_bit_and_free_success(self):
        rows=[dict(root='root',language='ko',kind='binding_color',bit=i%2,prediction=i%2,free_exact=i<2)
            for i in range(4)]
        result=code.contingency(rows)['counts']
        self.assertEqual(result['bit_correct'],4);self.assertEqual(result['free_correct'],2)
        self.assertEqual(result['bit_1_free_0'],2);self.assertEqual(result['bit_all4_exact_roots'],1)
        with self.assertRaises(ValueError):code.contingency(rows[:-1])
        rows[0]['free_exact']=None
        with self.assertRaises(ValueError):code.contingency(rows)


if __name__=='__main__':unittest.main()
