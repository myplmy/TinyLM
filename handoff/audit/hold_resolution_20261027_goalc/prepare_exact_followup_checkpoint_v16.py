"""Freeze owned progress evidence using the existing exact local-save primitives."""
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

frozen = AUDIT / 'prepare_exact_followup_checkpoint_v3.py'
nodes = [node for node in ast.parse(frozen.read_text(encoding='utf-8')).body
         if isinstance(node, ast.FunctionDef) and node.name in {'git', 'pin', 'copy'}]
assert len(nodes) == 3 and all(not node.decorator_list for node in nodes)
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(frozen), 'exec'), globals())
archive_source = AUDIT / 'prepare_exact_followup_checkpoint_v14.py'
nodes = [node for node in ast.parse(archive_source.read_text(encoding='utf-8')).body
         if isinstance(node, ast.FunctionDef) and node.name == 'archive_one']
assert len(nodes) == 1 and not nodes[0].decorator_list
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(archive_source), 'exec'), globals())
head = git('rev-parse', 'HEAD').decode().strip()
assert head == '9af1110cb20932e0310d0283430f29bd6b22941e'
branch = git('branch', '--show-current').decode().strip()
assert branch and not git('diff', '--cached', '--name-only', '-z')
archive = AUDIT / 'exact_followup_progress_archive_v16'
assert not archive.exists()
copies, reused, metadata = [], [], []
previous_path = AUDIT / 'EXACT_FOLLOWUP_PROGRESS_ARCHIVE_V15.json'
previous = inv.cache.read(previous_path)
prior_archives = {}
for row in previous['rows']:
    prior_archives[row['archive']['sha256']] = row['archive']
for row in previous.get('unchanged_prior_guides_reused', []):
    item = row.get('archive', row)
    prior_archives[item['sha256']] = item

progress_path = AUDIT / 'RESUME_PROGRESS_AND_SPEED_20261104_V13.json'
progress = inv.cache.read(progress_path)
assert progress['field_saved'] == 2332 and progress['combined_first_review_missing'] == 66067
assert progress['field_review_binding_errors'] == 0 and not progress['whole_goal_complete']
diagnostic_path = AUDIT / 'FIELD_BOUND_BODY_DIAGNOSTICS_COMPLETE_V1.json'
diagnostic = inv.cache.read(diagnostic_path)
assert diagnostic['saved_review_rows'] == 2224 and diagnostic['body_pairs_checked'] == 2220
snapshots = [('remaining_literal_full_counter_v1', 'v20'), ('birth_root11_independent_v1', 'v30')]
for view in (progress['field_versions'], diagnostic['versions']):
    snapshots.extend((f'remaining_field_title_page_{int(page):03}_counter_v1', version)
                     for page, version in view.items())
frozen_snapshots = []
for cohort, version in dict.fromkeys(snapshots):
    path = inv.BASE / (cohort + '_snapshots') / version / 'complete.json'
    value = inv.cache.read(path)
    assert value['root_adopted'] == value['cache_admitted'] == 0 and not value['errors']
    archive_one(path, archive / cohort / ('snapshot_' + version + '_complete.json'))
    metadata.extend(pin(ROOT / item['path']) for item in value['shards'])
    frozen_snapshots.append(dict(cohort=cohort, version=version, counts=value['counts'],
                                 coverage=value['coverage'], needs_root=value['needs_root']))

guard_path = AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
guard = inv.cache.read(guard_path)
assert inv.file_sha(guard_path) == 'CE929E1C714E5419A78FF22481A6F990F0B27C813204F4B3B94CC8D58E73D6EF'
for receipt_name, key in [('ROOT_THREE_FIELD_NARROW_FOLLOWUPS_VERIFIED_V1.json', 'rows'),
                          ('ROOT_TWO_FIELD_CODE_FOLLOWUPS_VERIFIED_V1.json', 'records')]:
    path = AUDIT / receipt_name
    receipt = inv.cache.read(path)
    metadata.append(pin(path))
    for row in receipt[key]:
        assert row['id'] not in guard['restricted_ids']
        assert row['original']['sha256'] not in guard['restricted_hashes']
        source = ROOT / row['sidecar']['path']
        assert inv.file_sha(source) == row['sidecar']['sha256']
        archive_one(source, archive / 'scoped_followup_sidecars' / row['id'].replace(':', '_') / source.name)

roles = ('context_controls', 'context_hangul', 'context_latin', 'historical_review', 'legacy_review')
for role in roles:
    for name in ('ROOT_FIELD_SHORT_READER_ENTRY_V1.md', 'ROOT_DIFF_READING_BOUNDARIES_V1.md'):
        path = inv.BASE / 'agents' / role / name
        archive_one(path, archive / 'role_guides' / role / name)
delivery_path = inv.BASE / 'birth_root11_input_delivery_gated_v1/v20/complete.json'
delivery = inv.cache.read(delivery_path)
assert not delivery['failures'] and delivery['raw_errors'] == 0
archive_one(delivery_path, archive / 'input_delivery_gated_v20/complete.json')
metadata.extend(pin(ROOT / item['path']) for item in diagnostic['shards'])
metadata.extend(pin(ROOT / item['path']) for item in delivery['shards'])
for name in ('complete.json',):
    metadata.append(pin(inv.BASE / 'field_bound_body_diagnostics_v1' / name))
metadata += [pin(ROOT / 'tmp/COORD_HOLD_01a17740.md'), pin(previous_path), pin(frozen),
             pin(archive_source), pin(progress_path), pin(diagnostic_path), pin(guard_path)]
inv.write_json(AUDIT / 'EXACT_FOLLOWUP_PROGRESS_ARCHIVE_V16.json', {
    'status': 'OWNED_SMALL_METADATA_REVIEWS_AND_SCOPED_SIDECARS_NOT_CORPUS_BODIES',
    'rows': copies, 'unchanged_prior_guides_reused': reused, 'snapshots': frozen_snapshots,
    'diagnostic_body_pairs': 2220, 'current_field_review_rows': 2332,
    'source_data_changed': False, 'goal_complete': False})

relative = str(AUDIT.relative_to(ROOT))
changed = set()
for args in [('ls-files', '--others', '--exclude-standard', '-z', '--', relative),
             ('diff', '--name-only', '-z', '--', relative)]:
    changed.update(value.decode() for value in git(*args).split(bytes([0])) if value)
for name in sorted(changed):
    path = ROOT / name
    assert path.resolve().is_relative_to(AUDIT) and not path.is_symlink()
    if path.is_file() and path.parent == AUDIT and path.suffix == '.json' and path.stat().st_size >= 500_000:
        metadata.append(pin(path))
inv.write_json(AUDIT / 'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V16.json', {
    'status': 'HASH_INDEX_ONLY_LOCAL_REVIEW_SHARDS_AND_DIAGNOSTIC_RECORDS', 'rows': metadata,
    'prior_large_index': pin(AUDIT / 'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V15.json'),
    'prior_large_objects_rehashed': False, 'source_bodies_staged': False,
    'inherited_initial_copy_and_reader_registry_evidence_not_recounted': True})
message = AUDIT / 'EXACT_FOLLOWUP_PROGRESS_COMMIT_MESSAGE_V16.txt'
text = chr(10).join(['데이터: 필드 검토 2332건과 누락 문맥 보완 근거를 저장한다', '',
    '- 필드 2332개 원문·본문·리뷰 연결과 66067개 1차 미저장을 구분한다.',
    '- 숫자 결합과 미상 피연산자 배정, 실제 코드값 복구의 다섯 보완을 검산한다.',
    '- 2220본문 진단과 숫자 국소 증명, 네 Unicode·스타일 문맥을 보존한다.',
    '- 과거 진단의 정확 계보 네 건을 재생성하고 독립 검산 근거를 연결한다.',
    '- 조건·기준·누락 서지와 인용부호의 후속 미결을 완료로 바꾸지 않는다.',
    '- 기존 캐시 H110173, 새 미채택 리뷰와 속도 관측의 한계를 구분한다.',
    '- 원형·대량 본문/캐시·보호 자료·타 세션 변경·push/PR은 제외한다.',
    '- 중간 저장 뒤 전량 큐와 검증을 계속하며 완료·일시중지로 바꾸지 않는다.', ''])
with message.open('x', encoding='utf-8') as stream:
    stream.write(text)
changed.update(str(path.relative_to(ROOT)) for path in
               (AUDIT / 'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V16.json', message))
explicit = []
for name in sorted(changed):
    path = ROOT / name
    assert path.resolve().is_relative_to(AUDIT) and not path.is_symlink()
    if not path.is_file() or not 0 < path.stat().st_size < 20_000_000:
        continue
    top_small = path.parent == AUDIT and (path.suffix in {'.py', '.md'} or
                 path.suffix in {'.json', '.log'} and path.stat().st_size < 500_000)
    reviewed = path.is_relative_to(AUDIT / 'exact_cohort_review_archive_v1') and path.suffix == '.md'
    if top_small or reviewed or path.is_relative_to(archive) or path == message:
        explicit.append(pin(path))
explicit.append(pin(ROOT / 'handoff/WIP_20261027_작업원장.md'))
assert len({row['path'] for row in explicit}) == len(explicit)
manifest = AUDIT / 'EXACT_FOLLOWUP_PROGRESS_SAVE_MANIFEST_V16.json'
inv.write_json(manifest, dict(expected_head=head, branch=branch, rows=explicit,
                             excluded_source_data=True, excluded_large_data=True, goal_complete=False))
print(json.dumps(dict(manifest=str(manifest.relative_to(ROOT)), expected_head=head, branch=branch,
                      paths=len(explicit)+1, bytes=sum(row['bytes'] for row in explicit)+manifest.stat().st_size,
                      archived_evidence=len(copies), reused_evidence=len(reused), local_hash_rows=len(metadata),
                      kinds=dict(Counter(Path(row['path']).suffix for row in explicit)), index_empty=True), ensure_ascii=False))
