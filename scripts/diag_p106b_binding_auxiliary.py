#!/usr/bin/env python3
"""Same-parent SFT/native replay with a removable training-only binding task."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter
from dataclasses import asdict
from datetime import datetime,timezone
import copy
import json
import os
import tempfile
import time
from scripts import p106b_binding_auxiliary as method
from scripts import diag_p106b_conditional_orpo as old
from scripts import diag_p106b_verbatim_source as supplier
from scripts.p106b_shards import ShardWriter,verify
from scripts.p106b_gate_runtime import GateNegative
base=old.base
TAG='p106b_binding_aux_v1_s1337'
CORPUS=ROOT/'HF/sft_ready'/TAG/'corpus'
EVIDENCE=ROOT/'test_result/evidence'/TAG
LOCAL=ROOT/'test_result/evidence/local'/TAG
CODE=('scripts/p106b_binding_auxiliary.py','scripts/diag_p106b_binding_auxiliary.py',
      'scripts/test_p106b_binding_auxiliary.py','scripts/p106b_gate_runtime.py',*old.CODE,*supplier.CODE)
SOURCE_POLICY=supplier.STUDENT_POLICY


def info():
    r=base.info();r.pop('weights',None)
    r.update(schema=method.VERSION,tag=TAG,arms={k:dict(weight=v[0],root_permuted=v[1]) for k,v in method.ARMS.items()},
        code_sha256={p:base.training.data.digest(ROOT/p) for p in sorted(set(CODE))},
        source_block=supplier.TAG,native_weight=1.,auxiliary_parameters=1538,auxiliary_lr=.001,
        auxiliary_weight_decay=0,auxiliary_init='ZERO_WITH_BODY_RNG_PRESERVED',
        auxiliary_scope='verified code binding causal query suffix; normal arms loss only at first assistant predictor',
        dense_arm='auxdense100',all_arms_compute_same_suffix_logits=True,
        inference_uses_auxiliary_head=False,teacher_calls_this_stage=0,formal_train_ready=False,
        student_source_policy='SOURCE_IS_QUOTED_DATA_V1',
        native_replay='same additional8x1024 train-only CE per update, weight1 in all five arms')
    return r


def checkpoint(arm):
    return ROOT/'runs/ckpt'/f'm100s10_ko-en_binding_aux_dense_chat32_{TAG}_{arm}.pt'


def required_json(path,meaning):
    if not path.is_file():raise GateNegative('prerequisite absent: '+meaning+'; '+str(path.relative_to(ROOT)))
    return json.loads(path.read_text())


def public_rows(rows):
    result=[]
    for row in rows:
        r=copy.deepcopy(row);m=r['meta']
        if len(r['messages'])!=2 or r['messages'][0]['role']!='user' or r['messages'][1]['role']!='assistant':
            raise ValueError('known source-only QA role contract required')
        content=r['messages'][0]['content']
        if len(content)!=1 or content[0]['type']!='text':raise ValueError('known source-only text block required')
        old_input=content[0]['text'];policy=SOURCE_POLICY[m['language']]+'\n'
        already=m.get('student_source_policy')=='SOURCE_IS_QUOTED_DATA_V1'
        if already and not old_input.startswith(policy):raise ValueError('declared source policy/input mismatch')
        if not already:
            content[0]['text']=policy+old_input
            for span in m.get('student_original_message_ranges',[]):
                span['start']+=len(policy);span['end']+=len(policy)
            m['pre_policy_actual_x_tokens']=m.get('actual_x_tokens')
        m.setdefault('original_student_input_sha256',method.prior.source.sha(old_input))
        m.update(original_course_kind=m['kind'],original_course_rubric=m['rubric'],
            kind='public_qa',rubric='UNSCORED_PUBLIC_QA',truth='PSEUDO_UNVERIFIED',
            student_source_policy='SOURCE_IS_QUOTED_DATA_V1')
        result.append(r)
    return result


def validate_budget(records,rows):
    if len(records)!=len(rows):raise ValueError('record/source count mismatch')
    bad=[dict(index=i,kind=rows[i]['meta']['kind'],x=r.x_tokens,targets=r.targets)
        for i,r in enumerate(records) if r.x_tokens>1024 or not r.targets]
    if bad:raise ValueError('strict1024/no-empty technical budget, no truncation: '+json.dumps(bad[:12]))


def public_panel(rows):
    families={}
    for row in rows:
        m=row['meta'];families.setdefault((m['language'],m['course_family']),[]).append(row)
    if len(families)!=8:raise ValueError('eight language/source-family lanes required')
    result=[]
    for lane,values in sorted(families.items()):
        if len(values)!=8:raise ValueError('eight source val rows per lane required')
        result.extend(sorted(values,key=lambda row:row['meta']['semantic_root_id'])[:2])
    return result


def generation_budget(prompt_tokens,model_limit):
    remaining=model_limit-prompt_tokens
    if remaining<1:raise ValueError('no generation room after complete prompt')
    return min(256,remaining)


def freeze(args):
    base.deadline()
    if CORPUS.parent.exists() or EVIDENCE.exists():raise GateNegative('previous auxiliary namespace preserved; fresh stage required')
    source_report=required_json(supplier.CORPUS/'report.json','completed source512/64 corpus')
    if source_report['status']!='SUPPORTED_SOURCE_CORPUS_FROZEN' or source_report['code_sha256']!=supplier.info()['code_sha256']:
        raise ValueError('same-code new supported512/64 source corpus prerequisite')
    for manifest in source_report['manifests'].values():verify(supplier.CORPUS,manifest)
    source={s:list(base.training.data.stream_rows(supplier.CORPUS,m)) for s,m in source_report['manifests'].items()}
    if {s:len(v) for s,v in source.items()}!=dict(train=512,val=64):raise ValueError('source block size differs')
    prior,original,previous,pairs,test=old.read_course()
    rows={s:[copy.deepcopy(r) for r in previous[s] if r['meta']['kind']!='public_qa'] for s in ('train','dev')}
    rows['train']+=public_rows(source['train']);rows['dev']+=public_rows(source['val'])
    rows['test']=method.fresh_test(base.data.code_rows())
    rows['public_eval']=public_panel([row for row in rows['dev'] if row['meta']['kind']=='public_qa'])
    from tokenizers import Tokenizer
    from tinylm.train.mtp_sft import encode_record
    from tinylm.chat.serialize import serialize
    tok=Tokenizer.from_file(str(base.training.data.TOKENIZER));legal=method.approved_questions();counts={};bits={}
    for split,values in rows.items():
        encoded=[encode_record(row,tok) for row in values]
        validate_budget(encoded,values)
        for row,rec in zip(values,encoded):
            row['meta'].update(actual_x_tokens=rec.x_tokens,assistant_targets=rec.targets)
        counts[split]=dict(rows=len(values),actual_x_tokens=sum(r.x_tokens for r in encoded),
            assistant_targets=sum(r.targets for r in encoded),languages=dict(Counter(r['meta']['language'] for r in values)))
        if split=='train':
            for row,rec in zip(values,encoded):
                bit=method.binding_bit(row,legal)
                if bit is None:continue
                prompt=serialize(dict(messages=row['messages'][:-1]),'chatml',add_generation_prompt=True)
                first=next(i for i,y in enumerate(rec.y) if y!=-100)
                if first!=len(tok.encode(prompt).ids)-1:raise ValueError('first assistant predictor/prefix boundary mismatch')
                positions=method.causal_suffix_positions(row,tok,first)
                bits[method.prior.source.sha(row['messages'])]=dict(bit=bit,root=row['meta']['semantic_root_id'],positions=positions)
    if counts['train']['rows']!=5632 or counts['dev']['rows']!=704 or len(bits)!=4096:
        raise ValueError('planned mixed/aux sizes differ')
    roots={s:{r['meta']['semantic_root_id'] for r in v} for s,v in rows.items()}
    if any(roots[a]&roots[b] for a,b in (('train','dev'),('train','test'),('dev','test'))):raise ValueError('source root overlap')
    CORPUS.mkdir(parents=True,exist_ok=False);manifests={}
    for split,values in rows.items():
        writer=ShardWriter(CORPUS,split)
        for row in values:writer.append(row)
        manifests[split]=writer.close(lineage=info());verify(CORPUS,manifests[split])
    value=dict(info(),status='BINDING_AUX_COURSE_FROZEN',counts=counts,manifests=manifests,
        source_corpus_sha256=base.training.data.digest(supplier.CORPUS/'report.json'),
        native_copy_sha256=original['native_copy_sha256'],native_copy=str((base.CORPUS/'native_train.bin').relative_to(ROOT)),
        labels=bits,expected_updates=176,expected_head_position_events=4*sum(len(v['positions']) for v in bits.values()),
        source_root_overlap=0,decision_note=args.decision_note,
        prior_orpo_test_scope='development only; final code facts use new entity names and roots')
    base.training.write(CORPUS/'report.json',value)
    base.training.write(EVIDENCE/'corpus_report.json',{k:v for k,v in value.items() if k!='labels'})
    print('[BINDING_AUX_CORPUS] '+json.dumps(dict(counts=counts,auxiliary_rows=len(bits))),flush=True)
    return 0


def read_course():
    r=required_json(CORPUS/'report.json','same-code frozen auxiliary corpus')
    if r['status']!='BINDING_AUX_COURSE_FROZEN' or r['code_sha256']!=info()['code_sha256']:
        raise ValueError('same-code frozen auxiliary course required')
    if base.training.data.digest(ROOT/r['native_copy'])!=r['native_copy_sha256']:
        raise ValueError('native train windows changed')
    for manifest in r['manifests'].values():verify(CORPUS,manifest)
    return r,{s:list(base.training.data.stream_rows(CORPUS,m)) for s,m in r['manifests'].items()}


def labels_for_rows(rows,contract,permuted=False):
    output=[]
    for row in rows:
        signature=method.prior.source.sha(row['messages']);item=contract['labels'].get(signature)
        output.append(None if item is None else method.maybe_flip(item['bit'],item['root'],permuted))
    return output


def auxiliary_dev(model,head,tok,values,pad):
    import torch
    from tinylm.train import mtp_sft as core
    rows=[r for r in values if r['meta']['kind'].startswith('binding_')]
    legal=method.approved_questions('dev');totals=Counter()
    model.eval()
    with torch.no_grad():
        for start in range(0,len(rows),8):
            selected=rows[start:start+8];records=[core.encode_record(row,tok) for row in selected]
            labels=[method.binding_bit(row,legal) for row in selected]
            x,y,seg=core.pad_records(records,pad,'cuda',fixed_width=1024,batch_size=8)
            labels+=[None]*(8-len(labels))
            with torch.autocast('cuda',dtype=torch.bfloat16):
                hidden=model(x,return_hidden=True);loss,n,correct=method.auxiliary_sum(head,hidden,y,labels)
            totals.update(loss_sum=float(loss),cases=n,correct=correct)
    model.train()
    return dict(totals,ce=totals['loss_sum']/totals['cases'],accuracy=totals['correct']/totals['cases'],
        scope='true producer dev labels; not free generation; no test labels')


def train(args,cost=False):
    r,rows=read_course();arm=args.arm;weight,permuted=method.ARMS[arm]
    target=EVIDENCE/(('cost_' if cost else '')+arm);local=LOCAL/(('cost_' if cost else '')+arm);out=checkpoint(arm)
    if target.exists() or local.exists() or (not cost and out.exists()):raise GateNegative('previous arm/output preserved')
    if not cost:
        for required_arm in ('aux0','aux100','auxdense100'):
            calibration=required_json(EVIDENCE/('cost_'+required_arm)/'report.json','actual zero/positive cost8')
            if calibration['code_sha256']!=info()['code_sha256'] or calibration['updates']!=8:
                raise ValueError('same-code actual zero/positive cost8 required')
    from scripts.p106b_gate_runtime import idle_before_gpu,wall_limit
    from tinylm.train import mtp_sft as core
    import numpy as np
    idle_before_gpu();target.mkdir(parents=True,exist_ok=False);began=time.perf_counter()
    with wall_limit(args.max_wall_sec):
        torch,model,cfg,tok,initial=base.training.load_runtime('parent_ntp')
        records=[core.encode_record(row,tok) for row in rows['train']]
        labels=labels_for_rows(rows['train'],r,permuted)
        by_record={id(rec):label for rec,label in zip(records,labels)}
        by_window={id(rec):r['labels'].get(method.prior.source.sha(row['messages']),{}).get('positions')
            for rec,row in zip(records,rows['train'])}
        dev_records=[core.encode_record(row,tok) for row in rows['dev']]
        native=np.memmap(ROOT/r['native_copy'],dtype=np.uint16,mode='r').reshape(-1,1025)
        if len(native)!=1408:raise ValueError('176x8 native windows required')
        os.environ['TORCHINDUCTOR_CACHE_DIR']=tempfile.mkdtemp(prefix='p106b_binding_aux_')
        model=model.cuda();model.train();head=method.new_head(cfg.dim,'cuda')
        if base.training.state_fingerprint(model)!=initial:raise ValueError('auxiliary creation changed initial body')
        pad=tok.token_to_id('<|pad|>')
        if pad is None:pad=tok.token_to_id('<pad>')
        if pad is None:raise ValueError('pad token absent')
        torch.cuda.reset_peak_memory_stats();before=None if cost else base.training.native_ce(model,base.NATIVE)
        compiled=torch.compile(model,mode='default');adam,muon=base.training.optimizers(model)
        for opt in (adam,muon):
            for group in opt.param_groups:group['lr']*=.5
        head_opt=torch.optim.AdamW(head.parameters(),lr=.001,weight_decay=0)
        steps=sft_x=assistant=native_x=auxiliary_count=head_events=0
        seconds=[];history=[];grad_max=0.;aux_sum=0.;aux_correct=0
        for epoch in range(4):
            for groups in base.training.batches(records,epoch):
                base.deadline();tick=time.perf_counter()
                denominator=sum(rec.targets for micro in groups for rec in micro)
                aux_denominator=sum(by_record[id(rec)] is not None for micro in groups for rec in micro)
                if not aux_denominator:raise ValueError('known binding rows required in whole update')
                for opt in (adam,muon,head_opt):opt.zero_grad(set_to_none=True)
                for micro in groups:
                    x,y,seg=core.pad_records(micro,pad,'cuda',fixed_width=1024,batch_size=8)
                    batch_labels=[by_record[id(rec)] for rec in micro]+[None]*(8-len(micro))
                    windows=[by_window[id(rec)] for rec in micro]+[None]*(8-len(micro))
                    with torch.autocast('cuda',dtype=torch.bfloat16):
                        hidden=compiled(x,return_hidden=True);sums,counts=core.components(model,hidden,y,seg,horizons=())
                        extra,n,correct,events=method.suffix_auxiliary_sum(head,hidden,y,batch_labels,windows,
                            dense=arm=='auxdense100')
                        loss=sums[1]/denominator+weight*extra/aux_denominator
                    if not torch.isfinite(loss):raise ValueError('nonfinite SFT/aux loss')
                    loss.backward();sft_x+=sum(rec.x_tokens for rec in micro);assistant+=sum(rec.targets for rec in micro)
                    auxiliary_count+=n;aux_sum+=float(extra.detach());aux_correct+=correct;head_events+=events
                native_records=[core.Record(a[:-1].astype('int64').tolist(),a[1:].astype('int64').tolist(),[1]*1024)
                    for a in native[steps*8:(steps+1)*8]]
                x,y,seg=core.pad_records(native_records,pad,'cuda',fixed_width=1024,batch_size=8)
                with torch.autocast('cuda',dtype=torch.bfloat16):
                    hidden=compiled(x,return_hidden=True);sums,counts=core.components(model,hidden,y,seg,horizons=())
                    loss=sums[1]/8192
                loss.backward();native_x+=8192
                gradient=torch.nn.utils.clip_grad_norm_([*model.parameters(),*head.parameters()],1.)
                if not torch.isfinite(gradient):raise ValueError('nonfinite gradient')
                grad_max=max(grad_max,float(gradient))
                for opt in (adam,muon,head_opt):opt.step()
                steps+=1;torch.cuda.synchronize();seconds.append(time.perf_counter()-tick)
                if steps==1 or steps%16==0:
                    print('[BINDING_AUX_UPDATE] '+json.dumps(dict(arm=arm,steps=steps,sft_x=sft_x,assistant=assistant,
                        native_x=native_x,auxiliary_count=auxiliary_count,aux_ce=aux_sum/auxiliary_count,
                        auxiliary_train_accuracy=aux_correct/auxiliary_count,last_sec=seconds[-1])),flush=True)
                if cost and steps==8:break
            if cost:break
            val=base.training.evaluate(model,dev_records,pad);native_eval=base.training.native_ce(model,base.NATIVE)
            aux_dev=auxiliary_dev(model,head,tok,rows['dev'],pad)
            generated=base.generate(model,cfg,tok,base.dev_sample(rows['dev']),local,f'dev_epoch{epoch+1}')
            history.append(dict(epoch=epoch+1,updates=steps,val=val,native=native_eval,auxiliary_dev=aux_dev,dev=generated))
        if not cost and (steps!=176 or sft_x!=4*r['counts']['train']['actual_x_tokens'] or auxiliary_count!=16384
                or head_events!=r['expected_head_position_events']):
            raise ValueError('planned actual exposures mismatch')
        head_norm=float(sum(p.detach().square().sum() for p in head.parameters()).sqrt())
        if (weight==0 and head_norm!=0) or (weight>0 and head_norm==0):
            raise ValueError('auxiliary zero/active parameter update contract failed')
        result=dict(info(),status='COST_MEASURED' if cost else 'TRAINED_FRESH_TEST_PENDING',arm=arm,
            weight=weight,root_permuted=permuted,updates=steps,initial_core_sha256=initial,
            corpus_sha256=base.training.data.digest(CORPUS/'report.json'),sft_x_tokens=sft_x,assistant_targets=assistant,
            native_x_tokens=native_x,auxiliary_targets=auxiliary_count,auxiliary_cumulative_ce=aux_sum/auxiliary_count,
            head_position_events_computed=head_events,
            head_position_events_active=0 if not weight else head_events if arm=='auxdense100' else auxiliary_count,
            effective_auxiliary_rows=auxiliary_count if weight else 0,
            auxiliary_cumulative_train_accuracy=aux_correct/auxiliary_count,history=history,native_before=before,
            auxiliary_head_parameter_l2=head_norm,
            grad_max=grad_max,gradient_clip=1.,clip_scope='body plus auxiliary, same policy in all arms',
            step_seconds=seconds,peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20,whole_sec=time.perf_counter()-began,
            head_in_model_state=False,head_forward_in_free_generation=False,actual_student_rollout='NOT_RUN')
        if not cost:
            with out.open('xb') as stream:torch.save(dict(model=model.state_dict(),cfg=asdict(cfg),step=steps,
                tokenizer_sha256=base.training.data.TOK_SHA,tokenizer_lineage='chat32',
                training_only_auxiliary=head.state_dict(),auxiliary_method=dict(tag=TAG,arm=arm)),stream)
            result.update(checkpoint=str(out.relative_to(ROOT)),checkpoint_sha256=base.training.data.digest(out),optimizer_saved=False)
        base.training.write(target/'report.json',result)
    print('[BINDING_AUX_FINAL] '+json.dumps({k:result[k] for k in ('arm','status','updates','whole_sec')}),flush=True)
    return 0


def evaluate(args):
    import gc
    from scripts.p106b_gate_runtime import idle_before_gpu,wall_limit
    from tinylm.infer.generate import _strip
    r,rows=read_course();target=EVIDENCE/'fresh_test'
    if target.exists():raise GateNegative('previous auxiliary test preserved')
    trained={arm:required_json(EVIDENCE/arm/'report.json','completed auxiliary arm '+arm) for arm in method.ARMS}
    for arm,report in trained.items():
        if report['status']!='TRAINED_FRESH_TEST_PENDING' or report['code_sha256']!=info()['code_sha256']:
            raise ValueError('same-code completed five arms prerequisite')
        if base.training.data.digest(ROOT/report['checkpoint'])!=report['checkpoint_sha256']:raise ValueError('checkpoint changed')
    idle_before_gpu();began=time.perf_counter();summaries={};public={};legacy={};live_dialogues={}
    with wall_limit(args.max_wall_sec):
        for arm in ('parent',*method.ARMS):
            base.deadline();torch,model,cfg,tok,initial=base.training.load_runtime('parent_ntp')
            if arm!='parent':
                state=torch.load(ROOT/trained[arm]['checkpoint'],map_location='cpu',weights_only=True)
                model.load_state_dict(_strip(state['model']),strict=True);del state
            model=model.cuda()
            summaries[arm]=base.generate(model,cfg,tok,rows['test'],LOCAL/'fresh_test'/arm,'code')
            summaries[arm]['native']=base.training.native_ce(model,base.NATIVE)
            public[arm]=generate_public(model,cfg,tok,rows['public_eval'],LOCAL/'fresh_test'/arm)
            from scripts.p106b_education_followup import answers
            from scripts.diag_p101a_mtp_parity import PrecisionForward
            legacy[arm]=answers(PrecisionForward(model,'fp32_math'),cfg,tok,LOCAL/'fresh_test'/arm,'legacy8')
            from scripts.diag_p106b_context_quality import probe
            dialogue_rows=[]
            for language in ('ko','en'):
                dialogue_rows.extend([row for row in rows['test'] if row['meta']['kind']=='update'
                    and row['meta']['language']==language][:2])
            live_dialogues[arm]=probe(model,cfg,tok,dialogue_rows,LOCAL/'fresh_test'/arm,'actual_update_dialogues')
            print('[BINDING_AUX_EVAL] '+json.dumps(dict(arm=arm,
                code_exact=sum(v['exact'] for v in summaries[arm]['counts'].values()),
                roots_all4=summaries[arm]['all4_exact_roots'],public=public[arm]['counts'],legacy8=legacy[arm],
                actual_dialogue=live_dialogues[arm]['dialogue_rollout'])),flush=True)
            del model;gc.collect();torch.cuda.empty_cache()
    value=dict(info(),status='AUXILIARY_FRESH_TEST_COLLECTED',arms=summaries,public_qa=public,legacy8=legacy,
        live_dialogues=live_dialogues,actual_student_rollout='FOUR_CODE_UPDATE_DIALOGUES_COLLECTED',
        rollout_scope='subset4 already in code640; compare gold-history final turn with actual model prior answers; not extra independent cases',
        whole_sec=time.perf_counter()-began,cases_per_arm=640,public_cases_per_arm=16,
        public_scope='DEV_SUBSET16_OF64; two per language/family, fixed before training; not independent world test',
        legacy8_scope='historical development diagnostic; greedy160 first answer and conditional up-to3 retries separately, not independent benchmark',
        auxiliary_head_used_for_generation=False,checkpoint_saved=False,model_training=False,
        scope='fresh code facts and unscored pseudo QA; not world benchmark/75M/300M')
    base.training.write(target/'report.json',value)
    return 0


def generate_public(model,cfg,tok,rows,directory):
    import torch
    from scripts.diag_p101a_mtp_parity import PrecisionForward
    from tinylm.chat.serialize import serialize
    from tinylm.infer.generate import sample
    from tinylm.train.mtp_sft import encode_record
    writer=ShardWriter(directory,'answers_public_source');counts=Counter()
    model.eval();model.freeze_quant();wrapped=PrecisionForward(model,'fp32_math')
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    try:
        with torch.no_grad():
            for row in rows:
                base.deadline();prompt=serialize(dict(messages=row['messages'][:-1]),'chatml',add_generation_prompt=True)
                limit=generation_budget(len(tok.encode(prompt).ids),cfg.max_seq_len)
                decoded,meta=sample(wrapped,cfg,tok,prompt,max_new=limit,temperature=0.,top_k=1,device='cuda',
                    logits_last_only=True,return_metadata=True,stop_token_sequences=[tok.encode('<|im_end|>').ids])
                prefix=tok.decode(tok.encode(prompt).ids)
                if not decoded.startswith(prefix):raise ValueError('public prefix extraction failed')
                answer=decoded[len(prefix):];gold=base.data.text(row,-1)
                target=encode_record(row,tok).targets
                counts.update(cases=1,literal_agreement=int(answer.strip()==gold.strip()),empty=int(not answer.strip()),
                    max_new=int(meta['finish_reason'] in ('MAX_NEW','MAX_NEW_EOS_DISABLED')),
                    context_cap_below256=int(limit<256),teacher_target_exceeds_cap=int(target>limit))
                writer.append(dict(label='public_source',messages=row['messages'][:-1],answer=answer,gold=gold,
                    meta=row['meta'],generation=meta,actual_max_new=limit,teacher_targets=target,
                    semantic_truth='PSEUDO_UNVERIFIED; offline reading required',exact_code_contract=None))
    finally:
        model.clear_quant();model.train()
    manifest=writer.close(lineage=dict(precision='FP32_MATH_NO_TF32',cache=True,native_tokens=1,
        temperature=0,max_new=256,context_cap='min256 and model_limit minus full prompt',semantic_judge=False))
    verify(directory,manifest)
    return dict(counts=dict(counts),raw_directory=str(directory.relative_to(ROOT)),raw_manifest=manifest,
        scope='fixed source dev panel only; literal agreement is not semantic correctness')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=('freeze','cost','train','evaluate'),required=True)
    p.add_argument('--arm',choices=tuple(method.ARMS),default='aux0')
    p.add_argument('--decision-note',default='')
    p.add_argument('--max-wall-sec',type=int,default=3600)
    group=p.add_mutually_exclusive_group(required=True)
    group.add_argument('--execute',action='store_true');group.add_argument('--check-only',action='store_true')
    args=p.parse_args()
    if not 60<=args.max_wall_sec<=7200:p.error('bounded60..7200')
    try:return dispatch(args,p)
    except GateNegative as exc:
        print('[BINDING_AUX_HOLD] '+str(exc),flush=True)
        return 8
    except KeyboardInterrupt:
        print('[BINDING_AUX_INTERRUPTED] incomplete; preserve raw/progress and previous outputs',flush=True)
        return 130
    except Exception as exc:
        print('[BINDING_AUX_ERROR] '+type(exc).__name__+': '+str(exc),flush=True)
        return 9


def dispatch(args,parser):
    if args.check_only:
        if args.mode!='freeze':read_course()
        print('[CHECK_ONLY] '+json.dumps(info()));return 0
    if not args.execute:parser.error('explicit execution required')
    base.deadline();remaining=int((base.DEADLINE-datetime.now(timezone.utc)).total_seconds())-600
    if remaining<60:raise TimeoutError('insufficient margin before17:00')
    args.max_wall_sec=min(args.max_wall_sec,remaining)
    if args.mode=='freeze':
        if not args.decision_note:parser.error('explicit diagnostic-based decision note required')
        return freeze(args)
    return train(args,cost=args.mode=='cost') if args.mode in ('train','cost') else evaluate(args)


if __name__=='__main__':raise SystemExit(main())
