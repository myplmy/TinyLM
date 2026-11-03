"""Append one actually read whole-source HOLD; leave pending items distinct."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


prior = AUDIT / 'ROOT_LITERAL_REVIEWED_NONADMISSIONS_V2.json'
result = json.loads(prior.read_text(encoding='utf-8'))
manifest_path = BASE / 'remaining_literal_full_counter_v1/manifest.json'
source = next(r for r in json.loads(manifest_path.read_text())['rows'] if r['id'] == 'expanded_train:323719')
contract = json.loads((AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json').read_text())
assert source['id'] not in contract['restricted_ids'] and source['original']['sha256'] not in contract['restricted_hashes']
original = ROOT / source['original']['path']
assert sha(original) == source['original']['sha256']
raw = original.read_text(encoding='utf-8')
assert len(raw) == 10719 and len(raw.splitlines()) == 96
sidecar = BASE / 'agents/context_controls/remaining_literal_full_counter_v1/hold_323719_v1.md'
assert sidecar.is_file() and len(result['rows']) == 8
result['rows'].append({'id': source['id'], 'role': source['role'], 'original': source['original'],
    'source_ids': source['source_ids'], 'source_ids_sha256': source['source_ids_sha256'],
    'occurrences': source['occurrences'], 'reviewer': 'root', 'full_original_actually_read': True,
    'observation_tool_chunk': '97c649',
    'specific_observation_limit': '동일도구출력의앞323294절은잘렸지만이ID의96줄은처음부터끝까지전부표시돼실제로읽었다.',
    'decision': 'HOLD', 'reviewed_disposition': 'INDIVIDUALLY_REVIEWED_OCR_AND_EXAM_RELATION_DAMAGE',
    'reason': '여러지문·질문·선택지·답안·대화가OCR오인식과누락으로섞여부분보존의독립관계를확정하지못했다. 정답/철자/문장관계를추정복구하지않는다.',
    'sidecar': {'path': str(sidecar.relative_to(ROOT)), 'sha256': sha(sidecar)},
    'raw_original_preserved': True, 'unread_bulk_disposition': False, 'new_prose_authored_by_root': False,
    'root_approved_nonadmission': True, 'cache_admitted': False})
result.update({'status': 'NINE_INDIVIDUAL_FULL_SOURCE_READINGS_NOT_UNREAD_HOLD_RENAMING',
    'unique_sources': 9, 'positions': sum(r['occurrences'] for r in result['rows']),
    'prior': {'path': str(prior.relative_to(ROOT)), 'sha256': sha(prior)}, 'new_roster_or_cache_adoption': 0})
out = AUDIT / 'ROOT_LITERAL_REVIEWED_NONADMISSIONS_V3.json'
with out.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
print(json.dumps({'sources': 9, 'positions': result['positions'], 'adopted': 0}))
