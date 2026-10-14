"""Independent small context/clarification SFT; same parent, new artifacts only."""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
from dataclasses import asdict
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import p106b_context_quality as data
from scripts import diag_p101a_sft_mtp as training
from scripts.p106b_shards import ShardWriter,verify
TAG='p106b_context_clarify_v1_s1337'
CORPUS=ROOT/'HF/sft_ready'/TAG/'corpus'
EVIDENCE=ROOT/'test_result/evidence'/TAG
ARMS={'ntp_hi':('parent_ntp',1e-4),'ntp_lo':('parent_ntp',1e-5),'mtp_hi':('parent_mtp',1e-4)}
CODE=('scripts/p106b_context_quality.py','scripts/diag_p106b_context_quality.py',
      'scripts/test_p106b_context_quality.py','scripts/diag_p101a_sft_mtp.py',
      'tinylm/train/mtp_sft.py','tinylm/infer/generate.py','tinylm/infer/mtp.py',
      'tinylm/config.py','tinylm/model/transformer.py','tinylm/model/ternary.py',
      'tinylm/model/modules.py','tinylm/train/muon.py','tinylm/train/optimizer_audit.py',
      'tinylm/chat/canonical.py','tinylm/chat/serialize.py','tinylm/data/sft.py',
      'scripts/diag_p101a_mtp_parity.py','scripts/p106b_education_followup.py',
      'scripts/p106b_memory_stream.py','scripts/p106b_gemma_teacher.py',
      'scripts/p106b_gemma_labels.py','scripts/p106b_teacher_format.py')


def info():
    return dict(schema=data.VERSION,tag=TAG,parent_sha256=training.PARENT_SHA,
        tokenizer_sha256=training.data.TOK_SHA,seed=1337,micro_bs=8,accum=16,seq=1024,
        grad_checkpoint=True,compile='default',epochs=4,expected_updates=128,
        train_rows=4096,val_rows=512,code_sha256={p:training.data.digest(ROOT/p) for p in CODE},
        same_initial_body=True,world_knowledge_claim=False,actual_draw='MEASURE_SEPARATELY_FROM_PADDING',
        inference_precision='FP32_MATH_NO_TF32',formal_train_ready=False)


def corpus():
    if CORPUS.exists() or CORPUS.is_symlink():raise FileExistsError('preserve frozen course; use new tag')
    from tokenizers import Tokenizer
    from tinylm.train import mtp_sft as core
    if training.data.digest(training.data.TOKENIZER)!=training.data.TOK_SHA:raise ValueError('tokenizer changed')
    tok=Tokenizer.from_file(str(training.data.TOKENIZER));rows=data.build()
    CORPUS.mkdir(parents=True,exist_ok=False);manifests={};counts={}
    for split,values in rows.items():
        writer=ShardWriter(CORPUS,split);total_x=total_y=0;h=Counter();families=Counter()
        for row in values:
            rec=core.encode_record(row,tok)
            if rec.x_tokens>1024:raise ValueError('course exceeds declared sequence; no truncation')
            writer.append(row);total_x+=rec.x_tokens;total_y+=rec.targets
            h.update(core.count_record(rec));families[row['meta']['kind']]+=1
        manifests[split]=writer.close(lineage=info());verify(CORPUS,manifests[split])
        counts[split]=dict(actual_x_tokens=total_x,assistant_targets=total_y,
            horizon_counts=dict(h),family_counts=dict(families),rows=len(values))
    result=dict(info(),status='COURSE_FROZEN',counts=counts,manifests=manifests,
        semantic_root_overlap=0,exact_conversation_duplicates=0,
        scope='eight procedural schemas; finite variants, not unique new world facts or75M')
    training.write(CORPUS/'report.json',result)
    training.write(EVIDENCE/'corpus'/'report.json',result)
    print('[CONTEXT_COURSE] '+json.dumps(counts,ensure_ascii=False),flush=True);return 0


def read_course():
    result=json.loads((CORPUS/'report.json').read_text())
    if result['status']!='COURSE_FROZEN' or result['code_sha256']!=info()['code_sha256']:
        raise FileNotFoundError('same-code course required')
    for manifest in result['manifests'].values():verify(CORPUS,manifest)
    values={split:list(training.data.stream_rows(CORPUS,result['manifests'][split])) for split in ('train','val')}
    return result,values


def exact(answer,gold,rubric):
    body=answer.strip()
    if rubric=='CLARIFICATION_POSTHOC':return None
    if rubric=='EXACT_JSON_OBJECT':
        try:return json.loads(body)==json.loads(gold)
        except (ValueError,TypeError):return False
    if rubric=='EXACT_INTEGER':
        import re
        return bool(re.fullmatch(r'[+-]?\d+',body)) and int(body)==int(gold)
    if rubric=='EXACT_BOOLEAN':return body.lower()==gold.lower()
    return body.casefold()==gold.casefold()


def probe(base,cfg,tok,rows,target,label):
    import torch
    from scripts.diag_p101a_mtp_parity import PrecisionForward
    from tinylm.chat.serialize import serialize
    from tinylm.infer.generate import sample
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    base.eval();base.freeze_quant();wrapped=PrecisionForward(base,'fp32_math')
    writer=ShardWriter(target,'answers_'+label);counts=defaultdict(lambda:dict(cases=0,exact_pass=0,literal_agreement=0))
    selected=rows[:64]
    with torch.no_grad():
        for row in selected:
            prompt=serialize(dict(messages=row['messages'][:-1]),'chatml',add_generation_prompt=True)
            decoded,meta=sample(wrapped,cfg,tok,prompt,max_new=64,temperature=0.,top_k=1,
                device='cuda',logits_last_only=True,return_metadata=True,
                stop_token_sequences=[tok.encode('<|im_end|>').ids])
            prefix=tok.decode(tok.encode(prompt).ids)
            if not decoded.startswith(prefix):raise ValueError('prompt extraction failed')
            answer=decoded[len(prefix):];gold=data.text(row,-1);kind=row['meta']['kind']
            judged=exact(answer,gold,row['meta']['rubric']);c=counts[kind];c['cases']+=1
            c['exact_pass']+=int(judged is True);c['literal_agreement']+=int(answer.strip()==gold.strip())
            record=dict(label=label,kind=kind,language=row['meta']['language'],
                root=row['meta']['semantic_root_id'],messages=row['messages'][:-1],
                question=data.text(row,-2),answer=answer,gold=gold,exact_code_contract=judged,
                literal_agreement=answer.strip()==gold.strip(),generation=meta,
                clarification_meaning_review='PENDING_GPT_OFFLINE' if judged is None else 'NOT_APPLICABLE')
            writer.append(record)
            print('[CONTEXT_FIRST_ANSWER] '+json.dumps({k:record[k] for k in
                ('label','kind','language','question','answer','gold','exact_code_contract')},ensure_ascii=False),flush=True)
        # Real dialogue separately: preceding assistant turns are model answers,
        # not gold teacher-history. Do not call last-turn conditioning a rollout.
        rollout_counts=Counter()
        for row in [r for r in selected if len(r['messages'])>2][:8]:
            actual_messages=[]
            for turn in range(0,len(row['messages']),2):
                actual_messages.append(row['messages'][turn])
                prompt=serialize(dict(messages=actual_messages),'chatml',add_generation_prompt=True)
                decoded,meta=sample(wrapped,cfg,tok,prompt,max_new=64,temperature=0.,top_k=1,
                    device='cuda',logits_last_only=True,return_metadata=True,
                    stop_token_sequences=[tok.encode('<|im_end|>').ids])
                prefix=tok.decode(tok.encode(prompt).ids)
                if not decoded.startswith(prefix):raise ValueError('rollout prompt extraction failed')
                answer=decoded[len(prefix):];gold=data.text(row,turn+1)
                declared=row['meta'].get('turn_rubrics')
                rubric=(declared[turn//2] if declared else row['meta']['rubric']
                    if turn+1==len(row['messages'])-1 else
                    'CLARIFICATION_POSTHOC' if row['meta']['kind']=='clarify_followup' else 'EXACT_INTEGER')
                judged=exact(answer,gold,rubric)
                record=dict(label=label+'_actual_rollout',kind=row['meta']['kind'],
                    language=row['meta']['language'],root=row['meta']['semantic_root_id'],turn=turn//2+1,
                    actual_prior_messages=actual_messages.copy(),question=data.text(row,turn),
                    answer=answer,gold=gold,exact_code_contract=judged,generation=meta,
                    clarification_meaning_review='PENDING_GPT_OFFLINE' if judged is None else 'NOT_APPLICABLE')
                writer.append(record);rollout_counts['turns']+=1;rollout_counts['exact_pass']+=int(judged is True)
                if not answer.strip():
                    rollout_counts['empty_reply_followup_not_run']+=1;break
                actual_messages.append(dict(role='assistant',content=answer))
    manifest=writer.close(lineage=dict(label=label,first_answer_only=True,
        prior_assistant_context='GOLD_HISTORY_FOR_LAST_TURN; real rollout separately required'))
    verify(target,manifest);base.clear_quant();base.train()
    return dict(counts=dict(counts),manifest=manifest,
        clarification_semantics='PENDING_OFFLINE_REVIEW',dialogue_rollout=dict(rollout_counts))


def train(args):
    report,rows=read_course();target=EVIDENCE/args.arm
    out=ROOT/'runs/ckpt'/('m100s10_ko-en_context4pass_dense_chat32_'+TAG+'_'+args.arm+'.pt')
    if target.exists() or out.exists() or target.is_symlink() or out.is_symlink():raise FileExistsError('fresh arm only')
    from scripts.p106b_gate_runtime import idle_before_gpu,wall_limit
    from tinylm.train import mtp_sft as core
    idle_before_gpu();target.mkdir(parents=True,exist_ok=False);began=time.perf_counter()
    source_arm,lr=ARMS[args.arm]
    epochs=info()['epochs'];expected=epochs*math.ceil(report['counts']['train']['rows']/128)
    with wall_limit(args.max_wall_sec):
        torch,base,cfg,tok,initial=training.load_runtime(source_arm)
        records={s:[core.encode_record(r,tok) for r in v] for s,v in rows.items()}
        os.environ['TORCHINDUCTOR_CACHE_DIR']=tempfile.mkdtemp(prefix='p106b_context_course_')
        base=base.cuda();base.train();pad=tok.token_to_id('<|pad|>')
        if pad is None:pad=tok.token_to_id('<pad>')
        if pad is None:raise ValueError('declared padding token absent')
        torch.cuda.reset_peak_memory_stats()
        before=probe(base,cfg,tok,rows['val'],target,'initial')
        from scripts.p106b_education_followup import ARMS as STUDENTS,answers
        from scripts.diag_p101a_mtp_parity import PrecisionForward
        legacy_before=answers(PrecisionForward(base,'fp32_math'),cfg,tok,target,'initial_legacy8')
        native_before=training.native_ce(base,ROOT/STUDENTS['b']['cache'])
        model=torch.compile(base,mode='default');adam,muon=training.optimizers(base)
        scale=lr/1e-4
        for opt in (adam,muon):
            for group in opt.param_groups:group['lr']*=scale
        updates=processed=targets=0;grad_max=0.;history=[];head_updates=Counter();step_seconds=[]
        for epoch in range(epochs):
            for groups in training.batches(records['train'],epoch):
                tick=time.perf_counter();denominators=Counter()
                for micro in groups:
                    for record in micro:denominators.update(core.count_record(record))
                weights=core.coefficients(updates,expected) if cfg.mtp_aux else {}
                active=tuple(h for h,v in weights.items() if v)
                adam.zero_grad(set_to_none=True);muon.zero_grad(set_to_none=True)
                for micro in groups:
                    x,y,seg=core.pad_records(micro,pad,'cuda',fixed_width=1024,batch_size=8)
                    with torch.autocast('cuda',dtype=torch.bfloat16):
                        hidden=model(x,return_hidden=True)
                        sums,valid=core.components(base,hidden,y,seg,horizons=active)
                        loss=core.normalized_loss(sums,dict(denominators),weights)
                    if not torch.isfinite(loss):raise ValueError('nonfinite training loss')
                    loss.backward();processed+=sum(r.x_tokens for r in micro);targets+=sum(r.targets for r in micro)
                gradient=torch.nn.utils.clip_grad_norm_(base.parameters(),1.)
                if not torch.isfinite(gradient):raise ValueError('nonfinite gradient')
                grad_max=max(grad_max,float(gradient))
                for h in active:
                    g=getattr(base,f'mtp_up{h}').grad
                    if g is not None and bool(g.ne(0).any()):head_updates[h]+=1
                adam.step();muon.step();updates+=1;torch.cuda.synchronize()
                step_seconds.append(time.perf_counter()-tick)
                if updates%8==0:print('[CONTEXT_UPDATE] '+json.dumps(dict(arm=args.arm,updates=updates,
                    actual_x=processed,targets=targets,last_sec=step_seconds[-1],grad_max=grad_max)),flush=True)
            val=training.evaluate(base,records['val'],pad)
            history.append(dict(epoch=epoch+1,updates=updates,val=val))
        if updates!=expected or processed!=epochs*report['counts']['train']['actual_x_tokens']:
            raise ValueError('planned real exposure mismatch')
        after=probe(base,cfg,tok,rows['val'],target,'final')
        legacy_after=answers(PrecisionForward(base,'fp32_math'),cfg,tok,target,'final_legacy8')
        native_after=training.native_ce(base,ROOT/STUDENTS['b']['cache'])
        payload=base.mtp_deployment_payload(keep_aux=True) if cfg.mtp_aux else dict(model=base.state_dict(),cfg=asdict(cfg))
        with out.open('xb') as stream:
            torch.save(dict(payload,step=updates,tokenizer_sha256=training.data.TOK_SHA,
                tokenizer_lineage='chat32',context_course=dict(tag=TAG,arm=args.arm,corpus_sha256=training.data.digest(CORPUS/'report.json'))),stream)
        result=dict(info(),arm=args.arm,status='CONTEXT_SFT_COMPLETE_REVIEW_PENDING',lr=lr,muon_lr=4*lr,
            initial_core_sha256=initial,corpus_sha256=training.data.digest(CORPUS/'report.json'),
            updates=updates,actual_x_tokens=processed,assistant_targets=targets,grad_max=grad_max,
            head_nonzero_gradient_updates=dict(head_updates),history=history,initial_answers=before,final_answers=after,
            legacy8_before=legacy_before,legacy8_after=legacy_after,
            native_before=native_before,native_after=native_after,
            head_tensor_bytes=base.mtp_head_bytes(),peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20,
            step_seconds=step_seconds,whole_sec=time.perf_counter()-began,
            checkpoint=str(out.relative_to(ROOT)),checkpoint_sha256=training.data.digest(out),
            optimizer_saved=False,general_intelligence_improvement='NOT_ESTABLISHED')
        training.write(target/'report.json',result)
    print('[CONTEXT_SFT_FINAL] '+json.dumps(dict(arm=args.arm,updates=updates,actual_x=processed,
        first_answer_counts=after['counts'],native_ce_after=native_after['ce']),ensure_ascii=False),flush=True)
    return 0


def teacher_pilot(args):
    from scripts import p106b_gemma_labels as teacher
    from scripts import diag_p106b_gemma_telemetry_resume as telemetry
    from scripts.p106b_memory_stream import PersistentMemory,stream_session_scope
    from scripts.p106b_gate_runtime import idle_before_gpu,wall_limit
    target=EVIDENCE/'teacher_pilot'
    if target.exists() or target.is_symlink():raise FileExistsError('old teacher comparison preserved')
    cases=[]
    for language in ('ko','en'):
        for kind in ('lookup','missing_item','missing_reference','arithmetic'):
            row=data.make(kind,language,317);q=data.text(row,0)
            if kind in ('lookup','missing_item'):
                reference,question=q.split('\n',1)
            else:reference,question='',q
            cases.append(dict(language=language,kind=kind,question=question,reference=reference,
                rubric=row['meta']['rubric'],gold=data.text(row,-1),root=row['meta']['semantic_root_id']))
    idle_before_gpu();target.mkdir(parents=True,exist_ok=False);writer=ShardWriter(target,'teacher_raw')
    began=time.perf_counter();records=[];rc=9;status='STARTED';metrics={}
    try:
        with wall_limit(args.max_wall_sec),PersistentMemory() as source:
            reader=telemetry.RetryingMemoryReader(source,emit=lambda line:print(line,flush=True))
            with stream_session_scope(reader),teacher.GemmaSession(True) as session:
                for i,case in enumerate(cases):
                    session.check();request=data.teacher_payload(case['question'],case['reference'],case['language'],2026101400+i)
                    tick=time.perf_counter();reply=session.request('/v1/chat/completions',request,timeout=180)
                    parsed=teacher.parsed_response(reply,case['language']);content=parsed.get('parsed_content')
                    answer=content['assistant_text'] if content else None
                    judged=exact(answer,case['gold'],case['rubric']) if answer is not None else None
                    canonical=None
                    if answer is not None:
                        from tinylm.chat.canonical import normalize,validate
                        canonical=validate(normalize(dict(messages=[
                            dict(role='user',content=(case['reference']+'\n'+case['question']).strip()),
                            dict(role='assistant',content=answer)],meta=dict(source='p106b_visible_reference_teacher_pilot',
                            source_sha256=data.sha(case),source_license='project_authored_synthetic',
                            language=case['language'],root_concept_id=case['root'],label_status='PSEUDO_UNVERIFIED',
                            teacher_reasoning_in_student=False,teacher_raw_row_1based=i+1))))
                    record=dict(case,payload=request,reply=reply,parsed=parsed,
                        student_question=(case['reference']+'\n'+case['question']).strip(),
                        canonical_candidate=canonical,
                        answer=answer,exact_code_contract=judged,seconds=time.perf_counter()-tick,
                        teacher_hidden_reference_sent=False,clarification_semantics='PENDING_OFFLINE_REVIEW',
                        automatic_training_admission=False,structural_attempts=1)
                    writer.append(record);records.append({k:v for k,v in record.items() if k not in ('payload','reply','parsed')})
                    print('[VISIBLE_REFERENCE_TEACHER] '+json.dumps(records[-1],ensure_ascii=False),flush=True)
                metrics=dict(memory=session.memory(),telemetry=reader.snapshot(),persistent=source.snapshot())
        status='TEACHER_VISIBLE_REFERENCE_COLLECTION_COMPLETE';rc=0
    except BaseException as exc:
        rc=130 if isinstance(exc,KeyboardInterrupt) else 9;status='INTERRUPTED' if rc==130 else 'EXECUTION_ERROR'
        metrics['error']=dict(type=type(exc).__name__,reason=str(exc)[:1000])
    finally:
        manifest=writer.close(lineage=info());verify(target,manifest)
        training.write(target/'report.json',dict(info(),status=status,returncode=rc,records=records,
            metrics=metrics,raw_manifest=manifest,whole_sec=time.perf_counter()-began,
            canonical_wrapper='CODE_ASSIGNS_VISIBLE_REFERENCE_AND_QUESTION; no teacher-owned JSON/ChatML',
            student_training='NOT_RUN',semantic_truth='NOT_REVIEWED',source_scope='producer synthetic examples only'))
    return rc


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=('corpus','train','teacher'),required=True)
    p.add_argument('--arm',choices=tuple(ARMS),default='ntp_hi');p.add_argument('--max-wall-sec',type=int,default=1800)
    g=p.add_mutually_exclusive_group(required=True);g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true')
    a=p.parse_args()
    if not 60<=a.max_wall_sec<=3600:p.error('bounded gate required')
    if a.check_only:
        if a.mode=='train':read_course()
        print('[CHECK_ONLY] '+json.dumps(info(),ensure_ascii=False));return 0
    if a.mode=='corpus':return corpus()
    if a.mode=='teacher':return teacher_pilot(a)
    existed=(EVIDENCE/a.arm).exists()
    try:return train(a)
    except BaseException as exc:
        target=EVIDENCE/a.arm;rc=130 if isinstance(exc,KeyboardInterrupt) else 9
        if not existed and target.is_dir() and not (target/'report.json').exists():
            training.write(target/'report.json',dict(info(),arm=a.arm,status='INTERRUPTED' if rc==130 else 'EXECUTION_ERROR',
                returncode=rc,error_type=type(exc).__name__,reason=str(exc)[:1000],
                checkpoint_valid='NOT_ESTABLISHED',source_and_old_checkpoints_mutated=False))
        print('[CONTEXT_SFT_ERROR] '+type(exc).__name__+': '+str(exc),flush=True);return rc

if __name__=='__main__':raise SystemExit(main())
