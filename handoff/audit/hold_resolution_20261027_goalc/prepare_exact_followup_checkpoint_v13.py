"""Freeze current owned metadata with the existing explicit-save primitives."""
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
head = git('rev-parse', 'HEAD').decode().strip()
assert head == '5959b15f42d9db35817ddf78f1296622e08c5940'
branch = git('branch', '--show-current').decode().strip()
assert branch and not git('diff', '--cached', '--name-only', '-z')
archive = AUDIT / 'exact_followup_progress_archive_v13'
assert not archive.exists()
copies, reused, metadata = [], [], []
previous_path = AUDIT / 'EXACT_FOLLOWUP_PROGRESS_ARCHIVE_V12.json'
previous = inv.cache.read(previous_path)
prior_archives = {}
for row in previous['rows']:
    prior_archives[row['archive']['sha256']] = row['archive']
for row in previous.get('unchanged_prior_guides_reused', []):
    item = row.get('archive', row)
    prior_archives[item['sha256']] = item


def archive_one(source, target):
    item = pin(source)
    old = prior_archives.get(item['sha256'])
    if old is not None:
        path = ROOT / old['path']
        assert path.resolve().is_relative_to(AUDIT) and inv.file_sha(path) == old['sha256']
        reused.append(dict(source=item, archive=old))
    else:
        copies.append(copy(source, target))


snapshots = [('remaining_literal_full_counter_v1', 'v20'),
             ('remaining_field_title_page_001_counter_v1', 'v8'),
             ('remaining_field_title_page_002_counter_v1', 'v8'),
             ('remaining_field_title_page_003_counter_v1', 'v6'),
             ('remaining_field_title_page_004_counter_v1', 'v12'),
             ('remaining_field_title_page_005_counter_v1', 'v9'),
             ('remaining_field_title_page_006_counter_v1', 'v6'),
             ('remaining_field_title_page_007_counter_v1', 'v2'),
             ('birth_root11_independent_v1', 'v25')]
frozen_snapshots = []
for cohort, version in snapshots:
    path = inv.BASE / (cohort + '_snapshots') / version / 'complete.json'
    value = inv.cache.read(path)
    assert not value['errors'] and value['root_adopted'] == value['cache_admitted'] == 0
    archive_one(path, archive / cohort / ('snapshot_' + version + '_complete.json'))
    metadata.extend(pin(ROOT / shard['path']) for shard in value['shards'])
    frozen_snapshots.append(dict(cohort=cohort, version=version, counts=value['counts'], coverage=value['coverage'], needs_root=value['needs_root']))

roles = ('context_controls', 'context_hangul', 'context_latin', 'historical_review', 'legacy_review')
for role in roles:
    path = inv.BASE / 'agents' / role / 'ROOT_FIELD_SHORT_READER_ENTRY_V1.md'
    archive_one(path, archive / 'field_short_guides' / role / path.name)
for role in ('context_controls', 'context_latin'):
    path = inv.BASE / 'agents' / role / 'birth_root11_independent_v1/ROOT_SHORT_READER_ENTRY_V1.md'
    archive_one(path, archive / 'birth_short_guides' / role / path.name)
for role, name in [('context_hangul', 'ROOT_85646_CORRECTION_SCOPE_V1.md'),
                   ('legacy_review', 'ROOT_63976_CORRECTION_SCOPE_V1.md')]:
    path = inv.BASE / 'agents' / role / name
    archive_one(path, archive / 'correction_guides' / role / name)
for page in range(1, 37):
    path = inv.BASE / 'agents/context_controls' / f'remaining_field_title_page_{page:03}_counter_v1/ROOT_UNCHANGED_INITIAL_COPIES_V1.md'
    archive_one(path, archive / 'controls_field_initial_copy_guides' / f'page_{page:03}' / path.name)
for name in ('hold-c-v1', 'hold-l-v1', 'hold-c-field-v1', 'hold-l-field-v1',
             'hold-h-field-v1', 'hold-j-field-v1', 'hold-g-field-v1'):
    archive_one(ROOT / 'tmp' / name, archive / 'fixed_reader_short_entries' / name)
for name in ('FIELD_SHORT_READER_CPU_TESTS_20261104_V1.log', 'FIELD_CONTROLS_INITIAL_COPIES_BUILD_V1.log'):
    archive_one(AUDIT / name, archive / 'tool_logs' / name)

delivery_path = inv.BASE / 'birth_root11_input_delivery_gated_v1/v15/complete.json'
delivery = inv.cache.read(delivery_path)
assert not delivery['failures'] and delivery['raw_errors'] == 0
assert delivery['counts']['INPUT_DELIVERED_BEFORE_REVIEW'] == 1534
archive_one(delivery_path, archive / 'input_delivery_gated_v15/complete.json')
for item in delivery['event_shards']:
    path = ROOT / item['path']
    assert inv.file_sha(path) == item['sha256']
    archive_one(path, archive / 'input_delivery_gated_v15/event_archive' / path.name)
metadata.extend(pin(ROOT / shard['path']) for shard in delivery['shards'])
negative_path = inv.BASE / 'birth_root11_input_delivery_gated_v1/v11/complete.json'
negative = inv.cache.read(negative_path)
assert negative['raw_errors'] == 0 and len(negative['failures']) == 1
assert negative['failures'][0]['id'] == 'expanded_train:449324'
archive_one(negative_path, archive / 'input_delivery_gated_v11_negative/complete.json')
metadata.extend(pin(ROOT / item['path']) for item in negative['event_shards'] + negative['shards'])
for directory in ('field_short_reader_registries_v1', 'field_birth_roles_short_reader_registries_v1'):
    paths = sorted((AUDIT / directory).glob('*.json'))
    assert len(paths) == (108 if directory == 'field_short_reader_registries_v1' else 72)
    metadata.extend(pin(path) for path in paths)
metadata += [pin(ROOT / 'tmp/COORD_HOLD_01a17740.md'), pin(previous_path), pin(frozen)]

inv.write_json(AUDIT / 'EXACT_FOLLOWUP_PROGRESS_ARCHIVE_V13.json', {
    'status': 'CURRENT_SMALL_METADATA_AND_REVIEW_ARCHIVE_NOT_CORPUS_BODIES',
    'rows': copies, 'unchanged_prior_guides_reused': reused, 'snapshots': frozen_snapshots,
    'source_data_changed': False, 'goal_complete': False})

relative = str(AUDIT.relative_to(ROOT))
changed = set()
for args in [('ls-files', '--others', '--exclude-standard', '-z', '--', relative),
             ('diff', '--name-only', '-z', '--', relative)]:
    changed.update(value.decode() for value in git(*args).split(bytes([0])) if value)
large_local = []
for name in sorted(changed):
    path = ROOT / name
    assert path.resolve().is_relative_to(AUDIT) and not path.is_symlink()
    if path.is_file() and path.parent == AUDIT and path.suffix == '.json' and path.stat().st_size >= 500_000:
        large_local.append(pin(path))
metadata += large_local
inv.write_json(AUDIT / 'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V13.json', {
    'status': 'HASH_INDEX_ONLY_LOCAL_REVIEW_SHARDS_AND_READER_REGISTRIES', 'rows': metadata,
    'prior_large_index': pin(AUDIT / 'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V12.json'),
    'prior_large_objects_rehashed': False, 'source_bodies_staged': False,
    'readers_regeneratable_from_pinned_existing_manifests': True})
message = AUDIT / 'EXACT_FOLLOWUP_PROGRESS_COMMIT_MESSAGE_V13.txt'
text = chr(10).join(['데이터: 전량 판독 전환과 입력 혼동 교정 근거를 저장한다', '',
    '- 생년독립2529/2707과controls배정1354저장종료, field1758/18237을동결한다.',
    '- 공식잔여H110173과새리뷰저장·22개명시후속보완검산을분리한다.',
    '- 실제누락입력449324와잘못된ID/문단삭제보고의정정·음성원형을보존한다.',
    '- 85646전량대조와단위/기호/조건보완의밖바이트및실제인용을검산한다.',
    '- 기존고정reader의짧은호출과두역할field확장을실제호출/거부로확인한다.',
    '- controls field초기사본3248은동일바이트작업본으로새정제나채택으로세지않는다.',
    '- 전달선결1534행과과거995범위의시각근거한계를분리하고WIP RUN을유지한다.',
    '- 대량본문/캐시·보호자료·타세션변경·push/PR은제외하며전체정제는계속한다.', ''])
with message.open('x', encoding='utf-8') as stream:
    stream.write(text)

changed.update(str(path.relative_to(ROOT)) for path in
               (AUDIT / 'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V13.json', message))
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
manifest = AUDIT / 'EXACT_FOLLOWUP_PROGRESS_SAVE_MANIFEST_V13.json'
inv.write_json(manifest, dict(expected_head=head, branch=branch, rows=explicit,
                             excluded_source_data=True, excluded_large_data=True, goal_complete=False))
print(json.dumps(dict(manifest=str(manifest.relative_to(ROOT)), expected_head=head, branch=branch,
                      paths=len(explicit)+1, bytes=sum(row['bytes'] for row in explicit)+manifest.stat().st_size,
                      archived_evidence=len(copies), reused_evidence=len(reused), local_hash_rows=len(metadata),
                      kinds=dict(Counter(Path(row['path']).suffix for row in explicit)), index_empty=True), ensure_ascii=False))
