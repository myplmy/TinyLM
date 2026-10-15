#!/usr/bin/env python3
"""Immutable source references with epoch-interleaved views and untouched TEST."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter,defaultdict
import copy
import json
from scripts import diag_p106b_relation_course as base
from scripts import p106b_relation_interleaved_schedule as schedule
from scripts import p106b_public_qa_roles as original_roles
from scripts.p106b_gate_runtime import GateNegative
from scripts.p106b_shards import ShardWriter,verify
prior=base.prior
training=base.training
factory=base.factory
PARENT,PARENT_SHA=base.PARENT,base.PARENT_SHA
TAG='p106b_relation_interleaved_v1_s1337'
CORPUS=ROOT/'HF/sft_ready'/TAG/'corpus'
EVIDENCE=ROOT/'test_result/evidence'/TAG
CODE=(*base.CODE,'scripts/diag_p106b_relation_train.py','scripts/test_p106b_relation_train.py',
    'scripts/p106b_public_qa_roles.py','scripts/test_p106b_public_qa_roles.py',
    'scripts/p106b_relation_interleaved_schedule.py','scripts/test_p106b_relation_interleaved_schedule.py',
    'scripts/diag_p106b_relation_interleaved_course.py','scripts/test_p106b_relation_interleaved_course.py')
PACKETS=(ROOT/'HF/sft_ready/p106b_capability_source_inventory_v1',ROOT/'HF/sft_ready/p106b_source_template_packet_v1_s1337')


def info():
    r=base.info();r.update(schema='P106B_RELATION_INTERLEAVED_V1',tag=TAG,fact_weights=[1.],
        code_sha256={p:training.data.digest(ROOT/p) for p in sorted(set(CODE))},
        source_course_report_sha256=training.data.digest(base.CORPUS/'report.json'),
        schedule='view=(neutral_root_index+epoch)%4; original teacher/code replay unchanged',
        current_natural_test_per_language=16,reserve_future_max_per_language=32,reserve_future_min_per_language=24,
        new_test_fiction_indices=[8192,8447],source_packet_report_sha256=[training.data.digest(p/'report.json') for p in PACKETS])
    return r


def write_rows(name,rows):
    w=ShardWriter(CORPUS,name)
    for row in rows:w.append(row)
    m=w.close(lineage=info());verify(CORPUS,m);return m


def clean_single_metadata(row):
    result=copy.deepcopy(row)
    for key in ('control_output_contract','capability_profile','capability_derivation','multiturn_kind',
        'assistant_targets','processed_x_tokens','original_source_x_tokens'):result['meta'].pop(key,None)
    return result


def reference_sha(row):
    text=''.join(b['text'] for b in row['messages'][0]['content']);a,b=row['meta']['user_reference_range']
    return factory.sha([row['meta']['language'],text[a:b]])


def fresh_sources(tok):
    source=prior.producer.data.source;old,oldrows,_=source.read_course();ids,keys,old_refs=source.old_source_exclusions();ids={x.upper() for x in ids};keys=set(keys)
    for values in oldrows.values():
        for row in values:
            if row['meta'].get('kind')!='natural_first_qa':continue
            ids.add(row['meta']['parent_concept_id'].upper());keys.update(source.method.passage_keys(row['meta']['original_first_pair']['reference']))
    inputs=json.loads((prior.producer.OUTPUT/'inputs.json').read_text())
    for job in training.data.stream_rows(prior.producer.OUTPUT,inputs['jobs_manifest']):keys.update(source.method.passage_keys(job['reference']))
    oldr=json.loads((base.CORPUS/'report.json').read_text())
    for row in training.data.stream_rows(base.CORPUS,oldr['manifests']['fresh_public_test']):
        ids.add(row['meta']['parent_concept_id'].upper());keys.update(source.method.passage_keys(row['meta']['original_first_pair']['reference']))
    for directory in PACKETS:
        report=json.loads((directory/'report.json').read_text())
        for sample in training.data.stream_rows(directory,report['sample_manifest']):
            if 'producer_identity' in sample:
                if sample['producer_identity']['family']!='Flan-Coqa':continue
                text=sample['original']['inputs']
            else:
                if sample['group'].split(':',1)[-1]!='Flan-Coqa':continue
                text=source.method.text(sample['original']['messages'][0])
            keys.update(source.method.passage_keys(text))
    if training.data.digest(training.data.PUBLIC/'report.json')!=training.data.PUBLIC_SHA:raise ValueError('pinned original public differs')
    candidates=[];seen=set();rejected=Counter()
    from tinylm.train import mtp_sft as core
    for split in ('train','val'):
        m=json.loads((training.data.PUBLIC/(split+'_shards_manifest.json')).read_text())
        for row in training.data.stream_rows(training.data.PUBLIC,m):
            meta=row['meta']
            if meta.get('selection_family')!='Flan-Coqa' or meta['parent_concept_id'].upper() in ids:continue
            try:
                triple,parsed=original_roles.wrap(row);rec=core.encode_record(triple,tok);first=source.method.first_pair(row)
                if rec.x_tokens>1024 or len(tok.encode(parsed['reference']).ids)>736 or len(tok.encode(parsed['pairs'][0]['answer']).ids)>24:continue
            except ValueError as exc:rejected[str(exc)]+=1;continue
            identity=source.method.sha([meta['language'],parsed['reference']]);passages=source.method.passage_keys(parsed['reference'])
            if identity in seen or passages&keys:continue
            seen.add(identity);candidates.append((factory.sha([TAG,identity]),meta['language'],row,triple,first,passages,identity))
    pools=defaultdict(list);taken=set()
    for rank,lang,row,triple,first,passages,identity in sorted(candidates,key=lambda x:x[0]):
        if passages&taken:continue
        taken.update(passages);pools[lang].append((row,triple,first,identity))
    supply={k:len(v) for k,v in pools.items()};reserve=min(32,min(len(pools[l]) for l in ('ko','en'))-16)
    if reserve<24:raise GateNegative('fresh source current16+future24 each short: '+str(supply))
    selected=[];reserved=[]
    for lang in ('ko','en'):
        for row,triple,first,identity in pools[lang][:16]:selected.append(clean_single_metadata(source.method.wrap(row,first,'INTERLEAVE_FRESH16')))
        for row,triple,first,identity in pools[lang][16:16+reserve]:
            child=copy.deepcopy(triple);child['meta'].update(semantic_root_id=identity,original_first_pair=first,reserved_for='future_original_three_qa_study_not_run');reserved.append(child)
    return selected,reserved,dict(supply=supply,current_per_language=16,reserved_per_language=reserve,rejections=dict(rejected),
        excludes_current128_and_all_previous_sources_and_template_packets=True,semantic_overlap='NOT_AUDITED',raw_id_is_bilingual_alignment=False)


def freeze():
    from tokenizers import Tokenizer
    prior.producer.legacy.source.deadline()
    if CORPUS.parent.exists() or EVIDENCE.exists():raise GateNegative('old interleave namespace preserved')
    old,rows,labels=base.read_course();probe=json.loads((base.EVIDENCE/'evaluate/history_prefix_recount.json').read_text())
    if probe['evaluation_report_sha256']!=training.data.digest(base.EVIDENCE/'evaluate/report.json') or probe['identical_prefix_output_disagreements']!=0:raise GateNegative('same-prefix history path not verified; do not train around measurement bugs')
    tok=Tokenizer.from_file(str(training.data.TOKENIZER));fresh,reserved,fresh_info=fresh_sources(tok)
    mixed,pointers,proof=schedule.schedules(rows);counts={k:base.counts(v,tok) for k,v in mixed.items()}
    expected=Counter()
    for c in counts.values():expected.update({k:c[k] for k in ('x_tokens','assistant_targets','fact_rows','fact_queries')})
    if any(expected[k]!=old['expected_exposures'][k] for k in expected):raise ValueError('same global actual x/targets/oracle exposures required')
    if any(c['rows']!=22016 for c in counts.values()):raise ValueError('same22016 per epoch')
    newtests={'test'+str(v):[factory.make(factory.graph(i,'test'),lang,v) for i in range(8192,8448) for lang in ('ko','en')] for v in range(4)}
    train_refs={reference_sha(r) for r in rows['train0'][:16384]}
    old_refs={reference_sha(r) for r in rows['test0']}
    new_refs={reference_sha(r) for r in newtests['test0']}
    if train_refs&new_refs or old_refs&new_refs:raise ValueError('same exact fictional source across split or old TEST')
    CORPUS.mkdir(parents=True,exist_ok=False);schedule_manifests={k:write_rows(k+'_source_pointers',v) for k,v in pointers.items()}
    manifests={k:write_rows(k,v) for k,v in newtests.items()};manifests['fresh_public_test']=write_rows('fresh_public_test',fresh)
    manifests['reserved_original_three_qa']=write_rows('reserved_original_three_qa',reserved)
    result=dict(info(),status='RELATION_INTERLEAVED_COURSE_FROZEN',schedule_manifests=schedule_manifests,manifests=manifests,
        counts=counts,schedule_proof=proof,expected_exposures=old['expected_exposures'],fresh_public=fresh_info,
        native_train_file=old['native_train_file'],native_train_offsets=old['native_train_offsets'],native_train_sha256=old['native_train_sha256'],native_val_sha256=old['native_val_sha256'],
        native_windows_identical_to_blocked=True,prior_history_probe_sha256=training.data.digest(base.EVIDENCE/'evaluate/history_prefix_recount.json'),
        current_test_roots_not_previous_development=True,future_reserved_test_evaluated=False,model_loading='NOT_RUN')
    training.write(CORPUS/'report.json',result);training.write(EVIDENCE/'corpus_report.json',result)
    print('[INTERLEAVE_COURSE] '+json.dumps(dict(expected=result['expected_exposures'],balance=proof['per_epoch_view_rows'],fresh=fresh_info)),flush=True);return 0


def read_course():
    r=prior.producer.legacy.source.required(CORPUS/'report.json')
    if r['status']!='RELATION_INTERLEAVED_COURSE_FROZEN' or r['code_sha256']!=info()['code_sha256'] or r['source_course_report_sha256']!=training.data.digest(base.CORPUS/'report.json'):raise ValueError('immutable source/schedule CODE changed')
    old,rows,labels=base.read_course();result=dict(rows)
    for key,m in r['schedule_manifests'].items():
        selected=[]
        for p in training.data.stream_rows(CORPUS,m):
            row=rows['train'+str(p['source_view'])][p['source_row_index']]
            if factory.sha(row)!=p['row_sha256']:raise ValueError('frozen source pointer content changed')
            selected.append(row)
        result[key]=selected
    for key,m in r['manifests'].items():result[key]=list(training.data.stream_rows(CORPUS,m))
    return r,result,labels


def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true');a=p.parse_args()
    if a.check_only:print('[INTERLEAVE_COURSE_CHECK_ONLY] '+json.dumps(info()));return 0
    try:return freeze()
    except GateNegative as exc:print('[INTERLEAVE_COURSE_HOLD] '+str(exc));return 8
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[INTERLEAVE_COURSE_ERROR] '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
