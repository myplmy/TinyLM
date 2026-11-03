"""Reuse the existing exact checkpoint planner for verified delivery evidence."""
from pathlib import Path
import ast

AUDIT = Path(__file__).resolve().parent
frozen = AUDIT / 'prepare_exact_followup_checkpoint_v9.py'
tree = ast.parse(frozen.read_text(encoding='utf-8'))
mapping = {
    'ae2233ac4c8cb05f13a786e1ed798699e07efb31': '45c2d532b82bd1d069d930c005f2c57b51713dcf',
    'exact_followup_progress_archive_v9': 'exact_followup_progress_archive_v10',
    'EXACT_FOLLOWUP_PROGRESS_ARCHIVE_V9.json': 'EXACT_FOLLOWUP_PROGRESS_ARCHIVE_V10.json',
    'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V9.json': 'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V10.json',
    'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V8.json': 'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V9.json',
    'EXACT_FOLLOWUP_PROGRESS_COMMIT_MESSAGE_V9.txt': 'EXACT_FOLLOWUP_PROGRESS_COMMIT_MESSAGE_V10.txt',
    'EXACT_FOLLOWUP_PROGRESS_SAVE_MANIFEST_V9.json': 'EXACT_FOLLOWUP_PROGRESS_SAVE_MANIFEST_V10.json',
}
new_snapshots = [('remaining_literal_full_counter_v1', 'v20'),
    ('remaining_field_title_page_001_counter_v1', 'v8'),
    ('remaining_field_title_page_002_counter_v1', 'v8'),
    ('remaining_field_title_page_003_counter_v1', 'v6'),
    ('remaining_field_title_page_004_counter_v1', 'v7'),
    ('remaining_field_title_page_005_counter_v1', 'v3'),
    ('birth_root11_independent_v1', 'v14')]
message = chr(10).join(['데이터: 입력 전달 검증과 잔여 판독 근거를 저장한다', '',
    '- 필드1231/출생독립1070리뷰의동결연결오류0과공식잔여H110173을구분한다.',
    '- 새고정reader의입력전달선결을CPU20시험/실제CLI로검증하고C115/L086부터적용한다.',
    '- 불변로그접두사본으로75개리뷰의정확패킷전달시각을검증하되의미승인으로쓰지않는다.',
    '- 세출생보완안의원문/새차이/sidecar와허용변경밖바이트를검산하고역법추정오류를정정한다.',
    '- 기존585flag의과거경로292개에서정확리뷰/본문/별도역할배정92개를연결하고소유연쇄의한계를남긴다.',
    '- 원문/대량본문/캐시/보호자료/타세션변경은staging하지않고명시SHA색인으로보존한다.',
    '- 다섯역할과전체정제를계속하며중간저장을goal완료/일시중지/추가300M승인으로바꾸지않는다.', ''])
extra = ['BIRTH_INPUT_DELIVERY_CURRENT_RUNTIME_EVIDENCE_V1.json',
    'BIRTH_INPUT_DELIVERY_READERS_VERIFIED_V1.json', 'BIRTH_INPUT_DELIVERY_CONFIG_V1.json',
    'BIRTH_INPUT_DELIVERY_ACTIVATION_V1.json', 'CURRENT_BIRTH_FOLLOWUP_SOURCE_ADJUDICATION_V1.json',
    'ORDERED_FLAG_OLD_PATH_PROVENANCE_AUDIT_V1.json', 'ORDERED_FLAG_OLD_PATH_PROVENANCE_AUDIT_V2.json',
    'ORDERED_FLAG_EXISTING_REVIEW_REUSE_SUMMARY_V1.json',
    'WIP_EXACT_FOLLOWUP_V21_APPLIED.json', 'WIP_EXACT_FOLLOWUP_V22_APPLIED.json']
archive_extra = '''
for selected_role, number in [('context_controls', 115), ('context_latin', 86)]:
    guide_path = inv.BASE / 'agents' / selected_role / 'birth_root11_independent_v1' / ('ROOT_DELIVERY_READER_TASK_' + str(number).zfill(3) + '_V1.md')
    copies.append(copy(guide_path, archive / 'delivery_reader_first_task_guides' / selected_role / guide_path.name))
test_log = AUDIT / 'INPUT_DELIVERY_GUARD_CPU_TESTS_20261104_V1.log'
copies.append(copy(test_log, archive / 'tool_logs' / test_log.name))
delivery_path = inv.BASE / 'birth_root11_input_delivery_gated_v1' / 'v5' / 'complete.json'
delivery = inv.cache.read(delivery_path)
assert not delivery['failures'] and delivery['counts']['INPUT_DELIVERED_BEFORE_REVIEW'] == 75
copies.append(copy(delivery_path, archive / 'input_delivery_gated_v5' / 'complete.json'))
for delivery_event in delivery['event_shards']:
    path = ROOT / delivery_event['path']
    assert inv.file_sha(path) == delivery_event['sha256']
    copies.append(copy(path, archive / 'input_delivery_gated_v5' / 'event_archive' / path.name))
for delivery_shard in delivery['shards']:
    metadata.append(pin(ROOT / delivery_shard['path']))
'''
counts = dict(snapshots=0, message=0, metadata=0, archive=0)
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if 'snapshots' in targets:
            node.value = ast.parse(repr(new_snapshots), mode='eval').body
            counts['snapshots'] += 1
        if 'message' in targets:
            node.value = ast.Constant(message)
            counts['message'] += 1
        if 'extra_metadata' in targets:
            assert isinstance(node.value, ast.List)
            node.value.elts += [ast.Constant(name) for name in extra]
            counts['metadata'] += 1
        if 'guide_copy_code' in targets:
            assert isinstance(node.value, ast.Constant)
            node.value.value += archive_extra
            counts['archive'] += 1
assert set(counts.values()) == {1}


class Versions(ast.NodeTransformer):
    def visit_Constant(self, node):
        if isinstance(node.value, str) and node.value in mapping:
            return ast.copy_location(ast.Constant(value=mapping[node.value]), node)
        return node


tree = Versions().visit(tree)
ast.fix_missing_locations(tree)
exec(compile(tree, str(frozen), 'exec'), {'__file__': __file__, '__name__': 'delivery_exact_checkpoint'})
