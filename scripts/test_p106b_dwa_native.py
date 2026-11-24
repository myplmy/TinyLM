"""Once-shifted predictor cache and unequal-row global gradients; no model."""
import unittest
from scripts.p106b_dwa_native import predictor_view,streaming_share,close_accounting,AdmissionHold
from scripts.p106b_dwa_cma import native_next_view,update_loss

class NativeDWABoundaryContracts(unittest.TestCase):
    def test_predictor_only_cache_matches_full_native_view_at_nonprefix_targets(self):
        import torch
        ids=[1,2,3,4,5];mask=[False,False,True,False,True]
        h=torch.arange(12,dtype=torch.float64).reshape(4,3)
        embedding=torch.nn.Embedding(6,3,dtype=torch.float64)
        actual=predictor_view(torch,ids,mask,h,embedding)
        full=native_next_view(torch,ids,mask,torch.cat((h,torch.full((1,3),1e30))),embedding)
        self.assertEqual(actual.prediction_positions,(1,3));self.assertEqual(actual.target_positions,(2,4))
        self.assertTrue(torch.equal(actual.hidden,full.hidden));self.assertTrue(torch.equal(actual.targets,full.targets))

    def test_already_shifted_or_short_mask_and_hidden_are_refused(self):
        import torch
        embedding=torch.nn.Embedding(6,3)
        for ids,mask,h in [([1,2,3],[False,True],torch.ones(2,3)),
            ([1,2,3],[False,True,True],torch.ones(3,3))]:
            with self.assertRaises(AdmissionHold):predictor_view(torch,ids,mask,h,embedding)

    def test_all_student_and_teacher_positions_are_counted_without_alignment_filter(self):
        rows=[dict(row_id='a',student_count=3,teacher_count=5),dict(row_id='b',student_count=2,teacher_count=4)]
        self.assertEqual(close_accounting(rows,expected_ids=['a','b'],student_targets=5,teacher_targets=9)['rows'],2)
        with self.assertRaises(AdmissionHold):close_accounting(rows[:1],expected_ids=['a','b'],student_targets=5,teacher_targets=9)

    def test_streamed_unequal_rows_preserve_the_complete_update_value_and_gradient(self):
        import torch
        z=torch.tensor(1.7,dtype=torch.float64,requires_grad=True)
        packets=[]
        for n in (2,5):
            raw={key:z.square()*float(n+i) for i,key in enumerate(
                ('student_ce','projector_ce','student_kd','teacher_kd','dtw_hidden','dtw_embedding'))}
            packets.append(dict(raw=raw,student_count=n))
        a=sum(streaming_share(p,global_student_targets=7) for p in packets)
        b=update_loss(packets,global_student_targets=7)
        ga=torch.autograd.grad(a,z,retain_graph=True)[0];gb=torch.autograd.grad(b,z)[0]
        self.assertTrue(torch.allclose(a,b,atol=1e-12,rtol=1e-12))
        self.assertTrue(torch.allclose(ga,gb,atol=1e-12,rtol=1e-12))

    def test_partial_update_cannot_close_or_claim_a_row_mean(self):
        rows=[dict(row_id='a',student_count=3,teacher_count=3)]
        with self.assertRaises(AdmissionHold):close_accounting(rows,expected_ids=['a'],student_targets=772,teacher_targets=811)
        packet=dict(student_count=3,raw={})
        with self.assertRaises(AdmissionHold):streaming_share(packet,global_student_targets=2)

if __name__=='__main__':unittest.main()
