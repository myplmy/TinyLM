"""Publish unchanged initial bodies so scoped reading need not block editing."""
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

group = 'birth_root11_independent_v1'
source_path = inv.BASE / group / 'manifest.json'
manifest = inv.cache.read(source_path)
contract_path = AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
contract = inv.cache.read(contract_path)
rows = [r for r in manifest['rows'] if r['role'] == 'context_controls']
assert len(rows) == 1354
assert not ({r['id'] for r in rows} & set(contract['restricted_ids']))
assert not ({r['original']['sha256'] for r in rows} & set(contract['restricted_hashes']))
directory = inv.BASE / 'agents/context_controls' / group
guide = directory / 'ROOT_UNCHANGED_INITIAL_COPIES_V1.md'
receipt = AUDIT / 'BIRTH_CONTROLS_INITIAL_COPIES_VERIFIED_V1.json'
assert not guide.exists() and not receipt.exists()
targets = {}
for row in rows:
    assert re.fullmatch(r'(?:expanded_train|validation):[0-9]+', row['id'])
    target = directory / (row['id'].replace(':', '_') + '_initial_candidate_v1.txt')
    assert not target.exists() and not target.is_symlink()
    targets[row['id']] = target
copies = []
for row in rows:
    source = ROOT / row['candidate']['path']
    assert source.parent == inv.BASE / group / 'inputs'
    assert not source.is_symlink() and inv.file_sha(source) == row['candidate']['sha256']
    data = source.read_bytes()
    assert 0 < len(data) < 20_000_000
    target = targets[row['id']]
    with target.open('xb') as stream:
        stream.write(data)
    assert inv.file_sha(target) == row['candidate']['sha256']
    copies.append({'id': row['id'], 'source': row['candidate'],
        'initial_copy': {'path': str(target.relative_to(ROOT)), 'sha256': row['candidate']['sha256']},
        'unchanged': True, 'luna_revision': False, 'root_admitted': False})
lines = ['# 변경 없는 초기 본문 사본과 고정 명령 사용', '',
    '총괄이 정확한 자기 배정1354건의 고정candidate 바이트를 이 자기 폴더에 그대로 복사하고 SHA를 검산했다.',
    '이 사본은 새 정제본이나 채택 결과가 아니다. 원문 판독은 계속 TASK의 고정reader로 한다.',
    '자기 initial_candidate 사본과 자기 새 TXT/MD는 직접 읽고 비교할 수 있다. 수정은 별도의 아직 없는 새 버전 TXT로만 쓴다.',
    '초기사본을 덮지 않으며, 같은 내용 그대로면 원래candidate를ACCEPT하고 복제본을수정으로세지않는다.',
    '아래 목록 외 다른역할/원형/외부파일을cp하거나Python으로읽지 않는다. 코드·해시·시험·웹·Git·모델 권한은 없다.',
    '고정reader문서의 한 줄은 Python 실행파일을 이미 포함하는 완결명령이다. cmd앞에 Python을 다시 붙이지 않는다.',
    '예전 명령을 재구성하지 말고 현재 TASK의 완결명령을 tools.exec_command의cmd값으로 그대로 쓴다. 도구 호출은 원문 코드의 실행이 아니다.', '']
lines += ['- ' + r['id'] + ': ' + str(ROOT / r['initial_copy']['path']) for r in copies]
with guide.open('x', encoding='utf-8') as stream:
    stream.write(chr(10).join(lines) + chr(10))
assert guide.stat().st_size < 20_000_000
inv.write_json(receipt, {'status': 'UNCHANGED_INITIAL_BODY_COPIES_VERIFIED_NOT_NEW_CLEANED_TEXT',
    'rows': copies, 'sources': 1354, 'guide': {'path': str(guide.relative_to(ROOT)), 'sha256': inv.file_sha(guide)},
    'input_pins': {str(p.relative_to(ROOT)): inv.file_sha(p) for p in
        (source_path, contract_path, Path(__file__).resolve())},
    'root_authored_cleaned_bodies': 0, 'cache_admitted': 0, 'goal_complete': False})
print(json.dumps({'unchanged_initial_copies': 1354, 'guide': str(guide), 'new_cleaned_bodies': 0, 'admitted': 0}))
