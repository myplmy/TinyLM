#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from collections import Counter
import contextlib
import io
import unittest
from scripts import diag_p106b_dualqa_production as p


class Production(unittest.TestCase):
    def test_six_lane_quotas_not_total_only(self):
        c=Counter({s+':'+l:n for s,n in p.data.TARGETS.items() for l in ('ko','en')})
        self.assertTrue(p.quotas_met(c));c['test:ko']-=1;self.assertFalse(p.quotas_met(c))

    def test_processed_and_full_lane_never_regenerated(self):
        jobs=[dict(root='a',split='train',language='ko'),dict(root='b',split='train',language='en')]
        self.assertEqual(p.next_jobs(jobs,{'a'},Counter()),[jobs[1]])
        c=Counter({'train:en':p.data.TARGETS['train']});self.assertEqual(p.next_jobs(jobs,{'a'},c),[])

    def test_test_content_hidden_without_losing_metrics(self):
        jobs=[dict(root='a',split='test')];out=io.StringIO()
        with contextlib.redirect_stdout(out):p.emit_factory(jobs)('[DUALQA_TEACHER_ANSWER] {"root":"a","fields":{"question":"SECRET_TEST"},"request_sec":2}')
        self.assertNotIn('SECRET_TEST',out.getvalue());self.assertIn('request_sec',out.getvalue())

    def test_runtime_scope_restores_old_code_functions(self):
        tag=p.legacy.TAG;wrap=p.legacy.method.wrap;thinking=p.legacy.teacher.THINKING
        with p.producer_scope([]):
            self.assertEqual(p.legacy.TAG,p.TAG);self.assertIs(p.legacy.method.wrap,p.data.render)
            self.assertEqual(p.legacy.teacher.THINKING,256)
        self.assertEqual(p.legacy.TAG,tag);self.assertIs(p.legacy.method.wrap,wrap);self.assertEqual(p.legacy.teacher.THINKING,thinking)


if __name__=='__main__':unittest.main()
