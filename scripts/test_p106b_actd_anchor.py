import copy
import unittest
import torch
from scripts import p106b_actd_anchor as a


class AnchorLossContracts(unittest.TestCase):
    def test_full_normalizer_and_unique_residual_match_independent_softmax(self):
        z=torch.tensor([[.2,-.3,1.1,.8]],dtype=torch.float64,requires_grad=True)
        ids=torch.tensor([[1,3]]);t=torch.log(torch.tensor([[.7,.3]],dtype=torch.float64))
        r=a.actd_sums(z,ids,t,residual_weight=1.)
        p=z.softmax(-1);expected=(p[:,[1,3]]-t.exp()).abs().sum()+p[:,[0,2]].sum()
        torch.testing.assert_close(r['loss_sum'],expected,atol=1e-14,rtol=1e-14)
        torch.testing.assert_close(torch.autograd.grad(r['loss_sum'],z,retain_graph=True)[0],
                                   torch.autograd.grad(expected,z)[0],atol=1e-14,rtol=1e-14)
        self.assertLess(float(r['anchor_probabilities'].sum()),1.)

    def test_duplicate_edges_are_literal_not_merged_probability_mass(self):
        z=torch.tensor([[.4,-.2]],dtype=torch.float64,requires_grad=True)
        ids=torch.tensor([[0,0]]);t=torch.log(torch.tensor([[.6,.4]],dtype=torch.float64))
        r=a.actd_sums(z,ids,t,residual_weight=1.)
        p=z.softmax(-1);literal=(p[0,0]-.6).abs()+(p[0,0]-.4).abs()+p[0,1]
        merged=(p[0,0]-1.).abs()+p[0,1]
        torch.testing.assert_close(r['loss_sum'],literal)
        self.assertNotAlmostEqual(float(r['loss_sum']),float(merged))
        self.assertEqual(r['unique_anchor_count'].tolist(),[1]);self.assertEqual(r['duplicate_anchor_edges'].tolist(),[1])

    def test_gradcheck_covers_full_vocabulary_not_only_anchor_gradients(self):
        torch.manual_seed(7113);z=torch.randn(2,5,dtype=torch.float64,requires_grad=True)
        ids=torch.tensor([[1,3],[2,2]]);t=torch.tensor([[.1,-1.],[.8,-.5]],dtype=torch.float64)
        self.assertTrue(torch.autograd.gradcheck(lambda x:a.actd_sums(x,ids,t,residual_weight=.7)['loss_sum'],(z,)))
        g=torch.autograd.grad(a.actd_sums(z,ids,t,residual_weight=.7)['loss_sum'],z)[0]
        self.assertTrue(bool(g[:,[0,4]].ne(0).all()))

    def test_all_vocabulary_anchored_has_exact_finite_zero_residual_gradient(self):
        z=torch.tensor([[.3,-.8]],dtype=torch.float64,requires_grad=True)
        r=a.actd_sums(z,torch.tensor([[0,1,0]]),torch.tensor([[.1,.0,-.1]]),residual_weight=1.)
        self.assertEqual(float(r['residual_sum']),0.)
        g=torch.autograd.grad(r['residual_sum'],z,retain_graph=True)[0]
        self.assertTrue(bool(torch.isfinite(g).all()));self.assertTrue(bool(g.eq(0).all()))
        self.assertTrue(bool(torch.isfinite(torch.autograd.grad(r['loss_sum'],z)[0]).all()))

    def test_large_finite_margin_and_empty_supervision_stay_finite(self):
        for margin in [100.,1000.]:
            z=torch.tensor([[margin,-margin,0.]],requires_grad=True)
            r=a.actd_sums(z,torch.tensor([[0,1]]),torch.tensor([[0.,-10.]]),residual_weight=1.)
            self.assertTrue(bool(torch.isfinite(r['loss_sum'])));self.assertTrue(bool(torch.isfinite(torch.autograd.grad(r['loss_sum'],z)[0]).all()))
        z=torch.empty(0,5,requires_grad=True)
        r=a.actd_sums(z,torch.empty(0,0,dtype=torch.long),torch.empty(0,0),residual_weight=1.)
        self.assertEqual(r['positions'],0);self.assertEqual(float(r['loss_sum']),0.)
        self.assertEqual(torch.autograd.grad(r['loss_sum'],z)[0].shape,z.shape)

    def test_sum_contract_preserves_global_position_denominator(self):
        z=torch.tensor([[.1,1.,-.5],[.9,-.1,.4]],dtype=torch.float64,requires_grad=True)
        ids=torch.tensor([[0,1],[1,2]]);t=torch.tensor([[0.,-.5],[0.,-.2]])
        full=a.actd_sums(z,ids,t,residual_weight=1.)['loss_sum']/2
        pieces=sum(a.actd_sums(z[i:i+1],ids[i:i+1],t[i:i+1],residual_weight=1.)['loss_sum']/2 for i in range(2))
        torch.testing.assert_close(full,pieces)

    def test_half_input_promotes_reductions_and_retains_student_gradient(self):
        z=torch.tensor([[1.,2.,3.]],dtype=torch.bfloat16,requires_grad=True)
        r=a.actd_sums(z,torch.tensor([[0,2]]),torch.tensor([[0.,-.5]]),residual_weight=1.)
        self.assertEqual(r['loss_sum'].dtype,torch.float32)
        self.assertTrue(bool(torch.isfinite(torch.autograd.grad(r['loss_sum'],z)[0]).all()))

    def test_invalid_ids_nonfinite_teacher_gradient_and_weights_fail_closed(self):
        z=torch.zeros(1,3);ids=torch.tensor([[0,1]]);t=torch.zeros(1,2)
        for zz,ii,tt,w in [(z,torch.tensor([[0,3]]),t,1.),(z,ids,t.clone().requires_grad_(),1.),
                            (z,ids,torch.tensor([[0.,float('nan')]]),1.),(z,ids,t,-1.),(z,ids,t,True),
                            (torch.tensor([[0.,float('inf'),1.]]),ids,t,1.)]:
            with self.assertRaises(a.AnchorContractError):a.actd_sums(zz,ii,tt,residual_weight=w)


class AnchorMappingContracts(unittest.TestCase):
    def mapper(self,extra=None,encode=None):
        pieces={0:b'cat',1:b'sleep',2:b'ing',3:bytes([227]),4:b' '}
        if extra:pieces.update(extra)
        return a.AnchorMapper(pieces,8,encode or (lambda text:[1,2]),teacher_special_ids={99,100},special_map={99:7})

    def test_exact_shared_bytes_and_first_subtoken_preserve_native_ids(self):
        ids=[41,42];pieces=[b'cat',b'sleeping'];before=copy.deepcopy((ids,pieces))
        r=self.mapper().map(ids,pieces)
        self.assertEqual([v['anchor_id'] for v in r],[0,1]);self.assertEqual(r[1]['retokenized_ids'],[1,2])
        self.assertEqual((ids,pieces),before)

    def test_explicit_special_and_shared_partial_byte_are_distinct(self):
        r=self.mapper().map([99,43],[None,bytes([227])])
        self.assertEqual([v['anchor_id'] for v in r],[7,3])
        with self.assertRaises(a.AnchorMappingHold):self.mapper().map([100],[None])

    def test_unshared_partial_utf8_and_ambiguous_shared_token_are_hold(self):
        with self.assertRaises(a.AnchorMappingHold):self.mapper().map([45],[bytes([227,130])])
        with self.assertRaises(a.AnchorMappingHold):self.mapper({5:b'cat'}).map([45],[b'cat'])

    def test_automatic_bos_normalization_and_duplicate_teacher_ids_are_rejected(self):
        for enc in [lambda text:[7,1,2],lambda text:[1],lambda text:[]]:
            with self.assertRaises(a.AnchorMappingHold):self.mapper(encode=enc).map([44],[b'sleeping'])
        with self.assertRaises(a.AnchorContractError):self.mapper().map([44,44],[b'cat',b'cat'])

    def test_unicode_character_positions_are_not_byte_counts(self):
        self.assertEqual(a.character_boundaries('가ab',[0,3,4,5]),[0,1,2,3])
        with self.assertRaises(a.AnchorMappingHold):a.character_boundaries('가ab',[1])
        with self.assertRaises(a.AnchorContractError):a.character_boundaries('가ab',[4,3])

    def test_nearest_tie_uses_earlier_boundary_and_reports_future(self):
        teacher=[(2,1,1),(6,1,2)]
        r=a.align_prefix_boundaries([(4,1,3),(5,1,4)],teacher,policy='nearest_monotonic')
        self.assertEqual([v['teacher_prefix_raw_index'] for v in r],[1,2])
        self.assertEqual([v['lookahead_characters'] for v in r],[0,1])
        left=a.align_prefix_boundaries([(4,1,3),(5,1,4)],teacher,policy='causal_left_variant')
        self.assertEqual([v['teacher_prefix_raw_index'] for v in left],[1,1])

    def test_same_teacher_prefix_may_supervise_multiple_student_positions_without_reshifting(self):
        r=a.align_prefix_boundaries([(3,1,2),(4,1,3)],[(4,1,5)],policy='nearest_monotonic')
        self.assertEqual([v['teacher_prefix_raw_index'] for v in r],[5,5])
        self.assertEqual([v['student_prefix_raw_index'] for v in r],[2,3])

    def test_owners_unknown_policy_and_missing_left_prefix_fail_closed(self):
        for student,teacher,policy in [([(1,1,2)],[(1,2,2)],'nearest_monotonic'),
                ([(1,1,2)],[(2,1,2)],'causal_left_variant'),
                ([(1,0,2)],[(1,1,2)],'nearest_monotonic'),
                ([(2,1,2),(1,1,3)],[(2,1,2)],'nearest_monotonic'),
                ([(1,1,2)],[(1,1,2)],'implicit')]:
            with self.assertRaises(a.AnchorContractError):a.align_prefix_boundaries(student,teacher,policy=policy)


if __name__=='__main__':unittest.main()
