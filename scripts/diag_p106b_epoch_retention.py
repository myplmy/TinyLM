#!/usr/bin/env python3
"""User GPU: immutable parent and four saved epochs, same36 replies/native val.

No teacher, retraining or checkpoint writes. CPU preflight verifies exact files,
not model quality. Epoch format is validated explicitly instead of fabricating
the final checkpoint's tokenizer metadata in the original file.
"""
from __future__ import annotations
import argparse
import gc
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.diag_p106b_refill_multiaxis import require_education,CORPUS_SHA,CORPUS,CHILD,load
from scripts.p106b_refill_eval_panel import collect,summarize,panel_sha
from scripts.p106b_mixed_scale import digest,safe_repo_path,TOKENIZER,TOK_SHA
from scripts.p106b_education_followup import ARMS
from scripts.p106b_gate_runtime import idle_before_gpu,wall_limit,disposition
from scripts.p106b_shards import ShardWriter,verify

SOURCE=ROOT/'HF/sft_ready/p106b_mixed_student_v3_en_refill'
OUTPUT=ROOT/'HF/sft_ready/p106b_epoch_retention_v1'
EDUCATION_SHA='B6F3CFF6255CEB23C75BC062099EB6B8F6B692D0F481F806459E4FB99DDE9E09'
PREVIOUS=ROOT/'HF/sft_ready/p106b_refill_multiaxis_v1'
PREVIOUS_SHA='139834F28C1E80A610C4C3CEF23AC5CDA717D2C5D00F07CEB652A21852167EDD'


def carried_answers():
    safe_repo_path(PREVIOUS)
    if digest(PREVIOUS/'report.json')!=PREVIOUS_SHA:raise ValueError('previous answer collection changed')
    previous=json.loads((PREVIOUS/'report.json').read_text(encoding='utf-8'))
    if previous['input']['panel_sha256']!=panel_sha():raise ValueError('panel changed, old answers cannot be inherited')
    if digest(CHILD)!=previous['input']['child_sha256']:raise ValueError('completed child differs')
    result={}
    for label,source in (('parent','parent'),('epoch4','student')):
        m=json.loads((PREVIOUS/f'answers_{source}_shards_manifest.json').read_text(encoding='utf-8'));verify(PREVIOUS,m)
        rows=[json.loads(line) for s in m['shards'] for line in (PREVIOUS/s['path']).read_text(encoding='utf-8').splitlines()]
        if len(rows)!=36 or m['concat_sha256']!=previous['models'][source]['raw_concat_sha256']:
            raise ValueError('exact36 inherited rows differ')
        result[label]=dict(rows=rows,source_model=source,concat_sha256=m['concat_sha256'])
    return result


def epoch_metadata(state,education,epoch):
    history=education['history'][:epoch]
    if (epoch not in (1,2,3,4) or state.get('epoch')!=epoch or state.get('input')!=education['input']
        or state.get('history')!=history or state.get('updates')!=history[-1]['updates']
        or state.get('step')!=2289+history[-1]['updates']
        or state.get('processed_tokens')!=sum(x['processed_tokens'] for x in history)):
        raise ValueError('epoch snapshot identity/history differs; wire/restarted model refused')
    snapshot_cfg=state.get('cfg',{})
    if snapshot_cfg.get('n_layers')!=14 or snapshot_cfg.get('tie_mlp') is not False or snapshot_cfg.get('vocab_size')!=32768:
        raise ValueError('same dense14/chat32 architecture required')


def check():
    safe_repo_path(OUTPUT)
    if OUTPUT.exists() or OUTPUT.is_symlink():raise FileExistsError('prior/partial output preserved; use new stage')
    paths=[SOURCE/'report.json',CORPUS/'report.json',TOKENIZER,ROOT/ARMS['b']['parent'],
           ROOT/ARMS['b']['cache']/'val.bin',CHILD]+[SOURCE/f'epoch_{e}.pt' for e in (1,2,3)]
    identities={}
    for path in paths:
        safe_repo_path(path)
        if not path.is_file():raise FileNotFoundError('exact input absent: '+str(path.relative_to(ROOT)))
        identities[str(path.relative_to(ROOT))]=digest(path)
    if identities[str((SOURCE/'report.json').relative_to(ROOT))]!=EDUCATION_SHA:
        raise ValueError('completed4pass report changed')
    corpus=json.loads((CORPUS/'report.json').read_text(encoding='utf-8'));education=json.loads((SOURCE/'report.json').read_text(encoding='utf-8'))
    require_education(education,corpus)
    if identities[str((CORPUS/'report.json').relative_to(ROOT))]!=CORPUS_SHA or digest(TOKENIZER)!=TOK_SHA:
        raise ValueError('corpus/tokenizer differs')
    if identities[ARMS['b']['parent']]!=ARMS['b']['sha']:raise ValueError('parent differs')
    carried=carried_answers()
    return dict(schema='P106B_EPOCH_RETENTION_PREFLIGHT_V1',identities=identities,
                panel_sha256=panel_sha(),models=5,planned_model_calls=108,total_answer_rows=180,
                carried_rows=72,carried_concat_sha256={k:v['concat_sha256'] for k,v in carried.items()},
                native_evaluation='all five endpoints freshly measured on the same current val.bin',maximum_attempts=1,
                max_new=160,max_input=800,teacher_resident=False,training='NOT_RUN',
                semantic_quality='NOT_REVIEWED',max_wall_sec=2400)


def execute(info):
    import torch
    from tokenizers import Tokenizer
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer
    from tinylm.infer.generate import sample,_strip
    from tinylm.data.prepare import verify_chat_tokenizer
    from scripts.paired_eval import full_val_losses
    from scripts.p106b_pipeline import flush_row
    idle_before_gpu();OUTPUT.mkdir(exist_ok=False)
    report=dict(schema='P106B_EPOCH_RETENTION_V1',input=info,models={},actual_model_calls=0,
                student_training='NOT_RUN',checkpoint_saved=False,semantic_quality='NOT_REVIEWED')
    education=json.loads((SOURCE/'report.json').read_text(encoding='utf-8'));carried=carried_answers()
    writer=None;base=None;begin=time.perf_counter()
    try:
        with wall_limit(2400):
            tok=Tokenizer.from_file(str(TOKENIZER));verify_chat_tokenizer(tok,32768)
            torch.set_num_threads(1);geometry=None
            for e in (0,1,2,3,4):
                label='parent' if e==0 else f'epoch{e}'
                torch.cuda.reset_peak_memory_stats()
                if e==0:base,cfg=load(ROOT/ARMS['b']['parent'],tok,torch)
                elif e==4:base,cfg=load(CHILD,tok,torch,education)
                else:
                    state=torch.load(SOURCE/f'epoch_{e}.pt',map_location='cpu',weights_only=True)
                    epoch_metadata(state,education,e)
                    cfg=TMTConfig(**state['cfg']);base=TiedMLPTransformer(cfg).cuda()
                    base.load_state_dict(_strip(state['model']),strict=True);del state
                    base.set_anneal(1.0);base.eval();base.freeze_quant()
                current={k:v for k,v in cfg.__dict__.items() if k!='grad_checkpoint'}
                if geometry is not None and current!=geometry:raise ValueError('endpoint architectures differ')
                geometry=current;writer=ShardWriter(OUTPUT,'answers_'+label)
                def persist(row):writer.append(dict(model=label,**row));flush_row(writer)
                def infer(prompt,value):
                    input_tokens=len(tok.encode(prompt).ids)
                    if input_tokens>800:raise ValueError('input budget exceeded, no silent truncation')
                    seed=20261005+int(panel_sha({'id':value['id']})[:6],16)
                    torch.manual_seed(seed);t=time.perf_counter();report['actual_model_calls']+=1
                    full,meta=sample(base,cfg,tok,prompt,max_new=160,temperature=0,top_k=1,
                        device='cuda',logits_last_only=True,return_metadata=True,
                        stop_token_sequences=[tok.encode('<|im_end|>').ids])
                    prefix=tok.decode(tok.encode(prompt).ids)
                    if not full.startswith(prefix):
                        persist(dict(case=value,raw_full_text=full,prompt=prompt,generation=meta,
                                     extraction_status='PREFIX_MISMATCH',human_review='NOT_RUN'))
                        raise ValueError('prefix mismatch, not semantic failure')
                    answer=full[len(prefix):]
                    print('[EPOCH_ANSWER] '+json.dumps(dict(model=label,id=value['id'],
                        question=value['question'],answer=answer,finish_reason=meta.get('finish_reason')),ensure_ascii=False),flush=True)
                    return answer,dict(meta,seed=seed,input_tokens=input_tokens,wall_sec=time.perf_counter()-t,
                                       raw_full_text=full)
                if label in carried:
                    rows=carried[label]['rows']
                    for row in rows:persist(dict(row,answer_evidence='HASH_LOCKED_PRIOR_COLLECTION',
                                              prior_source_model=carried[label]['source_model']))
                else:rows=collect(infer,on_row=persist)
                manifest=writer.close(lineage=info);verify(OUTPUT,manifest);writer=None
                losses,count=full_val_losses(base,cfg,ROOT/ARMS['b']['cache'],1024,4,'cuda')
                result=dict(summary=summarize(rows),native_ce=sum(losses)/len(losses),native_tokens=count,
                    trained_x_tokens=0 if e==0 else sum(h['processed_tokens'] for h in education['history'][:e]),
                    answer_evidence='HASH_LOCKED_PRIOR_COLLECTION' if label in carried else 'NEW_FIRST_ANSWERS',
                    newly_generated_answers=0 if label in carried else 36,
                    raw_concat_sha256=manifest['concat_sha256'],peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20)
                report['models'][label]=result
                print('[EPOCH_RESULT] '+json.dumps(dict(model=label,**result),ensure_ascii=False),flush=True)
                base.clear_quant();del base;base=None;gc.collect();torch.cuda.empty_cache()
            parent=report['models']['parent']['native_ce']
            for label,rec in report['models'].items():rec['native_delta_vs_parent']=rec['native_ce']-parent
            report.update(status='EPOCH_COLLECTION_COMPLETE',returncode=0)
    except BaseException as exc:
        status,rc=disposition(exc);report.update(status=status,returncode=rc,error_type=type(exc).__name__,error=str(exc)[:1600])
    finally:
        if writer is not None and writer._total_rows:
            m=writer.close(lineage=info);verify(OUTPUT,m);report['partial_manifest']=m
        report['whole_wall_sec']=time.perf_counter()-begin
        with (OUTPUT/'report.json').open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
        print('[EPOCH_FINAL] '+json.dumps(dict(status=report['status'],returncode=report['returncode'],
             actual_model_calls=report['actual_model_calls'],planned_model_calls=108,
             total_answer_rows=180,carried_rows=72,quality='NOT_REVIEWED'),ensure_ascii=False),flush=True)
    return report['returncode']


def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true');a=p.parse_args()
    try:
        info=check()
        if a.check_only:print('[CHECK_ONLY] '+json.dumps(info));return 0
        return execute(info)
    except (FileNotFoundError,FileExistsError) as exc:print('[HOLD] '+str(exc),file=sys.stderr);return 8
    except Exception as exc:print('[ERROR] '+str(exc),file=sys.stderr);return 9


if __name__=='__main__':raise SystemExit(main())
