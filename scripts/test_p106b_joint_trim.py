from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import copy
import unittest
from scripts import diag_p106b_joint_trim as code


class Trim(unittest.TestCase):
    def test_right_only_and_native_width_preserved(self):
        from tinylm.train.mtp_sft import Record
        a=Record([1,2],[-100,3],[0,1]);b=Record([1]*1024,[2]*1024,[1]*1024)
        self.assertEqual(tuple(code.trimmed_pad([a],0,fixed_width=1024,batch_size=8)[0].shape),(8,128))
        self.assertEqual(tuple(code.trimmed_pad([b],0,fixed_width=1024,batch_size=8)[0].shape),(8,1024))

    def test_source_metadata_not_overwritten(self):
        old=dict(tag='old',code_sha256={'producer':'hash'},labels={'x':dict(bit=1)})
        before=copy.deepcopy(old);info=dict(code_sha256={'runner':'new'},execution_padding='RIGHT_ONLY',source_dataset_report_sha256='input')
        new=code.adapted_course(old,info)
        self.assertEqual(old,before);self.assertEqual(new['source_producer_code_sha256'],old['code_sha256'])
        self.assertEqual(new['code_sha256'],info['code_sha256']);self.assertEqual(new['labels'],old['labels'])

    def test_scope_restores_global_callbacks(self):
        from tinylm.train import mtp_sft as core
        original=core.pad_records;tag=code.source.TAG;old_read=code.source.read_course
        old=dict(code_sha256={'producer':'hash'});info=dict(code_sha256={'runner':'new'},execution_padding='RIGHT_ONLY',source_dataset_report_sha256='input')
        with code.execution_scope(old,{'train':[]},info):
            self.assertEqual(code.source.TAG,code.TAG);self.assertIs(core.pad_records,code.trimmed_pad)
            self.assertEqual(code.source.read_course()[0]['source_producer_code_sha256'],old['code_sha256'])
        self.assertEqual(code.source.TAG,tag);self.assertIs(code.source.read_course,old_read);self.assertIs(core.pad_records,original)

    def test_auxiliary_objective_same_valid_hidden_under_padding(self):
        import torch
        torch.manual_seed(15);h=torch.randn(2,8,3);base=torch.nn.Linear(3,34)
        y=torch.tensor([[-100,1,2,-100,-100,3,4,-100],[-100,-100,-100,1,2,-100,-100,-100]])
        values=[]
        for width in (8,32):
            hidden=torch.cat((h,torch.zeros(2,width-8,3)),dim=1).requires_grad_();labels=torch.nn.functional.pad(y,(0,width-8),value=-100)
            head=copy.deepcopy(base);loss,n,_,events=code.source.method.objective(head,hidden,labels,[1,1217],[[5],[3]],beta=1.)
            loss.backward();values.append((float(loss.detach()),hidden.grad[:,:8].clone(),head.weight.grad.clone(),n,events))
            self.assertEqual(float(hidden.grad[:,8:].abs().sum()),0.)
        self.assertEqual(values[0][0],values[1][0]);self.assertTrue(torch.equal(values[0][1],values[1][1]));self.assertTrue(torch.equal(values[0][2],values[1][2]))


if __name__=='__main__':unittest.main()
