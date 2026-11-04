"""Freeze current owned small evidence; reuse explicit-save primitives directly."""
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
assert head == '2883463c1d3f8b15bcfa3d9ee77a52e466ec6b52'
branch = git('branch', '--show-current').decode().strip()
assert branch and not git('diff', '--cached', '--name-only', '-z')
archive = AUDIT / 'exact_followup_progress_archive_v15'
assert not archive.exists()
copies, reused, metadata = [], [], []
previous_path = AUDIT / 'EXACT_FOLLOWUP_PROGRESS_ARCHIVE_V14.json'
previous = inv.cache.read(previous_path)
prior_archives = {}
for row in previous['rows']:
    prior_archives[row['archive']['sha256']] = row['archive']
for row in previous.get('unchanged_prior_guides_reused', []):
    item = row.get('archive', row)
    prior_archives[item['sha256']] = item

progress_path = AUDIT / 'RESUME_PROGRESS_AND_SPEED_20261104_V12.json'
progress = inv.cache.read(progress_path)
assert progress['field_saved'] == 2163 and progress['combined_first_review_missing'] == 66236
assert progress['field_review_binding_errors'] == 0 and not progress['whole_goal_complete']
snapshots = [('remaining_literal_full_counter_v1', 'v20')]
snapshots += [(f'remaining_field_title_page_{int(page):03}_counter_v1', version)
              for page, version in progress['field_versions'].items()]
snapshots += [('birth_root11_independent_v1', 'v30')]
frozen_snapshots = []
for cohort, version in snapshots:
    path = inv.BASE / (cohort + '_snapshots') / version / 'complete.json'
    value = inv.cache.read(path)
    assert value['root_adopted'] == value['cache_admitted'] == 0 and not value['errors']
    archive_one(path, archive / cohort / ('snapshot_' + version + '_complete.json'))
    metadata.extend(pin(ROOT / item['path']) for item in value['shards'])
    frozen_snapshots.append(dict(cohort=cohort, version=version, counts=value['counts'],
                                 coverage=value['coverage'], needs_root=value['needs_root']))
for version, count in [('v13', 5), ('v15', 2)]:
    path = inv.BASE / 'remaining_field_title_page_001_counter_v1_snapshots' / version / 'complete.json'
    value = inv.cache.read(path)
    assert len(value['errors']) == count
    archive_one(path, archive / 'preserved_field001_rejections' / version / 'complete.json')
    metadata.extend(pin(ROOT / item['path']) for item in value['shards'])

roles = ('context_controls', 'context_hangul', 'context_latin', 'historical_review', 'legacy_review')
for role in roles:
    for name in ('ROOT_FIELD_SHORT_READER_ENTRY_V1.md', 'ROOT_DIFF_READING_BOUNDARIES_V1.md'):
        path = inv.BASE / 'agents' / role / name
        archive_one(path, archive / 'role_guides' / role / name)
    for page in range(1, 37):
        path = inv.BASE / 'agents' / role / f'remaining_field_title_page_{page:03}_counter_v1/ROOT_UNCHANGED_INITIAL_COPIES_V1.md'
        archive_one(path, archive / 'field_initial_copy_guides' / role / f'page_{page:03}' / path.name)
for role in ('context_controls', 'context_latin'):
    path = inv.BASE / 'agents' / role / 'birth_root11_independent_v1/ROOT_SHORT_READER_ENTRY_V1.md'
    archive_one(path, archive / 'birth_short_guides' / role / path.name)
for role, name in [('context_hangul', 'ROOT_85646_CORRECTION_SCOPE_V1.md'),
                   ('legacy_review', 'ROOT_63976_CORRECTION_SCOPE_V1.md')]:
    path = inv.BASE / 'agents' / role / name
    archive_one(path, archive / 'correction_guides' / role / name)
path = inv.BASE / 'agents/context_latin/birth_root11_independent_v1/ROOT_COMPLETE_PACKET_HEADER_CLARIFICATION_V1.md'
archive_one(path, archive / 'birth_header_scope_guide' / path.name)
for task in (253, 256, 262):
    path = inv.BASE / 'agents/context_latin/birth_root11_independent_v1' / f'execution_error_note_task{task}_v1.md'
    archive_one(path, archive / 'preserved_execution_errors' / path.name)
for name in ('hold-c-v1', 'hold-l-v1', 'hold-c-field-v1', 'hold-l-field-v1',
             'hold-h-field-v1', 'hold-j-field-v1', 'hold-g-field-v1'):
    archive_one(ROOT / 'tmp' / name, archive / 'fixed_reader_short_entries' / name)
for name in ('FIELD_SHORT_READER_CPU_TESTS_20261104_V1.log',
             'FIELD_CONTROLS_INITIAL_COPIES_BUILD_V1.log', 'FIELD_LATIN_INITIAL_COPIES_BUILD_V1.log',
             'FIELD_HANGUL_INITIAL_COPIES_BUILD_V1.log', 'FIELD_HISTORICAL_INITIAL_COPIES_BUILD_V1.log',
             'FIELD_LEGACY_INITIAL_COPIES_BUILD_V1.log'):
    archive_one(AUDIT / name, archive / 'tool_logs' / name)

delivery_path = inv.BASE / 'birth_root11_input_delivery_gated_v1/v20/complete.json'
delivery = inv.cache.read(delivery_path)
assert not delivery['failures'] and delivery['raw_errors'] == 0
assert delivery['counts']['INPUT_DELIVERED_BEFORE_REVIEW'] == 1712
archive_one(delivery_path, archive / 'input_delivery_gated_v20/complete.json')
for item in delivery['event_shards']:
    path = ROOT / item['path']
    assert inv.file_sha(path) == item['sha256']
    archive_one(path, archive / 'input_delivery_gated_v20/event_archive' / path.name)
metadata.extend(pin(ROOT / item['path']) for item in delivery['shards'])
for directory, count in [('field_short_reader_registries_v1', 108),
                         ('field_birth_roles_short_reader_registries_v1', 72)]:
    paths = sorted((AUDIT / directory).glob('*.json'))
    assert len(paths) == count
    metadata.extend(pin(path) for path in paths)
metadata += [pin(ROOT / 'tmp/COORD_HOLD_01a17740.md'), pin(previous_path), pin(frozen),
             pin(archive_source), pin(progress_path)]
inv.write_json(AUDIT / 'EXACT_FOLLOWUP_PROGRESS_ARCHIVE_V15.json', {
    'status': 'CURRENT_SMALL_METADATA_AND_REVIEW_ARCHIVE_NOT_CORPUS_BODIES',
    'rows': copies, 'unchanged_prior_guides_reused': reused, 'snapshots': frozen_snapshots,
    'source_data_changed': False, 'negative_field001_snapshots_preserved': ['v13', 'v15'],
    'goal_complete': False})

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
inv.write_json(AUDIT / 'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V15.json', {
    'status': 'HASH_INDEX_ONLY_LOCAL_REVIEW_SHARDS_AND_READER_REGISTRIES', 'rows': metadata,
    'prior_large_index': pin(AUDIT / 'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V14.json'),
    'prior_large_objects_rehashed': False, 'source_bodies_staged': False,
    'readers_regeneratable_from_pinned_existing_manifests': True})
message = AUDIT / 'EXACT_FOLLOWUP_PROGRESS_COMMIT_MESSAGE_V15.txt'
text = chr(10).join(['데이터: 생년 보완 종결과 본문 검토 2163건을 저장한다', '',
    '- 생년2707전량의최종고립파이프보완과34문맥범위종결근거를연결한다.',
    '- 소실조건식직접의존단락H와두문서의실제UTF8/끝LF차이를검산한다.',
    '- 필드2163유효저장과과거경로거부/미완TXT거부를구분해동결한다.',
    '- 다섯역할18237원형동일초기사본의범위와11240개신규독립검산을보존한다.',
    '- 공식H110173과미채택리뷰/미저장66236고유를구분하고속도한계를기록한다.',
    '- 원형·대량본문/캐시·보호자료·타세션dirtyflag·push/PR을저장대상에서제외한다.',
    '- 중간저장뒤전량큐/검증을계속하며완료·일시중지·학습승인으로바꾸지않는다.', ''])
with message.open('x', encoding='utf-8') as stream:
    stream.write(text)
changed.update(str(path.relative_to(ROOT)) for path in
               (AUDIT / 'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V15.json', message))
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
manifest = AUDIT / 'EXACT_FOLLOWUP_PROGRESS_SAVE_MANIFEST_V15.json'
inv.write_json(manifest, dict(expected_head=head, branch=branch, rows=explicit,
                             excluded_source_data=True, excluded_large_data=True, goal_complete=False))
print(json.dumps(dict(manifest=str(manifest.relative_to(ROOT)), expected_head=head, branch=branch,
                      paths=len(explicit)+1, bytes=sum(row['bytes'] for row in explicit)+manifest.stat().st_size,
                      archived_evidence=len(copies), reused_evidence=len(reused), local_hash_rows=len(metadata),
                      kinds=dict(Counter(Path(row['path']).suffix for row in explicit)), index_empty=True), ensure_ascii=False))
