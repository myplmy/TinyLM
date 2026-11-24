import unittest
import numpy as np
from scripts import p108e_policy as study


class ProbeSelectionContracts(unittest.TestCase):
    def row(self,questions,hinge,guard=0,norm=1.):
        return dict(score=dict(questions_all_gold=questions,mean_hinge=hinge),
                    guard_argmax_mismatches=guard,guard_logit_max_error=0.,actual_norm=norm,alpha=1.,layer=0)

    def test_normal_harm_cannot_win_by_target_score(self):
        current=self.row(0,1.)
        bad=self.row(24,0.,guard=1);good=self.row(1,.5)
        selected,reason=study.select([bad,good],current,budget=2.)
        self.assertIs(selected,good)

    def test_tiny_hinge_change_is_not_resolved_progress(self):
        current=self.row(1,.2);noise=self.row(1,.2-1e-7)
        selected,reason=study.select([noise],current,budget=2.)
        self.assertIsNone(selected)

    def test_interpolation_does_not_reset_other_layers(self):
        current={0:np.array([.5]),1:np.array([.3])};proposal={0:np.array([.8]),1:np.array([.3])}
        result=study.mix(current,proposal,.5)
        np.testing.assert_array_equal(result[1],current[1]);self.assertAlmostEqual(result[0][0],.65)

    def test_path_can_grow_while_net_returns_to_zero(self):
        first={0:np.zeros((2,2))};middle={0:np.ones((2,2))}
        self.assertAlmostEqual(study.physical_path(first,middle)+study.physical_path(middle,first),4.)
        self.assertAlmostEqual(study.physical_path(first,first),0.)

    def test_lossless_after_patch_preserves_exact_fp32_bits(self):
        before=np.array([[0.,-0.,.1],[-3.,1e-12,2.]],np.float32)
        after=before.copy();after[0,1]=1e-7;after[1,0]+=1e-3
        encoded=study.after_xor(before,after);restored=study.restore_xor(before,encoded)
        np.testing.assert_array_equal(restored.view(np.uint32),after.view(np.uint32))
        self.assertFalse(np.shares_memory(before,restored))


if __name__=="__main__":unittest.main()
