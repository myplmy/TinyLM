#!/usr/bin/env python3
"""CPU source/template raw packet only; no teacher, model, or training corpus."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from datetime import datetime,timezone
import hashlib
import json
import time
from scripts import p106b_source_template_samples as method
from scripts.p106b_gate_runtime import GateNegative,wall_limit
from scripts.p106b_shards import ShardWriter,verify
from scripts.diag_p106b_grounded_span import DEADLINE,deadline
TAG='p106b_source_template_packet_v1_s1337'
OUTPUT=ROOT/'HF/sft_ready'/TAG
EVIDENCE=ROOT/'test_result/evidence'/TAG
ORIGINAL=ROOT/'HF/sft_ready/p106b_capability_source_inventory_v1/report.json'
CODE=('scripts/p106b_source_template_samples.py','scripts/test_p106b_source_template_samples.py','scripts/diag_p106b_source_template_packet.py')


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(2**20),b''):h.update(block)
    return h.hexdigest().upper()


def specs():
    source=json.loads(ORIGINAL.read_text());values=[]
    for value in source['input']['sources']:
        if value['family'] not in ('aya_collection','aya_collection_en'):continue
        lang='ko' if value['family']=='aya_collection' else 'en'
        path=ROOT/value['path']
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to((ROOT/'HF/sft_sources').resolve()):raise ValueError('exact existing non-symlink public source required')
        values.append(dict(spec=value,language=lang))
    if len(values)!=9:raise ValueError('exact nine existing Collection source files required')
    return values


def info():
    return dict(schema='P106B_SOURCE_TEMPLATE_PACKET_V1',tag=TAG,code_sha256={p:digest(ROOT/p) for p in CODE},
        old_inventory_sha256=digest(ORIGINAL),source_specs=specs(),families=method.FAMILIES,per_language_family_template=8,
        teacher_calls=0,model_loading='NOT_RUN',training_corpus_saved=False,sample_packet=True,
        world_truth='NOT_REVIEWED',rights_status='CARD_ONLY, preserve exact original provenance',deadline_utc=DEADLINE.isoformat())


def run(a):
    import pyarrow.dataset as ds
    deadline()
    if OUTPUT.exists() or EVIDENCE.exists():raise GateNegative('old packet namespace preserved')
    metadata=info();started=time.perf_counter();sampler=method.Sampler();checked=[]
    with wall_limit(a.max_wall_sec):
        for item in metadata['source_specs']:
            deadline();spec=item['spec'];path=ROOT/spec['path']
            if digest(path)!=spec['sha256']:raise ValueError('pinned raw source changed: '+spec['path'])
            checked.append(dict(path=spec['path'],sha256=spec['sha256'],bytes=path.stat().st_size))
            names=[x+suffix for x in method.FAMILIES for suffix in ('',' (T)')]
            dataset=ds.dataset(str(path),format='parquet')
            scanner=dataset.scanner(columns=['id','inputs','targets','dataset_name','sub_dataset_name','task_type','template_id','language','script','split'],
                filter=ds.field('dataset_name').isin(names),batch_size=1024)
            for batch in scanner.to_batches():
                deadline()
                for row in batch.to_pylist():sampler.add(row,item['language'],spec)
            print('[SOURCE_TEMPLATE_FILE] '+json.dumps(dict(path=spec['path'],groups=len(sampler.groups),raw_selected_rows=sum(x['raw_rows'] for x in sampler.groups.values()))),flush=True)
        OUTPUT.mkdir(parents=True,exist_ok=False);writer=ShardWriter(OUTPUT,'raw_template_samples')
        for row in sampler.rows():writer.append(row)
        manifest=writer.close(lineage=metadata);verify(OUTPUT,manifest)
        report=dict(metadata,status='SOURCE_TEMPLATE_PACKET_PREPARED',counts=sampler.counts(),sample_manifest=manifest,
            sample_directory=str(OUTPUT.relative_to(ROOT)),source_hashes_checked=checked,rejections=dict(sampler.rejections),
            semantic_review='NOT_RUN',new_usable_tokens='NOT_MEASURED',new75M_ready=False,whole_sec=time.perf_counter()-started)
        for target in (OUTPUT/'report.json',EVIDENCE/'report.json'):
            target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('x',encoding='utf-8') as stream:json.dump(report,stream,ensure_ascii=False,indent=2);stream.write('\n')
    print('[SOURCE_TEMPLATE_PACKET] '+json.dumps(dict(groups=len(sampler.groups),sample_rows=manifest['rows'],raw_selected_rows=sum(x['raw_rows'] for x in sampler.groups.values()),whole_sec=report['whole_sec'])),flush=True);return 0


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--max-wall-sec',type=int,default=1800)
    g=p.add_mutually_exclusive_group(required=True);g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true');a=p.parse_args()
    if not 30<=a.max_wall_sec<=1800:p.error('bounded30..1800')
    if a.check_only:print('[SOURCE_TEMPLATE_CHECK_ONLY] '+json.dumps(info()));return 0
    try:
        a.max_wall_sec=min(a.max_wall_sec,int((DEADLINE-datetime.now(timezone.utc)).total_seconds())-2700)
        if a.max_wall_sec<30:raise GateNegative('45minute closure margin')
        return run(a)
    except GateNegative as exc:print('[SOURCE_TEMPLATE_HOLD] '+str(exc));return 8
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[SOURCE_TEMPLATE_ERROR] '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
