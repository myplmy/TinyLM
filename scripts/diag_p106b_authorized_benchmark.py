#!/usr/bin/env python3
"""Authorized fixed public benchmark of five immutable chat32 checkpoints.

CPU freeze/strict-load precedes any GPU evaluation. MC reuses the existing
scorer; free QA uses the production sampler. No training or network services.
"""
from __future__ import annotations
import argparse
from collections import Counter
import gc
import hashlib
import json
import math
from pathlib import Path
import random
import re
import statistics
import sys
import time
import unicodedata

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import eval_bench_suite as suite
from scripts.p106b_shards import ShardWriter,verify

TAG='p106b_authorized_validation_v1_s1337'
FROZEN=ROOT/'HF/sft_ready'/TAG/'public_benchmark'
EVIDENCE=ROOT/'test_result/evidence'/TAG
LOCAL=ROOT/'test_result/evidence/local'/TAG/'public_benchmark'
TOKENIZER=ROOT/'data_cache/tok-ko-en-32768-chat32.json'
TOKENIZER_SHA='9716F40E4C504D6AF37DDE76CCA578E30B45E9CA86C8B6BB79B2FA095D3AC88E'
TASKS=('kobest_copa','kobest_hellaswag','klue_nli','klue_ynat','piqa','hellaswag','arc_easy')
SEED=20261016
MC_N=256
GEN_N=64
MAX_NEW=128
CONTEXT=1024
BASE=('pretrain_chat32','runs/ckpt/m100s10_ko-en_300M_dense_chat32_p090b_s1337.pt',
      '12E18658CDCD0AFEBE5A87073DC8977304C0D490A03A8471779D514FBB0D9950')
REPORTS={
 'raw_role':'test_result/evidence/p106b_repair_role_v1_s1337/raw_role/report.json',
 'recovery':'test_result/evidence/p106b_evidence_preference_v1_s1337/evaluate/parent_report.json',
 'sft_only':'test_result/evidence/p106b_evidence_preference_v1_s1337/sft_only/report.json',
 'orpo010':'test_result/evidence/p106b_evidence_preference_v1_s1337/orpo010/report.json'}


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest().upper()


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:
        json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')


def normalized(text):
    # Preserve decimal points, minus signs, negation and internal word spacing.
    return ' '.join(unicodedata.normalize('NFKC',text).casefold().split())


def answer_scores(answer,golds):
    a=normalized(answer)
    exact=any(a==normalized(g) for g in golds)
    def f1(g):
        left=Counter(c for c in a if not c.isspace())
        right=Counter(c for c in normalized(g) if not c.isspace())
        common=sum((left&right).values())
        return 2*common/(sum(left.values())+sum(right.values())) if left and right else float(left==right)
    return dict(whitespace_nfkc_exact=int(exact),char_overlap_f1=max(map(f1,golds)))


def numerical(answer):
    text=answer.rsplit('####',1)[-1].strip().replace(',','')
    if re.fullmatch(r'[-+]?\d+(?:\.\d+)?',text):
        from decimal import Decimal
        return str(Decimal(text).normalize())
    return None


def sampled_indices(n,count,seed=SEED):
    values=list(range(count));random.Random(seed).shuffle(values)
    return sorted(values[:min(n,count)])


def candidates():
    specs=[BASE]
    for name,path in REPORTS.items():
        r=json.loads((ROOT/path).read_text(encoding='utf-8'))
        specs.append((name,r['checkpoint'],r['checkpoint_sha256']))
    return specs


def source_items(tok):
    from tinylm.chat.serialize import serialize
    sources={};tasks={}
    for task in TASKS:
        path=ROOT/'datasets/bench'/f'{task}.jsonl'
        raw=[json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
        chosen=sampled_indices(MC_N,len(raw));items=[]
        for i in chosen:
            item=suite.ADAPTERS[task](raw[i]);item['_iid']=f'{task}#{i}'
            items.append(dict(task=task,kind='mc',index=i,item=item))
        sources[task]=dict(path=str(path.relative_to(ROOT)),sha256=digest(path),rows=len(raw),indices=chosen)
        tasks[task]=items
    path=ROOT/'datasets/KorQuad/KorQuAD_2.1/KorQuAD_v1.0_dev.json'
    data=json.loads(path.read_text(encoding='utf-8'));flat=[]
    for article in data['data']:
        for paragraph in article['paragraphs']:
            for qa in paragraph['qas']:
                flat.append((paragraph['context'],qa))
    selected=sampled_indices(GEN_N,len(flat));ko=[]
    for i in selected:
        context,qa=flat[i]
        text=f"지문: {context}\n질문: {qa['question']}\n질문에 대한 답만 간결하게 쓰세요."
        prompt=serialize(dict(messages=[dict(role='user',content=text)]),'chatml',add_generation_prompt=True)
        ko.append(dict(task='korquad_free',kind='gen',index=i,id=qa['id'],prompt=prompt,
                       question=qa['question'],golds=[a['text'] for a in qa['answers']],
                       prompt_tokens=len(tok.encode(prompt).ids)))
    sources['korquad_free']=dict(path=str(path.relative_to(ROOT)),sha256=digest(path),rows=len(flat),indices=selected)
    tasks['korquad_free']=ko
    path=ROOT/'datasets/bench/gsm8k.jsonl'
    raw=[json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    selected=sampled_indices(GEN_N,len(raw));maths=[]
    for i in selected:
        question=raw[i]['question']
        text=question+'\nReturn the final numerical answer. If you show working, end with #### <number>.'
        prompt=serialize(dict(messages=[dict(role='user',content=text)]),'chatml',add_generation_prompt=True)
        maths.append(dict(task='gsm8k_free',kind='gen',index=i,id=f'gsm8k#{i}',prompt=prompt,
                          question=question,golds=[raw[i]['answer'].split('####')[-1].strip()],
                          prompt_tokens=len(tok.encode(prompt).ids)))
    sources['gsm8k_free']=dict(path=str(path.relative_to(ROOT)),sha256=digest(path),rows=len(raw),indices=selected)
    tasks['gsm8k_free']=maths
    return tasks,sources


def freeze():
    import torch
    from tokenizers import Tokenizer
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer
    from tinylm.infer.generate import _strip
    if FROZEN.exists():raise FileExistsError('frozen benchmark preserved')
    if digest(TOKENIZER)!=TOKENIZER_SHA:raise ValueError('exact chat32 tokenizer changed')
    tok=Tokenizer.from_file(str(TOKENIZER));models=[];geometry=None
    for name,path,sha in candidates():
        if digest(ROOT/path)!=sha:raise ValueError('checkpoint SHA differs: '+name)
        saved=torch.load(ROOT/path,map_location='cpu',weights_only=True)
        if saved.get('tokenizer_sha256')!=TOKENIZER_SHA or saved.get('tokenizer_lineage')!='chat32':
            raise ValueError('checkpoint tokenizer identity differs: '+name)
        cfg=TMTConfig(**saved['cfg']);model=TiedMLPTransformer(cfg)
        model.load_state_dict(_strip(saved['model']),strict=True)
        shapes={k:list(v.shape) for k,v in model.state_dict().items()}
        if geometry is None:geometry=shapes
        if shapes!=geometry or cfg.max_seq_len!=CONTEXT or cfg.mtp_aux:
            raise ValueError('same geometry/context and native one-token inference required')
        models.append(dict(name=name,checkpoint=path,sha256=sha,config=saved['cfg'],
                           n_layers=cfg.n_layers,parameters=sum(p.numel() for p in model.parameters())))
        del model,saved;gc.collect()
    if torch.cuda.is_initialized():raise ValueError('CPU freeze unexpectedly initialized CUDA')
    tasks,sources=source_items(tok)
    FROZEN.mkdir(parents=True,exist_ok=False)
    writer=ShardWriter(FROZEN,'cases')
    for rows in tasks.values():
        for row in rows:writer.append(row)
    manifest=writer.close(lineage=dict(seed=SEED,model_selection='frozen before benchmark outputs'))
    verify(FROZEN,manifest)
    report=dict(schema='P106B_AUTHORIZED_PUBLIC_BENCHMARK_V1',status='FROZEN_CPU_STRICT_LOAD_PASSED',
        driver_sha256=digest(__file__),models=models,tokenizer=str(TOKENIZER.relative_to(ROOT)),
        tokenizer_sha256=TOKENIZER_SHA,sources=sources,manifest=manifest,
        mc_tasks=list(TASKS),mc_n=MC_N,gen_n=GEN_N,seed=SEED,context=CONTEXT,max_new=MAX_NEW,
        precision='FP32_MATH',model_training_seeds=1,optimizer_updates=0,teacher_calls=0,
        mtp_inference=False,network=False,protected_heldout_used=False,
        contamination='NOT_AUDITED_AGAINST_ALL_PRETRAINING',
        limit='fixed local public subsets, not full official harness; MC likelihood is not free-answer ability',
        gen_eligibility={t:dict(asked=len(tasks[t]),fits=sum(r['prompt_tokens']+MAX_NEW<=CONTEXT for r in tasks[t]))
                         for t in ('korquad_free','gsm8k_free')})
    write(FROZEN/'report.json',report);write(EVIDENCE/'benchmark_inputs.json',report)
    print('[PUBLIC_BENCHMARK_FROZEN] '+json.dumps(dict(models=len(models),cases=manifest['rows'],gen=report['gen_eligibility']),ensure_ascii=False))


def run(max_wall):
    import torch
    import torch.nn.functional as F
    from tokenizers import Tokenizer
    from tinylm.infer.generate import load_model,sample
    from scripts.diag_p101a_mtp_parity import PrecisionForward
    from scripts.p106b_gate_runtime import wall_limit
    report=json.loads((FROZEN/'report.json').read_text(encoding='utf-8'))
    smoke=json.loads((EVIDENCE/'smoke_report.json').read_text(encoding='utf-8'))
    if smoke['failed_calls'] or smoke['summary_returncode'] or not smoke['original_synthetic_unchanged']:
        raise ValueError('complete dynamic smoke prerequisite failed')
    if report['driver_sha256']!=digest(__file__):raise ValueError('frozen benchmark code changed')
    verify(FROZEN,report['manifest'])
    tasks={task:[] for task in (*TASKS,'korquad_free','gsm8k_free')}
    for shard in report['manifest']['shards']:
        for line in (FROZEN/shard['path']).read_text(encoding='utf-8').splitlines():
            r=json.loads(line);tasks[r['task']].append(r)
    for s in report['sources'].values():
        if digest(ROOT/s['path'])!=s['sha256']:raise ValueError('public cache changed')
    if LOCAL.exists() or (EVIDENCE/'benchmark_report.json').exists():raise FileExistsError('old benchmark preserved')
    LOCAL.mkdir(parents=True,exist_ok=False)
    tok=Tokenizer.from_file(str(TOKENIZER));summaries={};start=time.perf_counter()
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    with wall_limit(max_wall):
        for spec in report['models']:
            name=spec['name'];checkpoint=ROOT/spec['checkpoint']
            if digest(checkpoint)!=spec['sha256']:raise ValueError('fixed checkpoint changed')
            model,cfg,device=load_model(arch='dense',ckpt_path=str(checkpoint),device='cuda')
            wrapped=PrecisionForward(model,'fp32_math');torch.cuda.reset_peak_memory_stats()
            writer=ShardWriter(LOCAL/name,'answers');summary={};model_started=time.perf_counter()
            for task,rows in tasks.items():
                began=time.perf_counter()
                if task in TASKS:
                    details=[];skips=[]
                    for offset in range(0,len(rows),16):
                        block=rows[offset:offset+16]
                        result=suite.run_mc(task,[r['item'] for r in block],wrapped,tok,device,CONTEXT,torch,F,False)
                        details.extend(result['rows']);skips.extend(result['skip_rows'])
                        for r in result['rows']:
                            original=next(v for v in block if v['item']['_iid']==r['id'])
                            writer.append(dict(model=name,task=task,kind='mc',**r,source_item=original['item']))
                        for r in result['skip_rows']:writer.append(dict(model=name,task=task,skipped=True,**r))
                        print('[BENCH_PROGRESS] '+json.dumps(dict(model=name,task=task,processed=min(offset+16,len(rows)),asked=len(rows),whole_sec=round(time.perf_counter()-start,2))),flush=True)
                    n=len(details)
                    if not n:raise ValueError('zero scored MC cases: '+task)
                    primary=[int(r['pred_harness']==r['gold']) for r in details]
                    picks=Counter(r['pred_harness'] for r in details)
                    golds=Counter(r['gold'] for r in details)
                    summary[task]=dict(asked=len(rows),n=n,skipped=len(skips),
                        correct=sum(primary),accuracy=suite.wilson(sum(primary),n),
                        accuracy_char_norm=sum(r['pred_harness_norm']==r['gold'] for r in details)/n,
                        internal_pmi_accuracy=sum(r['pred_internal']==r['gold'] for r in details)/n,
                        uniform_chance=statistics.fmean(1/len(r['sum_nll']) for r in details),
                        sample_majority_baseline=max(golds.values())/n,predictions=dict(picks),
                        degenerate_label_over90pct=max(picks.values())/n>.9,
                        gold_ce=statistics.fmean(r['mean_nll'][r['gold']] for r in details))
                else:
                    values=[];skipped=0;finishes=Counter()
                    for row in rows:
                        if row['prompt_tokens']+MAX_NEW>CONTEXT:
                            skipped+=1;writer.append(dict(model=name,task=task,id=row['id'],skipped=True,reason='full_prompt_plus128_exceeds1024'));continue
                        decoded,meta=sample(wrapped,cfg,tok,row['prompt'],max_new=MAX_NEW,temperature=0,top_k=1,
                            device=device,return_metadata=True,logits_last_only=True,use_cache=True,
                            stop_token_sequences=[tok.encode('<|im_end|>').ids])
                        prefix=tok.decode(tok.encode(row['prompt']).ids)
                        if not decoded.startswith(prefix):raise ValueError('generation prefix extraction differs')
                        answer=decoded[len(prefix):].split('<|im_end|>',1)[0].strip()
                        scores=answer_scores(answer,row['golds'])
                        if task=='gsm8k_free':scores['numeric_exact']=int(numerical(answer) is not None and numerical(answer)==numerical(row['golds'][0]))
                        values.append(scores);finishes[meta['finish_reason']]+=1
                        writer.append(dict(model=name,task=task,id=row['id'],prompt=row['prompt'],question=row['question'],
                            golds=row['golds'],answer=answer,generation=meta,scores=scores,skipped=False))
                    if not values:raise ValueError('zero scored generation cases')
                    primary='numeric_exact' if task=='gsm8k_free' else 'whitespace_nfkc_exact'
                    summary[task]=dict(asked=len(rows),n=len(values),skipped=skipped,
                        correct=sum(x[primary] for x in values),primary_metric=primary,
                        accuracy=suite.wilson(sum(x[primary] for x in values),len(values)),
                        char_overlap_f1=statistics.fmean(x['char_overlap_f1'] for x in values),finish_reasons=dict(finishes))
                summary[task]['wall_sec']=time.perf_counter()-began
                print('[PUBLIC_BENCHMARK_TASK] '+json.dumps(dict(model=name,task=task,**summary[task]),ensure_ascii=False),flush=True)
            manifest=writer.close(lineage=dict(checkpoint_sha256=spec['sha256'],inputs_sha256=digest(FROZEN/'report.json')))
            verify(LOCAL/name,manifest)
            if digest(checkpoint)!=spec['sha256']:raise ValueError('read-only checkpoint changed during benchmark')
            summary=dict(model=name,checkpoint=spec['checkpoint'],checkpoint_sha256=spec['sha256'],
                tasks=summary,raw_manifest=manifest,wall_sec=time.perf_counter()-model_started,
                peak_torch_reserved_mib=torch.cuda.max_memory_reserved()/2**20)
            write(EVIDENCE/f'benchmark_{name}.json',summary);summaries[name]=summary
            del wrapped,model;gc.collect();torch.cuda.empty_cache()
    final=dict(schema='P106B_AUTHORIZED_PUBLIC_BENCHMARK_RESULT_V1',status='COMPLETE',
        inputs_sha256=digest(FROZEN/'report.json'),driver_sha256=digest(__file__),models=summaries,
        whole_sec=time.perf_counter()-start,optimizer_updates=0,checkpoint_written=False,
        limit=report['limit'],contamination=report['contamination'])
    write(EVIDENCE/'benchmark_report.json',final)
    print('[PUBLIC_BENCHMARK_FINISHED] '+json.dumps(dict(models=len(summaries),whole_sec=final['whole_sec'])),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=('freeze','run'),required=True)
    p.add_argument('--execute',action='store_true')
    p.add_argument('--max-wall-sec',type=int,default=7200)
    a=p.parse_args()
    if a.mode=='freeze':freeze()
    else:
        if not a.execute:p.error('GPU evaluation requires --execute and current user permission')
        run(a.max_wall_sec)
    return 0


if __name__=='__main__':raise SystemExit(main())
