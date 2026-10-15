#!/usr/bin/env python3
"""Original first-QA versus three-QA course; preserved source, new outputs only."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter,defaultdict
import copy
import json
from scripts import diag_p106b_relation_interleaved_train_v2 as parent_runtime
from scripts import p106b_public_qa_roles as roles
from scripts import p106b_relation_fields as factory
from scripts.p106b_native_windows import reader,NATIVE_TRAIN
from scripts.p106b_shards import ShardWriter,verify
from scripts.p106b_gate_runtime import GateNegative
training=parent_runtime.training
base=parent_runtime.course.base
prior=base.prior
TAG='p106b_original_qa3_v1_s1337'
CORPUS=ROOT/'HF/sft_ready'/TAG/'corpus'
EVIDENCE=ROOT/'test_result/evidence'/TAG
PARENT=ROOT/'runs/ckpt/m100s10_ko-en_relation_dense_chat32_p106b_relation_interleaved_v2_s1337_fact1.pt'
PARENT_SHA='687EBCC5E30EA674EF4742BFC2BA6B98BCAB937541BD5498F567A9084387E831'
ARMS=('first','three')
CODE=(*parent_runtime.CODE,'scripts/p106b_public_qa_roles.py','scripts/test_p106b_public_qa_roles.py',
    'scripts/diag_p106b_original_qa3_course.py','scripts/test_p106b_original_qa3_course.py')


def info():
    return dict(schema='P106B_ORIGINAL_QA3_COURSE_V1',tag=TAG,code_sha256={p:training.data.digest(ROOT/p) for p in sorted(set(CODE))},
        parent=str(PARENT.relative_to(ROOT)),parent_sha256=PARENT_SHA,tokenizer_sha256=training.data.TOK_SHA,
        arms=list(ARMS),epochs=4,updates=200,rows_per_epoch=6356,natural_roots=2004,code_replay_rows=4096,fiction_replay_rows=256,
        micro_bs=8,accum=16,seq=1024,grad_checkpoint=True,compile='default',lr=5e-5,muon_lr=2e-4,
        word_weight=1.,native_weight=1.,binary_weight=1.,fact_weight=0.,fact_head_in_inference=False,
        teacher_calls=0,world_truth='ORIGINAL_PUBLIC_UNVERIFIED; fictional replay has producer truth only',
        formal_train_ready=False,comparison='PARTIAL_CONFOUNDED information/targets/turns differ, not pure format',
        deadline_utc=prior.producer.legacy.source.DEADLINE.isoformat())


def source_root(language,reference):return factory.sha([language,reference])


def natural_views(row):
    triple,parsed=roles.wrap(row);root=source_root(row['meta']['language'],parsed['reference'])
    triple['meta'].update(kind='public_qa',subkind='original_three_qa',semantic_root_id=root,source_reference=parsed['reference'],rubric='PUBLIC_LITERAL_TARGET')
    first=copy.deepcopy(triple);first['messages']=first['messages'][:2]
    first['meta'].update(subkind='original_first_qa',supervised_original_qa_count=1)
    triple['meta']['supervised_original_qa_count']=3
    return first,triple


def original_population(tok):
    source=prior.producer.data.source;old,rows,_=source.read_course()
    wanted={key:{r['meta']['parent_concept_id'] for r in rows[key] if r['meta']['kind']=='natural_first_qa'} for key in ('train','dev')}
    if len(wanted['train'])!=2048 or wanted['train']&wanted['dev']:raise ValueError('exact old TRAIN roots, separate DEV')
    selected={key:{a:[] for a in ARMS} for key in wanted};seen={};rejected=Counter();accepted=[]
    if training.data.digest(training.data.PUBLIC/'report.json')!=training.data.PUBLIC_SHA:raise ValueError('original public source changed')
    from tinylm.train import mtp_sft as core
    for split in ('train','val'):
        manifest=json.loads((training.data.PUBLIC/(split+'_shards_manifest.json')).read_text())
        for row in training.data.stream_rows(training.data.PUBLIC,manifest):
            meta=row['meta'];identity=meta.get('parent_concept_id')
            if meta.get('selection_family')!='Flan-Coqa':continue
            target=next((k for k,v in wanted.items() if identity in v),None)
            if target is None:continue
            digest=factory.sha(row['messages'][:2])
            if identity in seen:
                if seen[identity]!=digest:raise ValueError('same parent ID/different original first pair')
                continue
            seen[identity]=digest
            try:
                first,triple=natural_views(row)
                if core.encode_record(triple,tok).x_tokens>1024:raise ValueError('three-turn sequence exceeds1024')
            except ValueError as exc:rejected[target+':'+str(exc)]+=1;continue
            selected[target]['first'].append(first);selected[target]['three'].append(triple)
            if target=='train':accepted.append(identity)
    old_inventory=json.loads((ROOT/'test_result/evidence/p106b_public_three_qa_inventory_v1_s1337/report.json').read_text())
    if len(accepted)!=2004 or factory.sha(sorted(accepted))!=old_inventory['accepted_ids_sha256']:raise ValueError('exact pre-inventoried2004 TRAIN cohort required')
    if Counter(r['meta']['language'] for r in selected['train']['three'])!=dict(ko=995,en=1009):raise ValueError('fixed TRAIN languages')
    for key in selected:
        if len(selected[key]['first'])!=len(selected[key]['three']):raise ValueError('paired roots')
        for a,b in zip(selected[key]['first'],selected[key]['three']):
            if a['messages']!=b['messages'][:2]:raise ValueError('identical first prefix and target required')
    return selected,dict(rejected),old_inventory['accepted_ids_sha256']


def counts(rows,tok):
    result=Counter();languages=defaultdict(Counter)
    for row in rows:
        rec,_=factory.encode(row,tok)
        result.update(rows=1,x_tokens=rec.x_tokens,assistant_targets=rec.targets)
        languages[row['meta']['language']].update(x_tokens=rec.x_tokens,assistant_targets=rec.targets)
    return dict(result,languages={k:dict(v) for k,v in languages.items()})


def write_rows(name,rows):
    w=ShardWriter(CORPUS,name)
    for row in rows:w.append(row)
    m=w.close(lineage=info());verify(CORPUS,m);return m


def check_native(contract):
    import numpy as np
    required=('native_access','native_train_file','native_train_offsets','native_train_sha256','native_val_sha256')
    if any(k not in contract for k in required) or contract['native_access']!='INDEXED_TRAIN_ONLY':raise ValueError('explicit indexed native contract required before reader')
    windows=reader(ROOT,contract)
    if len(windows)!=1600 or windows.tokens.flags.writeable:raise ValueError('1600 read-only native windows required')
    ids=list(range(8))+list(range(1592,1600))
    for i in ids:
        offset=contract['native_train_offsets'][i]
        if len(windows[i])!=1025 or not np.array_equal(windows[i],windows.tokens[offset:offset+1025]):raise ValueError('actual reader source slice mismatch')
    return dict(reader_verified=True,read_only=True,full_schedule_windows=1600,windows_checked=16,cache_copies=0)


def freeze():
    import numpy as np
    from tokenizers import Tokenizer
    prior.producer.legacy.source.deadline()
    if CORPUS.parent.exists() or EVIDENCE.exists():raise GateNegative('old natural course outputs preserved')
    if training.data.digest(PARENT)!=PARENT_SHA:raise ValueError('fixed before-TEST parent changed')
    parent_report=json.loads((parent_runtime.course.EVIDENCE/'fact1/report.json').read_text())
    if parent_report['updates']!=688 or parent_report['checkpoint_sha256']!=PARENT_SHA:raise ValueError('complete predetermined parent required')
    tok=Tokenizer.from_file(str(training.data.TOKENIZER));population,rejected,accepted_sha=original_population(tok)
    original,base_rows,labels=base.read_course()
    code=[r for r in base_rows['train0'] if r['meta']['kind'] not in ('fictional_relation_fields','public_qa')]
    if len(code)!=4096:raise ValueError('same code replay4096')
    rows={};summaries={};expected={}
    for arm in ARMS:
        tally=Counter()
        for epoch in range(4):
            replay=[factory.make(factory.graph(i),lang,(i+epoch)%4) for i in range(128) for lang in ('ko','en')]
            key=arm+'_train'+str(epoch);rows[key]=copy.deepcopy(population['train'][arm])+copy.deepcopy(code)+replay
            summaries[key]=counts(rows[key],tok)
            if summaries[key]['rows']!=6356:raise ValueError('same6356 rows per epoch')
            tally.update({k:summaries[key][k] for k in ('x_tokens','assistant_targets')})
        expected[arm]=dict(tally,updates=200,native_x_tokens=1638400,binary_rows=12288,binary_position_events=original['expected_exposures']['known_binary_position_events'])
    rows['dev_natural_three']=population['dev']['three'];rows['dev_code']=copy.deepcopy(base_rows['known_code_dev'])
    rows['dev_fiction']=sum((copy.deepcopy(base_rows['dev'+str(v)]) for v in range(4)),[])
    reserve=json.loads((parent_runtime.course.CORPUS/'report.json').read_text());reserved=list(training.data.stream_rows(parent_runtime.course.CORPUS,reserve['manifests']['reserved_original_three_qa']))
    if len(reserved)!=64 or Counter(r['meta']['language'] for r in reserved)!=dict(ko=32,en=32):raise ValueError('fixed unexamined64 reserved natural roots required')
    rows['test_natural_three']=reserved
    train_roots={r['meta']['semantic_root_id'] for r in population['train']['three']};dev_roots={r['meta']['semantic_root_id'] for r in population['dev']['three']};test_roots={r['meta']['semantic_root_id'] for r in reserved}
    if train_roots&dev_roots or train_roots&test_roots or dev_roots&test_roots:raise ValueError('whole-source split overlap')
    rows['retention_fiction']=sum(([factory.make(factory.graph(i,'test'),lang,v) for i in range(8192,8256) for lang in ('ko','en')] for v in range(4)),[])
    excluded=set(original['native_train_offsets']);native_sources=[]
    for path in (prior.CORPUS/'report.json',prior.producer.data.source.CORPUS/'report.json',ROOT/'HF/sft_ready/p106b_context_replay_v2_s1337/corpus/report.json'):
        r=json.loads(path.read_text());excluded.update(r['native_train_offsets']);native_sources.append(dict(path=str(path.relative_to(ROOT)),sha256=training.data.digest(path)))
    tokens=np.memmap(ROOT/NATIVE_TRAIN,dtype=np.uint16,mode='r')
    offsets=[i for i in prior.data.binding.prior.source.native_offsets(len(tokens),1600+len(excluded)+1024) if i not in excluded][:1600]
    native=dict(native_access='INDEXED_TRAIN_ONLY',native_train_file=NATIVE_TRAIN,native_train_offsets=offsets,
        native_train_sha256=original['native_train_sha256'],native_val_sha256=original['native_val_sha256'])
    observation=check_native(native)
    CORPUS.mkdir(parents=True,exist_ok=False);manifests={k:write_rows(k,v) for k,v in rows.items()}
    label_manifest=write_rows('binary_labels',[dict(signature=k,**v) for k,v in labels.items()])
    result=dict(info(),status='ORIGINAL_QA3_COURSE_FROZEN',manifests=manifests,counts=summaries,expected_exposures=expected,
        binary_labels_manifest=label_manifest,source_inventory_accepted_sha256=accepted_sha,source_rejections=rejected,
        source_population_counts={k:len(v['three']) for k,v in population.items()},native_reader_observation=observation,
        native_exclusion_report_sha256=native_sources,parent_report_sha256=training.data.digest(parent_runtime.course.EVIDENCE/'fact1/report.json'),
        reserved_test_manifest_sha256=factory.sha(reserve['manifests']['reserved_original_three_qa']),
        train_dev_test_source_roots_disjoint=True,test_model_evaluation='NOT_RUN',**native)
    training.write(CORPUS/'report.json',result);training.write(EVIDENCE/'corpus_report.json',result)
    print('[ORIGINAL_QA3_COURSE] '+json.dumps(dict(expected=expected,population=result['source_population_counts'],native=observation)),flush=True);return 0


def read_course():
    r=prior.producer.legacy.source.required(CORPUS/'report.json')
    if r['status']!='ORIGINAL_QA3_COURSE_FROZEN' or r['code_sha256']!=info()['code_sha256']:raise ValueError('frozen natural course CODE changed')
    if training.data.digest(PARENT)!=PARENT_SHA or training.data.digest(ROOT/NATIVE_TRAIN)!=r['native_train_sha256'] or training.data.digest(prior.NATIVE/'val.bin')!=r['native_val_sha256']:raise ValueError('parent or native cache changed')
    check_native(r)
    rows={k:list(training.data.stream_rows(CORPUS,m)) for k,m in r['manifests'].items()}
    labels={v['signature']:{k:x for k,x in v.items() if k!='signature'} for v in training.data.stream_rows(CORPUS,r['binary_labels_manifest'])}
    return r,rows,labels


def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true');a=p.parse_args()
    if a.check_only:print('[ORIGINAL_QA3_CHECK_ONLY] '+json.dumps(info()));return 0
    try:return freeze()
    except GateNegative as exc:print('[ORIGINAL_QA3_HOLD] '+str(exc));return 8
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[ORIGINAL_QA3_ERROR] '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
