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


if __name__=='__main__':unittest.main(verbosity=2)
