#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import inspect
import subprocess
import unittest
from scripts import diag_p106b_evidence_preference_train as t


class Runtime(unittest.TestCase):
    def test_initializer_is_upstream_not_self(self):
        self.assertIs(t.upstream,t.course.upstream_runtime);self.assertIsNot(t.upstream,t)

    def test_actual_batch_and_fixed64(self):
        r=t.info();self.assertEqual((r['micro_bs'],r['accum'],r['updates']),(8,16,64))
        self.assertEqual(r['arms'],{'sft_only':0.,'orpo010':.1});self.assertEqual(r['native_weight'],1.)

    def test_new_outputs_only(self):
        paths=[t.checkpoint(a) for a in t.course.ARMS]
        self.assertEqual(len(set(paths)),2);self.assertNotIn(t.course.PARENT,paths)

    def test_both_arms_calculate_pairs_and_native(self):
        src=inspect.getsource(t.run)
        self.assertIn('beta*course.method.odds.preference_loss',src)
        self.assertNotIn('if beta',src);self.assertIn('native_x+=8192',src)
        self.assertIn('course.upstream.conversation_signature',src)

    def test_check_only_is_no_model_or_new_namespace(self):
        before=(t.course.CORPUS.parent.exists(),t.course.EVIDENCE.exists())
        p=subprocess.run([sys.executable,'-B','-X','utf8',t.__file__,'--mode','cost','--arm','sft_only','--check-only'],cwd=ROOT,capture_output=True,text=True,timeout=30)
        self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(before,(t.course.CORPUS.parent.exists(),t.course.EVIDENCE.exists()))

    def test_known_correction_old_wrong_turn_is_not_supervised(self):
        from tinylm.train.mtp_sft import encode_record
        factory=t.course.upstream.factory;tok=t.course.upstream.old._tokenizer()
        g=factory.graph(0,'train');row=factory.make(g,'ko',factory.MODES.index('correct'))
        plain=encode_record(row,tok);actual=t.encode(row,tok)
        self.assertEqual(plain.x,actual.x);self.assertLess(actual.targets,plain.targets)
        self.assertTrue(all(y==-100 for y,s in zip(actual.y,actual.segments) if s==1))
        self.assertTrue(any(y!=-100 and s==2 for y,s in zip(actual.y,actual.segments)))


if __name__=='__main__':unittest.main()
