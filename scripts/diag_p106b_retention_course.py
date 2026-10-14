#!/usr/bin/env python3
"""Bounded same-parent SFT/native-replay experiment; explicit execute and fresh outputs."""
from __future__ import annotations
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter,defaultdict
from dataclasses import asdict
from datetime import datetime,timezone
import json
import math
import os
import tempfile
import time
from scripts import p106b_retention_course as data
from scripts import diag_p101a_sft_mtp as training
from scripts.p106b_shards import ShardWriter,verify

TAG='p106b_context_replay_v2_s1337'
CORPUS=ROOT/'HF/sft_ready'/TAG/'corpus'
EVIDENCE=ROOT/'test_result/evidence'/TAG
LOCAL=ROOT/'test_result/evidence/local'/TAG
NATIVE=ROOT/'data_cache/ko-en_601000000_chat32'
DEADLINE=datetime(2026,10,15,8,0,tzinfo=timezone.utc)
CODE=('scripts/p106b_retention_course.py','scripts/diag_p106b_retention_course.py',
      'scripts/test_p106b_retention_course.py','scripts/diag_p106b_context_quality.py',
      'scripts/diag_p101a_mtp_parity.py','scripts/p106b_education_followup.py',*training.CODE)


def info():
    return dict(schema=data.VERSION,tag=TAG,parent_sha256=training.PARENT_SHA,
        tokenizer_sha256=training.data.TOK_SHA,seed=1337,micro_bs=8,accum=16,seq=1024,
        checkpoint_on=True,compile='default',epochs=4,lr=5e-5,muon_lr=2e-4,
        mtp=False,teacher_calls=0,weights=data.WEIGHTS,replay_micro_bs=8,
        native_replay='one additional8x1024 train-only CE batch per SFT optimizer update, even weight0',
        code_sha256={p:training.data.digest(ROOT/p) for p in sorted(set(CODE))},
        deadline_utc=DEADLINE.isoformat(),formal_train_ready=False,
        general_intelligence='NOT_ESTABLISHED',scope='new experimental curriculum, not75M/300M')


def deadline():
    if datetime.now(timezone.utc)>=DEADLINE:
        raise TimeoutError('2026-10-15 17:00 KST execution authority expired')


def checkpoint(arm):
    return ROOT/'runs/ckpt'/f'm100s10_ko-en_context_replay_dense_chat32_{TAG}_{arm}.pt'


def freeze():
    deadline()
    if CORPUS.parent.exists() or CORPUS.is_symlink() or EVIDENCE.exists():
        raise FileExistsError('preserve old course; new namespace required')
    from scripts import diag_p106b_source_course as source
    from tokenizers import Tokenizer
    from tinylm.train import mtp_sft as core
    import numpy as np
    if training.data.digest(training.data.TOKENIZER)!=training.data.TOK_SHA:
        raise ValueError('tokenizer changed')
    meta=json.loads((NATIVE/'meta.json').read_text())
    if meta['tokenizer_sha256']!=training.data.TOK_SHA or meta['token_dtype']!='uint16':
        raise ValueError('native replay tokenizer/dtype differs')
    _,old=source.read_course()
    rows=data.add_public(data.code_rows(),old);families=data.validate_splits(rows)
    tok=Tokenizer.from_file(str(training.data.TOKENIZER));counts={}
    for split,values in rows.items():
        records=[core.encode_record(row,tok) for row in values]
        counts[split]=dict(rows=len(values),actual_x_tokens=sum(r.x_tokens for r in records),
            assistant_targets=sum(r.targets for r in records),kinds=families[split],
            languages=dict(Counter(r['meta']['language'] for r in values)))
    if counts['train']['rows']!=5632:
        raise ValueError('expected code5120 plus public512')
    expected=4*math.ceil(len(rows['train'])/128)
    tokens=np.memmap(NATIVE/'train.bin',dtype=np.uint16,mode='r')
    offsets=data.native_offsets(len(tokens),expected*8)
    identities={name:training.data.digest(NATIVE/name) for name in ('meta.json','train.bin','val.bin')}
    CORPUS.mkdir(parents=True,exist_ok=False);manifests={}
    for split,values in rows.items():
        writer=ShardWriter(CORPUS,split)
        for row in values:writer.append(row)
        manifests[split]=writer.close(lineage=info());verify(CORPUS,manifests[split])
    with (CORPUS/'native_train.bin').open('xb') as stream:
        for offset in offsets:stream.write(tokens[offset:offset+1025].tobytes())
    report=dict(info(),status='COURSE_FROZEN',counts=counts,manifests=manifests,
        expected_updates=expected,native_source_sha256=identities,native_train_offsets=offsets,
        native_copy_sha256=training.data.digest(CORPUS/'native_train.bin'),
        native_replay_targets_per_arm=expected*8*1024,
        prior_public_source_report_sha256=training.data.digest(source.CORPUS/'report.json'),
        root_and_conversation_overlap=0,binding_names_disjoint=True,
        native_split_scope='train.bin for replay; val.bin for diagnostics; prior pretraining leakage not audited',
        native_copy_scope='disjoint selected train windows, repeated across arms but not within an arm')
    training.write(CORPUS/'report.json',report);training.write(EVIDENCE/'corpus_report.json',report)
    print('[REPLAY_CORPUS] '+json.dumps(dict(counts=counts,updates=expected),ensure_ascii=False),flush=True)
    return 0


def read_course():
    report=json.loads((CORPUS/'report.json').read_text())
    if report['status']!='COURSE_FROZEN' or report['code_sha256']!=info()['code_sha256']:
        raise ValueError('frozen code differs; preserve old evidence and use new stage')
    for manifest in report['manifests'].values():verify(CORPUS,manifest)
    if training.data.digest(CORPUS/'native_train.bin')!=report['native_copy_sha256']:
        raise ValueError('native copied train changed')
    if training.data.digest(NATIVE/'val.bin')!=report['native_source_sha256']['val.bin']:
        raise ValueError('native validation changed')
    rows={s:list(training.data.stream_rows(CORPUS,m)) for s,m in report['manifests'].items()}
    data.validate_splits(rows)
    return report,rows


def dev_sample(rows):
    groups=defaultdict(list);public=[]
    for row in rows:
        if row['meta']['kind']=='public_qa':public.append(row);continue
        groups[(row['meta']['language'],row['meta']['kind'])].append(row)
    result=[]
    for key,values in sorted(groups.items()):
        if key[1].startswith('binding_'):
            roots=sorted({r['meta']['semantic_root_id'] for r in values})[:4]
            result.extend(r for r in values if r['meta']['semantic_root_id'] in roots)
        else:result.extend(values[:4])
    return result+public[:16]


def generate(base,cfg,tok,rows,directory,label):
    import torch
    from scripts.diag_p101a_mtp_parity import PrecisionForward
    from tinylm.chat.serialize import serialize
    from tinylm.infer.generate import sample
    base.eval();base.freeze_quant();wrapped=PrecisionForward(base,'fp32_math')
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    writer=ShardWriter(directory,'answers_'+label)
    counts=defaultdict(Counter);roots=defaultdict(list);examples=[]
    try:
        with torch.no_grad():
            for row in rows:
                deadline();m=row['meta']
                prompt=serialize(dict(messages=row['messages'][:-1]),'chatml',add_generation_prompt=True)
                decoded,meta=sample(wrapped,cfg,tok,prompt,max_new=64,temperature=0.,top_k=1,
                    device='cuda',logits_last_only=True,return_metadata=True,
                    stop_token_sequences=[tok.encode('<|im_end|>').ids])
                prefix=tok.decode(tok.encode(prompt).ids)
                if not decoded.startswith(prefix):raise ValueError('prompt extraction failed')
                answer=decoded[len(prefix):];gold=data.text(row,-1)
                judged=data.exact(answer,gold,m['rubric'])
                counter=counts[m['language']+':'+m['kind']]
                counter.update(cases=1,scored=int(judged is not None),exact=int(judged is True),
                    teacher_literal_agreement=int(answer.strip()==gold.strip()),empty=int(not answer.strip()),
                    max_new=int(meta['finish_reason'] in ('MAX_NEW','MAX_NEW_EOS_DISABLED')))
                if m['kind'].startswith('binding_'):
                    roots[m['semantic_root_id']].append(judged is True)
                    counter['first_value_baseline']+=int(gold==m['first_value'])
                writer.append(dict(label=label,messages=row['messages'][:-1],answer=answer,gold=gold,
                    meta=m,generation=meta,exact_code_contract=judged,
                    prior_context='GOLD_HISTORY_FOR_MULTITURN; not actual student rollout'))
                if len(examples)<12 and m['kind']!='public_qa':
                    example=dict(question=data.text(row,-2),answer=answer,gold=gold,exact=judged)
                    examples.append(example)
    finally:
        base.clear_quant();base.train()
    manifest=writer.close(lineage=dict(label=label,precision='FP32_MATH_NO_TF32',cache=True,
        mtp_tokens=1,temperature=0,max_new=64,semantic_judge=False))
    verify(directory,manifest)
    result=dict(counts={k:dict(v) for k,v in counts.items()},binding_roots=len(roots),
        all4_exact_roots=sum(len(v)==4 and all(v) for v in roots.values()),
        raw_directory=str(directory.relative_to(ROOT)),raw_manifest=manifest,
        examples=examples,public_agreement_is_not_truth=True)
    print('[REPLAY_ANSWERS] '+json.dumps(dict(label=label,counts=result['counts'],
        binding_roots=len(roots),all4_exact_roots=result['all4_exact_roots']),ensure_ascii=False),flush=True)
    return result


def train(args,cost=False):
    deadline();report,rows=read_course();arm=args.arm;weight=data.WEIGHTS[arm]
    target=EVIDENCE/(('cost_' if cost else '')+arm);local=LOCAL/(('cost_' if cost else '')+arm)
    out=checkpoint(arm)
    if target.exists() or local.exists() or (not cost and out.exists()):
        raise FileExistsError('fresh arm only')
    if not cost:
        calibrated=json.loads((EVIDENCE/'cost_sft_only/report.json').read_text())
        if calibrated['code_sha256']!=info()['code_sha256'] or calibrated['updates']!=8:
            raise ValueError('same-code cost8 required')
    from scripts.p106b_gate_runtime import idle_before_gpu,wall_limit
    from tinylm.train import mtp_sft as core
    import numpy as np
    idle_before_gpu();target.mkdir(parents=True,exist_ok=False);began=time.perf_counter()
    with wall_limit(args.max_wall_sec):
        torch,base,cfg,tok,initial=training.load_runtime('parent_ntp')
        records={s:[core.encode_record(r,tok) for r in values] for s,values in rows.items()}
        native=np.memmap(CORPUS/'native_train.bin',dtype=np.uint16,mode='r').reshape(-1,1025)
        os.environ['TORCHINDUCTOR_CACHE_DIR']=tempfile.mkdtemp(prefix='p106b_replay_')
        base=base.cuda();base.train();pad=tok.token_to_id('<|pad|>')
        if pad is None:pad=tok.token_to_id('<pad>')
        if pad is None:raise ValueError('missing PAD')
        torch.cuda.reset_peak_memory_stats()
        before_native=None if cost else training.native_ce(base,NATIVE)
        model=torch.compile(base,mode='default');adam,muon=training.optimizers(base)
        for opt in (adam,muon):
            for group in opt.param_groups:group['lr']*=.5
        steps=processed=targets=native_x=native_y=0;grad_max=0.;seconds=[];history=[]
        for epoch in range(4):
            for groups in training.batches(records['train'],epoch):
                deadline();tick=time.perf_counter()
                denominator=sum(r.targets for micro in groups for r in micro)
                adam.zero_grad(set_to_none=True);muon.zero_grad(set_to_none=True)
                for micro in groups:
                    x,y,seg=core.pad_records(micro,pad,'cuda',fixed_width=1024,batch_size=8)
                    with torch.autocast('cuda',dtype=torch.bfloat16):
                        hidden=model(x,return_hidden=True)
                        sums,valid=core.components(base,hidden,y,seg,horizons=())
                        loss=sums[1]/denominator
                    if not torch.isfinite(loss):raise ValueError('nonfinite SFT loss')
                    loss.backward();processed+=sum(r.x_tokens for r in micro);targets+=sum(r.targets for r in micro)
                # Same native rows/CE calculation in every arm; weight is the only intervention.
                selected=native[steps*8:(steps+1)*8]
                native_records=[core.Record(r[:-1].astype('int64').tolist(),r[1:].astype('int64').tolist(),[1]*1024) for r in selected]
                if len(native_records)!=8:raise ValueError('native schedule exhausted')
                x,y,seg=core.pad_records(native_records,pad,'cuda',fixed_width=1024,batch_size=8)
                with torch.autocast('cuda',dtype=torch.bfloat16):
                    hidden=model(x,return_hidden=True)
                    sums,valid=core.components(base,hidden,y,seg,horizons=())
                    aux=weight*sums[1]/8192
                if not torch.isfinite(aux):raise ValueError('nonfinite native loss')
                aux.backward();native_x+=8192;native_y+=valid[1]
                gradient=torch.nn.utils.clip_grad_norm_(base.parameters(),1.)
                if not torch.isfinite(gradient):raise ValueError('nonfinite gradients')
                grad_max=max(grad_max,float(gradient));adam.step();muon.step();steps+=1
                torch.cuda.synchronize();seconds.append(time.perf_counter()-tick)
                if steps==1 or steps%16==0:
                    print('[REPLAY_UPDATE] '+json.dumps(dict(arm=arm,update=steps,sft_x=processed,
                        assistant_targets=targets,native_x=native_x,last_sec=seconds[-1])),flush=True)
                if cost and steps==8:break
            if cost:break
            val=training.evaluate(base,records['dev'],pad)
            native_eval=training.native_ce(base,NATIVE)
            generations=generate(base,cfg,tok,dev_sample(rows['dev']),local,f'dev_epoch{epoch+1}')
            history.append(dict(epoch=epoch+1,updates=steps,val=val,native=native_eval,dev=generations))
        if not cost and (steps!=report['expected_updates'] or processed!=4*report['counts']['train']['actual_x_tokens']):
            raise ValueError('exposure differs')
        result=dict(info(),arm=arm,weight=weight,status='COST_MEASURED' if cost else 'TRAINED_SEALED_TEST_PENDING',
            initial_core_sha256=initial,corpus_sha256=training.data.digest(CORPUS/'report.json'),updates=steps,
            sft_x_tokens=processed,assistant_targets=targets,native_x_tokens=native_x,native_targets=native_y,
            effective_native_objective_targets=native_y if weight else 0,
            grad_max=grad_max,gradient_measure='global preclip norm maximum including early updates; clip1',
            peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20,step_seconds=seconds,
            native_before=before_native,history=history,whole_sec=time.perf_counter()-began,
            actual_student_rollout='NOT_RUN',independent_world_truth='NOT_RUN')
        if not cost:
            with out.open('xb') as stream:
                torch.save(dict(model=base.state_dict(),cfg=asdict(cfg),step=steps,tokenizer_lineage='chat32',
                    tokenizer_sha256=training.data.TOK_SHA,retention_course=dict(tag=TAG,arm=arm,
                    corpus_sha256=result['corpus_sha256'])),stream)
            result.update(checkpoint=str(out.relative_to(ROOT)),checkpoint_sha256=training.data.digest(out),optimizer_saved=False)
        training.write(target/'report.json',result)
    print('[REPLAY_FINAL] '+json.dumps({k:result[k] for k in ('arm','status','updates','sft_x_tokens','native_x_tokens','whole_sec')}),flush=True)
    return 0


def evaluate(args):
    deadline();report,rows=read_course();target=EVIDENCE/'sealed_test'
    if target.exists():raise FileExistsError('sealed test immutable')
    arms={arm:json.loads((EVIDENCE/arm/'report.json').read_text()) for arm in data.WEIGHTS}
    for arm,r in arms.items():
        if (r['status']!='TRAINED_SEALED_TEST_PENDING' or r['code_sha256']!=info()['code_sha256'] or
            training.data.digest(ROOT/r['checkpoint'])!=r['checkpoint_sha256']):
            raise ValueError('completed same-code three arms required')
    from scripts.p106b_gate_runtime import idle_before_gpu,wall_limit
    from tinylm.infer.generate import _strip
    import gc
    idle_before_gpu();began=time.perf_counter();summaries={}
    with wall_limit(args.max_wall_sec):
        for arm in ('parent',*data.WEIGHTS):
            deadline();torch,base,cfg,tok,initial=training.load_runtime('parent_ntp')
            if arm!='parent':
                state=torch.load(ROOT/arms[arm]['checkpoint'],map_location='cpu',weights_only=True)
                base.load_state_dict(_strip(state['model']),strict=True);del state
            base=base.cuda()
            summaries[arm]=generate(base,cfg,tok,rows['test'],LOCAL/'sealed_test'/arm,'sealed')
            summaries[arm]['native']=training.native_ce(base,NATIVE)
            del base;gc.collect();torch.cuda.empty_cache()
    result=dict(info(),status='SEALED_CODE_TEST_COLLECTED',arms=summaries,whole_sec=time.perf_counter()-began,
        corpus_sha256=training.data.digest(CORPUS/'report.json'),cases_per_arm=len(rows['test']),
        model_training=False,checkpoint_saved=False,first_test_use=True,actual_student_rollout='NOT_RUN',
        interpretation='code-defined conditional task, not general intelligence/world knowledge; no sigma measured')
    training.write(target/'report.json',result)
    return 0


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('corpus','cost','train','evaluate'),required=True)
    parser.add_argument('--arm',choices=tuple(data.WEIGHTS),default='sft_only')
    parser.add_argument('--max-wall-sec',type=int,default=3600)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--execute',action='store_true');group.add_argument('--check-only',action='store_true')
    args=parser.parse_args()
    if not 60<=args.max_wall_sec<=21600:parser.error('wall bound60..21600')
    if args.check_only:
        if args.mode!='corpus':read_course()
        print('[CHECK_ONLY] '+json.dumps(info()));return 0
    deadline()
    if args.mode=='corpus':return freeze()
    if args.mode in ('cost','train'):return train(args,cost=args.mode=='cost')
    return evaluate(args)


if __name__=='__main__':raise SystemExit(main())
