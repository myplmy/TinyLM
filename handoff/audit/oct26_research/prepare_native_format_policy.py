#!/usr/bin/env python3
"""문헌 담당의 보류 계보를 총괄이 검산하고 제어된 형식 대조 policy를 봉인한다."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from scripts import p106b_native_format_pair as pair
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for raw in iter(lambda:f.read(1024*1024),b''):h.update(raw)
 return h.hexdigest().upper()
def write(p,d):
 raw=(json.dumps(d,ensure_ascii=False,indent=2,sort_keys=True)+'\n').encode()
 assert len(raw)<20_000_000
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(raw)
p=ROOT/'handoff/audit/oct26_research/native_known_holds_readback_v2.json'
assert digest(p)=='059D800CB0ECAEFA8DA8A742759BF374C24278F86D9E3460A22CF3059CC6DC04'
d=json.loads(p.read_text())
assert d['schema']=='P106B_NATIVE_KNOWN_HOLDS_READBACK_20261026_V2'
assert d['summary']['union_holds']==1793 and not d['unresolved_mappings']
assert d['summary']['mapped_targets']==1793 and len(d['decision_conflicts'])==1
assert d['decision_conflicts'][0]['eos_segment_index']==37460
assert d['source']['sha256']==pair.SOURCE_SHA
assert d['external_val']['sha256']=='AD7EFB0DBD0D830A216B4D21A91C8ACB3FC41DAE2B23A3A55999AE8727AA374C'
assert d['tokenizer']['sha256']==pair.TOKEN_SHA
assets=[]
for item in d['assets']:
 path=pair.safe(item['path'])
 assert path.stat().st_size==item['bytes']<20_000_000
 assert digest(path)==item['sha256']
 assets.append(dict(path=item['path'],bytes=item['bytes'],sha256=item['sha256']))
holds=[];hashes={};positions=set()
for row in d['known_holds']:
 i=row['eos_segment_index'];a,z=row['cache_body_ids'];s=row['original_text_sha256']
 target=row['format_target']
 assert row['source_cache_sha256']==pair.SOURCE_SHA and row['source_cache_path']==pair.SOURCE
 assert target['eos_segment_index']==i and target['cache_segment_ids']==[a,z] and target['original_text_sha256']==s
 assert target['candidate_text_sha256_verified_for_target'] is True
 assert i not in positions and a<=z and i>=0
 positions.add(i)
 holds.append(dict(id='eos_'+str(i),source_sha256=pair.SOURCE_SHA,eos_segment_index=i,
    cache_segment_ids=[a,z],original_text_sha256=s,
    disposition='EXCLUDE_BOTH_PENDING_CONFLICT' if i==37460 else 'EXCLUDE_BOTH_PRESERVE_EXPLICIT_HOLD'))
 hashes.setdefault(s,[]).append(i)
for s,ids in sorted(hashes.items()):
 holds.append(dict(id='text_'+s,original_text_sha256=s,match_scope='ALL_IDENTICAL_ORIGINAL_TEXT',
                   original_roster_eos=sorted(ids),disposition='EXCLUDE_BOTH_IDENTICAL_HELD_ORIGINAL'))
holdpath=ROOT/'handoff/audit/oct26_research/native_format_holds.json'
write(holdpath,dict(schema='P106B_NATIVE_FORMAT_HOLDS_V1',source_sha256=pair.SOURCE_SHA,
 original_explicit_eos_count=1793,identical_original_sha_count=len(hashes),holds=holds,
 original_readback_path=str(p.relative_to(ROOT)),original_readback_sha256=digest(p),
 semantic_badness_confirmed=False,
 conflict_policy='EOS37460 판정 충돌은 양쪽 원형을 유지하고 이번 대조에만 공통 제외한다. 의미 판정의 최신순 우선은 아니다.'))
identity=pair.source_identity()
assert identity['sha256']=='3B891A252C117E10707E6DE75E26A92F1A0FA7A223186ACECD50D9A8F0F83C0F'
report=ROOT/pair.REPORT
assert digest(report)=='40EC5BE8C312B95C764797881334E5B1DC8EEAF24C1A30F4BF02A974B3B5D4D0'
policy=dict(schema=pair.POLICY,approved_train_reuse=True,scope='TRAIN_FORMAT_COMPARISON_ONLY',
 decision_owner='26일17시까지 위임된 총괄의 제어된 형식 대조 결정',
 authority_reference='현재 사용자 CPU/GPU 주도적 연구·미완원장 착수 및 원문/정제본 분리 지시',
 root_f4='handoff/audit/oct26_research/native_format_pair_preflight.md',
 source_code_sha256=identity['sha256'],
 source=dict(path=pair.SOURCE,sha256=pair.SOURCE_SHA),
 report=dict(path=pair.REPORT,sha256=digest(report)),
 tokenizer=dict(path=d['tokenizer']['path'],sha256=d['tokenizer']['sha256']),
 validation=dict(path=d['external_val']['path'],sha256=d['external_val']['sha256']),
 holds=dict(path=str(holdpath.relative_to(ROOT)),sha256=digest(holdpath)),
 minimum_ids_per_arm=600047616,full_semantic_review=False,
 review_queue_policy='PRESERVE_NOT_AUTOMATIC_HOLD',reserved_action='EXCLUDE_BOTH',
 original_source_kind='PRIOR_NATIVE_TRAIN_REUSE',
 semantic_review_claim='형식 파생본이며 기사 내용/사실/권리의 전수 검수 완료가 아니다.',
 original_document_identity='EOS_CACHE_SEGMENTS_NOT_ORIGINAL_URL_DOCUMENTS',
 global_document_leakage='UNVERIFIED',near_duplicate_decontamination='NOT_ESTABLISHED',
 benchmark_training=False,
 canonical_benchmark_answers_added=0,
 known_hold_action='명시 보류와 동일한 원문 SHA 전부를 두팔에서 공통 제외',
 preserved_conflict_count=1,
 canonical_originals_mutated=False,
 training_status='NOT_RUN',
 output='data_cache/p106b_native_format_pair_v1_20261026_s1337')
policypath=ROOT/'handoff/audit/oct26_research/native_format_pair_policy.json'
write(policypath,policy)
pair.metadata(str(policypath.relative_to(ROOT)))
receipt=dict(schema='P106B_NATIVE_FORMAT_POLICY_ROOT_READBACK_V1',assets_rehashed=len(assets),
 assets_bytes=sum(x['bytes'] for x in assets),assets=assets,original_positions=1793,
 original_text_sha_groups=len(hashes),hold_entries=len(holds),source_code_sha256=identity['sha256'],
 policy_path=str(policypath.relative_to(ROOT)),policy_sha256=digest(policypath),
 holds_path=str(holdpath.relative_to(ROOT)),holds_sha256=digest(holdpath),
 source_whole_hash_in_this_step=False,large_candidate_all_shards_in_this_step=False,
 actual_two_pool_build='NOT_RUN',new_model_training=0)
write(ROOT/'handoff/audit/oct26_research/native_format_policy_root_readback.json',receipt)
print(json.dumps({k:v for k,v in receipt.items() if k!='assets'},ensure_ascii=False,indent=2))

