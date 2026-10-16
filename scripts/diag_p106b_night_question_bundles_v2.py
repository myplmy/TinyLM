#!/usr/bin/env python3
"""Write-once sharded recovery of the source-defined CPU question-bundle census."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import diag_p106b_night_question_bundles as old
from scripts.p106b_shards import ShardWriter,verify

qa,method,probe=old.qa,old.method,old.probe
TAG='p106b_night_question_bundles_v2_s1337'
FROZEN=ROOT/'HF/sft_ready'/TAG/'source'
EVIDENCE=ROOT/'test_result/evidence'/TAG
CODE=(*old.CODE,'scripts/diag_p106b_night_question_bundles_v2.py',
      'scripts/test_p106b_night_question_bundles_v2.py','scripts/p106b_shards.py')


def info():
    return dict(old.info(),schema='P106B_NIGHT_QUESTION_BUNDLE_RUNTIME_V2',tag=TAG,
        code_sha256={p:qa.data.digest(ROOT/p) for p in sorted(set(CODE))},
        storage='full source bundles in ignored row-aligned JSONL shards <=20,000,000 bytes; Git summaries only')


def safe():
    for target in (FROZEN,EVIDENCE):
        for path in (target,*target.parents):
            if path.is_symlink():raise ValueError('linked bundle recovery namespace')
            if path==ROOT:break


def save_census(name,census,*,limit=20_000_000):
    manifest=None
    if census['bundles']:
        writer=ShardWriter(FROZEN,name,limit=limit)
        for row in census['bundles']:writer.append(row)
        manifest=writer.close(lineage=dict(full_census_sha256=method._sha(census)))
    summary=old.source_summary(census)
    qa.write(FROZEN/(name+'_summary.json'),summary)
    return dict(summary_sha256=qa.data.digest(FROZEN/(name+'_summary.json')),
        manifest_sha256=qa.data.digest(FROZEN/(name+'_shards_manifest.json')) if manifest is not None else None,
        full_census_sha256=method._sha(census))


def restore_census(name,storage):
    summary_path=FROZEN/(name+'_summary.json')
    if qa.data.digest(summary_path)!=storage['summary_sha256']:raise ValueError('source summary changed')
    summary=qa.required(summary_path);rows=[]
    if storage['manifest_sha256'] is not None:
        path=FROZEN/(name+'_shards_manifest.json')
        if qa.data.digest(path)!=storage['manifest_sha256']:raise ValueError('source manifest changed')
        manifest=qa.required(path);verify(FROZEN,manifest)
        for shard in manifest['shards']:
            with (FROZEN/shard['path']).open(encoding='utf-8') as stream:
                rows.extend(json.loads(line) for line in stream)
        if manifest['lineage']!={'full_census_sha256':storage['full_census_sha256']}:
            raise ValueError('source shard lineage changed')
    census=dict(summary,bundles=rows)
    if method._sha(census)!=storage['full_census_sha256']:raise ValueError('full census reconstruction changed')
    return census


def prepare():
    import torch
    safe();train,test=old.sources()
    if FROZEN.exists() or EVIDENCE.exists():raise FileExistsError('old census recovery preserved')
    censuses={name:method.census(rows) for name,rows in (('train',train),('test',test))}
    if torch.cuda.is_initialized():raise ValueError('CPU census initialized CUDA')
    selected=[]
    for language in ('ko','en'):
        values=[b for b in censuses['test']['bundles'] if b['language']==language and b['character_distinct_candidate']]
        selected.extend(b['bundle_id'] for b in sorted(values,key=lambda b:qa.data.sha([20261017,'bundle-review',b['bundle_id']]))[:2])
    storage={name:save_census(name,census) for name,census in censuses.items()}
    result=dict(info(),status='QUESTION_BUNDLE_CPU_FROZEN',cuda_initialized=False,
        censuses={name:old.source_summary(c) for name,c in censuses.items()},storage=storage,
        review_bundle_ids=sorted(selected),review_selection='source bundle ID hash only; no output selection')
    qa.write(FROZEN/'report.json',result);qa.write(EVIDENCE/'inputs.json',result)
    print('[QUESTION_BUNDLE_CPU] '+json.dumps({name:c['counts'] for name,c in censuses.items()}),flush=True)
    return 0


def read_inputs():
    safe();frozen=qa.required(FROZEN/'report.json');train,test=old.sources()
    if (frozen.get('status')!='QUESTION_BUNDLE_CPU_FROZEN'
            or any(frozen.get(k)!=v for k,v in info().items())
            or frozen.get('cuda_initialized') is not False or qa.required(EVIDENCE/'inputs.json')!=frozen):
        raise ValueError('same-code whole CPU source proof required')
    censuses={}
    for name,rows in (('train',train),('test',test)):
        actual=method.census(rows);saved=restore_census(name,frozen['storage'][name])
        if saved!=actual or old.source_summary(actual)!=frozen['censuses'][name]:
            raise ValueError('source census differs')
        censuses[name]=saved
    return frozen,test,censuses['test']


def readback():
    _,cases,census=read_inputs();target=EVIDENCE/'readback.json'
    if target.exists():raise FileExistsError('old bundle recovery readback preserved')
    reports={};identities={};source_reports={}
    for provider,endpoints in old.PROVIDERS:
        family='foundation' if provider is old.e else 'prompt' if provider is old.prompt else 'unique'
        for endpoint in endpoints:
            _,identity,_,report_hash,events=probe.verified_primary(provider,endpoint)
            label=family+'.'+endpoint
            reports[label]=old.compact_result(method.summarize(events,cases),census)
            source_reports[label]=report_hash;identities.setdefault(identity,[]).append(label)
    if list(reports)!=old.labels():raise ValueError('all ten fixed labels required')
    result=dict(info(),status='QUESTION_BUNDLE_TEN_RAW_RECOUNTED',errors=0,
        input_report_sha256=qa.data.digest(FROZEN/'report.json'),endpoint_report_sha256=source_reports,
        checkpoint_alias_groups=identities,reports=reports,incomplete_endpoints_filled_with_zero=False,
        training_examples_generated=False)
    qa.write(target,result)
    for label,report in reports.items():
        print('[QUESTION_BUNDLE_MODEL] '+json.dumps(dict(endpoint=label,by_language={l:report['by_language'][l]['by_category']['character_distinct_candidate'] for l in ('ko','en')})),flush=True)
    return 0


def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=('freeze','readback'),required=True)
    p.add_argument('--execute',action='store_true');a=p.parse_args()
    if not a.execute:p.error('explicit CPU operation required')
    try:return prepare() if a.mode=='freeze' else readback()
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[QUESTION_BUNDLE_ERROR] '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
