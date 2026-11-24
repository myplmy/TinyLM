#!/usr/bin/env python3
"""DEV-only decoder choice and sealed FINAL dialogue evaluation.

Weights are exact ordered packet replays. Existing sample/serialization owns
every generated token. Neither DEV nor FINAL is used to fit a weight/value.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
import gc
import hashlib
import json
import time
import traceback

import tinylm
import torch
from scripts import diag_p108b_geometry as atlas
from scripts import diag_p108b_value_library as library
from scripts import diag_p108b_policy as policy_io
from scripts import p108b_policy as policy
from scripts import p108b_decode as decode
from scripts import p108b_replay as replay
from scripts.p108b_tinylm import TinyAdapter
from scripts import interactive_research_infer as manual
from scripts import p108_weight_space as metrics
from scripts.p106b_shards import ShardWriter

BASE=atlas.BASE
OUT=BASE/'evaluation_v1'
SOURCES=('scripts/diag_p108b_evaluate.py','scripts/test_p108b_evaluate.py',
         'scripts/p108b_decode.py','scripts/test_p108b_decode.py','scripts/p108b_replay.py','scripts/test_p108b_replay.py')


def seed_for(seed,ident):
    return int.from_bytes(hashlib.sha256(f'{seed}:{ident}'.encode('utf-8')).digest()[:4],'big')


def summarize(rows,required):
    dev=[r for r in rows if r['split']=='select_dev']
    protect=[r for r in rows if r['split']!='select_dev'and r['protected']]
    if len(dev)!=96 or len(protect)!=16:raise ValueError('exact96DEV and16legacy protection required')
    correct={r['id']for r in protect if r['exact']}
    return dict(dev=policy.dev_summary(dev),protected_correct=len(correct),
        lost_protected_ids=sorted(set(required)-correct),unwanted_loops=policy.unwanted_loops(rows),
        question_echoes=sum(r['diagnostics']['question_echo']for r in rows),
        empty=sum(r['diagnostics']['empty']for r in rows),items=len(rows))


def select_decoder(runs):
    candidates=[]
    for spec in decode.registered():
        records=[r for r in runs if r['decoder']==spec.name]
        expected=3 if spec.temperature else 1
        if len(records)!=expected:raise ValueError('complete prescribed seed panel required')
        summaries=[r['summary']for r in records];n=len(summaries)
        mean=lambda field:sum(s[field]for s in summaries)/n
        loss=sum(len(s['lost_protected_ids'])for s in summaries)/n
        content=sum(s['dev']['target_exact']+s['dev']['other_exact']for s in summaries)/n
        protection=mean('protected_correct')+sum(s['dev']['protected_exact']for s in summaries)/n
        key=(loss,-content,-protection,mean('unwanted_loops'),mean('question_echoes'),mean('empty'),
             0 if spec.name=='GREEDY'else 1,spec.name)
        candidates.append(dict(decoder=asdict(spec),mean_lost_protected=loss,mean_dev_content_exact=content,
            mean_protected_exact=protection,mean_unwanted_loops=mean('unwanted_loops'),key=list(key)))
    return dict(chosen=min(candidates,key=lambda r:tuple(r['key'])),candidates=candidates,
        rule='one global decoder per model; legacy protection,DEV content,protection,unwanted repetition; no FINAL')


def choose_weights():
    primary={s['name']for s in policy_io.verify()['primary']}
    batches=[json.loads(p.read_text(encoding='utf-8'))for p in policy_io.OUT.glob('batch_*.json')]
    closed=[r for r in batches if set(r['policy_names'])==primary and r['status']=='POLICY_BATCH_COMPLETE_QUALITY_REVIEW_SEPARATE'
            and r['registered_core_unchanged']and r['cuda_allocated_after_bytes']==r['cuda_reserved_after_bytes']==0]
    if not closed:raise ValueError('all18 primary arms and strict final cleanup required before model selection')
    if (BASE/'support_profile_v2.json').is_file():
        extra=json.loads((BASE/'support_v2/report.json').read_text(encoding='utf-8'))
        if (extra['status']!='SIX_SPARSE_CONTROLS_COMPLETE' or not extra['registered_core_unchanged'] or
                extra['cuda_allocated_after_bytes'] or extra['cuda_reserved_after_bytes']):
            raise ValueError('conditional sparse panel must close before FINAL selection')
        primary|={r['name']for r in extra['arms']}
    if (BASE/'regularizer_profile_v1.json').is_file():
        rp=json.loads((BASE/'regularizer_profile_v1.json').read_text(encoding='utf-8'))
        expected={s['name']for s in rp['primary']};closed_names=set()
        for path in (BASE/'regularizer_v1').glob('batch_*.json'):
            r=json.loads(path.read_text(encoding='utf-8'))
            if (r['status']=='POLICY_BATCH_COMPLETE_QUALITY_REVIEW_SEPARATE'and r['registered_core_unchanged']and
                    r['cuda_allocated_after_bytes']==r['cuda_reserved_after_bytes']==0):closed_names.update(r['policy_names'])
        if closed_names!=expected:raise ValueError('both regularizer modes must close before FINAL')
        primary|=expected
    primary|={f'atlas_layer{i:02d}'for i in range(14)}
    original=replay.read_arm('original')
    required={r['id']for r in original['answers']if r['split']!='select_dev'and r['protected']and r['exact']}
    records={}
    for name in sorted(primary):
        arm=replay.read_arm(name);summary=summarize([r for r in arm['answers']if r['split']=='select_dev'or r['protected']],required)
        d=summary['dev']
        key=(len(summary['lost_protected_ids']),-d['target_exact']-d['other_exact'],
             -summary['protected_correct']-d['protected_exact'],summary['unwanted_loops'],
             summary['question_echoes'],summary['empty'],name)
        records[name]=dict(name=name,summary=summary,key=list(key),core_sha256=arm['core_sha256'])
    fixed=[f'{prefix}{n}'for prefix in ('SAME','SEQ','EQUAL')for n in (2,4)]
    fixed.extend(f'atlas_layer{i:02d}'for i in range(14))
    fixed.extend(n for n in primary if n.startswith(('REGINC_','REGTOTAL_'))and n.endswith('SAME4'))
    adaptive=[n for n in primary if n.startswith(('ADAPT_','SINGLE1_SPARSE','SELECT_'))or
              (n.startswith(('REGINC_','REGTOTAL_'))and n.endswith('ADAPT_R4'))]
    best_fixed=min(fixed,key=lambda n:tuple(records[n]['key']))
    best_adaptive=min(adaptive,key=lambda n:tuple(records[n]['key']))
    return dict(arms=['original','SINGLE1',best_fixed,best_adaptive],selection_records=records,
        rule='frozen loss-best single9 control plus best feasible full14 single/fixed and adaptive/selective states; per-case protection before DEV content')


def prepare():
    selected=choose_weights();parent=policy_io.verify();refs={}
    for path in sorted(policy_io.OUT.rglob('*')):
        if path.is_file():refs[str(path.relative_to(atlas.ROOT))]=manual.file_sha(path)
    sources=dict(parent['sources']);sources.update({name:manual.file_sha(atlas.ROOT/name)for name in SOURCES})
    if (BASE/'support_profile_v2.json').is_file():
        extra=json.loads((BASE/'support_profile_v2.json').read_text(encoding='utf-8'));sources.update(extra['sources'])
        paths=[BASE/'support_profile_v2.json',BASE/'support_initial_plan_v2.md']+sorted((BASE/'support_v2').rglob('*'))
        for path in paths:
            if path.is_file():refs[str(path.relative_to(atlas.ROOT))]=manual.file_sha(path)
    if (BASE/'regularizer_profile_v1.json').is_file():
        extra=json.loads((BASE/'regularizer_profile_v1.json').read_text(encoding='utf-8'));sources.update(extra['sources'])
        paths=[BASE/'regularizer_profile_v1.json',BASE/'regularizer_initial_plan_v1.md']+sorted((BASE/'regularizer_v1').rglob('*'))
        for path in paths:
            if path.is_file():refs[str(path.relative_to(atlas.ROOT))]=manual.file_sha(path)
    profile=dict(schema='P108B_DEV_DECODE_FINAL_V1',authority_directive=140,deadline=library.DEADLINE.isoformat(),
        model=parent['model'],origin=parent['origin'],sources=sources,references=refs,**selected,
        policy_profile_sha256=manual.file_sha(BASE/'policy_profile_v1.json'),
        final_data_sha256=manual.file_sha(BASE/'final_language.json'),select_data_sha256=manual.file_sha(BASE/'select_dev.json'),
        decoders=[asdict(s)for s in decode.registered()],stochastic_seeds=[17,29,43],
        seeds_matched_by='SHA256(seed:questionID), same across models/settings',max_new_dev=64,max_new_final=128,
        initial_final_cases=192,actual_final_user_turns=240,final_answers_consumed=False,
        main_final_regime='common GREEDY for all four weight states',
        secondary_final_regime='DEV-selected decoder if different;3seeds for stochastic',
        final_role='held out from weight and decoder selection; actual self-generated dialogue history',
        body_optimizer_updates=0,value_optimizer_updates=0,checkpoint_writes=0,
        source_role_map=dict(legacy_fit='FIT_ONLY',legacy_protection='REUSED_HISTORY_DEVELOPMENT_GUARD_NOT_NEW_TEST',
            select_dev='SELECT_DEV_ONLY',final_language='FINAL_ONLY_NO_WEIGHT_OR_DECODER_FITTING'),
        initial_plan_sha256=manual.file_sha(atlas.ROOT/library.PLAN))
    library.write_new(BASE/'evaluation_profile_v1.json',profile)
    with (BASE/'evaluation_initial_plan_v1.md').open('xb')as stream:stream.write((atlas.ROOT/library.PLAN).read_bytes())
    print('[EVALUATION_PREPARED] '+json.dumps(dict(arms=profile['arms'],final_answers_consumed=False)),flush=True)


def verify():
    policy_io.verify();p=json.loads((BASE/'evaluation_profile_v1.json').read_text(encoding='utf-8'));library.Budget().check()
    for name,sha in dict(p['sources'],**p['references']).items():
        if manual.file_sha(atlas.ROOT/name)!=sha:raise ValueError('sealed evaluation input changed: '+name)
    for name,key in [('policy_profile_v1.json','policy_profile_sha256'),('select_dev.json','select_data_sha256'),
                     ('final_language.json','final_data_sha256'),('evaluation_initial_plan_v1.md','initial_plan_sha256')]:
        if manual.file_sha(BASE/name)!=p[key]:raise ValueError('sealed evaluation role/data/plan changed')
    return p


def choose():
    p=verify();records={}
    for name in p['arms']:
        path=OUT/'decode'/name/'report.json';r=json.loads(path.read_text(encoding='utf-8'))
        if r['status']!='DECODE_COMPLETE_QUALITY_SEPARATE'or not r['original_restored']or r['cuda_allocated_after_bytes']or r['cuda_reserved_after_bytes']:
            raise ValueError('all model decoder panels must close with original/CUDA proof')
        records[name]=dict(source_report_sha256=manual.file_sha(path),**select_decoder(r['runs']))
    library.write_new(BASE/'decode_selection_v1.json',dict(schema=p['schema'],models=records,final_answers_consumed=False,
        evaluation_profile_sha256=manual.file_sha(BASE/'evaluation_profile_v1.json')))
    print('[DECODERS_FROZEN] '+json.dumps({n:r['chosen']['decoder']['name']for n,r in records.items()}),flush=True)


def generated(active,row,spec,seed,max_new,history=()):
    answer,generation=decode.emit(active,row['question'],spec,seed=seed_for(seed,row['id']),max_new=max_new,history=history)
    tail=len(generation['terminal_ids']);ids=generation['generated_ids'][:-tail]if tail else generation['generated_ids']
    return dict(row,answer=answer,generation=generation,decoder=asdict(spec),seed=seed,
        exact=None if row.get('expected')is None else metrics.exact_answer(answer,row['expected']),
        diagnostics=metrics.repetition_metrics(ids,answer,row['question']),actual_history=list(history))


def dialogue(rows,emit):
    """Actual model answers, never expected answers, become later context."""
    for row in rows:
        history=[];first=dict(row,turn=1);answer=emit(first,history);yield answer
        history.extend([dict(role='user',content=first['question']),dict(role='assistant',content=answer['answer'])])
        for j,question in enumerate(row.get('followups',[]),start=2):
            follow=dict(row,id=row['id']+f':turn{j}',question=question,expected=None,turn=j,followup_of=row['id'])
            answer=emit(follow,list(history));yield answer
            history.extend([dict(role='user',content=question),dict(role='assistant',content=answer['answer'])])


def execute(phase,names):
    p=verify();names=names or p['arms']
    if len(names)!=len(set(names))or any(n not in p['arms']for n in names):raise ValueError('only frozen selected model names allowed')
    if phase=='final':
        selection=json.loads((BASE/'decode_selection_v1.json').read_text(encoding='utf-8'))
        if selection['final_answers_consumed']or selection['evaluation_profile_sha256']!=manual.file_sha(BASE/'evaluation_profile_v1.json'):
            raise ValueError('pre-FINAL decoder selection required')
        final=json.loads((BASE/'final_language.json').read_text(encoding='utf-8'))
        if final['role']!='FINAL_EVALUATION_ONLY_NOT_EDITOR_INPUT'or len(final['rows'])!=192:raise ValueError('sealed FINAL role/count required')
    budget=library.Budget(10800);torch.set_num_threads(4)
    data=json.loads((BASE/'data.json').read_text(encoding='utf-8'));fits=[r for r in data['rows']if r['split']=='fit']
    for name in names:
        budget.check();directory=OUT/phase/name
        if directory.exists():raise FileExistsError('prior evaluation attempt preserved; no overwrite')
        directory.mkdir(parents=True);started=time.monotonic();adapter=active=None;failure=None
        result=dict(schema=p['schema'],name=name,phase=phase,status='STARTED',new_generated_calls=0,
            source_profile_sha256=manual.file_sha(BASE/'evaluation_profile_v1.json'),runs=[],
            body_optimizer_updates=0,value_optimizer_updates=0,checkpoint_writes=0)
        try:
            result['entry_resources']=library.resources();arm=replay.read_arm(name)
            with manual.selected_runtime(manual.resolve_model(p['model']))as active:
                adapter=TinyAdapter(active,fits,data['calibration_questions'],budget=budget)
                torch.cuda.reset_peak_memory_stats()
                try:
                    with replay.install(adapter,arm)as proof:
                        result['weight_replay']=proof
                        canary=adapter.generate(arm['answers'][0],max_new=64,variant=name+':REPLAY_CANARY')
                        if canary['generation']['generated_ids']!=arm['answers'][0]['generation']['generated_ids']:
                            raise RuntimeError('saved greedy token replay canary differs')
                        result['replay_canary']=canary;result['new_generated_calls']+=1
                        writer=ShardWriter(directory,'answers',limit=3_000_000)
                        if phase=='decode':
                            rows=[r for r in data['rows']if r['protected']]+json.loads((BASE/'select_dev.json').read_text(encoding='utf-8'))['rows']
                            required={r['id']for r in arm['answers']if r['split']!='select_dev'and r['protected']and r['exact']}
                            for spec in decode.registered():
                                seeds=p['stochastic_seeds']if spec.temperature else[17]
                                for seed in seeds:
                                    answers=[]
                                    for row in rows:
                                        budget.check()
                                        if spec.name=='GREEDY':
                                            answer=dict(next(r for r in arm['answers']if r['id']==row['id']),decoder=asdict(spec),seed=seed,reused_exact_saved_generation=True)
                                        else:
                                            answer=generated(active,row,spec,seed,p['max_new_dev']);result['new_generated_calls']+=1
                                        answers.append(answer);writer.append(answer)
                                    result['runs'].append(dict(decoder=spec.name,seed=seed,summary=summarize(answers,required)))
                                    print('[DECODE_PANEL] '+json.dumps(dict(name=name,decoder=spec.name,seed=seed,
                                        summary=result['runs'][-1]['summary'])),flush=True)
                            result['status']='DECODE_COMPLETE_QUALITY_SEPARATE'
                        else:
                            selected_spec=decode.Decoder(**selection['models'][name]['chosen']['decoder'])
                            regimes=[('COMMON_GREEDY',decode.Decoder('GREEDY'),17)]
                            if selected_spec.name!='GREEDY':
                                regimes.extend(('DEV_SELECTED',selected_spec,seed)for seed in(p['stochastic_seeds']if selected_spec.temperature else[17]))
                            for regime,spec,seed in regimes:
                                answers=[]
                                def emit(row,history):
                                    budget.check();answer=generated(active,row,spec,seed,p['max_new_final'],history)
                                    answer.update(evaluation_regime=regime,variant=name)
                                    result['new_generated_calls']+=1;return answer
                                for answer in dialogue(final['rows'],emit):answers.append(answer);writer.append(answer)
                                if len(answers)!=240:raise RuntimeError('complete actual240 dialogue calls required')
                                result['runs'].append(dict(regime=regime,decoder=asdict(spec),seed=seed,summary=metrics.summarize(answers),
                                    initial_summary=metrics.summarize([r for r in answers if r['turn']==1]),
                                    followup_summary=metrics.summarize([r for r in answers if r['turn']>1]),
                                    unwanted_loops=policy.unwanted_loops(answers),root_language_review='NOT_YET_READ'))
                                print('[FINAL_PANEL] '+json.dumps(dict(name=name,regime=regime,seed=seed,
                                    summary=result['runs'][-1]['summary'])),flush=True)
                            result['decoder_selection_sha256']=manual.file_sha(BASE/'decode_selection_v1.json')
                            result['status']='FINAL_GENERATION_COMPLETE_LANGUAGE_REVIEW_PENDING'
                        result['answers_manifest']=writer.close(lineage=dict(arm=name,phase=phase,core_sha256=arm['core_sha256']))
                        result['peak_allocated_mib']=torch.cuda.max_memory_allocated()/2**20
                        result['peak_reserved_mib']=torch.cuda.max_memory_reserved()/2**20
                        result['model_forward_counts']=dict(adapter.counts)
                    result['original_restored']=proof['original_core_restored']
                finally:
                    if adapter is not None:adapter.close();adapter=None
        except BaseException as error:
            failure=error;result.update(status='EVALUATION_ERROR',error=str(error),traceback=traceback.format_exc())
        finally:
            active=adapter=None;gc.collect();cleanup_error=library.cleanup(result)
            if failure is None:failure=cleanup_error
            result['wall_seconds']=time.monotonic()-started;library.write_new(directory/'report.json',result)
            print('[EVALUATION_MODEL_END] '+json.dumps({k:result.get(k)for k in('name','phase','status','new_generated_calls','wall_seconds','cuda_allocated_after_bytes','cuda_reserved_after_bytes','error')}),flush=True)
        if failure is not None:raise RuntimeError('preserved evaluation failure')from failure


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','check','decode','select','final']);parser.add_argument('--arms',nargs='+')
    args=parser.parse_args()
    if args.phase=='prepare':prepare()
    elif args.phase=='check':verify();print('[EVALUATION_CHECK] pinned CPU/source/role checks; no model')
    elif args.phase=='select':choose()
    else:execute(args.phase,args.arms)


if __name__=='__main__':main()
