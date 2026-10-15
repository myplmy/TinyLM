#!/usr/bin/env python3
"""Fresh immutable fictional relation course plus older teacher/code replay."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter,defaultdict
import copy
from datetime import datetime,timezone
import json
from scripts import p106b_relation_fields as factory
from scripts import diag_p106b_dualqa_curriculum as prior
from scripts import diag_p101a_sft_mtp as training
from scripts.p106b_shards import ShardWriter,verify
from scripts.p106b_gate_runtime import GateNegative
from scripts.p106b_native_windows import NATIVE_TRAIN
TAG='p106b_relation_fields_v1_s1337'
CORPUS=ROOT/'HF/sft_ready'/TAG/'corpus'
EVIDENCE=ROOT/'test_result/evidence'/TAG
PARENT=ROOT/'runs/ckpt/m100s10_ko-en_dualqa_dense_chat32_p106b_dualqa_curriculum_v1_s1337_contrast_epoch2.pt'
PARENT_SHA='B1484726ACF786AF6B65F8A94AF66A0E8D192897BFF3553B9EE2A7EF11559515'
ROOT_COUNTS={'train':8192,'dev':128,'test':256}
REPLAY_VIEWS=('repeat0','contrast0','repeat1','contrast1')
CODE=(*prior.CODE,'scripts/p106b_relation_fields.py','scripts/test_p106b_relation_fields.py',
    'scripts/p106b_relation_auxiliary.py','scripts/test_p106b_relation_auxiliary.py',
    'scripts/diag_p106b_relation_course.py','scripts/test_p106b_relation_course.py')


def info():
    return dict(schema=factory.VERSION,tag=TAG,code_sha256={p:training.data.digest(ROOT/p) for p in sorted(set(CODE))},
        parent=str(PARENT.relative_to(ROOT)),parent_sha256=PARENT_SHA,tokenizer_sha256=training.data.TOK_SHA,
        roots=ROOT_COUNTS,train_rows_per_epoch=22016,epochs=4,updates=688,micro_bs=8,accum=16,seq=1024,
        grad_checkpoint=True,compile='default',lr=5e-5,muon_lr=2e-4,native_weight=1.,known_query_weight=1.,
        fact_weights=[0.,1.],fact_rank=64,fact_parameters=98304,fact_in_inference=False,
        masked_wrong_first_answer=True,teacher_calls=0,formal_train_ready=False,
        world_truth='FICTIONAL_PRODUCER_GRAPH_ONLY; public teacher replay still unverified',
        deadline_utc=prior.producer.legacy.source.DEADLINE.isoformat())


def write_rows(name,rows):
    writer=ShardWriter(CORPUS,name)
    for r in rows:writer.append(r)
    manifest=writer.close(lineage=info());verify(CORPUS,manifest);return manifest


def counts(rows,tok):
    result=Counter();language=defaultdict(Counter)
    for r in rows:
        rec,label=factory.encode(r,tok)
        result.update(rows=1,x_tokens=rec.x_tokens,assistant_targets=rec.targets,
            fact_rows=int(label is not None),fact_queries=len(label['queries']) if label else 0)
        language[r['meta']['language']].update(x_tokens=rec.x_tokens,assistant_targets=rec.targets)
    return dict(result,languages={k:dict(v) for k,v in language.items()})


def fresh_public(tok):
    source=prior.producer.data.source;old,old_rows,_=source.read_course()
    old_ids,old_keys,old_refs=source.old_source_exclusions();used_ids={s.upper() for s in old_ids};used_keys=set(old_keys)
    for rows in old_rows.values():
        for row in rows:
            if row['meta'].get('kind')!='natural_first_qa':continue
            used_ids.add(row['meta']['parent_concept_id'].upper())
            used_keys.update(source.method.passage_keys(row['meta']['original_first_pair']['reference']))
    inputs=json.loads((prior.producer.OUTPUT/'inputs.json').read_text())
    for job in training.data.stream_rows(prior.producer.OUTPUT,inputs['jobs_manifest']):
        used_keys.update(source.method.passage_keys(job['reference']))
    if training.data.digest(training.data.PUBLIC/'report.json')!=training.data.PUBLIC_SHA:raise ValueError('pinned existing public source changed')
    candidates=[];seen=set();rejected=Counter()
    for split in ('train','val'):
        manifest=json.loads((training.data.PUBLIC/(split+'_shards_manifest.json')).read_text())
        for row in training.data.stream_rows(training.data.PUBLIC,manifest):
            m=row['meta']
            if m.get('selection_family')!='Flan-Coqa' or m.get('language') not in ('ko','en'):continue
            if m['parent_concept_id'].upper() in used_ids:continue
            try:
                pair=source.method.first_pair(row)
                if len(tok.encode(pair['answer']).ids)>24 or len(tok.encode(pair['reference']).ids)>736:continue
                item=source.method.wrap(row,pair,'relation_fresh_public_test')
                rec,_=factory.encode(item,tok)
            except ValueError as exc:rejected[str(exc)]+=1;continue
            identity=item['meta']['semantic_root_id']
            if identity in seen:continue
            seen.add(identity);keys=source.method.passage_keys(pair['reference'])
            if keys&used_keys:rejected['previous_source_exact24word']+=1;continue
            candidates.append((item,keys))
    pools=defaultdict(list);taken=set()
    for row,keys in sorted(candidates,key=lambda x:factory.sha([TAG,'FRESH',x[0]['meta']['semantic_root_id']])):
        if keys&taken:continue
        taken.update(keys);pools[row['meta']['language']].append(row)
    supply={k:len(v) for k,v in pools.items()};selected=[]
    for lang in ('ko','en'):
        if len(pools[lang])<64:raise GateNegative('fresh public64 each language short: '+str(supply))
        selected.extend(pools[lang][:64])
    return selected,dict(supply=supply,rejected=dict(rejected),previous_frozen_jobs_excluded=2112,
        old_source_report_sha256=training.data.digest(source.CORPUS/'report.json'),public_report_sha256=training.data.PUBLIC_SHA,
        previous_teacher_inputs_sha256=training.data.digest(prior.producer.OUTPUT/'inputs.json'),
        old_literal_source_exclusions=old_refs,cross_language_semantic_overlap='NOT_AUDITED',pretraining_overlap='NOT_AUDITED',
        source_truth='ORIGINAL_PUBLIC_FIRST_QA_UNVERIFIED',fresh_test_teacher_generated=False)


def freeze():
    import numpy as np
    from tokenizers import Tokenizer
    prior.producer.legacy.source.deadline()
    if CORPUS.parent.exists() or EVIDENCE.exists():raise GateNegative('old relation namespace preserved')
    if training.data.digest(PARENT)!=PARENT_SHA:raise ValueError('prelocked DEV parent changed')
    lock=json.loads((prior.EVIDENCE/'devbest_selection.json').read_text())
    if lock['choices']['contrast']['checkpoint_sha256']!=PARENT_SHA:raise ValueError('parent must be pre-TEST DEV choice')
    old,rows,old_labels=prior.read_course();tok=Tokenizer.from_file(str(training.data.TOKENIZER))
    fresh,fresh_info=fresh_public(tok)
    all_rows={};summaries={};expected=Counter();roots_by_split={};source_refs=[]
    for split,n in ROOT_COUNTS.items():
        graphs=[factory.graph(i,split) for i in range(n)];roots_by_split[split]={g['root'] for g in graphs}
        for view in range(4):
            key=split+str(view);values=[factory.make(g,lang,view) for g in graphs for lang in ('ko','en')]
            if split=='train':values+=copy.deepcopy(rows[REPLAY_VIEWS[view]])
            all_rows[key]=values;summaries[key]=counts(values,tok)
            if split=='train':expected.update({k:summaries[key][k] for k in ('x_tokens','assistant_targets','fact_rows','fact_queries')})
    for a,b in (('train','dev'),('train','test'),('dev','test')):
        if roots_by_split[a]&roots_by_split[b]:raise ValueError('neutral graph split overlap')
    if any(summaries['train'+str(v)]['rows']!=22016 for v in range(4)):raise ValueError('exact22016/76per epoch')
    if expected['fact_rows']!=65536 or expected['fact_queries']!=114688:raise ValueError('masked oracle row/query exposure mismatch')
    all_rows['teacher_dev']=copy.deepcopy(rows['dev']);all_rows['known_code_dev']=copy.deepcopy(rows['code_retention_dev']);all_rows['fresh_public_test']=fresh
    for key in ('teacher_dev','known_code_dev','fresh_public_test'):summaries[key]=counts(all_rows[key],tok)
    native=np.memmap(ROOT/NATIVE_TRAIN,dtype=np.uint16,mode='r');excluded=set(old['native_train_offsets'])
    ancestor=json.loads((prior.producer.data.source.CORPUS/'report.json').read_text());excluded.update(ancestor['native_train_offsets'])
    old_native=json.loads((ROOT/'HF/sft_ready/p106b_context_replay_v2_s1337/corpus/report.json').read_text());excluded.update(old_native['native_train_offsets'])
    offsets=[i for i in prior.data.binding.prior.source.native_offsets(len(native),688*8+len(excluded)+1024) if i not in excluded][:688*8]
    if len(offsets)!=5504:raise ValueError('complete disjoint native train schedule')
    CORPUS.mkdir(parents=True,exist_ok=False);manifests={key:write_rows(key,values) for key,values in all_rows.items()}
    labels_manifest=write_rows('known_code_labels',[dict(signature=k,**v) for k,v in old_labels.items()])
    result=dict(info(),status='RELATION_COURSE_FROZEN',counts=summaries,manifests=manifests,known_code_labels_manifest=labels_manifest,
        original_course_sha256=training.data.digest(prior.CORPUS/'report.json'),prelocked_parent_selection_sha256=training.data.digest(prior.EVIDENCE/'devbest_selection.json'),
        expected_exposures=dict(expected,native_x_tokens=688*8192,known_binary_rows=12288,known_binary_position_events=old['expected_exposures']['code_auxiliary_position_events']),
        fresh_public=fresh_info,native_access='INDEXED_TRAIN_ONLY',native_train_file=NATIVE_TRAIN,native_train_offsets=offsets,
        native_train_sha256=old['native_train_sha256'],native_val_sha256=old['native_val_sha256'],
        same_graph_language_children_grouped=True,original_wrong_first_answers_are_context_not_targets=True,model_loading='NOT_RUN')
    training.write(CORPUS/'report.json',result);training.write(EVIDENCE/'corpus_report.json',result)
    print('[RELATION_COURSE_FROZEN] '+json.dumps(dict(expected=result['expected_exposures'],fresh_supply=fresh_info['supply'],train_rows=22016,views=4)),flush=True)
    return 0


def read_course():
    r=prior.producer.legacy.source.required(CORPUS/'report.json')
    if r['status']!='RELATION_COURSE_FROZEN' or r['code_sha256']!=info()['code_sha256']:raise ValueError('frozen relation code changed')
    if training.data.digest(PARENT)!=PARENT_SHA or training.data.digest(ROOT/NATIVE_TRAIN)!=r['native_train_sha256'] or training.data.digest(prior.NATIVE/'val.bin')!=r['native_val_sha256']:raise ValueError('immutable parent/cache changed')
    rows={key:list(training.data.stream_rows(CORPUS,m)) for key,m in r['manifests'].items()}
    labels={x['signature']:{k:v for k,v in x.items() if k!='signature'} for x in training.data.stream_rows(CORPUS,r['known_code_labels_manifest'])}
    return r,rows,labels


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true');p.add_argument('--check-only',action='store_true');a=p.parse_args()
    if a.execute==a.check_only:p.error('exactly one execute/check-only')
    if a.check_only:print('[RELATION_COURSE_CHECK_ONLY] '+json.dumps(info()));return 0
    try:return freeze()
    except GateNegative as exc:print('[RELATION_COURSE_HOLD] '+str(exc));return 8
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[RELATION_COURSE_ERROR] '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
