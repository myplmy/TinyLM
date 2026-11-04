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
assert head == 'b9259eaba7de799086bec65df12302e5e133deb3'
branch = git('branch', '--show-current').decode().strip()
assert branch and not git('diff', '--cached', '--name-only', '-z')
archive = AUDIT / 'exact_followup_progress_archive_v17'
assert not archive.exists()
copies, reused, metadata = [], [], []
previous_path = AUDIT / 'EXACT_FOLLOWUP_PROGRESS_ARCHIVE_V16.json'
previous = inv.cache.read(previous_path)
prior_archives = {}
for row in previous['rows']:
    prior_archives[row['archive']['sha256']] = row['archive']
for row in previous.get('unchanged_prior_guides_reused', []):
    item = row.get('archive', row)
    prior_archives[item['sha256']] = item

progress_path = AUDIT / 'POST_V15_SCOPE_DELTA_V1.json'
progress = inv.cache.read(progress_path)
assert progress['field_saved_frozen'] == 2810 and progress['combined_first_review_missing'] == 65589
assert progress['field_review_binding_errors'] == 0 and not progress['whole_goal_complete']
diagnostic_path = AUDIT / 'FIELD_BOUND_BODY_DIAGNOSTICS_COMPLETE_V3.json'
diagnostic = inv.cache.read(diagnostic_path)
assert diagnostic['saved_review_rows'] == 2720 and diagnostic['body_pairs_checked'] == 2714
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


# Archive only source-linked sidecars after the ID and original-SHA guards.
receipt_specs = [
    ('ROOT_POST_HOLD_HEADERS_AND_APPLICATION_VERIFIED_V1.json', 'records'),
    ('ROOT_FOUR_NUMERIC_CONTEXT_FOLLOWUPS_VERIFIED_V1.json', 'records'),
    ('ROOT_TWO_V3_NUMERIC_FOLLOWUPS_VERIFIED_V1.json', 'records'),
    ('ROOT_50533_EXACT_DECIMAL_FOLLOWUP_VERIFIED_V1.json', None),
    ('CURRENT_FIELD_WHOLE_HOLD_ADJUDICATIONS_V5.json', 'rows'),
    ('ROOT_163020_AND_96670_SELECTED_RECOVERY_VERIFIED_V1.json', 'records'),
]
for receipt_name, key in receipt_specs:
    receipt_path = AUDIT / receipt_name
    receipt = inv.cache.read(receipt_path)
    metadata.append(pin(receipt_path))
    for row in receipt[key] if key else [receipt]:
        assert row['id'] not in guard['restricted_ids']
        assert row['original']['sha256'] not in guard['restricted_hashes']
        for item_key in ('sidecar', 'note'):
            item = row.get(item_key)
            if item:
                source = ROOT / item['path']
                assert inv.file_sha(source) == item['sha256']
                archive_one(source, archive / 'scoped_followup_sidecars' / row['id'].replace(':', '_') / source.name)

bindings_path = AUDIT / 'NUMERIC_INDEPENDENT_20_REVIEW_BINDINGS_VERIFIED_V1.json'
bindings = inv.cache.read(bindings_path)
assert not bindings['errors'] and len(bindings['rows']) == 20
assert bindings['total_targets'] == 275 and bindings['prior_manual_targets'] == 273
independent_manifest_path = inv.BASE / 'agents/context_controls/numeric_independent_20_v1/manifest.json'
independent_manifest = inv.cache.read(independent_manifest_path)
assert len(independent_manifest['rows']) == 20
for row in independent_manifest['rows']:
    assert row['id'] not in guard['restricted_ids']
    assert row['original']['sha256'] not in guard['restricted_hashes']
metadata.append(pin(bindings_path))
for name, expected_sha in bindings['input_pins'].items():
    source = ROOT / name
    assert inv.file_sha(source) == expected_sha
    if source.is_relative_to(independent_manifest_path.parent) and source.suffix in {'.json', '.md'}:
        archive_one(source, archive / 'numeric_independent_20' / source.name)
old_wrong_sha_review = independent_manifest_path.parent / 'NUMERIC_REVIEW_TASK_002.md'
archive_one(old_wrong_sha_review, archive / 'numeric_independent_20_negative' / old_wrong_sha_review.name)
for receipt_name, note_key in [
    ('ROOT_97960_DRAFT_DELETION_INCIDENT_V1.json', 'incident_note'),
    ('ROOT_158543_INVALID_DRAFT_AND_SELECTED_V2_VERIFIED_V1.json', 'note'),
]:
    receipt_path = AUDIT / receipt_name
    receipt = inv.cache.read(receipt_path)
    assert receipt['id'] not in guard['restricted_ids']
    assert receipt['original']['sha256'] not in guard['restricted_hashes']
    item = receipt[note_key]
    source = ROOT / item['path']
    assert inv.file_sha(source) == item['sha256']
    archive_one(source, archive / 'incident_notes' / source.name)
    metadata.append(pin(receipt_path))

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
    metadata.append(pin(inv.BASE / 'field_bound_body_diagnostics_v3' / name))
metadata += [pin(ROOT / 'tmp/COORD_HOLD_01a17740.md'), pin(previous_path), pin(frozen),
             pin(archive_source), pin(progress_path), pin(diagnostic_path), pin(guard_path)]
inv.write_json(AUDIT / 'EXACT_FOLLOWUP_PROGRESS_ARCHIVE_V17.json', {
    'status': 'OWNED_SMALL_METADATA_REVIEWS_AND_SCOPED_SIDECARS_NOT_CORPUS_BODIES',
    'rows': copies, 'unchanged_prior_guides_reused': reused, 'snapshots': frozen_snapshots,
    'diagnostic_body_pairs': 2714, 'current_field_review_rows': 2810,
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
inv.write_json(AUDIT / 'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V17.json', {
    'status': 'HASH_INDEX_ONLY_LOCAL_REVIEW_SHARDS_AND_DIAGNOSTIC_RECORDS', 'rows': metadata,
    'prior_large_index': pin(AUDIT / 'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V16.json'),
    'prior_large_objects_rehashed': False, 'source_bodies_staged': False,
    'inherited_initial_copy_and_reader_registry_evidence_not_recounted': True})
message = AUDIT / 'EXACT_FOLLOWUP_PROGRESS_COMMIT_MESSAGE_V17.txt'
text = chr(10).join(['데이터: 필드 검토 2810건과 수식·편집 복구 검산을 저장한다', '',
    '- 첫 두 묶음 각 512건과 65589개 고유 원문의 1차 미검토를 구분한다.',
    '- 2714본문 UTF-8·메모 진단과 숫자 문맥 검토의 제한 범위를 보존한다.',
    '- 숫자 독립 20원문과 소실 전제·위키 도식·평탄화 수식 보완을 연결한다.',
    '- 실패 초안과 보고 혼동을 보존하고 실제 선택본의 차이·말미를 검산한다.',
    '- 공식 캐시 H110173과 새 미채택 리뷰, 속도 관측의 한계를 구분한다.',
    '- 원형·대량 본문/캐시·보호 자료·타 세션 변경·push/PR은 제외한다.',
    '- 중간 저장 뒤 전량 큐와 검증을 계속하며 완료·일시중지로 바꾸지 않는다.', ''])
with message.open('x', encoding='utf-8') as stream:
    stream.write(text)
changed.update(str(path.relative_to(ROOT)) for path in
               (AUDIT / 'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V17.json', message))
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
manifest = AUDIT / 'EXACT_FOLLOWUP_PROGRESS_SAVE_MANIFEST_V17.json'
inv.write_json(manifest, dict(expected_head=head, branch=branch, rows=explicit,
                             excluded_source_data=True, excluded_large_data=True, goal_complete=False))
print(json.dumps(dict(manifest=str(manifest.relative_to(ROOT)), expected_head=head, branch=branch,
                      paths=len(explicit)+1, bytes=sum(row['bytes'] for row in explicit)+manifest.stat().st_size,
                      archived_evidence=len(copies), reused_evidence=len(reused), local_hash_rows=len(metadata),
                      kinds=dict(Counter(Path(row['path']).suffix for row in explicit)), index_empty=True), ensure_ascii=False))
