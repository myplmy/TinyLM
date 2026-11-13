import unittest
from pathlib import Path
import torch
from scripts import diag_p106b_actd_determinism as d


class DeterminismContracts(unittest.TestCase):
    def test_cloned_runner_keeps_original_loss_cache_and_code_and_does_not_mutate_globals(self):
        before=d.old.run.__globals__['d'];runner=d.build_runner(Path('/tmp/actd_unused_contract'))
        self.assertIs(runner.__code__,d.old.run.__code__)
        self.assertIs(runner.__globals__['read_cache'],d.old.read_cache)
        self.assertIs(d.old.run.__globals__['d'],before)
        self.assertEqual(runner.__globals__['d'].BASE,Path('/tmp/actd_unused_contract'))
        self.assertNotEqual(before.BASE,runner.__globals__['d'].BASE)
    def test_detailed_comparison_preserves_original_tolerance_and_all_original_numeric_fields(self):
        a={'embedding':torch.tensor([1.,2.]),'head':torch.tensor([3.])}
        b={'embedding':torch.tensor([1.01,2.]),'head':torch.tensor([3.])}
        old=d.old.compare_gradients(torch,a,b);new=d.compare_gradients(torch,a,b)
        self.assertTrue(all(new[k]==v for k,v in old.items()));self.assertFalse(new['repeat_exact'])
        self.assertEqual(new['outside_parameters'][0]['parameter'],'embedding')
        self.assertEqual(new['outside_parameters'][0]['outside_tolerance'],1)
    def test_exact_replay_has_no_false_gradient_error_and_nonfinite_is_rejected(self):
        a={'x':torch.tensor([0.,1.,-1.])};r=d.compare_gradients(torch,a,{'x':a['x'].clone()})
        self.assertTrue(r['repeat_exact']);self.assertEqual(r['outside_tolerance'],0)
        with self.assertRaises(ValueError):d.compare_gradients(torch,a,{'x':torch.full((3,),float('nan'))})


if __name__=='__main__':unittest.main()
