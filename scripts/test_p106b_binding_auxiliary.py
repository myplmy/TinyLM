from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import copy
import unittest
from collections import defaultdict
from scripts import p106b_binding_auxiliary as code


class Contracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=[code.prior.correct_own_question(row) for row in code.prior.source.binding_rows('train',2)]
        cls.legal={code.prior.source.sha(row['messages']):copy.deepcopy(row['meta']) for row in cls.rows}

    def test_producer_only_and_unknown_not_inferred(self):
        row=copy.deepcopy(self.rows[0]);self.assertIn(code.binding_bit(row,self.legal),(0,1))
        row['messages'][0]['content'][0]['text']+=' changed'
        with self.assertRaises(ValueError):code.binding_bit(row,self.legal)
        row['meta']['kind']='expanded_grounded_qa'
        self.assertIsNone(code.binding_bit(row,self.legal))

    def test_root_flip_preserves_two_two_balance(self):
        values=defaultdict(list)
        for row in self.rows:
            root=row['meta']['semantic_root_id'];bit=code.binding_bit(row,self.legal)
            values[root].append(code.maybe_flip(bit,root,True))
        self.assertTrue(all(len(v)==4 and sum(v)==2 for v in values.values()))

    def test_unchanged_question_cannot_forge_source_order_metadata(self):
        row=copy.deepcopy(self.rows[0]);m=row['meta']
        m['ordered_entities'].reverse();m['first_value']=m['mapping'][m['ordered_entities'][0]]
        with self.assertRaises(ValueError):code.binding_bit(row,self.legal)

    def test_head_does_not_advance_rng(self):
        import torch
        before=torch.get_rng_state().clone();head=code.new_head(768)
        self.assertTrue(torch.equal(before,torch.get_rng_state()))
        self.assertEqual(sum(p.numel() for p in head.parameters()),1538)
        self.assertTrue(all(not bool(p.detach().any()) for p in head.parameters()))

    def test_first_predictor_position_and_no_unknown_label(self):
        import torch
        y=torch.tensor([[-100,-100,6,7,-100],[-100,4,5,-100,-100]])
        rows,positions=code.first_positions(y,[1,None])
        self.assertEqual((rows.tolist(),positions.tolist()),([0],[2]))
        with self.assertRaises(ValueError):code.first_positions(y,[0])

    def test_global_denominator_matches_split_microbatches(self):
        import torch
        torch.manual_seed(1)
        h=torch.randn(4,5,3,requires_grad=True);y=torch.tensor([[-100,1,2,3,-100]]*4)
        head=code.new_head(3)
        with torch.no_grad():head.weight.fill_(.03);head.weight[1].mul_(-1)
        labels=[0,1,None,0]
        total,n,_=code.auxiliary_sum(head,h,y,labels)
        whole=torch.autograd.grad(total/n,h,retain_graph=True)[0]
        parts=sum(code.auxiliary_sum(head,h[i:i+2],y[i:i+2],labels[i:i+2])[0]/n for i in (0,2))
        self.assertTrue(torch.allclose(whole,torch.autograd.grad(parts,h)[0]))

    def test_zero_coefficient_cannot_change_sft_gradient(self):
        import torch
        h=torch.randn(2,4,3,requires_grad=True);y=torch.tensor([[-100,1,2,-100]]*2);head=code.new_head(3)
        with torch.no_grad():head.weight.copy_(torch.randn_like(head.weight))
        aux,n,_=code.auxiliary_sum(head,h,y,[0,1]);sft=h.square().mean()
        self.assertGreater(float(torch.autograd.grad(aux,h,retain_graph=True)[0].abs().sum()),0.)
        a=torch.autograd.grad(sft+0*aux/n,h,retain_graph=True)[0]
        b=torch.autograd.grad(sft,h)[0]
        self.assertTrue(torch.equal(a,b))

    def test_first_target_cannot_read_later_answer_body(self):
        import torch
        from scripts.test_p101a_sft_mtp import tiny
        model,cfg=tiny(False);model.eval();torch.set_num_threads(1)
        a=torch.tensor([[1,2,3,4,5]]);b=a.clone();b[:,3:]=torch.tensor([[8,9]])
        with torch.no_grad():
            left=model(a,return_hidden=True);right=model(b,return_hidden=True)
        self.assertTrue(torch.equal(left[:,:3],right[:,:3]))

    def test_fresh_test_count_and_names(self):
        rows=code.prior.source.code_rows();result=code.fresh_test(rows)
        self.assertEqual(len(result),640)
        self.assertEqual(len({code.prior.source.sha(r['messages']) for r in result}),640)
        self.assertEqual(sum(r['meta'].get('target_is_first',False) for r in result[:512]),256)
        old=code.prior.fresh_test(rows)
        self.assertFalse({r['meta']['semantic_root_id'] for r in result}&{r['meta']['semantic_root_id'] for r in old})

    def test_consumer_rejects_oversized_or_empty_record_without_truncation(self):
        from types import SimpleNamespace
        from scripts import diag_p106b_binding_auxiliary as driver
        rows=[dict(meta=dict(kind='fixture'))]
        driver.validate_budget([SimpleNamespace(x_tokens=1024,targets=1)],rows)
        with self.assertRaises(ValueError):driver.validate_budget([SimpleNamespace(x_tokens=1025,targets=1)],rows)
        with self.assertRaises(ValueError):driver.validate_budget([SimpleNamespace(x_tokens=12,targets=0)],rows)

    def test_source_policy_is_software_input_wrapper_not_teacher_answer(self):
        from scripts import diag_p106b_binding_auxiliary as driver
        row=copy.deepcopy(self.rows[0]);row['meta'].update(kind='expanded_grounded_qa',rubric='CLARIFICATION_POSTHOC')
        original=copy.deepcopy(row);wrapped=driver.public_rows([row])[0]
        self.assertEqual(row,original)
        self.assertEqual(wrapped['messages'][-1],row['messages'][-1])
        self.assertTrue(wrapped['messages'][0]['content'][0]['text'].endswith(row['messages'][0]['content'][0]['text']))
        self.assertEqual(wrapped['meta']['rubric'],'UNSCORED_PUBLIC_QA')
        self.assertIsNone(code.binding_bit(wrapped,self.legal))
        again=driver.public_rows([wrapped])[0]
        self.assertEqual(again['messages'],wrapped['messages'])

    def test_public_budget_keeps_full_prompt_and_records_context_cap(self):
        from scripts import diag_p106b_binding_auxiliary as driver
        self.assertEqual(driver.generation_budget(600,1024),256)
        self.assertEqual(driver.generation_budget(900,1024),124)
        with self.assertRaises(ValueError):driver.generation_budget(1024,1024)

    def test_public_panel_is_source_stratified_and_order_independent(self):
        from scripts import diag_p106b_binding_auxiliary as driver
        rows=[dict(meta=dict(language=lang,course_family=family,
            semantic_root_id=code.prior.source.sha([lang,family,i])))
            for lang in ('ko','en') for family in ('a','b','c','d') for i in range(8)]
        a=driver.public_panel(rows);b=driver.public_panel(list(reversed(rows)))
        self.assertEqual(a,b);self.assertEqual(len(a),16)
        self.assertEqual(sum(r['meta']['language']=='ko' for r in a),8)

    def test_missing_prerequisite_is_hold_without_model(self):
        from unittest.mock import patch
        from contextlib import redirect_stdout
        from io import StringIO
        from scripts import diag_p106b_binding_auxiliary as driver
        captured=StringIO()
        with patch.object(sys,'argv',['diag','--mode','cost','--execute']),\
             patch.object(driver,'read_course',side_effect=driver.GateNegative('fixture prerequisite')),\
             patch.object(driver.base.training,'load_runtime') as loader,redirect_stdout(captured):
            self.assertEqual(driver.main(),8)
            loader.assert_not_called()
        self.assertIn('BINDING_AUX_HOLD',captured.getvalue())

    def test_suffix_waits_for_last_overlapping_character_token(self):
        from types import SimpleNamespace
        from tinylm.chat.serialize import serialize
        class Tokens:
            def encode(self,text):
                offsets=[(i,i+1) for i in range(len(text)) for _ in range(2)]
                return SimpleNamespace(ids=list(range(len(offsets))),offsets=offsets)
        row=self.rows[0];prompt=serialize(dict(messages=row['messages'][:-1]),'chatml',add_generation_prompt=True)
        end=prompt.rfind(row['meta']['requested_entity'])+len(row['meta']['requested_entity'])
        positions=code.causal_suffix_positions(row,Tokens(),len(prompt)*2-1)
        self.assertEqual(positions[0],end*2-1)
        self.assertEqual(positions[-1],len(prompt)*2-1)

    def test_first_mode_matches_original_loss_and_gradient(self):
        import torch
        h=torch.randn(2,7,3,requires_grad=True);y=torch.tensor([[-100,-100,-100,1,2,3,-100]]*2)
        head=code.new_head(3)
        with torch.no_grad():head.weight.copy_(torch.randn_like(head.weight))
        original,n,_=code.auxiliary_sum(head,h,y,[0,1])
        packed,count,correct,events=code.suffix_auxiliary_sum(head,h,y,[0,1],[[1,2,3],[2,3]],False)
        a=torch.autograd.grad(original,h,retain_graph=True)[0]
        b=torch.autograd.grad(packed,h,retain_graph=True)[0]
        self.assertTrue(torch.allclose(original,packed,atol=1e-7,rtol=1e-6))
        self.assertTrue(torch.allclose(a,b,atol=1e-7,rtol=1e-6))
        self.assertEqual((n,count,events),(2,2,5))
        with self.assertRaises(ValueError):code.suffix_auxiliary_sum(head,h,y,[0,1],[[1,2,3,4],[3]],True)
        with self.assertRaises(ValueError):code.suffix_auxiliary_sum(head,h,y,[None,1],[[3],[3]],True)

    def test_dense_objective_weights_rows_not_window_lengths(self):
        import torch
        h=torch.randn(2,7,3,requires_grad=True);y=torch.tensor([[-100,-100,-100,1,2,3,-100]]*2)
        head=code.new_head(3)
        with torch.no_grad():head.weight.copy_(torch.randn_like(head.weight))
        loss,n,_,events=code.suffix_auxiliary_sum(head,h,y,[0,1],[[1,2,3],[3]],True)
        a=torch.nn.functional.cross_entropy(head(h[0,1:4]),torch.zeros(3,dtype=torch.long))
        b=torch.nn.functional.cross_entropy(head(h[1,3:4]),torch.ones(1,dtype=torch.long))
        self.assertTrue(torch.allclose(loss/n,(a+b)/2));self.assertEqual(events,4)
        separate=sum(code.suffix_auxiliary_sum(head,h[i:i+1],y[i:i+1],[i],[[1,2,3] if i==0 else [3]],True)[0]/n
            for i in (0,1))
        self.assertTrue(torch.allclose(loss/n,separate))


if __name__=='__main__':unittest.main()
