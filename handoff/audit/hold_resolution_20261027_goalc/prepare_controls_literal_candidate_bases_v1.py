"""Copy unchanged assigned candidates; the role alone authors cleaned text."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

manifest_path = inv.BASE / 'remaining_literal_full_counter_v1/manifest.json'
manifest = inv.cache.read(manifest_path)
contract = inv.cache.read(AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json')
rows = [r for r in manifest['rows'] if r['role'] == 'context_controls']
assert len(rows) == 357 and len({r['id'] for r in rows}) == 357
assert not ({r['id'] for r in rows} & set(contract['restricted_ids']))
assert not ({r['original']['sha256'] for r in rows} & set(contract['restricted_hashes']))
directory = inv.BASE / 'agents/context_controls/remaining_literal_full_counter_v1'
bases = directory / 'candidate_bases_v1'
bases.mkdir(exist_ok=False)
lines = ['# controls의 원형 후보 복사 명령', '',
    '357개 정확 배정 후보를 총괄이 바이트 변경 없이 복사했다. 정제본 작성/채택 증거가 아니다.',
    '자기 TASK 원문 전문과 후보/차이는 여전히 고정 reader와 identityV2로 먼저 실제 읽는다.',
    '수정이 필요할 때만 해당 cp -n 명령으로 자기 새 working_v1 TXT를 만든다.',
    'ACCEPT는 원래 TASK candidate basename을 그대로 선택하고 동일 TXT 복사를 수정으로 세지 않는다.',
    'catalog는 자기 ID의 정확 블록만 읽는다. 명시한 이 MD의 rg 검색은 허용되며 전역/무경로 검색은 금지다.',
    '원형 base와 자기 새 작업본문의 literal diff/읽기는 실제 변경 검수로 허용한다. base를 변경/삭제하지 않는다.',
    '이미 존재한 TXT/리뷰는 수정하지 말고 새 v2 이상을 사용한다. 바이트 단위 끝 자르기는 금지한다.', '']
copied = []
for row in sorted(rows, key=lambda r:r['id']):
    pin = row['candidate']
    source = ROOT / pin['path']
    assert not source.is_symlink() and source.resolve().is_relative_to((inv.BASE / 'remaining_literal_full_counter_v1/inputs').resolve())
    data = source.read_bytes()
    assert inv.sha(data.decode('utf-8')) == pin['sha256'] == inv.file_sha(source)
    assert 0 < len(data) < 20_000_000
    stem = row['id'].replace(':','_')
    base = bases / (stem + '_candidate_base_v1.txt')
    work = directory / (stem + '_literal_working_v1.txt')
    with base.open('xb') as stream:stream.write(data)
    assert inv.file_sha(base) == pin['sha256']
    lines.extend(['## ' + row['id'], 'candidate SHA-256: ' + pin['sha256'],
        '```bash', 'cp -n ' + str(base) + ' ' + str(work), '```', ''])
    copied.append(dict(id=row['id'], candidate=pin,
        base=dict(path=str(base.relative_to(ROOT)), sha256=inv.file_sha(base)), working_path=str(work.relative_to(ROOT))))
catalog = directory / 'ROOT_LITERAL_CANDIDATE_COPY_COMMANDS_V1.md'
with catalog.open('x', encoding='utf-8') as stream:stream.write(chr(10).join(lines) + chr(10))
inv.write_json(AUDIT / 'CONTROLS_LITERAL_UNCHANGED_CANDIDATE_BASES_V1.json',
    dict(status='UNCHANGED_INPUT_COPIES_NOT_CLEANING', rows=copied,
        catalog=dict(path=str(catalog.relative_to(ROOT)), sha256=inv.file_sha(catalog)),
        manifest_sha256=inv.file_sha(manifest_path), producer_sha256=inv.file_sha(Path(__file__)),
        root_authored_cleaned_bodies=0, protected_bodies_opened=0,
        goal_complete=False, training_authorized=False))
print(json.dumps(dict(unchanged_candidate_bases=len(copied), root_authored_cleaned_bodies=0)))
