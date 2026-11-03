"""Archive bounded recovery evidence with the existing explicit-save helpers."""
from pathlib import Path
from collections import Counter
import ast
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

reuse = AUDIT / 'prepare_exact_followup_checkpoint_v3.py'
tree = ast.parse(reuse.read_text(encoding='utf-8'))
definitions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in {'git', 'pin', 'copy'}]
assert {n.name for n in definitions} == {'git', 'pin', 'copy'}
exec(compile(ast.Module(body=definitions, type_ignores=[]), str(reuse), 'exec'), globals())
head = git('rev-parse', 'HEAD').decode().strip()
assert head == '767f408e8af1c0e85c39d6b747c822aec97f88cf'
branch = git('branch', '--show-current').decode().strip()
assert not git('diff', '--cached', '--name-only', '-z')
archive = AUDIT / 'exact_followup_progress_archive_v7'
assert not archive.exists()
copies, metadata, reused, snapshots = [], [], [], []
for group, version in [('remaining_literal_full_counter_v1', 'v18'),
                       ('remaining_field_title_page_001_counter_v1', 'v5'),
                       ('remaining_field_title_page_002_counter_v1', 'v4'),
                       ('remaining_field_title_page_003_counter_v1', 'v1')]:
    path = inv.BASE / (group + '_snapshots') / version / 'complete.json'
    copies.append(copy(path, archive / group / ('snapshot_' + version + '_complete.json')))
    snapshot = inv.cache.read(path)
    snapshots.append({'cohort': group, 'version': version, 'counts': snapshot.get('counts', {})})
    for shard in snapshot['shards']:
        metadata.append(pin(ROOT / shard['path']))

roles = ('context_controls', 'context_hangul', 'context_latin', 'historical_review', 'legacy_review')
cohort = 'remaining_literal_full_counter_v1'
for role in roles:
    for guide in sorted((inv.BASE / 'agents' / role / cohort).glob('ROOT_*.md')):
        old = AUDIT / 'exact_followup_progress_archive_v5' / cohort / role / guide.name
        if old.is_file() and inv.file_sha(old) == inv.file_sha(guide):
            reused.append(pin(old))
        else:
            copies.append(copy(guide, archive / cohort / role / guide.name))
    directory = inv.BASE / 'agents' / role
    for name in ('ROOT_OTHER_TYPES_PHASE_AUTHORIZATION_V1.md',
                 'ROOT_REVIEW_WORKFLOW_CONTINUITY_V2.md', 'ROOT_REVIEW_WORKFLOW_CONTINUITY_V3.md'):
        copies.append(copy(directory / name, archive / 'role_guides' / role / name))
    groups = ['root11_ordered_corrections_v1', 'root11_ordered_additional_corrections_v1',
              'root11_birth_1031233_correction_v1', 'root11_birth_1052119_correction_v1']
    groups += ['root11_birth_' + digits + '_correction_v2'
               for digits in ('104207', '1056327', '1056993', '1060163', '106989')]
    for group in groups:
        folder = directory / group
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob('*.md')):
            copies.append(copy(path, archive / group / role / path.name))
        for path in sorted(folder.glob('*.txt')):
            metadata.append(pin(path))

for name in ('ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V7.json',
             'ROOT_LITERAL_REVIEWED_NONADMISSIONS_V2.json',
             'WORKING_COPY_HISTORY_INCIDENT_RECONCILIATION_V1.json',
             'LUNA_TEMP_PATH_BOUNDARY_INCIDENT_19916_V1.json',
             'OUTPUT_HEADING_80_BINDINGS_VERIFIED_V2.json',
             'LITERAL_SAVED_ROW_PROGRESS_OBSERVATION_V1.json'):
    metadata.append(pin(AUDIT / name))
inv.write_json(AUDIT / 'EXACT_FOLLOWUP_PROGRESS_ARCHIVE_V7.json', {
    'status': 'BOUNDED_NEW_REVIEW_AND_RECOVERY_EVIDENCE_NOT_CORPUS_BODIES',
    'rows': copies, 'unchanged_prior_guides_reused': reused, 'snapshots': snapshots,
    'goal_complete': False, 'source_data_changed': False})
inv.write_json(AUDIT / 'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V7.json', {
    'status': 'HASH_INDEX_ONLY_DERIVED_LOCAL_BODIES_AND_REVIEW_SHARDS', 'rows': metadata,
    'prior_large_index': pin(AUDIT / 'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V6.json'),
    'prior_large_objects_rehashed': False, 'source_bodies_staged': False,
    'reused_copy_helpers': pin(reuse)})

relative = str(AUDIT.relative_to(ROOT))
changed = set()
for args in [('ls-files', '--others', '--exclude-standard', '-z', '--', relative),
             ('diff', '--name-only', '-z', '--', relative)]:
    changed.update(value.decode() for value in git(*args).split(bytes([0])) if value)
explicit = []
for name in sorted(changed):
    path = ROOT / name
    assert path.is_relative_to(AUDIT) and not path.is_symlink()
    if not path.is_file() or not 0 < path.stat().st_size < 20_000_000:
        continue
    small = path.parent == AUDIT and (path.suffix in {'.py', '.md'} or
            path.suffix == '.json' and path.stat().st_size < 500_000)
    reviewed = path.is_relative_to(AUDIT / 'exact_cohort_review_archive_v1') and path.suffix == '.md'
    if small or reviewed or path.is_relative_to(archive):
        explicit.append(pin(path))
explicit.append(pin(ROOT / 'handoff/WIP_20261027_작업원장.md'))
assert len({row['path'] for row in explicit}) == len(explicit)
message = AUDIT / 'EXACT_FOLLOWUP_PROGRESS_COMMIT_MESSAGE_V7.txt'
body = chr(10).join([
    '데이터: 출력 연결 오류와 잔여 의미 검토를 보완한다', '',
    '- 실제 저장 리뷰와 본문은 literal snapshot18 및 field 세 페이지의 동결 집계에 연결한다.',
    '- 출력 표제 두 형식의 연결 오류80건을 리뷰 원형과 본문SHA로 검산하고7시험 통과를 기록한다.',
    '- ROOT11의 독립 전문15건에서 찾은 기존오류10건의 새 수정본문까지 검토하고 미채택 상태를 명시한다.',
    '- 잔여flag570건과 출생독립2차 전량검토 및 전체 잔여정제는 계속 진행한다.',
    '- 중복 읽기와 경로오류의 병목을 줄이고 범위 밖tmp기록 및 이전 사본이력의 한계를 보존한다.',
    '- 대량 본문과 캐시는 로컬SHA색인으로 연결하고 보호자료와 타세션 변경을staging하지 않는다.',
    '- 관리goal의blocked 표시와 실제 진행상태를 구분하며 중간저장을 완료나 일시중지로 처리하지 않는다.', ''])
with message.open('x', encoding='utf-8') as stream:
    stream.write(body)
manifest = AUDIT / 'EXACT_FOLLOWUP_PROGRESS_SAVE_MANIFEST_V7.json'
inv.write_json(manifest, {'expected_head': head, 'branch': branch, 'rows': explicit,
    'excluded_source_data': True, 'excluded_large_data': True, 'goal_complete': False})
print(json.dumps({'manifest': str(manifest.relative_to(ROOT)), 'expected_head': head, 'branch': branch,
    'paths': len(explicit) + 1, 'bytes': sum(row['bytes'] for row in explicit) + manifest.stat().st_size,
    'archived_evidence': len(copies), 'reused_prior_guides': len(reused),
    'local_hash_rows': len(metadata), 'kinds': dict(Counter(Path(row['path']).suffix for row in explicit)),
    'index_empty': True}, ensure_ascii=False))
