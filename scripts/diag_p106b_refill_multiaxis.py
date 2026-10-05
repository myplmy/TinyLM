#!/usr/bin/env python3
"""User GPU post-training parent/child36+36 first answers, no teacher or retraining.

CPU preflight only reads exact identities. The new4pass child, not the two-update
wire child, is required. Success means answer collection, not intelligence PASS.
"""
from __future__ import annotations
import argparse
import gc
import json
from pathlib import Path
import sqlite3
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.p106b_refill_eval_panel import panel,panel_sha,collect,summarize
from scripts.p106b_mixed_scale import safe_repo_path,digest,TOKENIZER,TOK_SHA
from scripts.p106b_education_followup import ARMS
from scripts.p106b_gate_runtime import idle_before_gpu,wall_limit,disposition
from scripts.p106b_shards import ShardWriter,verify

CORPUS=ROOT/'HF/sft_ready/p106b_mixed_public_v3_en_refill'
CHILD=ROOT/'runs/ckpt/m100s10_ko-en_300M_p106b_s4_refill300m_chat32_s1337.pt'
CHILD_LOG=ROOT/'runs/logs/m100s10_ko-en_300M_p106b_s4_refill300m_chat32_s1337.json'
OUTPUT=ROOT/'HF/sft_ready/p106b_refill_multiaxis_v1'
CORPUS_SHA='5035CAD5B9B357AB63B8C69F3C73E2D9BAE5E4A76179ECB32EFE2AE4C1A9D005'


def read_json(path):
    safe_repo_path(path)
    if not path.is_file():raise FileNotFoundError('upstream file absent: '+str(path.relative_to(ROOT)))
    return json.loads(path.read_text(encoding='utf-8'))


def require_education(report,corpus):
    expected=sum(corpus['nonpadding_tokens']['train:'+lang] for lang in ('ko','en'))
    if (report.get('status')!='EDUCATION_COMPLETE' or report.get('scope')!='FOUR_REAL_EPOCHS'
            or report.get('processed_conversation_tokens')!=4*expected
            or report.get('input',{}).get('corpus_report_sha256')!=CORPUS_SHA
            or report.get('input',{}).get('parent_sha256')!=ARMS['b']['sha']
            or report.get('input',{}).get('tokenizer_sha256')!=TOK_SHA):
        raise ValueError('completed exact4pass lineage required; wire2 is not education')
    for split in ('train','val'):
        if report['input'].get(split+'_concat_sha256')!=corpus[split+'_concat_sha256']:
            raise ValueError('corpus shard identity differs')
    history=report.get('history',[])
    if len(history)!=4 or any(h.get('epoch')!=i or h.get('epoch_complete') is not True
                              or h.get('processed_tokens')!=expected for i,h in enumerate(history,1)):
        raise ValueError('all four complete epoch records required')


def exact_overlap(corpus):
    from tinylm.chat.canonical import normalize
    from tinylm.data.sft import conversation_split_key
    path=safe_repo_path(CORPUS/'candidate_index.sqlite')
    if not path.is_file():raise FileNotFoundError('exact corpus index absent')
    cases=panel()['singles']+[t for e in panel()['episodes'] for t in e['turns']]
    con=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
    try:
        found=[]
        for c in cases:
            key=conversation_split_key(normalize({'messages':[dict(role='user',content=c['question']),
                                                             dict(role='assistant',content='probe')]})).hex().upper()
            row=con.execute('SELECT split FROM candidates WHERE prompt=? AND selected=1',(key,)).fetchone()
            if row:found.append(dict(id=c['id'],split=row[0]))
        return dict(exact_first_question_matches=found,semantic_or_pretraining_overlap='NOT_RUN',
                    scope='read-only selected corpus index, not a sealed generalization proof')
    finally:con.close()


def check():
    safe_repo_path(OUTPUT)
    if OUTPUT.exists() or OUTPUT.is_symlink():raise FileExistsError('prior/partial outputs preserved, use new stage')
    corpus=read_json(CORPUS/'report.json')
    if digest(CORPUS/'report.json')!=CORPUS_SHA or corpus.get('token_target_ready') is not True:
        raise ValueError('pinned75M corpus differs')
    if digest(TOKENIZER)!=TOK_SHA:raise ValueError('chat32 tokenizer changed')
    parent=ROOT/ARMS['b']['parent'];safe_repo_path(parent)
    if digest(parent)!=ARMS['b']['sha']:raise ValueError('parent identity differs')
    overlap=exact_overlap(corpus)
    print('[PANEL_CPU] '+json.dumps(dict(panel_sha256=panel_sha(),planned_model_calls=72,
        exact_overlap=overlap,model_loading='NOT_RUN'),ensure_ascii=False),flush=True)
    education=read_json(CHILD_LOG);require_education(education,corpus)
    safe_repo_path(CHILD)
    if not CHILD.is_file():raise FileNotFoundError('full4pass child checkpoint absent')
    return dict(schema='P106B_REFILL_MULTIAXIS_PREFLIGHT_V1',parent=ARMS['b']['parent'],
        parent_sha256=ARMS['b']['sha'],child=str(CHILD.relative_to(ROOT)),child_sha256=digest(CHILD),
        child_log_sha256=digest(CHILD_LOG),corpus_report_sha256=CORPUS_SHA,tokenizer_sha256=TOK_SHA,
        panel_sha256=panel_sha(),overlap=overlap,planned_model_calls=72,maximum_attempts=1,
        max_new=160,max_input=800,max_wall_sec=1800,temperature=0,top_k=1,teacher_resident=False,
        semantic_quality='NOT_REVIEWED',formal_train_ready=False,
        code_sha256={p:digest(ROOT/p) for p in ('scripts/p106b_refill_eval_panel.py','scripts/diag_p106b_refill_multiaxis.py',
                                             'tinylm/infer/generate.py','tinylm/chat/serialize.py')})


def require_checkpoint_metadata(state, education):
    if state.get('sft')!=education or state.get('step')!=2289+education['optimizer_updates']:
        raise ValueError('checkpoint metadata differs from full education log; wire child refused')


def load(path,tokenizer,torch,education=None):
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer
    from tinylm.infer.generate import _strip
    from scripts.train_sft_p090 import validate_parent_lineage
    state=torch.load(path,map_location='cpu',weights_only=True)
    if education is not None:require_checkpoint_metadata(state,education)
    validate_parent_lineage(state,TOK_SHA,'chat32',tokenizer)
    cfg=TMTConfig(**state['cfg'])
    if cfg.n_layers!=14 or cfg.tie_mlp or cfg.vocab_size!=32768:
        raise ValueError('samechat32 dense14 geometry required')
    base=TiedMLPTransformer(cfg).cuda();base.load_state_dict(_strip(state['model']),strict=True)
    del state;base.set_anneal(1.0);base.eval();base.freeze_quant()
    return base,cfg


def execute(info):
    from tokenizers import Tokenizer
    from tinylm.infer.generate import sample
    import torch
    idle_before_gpu();OUTPUT.mkdir(exist_ok=False)
    report=dict(schema='P106B_REFILL_MULTIAXIS_V1',input=info,planned_model_calls=72,
        actual_model_calls=0,models={},student_training='NOT_RUN',checkpoint_saved=False,
        semantic_quality='NOT_REVIEWED',scope='posthoc answer collection and explicit contracts only')
    started=time.perf_counter();base=None;writer=None
    try:
        with wall_limit(1800):
            tok=Tokenizer.from_file(str(TOKENIZER));torch.set_num_threads(1)
            geometry=None
            for label,path in (('parent',ROOT/info['parent']),('student',CHILD)):
                base,cfg=load(path,tok,torch,read_json(CHILD_LOG) if label=='student' else None)
                current={k:v for k,v in cfg.__dict__.items() if k not in ('grad_checkpoint',)}
                if geometry is not None and current!=geometry:raise ValueError('parent/child architecture differs')
                geometry=current
                writer=ShardWriter(OUTPUT,'answers_'+label)
                def persist(row):
                    from scripts.p106b_pipeline import flush_row
                    writer.append(dict(model=label,**row));flush_row(writer)
                def infer(prompt,value):
                    count=len(tok.encode(prompt).ids)
                    if count>800:raise ValueError('input budget exceeded; preserve partial instead of silent truncation')
                    seed=20261005+int(panel_sha({'id':value['id']})[:6],16)
                    torch.manual_seed(seed);begin=time.perf_counter();report['actual_model_calls']+=1
                    full,meta=sample(base,cfg,tok,prompt,max_new=160,temperature=0,top_k=1,
                        device='cuda',logits_last_only=True,return_metadata=True,
                        stop_token_sequences=[tok.encode('<|im_end|>').ids])
                    prefix=tok.decode(tok.encode(prompt).ids)
                    if not full.startswith(prefix):
                        persist(dict(case=value,prompt=prompt,raw_full_text=full,extraction_status='PREFIX_MISMATCH',
                                     model_call_attempted=True,generation=meta,human_review='NOT_RUN'))
                        raise ValueError('generation prefix mismatch, not a model answer failure')
                    answer=full[len(prefix):]
                    meta=dict(meta,seed=seed,input_tokens=count,wall_sec=time.perf_counter()-begin,raw_full_text=full)
                    print('[MULTIAXIS_ANSWER] '+json.dumps(dict(model=label,id=value['id'],
                        question=value['question'],answer=answer,finish_reason=meta.get('finish_reason')),ensure_ascii=False),flush=True)
                    return answer,meta
                # collect has no retry and includes actual previous assistant replies.
                rows=collect(infer,on_row=persist)
                manifest=writer.close(lineage=info);verify(OUTPUT,manifest);writer=None
                report['models'][label]=dict(summary=summarize(rows),raw_concat_sha256=manifest['concat_sha256'],
                    rows=len(rows),peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20,
                    memory_scope='process cumulative; not a paired per-model memory comparison')
                base.clear_quant();del base;base=None;gc.collect();torch.cuda.empty_cache()
            report.update(status='ANSWER_COLLECTION_COMPLETE',returncode=0)
    except BaseException as exc:
        status,rc=disposition(exc);report.update(status=status,returncode=rc,error_type=type(exc).__name__,error=str(exc)[:1600])
    finally:
        if writer is not None and writer._total_rows:
            partial=writer.close(lineage=info);verify(OUTPUT,partial);report['partial_raw_manifest']=partial
        report['whole_wall_sec']=time.perf_counter()-started
        with (OUTPUT/'report.json').open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
        print('[MULTIAXIS_FINAL] '+json.dumps(dict(status=report['status'],returncode=report['returncode'],
            actual_model_calls=report['actual_model_calls'],semantic_quality='NOT_REVIEWED',
            evidence='HF/sft_ready/p106b_refill_multiaxis_v1/report.json'),ensure_ascii=False),flush=True)
    return report['returncode']


def main():
    p=argparse.ArgumentParser(description=__doc__);a=p.add_mutually_exclusive_group(required=True)
    a.add_argument('--execute',action='store_true');a.add_argument('--check-only',action='store_true')
    args=p.parse_args()
    try:
        info=check()
        if args.check_only:print('[CHECK_ONLY] '+json.dumps(info,ensure_ascii=False));return 0
        return execute(info)
    except (FileNotFoundError,FileExistsError) as exc:
        print('[HOLD] '+str(exc),file=sys.stderr);return 8
    except Exception as exc:
        print('[ERROR] '+type(exc).__name__+': '+str(exc),file=sys.stderr);return 9


if __name__=='__main__':raise SystemExit(main())
