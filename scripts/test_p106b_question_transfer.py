"""Bounded synthetic contracts only; no actual source, checkpoints or GPU."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import ast
from collections import Counter
import copy
from datetime import datetime,timezone
import hashlib
import importlib
import json
import tempfile
import unittest
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import patch
from scripts import diag_p106b_question_transfer as d


class FakeTokenizer:
    def token_to_id(self,value):return {'<|im_end|>':4,'<eos>':2,'<pad>':0}[value]
    def encode(self,value):
        class Encoded:ids=[10,11]
        return Encoded()
    def decode(self,ids,skip_special_tokens=True):
        return ''.join({10:'p',11:'q',35:'5',4:'<|im_end|>',2:'<eos>'}.get(i,'?') for i in ids)


def fake_case(lane='canary'):
    c=dict(id='A',lane=lane,family='arithmetic',language='en',messages=[dict(role='user',content='Compute')],gold='5')
    c['encoding']=d.case_encoding(c,FakeTokenizer()) if lane=='user_seen' else dict(
        prompt_sha256='P',prompt_ids_sha256='I',prompt_tokens=2)
    return c


def event_for(case,answer='5',generated=None,finish='STOP_SEQUENCE'):
    ids=[35,4] if generated is None else generated
    term=[4] if finish=='STOP_SEQUENCE' else [2] if finish=='EOS' else []
    content=ids[:-len(term)] if term else ids
    g=dict(max_new=64,precision='FP32_MATH',temperature=0.,top_k=1,use_cache=True,mtp=False,
        candidate_answers_supplied=False,prompt_sha256=case['encoding']['prompt_sha256'],
        prompt_ids_sha256=case['encoding']['prompt_ids_sha256'],prompt_tokens=case['encoding']['prompt_tokens'],
        generated_ids=ids,generated_tokens=len(ids),generated_ids_sha256=d.sha(ids),
        terminal_ids=term,content_ids_sha256=d.sha(content),finish_reason=finish,
        matched_stop_sequence=[4] if finish=='STOP_SEQUENCE' else None,
        stop_token_sequences=[[4]],
        body_utf8_sha256=hashlib.sha256(answer.encode()).hexdigest().upper())
    return dict(id=case['id'],case_sha256=d.sha(case),answer=answer,generation=g,metrics=d.classify_case(case,answer))


class ScheduleTests(unittest.TestCase):
    def test_four_pass_exact384_updates_micro8_accum16(self):
        total=0
        for epoch in range(4):
            groups=d.schedule(epoch)
            self.assertEqual(len(groups),96)
            self.assertTrue(all(len(g)==16 and all(len(m)==8 for m in g) for g in groups))
            self.assertEqual(sorted(i for g in groups for m in g for i in m),list(range(12288)))
            self.assertEqual(groups,d.schedule(epoch));total+=len(groups)
        self.assertEqual(total,384)
        self.assertNotEqual(d.schedule(0),d.schedule(1))

    def test_bad_epoch_and_incomplete_denominator_rejected(self):
        for args in [(True,),(-1,),(4,),(0,4096)]:
            with self.assertRaises(ValueError):d.schedule(*args)

    def test_global_target_sum_not_micro_mean_or_extra_accum_division(self):
        import torch
        p=torch.tensor(2.,requires_grad=True)
        sums=[p*3,p*9];targets=[1,5]
        actual=sum(d.normalized_assistant_loss(x,sum(targets)) for x in sums)
        actual.backward()
        self.assertAlmostEqual(float(actual.detach()),4.)
        self.assertAlmostEqual(float(p.grad),2.)
        wrong_micro=sum(float(x.detach())/n for x,n in zip(sums,targets))/2
        self.assertNotAlmostEqual(float(actual.detach()),wrong_micro)
        self.assertNotAlmostEqual(float(actual.detach()),float(actual.detach())/16)
        for n in [0,-1,True,6.]:
            with self.assertRaises(ValueError):d.normalized_assistant_loss(1.,n)

    def test_natural_has_same_position_schedule_but_never_rephrases_question(self):
        for arm in d.ARMS:
            for rotation in range(4):
                positions=[d.natural_layout(arm,e,rotation) for e in range(4)]
                self.assertEqual(Counter(positions),{'CQ':2,'QC':2} if arm.endswith('_balanced') else {'CQ':4})
        p=dict(language='en',context='alpha text.',question='Which alpha?',answers=[dict(text='text')],
            split='train',root='r',article_id='a',source_path='SOURCE',source_sha256='H')
        for pos in ['CQ','QC']:
            row=d.natural_row(p,pos);q=row['messages'][0]['content']
            self.assertEqual(q.count(p['question']),1);self.assertEqual(q.count(p['context']),1)
            self.assertEqual(row['messages'][1]['content'],'text')
            self.assertEqual(q.index(p['context'])<q.index(p['question']),pos=='CQ')

    def test_native_windows_are_same3072_disjoint_complete_train_only(self):
        a=d.original.native_offsets(count=3072,seed=20261019)
        self.assertEqual(a,d.original.native_offsets(count=3072,seed=20261019))
        self.assertEqual(len(set(a)),3072)
        self.assertTrue(all(y-x>=1025 for x,y in zip(sorted(a),sorted(a)[1:])))
        self.assertTrue(all(0<=v<=597995000-1025 for v in a))


class WireTests(unittest.TestCase):
    def test_masked_old_wrong_turn_keeps_owner_and_roundtrips_without_target_loss(self):
        from tinylm.train.mtp_sft import Record, count_record
        r=Record([8,9,12,13,14],[-100,-100,-100,7,4],[0,1,1,2,2])
        value=d.wire(r,'repair','replay','en','graph',dict(source='masked-turn-fixture'))
        before=copy.deepcopy(value)
        restored=d.unwire(value)
        self.assertEqual(restored,r);self.assertEqual(value,before)
        self.assertEqual(d.wire(restored,'repair','replay','en','graph',value['encoding']),value)
        self.assertEqual(restored.targets,2)
        self.assertEqual(count_record(restored,horizons=(1,2)),{1:2,2:1})

    def test_ignored_logits_have_zero_direct_gradient_but_corrected_targets_train(self):
        import torch
        from tinylm.train.mtp_sft import horizon_targets, ce_sum
        y=torch.tensor([[-100,-100,7,4]]);segments=torch.tensor([[0,1,2,2]])
        labels,valid=horizon_targets(y,segments,1)
        self.assertEqual(labels.tolist(),y.tolist())
        self.assertEqual(valid.tolist(),[[False,False,True,True]])
        logits=torch.arange(64,dtype=torch.float32).reshape(1,4,16).clone().requires_grad_()
        loss=ce_sum(logits,labels)/2;loss.backward()
        self.assertEqual(float(logits.grad[:,:2].abs().sum()),0.)
        self.assertGreater(float(logits.grad[:,2:].abs().sum()),0.)
        changed=logits.detach().clone();changed[:,:2]=10000.
        self.assertEqual(float(ce_sum(changed,labels)/2),float(loss.detach()))
        self.assertEqual(horizon_targets(y,segments,2)[0].tolist(),[[-100,-100,4]])

    def test_positive_target_owner_zero_is_rejected_even_with_fresh_hash(self):
        from tinylm.train.mtp_sft import Record
        value=d.wire(Record([8,9,35],[-100,35,4],[0,0,1]),'id','coded','en','parent')
        with self.assertRaises(ValueError):d.unwire(value)

    def test_roundtrip_excludes_prompt_from_assistant_ce(self):
        from tinylm.train.mtp_sft import Record
        r=Record([8,9,35],[-100,35,4],[0,1,1])
        value=d.wire(r,'id','coded','en','parent',dict(source='fixture'))
        observed=d.unwire(value)
        self.assertEqual(observed,r);self.assertEqual(observed.targets,2)

    def test_bad_lengths_labels_turn_owners_hash_and_unknown_fields_rejected(self):
        from tinylm.train.mtp_sft import Record
        original=d.wire(Record([8,9,35],[-100,35,4],[0,1,1]),'id','coded','en','p')
        for field,value in [('x',[]),('y',[35]),('segments',[0,0,1]),('record_sha256','F'*64),
                            ('assistant_targets',3),('x_tokens',999),('unexpected',1)]:
            bad=copy.deepcopy(original);bad[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):d.unwire(bad)

    def test_wrong_stem_path_and_duplicate_sequence_fail_before_payload_hash(self):
        for name in ['/etc/passwd','../answers_000000.jsonl','other_000000.jsonl','answers_000001.jsonl']:
            m=dict(rows=1,shards=[dict(path=name,bytes=64)])
            with patch.object(d,'safe',side_effect=lambda p:p),patch.object(d,'verify') as verify,patch.object(d,'required') as required:
                with self.assertRaises(ValueError):d.read_rows(Path('/tmp/NO_SOURCE'),m,'answers',1)
                verify.assert_not_called();required.assert_not_called()

    def test_empty_negative_or_boolean_shard_sizes_rejected(self):
        for size in [0,-1,True,20000000]:
            m=dict(rows=1,shards=[dict(path='answers_000000.jsonl',bytes=size)])
            with patch.object(d,'safe',side_effect=lambda p:p),self.assertRaises(ValueError):d.read_rows(Path('/tmp/NO_SOURCE'),m,'answers',1)


class SourceGrammarTests(unittest.TestCase):
    def test_recovery_keeps_the_v1_scientific_selection_key(self):
        self.assertEqual(d.TAG,'p106b_question_transfer_v2_s1337')
        self.assertEqual(d.DATA_SELECTION_KEY,'p106b_question_transfer_v1_s1337')

    def test_every_pass_and_dev_fail_before_model_or_gpu_admission(self):
        import torch
        from tinylm.train.mtp_sft import Record
        good=d.wire(Record([8,9,35],[-100,35,4],[0,1,1]),'id','coded','en','p')
        bad=copy.deepcopy(good);bad['segments']=[0,0,1]
        bad['record_sha256']=d.sha({k:bad[k] for k in ('x','y','segments')})
        initialized=torch.cuda.is_initialized()
        for broken in ('late_pass','dev'):
            with self.subTest(broken=broken),tempfile.TemporaryDirectory() as directory,ExitStack() as stack:
                stack.enter_context(patch.object(d,'EVIDENCE',Path(directory)))
                stack.enter_context(patch.object(d,'safe',side_effect=lambda p:p))
                stack.enter_context(patch.object(d,'authority',return_value=100000.))
                stack.enter_context(patch.object(d,'read_prepared',return_value=({'manifests':{'dev':{}}},None,None)))
                stack.enter_context(patch.object(d,'digest',side_effect=[d.base.NATIVE_TRAIN_SHA,d.base.NATIVE_VAL_SHA]))
                reads=stack.enter_context(patch.object(d,'records_for',side_effect=
                    [[d.unwire(good)]]*3+[ValueError('late pass')] if broken=='late_pass' else
                    [[d.unwire(good)]]*4))
                stack.enter_context(patch.object(d,'read_rows',return_value=[bad] if broken=='dev' else [good]))
                load=stack.enter_context(patch.object(d.base,'load_parent',side_effect=AssertionError('MODEL')))
                optimizer=stack.enter_context(patch.object(d.base,'make_optimizers',side_effect=AssertionError('OPTIMIZER')))
                idle=stack.enter_context(patch('scripts.p106b_gate_runtime.idle_before_gpu',side_effect=AssertionError('GPU_ADMISSION')))
                with self.assertRaises(ValueError):d.train('fixed_last',cost=True)
                self.assertEqual(reads.call_count,4)
                load.assert_not_called();optimizer.assert_not_called();idle.assert_not_called()
                self.assertFalse((Path(directory)/'cost_fixed_last').exists())
        self.assertEqual(torch.cuda.is_initialized(),initialized)

    def row(self,kind,lang,questions):
        return dict(meta=dict(kind=kind,language=lang,generation_version='P106B_VISIBLE_CONTEXT_CLARIFY_V1'),
                    messages=[dict(role='user',content=q) for q in questions])

    def test_exact_replay_calculation_and_update_recovery(self):
        p=self.row('arithmetic','en',['Calculate 49-32. Reply with only one integer.'])
        self.assertEqual(d.replay_calculations(p),[('-',49,32)])
        p=self.row('arithmetic','ko',['32+49의 계산 결과를 정수 하나로만 답하세요.'])
        self.assertEqual(d.replay_calculations(p),[('+',32,49)])
        p=self.row('update','en',['Give 46+10 as one integer only.',
            'In that calculation, replace the second number 10 with 98. Give only the updated result.'])
        self.assertEqual(d.replay_calculations(p),[('+',10,46),('+',46,98)])

    def test_unknown_or_changed_registered_grammar_is_not_guessed(self):
        for q in ['Calculate 49-32.','49-32','Ignore source. Calculate 49-32. Reply with only one integer.']:
            with self.assertRaises(ValueError):d.replay_calculations(self.row('arithmetic','en',[q]))
        p=self.row('arithmetic','en',['Calculate 49-32. Reply with only one integer.']);p['meta']['generation_version']='OTHER'
        with self.assertRaises(ValueError):d.replay_calculations(p)
        self.assertEqual(d.replay_calculations(dict(meta=dict(kind='natural'),messages=[])),[])

    def test_addition_commutation_not_subtraction_exclusion(self):
        self.assertEqual(d.calculation('+',2,9),d.calculation('+',9,2))
        self.assertNotEqual(d.calculation('-',2,9),d.calculation('-',9,2))


class GenerationTests(unittest.TestCase):
    def run_emission(self,generated,reason):
        tok=FakeTokenizer();seen={}
        def sample(model,cfg,capture,prompt,**kwargs):
            seen.update(kwargs)
            full=[10,11]+generated;capture.decode(full)
            return 'unused full text',dict(finish_reason=reason,generated_tokens=len(generated),max_new=kwargs['max_new'],
                matched_stop_sequence=[4] if reason=='STOP_SEQUENCE' else None,
                stop_token_sequences=[[4]],eos_token_available=True)
        class Cfg:max_seq_len=1024
        generate_module=importlib.import_module('tinylm.infer.generate')
        with patch.object(generate_module,'sample',side_effect=sample):
            body,meta=d.emit64(object(),Cfg(),tok,[dict(role='user',content='Compute')])
        return body,meta,seen

    def test_actual_sampler_uses64_not128_then_truncates(self):
        body,m,seen=self.run_emission([35,4],'STOP_SEQUENCE')
        self.assertEqual(body,'5');self.assertEqual(seen['max_new'],64)
        self.assertEqual((seen['temperature'],seen['top_k'],seen['use_cache']),(0.,1,True))
        self.assertEqual(m['generated_ids'],[35,4]);self.assertEqual(m['terminal_ids'],[4])
        self.assertEqual(m['body_utf8_sha256'],hashlib.sha256(b'5').hexdigest().upper())

    def test_only_authenticated_last_eot_or_eos_removed(self):
        body,m,_=self.run_emission([35,2],'EOS');self.assertEqual(body,'5');self.assertEqual(m['terminal_ids'],[2])
        for ids,reason in [([35,2],'STOP_SEQUENCE'),([35,4],'EOS'),([35],'OTHER')]:
            with self.assertRaises(ValueError):self.run_emission(ids,reason)

    def test_recount_checks_complete_raw_receipt_and_recomputes_scores(self):
        c=fake_case();e=event_for(c);s=d.recount([e],[c])
        self.assertEqual(s['actual_answers'],1);self.assertEqual(s['cells'][0]['correct'],1)
        for field,value in [('precision','BF16'),('max_new',128),('temperature',1.),('top_k',20),
            ('generated_tokens',True),('generated_ids_sha256','BAD'),('content_ids_sha256','BAD'),
            ('terminal_ids',[]),('finish_reason','UNKNOWN'),('body_utf8_sha256','BAD'),('candidate_answers_supplied',True)]:
            bad=copy.deepcopy(e);bad['generation'][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):d.recount([bad],[c])
        bad=copy.deepcopy(e);bad['answer']='4';bad['generation']['body_utf8_sha256']=hashlib.sha256(b'4').hexdigest().upper()
        with self.assertRaises(ValueError):d.recount([bad],[c])

    def test_missing_duplicate_reordered_or_wrong_case_is_not_zero_imputation(self):
        c=fake_case();e=event_for(c)
        with self.assertRaises(d.Pending):d.recount([], [c])
        with self.assertRaises(d.Pending):d.recount([e,e], [c,c])
        bad=copy.deepcopy(e);bad['case_sha256']='BAD'
        with self.assertRaises(ValueError):d.recount([bad],[c])

    def test_user_unadjudicated_and_natural_alias_metric_separate(self):
        self.assertIsNone(d.classify_case(dict(lane='user_seen'),'any')['correct'])
        metric=d.classify_case(dict(lane='natural',aliases=['Paris'],language='en'),'Paris')
        self.assertTrue(metric['correct']);self.assertEqual(metric['em'],1.)
        self.assertIn('not semantic',metric['scope'])


class AdmissionTests(unittest.TestCase):
    def test_absolute_timezone_and_three_hour_training_reserve(self):
        self.assertEqual(d.authority(training=True,now=datetime(2026,10,20,4,tzinfo=timezone.utc)),3600.)
        self.assertEqual(d.authority(now=datetime(2026,10,20,4,tzinfo=timezone.utc)),14400.)
        with self.assertRaises(d.Pending):d.authority(training=True,now=datetime(2026,10,20,5,tzinfo=timezone.utc))
        with self.assertRaises(d.Pending):d.authority(now=d.END)
        with self.assertRaises(ValueError):d.authority(now=datetime(2026,10,19))

    def test_exact_three_phase_noninteractive_commands(self):
        phases=d.phase_commands('cost','fixed_last',max_wall_sec=900)
        self.assertEqual([x[0] for x in phases],['REGRESSION','PREFLIGHT','EXECUTE'])
        self.assertIn('--worker',phases[2][1]);self.assertIn('preflight',phases[1][1])
        phases=d.phase_commands('prepare',max_wall_sec=600)
        self.assertIn('source',phases[1][1])
        for args in [('train',None,None,900),('evaluate',None,None,900),('train','BAD',None,900),
                     ('evaluate','fixed_last','parent',900),('prepare',None,None,0)]:
            with self.assertRaises(ValueError):d.phase_commands(*args)

    def test_check_only_never_opens_actual_assets_or_runs_child(self):
        with patch.object(d,'source_inputs',side_effect=AssertionError('SOURCE')),patch.object(d,'read_prepared',side_effect=AssertionError('CORPUS')),patch.object(d.subprocess,'run',side_effect=AssertionError('CHILD')),patch.object(d,'info',return_value=dict(scope='CODE_ONLY')):
            self.assertEqual(d.main(['--mode','prepare','--check-only']),0)

    def test_recipe_distinguishes_zero_new_training_and_cost_writes_no_checkpoint(self):
        source=(ROOT/'scripts/diag_p106b_question_transfer.py').read_text()
        ast.parse(source)
        self.assertEqual((d.CONTEXT,d.MAX_NEW,d.ROWS,d.UPDATES,d.EXPECTED_ANSWERS),(1024,64,12288,384,1694))
        self.assertEqual(d.EVAL_RESERVE+d.RECORD_RESERVE,10800)
        self.assertTrue(set(d.OWN_CODE).isdisjoint(d.original.OWN_CODE))
        self.assertNotIn('input(',source)


class RepairBoundaryTests(unittest.TestCase):
    def test_child_path_and_endpoint_rejected_before_digest_or_source_access(self):
        exact=str(d.checkpoint('fixed_last').relative_to(d.ROOT))
        for path in ['/OUTSIDE/UNTRUSTED/model.pt','../model.pt',str(d.checkpoint('varied_last').relative_to(d.ROOT)),exact+'/../model.pt']:
            report=dict(checkpoint=path,status='NOT_RUN',updates=0)
            with patch.object(d.base,'stage_report',return_value=report),patch.object(d,'digest',side_effect=AssertionError('PAYLOAD_DIGEST')) as digest,patch.object(d,'read_prepared',side_effect=AssertionError('SOURCE')) as source:
                with self.assertRaises(ValueError):d.identity('fixed_last',{})
                digest.assert_not_called();source.assert_not_called()
        with patch.object(d.base,'stage_report',side_effect=AssertionError('REPORT')):
            with self.assertRaises(ValueError):d.identity('UNKNOWN',{})

    def test_owned_child_still_requires_complete_training_and_activity(self):
        arm='fixed_last';report=dict(checkpoint=str(d.checkpoint(arm).relative_to(d.ROOT)),checkpoint_sha256='B'*64,final_core_sha256='C'*64)
        with patch.object(d.base,'stage_report',return_value=report),patch.object(d,'verify_training',side_effect=ValueError('PARTIAL')) as verify,patch.object(d,'read_activity') as ledger:
            with self.assertRaises(ValueError):d.identity(arm,{'frozen':True})
            verify.assert_called_once();ledger.assert_not_called()
        with patch.object(d.base,'stage_report',return_value=report),patch.object(d,'verify_training',return_value=[]),patch.object(d,'read_activity',side_effect=d.Pending('MISSING_LEDGER')):
            with self.assertRaises(d.Pending):d.identity(arm,{'frozen':True})
        with patch.object(d.base,'stage_report',return_value=report),patch.object(d,'verify_training',return_value=[]),patch.object(d,'read_activity',return_value=dict(complete=True)):
            self.assertEqual(d.identity(arm,{'frozen':True})['expected_core_sha256'],'C'*64)

    def training_fixture(self,cost=True):
        n=8 if cost else 384;arm='fixed_last';fakeinfo=dict(schema=d.SCHEMA,tag=d.TAG,code_sha256={'FIXTURE':'CODE'})
        frozen=dict(exposure={arm:[dict(update_target_denominators=[10]*96,counts=dict(x_tokens=3840,assistant_targets=960,positive_rows=12288)) for _ in range(4)]})
        events=[dict(update=i+1,epoch=i//96+1,assistant_targets=10,native_targets=8192,x_tokens=40,
            assistant_ce=1.,native_ce=2.,gradient_norm=.5,step_seconds=3.) for i in range(n)]
        report=dict(fakeinfo,status='COST8_COMPLETE' if cost else 'TRAIN_COMPLETE_EVALUATION_PENDING',
            arm=arm,updates=n,corpus_sha256='CORPUS',initial_core_sha256=d.base.PARENT_CORE,
            final_core_sha256='D'*64,checkpoint_written=not cost,actual_optimizer_groups=[],
            event_manifest=dict(lineage=dict(tag=d.TAG,arm=arm,cost=cost)),step_seconds=[3.]*n,
            grad_max=.5,clip_events=0,totals=dict(positive_rows=128*n,x_tokens=40*n,assistant_targets=10*n,native_targets=8192*n))
        if not cost:report.update(checkpoint=str(d.checkpoint(arm).relative_to(d.ROOT)),checkpoint_sha256='CP')
        return fakeinfo,frozen,events,report

    def test_completed_cost_and_training_receipts_have_strict_source_raw_body_exposure(self):
        for cost in [True,False]:
            info,frozen,events,report=self.training_fixture(cost)
            def digest(path):return 'CORPUS' if path==d.CORPUS/'report.json' else 'CP'
            with patch.object(d,'info',return_value=info),patch.object(d,'digest',side_effect=digest),patch.object(d,'read_rows',return_value=events),patch.object(d.original,'validate_groups',return_value=None):
                self.assertEqual(d.verify_training(report,'fixed_last',frozen,cost),events)
                for field,value in [('status','NOT_RUN'),('updates',0),('arm','varied_last'),('corpus_sha256','STALE'),('code_sha256',{'FIXTURE':'OLD'}),('final_core_sha256','BAD'),('event_manifest',dict(lineage=dict(tag=d.TAG,arm='WRONG',cost=cost)))]:
                    bad=copy.deepcopy(report);bad[field]=value
                    with self.subTest(cost=cost,field=field),self.assertRaises(ValueError):d.verify_training(bad,'fixed_last',frozen,cost)

    def evaluation_fixture(self):
        cases=[fake_case()];frozen=dict(cases_sha256=d.sha(cases));info=dict(schema=d.SCHEMA,tag=d.TAG,code_sha256={'FIXTURE':'CODE'})
        link=dict(endpoint='parent',checkpoint='OWNED',checkpoint_sha256='CP',expected_core_sha256='C'*64)
        report=dict(info,status='ACTUAL_FIRST_ANSWERS_RECORDED',endpoint='parent',lineage=link,
            corpus_sha256='CURRENT',cases_sha256=d.sha(cases),core_before='C'*64,core_after='C'*64,
            model_training=False,weights_changed=False,checkpoints_written=0,answer_manifest=dict(lineage=dict(tag=d.TAG,**link)))
        report['native32_fp32']=dict(ce=3.,targets=32768,windows=32,precision='FP32_MATH',val_sha256=d.base.NATIVE_VAL_SHA)
        return cases,frozen,info,link,report

    def test_stale_eval_source_case_recipe_body_and_manifest_are_not_completion(self):
        cases,frozen,info,link,report=self.evaluation_fixture()
        with patch.object(d,'EXPECTED_ANSWERS',1),patch.object(d,'info',return_value=info),patch.object(d,'digest',return_value='CURRENT'):
            d.validate_evaluation(report,'parent',frozen,cases,link)
            for field,value in [('corpus_sha256','WRONG_SOURCE'),('cases_sha256','WRONG_CASES'),('core_after','WRONG_BODY'),('weights_changed',True),('checkpoints_written',1),('code_sha256',{'FIXTURE':'STALE'}),('lineage',{}),('answer_manifest',dict(lineage={}))]:
                bad=copy.deepcopy(report);bad[field]=value
                with self.subTest(field=field),self.assertRaises(ValueError):d.validate_evaluation(bad,'parent',frozen,cases,link)
            with self.assertRaises(ValueError):d.validate_evaluation(report,'parent',dict(cases_sha256='OTHER'),cases,link)

    def test_string_bool_negative_and_out_of_vocabulary_token_ids_rejected(self):
        c=fake_case()
        for ids in ['5'*64,[True,4],[-1,4],[40000,4],(35,4)]:
            e=event_for(c,generated=ids,finish='MAX_NEW' if isinstance(ids,str) else 'STOP_SEQUENCE')
            with self.subTest(ids=str(ids)[:40]),self.assertRaises(ValueError):d.recount([e],[c])

    def test_actual_body_must_decode_from_recorded_content_ids_when_authenticated(self):
        c=fake_case();e=event_for(c,answer='6')
        # Hash-only bookkeeping remains explicitly weaker than real decode.
        self.assertEqual(d.recount([e],[c])['token_body_correspondence'],'NOT_CHECKED_BY_PURE_RECOUNT')
        with self.assertRaises(ValueError):d.recount([e],[c],FakeTokenizer())
        e=event_for(c);self.assertEqual(d.recount([e],[c],FakeTokenizer())['token_body_correspondence'],'FROZEN_TOKENIZER_DECODE_VERIFIED')

    def test_source_preflight_and_budget_obey_authority_before_source_or_payloads(self):
        for mode in ['source','preflight','budget']:
            with patch.object(d,'authority',side_effect=d.Pending('ENDED')),patch.object(d,'source_inputs',side_effect=AssertionError('SOURCE')) as source,patch.object(d,'read_prepared',side_effect=AssertionError('CORPUS')) as corpus,patch.object(d,'budget',side_effect=AssertionError('BUDGET')) as budget:
                with self.assertRaises(d.Pending):d.run_worker(mode)
                source.assert_not_called();corpus.assert_not_called();budget.assert_not_called()

    def activity_fixture(self,complete=True):
        info=dict(code_sha256={'FIXTURE':'CODE'})
        r=dict(schema=d.SCHEMA,tag=d.TAG,key='cost_fixed_last',mode='cost',arm='fixed_last',endpoint=None,
            seconds=12.,returncode=0 if complete else None,complete=complete,limit=900,
            recorded_at='2026-10-19T02:00:00+00:00',scope='actual worker wall including input verification; regression/preflight wrapper excluded',
            code_sha256=info['code_sha256'],corpus_sha256='CORPUS')
        return info,r

    def test_activity_minimal_unknown_stale_false_status_or_wrong_key_never_silently_zero(self):
        info,r=self.activity_fixture();path=d.EVIDENCE/'activity_cost_fixed_last.json'
        with patch.object(d,'safe',side_effect=lambda x:x),patch.object(d,'info',return_value=info),patch.object(d,'digest',return_value='CORPUS'),patch.object(Path,'is_file',return_value=True):
            with patch.object(d,'required',return_value=r):self.assertEqual(d.read_activity(path,mode='cost',arm='fixed_last',completed=True)['seconds'],12.)
            bads=[dict(tag=d.TAG,seconds=.001)]
            for field,value in [('key','train_fixed_last'),('mode','UNKNOWN'),('arm','OTHER'),('seconds',True),('complete',False),('returncode',False),('limit',True),('corpus_sha256','OLD'),('code_sha256',{}),('recorded_at','2026-10-19T02:00:00')]:
                bad=copy.deepcopy(r);bad[field]=value;bads.append(bad)
            for bad in bads:
                with patch.object(d,'required',return_value=bad),self.assertRaises((ValueError,d.Pending)):d.read_activity(path,mode='cost',arm='fixed_last',completed=True)
            _,failed=self.activity_fixture(complete=False)
            with patch.object(d,'required',return_value=failed):
                self.assertEqual(d.read_activity(path)['seconds'],12.)
                with self.assertRaises(d.Pending):d.read_activity(path,completed=True)

    def test_missing_closed_cost_activity_blocks_budget_after_valid_cost_report(self):
        fake=dict(step_seconds=[3.]*8)
        with patch.object(d,'read_prepared',return_value=({},None,None)),patch.object(d.base,'stage_report',return_value=fake),patch.object(d,'verify_training',return_value=[]),patch.object(d,'read_activity',side_effect=FileNotFoundError('MISSING')),patch.object(d,'spent_seconds',return_value=0.):
            with self.assertRaises(FileNotFoundError):d.budget()


class CompleteReadbackFixtureTests(unittest.TestCase):
    def test_full8470_synthetic_closure_and_each_stale_source_fail_closed(self):
        course=d.data.build_course();source=dict(test=[])
        for language in ('ko','en'):
            for i in range(32):
                source['test'].append(dict(language=language,root=language+str(i),context='source word '+str(i),
                    question='Which word '+str(i)+'?',answers=[dict(text='word')],aliases=['word'],
                    split='test',article_id=language+str(i//4),source_path='CODE_FIXTURE',source_sha256='F'*64))
        cases=d.evaluation_cases(course,source)
        self.assertEqual(len(cases),1694)
        self.assertEqual(Counter(c['lane'] for c in cases),dict(coded=1536,natural=128,canary=24,user_seen=6))
        for c in cases:
            c['encoding']=dict(prompt_sha256=d.sha(['PROMPT',c['id']]),prompt_ids_sha256=d.sha(['IDS',c['id']]),prompt_tokens=2)
        class ToyDecoder:
            def __init__(self):self.characters={};self.reverse={}
            def token_to_id(self,value):return {'<eos>':2,'<|im_end|>':4}[value]
            def ids(self,body):
                result=[]
                for ch in body:
                    if ch not in self.characters:
                        token=100+len(self.characters);self.characters[ch]=token;self.reverse[token]=ch
                    result.append(self.characters[ch])
                return result
            def decode(self,ids,skip_special_tokens=False):return ''.join(self.reverse[i] for i in ids)
        tok=ToyDecoder();minimal=dict(schema=d.SCHEMA,tag=d.TAG,code_sha256={'FIXTURE':'CODE'})
        frozen=dict(cases_sha256=d.sha(cases),manifests=dict(cases={'rows':1694}),exposure={})
        reports={};raw={};hashes={d.CORPUS/'report.json':'CORPUS',d.natural.TOKENIZER:d.natural.TOK_SHA};activities={}
        core={};cp={}
        for endpoint in d.ENDPOINTS:
            if endpoint=='parent':
                cp[endpoint]=str(d.base.PARENT.relative_to(d.ROOT));core[endpoint]=d.base.PARENT_CORE;cp_sha=d.base.PARENT_SHA
            else:
                info,train_frozen,events,training=RepairBoundaryTests().training_fixture(cost=False)
                cp[endpoint]=str(d.checkpoint(endpoint).relative_to(d.ROOT));core[endpoint]=d.sha(['CORE',endpoint]);cp_sha=d.sha(['CP',endpoint])
                training.update(arm=endpoint,checkpoint=cp[endpoint],checkpoint_sha256=cp_sha,final_core_sha256=core[endpoint])
                training['event_manifest']['lineage']=dict(tag=d.TAG,arm=endpoint,cost=False)
                reports[d.EVIDENCE/('train_'+endpoint)/'report.json']=training
                frozen['exposure'][endpoint]=copy.deepcopy(train_frozen['exposure']['fixed_last'])
                raw[(d.EVIDENCE/('train_'+endpoint),'updates',384)]=events
                activities[d.EVIDENCE/('activity_train_'+endpoint+'.json')]=dict(mode='train',arm=endpoint,endpoint=None)
            link=dict(endpoint=endpoint,checkpoint=cp[endpoint],checkpoint_sha256=cp_sha,expected_core_sha256=core[endpoint])
            hashes[d.ROOT/cp[endpoint]]=cp_sha;events=[]
            for c in cases:
                body=c.get('gold','');ids=tok.ids(body)+[4];e=event_for(c,answer=body,generated=ids)
                e['lineage']=dict(tag=d.TAG,**link);events.append(e)
            local=d.LOCAL/('evaluate_'+endpoint)
            manifest=dict(rows=1694,lineage=dict(tag=d.TAG,**link))
            reports[d.EVIDENCE/('evaluate_'+endpoint)/'report.json']=dict(minimal,
                status='ACTUAL_FIRST_ANSWERS_RECORDED',endpoint=endpoint,lineage=link,corpus_sha256='CORPUS',
                cases_sha256=d.sha(cases),core_before=core[endpoint],core_after=core[endpoint],
                summary=d.recount(events,cases,tok),answer_manifest=manifest,answer_manifest_sha256='MANIFEST',
                model_training=False,weights_changed=False,checkpoints_written=0,
                native32_fp32=dict(ce=3.,targets=32768,windows=32,precision='FP32_MATH',val_sha256=d.base.NATIVE_VAL_SHA))
            raw[(local,'answers',1694)]=events;hashes[local/'answers_shards_manifest.json']='MANIFEST'
            activities[d.EVIDENCE/('activity_evaluate_'+endpoint+'.json')]=dict(mode='evaluate',arm=None,endpoint=endpoint)
        raw[(d.CORPUS,'cases',1694)]=cases
        def artifact(path):
            if path in reports:return reports[path]
            raise AssertionError('undeclared synthetic artifact:'+str(path))
        def digest(path):
            if path in hashes:return hashes[path]
            raise AssertionError('unapproved synthetic digest:'+str(path))
        def read_rows(directory,manifest,stem,count):
            key=(directory,stem,count)
            if key not in raw:raise AssertionError('undeclared synthetic cohort:'+str(key))
            return raw[key]
        def activity(path,**kwargs):
            self.assertIn(path,activities);wanted=activities[path]
            self.assertEqual((kwargs.get('mode'),kwargs.get('arm'),kwargs.get('endpoint')),
                (wanted['mode'],wanted['arm'],wanted['endpoint']))
            self.assertTrue(kwargs['completed']);return dict(complete=True)
        saved=[]
        with ExitStack() as stack:
            stack.enter_context(patch.object(d,'info',return_value=minimal))
            stack.enter_context(patch.object(d,'read_prepared',return_value=(frozen,None,course)))
            stack.enter_context(patch.object(d.base,'stage_report',side_effect=artifact))
            stack.enter_context(patch.object(d,'read_rows',side_effect=read_rows))
            stack.enter_context(patch.object(d,'digest',side_effect=digest))
            stack.enter_context(patch.object(d.original,'validate_groups',return_value=None))
            stack.enter_context(patch.object(d,'read_activity',side_effect=activity))
            stack.enter_context(patch.object(d,'write',side_effect=lambda p,v:saved.append((p,v))))
            stack.enter_context(patch('builtins.print'))
            stack.enter_context(patch.dict(sys.modules,tokenizers=SimpleNamespace(Tokenizer=SimpleNamespace(from_file=lambda path:tok))))
            self.assertEqual(d.readback(),0);self.assertEqual(saved[-1][1]['actual_answers'],8470)
            self.assertEqual(saved[-1][1]['status'],'FOUR_ARM_ACTUAL_READBACK_COMPLETE')
            for endpoint in d.ENDPOINTS:
                report=reports[d.EVIDENCE/('evaluate_'+endpoint)/'report.json']
                old=report['corpus_sha256'];report['corpus_sha256']='WRONG_SOURCE';before=len(saved)
                with self.assertRaises(ValueError):d.readback()
                self.assertEqual(len(saved),before);report['corpus_sha256']=old
            old=frozen['cases_sha256'];frozen['cases_sha256']='WRONG_CASES';before=len(saved)
            with self.assertRaises(ValueError):d.readback()
            self.assertEqual(len(saved),before);frozen['cases_sha256']=old
            report=reports[d.EVIDENCE/'train_fixed_last'/'report.json'];old=report['updates'];report['updates']=0
            with self.assertRaises(ValueError):d.readback()
            report['updates']=old


if __name__=='__main__':unittest.main(verbosity=2)
