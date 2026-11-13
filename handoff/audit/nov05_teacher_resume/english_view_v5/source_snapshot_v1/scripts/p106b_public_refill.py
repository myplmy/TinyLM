#!/usr/bin/env python3
"""English supply for the approved publicC+B75M path, immutable new version.

fetch: user-run exact7 English TRAIN files only, no test/validation downloads.
build: existing five sources plus those files, global hash and25% family cap.
No model/GPU. Original corpora/manifest remain unchanged. New20MB shards only.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import sys
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.p106b_mixed_scale import (safe_repo_path, digest, source_specs, attach,
    rows_for as original_rows_for, COLLECTION_EXCLUDED, GOAL)

REPO='CohereLabs/aya_collection_language_split'
REVISION='a3af2fde4b4cb5b2775830b11244a1a20b5f004f'
SOURCE=ROOT/'HF/sft_sources/p106b_aya_collection_en_a3af2fde'
OUTPUT=ROOT/'HF/sft_ready/p106b_mixed_public_v3_en_refill'
WIRE=ROOT/'HF/sft_ready/p106b_mixed_student_wire_v3_en_refill'
STUDENT=ROOT/'HF/sft_ready/p106b_mixed_student_v3_en_refill'
FILES=(
    (627179915,'E62C621D50DEB9EB38842D2B32C5875001DAF93E482A179463D2D8007288E603'),
    (319443283,'F4395CC222ACCC3DCA1B21958FC0AB96B9E77BA46CBCD2A8FA2F99A89252FD8F'),
    (319371110,'0859D39AD651158D7E4FF7C50F8A104FA65D201E00DE9A4C6346888EDE486AA5'),
    (1624259026,'F378F421DFBCC32C602E043CF40F7804C613D85C37710994C8392CF2FEC69CF4'),
    (2008783413,'CFAC8220A3323B41941B3540D8DE4019804E98166E608CDDF8B9A6BC0375642B'),
    (868340093,'21E8840B93F2785E9F2C826B2F6F4DB4C4C72A70512BB2EE5F753DD4380081A4'),
    (553821641,'2482CA4333623B6DF7DDEBD5D0536D9D41AA6F89644A7FA10C7B46D1D9A3FE99'),
)


def english_specs():
    return [dict(family='aya_collection_en', language='en',
        path=str((SOURCE/f'english/train-{i:05d}-of-00007.parquet').relative_to(ROOT)),
        remote_file=f'english/train-{i:05d}-of-00007.parquet',
        repo=REPO, revision=REVISION, license='Apache-2.0_card',
        source_rights='CARD_ONLY_NOT_BLANKET_SUBSOURCE_CLEARANCE',
        original_split='train', sha256=sha, bytes=size) for i,(size,sha) in enumerate(FILES)]


def fetch_one(spec, opener=urlopen):
    path=safe_repo_path(ROOT/spec['path'])
    if path.exists():
        if path.stat().st_size!=spec['bytes'] or digest(path)!=spec['sha256']:
            raise ValueError('existing source changed; never overwrite: '+str(path))
        return 'VERIFIED_EXISTING'
    partial=path.with_name(path.name+'.partial')
    safe_repo_path(partial)
    if partial.exists() or partial.is_symlink():
        raise FileExistsError('partial preserved; inspect before a new download/version')
    path.parent.mkdir(parents=True,exist_ok=True)
    url=f"https://huggingface.co/datasets/{spec['repo']}/resolve/{spec['revision']}/{spec['remote_file']}"
    with opener(url,timeout=120) as remote, partial.open('xb') as out:
        total=0
        while True:
            block=remote.read(8*2**20)
            if not block:break
            total+=len(block)
            if total>spec['bytes']:raise ValueError('remote content larger than pinned source')
            out.write(block)
    if partial.stat().st_size!=spec['bytes'] or digest(partial)!=spec['sha256']:
        raise ValueError('download size/SHA mismatch; partial retained')
    os.link(partial,path)  # Fail if another writer published; do not replace a source.
    partial.unlink()  # Remove only this private completed temporary link.
    return 'DOWNLOADED_VERIFIED'


def fetch():
    safe_repo_path(SOURCE)
    if shutil.disk_usage(ROOT/'HF').free<sum(s for s,_ in FILES)+8*2**30:
        raise ValueError('need6.32GB sources plus8GiB processing headroom')
    for spec in english_specs():
        state=fetch_one(spec)
        print('[SOURCE_FILE] '+json.dumps(dict(path=spec['path'],status=state,sha256=spec['sha256'])),flush=True)
    manifest=SOURCE/'source_manifest.json'
    payload=dict(schema='P106B_ENGLISH_REFILL_SOURCE_V1',sources=english_specs(),
        total_bytes=sum(s for s,_ in FILES),heldout_source_files_used=False,
        source_quality='NOT_REVIEWED',formal_train_ready=False)
    if manifest.exists():
        if json.loads(manifest.read_text(encoding='utf-8'))!=payload:raise ValueError('source manifest changed')
    else:
        with manifest.open('x',encoding='utf-8') as f:json.dump(payload,f,ensure_ascii=False,indent=2);f.write('\n')
    return 0


def english_rows(spec):
    if spec['family']!='aya_collection_en':
        yield from original_rows_for(spec);return
    import pyarrow.parquet as pq
    for batch in pq.ParquetFile(ROOT/spec['path']).iter_batches(batch_size=512,
            columns=['id','inputs','targets','dataset_name']):
        for row in batch.to_pylist():
            family=row.get('dataset_name')
            if not isinstance(family,str) or family in COLLECTION_EXCLUDED:continue
            q,a=row.get('inputs'),row.get('targets')
            if not isinstance(q,str) or not isinstance(a,str) or not q.strip() or not a.strip():continue
            item=attach([dict(role='user',content=q.strip()),dict(role='assistant',content=a.strip())],
                spec,row['id'],'en',family)
            item['meta'].update(original_split='train',source_collection_row_id=row['id'])
            yield item


def build_check():
    from scripts.p106b_mixed_scale import TOKENIZER,TOK_SHA
    safe_repo_path(OUTPUT)
    if OUTPUT.exists() or OUTPUT.is_symlink():raise FileExistsError('preserve prior corpus, new version required')
    if digest(TOKENIZER)!=TOK_SHA:raise ValueError('chat32 tokenizer changed')
    specs=source_specs()+english_specs()
    for spec in specs:
        path=safe_repo_path(ROOT/spec['path'])
        if not path.is_file():raise FileNotFoundError('source fetch prerequisite: '+spec['path'])
        if digest(path)!=spec['sha256']:raise ValueError('pinned input changed: '+spec['path'])
    if shutil.disk_usage(ROOT/'HF').free<8*2**30:raise ValueError('need8GiB new processing headroom')
    return sorted(specs,key=lambda s:(s['path'],s['sha256']))


def build(specs):
    from scripts import p106b_balanced_public as balanced
    from unittest.mock import patch
    # Process-local reuse of the tested selection engine. Old v2 path/defaults never change on disk.
    with patch.object(balanced,'OUTPUT',OUTPUT),patch.object(balanced,'rows_for',english_rows):
        return balanced.execute(specs)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=('fetch','build'),required=True)
    a=p.add_mutually_exclusive_group(required=True)
    a.add_argument('--execute',action='store_true');a.add_argument('--check-only',action='store_true')
    args=p.parse_args()
    if args.mode=='fetch':
        if args.check_only:
            print('[FETCH_PLAN] '+json.dumps(dict(sources=english_specs(),total_bytes=sum(s for s,_ in FILES),
                network='NOT_RUN',quality='NOT_REVIEWED',gpu='NOT_RUN'),ensure_ascii=False));return 0
        return fetch()
    specs=build_check()
    if args.check_only:
        print('[BUILD_CHECK] '+json.dumps(dict(sources=specs,output=str(OUTPUT.relative_to(ROOT)),
            source_token_cap=GOAL//4,train_per_language=GOAL,gpu='NOT_RUN'),ensure_ascii=False));return 0
    return build(specs)


if __name__=='__main__':
    try:raise SystemExit(main())
    except KeyboardInterrupt:
        print('[INTERRUPTED] new partials preserved; original inputs unchanged',file=sys.stderr);raise SystemExit(130)
    except (FileNotFoundError,FileExistsError) as exc:
        print('[HOLD] '+str(exc),file=sys.stderr);raise SystemExit(8)
    except Exception as exc:
        print('[ERROR] '+type(exc).__name__+': '+str(exc),file=sys.stderr);raise SystemExit(9)
