#!/usr/bin/env python3
"""Fresh document paired QA: actual student history and gold history separated."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter,defaultdict
from datetime import datetime,timezone
import copy
import gc
import json
import time
from scripts import diag_p106b_dualqa_curriculum as course
from scripts import p106b_grounded_span as metrics
from scripts import diag_p106b_grounded_span as legacy
from scripts.p106b_gate_runtime import GateNegative,idle_before_gpu,wall_limit
from scripts.p106b_shards import ShardWriter,verify
from tinylm.chat.canonical import validate,normalize
TAG=course.TAG
EVIDENCE=course.EVIDENCE/'evaluate'
LOCAL=ROOT/'test_result/evidence/local'/TAG/'evaluate'
CODE=('scripts/diag_p106b_dualqa_eval.py','scripts/test_p106b_dualqa_eval.py')


def metadata():
    return dict(schema='P106B_DUAL_QA_FRESH_ACTUAL_HISTORY_V1',tag=TAG,
        code_sha256={p:course.training.data.digest(ROOT/p) for p in CODE},
        endpoints=['parent',*course.data.ARMS],precision='FP32_MATH',temperature=0.,top_k=1,
        source_contexts=256,orders_per_context=2,turns_per_order=2,
        actual_answers_per_endpoint=1024,gold_history_second_answers_per_endpoint=512,
        student_mtp=False,auxiliary_used_in_inference=False,semantic_truth='NOT_RUN',
        source_target='TEACHER_PSEUDO_UNVERIFIED',bootstrap_unit='whole document root',
        checkpoint_policy='final4epoch primary; no test-selected checkpoint')


def collect(row,parity,tok,emit):
    """No future gold in actual prefix, and no first-eight row slicing."""
    view=course.data.view(row,'contrast',parity,tok)
    messages=view['messages'];history=[];events=[]
    for turn in (0,1):
        history.append(copy.deepcopy(messages[2*turn]));prefix=validate(normalize(dict(messages=history)))['messages']
        answer,generation=emit(prefix)
        if not isinstance(answer,str):raise ValueError('exact model output string required, including empty')
        events.append(dict(root=row['meta']['semantic_root_id'],language=row['meta']['language'],order=parity,turn=turn+1,
            history='ACTUAL_MODEL',messages=copy.deepcopy(prefix),answer=answer,
            gold=course.data.text(messages[2*turn+1]),generation=generation,
            teacher_record_id=row['meta']['teacher_record_id'],source_truth='TEACHER_PSEUDO_UNVERIFIED'))
        history.append(dict(role='assistant',content=[dict(type='text',text=answer)]))
    prefix=copy.deepcopy(messages[:3]);answer,generation=emit(prefix)
    events.append(dict(root=row['meta']['semantic_root_id'],language=row['meta']['language'],order=parity,turn=2,
        history='GOLD_REFERENCE',messages=prefix,answer=answer,gold=course.data.text(messages[3]),generation=generation,
        teacher_record_id=row['meta']['teacher_record_id'],source_truth='TEACHER_PSEUDO_UNVERIFIED'))
    return events


def score(event):
    answer,gold=event['answer'],event['gold'];finish=event['generation']['finish_reason']
    return dict(cases=1,literal=int(answer.strip()==gold.strip()),lexical_f1=metrics.token_f1(answer,gold),
        empty=int(not answer.strip()),max_new=int(finish.startswith('MAX_NEW')),
        context_exhausted=int(finish=='CONTEXT_BUDGET_EXHAUSTED'))


def emit_function(model,cfg,tok):
    from scripts.diag_p101a_mtp_parity import PrecisionForward
    from tinylm.chat.serialize import serialize
    from tinylm.infer.generate import sample
    wrapped=PrecisionForward(model,'fp32_math')
    def emit(messages):
        course.producer.legacy.source.deadline()
        prompt=serialize(dict(messages=messages),'chatml',add_generation_prompt=True)
        tokens=tok.encode(prompt).ids;cap=min(64,cfg.max_seq_len-len(tokens))
        if cap<1:return '',dict(finish_reason='CONTEXT_BUDGET_EXHAUSTED',prompt_tokens=len(tokens),requested_max_new=64,actual_max_new=0)
        output,info=sample(wrapped,cfg,tok,prompt,max_new=cap,temperature=0.,top_k=1,device='cuda',
            logits_last_only=True,return_metadata=True,stop_token_sequences=[tok.encode('<|im_end|>').ids])
        prefix=tok.decode(tokens)
        if not output.startswith(prefix):raise ValueError('exact decoded prompt prefix missing')
        return output[len(prefix):],dict(info,prompt_tokens=len(tokens),actual_max_new=cap)
    return emit


def actual_source(model,cfg,tok,rows,directory):
    import torch
    if len(rows)!=256 or Counter(r['meta']['language'] for r in rows)!=dict(ko=128,en=128):raise ValueError('all256 fresh balanced contexts required')
    if len({r['meta']['semantic_root_id'] for r in rows})!=256:raise ValueError('fresh document root unique')
    writer=ShardWriter(directory,'source_actual_and_gold');counts=defaultdict(Counter);emit=emit_function(model,cfg,tok)
    model.eval();model.freeze_quant()
    try:
        with torch.no_grad():
            for index,row in enumerate(rows):
                for parity in (0,1):
                    for event in collect(row,parity,tok,emit):
                        value=score(event);event.update(scores=value);writer.append(event)
                        counts[event['history']+':'+event['language']+':turn'+str(event['turn'])].update(value)
                if (index+1)%32==0:print('[DUALQA_EVAL_SOURCE_PROGRESS] '+json.dumps(dict(contexts=index+1,total_contexts=256)),flush=True)
    finally:model.clear_quant();model.train()
    manifest=writer.close(lineage=metadata());verify(directory,manifest)
    primary=sum(v['cases'] for k,v in counts.items() if k.startswith('ACTUAL_MODEL:'))
    gold=sum(v['cases'] for k,v in counts.items() if k.startswith('GOLD_REFERENCE:'))
    if primary!=1024 or gold!=512 or manifest['rows']!=1536:raise ValueError('actual1024 and gold-second512 separate')
    return dict(counts={k:dict(v) for k,v in counts.items()},manifest=manifest,directory=str(directory.relative_to(ROOT)),
        actual_answers=primary,gold_second_answers=gold,semantic_truth='NOT_RUN',scope='literal pseudo-target fidelity, not fact truth or official QA benchmark')


def run(args):
    import torch
    from tinylm.infer.generate import _strip
    from scripts.p106b_education_followup import answers
    from scripts.diag_p101a_mtp_parity import PrecisionForward
    r,rows,labels=course.read_course()
    reports={a:course.producer.legacy.source.required(course.EVIDENCE/a/'report.json') for a in course.data.ARMS}
    for arm,report in reports.items():
        if report['status']!='TRAINED_NEW_SOURCE_TEST_PENDING' or report['updates']!=176 or report['code_sha256']!=course.info()['code_sha256']:
            raise ValueError('complete matching final4epoch courses required')
        if report['checkpoint_sha256']!=course.training.data.digest(ROOT/report['checkpoint']):raise ValueError('final checkpoint changed')
    if EVIDENCE.exists() or LOCAL.exists():raise GateNegative('old evaluation evidence preserved')
    idle_before_gpu();EVIDENCE.mkdir(parents=True,exist_ok=False);began=time.perf_counter();endpoints={}
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    with wall_limit(args.max_wall_sec):
        for arm in ('parent',*course.data.ARMS):
            torch,model,cfg,tok,initial=course.load_parent()
            cp=course.producer.PARENT;identity=course.producer.PARENT_SHA
            if arm!='parent':
                cp=ROOT/reports[arm]['checkpoint'];identity=reports[arm]['checkpoint_sha256']
                saved=torch.load(cp,map_location='cpu',weights_only=True)
                if saved['curriculum']!=dict(tag=TAG,arm=arm,epoch=4):raise ValueError('selected final4epoch checkpoint lineage')
                model.load_state_dict(_strip(saved['model']),strict=True);del saved
            initial=course.training.state_fingerprint(model);model=model.cuda();directory=LOCAL/arm
            values=dict(source=actual_source(model,cfg,tok,rows['test_source'],directory),
                public_bridge=legacy.generate(model,cfg,tok,rows['test_bridge'],directory,'original_public_bridge256'),
                known_code_development=legacy.generate(model,cfg,tok,rows['code_retention_dev'],directory,'known_code_dev640'),
                native=course.training.native_ce(model,course.NATIVE))
            values['legacy8']=answers(PrecisionForward(model,'fp32_math'),cfg,tok,directory,'legacy8')
            if course.training.state_fingerprint(model)!=initial:raise ValueError('evaluation changed body parameters')
            endpoint=dict(checkpoint=str(cp.relative_to(ROOT)),checkpoint_sha256=identity,core_before_after_sha256=initial,metrics=values)
            course.training.write(EVIDENCE/(arm+'_report.json'),dict(metadata(),arm=arm,**endpoint));endpoints[arm]=endpoint
            print('[DUALQA_EVAL_ENDPOINT] '+json.dumps(dict(arm=arm,source=values['source']['counts'],native=values['native'],legacy8=values['legacy8'])),flush=True)
            del model;gc.collect();torch.cuda.empty_cache()
    report=dict(metadata(),status='DUALQA_FRESH_ACTUAL_HISTORY_EVALUATED',endpoints=endpoints,
        corpus_report_sha256=course.training.data.digest(course.CORPUS/'report.json'),whole_sec=time.perf_counter()-began,
        semantic_truth='NOT_RUN',cross_language_semantic_overlap='NOT_AUDITED',native_scope='fixed32crops only')
    course.training.write(EVIDENCE/'report.json',report)
    return 0


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true');p.add_argument('--check-only',action='store_true')
    p.add_argument('--max-wall-sec',type=int,default=10800);a=p.parse_args()
    if not 60<=a.max_wall_sec<=14400:p.error('bounded60..14400')
    if a.execute==a.check_only:p.error('one of --execute / --check-only required')
    if a.check_only:print('[DUALQA_EVAL_CHECK_ONLY] '+json.dumps(metadata()));return 0
    try:
        course.producer.legacy.source.deadline()
        a.max_wall_sec=min(a.max_wall_sec,int((course.producer.legacy.source.DEADLINE-datetime.now(timezone.utc)).total_seconds())-2700)
        if a.max_wall_sec<60:raise GateNegative('45minute closure margin required')
        return run(a)
    except (GateNegative,FileNotFoundError) as exc:print('[DUALQA_EVAL_HOLD] '+str(exc));return 8
    except KeyboardInterrupt:print('[DUALQA_EVAL_INTERRUPTED] raw partial answers preserved');return 130
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[DUALQA_EVAL_ERROR] '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
