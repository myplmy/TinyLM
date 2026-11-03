"""Save exact current review evidence and full next queues with prior copy guards."""
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

reuse_path = AUDIT / 'prepare_exact_followup_checkpoint_v3.py'
tree = ast.parse(reuse_path.read_text(encoding='utf-8'))
definitions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in {'git', 'pin', 'copy'}]
assert {node.name for node in definitions} == {'git', 'pin', 'copy'}
exec(compile(ast.Module(body=definitions, type_ignores=[]), str(reuse_path), 'exec'), globals())
head = git('rev-parse', 'HEAD').decode().strip()
assert head == '42ca61d0b10e85ab5507d48cca9450563b7a2c9f'
branch = git('branch', '--show-current').decode().strip()
assert not git('diff', '--cached', '--name-only', '-z')
archive = AUDIT / 'exact_followup_progress_archive_v5'
assert not archive.exists()
copies = []
metadata = []
cohort = 'remaining_literal_full_counter_v1'
snapshot_path = inv.BASE / (cohort + '_snapshots/v10/complete.json')
copies.append(copy(snapshot_path, archive / cohort / 'snapshot_v10_complete.json'))
for shard in inv.cache.read(snapshot_path)['shards']:
    metadata.append(pin(ROOT / shard['path']))
for guide in sorted((inv.BASE / cohort).glob('ROOT_*.md')):
    copies.append(copy(guide, archive / cohort / guide.name))
roles = ('context_controls', 'context_hangul', 'context_latin', 'historical_review', 'legacy_review')
for role in roles:
    for guide in sorted((inv.BASE / 'agents' / role / cohort).glob('ROOT_*.md')):
        copies.append(copy(guide, archive / cohort / role / guide.name))
    for name in ('ROOT_ALL_FIELD_PAGE_TASKS_V1.md', 'ROOT_ALL_OTHER_TYPES_PAGE_TASKS_V1.md',
                 'REMAINING_OTHER_TYPES_QUEUE_V1.md'):
        guide = inv.BASE / 'agents' / role / name
        assert guide.is_file()
        copies.append(copy(guide, archive / 'phase_queues' / role / name))
other_path = inv.BASE / 'remaining_other_types_readers_v1/complete.json'
other = inv.cache.read(other_path)
assert other['sources'] == 50162 and len(other['pages']) == 98
for page in other['pages']:
    metadata.append(pin(ROOT / page['path']))
    for role in page['assignments']:
        directory = inv.BASE / 'agents' / role / page['group']
        names = ['START_HERE.md', 'ROOT_IDENTITY_TASK_001_V1.md']
        if role == 'context_controls': names.append('ROOT_SCOPED_INPUT_READER_V1.md')
        for name in names:
            copies.append(copy(directory / name, archive / page['group'] / role / name))
for name in ('remaining_other_types_full_sources_v1/complete.json',
             'remaining_other_types_native_proofs_v1/complete.json',
             'remaining_other_types_readers_v1/complete.json'):
    metadata.append(pin(inv.BASE / name))
for name in ('ROOT_AUTHORED_SELECTIONS_V11.json', 'IDENTICAL_LITERAL_INPUT_READING_PROOFS_V2.json',
             'LITERAL_ROLE_FIXED_READERS_VERIFIED_V2.json'):
    metadata.append(pin(AUDIT / name))
inv.write_json(AUDIT / 'EXACT_FOLLOWUP_PROGRESS_ARCHIVE_V5.json', {
    'status': 'IMMUTABLE_SMALL_REVIEW_AND_QUEUE_EVIDENCE_NOT_SOURCE_BODIES', 'rows': copies,
    'goal_complete': False, 'source_data_changed': False})
inv.write_json(AUDIT / 'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V5.json', {
    'status': 'HASH_INDEX_ONLY_LARGE_LOCAL_INPUTS_AND_SELECTIONS', 'rows': metadata,
    'prior_large_index': pin(AUDIT / 'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V4.json'),
    'prior_large_objects_rehashed': False, 'source_bodies_staged': False,
    'reused_copy_helpers': pin(reuse_path)})
relative = str(AUDIT.relative_to(ROOT))
changed = set()
for args in (('ls-files', '--others', '--exclude-standard', '-z', '--', relative),
             ('diff', '--name-only', '-z', '--', relative)):
    changed.update(value.decode() for value in git(*args).split(bytes([0])) if value)
explicit = []
for name in sorted(changed):
    path = ROOT / name
    assert path.is_relative_to(AUDIT) and not path.is_symlink()
    if not path.is_file() or not 0 < path.stat().st_size < 20_000_000: continue
    top = path.parent == AUDIT
    small = top and (path.suffix in {'.py', '.md'} or path.suffix == '.json' and path.stat().st_size < 500_000)
    reviewed = path.is_relative_to(AUDIT / 'exact_cohort_review_archive_v1') and path.suffix == '.md'
    if small or reviewed or path.is_relative_to(archive): explicit.append(pin(path))
explicit.append(pin(ROOT / 'handoff/WIP_20261027_작업원장.md'))
assert len({row['path'] for row in explicit}) == len(explicit)
body = chr(10).join([
    '데이터: 전량 판독 입력과 오삭제 복구 근거를 저장한다', '',
    '- 잔여 중 보호제외 70191고유의 native 입력 전량일치와 읽기준비를 기록한다.',
    '- 다른유형 50162의 실제 native0 및98페이지/396944파일 준비검산을 보존한다.',
    '- literal snapshot10의1476저장행과317미저장행을 채택·검토완료와 구분한다.',
    '- 역할별 정확TASK색인과 고정reader 및 원문 그대로의 readonly 별칭을 연결한다.',
    '- 질문·gmtime실패조건 오삭제 복구, primary API표제/코드개행 및 실패·정정 이력을 저장한다.',
    '- 대량 원문·정제TXT·캐시는 로컬 SHA색인으로만 연결하고 보호·타세션자료를 보존한다.',
    '- 전체 정제·독립 의미검토·정본 연쇄는 계속하며 goal완료/일시중지/학습승인을 선언하지 않는다.', ''])
message = AUDIT / 'EXACT_FOLLOWUP_PROGRESS_COMMIT_MESSAGE_V5.txt'
with message.open('x', encoding='utf-8') as stream: stream.write(body)
manifest = AUDIT / 'EXACT_FOLLOWUP_PROGRESS_SAVE_MANIFEST_V5.json'
inv.write_json(manifest, {'expected_head': head, 'branch': branch, 'rows': explicit,
    'excluded_source_data': True, 'excluded_large_data': True, 'goal_complete': False})
print(json.dumps({'manifest': str(manifest.relative_to(ROOT)), 'expected_head': head, 'branch': branch,
    'paths': len(explicit) + 1, 'bytes': sum(row['bytes'] for row in explicit) + manifest.stat().st_size,
    'kinds': dict(Counter(Path(row['path']).suffix for row in explicit)), 'archived_evidence': len(copies),
    'local_hash_rows': len(metadata), 'index_empty': True}, ensure_ascii=False))
