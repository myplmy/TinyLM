#!/usr/bin/env python3
"""Exact producer replay for the preserved QA3 course; all consumers before CUDA."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter
import json
from scripts import diag_p106b_original_qa3_course as frozen
from scripts.p106b_gate_runtime import GateNegative

TAG='p106b_original_qa3_v2_s1337'
EVIDENCE=ROOT/'test_result/evidence'/TAG
CORPUS=frozen.CORPUS
CODE=(*frozen.CODE,'scripts/diag_p106b_original_qa3_runtime_v2.py',
      'scripts/test_p106b_original_qa3_runtime_v2.py',
      'scripts/diag_p106b_original_qa3_train_v2.py','scripts/test_p106b_original_qa3_train_v2.py')


def __getattr__(name):return getattr(frozen,name)


def conversation_signature(messages):return frozen.prior.data.binding.prior.source.sha(messages)


def info():
    r=frozen.info()
    r.update(schema='P106B_ORIGINAL_QA3_RUNTIME_V2',tag=TAG,dataset_tag=frozen.TAG,
        code_sha256={p:frozen.training.data.digest(ROOT/p) for p in sorted(set(CODE))},
        development_origin='exact binding.fresh_test(retention_course.code_rows()); prior TEST reused as development only',
        consumer_contract='reproduce all640 messages; verify512 binding metadata/causal positions; never widen approved train/dev labels')
    return r


def development_labels(rows,tok):
    binding=frozen.prior.data.binding
    producer=binding.fresh_test(binding.prior.source.code_rows())
    sha=conversation_signature
    if len(rows)!=640 or [sha(r['messages']) for r in rows]!=[sha(r['messages']) for r in producer]:
        raise ValueError('exact original640 producer conversations required')
    approved={sha(r['messages']):r['meta'] for r in producer}
    result=frozen.prior.data.known_contract(rows,tok,approved)
    if len(result)!=512:raise ValueError('exact512 development binding contracts required')
    return result


def validate_consumers(r,rows,labels):
    from tokenizers import Tokenizer
    import torch
    if torch.cuda.is_initialized():raise ValueError('CPU consumer proof must precede CUDA initialization')
    tok=Tokenizer.from_file(str(frozen.training.data.TOKENIZER))
    code=[x for x in rows['first_train0'] if x['meta']['kind'] not in ('public_qa','fictional_relation_fields')]
    trusted=frozen.prior.data.known_contract(code,tok,frozen.prior.data.binding.approved_questions('train'))
    if len(code)!=4096 or len(trusted)!=3072 or trusted!=labels:raise ValueError('unchanged train3072 binary labels required')
    per_epoch={}
    for arm in frozen.ARMS:
        per_epoch[arm]=[sum(conversation_signature(row['messages']) in labels for row in rows[arm+'_train'+str(epoch)]) for epoch in range(4)]
        if per_epoch[arm]!=[3072]*4:raise ValueError('actual trainer lookup must preserve3072 binding rows in every epoch')
    dev=development_labels(rows['dev_code'],tok)
    if set(dev)&set(labels):raise ValueError('development/train label conversation overlap')
    counts={}
    for key in ('dev_natural_three','dev_code','dev_fiction'):
        totals=Counter()
        for row in rows[key]:
            rec,_=frozen.factory.encode(row,tok)
            if not 0<rec.targets or rec.x_tokens>1024:raise ValueError('actual development encoding has empty/oversized targets')
            totals.update(rows=1,x_tokens=rec.x_tokens,assistant_targets=rec.targets)
        if not totals['rows'] or not totals['assistant_targets']:raise ValueError('empty development lane')
        counts[key]=dict(totals)
    return dict(train_label_count=len(labels),train_lookup_per_epoch=per_epoch,development_label_count=len(dev),development_counts=counts,
        original_producer_messages=640,native=frozen.check_native(r),cuda_initialized=False,
        original_course_sha256=frozen.training.data.digest(CORPUS/'report.json'),
        model_forward=False,optimizer_updates=0,checkpoints_written=0),dev


def read_course():
    r,rows,labels=frozen.read_course()
    proof=frozen.prior.producer.legacy.source.required(EVIDENCE/'cpu_consumer_report.json')
    if proof['code_sha256']!=info()['code_sha256'] or proof['status']!='ACTUAL_CPU_CONSUMERS_VERIFIED':
        raise ValueError('same-code actual CPU consumer proof required before CUDA')
    observed,dev=validate_consumers(r,rows,labels)
    if observed!=proof['observation']:raise ValueError('actual preserved consumers differ from CPU proof')
    return r,rows,labels


def main():
    p=argparse.ArgumentParser(description=__doc__)
    g=p.add_mutually_exclusive_group(required=True);g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true');a=p.parse_args()
    if a.check_only:print('[ORIGINAL_QA3_RUNTIME_V2_CHECK] '+json.dumps(info()));return 0
    target=EVIDENCE/'cpu_consumer_report.json'
    try:
        frozen.prior.producer.legacy.source.deadline()
        if target.exists():raise GateNegative('old CPU proof preserved')
        r,rows,labels=frozen.read_course();observation,_=validate_consumers(r,rows,labels)
        frozen.training.write(target,dict(info(),status='ACTUAL_CPU_CONSUMERS_VERIFIED',observation=observation))
        print('[ORIGINAL_QA3_ACTUAL_CPU_CONSUMERS] '+json.dumps(observation),flush=True);return 0
    except GateNegative as exc:print('[ORIGINAL_QA3_RUNTIME_V2_HOLD] '+str(exc));return 8
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[ORIGINAL_QA3_RUNTIME_V2_ERROR] '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
