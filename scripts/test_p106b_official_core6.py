"""Pure Core6 raw/denominator/admission contracts; no framework or model."""
from __future__ import annotations
from contextlib import contextmanager
import json
import ast
import inspect
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import diag_p106b_official_core6 as run
from scripts.p106b_shards import ShardWriter,verify


class FakeTask:
    multiple_input=False
    eval_docs=[dict(choices=['X','a much longer answer'],gold=1),dict(choices=['long answer','Y'],gold=0)]
    def doc_to_choice(self,doc):return doc['choices']
    def doc_to_target(self,doc):return doc['gold']
    def doc_to_text(self,doc):return doc['gold']


class Core6Contracts(unittest.TestCase):
    def test_strict_model_entry_keeps_parameter_version_counters(self):
        tree=ast.parse(inspect.getsource(run.execute))
        called=[node.func.attr for node in ast.walk(tree) if isinstance(node,ast.Call)
                and isinstance(node.func,ast.Attribute)]
        self.assertIn('no_grad',called)
        self.assertNotIn('inference_mode',called)

    def test_exact_denominators(self):
        self.assertEqual(sum(run.expected_counts('full').values()),19965)
        self.assertEqual(sum(run.expected_counts('cost').values()),192)
        with self.assertRaises(ValueError):run.expected_counts('approximate')

    def test_sum_and_original_character_norm_differ(self):
        row=run.independent_row(['X','a much longer answer'],1,[-1.,-2.])
        self.assertEqual((row['pred'],row['pred_norm'],row['acc'],row['acc_norm']),(0,1,0,1))

    def test_tie_uses_first_like_numpy_argmax(self):
        row=run.independent_row(['A','B'],0,[-1.,-1.])
        self.assertEqual((row['acc'],row['acc_norm']),(1,1))

    def test_invalid_complete_choice_sets_refused(self):
        for choices,gold,scores in ((['A','B'],0,[-1.]),(['A',''],0,[-1.,-2.]),
                (['A','B'],True,[-1.,-2.]),(['A','B'],2,[-1.,-2.]),
                (['A','B'],0,[float('nan'),-2.]),(['A','B'],0,[.1,-2.])):
            with self.subTest(choices=choices,gold=gold,scores=scores),self.assertRaises(ValueError):
                run.independent_row(choices,gold,scores)

    def rows(self):
        return [dict(doc_id=0,filtered_resps=[(-1.,False),(-2.,False)],acc=0,acc_norm=1),
                dict(doc_id=1,filtered_resps=[(-2.,False),(-1.,False)],acc=0,acc_norm=1)]

    def test_full_raw_recount_and_baselines(self):
        check=run.audit_samples(FakeTask(),self.rows(),2)
        self.assertEqual((check['correct'],check['correct_norm'],check['random_expected_correct']),(0,2,1.))
        self.assertEqual(check['posthoc_majority_correct'],1)

    def test_wino_multiple_input_gold_uses_text_not_suffix(self):
        task=FakeTask();task.multiple_input=True
        task.doc_to_target=lambda doc:'unlabelled suffix'
        self.assertEqual(run.audit_samples(task,self.rows(),2)['correct_norm'],2)

    def test_dropped_duplicate_or_reordered_docs_fail(self):
        for rows in (self.rows()[:1],self.rows()[::-1],[self.rows()[0]]*2):
            with self.subTest(rows=rows),self.assertRaises(ValueError):run.audit_samples(FakeTask(),rows,2)

    def test_wrong_upstream_metric_fails_not_zero_score(self):
        rows=self.rows();rows[0]['acc_norm']=0
        with self.assertRaises(ValueError):run.audit_samples(FakeTask(),rows,2)

    def cost(self):
        return dict(status='LIMITED_COST_DIAGNOSTIC',model='native595-f',source_identity={'sha256':'A'},
            actual_counts=run.expected_counts('cost'),policy=run.policy(),evaluation_seconds=6.,
            task_evaluation_seconds={name:(1. if name!='hellaswag' else 3.) for name in run.TASK_COUNTS})

    def test_full_forecast_task_weighted_not_unweighted192(self):
        cost=self.cost()
        with patch.object(run,'digest',return_value='C'*64):
            result=run.admit_full(cost,{'sha256':'A'},'native595-f',run.DEADLINE-10000)
        expected=sum(run.TASK_COUNTS[n]*s/32 for n,s in cost['task_evaluation_seconds'].items())*1.5+60
        self.assertAlmostEqual(result['forecast_seconds'],expected)
        self.assertGreater(result['forecast_seconds'],sum(cost['task_evaluation_seconds'].values())*19965/192*1.5+60)

    def test_missing_cost_policy_or_source_refused(self):
        for field,value in (('status','STARTED'),('source_identity',{}),('policy',{}),('actual_counts',{}),
                ('task_evaluation_seconds',{})):
            cost=self.cost();cost[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                run.admit_full(cost,{'sha256':'A'},'native595-f',run.DEADLINE-10000)

    def test_deadline_or_two_hour_budget_refused(self):
        for now,scale in ((run.DEADLINE-1,1),(run.DEADLINE-100000,1000)):
            cost=self.cost();cost['task_evaluation_seconds']={k:v*scale for k,v in cost['task_evaluation_seconds'].items()}
            with self.subTest(now=now),self.assertRaises(ValueError):run.admit_full(cost,{'sha256':'A'},'native595-f',now)

    def test_observer_restores_method_and_bounds_continuation(self):
        class LM:
            def _loglikelihood_tokens(self,requests,**kwargs):return [(-1.,False)]*len(requests)
        with tempfile.TemporaryDirectory() as tmp:
            lm=LM();original=lm._loglikelihood_tokens;writer=ShardWriter(Path(tmp),'tokens')
            with run.length_observer(lm,writer) as summary:
                self.assertEqual(lm._loglikelihood_tokens([(('C','D'),[1]*1024,[2]*2)]),[(-1.,False)])
                with self.assertRaises(ValueError):lm._loglikelihood_tokens([(('C','D'),[1],[2]*1025)])
            self.assertEqual(lm._loglikelihood_tokens,original)
            self.assertEqual(summary['context_tokens_removed'],1)
            manifest=writer.close(lineage={'synthetic':True});verify(Path(tmp),manifest)


if __name__=='__main__':unittest.main()
