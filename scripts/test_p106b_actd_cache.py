import copy
import math
import unittest
import torch
from scripts import p106b_actd_cache as c
from scripts import p106b_actd_anchor as a
from scripts.p106b_alm_bytes import build_teacher_stream


class ACTDCacheContracts(unittest.TestCase):
    def test_predictor_is_exactly_one_before_target_and_partial_utf8_is_held(self):
        stream=build_teacher_stream('가X',[10,11,12],[[234],[176,128],[88]],
            supervised=[False,True,True],turn_ids=[0,1,1])
        positions,holds=c.prefix_candidates(stream)
        self.assertEqual(len(holds),1);self.assertEqual(holds[0]['target_raw_index'],1)
        self.assertEqual(positions[0]['prefix_raw_index'],1)
        self.assertEqual(positions[0]['target_raw_index'],2);self.assertEqual(positions[0]['character_end'],1)

    def test_alignment_reports_future_and_never_crosses_owner(self):
        s=[dict(character_end=1,owner=1,prefix_raw_index=2,target_raw_index=3,target_id=9),
           dict(character_end=4,owner=2,prefix_raw_index=5,target_raw_index=6,target_id=8)]
        t=[dict(character_end=2,owner=1,prefix_raw_index=1,target_raw_index=2,target_id=7),
           dict(character_end=4,owner=1,prefix_raw_index=3,target_raw_index=4,target_id=7)]
        r,h=c.align_positions(s,t,policy='nearest_monotonic')
        self.assertEqual(len(r),1);self.assertEqual(r[0]['lookahead_characters'],1);self.assertEqual(len(h),1)
        r,h=c.align_positions(s,t,policy='causal_left_variant');self.assertEqual(r,[]);self.assertEqual(len(h),2)

    def test_literal_added_false_is_decoded_not_collapsed_to_semantic_control(self):
        mapper=a.AnchorMapper({0:b'<',1:b'think',2:b'>'},4,lambda s:[0,1,2],teacher_special_ids={10},special_map={10:3})
        raw={'added_tokens':[dict(id=9,content='<think>',special=False),dict(id=10,content='EOS',special=True)]}
        r=c.literal_added_overrides(raw,lambda i:'<think>',mapper,[None]*11)
        self.assertEqual(r[0]['anchor_id'],0);self.assertNotEqual(r[0]['anchor_id'],3)
        with self.assertRaises(ValueError):c.literal_added_overrides(raw,lambda i:'changed',mapper,[None]*11)

    def test_topk_uses_full_logits_without_forced_gold_or_finite_repair(self):
        x=torch.tensor([[5.,2.,-3.,1.]])
        ids,scores,z=c.native_topk(x,k=2)
        self.assertEqual(ids.tolist(),[[0,1]]);self.assertTrue(torch.equal(scores,x[:,[0,1]]))
        self.assertTrue(torch.equal(z,torch.logsumexp(x,dim=-1)))
        for bad in [x.half(),torch.tensor([[float('nan'),1.]])]:
            with self.assertRaises(ValueError):c.native_topk(bad,k=2)

    def distribution(self,anchors=None):
        return c.distribution([2,1],[3.,2.],math.log(math.exp(3)+math.exp(2)+1),
            anchor_lookup=anchors or [0,1,1],student_vocab=3,k=2)

    def test_duplicate_student_anchors_retained_and_missing_edge_holds_whole_row(self):
        r=self.distribution();self.assertEqual(r['anchor_ids'],[1,1]);self.assertEqual(r['duplicate_anchor_edges'],1)
        r=self.distribution([0,None,1]);self.assertFalse(r['accepted']);self.assertIsNone(r['anchor_ids'])
        self.assertEqual(r['native_ids'],[2,1]);self.assertEqual(r['native_logits'],[3.,2.])
        self.assertEqual(r['unmapped_native_ids'],[1])

    def test_topk_malformed_contracts_are_rejected(self):
        for ids,scores,z in [([2,2],[3.,2.],4.),([2,1],[2.,3.],4.),([2,1],[3.,float('inf')],4.),
                              ([2,1],[3.,2.],2.),([2,7],[3.,2.],4.),([2],[3.],4.)]:
            with self.assertRaises(ValueError):c.distribution(ids,scores,z,anchor_lookup=[0,1,1],student_vocab=3,k=2)

    def test_acceptance_accounts_original_ce_without_silent_subset_changes(self):
        p=dict(teacher_prefix_union=[4],student_boundary_holds=[],ce_targets=1,
            alignment_holds={name:[] for name in c.POLICIES},
            alignments={name:[dict(teacher_prefix_raw_index=4,student_prefix_raw_index=6)] for name in c.POLICIES})
        d=self.distribution();rows,holds=c.accepted_positions(p,{4:d},policy=c.POLICIES[0],k=2,anchor_lookup=[0,1,1],student_vocab=3)
        self.assertEqual((len(rows),len(holds)),(1,0))
        bad=copy.deepcopy(d);bad['anchor_ids']=[0,0]
        with self.assertRaises(ValueError):c.accepted_positions(p,{4:bad},policy=c.POLICIES[0],k=2,anchor_lookup=[0,1,1],student_vocab=3)
        with self.assertRaises(ValueError):c.accepted_positions(p,{},policy=c.POLICIES[0],k=2,anchor_lookup=[0,1,1],student_vocab=3)


if __name__=='__main__':unittest.main()
