#!/usr/bin/env python3
"""Post-primary repeated-question controls and prelocked DEV checkpoint reading."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
import copy
from datetime import datetime,timezone
import gc
import json
import time
from scripts import p106b_dualqa_dialogue_controls as control
from scripts import diag_p106b_dualqa_eval as primary
from scripts import diag_p106b_dualqa_checkpoint_choice as selector
from scripts import summarize_p106b_dualqa_eval as paired
from scripts.p106b_gate_runtime import GateNegative,idle_before_gpu,wall_limit
from scripts.p106b_shards import ShardWriter
course=primary.course
EVIDENCE=course.EVIDENCE/'followup'
LOCAL=primary.LOCAL/'followup'
CODE=('scripts/p106b_dualqa_dialogue_controls.py','scripts/test_p106b_dualqa_dialogue_controls.py','scripts/diag_p106b_dualqa_followup.py')


def metadata():
    return dict(schema='P106B_DUALQA_FROZEN_FOLLOWUP_V1',tag=course.TAG,
        code_sha256={p:course.training.data.digest(ROOT/p) for p in CODE},
        primary_final4epoch_unchanged=True,selection_rule='prelocked source DEV only',
        precision='FP32_MATH',temperature=0,top_k=1,max_new=64,
        actual_answers_per_pattern_endpoint=1024,gold_second_answers_per_pattern_endpoint=512,
        teacher_calls=0,optimizer_updates=0,new_checkpoints=0,auxiliary_in_inference=False,
        semantic_truth='NOT_RUN',normal_repeat_answers_allowed=True)


def prerequisites():
    frozen,rows,labels=course.read_course();lock=course.producer.legacy.source.required(selector.TARGET)
    if lock['schema']!='P106B_DUALQA_DEV_SELECTION_LOCK_V1' or lock['tag']!=course.TAG or lock['primary_test_started']:
        raise ValueError('pre-TEST DEV selection required')
    for path,sha in lock['code_sha256'].items():
        if course.training.data.digest(ROOT/path)!=sha:raise ValueError('prelocked selection code changed')
    for arm,ref in lock['training_report_refs'].items():
        if course.training.data.digest(ROOT/ref['path'])!=ref['sha256']:raise ValueError('prelocked training report changed')
    p=course.producer.legacy.source.required(primary.EVIDENCE/'report.json')
    if p['status']!='DUALQA_FRESH_ACTUAL_HISTORY_EVALUATED' or p['corpus_report_sha256']!=lock['corpus_report_sha256']:
        raise ValueError('complete primary same-course evaluation required')
    if p['code_sha256']!=primary.metadata()['code_sha256']:raise ValueError('primary evaluation implementation changed')
    return p,rows,lock


def endpoint(cp,sha,arm,epoch):
    return dict(checkpoint=cp,checkpoint_sha256=sha,arm=arm,epoch=epoch)


def load(item):
    import torch
    from tinylm.infer.generate import _strip
    if course.training.data.digest(ROOT/item['checkpoint'])!=item['checkpoint_sha256']:raise ValueError('selected weights changed')
    torch,model,cfg,tok,initial=course.load_parent()
    if item['epoch']:
        saved=torch.load(ROOT/item['checkpoint'],map_location='cpu',weights_only=True)
        if saved['curriculum']!=dict(tag=course.TAG,arm=item['arm'],epoch=item['epoch']) or saved['step']!=44*item['epoch']:
            raise ValueError('exact selected curriculum lineage required')
        if saved['tokenizer_sha256']!=course.training.data.TOK_SHA:raise ValueError('same tokenizer required')
        model.load_state_dict(_strip(saved['model']),strict=True);del saved
    elif item['checkpoint_sha256']!=course.producer.PARENT_SHA:
        raise ValueError('parent label must reference Source0')
    before=course.training.state_fingerprint(model)
    return torch,model.cuda(),cfg,tok,before


def evaluate(mode,args):
    import torch
    p,rows,lock=prerequisites();target=EVIDENCE/mode;local=LOCAL/mode
    if target.exists() or local.exists():raise GateNegative('old followup output preserved')
    references={}
    if mode=='repeat':
        items={a:endpoint(p['endpoints'][a]['checkpoint'],p['endpoints'][a]['checkpoint_sha256'],a,0 if a=='parent' else 4) for a in ('parent','repeat','contrast')}
    else:
        refs=course.producer.legacy.source.required(EVIDENCE/'repeat/report.json')
        if refs['status']!='DUALQA_FOLLOWUP_EVALUATED' or refs['mode']!='repeat':raise ValueError('repeat-control endpoints required before DEV candidates')
        if refs['selection_sha256']!=course.training.data.digest(selector.TARGET):raise ValueError('same locked choices required')
        if refs['code_sha256']!=metadata()['code_sha256'] or refs['primary_report_sha256']!=course.training.data.digest(primary.EVIDENCE/'report.json'):
            raise ValueError('same frozen repeat control and primary report required')
        references=refs['endpoints']
        items={a:endpoint(v['checkpoint'],v['checkpoint_sha256'],a,v['epoch']) for a,v in lock['choices'].items()}
    needs_gpu=mode=='repeat' or any(v['epoch']!=4 for v in items.values())
    if needs_gpu:idle_before_gpu()
    target.mkdir(parents=True,exist_ok=False);began=time.perf_counter();results={};loaded=0
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    with wall_limit(args.max_wall_sec):
        for arm,item in items.items():
            course.producer.legacy.source.deadline()
            if mode=='devbest' and item['epoch']==4:
                base=p['endpoints'][arm];repeat=references[arm]
                if base['checkpoint_sha256']!=item['checkpoint_sha256'] or repeat['checkpoint_sha256']!=item['checkpoint_sha256']:raise ValueError('reuse requires identical final weights')
                values=dict(base['metrics']);values['source_mixed']=values.pop('source');values['source_repeat']=repeat['metrics']['source_repeat']
                value=dict(item,metrics=values,reused_primary_final=True,new_model_loaded=False)
            else:
                torch,model,cfg,tok,before=load(item);loaded+=1;directory=local/arm
                print('[DUALQA_FOLLOWUP_BEGIN] '+json.dumps(dict(mode=mode,arm=arm,epoch=item['epoch'],checkpoint_sha256=item['checkpoint_sha256'])),flush=True)
                values={}
                if mode=='devbest':values['source_mixed']=control.source(model,cfg,tok,rows['test_source'],directory,arm,'contrast',metadata())
                values['source_repeat']=control.source(model,cfg,tok,rows['test_source'],directory,arm,'repeat',metadata())
                if mode=='devbest':
                    values.update(public_bridge=primary.legacy.generate(model,cfg,tok,rows['test_bridge'],directory,'bridge256'),
                        known_code_development=primary.legacy.generate(model,cfg,tok,rows['code_retention_dev'],directory,'code_dev640'),
                        native=course.training.native_ce(model,course.NATIVE))
                    from scripts.p106b_education_followup import answers
                    from scripts.diag_p101a_mtp_parity import PrecisionForward
                    values['legacy8']=answers(PrecisionForward(model,'fp32_math'),cfg,tok,directory,'legacy8')
                if course.training.state_fingerprint(model)!=before:raise ValueError('followup changed body parameters')
                value=dict(item,metrics=values,core_before_after_sha256=before,reused_primary_final=False,new_model_loaded=True)
                del model;gc.collect();torch.cuda.empty_cache()
            results[arm]=value;course.training.write(target/(arm+'_report.json'),dict(metadata(),mode=mode,endpoint=value))
            print('[DUALQA_FOLLOWUP_ENDPOINT] '+json.dumps(dict(mode=mode,arm=arm,epoch=item['epoch'],
                source_repeat=value['metrics']['source_repeat']['counts'],semantic_truth='NOT_RUN')),flush=True)
    result=dict(metadata(),status='DUALQA_FOLLOWUP_EVALUATED',mode=mode,endpoints=results,loaded_models=loaded,
        selection_sha256=course.training.data.digest(selector.TARGET),primary_report_sha256=course.training.data.digest(primary.EVIDENCE/'report.json'),
        whole_sec=time.perf_counter()-began,checkpoint_selection_not_changed=True)
    course.training.write(target/'report.json',result)
    print('[DUALQA_FOLLOWUP_FINAL] '+json.dumps(dict(status=result['status'],mode=mode,loaded_models=loaded,
        whole_sec=result['whole_sec'],semantic_truth='NOT_RUN',optimizer_updates=0,new_checkpoints=0)),flush=True)
    return 0


def readback():
    p,rows,lock=prerequisites();rep=course.producer.legacy.source.required(EVIDENCE/'repeat/report.json')
    dev=course.producer.legacy.source.required(EVIDENCE/'devbest/report.json');path=EVIDENCE/'joint_readback.json'
    if path.exists():raise GateNegative('old joint readback preserved')
    for r in (rep,dev):
        if r['selection_sha256']!=course.training.data.digest(selector.TARGET) or r['code_sha256']!=metadata()['code_sha256']:raise ValueError('same frozen followup reports required')
        if r['primary_report_sha256']!=course.training.data.digest(primary.EVIDENCE/'report.json'):raise ValueError('same primary source report required')
    panels={};counts={}
    for label,item in p['endpoints'].items():
        panels[label]={'contrast':paired.indexed(paired.load(item['metrics']['source'])),
            'repeat':paired.indexed(paired.load(rep['endpoints'][label]['metrics']['source_repeat']))}
    for arm,item in dev['endpoints'].items():
        panels[arm+'_devbest']={'contrast':paired.indexed(paired.load(item['metrics']['source_mixed'])),
            'repeat':paired.indexed(paired.load(item['metrics']['source_repeat']))}
    behaviours={name:control.behaviour(value['contrast'],value['repeat']) for name,value in panels.items()}
    comparisons={}
    for left,right in (('parent','repeat'),('parent','contrast'),('repeat','contrast'),
                       ('repeat','repeat_devbest'),('contrast','contrast_devbest'),('repeat_devbest','contrast_devbest')):
        comparisons[left+'_to_'+right]={}
        for pattern in control.PATTERNS:
            comparisons[left+'_to_'+right][pattern]={lang or 'all':paired.compare(panels[left][pattern],panels[right][pattern],language=lang) for lang in (None,'ko','en')}
    # Same predeclared eight source roots as the primary readback, never failure-picked.
    primary_readback=course.producer.legacy.source.required(primary.EVIDENCE/'paired_readback.json')
    sample=list(course.training.data.stream_rows(ROOT/primary_readback['sample8_directory'],primary_readback['sample8_manifest']))
    if len(sample)!=8:raise ValueError('fixed primary sample8 required')
    writer=ShardWriter(LOCAL/'fixed_sample8','review')
    for original in sample:
        root=original['root'];item=copy.deepcopy(original)
        item['all_model_answers']={label:{pattern:[values[pattern][root,0,t,'ACTUAL_MODEL']['answer'] for t in (1,2)] for pattern in control.PATTERNS} for label,values in panels.items()}
        item['scope']='8source contexts/up to5endpoint labels/two patterns; aliases may share weights; nonblind review NOT_RUN, no semantic grade'
        writer.append(item)
    manifest=writer.close(lineage=dict(selection='same locked primary sample8 roots and order0; independent of correctness'))
    result=dict(metadata(),status='RAW_DOCUMENTS_RECHECKED',models=list(panels),behaviour=behaviours,comparisons=comparisons,
        selected_epochs={a:v['epoch'] for a,v in lock['choices'].items()},primary_final4epoch_unchanged=True,
        same_selected_epoch_exposure=lock['choices']['repeat']['epoch']==lock['choices']['contrast']['epoch'],
        secondary_is_not_test_best_selection=True,sample8_manifest=manifest,sample8_directory=str((LOCAL/'fixed_sample8').relative_to(ROOT)),
        input_sha256=dict(primary=course.training.data.digest(primary.EVIDENCE/'report.json'),
            repeat=course.training.data.digest(EVIDENCE/'repeat/report.json'),devbest=course.training.data.digest(EVIDENCE/'devbest/report.json'),
            selection=course.training.data.digest(selector.TARGET)),
        scope='document-root conditional model comparisons; not training-seed variance, world truth or blanket anti-repetition',models_loaded=0)
    course.training.write(path,result);print('[DUALQA_FOLLOWUP_READBACK] '+json.dumps(dict(behaviour=behaviours,selected_epochs=result['selected_epochs'])),flush=True)
    return 0


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=('repeat','devbest','readback'),required=True)
    p.add_argument('--max-wall-sec',type=int,default=7200);p.add_argument('--execute',action='store_true');a=p.parse_args()
    if not a.execute:p.error('explicit execution required')
    if not 60<=a.max_wall_sec<=14400:p.error('bounded60..14400')
    if a.mode=='readback' and a.max_wall_sec!=7200:p.error('nondefault GPU wall applies only to evaluation')
    try:
        course.producer.legacy.source.deadline()
        if a.mode=='readback':return readback()
        a.max_wall_sec=min(a.max_wall_sec,int((course.producer.legacy.source.DEADLINE-datetime.now(timezone.utc)).total_seconds())-2700)
        if a.max_wall_sec<60:raise GateNegative('45minute closing margin required')
        return evaluate(a.mode,a)
    except (GateNegative,FileNotFoundError) as exc:print('[DUALQA_FOLLOWUP_HOLD] '+str(exc));return 8
    except KeyboardInterrupt:print('[DUALQA_FOLLOWUP_INTERRUPTED] preserve partial private answers');return 130
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[DUALQA_FOLLOWUP_ERROR] '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
