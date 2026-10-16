#!/usr/bin/env python3
"""Frozen first-turn preference/replay, same E970 parent, fresh visible-fact test."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter,defaultdict
import copy
import json
from scripts import diag_p106b_evidence_recovery_train as upstream_runtime
from scripts import p106b_evidence_preference as method
from scripts.p106b_shards import ShardWriter,verify
from scripts.p106b_gate_runtime import GateNegative
upstream=upstream_runtime.course
training=upstream.training
producer=upstream.producer
prior=upstream.prior
TAG='p106b_evidence_preference_v1_s1337'
CORPUS=ROOT/'HF/sft_ready'/TAG/'corpus'
EVIDENCE=ROOT/'test_result/evidence'/TAG
PARENT=upstream_runtime.checkpoint('evidence_recovery')
PARENT_SHA='E9707AA2ABB55054DA226A6303A0EEAD8BA0B653029E24AFAD2A63D86E729E42'
PARENT_REPORT=upstream.EVIDENCE/'evaluate/evidence_recovery_report.json'
ARMS=method.ARMS
CODE=(*upstream_runtime.CODE,'scripts/p106b_evidence_preference.py','scripts/test_p106b_evidence_preference.py',
    'scripts/diag_p106b_evidence_preference_course.py','scripts/test_p106b_evidence_preference_course.py')


def info():
    return dict(schema='P106B_EVIDENCE_PREFERENCE_COURSE_V1',tag=TAG,arms=ARMS,
        code_sha256={p:training.data.digest(ROOT/p) for p in sorted(set(CODE))},
        parent=str(PARENT.relative_to(ROOT)),parent_sha256=PARENT_SHA,tokenizer_sha256=training.data.TOK_SHA,
        rows=8192,passes=1,updates=64,micro_bs=8,accum=16,seq=1024,grad_checkpoint=True,compile='default',
        lr=5e-5,muon_lr=2e-4,word_weight=1.,native_weight=1.,binary_weight=1.,fact_weight=0.,
        pairs_per_update=16,contrast_pairs=1024,teacher_calls=0,student_mtp=False,
        scope='same known sufficiency firstturn positives/replay/native; beta0 versus0.1 only; no general-world epistemic classifier',
        additional_exposure='one extra diagnostic pass, parent already saw graphs/native windows; not main75M/300M',
        checkpoint_policy='fixed final64 only, no test selection/intermediate/optimizer state',
        deadline_utc=upstream.producer.original.prior.producer.legacy.source.DEADLINE.isoformat())


def choose_replay(values,labels):
    public=[r for r in values if r['meta']['kind']=='public_qa']
    fiction=[r for r in values if r['meta']['kind']=='fictional_relation_fields']
    binary=[r for r in values if upstream.conversation_signature(r['messages']) in labels]
    other=[r for r in values if r['meta']['kind'] not in ('public_qa','fictional_relation_fields','evidence_recovery')
        and upstream.conversation_signature(r['messages']) not in labels]
    groups=defaultdict(list)
    for r in other:groups[(r['meta']['language'],r['meta']['kind'])].append(r)
    if len(public)!=512 or len(fiction)!=256 or len(binary)!=3072 or len(groups)!=8:
        raise ValueError('same public512/fiction256/binary3072/eight other-code buckets required')
    extra=[]
    for key,lane in sorted(groups.items()):
        ranked=sorted(lane,key=lambda r:method.previous.wrap.sha([TAG,'REPLAY',r['messages']]))
        if len(ranked)<32:raise ValueError('balanced code32/bucket short')
        extra.extend(ranked[:32])
    result=copy.deepcopy(public+fiction+binary+extra)
    if len(result)!=4096:raise ValueError('exact replay4096 required')
    return result


def _write(name,values):
    w=ShardWriter(CORPUS,name)
    for v in values:w.append(v)
    m=w.close(lineage=info());verify(CORPUS,m);return m


def freeze():
    from tinylm.train.mtp_sft import encode_record
    if CORPUS.parent.exists() or CORPUS.parent.is_symlink() or EVIDENCE.exists() or EVIDENCE.is_symlink():raise GateNegative('fresh preference namespace required')
    original,oldrows,labels=upstream.read_course();tok=upstream.old._tokenizer()
    if training.data.digest(PARENT)!=PARENT_SHA:raise ValueError('exact E970 parent changed')
    graphs={r['meta']['neutral_root']:r['meta']['producer_graph'] for r in oldrows['evidence_recovery_train0'] if r['meta']['kind']=='evidence_recovery'}
    selected=method.select_graphs(list(graphs.values()),512,TAG);pairs=[]
    for rank,g in enumerate(selected):
        for lang in ('ko','en'):
            for condition in range(4):
                p=method.make_pair(g,lang,condition,rank%2,tok)
                p['source_signature']=upstream.conversation_signature(p['chosen']['messages']);pairs.append(p)
    indexed=method.index_pairs(pairs)
    if len(pairs)!=4096 or len(indexed)!=4096:raise ValueError('complete4096 producer pair identities required')
    values=[p['chosen'] for p in pairs]+choose_replay(oldrows['complete_replay_train0'],labels)
    records=[encode_record(r,tok) for r in values]
    known={id(rec):r['meta']['semantic_root_id'] if r['meta']['kind']=='evidence_preference' else None for rec,r in zip(records,values)}
    legal=set(indexed);pair_counts=[]
    for batch in training.batches(records,0):
        n=sum(known[id(r)] in legal for micro in batch for r in micro);pair_counts.append(n)
    if len(pair_counts)!=64 or min(pair_counts)<16:raise ValueError('actual64 batches with16 available pairs required')
    train_graphs,dev_graphs,old_test=upstream.source_groups();newtest=method.fresh_test(old_test,TAG)
    test=[method.previous.make(g,l,c,True,3,tok) for g in newtest for l in ('ko','en') for c in range(4)]
    if len(test)!=1024 or {r['meta']['neutral_root'] for r in test}&set(graphs):raise ValueError('fresh test1024 source separation required')
    rows=dict(train=values,test_evidence=test)
    for key in ('dev_natural_three','dev_code','dev_fiction','dev_role','dev_evidence','test_source','development_source64','retention_fiction','test_role_style0','test_role_style2'):
        rows[key]=copy.deepcopy(oldrows[key])
    counts=upstream.old.counts(values,tok)
    CORPUS.mkdir(parents=True,exist_ok=False);manifests={k:_write(k,v) for k,v in rows.items()}
    pm=_write('pairs',pairs);lm=_write('binary_labels',[dict(signature=k,**v) for k,v in sorted(labels.items())])
    native={k:copy.deepcopy(original[k]) for k in ('native_access','native_train_file','native_train_offsets','native_train_sha256','native_val_sha256')}
    observation=upstream.native_contract(native)
    expected=dict(x_tokens=counts['x_tokens'],assistant_targets=counts['assistant_targets'],native_x_tokens=64*8192,
        binary_rows=3072,contrast_pairs=64*16,updates=64)
    report=dict(info(),status='EVIDENCE_PREFERENCE_COURSE_FROZEN',manifests=manifests,pairs_manifest=pm,binary_labels_manifest=lm,
        counts=counts,expected_exposures=expected,pairs_per_batch=pair_counts,pair_modes=dict(Counter(p['mode'] for p in pairs)),
        pair_index='FULL_PRODUCER_PAIR_ID',distinct_chosen_conversations=len({p['source_signature'] for p in pairs}),
        positive_alias_exposures=len(pairs)-len({p['source_signature'] for p in pairs}),
        source_course_sha256=training.data.digest(upstream.CORPUS/'report.json'),parent_endpoint_report=str(PARENT_REPORT.relative_to(ROOT)),
        parent_endpoint_report_sha256=training.data.digest(PARENT_REPORT),native=observation,**native)
    training.write(CORPUS/'report.json',report);training.write(EVIDENCE/'corpus_report.json',report)
    print('[EVIDENCE_PREFERENCE_COURSE] '+json.dumps(dict(rows=8192,pairs=4096,test=1024,counts=counts,pairs_per_batch_min=min(pair_counts))),flush=True);return 0


def read_course():
    r=upstream.producer.required(CORPUS/'report.json')
    if r['status']!='EVIDENCE_PREFERENCE_COURSE_FROZEN' or r['code_sha256']!=info()['code_sha256']:raise ValueError('frozen preference CODE changed')
    if training.data.digest(PARENT)!=PARENT_SHA or training.data.digest(training.data.TOKENIZER)!=training.data.TOK_SHA:raise ValueError('fixed parent/tokenizer changed')
    upstream.native_contract(r)
    rows={k:list(training.data.stream_rows(CORPUS,m)) for k,m in r['manifests'].items()}
    pairs=list(training.data.stream_rows(CORPUS,r['pairs_manifest']))
    labels={x['signature']:{k:v for k,v in x.items() if k!='signature'} for x in training.data.stream_rows(CORPUS,r['binary_labels_manifest'])}
    return r,rows,labels,pairs


def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true');a=p.parse_args()
    if a.check_only:print(json.dumps(info()));return 0
    try:upstream.producer.original.prior.producer.legacy.source.deadline();return freeze()
    except GateNegative as exc:print('[EVIDENCE_PREFERENCE_COURSE_HOLD] '+str(exc));return 8
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[EVIDENCE_PREFERENCE_COURSE_ERROR] '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
