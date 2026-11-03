"""Copy exact assigned inputs for editing without authoring any cleaned prose."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

group = 'remaining_literal_full_counter_v1'
manifest_path = inv.BASE / group / 'manifest.json'
snapshot_path = inv.BASE / (group + '_snapshots/v9/complete.json')
manifest = inv.cache.read(manifest_path)
by_id = {row['id']: row for row in manifest['rows']}
contract = inv.cache.read(AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json')
pending = []
for pin in inv.cache.read(snapshot_path)['shards']:
    path = ROOT / pin['path']
    assert inv.file_sha(path) == pin['sha256']
    pending.extend(row['id'] for row in inv.cache.read(path)
                   if row.get('role') == 'context_hangul' and row.get('status') == 'TEXT_ADJUDICATION_NOT_ADMISSION')
assert len(pending) == len(set(pending)) == 17
directory = inv.BASE / 'agents/context_hangul' / group
aliases = directory / 'root_literal_reopen_inputs_v1'
assert not aliases.exists()
aliases.mkdir()
records = []
lines = ['# 옛 한글 literal 미결의 정확 입력 사본과 새 작업 사본', '',
         '아래 17개 자기배정 원문/후보 사본은 canonical 입력과 바이트가 같다. 입력 사본은 읽기 전용이다.',
         'working 경로만 첫 새 리뷰를 기록하기 전 편집 가능하다. 리뷰에 연결한 뒤에는 기존 버전을 덮지 말고 새 버전을 쓴다.',
         'reader stdout에는 프레임/표제가 있으므로 그것을 새 원문 TXT로 오인해 저장하지 않는다.',
         '다른 역할/보호자료/코드/JSON/임의 Python 권한은 없다. 실제 내용 정제는 Luna가 수행한다.', '']
for ident in pending:
    row = by_id[ident]
    assert row['role'] == 'context_hangul'
    assert ident not in contract['restricted_ids']
    assert row['original']['sha256'] not in contract['restricted_hashes']
    assert row['original']['sha256'] == row['original_text_sha256']
    result = {'id': ident, 'files': {}}
    lines.append('## ' + ident)
    for kind in ('original', 'candidate'):
        source = ROOT / row[kind]['path']
        assert source.is_file() and not source.is_symlink()
        assert inv.file_sha(source) == row[kind]['sha256']
        data = source.read_bytes()
        assert 0 < len(data) < 20_000_000
        target = aliases / (ident.replace(':', '_') + '_' + kind + '.txt')
        with target.open('xb') as stream:
            stream.write(data)
        assert inv.file_sha(target) == row[kind]['sha256']
        target.chmod(0o444)
        result['files'][kind] = {'path': str(target.relative_to(ROOT)), 'sha256': row[kind]['sha256']}
        lines.append(kind + ': ' + str(target))
        if kind == 'candidate':
            working = directory / (ident.replace(':', '_') + '_literal_rootclosure_20261103_v1.txt')
            with working.open('xb') as stream:
                stream.write(data)
            assert inv.file_sha(working) == row[kind]['sha256']
            result['working'] = {'path': str(working.relative_to(ROOT)), 'initial_sha256': row[kind]['sha256']}
            lines.append('working: ' + str(working))
    lines.append('')
    records.append(result)
scope = directory / 'ROOT_LITERAL_REOPEN_EXACT_COPIES_V1.md'
with scope.open('x', encoding='utf-8') as stream:
    stream.write(chr(10).join(lines) + chr(10))
inv.write_json(AUDIT / 'HANGUL_LITERAL_REOPEN_EXACT_COPIES_V1.json', {
    'status': 'EXACT_ASSIGNED_BYTES_COPIED_NOT_CLEANED_PROSE', 'rows': records,
    'scope': {'path': str(scope.relative_to(ROOT)), 'sha256': inv.file_sha(scope)},
    'input_pins': {str(path.relative_to(ROOT)): inv.file_sha(path) for path in (manifest_path, snapshot_path, Path(__file__))},
    'source_or_candidate_changed': False, 'cleaned_prose_authored_by_root': 0,
    'goal_complete': False, 'training_authorized': False})
print(json.dumps({'sources': len(records), 'readonly_input_copies': len(records) * 2, 'new_working_copies': len(records)}))
