#!/usr/bin/env python3
"""Immutable matched replay versus query-specific evidence-recovery course."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter
import copy
import json
from scripts import diag_p106b_repair_role_course as old
from scripts import diag_p106b_repair_role_train as parent_runtime
from scripts import p106b_evidence_recovery as method
from scripts.p106b_native_windows import reader,NATIVE_TRAIN
from scripts.p106b_shards import ShardWriter,verify
from scripts.p106b_gate_runtime import GateNegative
training=old.training
prior=old.prior
factory=old.factory
producer=old.producer
conversation_signature=old.conversation_signature
development_labels=old.development_labels
TAG='p106b_evidence_recovery_v1_s1337'
CORPUS=ROOT/'HF/sft_ready'/TAG/'corpus'
EVIDENCE=ROOT/'test_result/evidence'/TAG
PARENT=parent_runtime.checkpoint('raw_role')
PARENT_SHA='7E584E9F0B99CCFC73D12ED9B36376F214990F5860C85F4A413C096B9438B838'
PARENT_REPORT=old.EVIDENCE/'evaluate/raw_role_report.json'
ARMS=('complete_replay','evidence_recovery')
CODE=(*parent_runtime.CODE,'scripts/p106b_evidence_recovery.py','scripts/test_p106b_evidence_recovery.py',
    'scripts/diag_p106b_evidence_recovery_course.py','scripts/test_p106b_evidence_recovery_course.py')


def info():
    return dict(schema='P106B_EVIDENCE_RECOVERY_COURSE_V1',tag=TAG,
        code_sha256={p:training.data.digest(ROOT/p) for p in sorted(set(CODE))},
        arms=list(ARMS),parent=str(PARENT.relative_to(ROOT)),parent_sha256=PARENT_SHA,
        tokenizer_sha256=training.data.TOK_SHA,rows_per_epoch=6912,epochs=4,updates=216,
        micro_bs=8,accum=16,seq=1024,grad_checkpoint=True,compile='default',lr=5e-5,muon_lr=2e-4,
        word_weight=1.,native_weight=1.,binary_weight=1.,fact_weight=0.,student_mtp=False,
        teacher_calls=0,semantic_truth='given code-authored fictional fields and explicit updates only',
        source_eval_scope='old64 is posthoc DEV; some source task directions invalid for pure QA, not new test truth',
        formal_train_ready=False,comparison='PARTIAL_CONFOUNDED pragmatic curricula: evidence and first-answer target/amount differ',
        additional_exposure='four more passes from raw_role; not cumulative4 or novel world facts',
        checkpoint_policy='fixed final4 only; log all epoch losses',
        deadline_utc=producer.original.prior.producer.legacy.source.DEADLINE.isoformat())


def native_contract(r):return old.native_contract(r)


def source_groups():
    train=method.graphs(1024,'train');dev=method.graphs(64,'dev')
    excluded={method.neutral(g) for g in method.base.graphs(128,'test')}
    test=method.graphs(128,'test',exclude=excluded)
    sets=[{method.neutral(g) for g in values} for values in (train,dev,test)]
    if sets[0]&sets[1] or sets[0]&sets[2] or sets[1]&sets[2] or sets[2]&excluded:
        raise ValueError('neutral visible facts overlap train/dev/test or previous primary')
    return train,dev,test


def extras(graphs,epoch,partial,tok):
    ranks=Counter();rows=[]
    for g in graphs:
        rank=ranks[g['family']];ranks[g['family']]+=1;mode=(rank+epoch)%4
        rows.extend(method.make(g,language,mode,partial,epoch%2,tok) for language in ('ko','en'))
    if Counter(x['meta']['condition'] for x in rows)!={i:len(rows)//4 for i in range(4)}:
        raise ValueError('four counterfactual cells not balanced')
    if partial and Counter(x['meta']['first_response_intent'] for x in rows)!={'ANSWER':len(rows)//2,'ASK_FOR_MISSING_FACT':len(rows)//2}:
        raise ValueError('query-sufficient versus insufficient first answers not balanced')
    return rows


def write_rows(name,rows):
    writer=ShardWriter(CORPUS,name)
    for row in rows:writer.append(row)
    m=writer.close(lineage=info());verify(CORPUS,m);return m


def make_course():
    import numpy as np
    original,oldrows,labels=old.read_course();tok=old._tokenizer();train,dev,test=source_groups()
    source512=[copy.deepcopy(x) for x in oldrows['raw_role_train0'] if x['meta']['kind']=='public_qa']
    code=[copy.deepcopy(x) for x in oldrows['raw_role_train0'] if x['meta']['kind'] not in ('public_qa','fictional_relation_fields','role_bridge')]
    if len(source512)!=512 or len(code)!=4096 or len(labels)!=3072:raise ValueError('same raw512/code4096/original binary3072 required')
    rows={};counts={};expected={}
    for arm in ARMS:
        total=Counter()
        for epoch in range(4):
            fiction=[copy.deepcopy(x) for x in oldrows['raw_role_train'+str(epoch)] if x['meta']['kind']=='fictional_relation_fields']
            values=copy.deepcopy(source512)+copy.deepcopy(code)+fiction+extras(train,epoch,arm=='evidence_recovery',tok)
            key=arm+'_train'+str(epoch);rows[key]=values;counts[key]=old.counts(values,tok)
            if len(values)!=6912 or sum(conversation_signature(x['messages']) in labels for x in values)!=3072:
                raise ValueError('same6912/full54 batches/3072 binary consumers required')
            total.update({k:counts[key][k] for k in ('x_tokens','assistant_targets')})
        expected[arm]=dict(total,updates=216,native_x_tokens=216*8192,binary_rows=12288,binary_position_events=165748)
    for name in ('dev_natural_three','dev_code','dev_fiction','dev_role'):
        rows[name]=copy.deepcopy(oldrows[name])
    rows['dev_evidence']=[method.make(g,l,m,True,1,tok) for g in dev for l in ('ko','en') for m in range(4)]
    rows['test_evidence']=[method.make(g,l,m,True,2,tok) for g in test for l in ('ko','en') for m in range(4)]
    for name in ('test_source','development_source64','retention_fiction','test_role_style0','test_role_style2'):
        rows[name]=copy.deepcopy(oldrows[name])
    for name in ('dev_evidence','test_evidence'):
        summary=old.counts(rows[name],tok)
        if summary['rows'] not in (512,1024):raise ValueError('complete four-cell/language evaluation required')
    excluded=set(original['native_train_offsets']);refs=[dict(path=str((old.CORPUS/'report.json').relative_to(ROOT)),sha256=training.data.digest(old.CORPUS/'report.json'))]
    for item in original['native_exclusion_reports']:
        path=ROOT/item['path'];r=producer.required(path);excluded.update(r['native_train_offsets']);refs.append(dict(path=item['path'],sha256=training.data.digest(path)))
    tokens=np.memmap(ROOT/NATIVE_TRAIN,dtype=np.uint16,mode='r')
    offsets=[i for i in prior.data.binding.prior.source.native_offsets(len(tokens),1728+len(excluded)+1024) if i not in excluded][:1728]
    native=dict(native_access='INDEXED_TRAIN_ONLY',native_train_file=NATIVE_TRAIN,native_train_offsets=offsets,
        native_train_sha256=original['native_train_sha256'],native_val_sha256=original['native_val_sha256'])
    observation=native_contract(native)
    if len(development_labels(rows['dev_code'],tok))!=512:raise ValueError('same original DEV512/640 contract')
    parent=producer.required(PARENT_REPORT)
    if parent['checkpoint_sha256']!=PARENT_SHA:raise ValueError('old parent endpoint identity changed')
    details=dict(counts=counts,expected_exposures=expected,native_exclusion_reports=refs,
        parent_endpoint_report=str(PARENT_REPORT.relative_to(ROOT)),parent_endpoint_report_sha256=training.data.digest(PARENT_REPORT),
        initial_core_sha256=parent['core_before_after_sha256'],upstream_course_sha256=training.data.digest(old.CORPUS/'report.json'),
        actual_cpu_consumers=dict(train_binary=3072,dev_binary=512,native_windows=1728,native=observation),
        groups=dict(train=1024,dev=64,test=128,previous_primary_visible_facts_excluded=True),
        first_test_intents=dict(Counter(x['meta']['first_response_intent'] for x in rows['test_evidence'])),**native)
    return rows,labels,details


def freeze():
    if CORPUS.parent.exists() or EVIDENCE.exists():raise GateNegative('old evidence-recovery course preserved')
    if training.data.digest(PARENT)!=PARENT_SHA:raise ValueError('fixed7E parent changed')
    rows,labels,details=make_course();CORPUS.mkdir(parents=True,exist_ok=False)
    manifests={k:write_rows(k,v) for k,v in rows.items()};lm=write_rows('binary_labels',[dict(signature=k,**v) for k,v in labels.items()])
    result=dict(info(),status='EVIDENCE_RECOVERY_COURSE_FROZEN',manifests=manifests,binary_labels_manifest=lm,**details)
    training.write(CORPUS/'report.json',result);training.write(EVIDENCE/'corpus_report.json',result)
    print('[EVIDENCE_COURSE] '+json.dumps(dict(expected=result['expected_exposures'],groups=result['groups'],test_intents=result['first_test_intents'])),flush=True);return 0


def read_course():
    r=producer.required(CORPUS/'report.json')
    if r['status']!='EVIDENCE_RECOVERY_COURSE_FROZEN' or r['code_sha256']!=info()['code_sha256']:raise ValueError('frozen evidence course CODE changed')
    if training.data.digest(training.data.TOKENIZER)!=training.data.TOK_SHA:raise ValueError('physical tokenizer changed')
    for path,identity in ((PARENT,PARENT_SHA),(PARENT_REPORT,r['parent_endpoint_report_sha256']),
        (ROOT/NATIVE_TRAIN,r['native_train_sha256']),(prior.NATIVE/'val.bin',r['native_val_sha256'])):
        if training.data.digest(path)!=identity:raise ValueError('parent/endpoint/native changed')
    native_contract(r)
    rows={k:list(training.data.stream_rows(CORPUS,m)) for k,m in r['manifests'].items()}
    labels={x['signature']:{k:v for k,v in x.items() if k!='signature'} for x in training.data.stream_rows(CORPUS,r['binary_labels_manifest'])}
    if len(labels)!=3072:raise ValueError('original binary labels missing')
    return r,rows,labels


def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true');a=p.parse_args()
    if a.check_only:print('[EVIDENCE_COURSE_CHECK] '+json.dumps(info()));return 0
    try:producer.original.prior.producer.legacy.source.deadline();return freeze()
    except GateNegative as exc:print('[EVIDENCE_COURSE_HOLD] '+str(exc));return 8
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[EVIDENCE_COURSE_ERROR] '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
