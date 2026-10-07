#!/usr/bin/env python3
"""User CPU inventory of pinned public sources, not a new75M training corpus.

Count every normalized source row and current routing decision. Keep at most8
hash-selected full rows per family/language for later contextual review. Token
and mask checks are sampled only; they are not a full usable-token census.
No teacher, model, GPU, downloads or old corpus writes.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import p106b_capability_corpus as capability
from scripts.p106b_public_refill import english_rows
from scripts.p106b_mixed_scale import digest,safe_repo_path,TOKENIZER,TOK_SHA
from scripts.p106b_shards import ShardWriter,verify
from tinylm.data.sft import encode_conversation,sft_targets

OUTPUT=ROOT/'HF/sft_ready/p106b_capability_source_inventory_v1'
PER_GROUP=8
MAX_SAMPLE_ROW_BYTES=250_000
MAX_SAMPLE_BYTES=64*2**20


def sample_rank(row):
    meta=row['meta']
    reference={key:meta.get(key) for key in ('source_repo','source_revision','source_sha256',
                                            'source_id','source_family','language')}
    return hashlib.sha256(json.dumps(reference,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


class Inventory:
    def __init__(self):
        self.groups={};self.samples={};self.total=0;self.sample_rejections=Counter()

    def add(self,row):
        self.total+=1
        language=row['meta']['language'];family=capability.engine.family_bucket(row['meta']['source_family'])
        group=language+':'+family
        body=row['messages'][1:] if row['messages'][0]['role']=='system' else row['messages']
        derived=capability.derive(row)
        rec=self.groups.setdefault(group,dict(language=language,family=family,original_rows=0,
            current_builder_eligible_rows=0,current_builder_unassigned_rows=0,role_sequence_rows=0,
            normalized_user_turns=Counter(),source_paths=set()))
        rec['original_rows']+=1;rec['normalized_user_turns'][str(sum(m['role']=='user' for m in body))]+=1
        if len(body)>=4:rec['role_sequence_rows']+=1
        rec['current_builder_eligible_rows' if derived is not None else 'current_builder_unassigned_rows']+=1
        rec['source_paths'].add(row['meta'].get('inventory_source_path',''))
        payload=dict(group=group,current_builder_eligible=derived is not None,original=row,
                     sampled_derived=derived,quality='NOT_REVIEWED',training_admission='NOT_DECIDED')
        size=len(json.dumps(payload,ensure_ascii=False).encode())
        if size>MAX_SAMPLE_ROW_BYTES:
            self.sample_rejections['row_preview_too_large']+=1;return
        choices=self.samples.setdefault(group,{})
        choices[sample_rank(row)]=payload
        if len(choices)>PER_GROUP:del choices[max(choices)]

    def rows(self):
        used=0
        for group in sorted(self.samples):
            for rank,payload in sorted(self.samples[group].items()):
                size=len(json.dumps(payload,ensure_ascii=False).encode())
                if used+size>MAX_SAMPLE_BYTES:
                    self.sample_rejections['global_sample_byte_cap']+=1;continue
                used+=size;yield dict(payload,sampling_rank=rank)

    def summary(self):
        groups=[]
        for _,rec in sorted(self.groups.items()):
            rec=dict(rec);rec['normalized_user_turns']=dict(rec['normalized_user_turns'])
            rec['source_paths']=sorted(rec['source_paths']);groups.append(rec)
        return dict(original_rows=self.total,groups=groups,
            current_builder_eligible_rows=sum(r['current_builder_eligible_rows'] for r in groups),
            current_builder_unassigned_rows=sum(r['current_builder_unassigned_rows'] for r in groups),
            sample_rejections=dict(self.sample_rejections),
            routing_scope='existing family/role policy, NOT a semantic defect classifier',
            quality='NOT_REVIEWED',full_usable_tokens='NOT_MEASURED',new75M_ready=False)


def token_sample(row,tok):
    result=dict(original_nonpadding_tokens=None,derived_nonpadding_tokens=None,derived_targets=None)
    try:
        ids,_,_=encode_conversation(row['original'],tok)
        result['original_nonpadding_tokens']=max(0,len(ids)-1)
        derived=row['sampled_derived']
        if derived is not None:
            ids,labels,_=encode_conversation(derived,tok);x,targets=sft_targets(ids,labels)
            result.update(derived_nonpadding_tokens=len(x),derived_targets=sum(value>=0 for value in targets),
                          derived_within1024=len(ids)-1<=1024)
    except (ValueError,TypeError,KeyError) as exc:
        result.update(token_error_type=type(exc).__name__,token_error=str(exc)[:300])
    result['scope']='sample only, never extrapolated as measured whole-corpus supply'
    return result


def check():
    safe_repo_path(OUTPUT)
    if OUTPUT.exists() or OUTPUT.is_symlink():raise FileExistsError('prior inventory preserved; use new stage')
    specs=capability.sources()
    if digest(TOKENIZER)!=TOK_SHA:raise ValueError('chat32 tokenizer differs')
    return dict(schema='P106B_PUBLIC_SOURCE_INVENTORY_PREFLIGHT_V1',sources=specs,
        source_hashes='FULL_USER_EXECUTION_ONLY',output=str(OUTPUT.relative_to(ROOT)),
        samples_per_family_language=PER_GROUP,source_quality='NOT_REVIEWED',
        model_loading='NOT_RUN',gpu='NOT_RUN',downloads='NOT_RUN')


def execute(info):
    from tokenizers import Tokenizer
    for spec in info['sources']:
        if digest(ROOT/spec['path'])!=spec['sha256']:raise ValueError('pinned public source changed')
    OUTPUT.mkdir(exist_ok=False);inventory=Inventory();began=time.perf_counter();writer=None
    report=dict(schema='P106B_PUBLIC_SOURCE_INVENTORY_V1',input=info,
                student_training='NOT_RUN',teacher_generation='NOT_RUN',new75M_ready=False)
    try:
        for spec in info['sources']:
            before=inventory.total
            for row in english_rows(spec):
                row['meta']['inventory_source_path']=spec['path'];inventory.add(row)
            print('[SOURCE_INVENTORY] '+json.dumps(dict(path=spec['path'],rows=inventory.total-before,
                cumulative_rows=inventory.total)),flush=True)
        if not inventory.total:raise ValueError('zero source observations cannot pass inventory')
        tok=Tokenizer.from_file(str(TOKENIZER));writer=ShardWriter(OUTPUT,'review_samples')
        for row in inventory.rows():
            row['sample_token_contract']=token_sample(row,tok);writer.append(row)
        if not writer._total_rows:raise ValueError('zero review samples cannot pass inventory')
        manifest=writer.close(lineage=info);verify(OUTPUT,manifest);writer=None
        report.update(inventory.summary(),status='INVENTORY_COMPLETE',returncode=0,
                      sample_manifest=manifest)
    except BaseException as exc:
        from scripts.p106b_gate_runtime import disposition
        status,rc=disposition(exc);report.update(inventory.summary(),status=status,returncode=rc,
                                               error_type=type(exc).__name__,error=str(exc)[:1000])
    finally:
        if writer is not None and writer._total_rows:
            report['partial_sample_manifest']=writer.close(lineage=info);verify(OUTPUT,report['partial_sample_manifest'])
        report['whole_wall_sec']=time.perf_counter()-began
        with (OUTPUT/'report.json').open('x',encoding='utf-8') as stream:
            json.dump(report,stream,ensure_ascii=False,indent=2);stream.write('\n')
        print('[INVENTORY_FINAL] '+json.dumps({key:report.get(key) for key in
            ('status','returncode','original_rows','current_builder_eligible_rows',
             'current_builder_unassigned_rows','full_usable_tokens','error_type','error')},ensure_ascii=False),flush=True)
    return report['returncode']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--execute',action='store_true');mode.add_argument('--check-only',action='store_true')
    args=parser.parse_args()
    try:
        info=check()
        if args.check_only:print('[CHECK_ONLY] '+json.dumps(info));return 0
        return execute(info)
    except (FileNotFoundError,FileExistsError) as exc:print('[HOLD] '+str(exc),file=sys.stderr);return 8
    except Exception as exc:print('[ERROR] '+type(exc).__name__+': '+str(exc),file=sys.stderr);return 9


if __name__=='__main__':raise SystemExit(main())
