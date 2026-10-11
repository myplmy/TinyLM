"""CPU algebraic nullspace controls; no checkpoint/model/tokenizer IO."""
import unittest
import torch
from scripts.p093b_similarity_control import head_basis,reflect,cosine


class SimilarityTests(unittest.TestCase):
    def test_reflection_preserves_norm_and_complete_factorized_readout(self):
        torch.manual_seed(1337)
        w=torch.randn(12,4);embedding=torch.randn(31,4);x=torch.randn(12)
        q,_=head_basis(w,torch.tensor(4.))
        y,s=reflect(x,q)
        a=embedding@(w.T@(x*4/x.square().mean().sqrt()))
        b=embedding@(w.T@(y*4/y.square().mean().sqrt()))
        self.assertLess(float((a-b).abs().max()),1e-4)
        self.assertLess(s["norm_relative_difference_fp64"],1e-12)
        self.assertLess(s["visible_projection_max_difference_fp64"],1e-12)
        self.assertAlmostEqual(cosine(x,y),1-2*s["null_energy_fraction"],places=6)

    def test_per_channel_scale_is_part_of_readout_basis(self):
        torch.manual_seed(1);w=torch.randn(12,4);scale=torch.rand(12)+.5;x=torch.randn(12)
        q,_=head_basis(w,scale);y,_=reflect(x,q)
        a=w.T@(x*scale/x.norm());b=w.T@(y*scale/y.norm())
        self.assertLess(float((a-b).abs().max()),1e-5)

    def test_square_head_has_no_reserved_nullspace_claim(self):
        with self.assertRaises(ValueError):head_basis(torch.eye(4),1.)

    def test_zero_and_wrong_vectors_rejected(self):
        with self.assertRaises(ValueError):cosine(torch.zeros(4),torch.zeros(4))
        q,_=head_basis(torch.randn(8,3),1.)
        with self.assertRaises(ValueError):reflect(torch.zeros(4),q)

    def test_zero_null_component_is_noop_not_evidence_of_cosine_reduction(self):
        q,_=head_basis(torch.randn(8,3),1.)
        x=(q@torch.tensor([1.,2.,3.],dtype=torch.float64)).float()
        y,s=reflect(x,q)
        self.assertLess(s["null_energy_fraction"],1e-12)
        self.assertGreater(cosine(x,y),.999999)


if __name__=="__main__":unittest.main(verbosity=2)
