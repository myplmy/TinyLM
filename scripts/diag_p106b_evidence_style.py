#!/usr/bin/env python3
"""Posthoc same-fact first-answer wording control; never trains or changes defaults."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter
from datetime import datetime,timezone
import gc
import json
import time
from scripts import diag_p106b_evidence_preference_evaluate as prior
from scripts.p106b_shards import ShardWriter,verify
from scripts.p106b_gate_runtime import GateNegative,idle_before_gpu,wall_limit
course=prior.course
method=prior.method
TAG='p106b_evidence_style_v1_s1337'
OUTPUT=ROOT/'HF/sft_ready'/TAG
EVIDENCE=ROOT/'test_result/evidence'/TAG
LOCAL=ROOT/'test_result/evidence/local'/TAG
SELECTION=course.EVIDENCE/'manual_selection_before_answers.json'
CODE=(*prior.CODE,'scripts/diag_p106b_evidence_style.py','scripts/test_p106b_evidence_style.py')
SUCCESS_CRITERION='All96 style3 first-answer anchors exactly replay; fixed192 outputs, no weight changes. Not semantic quality PASS.'


def info():
    return dict(schema='P106B_EVIDENCE_WORDING_CONTROL_V1',tag=TAG,
        code_sha256={p:course.training.data.digest(ROOT/p) for p in sorted(set(CODE))},
        selection_sha256=course.training.data.digest(SELECTION),
        source_course_sha256=course.training.data.digest(course.CORPUS/'report.json'),
        selection='same already-read fixed4 neutral groups, all32 language/condition children',
        scope='POSTHOC_DEV, wording bundle0 versus3; facts/masks/targets/checkpoints unchanged',
        neutral_groups=4,cases=32,views=[0,3],endpoints=['parent',*course.ARMS],actual_answers=192,
        independent_new_style0_answers=96,exact_replay_style3_answers=96,
        generation='same FP32_MATH greedy64/cache/EOT as completed primary evaluation',
        optimizer_updates=0,teacher_calls=0,checkpoint_written=False,student_mtp=False,
        memory_feature=False,formal_train_ready=False,general_intelligence='NOT_ESTABLISHED')


def text(message):
    return ''.join(x['text'] for x in message['content'])


def views(row,tok):
    from tinylm.chat.serialize import serialize
    meta=row['meta'];out={}
    for style in (0,3):
        other=course.method.previous.make(meta['producer_graph'],meta['language'],meta['condition'],True,style,tok)
        if other['messages'][1]!=row['messages'][1] or other['meta']['first_available_keys']!=meta['first_available_keys']:
            raise ValueError('same answer and available facts required')
        if style==3 and other['messages'][0]!=row['messages'][0]:raise ValueError('exact original style3 input required')
        messages=other['messages'][:1];tokens=len(tok.encode(serialize(dict(messages=messages),'chatml',add_generation_prompt=True)).ids)
        if tokens+64>1024:raise ValueError('complete prompt and64 output budget required')
        out[str(style)]=dict(messages=messages,prompt_tokens=tokens)
    return dict(root=meta['semantic_root_id'],neutral_root=meta['neutral_root'],language=meta['language'],
        family=meta['family'],condition=meta['condition'],sufficient=meta['query_sufficient'],
        omitted=meta['omitted_key'],requested_field=meta['requested_fields'][0],gold=text(row['messages'][1]),views=out)


def anchor_check(event,anchor):
    if any(event[k]!=anchor[k] for k in ('messages','answer','gold')):raise ValueError('fixed style3 first-answer replay differs')
    for key in ('prompt_tokens','actual_max_new','finish_reason'):
        if event['generation'].get(key)!=anchor['generation'].get(key):raise ValueError('style3 generation contract differs')


def summarize(events):
    out={}
    for style in (0,3):
        lane=[x for x in events if x['style']==style]
        for intent,subset in (('all',lane),('ANSWER',[x for x in lane if x['sufficient']]),
                             ('ASK_PROXY',[x for x in lane if not x['sufficient']])):
            count=Counter()
            for e in subset:
                if prior.method.source.score(e)!=e['scores']:raise ValueError('raw first-answer score mismatch')
                count.update(e['scores'])
            out[str(style)+'/'+intent]=dict(count)
    return out


def can_start(now,deadline,limit):
    return (now.hour,now.minute)<(7,15) and (deadline-now).total_seconds()>=limit+2700


def freeze():
    if OUTPUT.exists() or EVIDENCE.exists() or OUTPUT.is_symlink() or EVIDENCE.is_symlink():raise GateNegative('old wording outputs preserved')
    frozen=course.producer.required(course.CORPUS/'report.json')
    chosen=set(course.producer.required(SELECTION)['selected'].values())
    rows=[r for r in course.training.data.stream_rows(course.CORPUS,frozen['manifests']['test_evidence']) if r['meta']['neutral_root'] in chosen]
    tok=course.upstream.old._tokenizer();cases=[views(r,tok) for r in rows]
    if len(cases)!=32 or len({r['root'] for r in cases})!=32 or len(chosen)!=4:raise ValueError('same fixed4/all32 children required')
    OUTPUT.mkdir(parents=True,exist_ok=False);writer=ShardWriter(OUTPUT,'inputs')
    for row in cases:writer.append(row)
    manifest=writer.close(lineage=info());verify(OUTPUT,manifest)
    report=dict(info(),status='WORDING_CONTROL_INPUTS_FROZEN',manifest=manifest,
        prompt_token_range=[min(v['prompt_tokens'] for r in cases for v in r['views'].values()),
                            max(v['prompt_tokens'] for r in cases for v in r['views'].values())])
    course.training.write(OUTPUT/'report.json',report);course.training.write(EVIDENCE/'inputs.json',report)
    print('[WORDING_INPUTS] '+json.dumps(dict(cases=32,view_inputs=64,prompt_range=report['prompt_token_range'])));return 0


def run(a):
    import torch
    from tinylm.infer.generate import _strip
    report=course.producer.required(OUTPUT/'report.json')
    if report['code_sha256']!=info()['code_sha256']:raise ValueError('wording CODE changed')
    verify(OUTPUT,report['manifest']);cases=list(course.training.data.stream_rows(OUTPUT,report['manifest']))
    completed=course.producer.required(prior.EVIDENCE/'report.json')
    recounted=course.producer.required(prior.EVIDENCE/'paired_readback.json')
    if completed['status']!='EVIDENCE_PREFERENCE_ACTUAL_EVALUATED' or recounted['status']!='EVIDENCE_PREFERENCE_RAW_RECOUNTED':
        raise GateNegative('complete primary actual and raw recount required')
    if completed['code_sha256']!=prior.info()['code_sha256']:raise ValueError('primary frozen CODE changed')
    target=EVIDENCE/'evaluate'
    if target.exists() or LOCAL.exists():raise GateNegative('old wording actual preserved')
    now=datetime.now(timezone.utc);deadline=course.producer.original.prior.producer.legacy.source.DEADLINE
    if not can_start(now,deadline,a.max_wall_sec):
        raise GateNegative('new GPU before16:15KST and45minute closure margin required')
    idle_before_gpu();started=time.perf_counter();target.mkdir(parents=True,exist_ok=False);endpoints={}
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    with wall_limit(a.max_wall_sec):
        for arm in ('parent',*course.ARMS):
            torch,model,cfg,tok,_,_=prior.training.load_parent()
            source=completed['endpoints'][arm];path=ROOT/source['checkpoint']
            if course.training.data.digest(path)!=source['checkpoint_sha256']:raise ValueError('fixed endpoint weight changed')
            if arm!='parent':
                saved=torch.load(path,map_location='cpu',weights_only=True)
                model.load_state_dict(_strip(saved['model']),strict=True);del saved
            if cfg.max_seq_len!=1024:raise ValueError('same original1024 context')
            initial=course.training.state_fingerprint(model)
            if initial!=source['core_before_after_sha256']:raise ValueError('same actual endpoint core required')
            oldevents=prior.read_values(source['metrics']['evidence_test'])
            anchors={e['root']:e for e in oldevents if e['turn']==1 and e['history']=='ACTUAL_MODEL'}
            model=model.cuda();torch.cuda.reset_peak_memory_stats();model.eval();model.freeze_quant()
            emit=prior.previous.old_eval.reference.generation.emit_function(model,cfg,tok)
            writer=ShardWriter(LOCAL/arm,'wording');events=[]
            try:
                with torch.no_grad():
                    for i,row in enumerate(cases):
                        for style in ((0,3) if i%2==0 else (3,0)):
                            view=row['views'][str(style)];answer,generation=emit(view['messages'])
                            event={k:v for k,v in row.items() if k!='views'}
                            event.update(style=style,messages=view['messages'],answer=answer,generation=generation,
                                turn=1,history='ACTUAL_MODEL',source_truth='GIVEN_FICTIONAL_FIELDS_ONLY')
                            event['scores']=prior.method.source.score(event)
                            if style==3:anchor_check(event,anchors[row['root']])
                            writer.append(event);events.append(event)
            finally:model.clear_quant();model.train()
            manifest=writer.close(lineage=info());verify(LOCAL/arm,manifest)
            if len(events)!=64 or course.training.state_fingerprint(model)!=initial:raise ValueError('exact64 unchanged-body outputs required')
            endpoints[arm]=dict(checkpoint=source['checkpoint'],checkpoint_sha256=source['checkpoint_sha256'],
                core_before_after_sha256=initial,directory=str((LOCAL/arm).relative_to(ROOT)),manifest=manifest,
                counts=summarize(events),style3_exact_replays=32,peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20)
            print('[WORDING_ENDPOINT] '+json.dumps(dict(arm=arm,counts=endpoints[arm]['counts'])),flush=True)
            del model;gc.collect();torch.cuda.empty_cache()
    result=dict(info(),status='WORDING_CONTROL_ACTUAL_REPLAY_VERIFIED',
        primary_report_sha256=course.training.data.digest(prior.EVIDENCE/'report.json'),
        paired_report_sha256=course.training.data.digest(prior.EVIDENCE/'paired_readback.json'),
        endpoints=endpoints,whole_sec=time.perf_counter()-started)
    course.training.write(target/'report.json',result);return 0


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=('freeze','evaluate'),required=True)
    p.add_argument('--max-wall-sec',type=int,default=600)
    g=p.add_mutually_exclusive_group(required=True);g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true');a=p.parse_args()
    if not 60<=a.max_wall_sec<=600:p.error('explicit60..600 bound')
    if a.check_only:print('[WORDING_CHECK] '+json.dumps(info()));return 0
    try:
        course.producer.original.prior.producer.legacy.source.deadline()
        return freeze() if a.mode=='freeze' else run(a)
    except GateNegative as exc:print('[WORDING_HOLD] '+str(exc));return 8
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[WORDING_ERROR] '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
