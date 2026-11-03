"""Add per-TASK proof plans; preserve all existing source and assignment bytes."""
from collections import Counter
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(AUDIT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_review_safeguards_v3 as safeguards
from identical_input_reading_v1 import digest, prove_identical

GROUP = 'remaining_literal_full_counter_v1'
OUT = inv.BASE / GROUP
manifest_path = OUT / 'manifest.json'
contract_path = AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
test_path = AUDIT / 'IDENTICAL_INPUT_READING_TEST_RESULT_V1.json'
test = inv.cache.read(test_path)
inv.require(test['process_exit_code'] == 0, 'successful negative contracts required')
inv.require(inv.file_sha(ROOT / test['test']) == test['test_sha256']
    and inv.file_sha(ROOT / test['log']) == test['log_sha256'], 'test evidence changed')
manifest = inv.cache.read(manifest_path)
contract = inv.cache.read(contract_path)
blocked_ids, blocked_hashes = set(contract['restricted_ids']), set(contract['restricted_hashes'])
inv.require(len(manifest['rows']) == 1793, 'exact whole literal type required')
inv.require(not ({row['id'] for row in manifest['rows']} & blocked_ids), 'restricted ID blocked before reads')
inv.require(not ({row['original']['sha256'] for row in manifest['rows']} & blocked_hashes),
    'restricted SHA blocked before reads')
pins = {str(p.relative_to(ROOT)): inv.file_sha(p) for p in [manifest_path, contract_path, test_path,
    AUDIT / 'identical_input_reading_v1.py', AUDIT / 'IDENTICAL_INPUT_READING_SCOPE_V1.md', Path(__file__)]}
for name, expected in manifest['input_pins'].items():
    inv.require(inv.file_sha(ROOT / name) == expected, 'assignment dependency changed')
for name, expected in manifest['source_code_pins'].items():
    inv.require(inv.file_sha(ROOT / name) == expected, 'frozen source code changed')


def read_pin(pin, allowed):
    path = ROOT / pin['path']
    inv.require(not path.is_symlink() and path.resolve().is_relative_to(allowed.resolve()),
        'input left exact source namespace')
    data = path.read_bytes()
    inv.require(digest(data) == pin['sha256'], 'exact assigned bytes changed')
    return data


proofs = {}
totals = Counter()
for row in manifest['rows']:
    ident = row['id']
    if row['original']['sha256'] != row['candidate']['sha256']:
        proofs[ident] = dict(protocol='SEPARATE_COMPLETE_READING_REQUIRED', id=ident,
            original=row['original'], candidate=row['candidate'])
        totals['nonidentical_sources_full_separate_reading'] += 1
        continue
    original = read_pin(row['original'], OUT / 'inputs')
    candidate = read_pin(row['candidate'], OUT / 'inputs')
    packets = [dict(pin, payload=read_pin(pin, OUT / 'reading_packets_v1')) for pin in row['reading_parts']]
    proof = prove_identical(ident, original, candidate, row['original']['sha256'],
        row['candidate']['sha256'], packets)
    proofs[ident] = dict(proof, id=ident, original=row['original'], candidate=row['candidate'])
    totals['byte_identical_sources'] += 1
    totals['all_packet_parts'] += len(packets)
    totals['required_packet_parts'] += len(proof['required_packets'])
    totals['duplicate_only_packet_parts'] += len(proof['duplicate_only_packets'])


def save_new(path, payload):
    data = payload.encode('utf-8')
    inv.require(0 < len(data) < 20_000_000, 'artifact requires split')
    with path.open('xb') as stream: stream.write(data)
    return dict(path=str(path.relative_to(ROOT)), sha256=inv.file_sha(path), bytes=len(data))


plans = []
for role, assigned in manifest['assignments'].items():
    directory = inv.BASE / 'agents' / role / GROUP
    assigned = set(assigned)
    seen = set()
    for task in sorted(directory.glob('TASK_*.md')):
        task_text = task.read_text(encoding='utf-8')
        ids = sorted(safeguards.explicit_task_ids(task_text))
        inv.require(ids and set(ids) <= assigned and not (set(ids) & seen), 'exact TASK assignment differs')
        seen.update(ids)
        lines = ['# 동일 입력 판독 연결: ' + task.stem, '',
            '총괄이 실제 원문/후보 바이트·SHA와 순서 패킷 전체를 검산한 추가 계획이다.',
            '아래 동일성 증명이 있는 ID만 적용한다. 원문 전문은 첫 문자부터 실제 END까지 실제 읽고,',
            'candidate는 정확 바이트 동일성으로 연결하며 full_diff 프레임의 끝까지 읽는다.',
            '이를 원문/후보 두 번의 독립 판독으로 기록하지 않는다. 새 수정 TXT는 전문 재열람과 전체 diff를 계속 확인한다.',
            'TASK의 모든 ID는 각각 리뷰에 포함한다. READING_VIEWS는 경로 인덱스이며 전체 인덱스 EOF의 반복 판독은 불필요하다.',
            '서로 다른 후보는 기존 전문/후보/전체diff와 모든 패킷을 그대로 읽는다.',
            '기존 허용·금지·보호 경계와 다른 역할 접근 금지는 유지한다.',
            'controls는 아래 정확 고정 reader 명령만 사용한다. 다른 역할은 아래 정확 cat 경로를 쓴다.', '']
        for ident in ids:
            row = next(r for r in manifest['rows'] if r['id'] == ident)
            proof = proofs[ident]
            lines.extend(['## ' + ident, 'original SHA-256: ' + row['original']['sha256'],
                'candidate SHA-256: ' + row['candidate']['sha256']])
            if proof['protocol'] != 'EXACT_IDENTICAL_INPUT_READING_V1':
                lines.extend(['서로 다른 입력: 기존 TASK의 모든 입력을 별도로 전문 판독한다.', ''])
                continue
            lines.extend(['실제 바이트 동일·모든 순서 패킷 재구성 일치.',
                '원문 전문 프레임 패킷: ' + str(proof['original_packets']),
                'full_diff 프레임 패킷: ' + str(proof['full_diff_packets']),
                '중복 후보만 포함해 생략 가능한 패킷: ' + str(proof['duplicate_only_packets']),
                '아래 명령은 원문 전체와 최종 diff를 포함한다. 중간 원문 안의 END 문자열을 종료표식으로 삼지 않는다.', '```bash'])
            if role == 'context_controls':
                reader = str(AUDIT / 'read_context_controls_literal_packet_v1.py')
                for number in proof['required_packets']:
                    lines.append('/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B ' + reader
                        + ' --source-id ' + ident + ' --packet ' + str(number) + ' --piece 1')
            else:
                required = [str(ROOT / row['reading_parts'][number - 1]['path']) for number in proof['required_packets']]
                for start in range(0, len(required), 3):
                    lines.append('cat ' + ' '.join(required[start:start + 3]))
            lines.extend(['```', '리뷰 실제 판독범위: 원문 전문 실제 판독 + 후보 바이트동일 증명 연결 + 최종 full_diff 끝 확인.', ''])
        plan = directory / ('ROOT_IDENTITY_' + task.stem + '_V2.md')
        plans.append(dict(save_new(plan, chr(10).join(lines) + chr(10)), role=role,
            task=str(task.relative_to(ROOT)), task_sha256=inv.file_sha(task), ids=ids))
    inv.require(seen == assigned, 'whole role assignment not covered')

result = dict(status='EXACT_BYTES_AND_ORDERED_FRAMES_PROVED_NOT_MEANING_APPROVAL',
    counts=dict(totals), rows=list(proofs.values()), plans=plans, input_pins=pins,
    protected_bodies_opened=0, source_texts_changed=0, candidate_texts_changed=0,
    goal_complete=False, training_authorized=False)
save_new(AUDIT / 'IDENTICAL_LITERAL_INPUT_READING_PROOFS_V2.json',
    json.dumps(result, ensure_ascii=False, indent=2) + chr(10))
print(json.dumps(dict(counts=dict(totals), plans=len(plans), cache_admitted=False)))
