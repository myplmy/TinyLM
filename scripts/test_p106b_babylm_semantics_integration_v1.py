"""Unmodified scorer integration with synthetic char tokens/uniform logits.

No actual tokenizer/model numerical oracle or BabyLM benchmark is run.
Fixtures and raw outputs are preserved in a new explicitly SYNTHETIC namespace.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime,timezone
import hashlib,json,math,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT)not in sys.path:sys.path.insert(0,str(ROOT))
from scripts import diag_p106b_babylm_semantics as worker
from scripts import p106b_babylm_semantics as core
BASE=ROOT/'test_result/evidence/p106b_babylm_semantics_SYNTHETIC_cpu_integration_v1_20261117'
class Characters:
    def __call__(self,*,text,return_offsets_mapping):
        assert return_offsets_mapping is True
        return dict(input_ids=[1]+[ord(char)%120+2 for char in text],attention_mask=[1]*(len(text)+1),
            offset_mapping=[[0,0]]+[[i,i+1]for i in range(len(text))])
class UniformLogits:
    def __init__(self,torch):self.torch=torch;self.calls=0
    def __call__(self,*,input_ids,attention_mask):
        assert input_ids.device.type=='cpu'and input_ids.shape==attention_mask.shape
        assert not self.torch.is_grad_enabled()and not self.torch.cuda.is_initialized()
        self.calls+=1
        return dict(logits=self.torch.zeros((*input_ids.shape,128),dtype=self.torch.float32,device='cpu'))
class OfficialScorerIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import torch
        cls.torch=torch;torch.set_num_threads(2);torch.set_num_interop_threads(1)
        cls.profile=worker.verify_profile();BASE.mkdir(exist_ok=False)
    def run_fixture(self,task,filename,raw,expected_by_uid,skipped):
        torch=self.torch;directory=BASE/('SYNTHETIC_'+task);directory.mkdir()
        fixture=directory/filename
        with fixture.open('x',encoding='utf-8')as f:
            for value in raw:f.write(json.dumps(value)+'\n')
        spec=dict(path=str(fixture.relative_to(ROOT)),task=task,decoded_rows=sum(expected_by_uid.values()),
            raw_rows=len(raw),official_skipped_rows=skipped,by_UID=expected_by_uid,sha256=worker.prior.digest(fixture))
        official,proof=core.load_official(worker.prior.SOURCE,torch,device='cpu')
        processor=Characters();meta=worker.tokenizer_sweep(official,processor,spec)
        forward=UniformLogits(torch);torch.manual_seed(1337)
        def check():self.assertFalse(torch.cuda.is_initialized())
        with torch.no_grad():
            summary=worker.score_file(official,torch,forward,processor,0,spec,meta,'full',directory,check,[0])
        self.assertEqual(summary['rows'],sum(expected_by_uid.values()))
        self.assertEqual({u:v['total']for u,v in summary['by_UID'].items()},expected_by_uid)
        events=[]
        for part in summary['manifest']['shards']:
            events.extend(json.loads(line)for line in(directory/part['path']).read_text(encoding='utf-8').splitlines())
        self.assertEqual([row['index']for row in events],list(range(len(events))))
        self.assertEqual([row['source']['kept_index']for row in events],list(range(len(events))))
        for event in events:
            self.assertEqual(event['task'],task)
            self.assertEqual(event['candidate_count'],2 if task=='comps' else 5)
            # Independent char-completion length oracle, without using mask sums.
            for score,completion in zip(event['scores'],event['raw']['completions']):
                self.assertTrue(math.isclose(score,-len(completion)*math.log(128),abs_tol=1e-5,rel_tol=1e-6))
            for native,sentence in zip(event['native_inputs'],event['raw']['sentences']):
                self.assertEqual(len(native['ids']),len(sentence)+1)
                self.assertEqual(native['phrase_mask'][0],0)
        self.assertEqual(forward.calls,2 if task=='comps' else 5)
        self.assertFalse(torch.cuda.is_initialized())
        return summary,events
    def test_comps_full_original_scorer_two_candidates_rightpad_suffix_sum_and_trace(self):
        rows=[dict(id=i,property='synthetic property',prefix_acceptable=a,prefix_unacceptable=b,property_phrase=c)
            for i,(a,b,c)in enumerate((('a','long prefix','xy'),('another','b','z'),('red','blue','one')))]
        summary,events=self.run_fixture('comps','comps_base.jsonl',rows,{'base':3},0)
        self.assertEqual(summary['exact_ties'],3)
        self.assertEqual([row['source']['raw_line']for row in events],[1,2,3])
    def test_entity_full_original_scorer_five_candidates_author_skip_UID_macro_and_trace(self):
        rows=[dict(sample_id=1,example_id=0,numops=0,input_prefix='Answer: ',options=['a','bb','ccc','dddd','eeeee']),
            dict(sample_id=2,example_id=1,numops=0,input_prefix='Skip: ',options=['a','nothing','ccc','dddd','eeeee']),
            dict(sample_id=3,example_id=2,numops=1,input_prefix='Longer answer: ',options=['red','one','two','see','off'])]
        summary,events=self.run_fixture('entity_tracking','regular.jsonl',rows,{'regular_0_ops':1,'regular_1_ops':1},1)
        self.assertEqual(summary['uids'],2);self.assertEqual([e['source']['raw_line']for e in events],[1,3])
        self.assertEqual(events[0]['chosen'],0);self.assertEqual(summary['exact_ties'],1)
def main():
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(OfficialScorerIntegration))
    if BASE.exists():
        receipt=dict(schema='P106B_BABYLM_SYNTHETIC_CPU_SCORER_INTEGRATION_V1',UTC=datetime.now(timezone.utc).isoformat(),
            tests=result.testsRun,successful=result.wasSuccessful(),failures=len(result.failures),errors=len(result.errors),
            current_worker_profile_SHA256=worker.prior.digest(worker.PROFILE),source_SHA256=worker.prior.digest(Path(__file__)),
            unchanged_current_worker_profile_verified=True,actual_BabyLM_rows_evaluated=0,actual_models=0,GPU_calls=0,
            actual_native_tokenizer_or_model_numerical_oracles='NOT_RUN',
            fixture_summary_full_flag='Full means whole SYNTHETIC fixture;not actual benchmark qualification',
            synthetic_forward='CPU_ALL_ZERO_LOGITS_V128;CHARACTER_PROCESSOR;NO_MODEL_CLASS',
            source='Exact unchanged official decode/getitem/collate/compute_causal_results/rank/process_results',
            tests_not_substitute_for_actual_GPU_oracles=True)
        with(BASE/'report.json').open('x',encoding='utf-8')as f:json.dump(receipt,f,ensure_ascii=False,indent=2)
        print(json.dumps(receipt,ensure_ascii=False),flush=True)
    return 0 if result.wasSuccessful() else 1
if __name__=='__main__':raise SystemExit(main())
