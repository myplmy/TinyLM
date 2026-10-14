"""CPU-only source contracts and exact objective normalization; no real data/model."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import unittest
from unittest.mock import patch
import torch
from scripts import p106b_source_course as data
from tinylm.data.prepare import SyntheticTokenizer
from tinylm.train import mtp_sft as core
from tinylm.chat.canonical import normalize


class SourceCourseTests(unittest.TestCase):
    def candidate(self):
        return normalize(dict(messages=[dict(role='user',content='Reference'),dict(role='assistant',content='blue')],
            meta=dict(language='en',parent_concept_id='A'*64,source_reference_trace=[dict(text='Mina is blue.',id=1)])))
    def test_supported_and_missing_views_share_group(self):
        a,b=data.views(self.candidate(),'What color is Mina?','train')
        self.assertEqual(a['meta']['semantic_root_id'],b['meta']['semantic_root_id'])
        self.assertIn('Mina is blue.',data.source.text(a['messages'][0]));self.assertNotIn('Mina is blue.',data.source.text(b['messages'][0]))
        self.assertIn('only the supplied reference',data.source.text(b['messages'][0]))
        self.assertIn('provide',data.source.text(b['messages'][-1]))
    def test_reference_targets_do_not_supervise_assistant(self):
        a,b=data.views(self.candidate(),'What color is Mina?','train');tok=SyntheticTokenizer()
        ra=data.record(a,tok);rb=data.record(b,tok)
        self.assertGreater(data.native_count(ra),0);self.assertEqual(data.native_count(rb),0)
        self.assertTrue(all(y==core.IGNORE for y,n in zip(ra.y,ra.reference_y) if n!=core.IGNORE))
    def test_document_keys_protect_long_reference_duplicates(self):
        a=self.candidate();a['messages'][0]['content'][0]['text']='x'*220
        b=self.candidate();b['meta']['parent_concept_id']='B'*64;b['messages'][0]['content'][0]['text']='x'*220
        self.assertTrue(data.document_keys(a)&data.document_keys(b))
    def test_family_and_weight_contract(self):
        r=self.candidate();r['meta']['source_family']='Adversarial QA (T)';self.assertEqual(data.family(r),'ADVERSARIAL')
        with self.assertRaises(ValueError):data.ReferenceObjective(.5)
    def test_zero_weight_exactly_preserves_main_gradient(self):
        t=torch.tensor(2.,requires_grad=True)
        with data.ReferenceObjective(0.):loss=core.normalized_loss({1:t*4}, {1:8,'reference':4},{})
        self.assertEqual(float(loss),1.);loss.backward();self.assertEqual(float(t.grad),.5)
    def test_reference_uses_global_update_denominator(self):
        a=torch.tensor(4.,requires_grad=True);b=torch.tensor(6.,requires_grad=True)
        with data.ReferenceObjective(.1):loss=core.normalized_loss({1:a,'reference':b},{1:8,'reference':12},{})
        self.assertAlmostEqual(float(loss),.55,places=6);loss.backward()
        self.assertAlmostEqual(float(a.grad),1/8);self.assertAlmostEqual(float(b.grad),.1/12)
    def test_padding_and_scope_restoration(self):
        before=core.encode_record;a,b=data.views(self.candidate(),'Mina color?','train');records=[data.record(r,SyntheticTokenizer()) for r in (a,b)]
        with data.ReferenceObjective(.1) as obj:
            x,y,seg=core.pad_records(records,0,'cpu',fixed_width=1024,batch_size=8)
            self.assertEqual(x.shape,(8,1024));self.assertEqual(obj.reference_y.shape,y.shape)
            self.assertTrue(bool(obj.reference_y[2:].eq(core.IGNORE).all()))
        self.assertIs(core.encode_record,before)

if __name__=='__main__':unittest.main(verbosity=2)
