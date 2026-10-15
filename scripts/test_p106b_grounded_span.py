#!/usr/bin/env python3
"""CPU-only contract regressions. No project source files or model weights opened."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import copy
import unittest
from scripts import p106b_grounded_span as m


def source(ko=False):
    from tinylm.chat.canonical import normalize
    reference=('미래시는 가상 도시입니다. 지아의 역할은 사서입니다. 다음 설명은 연습용 기록이며 실제 인물과 관계가 없습니다. '*5 if ko else
        'An imaginary town has a library. Amy works as its librarian. The following record is fictional and is used only for a test. '*5)
    # Unique target, but a long reference with a separate repeated background.
    reference=('기록상 건물 이름은 누리관입니다. ' if ko else 'The recorded building name is Nuri Hall. ')+reference
    question='건물 이름은 무엇입니까?' if ko else 'What is the building name?'
    return normalize(dict(messages=[dict(role='user',content=reference+'\n1. '+question+'\n2. Another question?'),
        dict(role='assistant',content='1. 누리관\n2. 기타' if ko else '1. Nuri Hall\n2. other')],
        meta=dict(source='p106b_public_direct',selection_family='Flan-Coqa',language='ko' if ko else 'en',parent_concept_id='A'*64,source_split='train')))


class Contract(unittest.TestCase):
    def test_first_pair_exact_source(self):
        row=source();before=copy.deepcopy(row);p=m.first_pair(row)
        self.assertEqual(p['answer'],'Nuri Hall');self.assertEqual(row,before)
        self.assertEqual(p['reference'][slice(*p['answer_reference_range'])],p['answer'])
        self.assertNotIn('Another question',p['question']);self.assertNotIn('1. ',p['reference'])

    def test_declared_family_only(self):
        row=source();row['meta']['selection_family']='Dolly-v2'
        with self.assertRaises(ValueError):m.first_pair(row)

    def test_duplicate_markers_rejected(self):
        row=source();row['messages'][0]['content'][0]['text']+=' 1. repeated'
        with self.assertRaises(ValueError):m.first_pair(row)

    def test_repeated_or_absent_target_rejected(self):
        for replacement in ('Nuri Hall and Nuri Hall. ','No named building. '):
            row=source();row['messages'][0]['content'][0]['text']=replacement+row['messages'][0]['content'][0]['text'].replace('Nuri Hall','elsewhere')
            with self.assertRaises(ValueError):m.first_pair(row)

    def test_korean_inline(self):
        row=source(True);row['messages'][0]['content'][0]['text']=row['messages'][0]['content'][0]['text'].replace('\n',' ')
        row['messages'][1]['content'][0]['text']=row['messages'][1]['content'][0]['text'].replace('\n',' ')
        pair=m.first_pair(row);self.assertEqual(pair['answer'],'누리관')

    def test_wrapper_preserves_exact_source(self):
        row=source();p=m.first_pair(row);out=m.wrap(row,p,'dev');u=m.text(out['messages'][0])
        self.assertEqual(u[slice(*out['meta']['user_reference_range'])],p['reference'])
        self.assertEqual(u[slice(*out['meta']['user_answer_range'])],p['answer'])
        self.assertFalse(out['meta']['inference_uses_auxiliary'])

    def test_passage_overlap_ignores_space_layout(self):
        words=' '.join('item'+str(i) for i in range(50))
        self.assertTrue(m.passage_keys(words)&m.passage_keys('prefix '+words.replace(' ','\n')))

    def test_rng_preserved(self):
        import torch
        torch.manual_seed(123);before=torch.random.get_rng_state();m.new_head(8,rank=4)
        self.assertTrue(torch.equal(before,torch.random.get_rng_state()))

    def test_positive_and_zero_gradients(self):
        import torch
        for weight in (0.,.3):
            head=m.new_head(8,rank=4);hidden=torch.randn(2,12,8,requires_grad=True)
            labels=[dict(query=8,positions=[1,2,3,4],start=1,end=2),None]
            loss,n,c,b=m.auxiliary_sum(head,hidden,labels);(weight*loss).backward()
            self.assertEqual(n,1);self.assertTrue(torch.isfinite(loss))
            self.assertEqual(bool(hidden.grad.abs().sum()),bool(weight))
            self.assertEqual(bool(sum(p.grad.abs().sum() for p in head.parameters())),bool(weight))
            self.assertEqual(float(hidden.grad[:,9:].abs().sum()),0.)

    def test_future_location_rejected(self):
        import torch
        with self.assertRaises(ValueError):m.auxiliary_sum(m.new_head(8,rank=4),torch.randn(1,12,8),[dict(query=4,positions=[2,4],start=0,end=1)])

    def test_independent_head_parameter_count(self):
        h=m.new_head(768);self.assertEqual(sum(p.numel() for p in h.parameters()),196608)

    def test_f1_is_not_semantic_judge(self):
        self.assertEqual(m.token_f1('Nuri Hall','Nuri Hall'),1.)
        self.assertEqual(m.token_f1('wrong','Nuri Hall'),0.)


if __name__=='__main__':unittest.main()
