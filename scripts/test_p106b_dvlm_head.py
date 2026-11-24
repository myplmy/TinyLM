"""Shared byte rows, unsupported UTF8, full means and detached head-only CE."""
import unittest

from scripts import p106b_dvlm_head as core
from scripts.p106b_dvlm_pts import AdmissionHold


def raw(vocab,added=()):
    return dict(model=dict(type='BPE',vocab=vocab),decoder=dict(type='ByteLevel'),added_tokens=list(added))


def example_map():
    student=raw({'a':0,'\u00c3':1,'bc':2})
    teacher=raw({'a':0,'\u00c3':1,'b':2,'c':3})
    def decode_student(ids):
        return ''.join({0:'a',2:'bc'}[i] for i in ids)
    def encode_teacher(text):
        return [{'a':0,'b':2,'c':3}[letter] for letter in text]
    def decode_teacher(ids):
        return ''.join({0:'a',2:'b',3:'c'}[i] for i in ids)
    return core.initialization_map(student,teacher,decode_student=decode_student,
        encode_teacher=encode_teacher,decode_teacher=decode_teacher)


class HeadContracts(unittest.TestCase):
    def test_shared_raw_byte_fragment_copies_without_lossy_standalone_decode(self):
        mapping=example_map()
        self.assertTrue(mapping['complete'])
        self.assertEqual(mapping['counts'],{'SHARED_NATIVE_PIECE':2,'MEAN_RETOKENIZED':1})
        self.assertEqual(mapping['records'][1]['teacher_ids'],[1])
        self.assertEqual(mapping['records'][2]['teacher_ids'],[2,3])

    def test_unmatched_invalid_utf8_row_is_hold_and_not_random_fill(self):
        mapping=core.initialization_map(raw({'\u00c2':0}),raw({'a':0}),
            decode_student=lambda _:self.fail('do not decode an unmatched byte fragment'),
            encode_teacher=lambda _:self.fail('do not encode an invalid UTF8 fragment'),decode_teacher=lambda _:'a')
        self.assertFalse(mapping['complete'])
        with self.assertRaisesRegex(AdmissionHold,'before head allocation'):
            core.initialize_head(None,None,mapping)

    def test_added_token_properties_are_not_silently_treated_as_shared(self):
        vocab={'a':0,'b':1,'EOS':2}
        mapping=core.initialization_map(raw(vocab,[dict(id=2,content='EOS',special=True)]),
            raw(vocab,[dict(id=2,content='EOS',special=False)]),decode_student=lambda _:'EOS',
            encode_teacher=lambda _:[2],decode_teacher=lambda _:'EOS')
        self.assertEqual(mapping['records'][2]['method'],'MEAN_RETOKENIZED')

    def test_all_initialized_rows_match_independent_fp64_means(self):
        import torch
        teacher=torch.arange(20,dtype=torch.float32).reshape(4,5).requires_grad_()
        before=teacher.detach().clone();mapping=example_map()
        head=core.initialize_head(torch,teacher,mapping,chunk_rows=2)
        self.assertTrue(core.independent_row_oracle(torch,head,teacher,mapping,atol=0.,rtol=0.)['passed'])
        self.assertTrue(torch.equal(head.detach()[2],(teacher.detach()[2]+teacher.detach()[3])/2))
        self.assertTrue(torch.equal(teacher.detach(),before))
        self.assertIsNone(teacher.grad)

    def test_head_backward_keeps_teacher_and_hidden_unmodified(self):
        import torch
        teacher=torch.arange(20,dtype=torch.float32).reshape(4,5).requires_grad_()
        hidden=torch.tensor([[.1,.2,.3,.4,.5],[.5,.4,.3,.2,.1]],requires_grad=True)
        head=core.initialize_head(torch,teacher,example_map())
        before=head.detach().clone()
        report=core.head_gradient_probe(torch,head,hidden,[2,-100])
        self.assertEqual(report['supervised_targets'],1)
        self.assertTrue(report['finite'])
        self.assertTrue(report['gradient_nonzero'])
        self.assertIsNone(teacher.grad)
        self.assertIsNone(hidden.grad)
        self.assertTrue(torch.equal(head.detach(),before))
        self.assertEqual(report['optimizer_updates'],0)

    def test_sparse_student_vocabulary_is_not_claimed_as_a_complete_head(self):
        with self.assertRaisesRegex(AdmissionHold,'dense student head'):
            core.initialization_map(raw({'a':1}),raw({'a':0}),decode_student=lambda _:'a',
                encode_teacher=lambda _:[0],decode_teacher=lambda _:'a')


if __name__=='__main__':unittest.main()
