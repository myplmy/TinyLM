#!/usr/bin/env python3
"""Common repaired/raw sources crossed with role bridge/repeat-control replay."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter,defaultdict
import copy
import json
from scripts import diag_p106b_source_repair3 as producer
from scripts import p106b_role_bridge as bridge
from scripts import diag_p106b_original_qa3_runtime_v2 as old
from scripts.p106b_native_windows import reader,NATIVE_TRAIN
from scripts.p106b_shards import ShardWriter,verify
from scripts.p106b_gate_runtime import GateNegative
training=old.training
prior=old.prior
factory=old.factory
conversation_signature=old.conversation_signature
development_labels=old.development_labels
TAG='p106b_repair_role_v1_s1337'
CORPUS=ROOT/'HF/sft_ready'/TAG/'corpus'
EVIDENCE=ROOT/'test_result/evidence'/TAG
PARENT=ROOT/'runs/ckpt/m100s10_ko-en_originalqa3_dense_chat32_p106b_original_qa3_v2_s1337_three.pt'
PARENT_SHA='567D379E3F8F1B8BBE1F65303DE9AAF1D1F3A33AFE5F9EA51CD12EE06069F9AF'
ARMS=('raw_repeat','repair_repeat','raw_role','repair_role')
CODE=(*producer.CODE,*old.CODE,'scripts/p106b_role_bridge.py','scripts/test_p106b_role_bridge.py',
      'scripts/diag_p106b_repair_role_course.py','scripts/test_p106b_repair_role_course.py')


def info():
    return dict(schema='P106B_REPAIR_ROLE_COURSE_V1',tag=TAG,
        code_sha256={p:training.data.digest(ROOT/p) for p in sorted(set(CODE))},
        teacher_source_tag=producer.TAG,arms=list(ARMS),parent=str(PARENT.relative_to(ROOT)),parent_sha256=PARENT_SHA,
        tokenizer_sha256=training.data.TOK_SHA,public_roots=512,code_replay_rows=4096,fiction_replay_rows=256,extra_rows=2048,
        rows_per_epoch=6912,epochs=4,updates=216,micro_bs=8,accum=16,seq=1024,grad_checkpoint=True,compile='default',
        lr=5e-5,muon_lr=2e-4,word_weight=1.,native_weight=1.,binary_weight=1.,fact_weight=0.,student_mtp=False,
        semantic_truth='teacher/public pseudo labels unverified; role/control only given code facts',formal_train_ready=False,
        comparison='PARTIAL_CONFOUNDED practical recipes; token/target amounts and text/knowledge types differ',
        checkpoint_policy='fixed final4epoch only, no intermediate weight files; log all epoch losses',
        deadline_utc=producer.original.prior.producer.legacy.source.DEADLINE.isoformat())


def selected_teacher():
    r,jobs,processed,counts,reports=producer.state()
    if any(counts[l]!=producer.GOAL for l in ('ko','en')):raise GateNegative('actual common repaired512 not complete')
    windows=sorted(producer.EVIDENCE.glob('window_*.json'))
    if not windows:raise GateNegative('teacher final operational evidence missing')
    final=producer.required(windows[-1])
    if not final['source_quota_complete'] or final['error'] is not None:raise GateNegative('teacher operational error requires separate data adjudication')
    rows=[]
    for ref in reports:
        p=ROOT/ref['path'];b=producer.required(p);m=b['candidate_manifest']
        if m:
            verify(p.parent,m);rows.extend(training.data.stream_rows(p.parent,m))
    if len(rows)!=512 or len({r['root'] for r in rows})!=512:raise ValueError('unique paired512 candidates required')
    if Counter(r['language'] for r in rows)!=dict(ko=256,en=256):raise ValueError('paired source language quota')
    for row in rows:
        job=row['job']
        if producer.fields.render(job,job['raw_pairs'],_tokenizer(),repaired=False)!=row['raw_student']:
            raise ValueError('raw source reconstruction mismatch')
        a,b=row['repaired_student']['meta']['student_reference_range']
        if producer.fields.text(row['repaired_student']['messages'][0])[a:b]!=job['reference']:
            raise ValueError('repaired student source changed')
    return r,rows,reports,windows[-1]


_TOK=None
def _tokenizer():
    from tokenizers import Tokenizer
    global _TOK
    if _TOK is None:
        if training.data.digest(training.data.TOKENIZER)!=training.data.TOK_SHA:raise ValueError('student tokenizer changed')
        _TOK=Tokenizer.from_file(str(training.data.TOKENIZER))
    return _TOK


def counts(rows,tok):
    total=Counter();languages=defaultdict(Counter)
    for row in rows:
        rec,_=factory.encode(row,tok)
        if rec.x_tokens>1024 or not rec.targets:raise ValueError('complete1024/no empty targets')
        total.update(rows=1,x_tokens=rec.x_tokens,assistant_targets=rec.targets)
        languages[row['meta']['language']].update(rows=1,x_tokens=rec.x_tokens,assistant_targets=rec.targets)
    return dict(total,languages={k:dict(v) for k,v in languages.items()})


def write_rows(name,rows):
    writer=ShardWriter(CORPUS,name)
    for row in rows:writer.append(row)
    manifest=writer.close(lineage=info());verify(CORPUS,manifest);return manifest


def bridge_views(graphs,epoch,tok):
    ranks=Counter();result=[]
    for g in graphs:
        rank=ranks[g['family']];ranks[g['family']]+=1
        view=(rank+epoch)%4
        result.extend(bridge.make(g,language,view,0,tok) for language in ('ko','en'))
    return result


def native_contract(contract):
    import numpy as np
    keys=('native_access','native_train_file','native_train_offsets','native_train_sha256','native_val_sha256')
    if any(k not in contract for k in keys) or contract['native_access']!='INDEXED_TRAIN_ONLY':
        raise ValueError('explicit indexed native contract required before legacy reader')
    offsets=contract['native_train_offsets'];windows=reader(ROOT,contract)
    if len(offsets)!=1728 or len(set(offsets))!=1728 or len(windows)!=1728 or windows.tokens.flags.writeable:
        raise ValueError('actual read-only1728 native consumer')
    for i in [*range(8),*range(1720,1728)]:
        if len(windows[i])!=1025 or not np.array_equal(windows[i],windows.tokens[offsets[i]:offsets[i]+1025]):
            raise ValueError('actual native reader source slice')
    return dict(read_only=True,windows=1728,slices_checked=16)


def make_course():
    import numpy as np
    tok=_tokenizer();source,paired,source_reports,source_final=selected_teacher()
    original,oldrows,labels=old.frozen.read_course()
    code=[copy.deepcopy(r) for r in oldrows['three_train0'] if r['meta']['kind'] not in ('public_qa','fictional_relation_fields')]
    if len(code)!=4096:raise ValueError('same original4096 code replay')
    approved=old.prior.data.binding.approved_questions('train')
    trusted=old.prior.data.known_contract(code,tok,approved)
    if trusted!=labels or len(trusted)!=3072:raise ValueError('actual original3072 binary labels')
    control=[]
    for language in ('ko','en'):
        for kind in ('binding_color','binding_department'):
            lane=[r for r in code if r['meta']['language']==language and r['meta']['kind']==kind]
            selected=sorted(lane,key=lambda r:producer.fields.sha([TAG,'CONTROL',r['messages']]))[:512]
            if len(selected)!=512:raise ValueError('balanced proven control source short')
            control.extend(bridge.repeat_control(r,tok,approved) for r in selected)
    graphs=bridge.graphs(1024,'train');rows={};summaries={};expected={}
    public={key:[copy.deepcopy(r['repaired_student' if key=='repair' else 'raw_student']) for r in paired] for key in ('raw','repair')}
    views=[bridge_views(graphs,e,tok) for e in range(4)]
    for arm in ARMS:
        variant,extra=arm.split('_');totals=Counter()
        for epoch in range(4):
            fiction=[old.factory.make(old.factory.graph(i),language,(i+epoch)%4) for i in range(128) for language in ('ko','en')]
            key=arm+'_train'+str(epoch)
            rows[key]=copy.deepcopy(public[variant])+copy.deepcopy(code)+fiction+copy.deepcopy(views[epoch] if extra=='role' else control)
            summaries[key]=counts(rows[key],tok)
            if summaries[key]['rows']!=6912:raise ValueError('same6912 rows per epoch required')
            binary_count=sum(old.conversation_signature(r['messages']) in labels for r in rows[key])
            if binary_count!=3072:raise ValueError('actual trainer binary lookup must remain3072 per epoch')
            totals.update({k:summaries[key][k] for k in ('x_tokens','assistant_targets')})
        expected[arm]=dict(totals,updates=216,native_x_tokens=216*8192,binary_rows=12288,
            binary_position_events=original['expected_exposures']['three']['binary_position_events'])
    rows['dev_natural_three']=copy.deepcopy(oldrows['dev_natural_three']);rows['dev_code']=copy.deepcopy(oldrows['dev_code']);rows['dev_fiction']=copy.deepcopy(oldrows['dev_fiction'])
    rows['dev_role']=bridge_views(bridge.graphs(64,'dev'),0,tok)
    source_inputs=producer.required(producer.OUTPUT/'inputs.json')
    rows['test_source']=list(training.data.stream_rows(producer.OUTPUT,source_inputs['manifests']['fresh_public_test']))
    rows['development_source64']=copy.deepcopy(oldrows['test_natural_three']);rows['retention_fiction']=copy.deepcopy(oldrows['retention_fiction'])
    for style in (0,2):
        rows['test_role_style'+str(style)]=[];ranks=Counter()
        for g in bridge.graphs(128,'test'):
            rank=ranks[g['family']];ranks[g['family']]+=1;view=rank%4
            rows['test_role_style'+str(style)].extend(bridge.make(g,language,view,style,tok) for language in ('ko','en'))
    train_refs={r['job']['root'] for r in paired};test_refs={r['meta']['semantic_root_id'] for r in rows['test_source']}
    if len(test_refs)!=64 or train_refs&test_refs:raise ValueError('new public exact reference train/test overlap')
    native_sources=[old.CORPUS/'report.json',old.base.CORPUS/'report.json',old.prior.CORPUS/'report.json',
        old.prior.producer.data.source.CORPUS/'report.json',ROOT/'HF/sft_ready/p106b_context_replay_v2_s1337/corpus/report.json']
    excluded=set();native_refs=[]
    for path in native_sources:
        r=producer.required(path);excluded.update(r['native_train_offsets']);native_refs.append(dict(path=str(path.relative_to(ROOT)),sha256=training.data.digest(path)))
    tokens=np.memmap(ROOT/NATIVE_TRAIN,dtype=np.uint16,mode='r')
    offsets=[i for i in old.prior.data.binding.prior.source.native_offsets(len(tokens),1728+len(excluded)+1024) if i not in excluded][:1728]
    native=dict(native_access='INDEXED_TRAIN_ONLY',native_train_file=NATIVE_TRAIN,native_train_offsets=offsets,
        native_train_sha256=original['native_train_sha256'],native_val_sha256=original['native_val_sha256'])
    native_observation=native_contract(native)
    dev=old.development_labels(rows['dev_code'],tok)
    if len(dev)!=512:raise ValueError('original dev640 producer512 label contract')
    return rows,labels,dict(counts=summaries,expected_exposures=expected,native_exclusion_reports=native_refs,
        teacher_source_reports=source_reports,teacher_final_report=str(source_final.relative_to(ROOT)),
        teacher_final_sha256=training.data.digest(source_final),teacher_inputs_sha256=training.data.digest(producer.OUTPUT/'inputs.json'),
        actual_cpu_consumers=dict(train_binary=3072,dev_binary=512,native_windows=1728,native_slices_checked=16,
            code4096=counts(code,tok),dev_role=counts(rows['dev_role'],tok),new_public_test64=len(test_refs),native=native_observation),**native)


def freeze():
    if CORPUS.parent.exists() or EVIDENCE.exists():raise GateNegative('old repair-role course preserved')
    if training.data.digest(PARENT)!=PARENT_SHA:raise ValueError('prelocked student initializer changed')
    rows,labels,details=make_course();CORPUS.mkdir(parents=True,exist_ok=False)
    manifests={k:write_rows(k,v) for k,v in rows.items()}
    label_manifest=write_rows('binary_labels',[dict(signature=k,**v) for k,v in labels.items()])
    result=dict(info(),status='REPAIR_ROLE_COURSE_FROZEN',manifests=manifests,binary_labels_manifest=label_manifest,**details)
    training.write(CORPUS/'report.json',result);training.write(EVIDENCE/'corpus_report.json',result)
    print('[REPAIR_ROLE_COURSE] '+json.dumps(dict(expected=result['expected_exposures'],consumers=result['actual_cpu_consumers'])),flush=True);return 0


def read_course():
    report=producer.required(CORPUS/'report.json')
    if report['status']!='REPAIR_ROLE_COURSE_FROZEN' or report['code_sha256']!=info()['code_sha256']:raise ValueError('frozen repair-role course CODE changed')
    if training.data.digest(training.data.TOKENIZER)!=training.data.TOK_SHA:raise ValueError('physical student tokenizer changed')
    for path,identity in ((PARENT,PARENT_SHA),(ROOT/NATIVE_TRAIN,report['native_train_sha256']),(old.prior.NATIVE/'val.bin',report['native_val_sha256'])):
        if training.data.digest(path)!=identity:raise ValueError('initializer/native cache changed')
    native_contract(report)
    rows={k:list(training.data.stream_rows(CORPUS,m)) for k,m in report['manifests'].items()}
    labels={r['signature']:{k:v for k,v in r.items() if k!='signature'} for r in training.data.stream_rows(CORPUS,report['binary_labels_manifest'])}
    if len(labels)!=3072:raise ValueError('original binary labels missing')
    return report,rows,labels


def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true');a=p.parse_args()
    if a.check_only:print('[REPAIR_ROLE_COURSE_CHECK] '+json.dumps(info()));return 0
    try:
        producer.original.prior.producer.legacy.source.deadline();return freeze()
    except GateNegative as exc:print('[REPAIR_ROLE_COURSE_HOLD] '+str(exc));return 8
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[REPAIR_ROLE_COURSE_ERROR] '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
