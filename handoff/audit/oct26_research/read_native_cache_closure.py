#!/usr/bin/env python3
"""새 캐시의 원형완결을 읽고 제외 사유·편집 기록을 독립 재계수한다."""
from collections import Counter
import hashlib,json
from pathlib import Path
import sys,time
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from scripts import p106b_native_format_pair as pair
base=ROOT/'data_cache/p106b_native_format_pair_v1_20261026_s1337'
report=base/'complete.json';raw=report.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper()=='934F0879B830AFD3D216829D81869172FD4FF7CFB0DF4CEEDA9DF194849537A0'
d=json.loads(raw)
assert not (base/'failed.json').exists() and not d['synthetic']
assert d['training_admission']=='CPU_CACHE_PREPARED_NOT_TRAIN_OR_QUALITY_PASS'
counts=Counter();exclusions=Counter();edits=Counter();kept_edits=Counter();at=0;offsets=Counter();changed_kept=0;length_delta=0;absolute_length_delta=0
started=time.monotonic()
for spec in d['ledger']['shards']:
 path=pair.safe(str((base/'ledger'/spec['path']).relative_to(ROOT)))
 assert path.stat().st_size<20_000_000
 with path.open(encoding='utf-8') as stream:
  for line in stream:
   row=json.loads(line)
   assert row['eos_segment_index']==at;at+=1;counts['documents']+=1
   counts['kept' if row['kept'] else 'excluded']+=1
   exclusions.update(row['exclusions'])
   edits.update(x['operation'] for x in row['edits'])
   if row['kept']:
    changed_kept+=row['changed']
    kept_edits.update(x['operation'] for x in row['edits'])
    for arm in ('original','format'):
     assert row[arm]['offset_ids']==offsets[arm]
     offsets[arm]+=row[arm]['tokens']
    delta=row['original']['tokens']-row['format']['tokens']
    length_delta+=delta;absolute_length_delta+=abs(delta)
assert counts['documents']==d['documents'] and counts['kept']==d['kept_documents']
assert all(offsets[k]==d['arms'][k]['tokens'] for k in offsets)
policy=ROOT/'handoff/audit/oct26_research/native_format_pair_policy.json'
assert pair.source_identity()['sha256']==d['source_identity']['sha256']
out=dict(schema='P106B_NATIVE_FORMAT_CACHE_ROOT_CLOSURE_V1',actual_root_launcher_exit=0,
 source_report=str(report.relative_to(ROOT)),source_report_sha256=hashlib.sha256(raw).hexdigest().upper(),
 policy_path=str(policy.relative_to(ROOT)),policy_sha256=hashlib.sha256(policy.read_bytes()).hexdigest().upper(),
 source_identity=d['source_identity'],actual_counts=dict(counts),exclusions=dict(exclusions),
 edits=dict(edits),kept_edits=dict(kept_edits),changed_kept_documents=changed_kept,
 net_id_length_decrease=length_delta,absolute_document_id_length_delta=absolute_length_delta,
 token_edit_distance='NOT_MEASURED_LENGTH_DIFFERENCE_IS_NOT_EDITED_TOKEN_COUNT',
 arms=d['arms'],ledger=dict(rows=d['ledger']['rows'],bytes=d['ledger']['bytes'],
  concat_sha256=d['ledger']['concat_sha256'],shards=d['ledger']['shards']),
 validation=d['validation'],source_binary_rehashed_in_this_readback=False,
 prepared_two_pool_runtime_complete=True,semantic_quality='NOT_ESTABLISHED',
 document_unit='EOS_CACHE_SEGMENTS_NOT_ORIGINAL_URL_DOCUMENTS',
 original_url_global_leakage='UNVERIFIED',source_candidates_mutated=False,
 native300m_training='NOT_RUN',teacher75m_sft_complete=False,
 elapsed_root_readback_sec=time.monotonic()-started)
target=ROOT/'handoff/audit/oct26_research/native_cache_root_closure.json'
with target.open('x',encoding='utf-8') as f:json.dump(out,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({k:out[k] for k in ['actual_counts','exclusions','edits','kept_edits','changed_kept_documents','net_id_length_decrease','absolute_document_id_length_delta','elapsed_root_readback_sec']},ensure_ascii=False,indent=2))

