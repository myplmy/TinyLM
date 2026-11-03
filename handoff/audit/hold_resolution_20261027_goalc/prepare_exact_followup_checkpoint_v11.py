"""Reuse the exact planner for the verified negative-row and source followups."""
from pathlib import Path
import ast

AUDIT = Path(__file__).resolve().parent
frozen = AUDIT / 'prepare_exact_followup_checkpoint_v10.py'
tree = ast.parse(frozen.read_text(encoding='utf-8'))
mapping = {
    '45c2d532b82bd1d069d930c005f2c57b51713dcf': '2f811836774ababf680c5d64a0f6c8825280935c',
    'exact_followup_progress_archive_v10': 'exact_followup_progress_archive_v11',
    'EXACT_FOLLOWUP_PROGRESS_ARCHIVE_V10.json': 'EXACT_FOLLOWUP_PROGRESS_ARCHIVE_V11.json',
    'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V10.json': 'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V11.json',
    'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V9.json': 'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V10.json',
    'EXACT_FOLLOWUP_PROGRESS_COMMIT_MESSAGE_V10.txt': 'EXACT_FOLLOWUP_PROGRESS_COMMIT_MESSAGE_V11.txt',
    'EXACT_FOLLOWUP_PROGRESS_SAVE_MANIFEST_V10.json': 'EXACT_FOLLOWUP_PROGRESS_SAVE_MANIFEST_V11.json',
}
snapshots = [('remaining_literal_full_counter_v1', 'v20'),
    ('remaining_field_title_page_001_counter_v1', 'v8'),
    ('remaining_field_title_page_002_counter_v1', 'v8'),
    ('remaining_field_title_page_003_counter_v1', 'v6'),
    ('remaining_field_title_page_004_counter_v1', 'v10'),
    ('remaining_field_title_page_005_counter_v1', 'v5'),
    ('remaining_field_title_page_006_counter_v1', 'v3'),
    ('birth_root11_independent_v1', 'v20')]
message = chr(10).join(['데이터: 잔여 판독과 거부 행 검증 근거를 저장한다', '',
    '- 필드 1382/18237과 생년 독립 1440/2707의 고정 집계 및 공식 잔여 HOLD110173을 구분한다.',
    '- 잘못된 출력 연결 두 행을 격리하는 새 검증기를 CPU28회귀와 실제 음성 스냅샷으로 확인한다.',
    '- 불변 이벤트 접두로 445행의 입력 전달 선결을 검증하고 이를 이해·의미 승인으로 쓰지 않는다.',
    '- 새 네 보완 본문의 조건·단위·원형 인용과 정확 허용 변경 밖 바이트를 대조한다.',
    '- 두 필드 원문의 개별 전체 HOLD와 패킷 분할을 원문 손상으로 오인한 설명의 정정을 기록한다.',
    '- 기존 경고 다섯 건의 이전·현재 리뷰와 본문 소유 연쇄를 찾아 기록 경로390/585를 연결한다.',
    '- 원형·대량본문·캐시·보호자료·타세션 변경은 staging하지 않고 명시 SHA색인으로 보존한다.',
    '- 다섯 역할과 전체 정제를 계속하며 중간 저장을 완료·일시중지·추가300M 승인으로 바꾸지 않는다.', ''])
extra = ['RESUME_PROGRESS_AND_SPEED_20261104_V4.json',
    'CURRENT_FIELD_AND_BIRTH_FOLLOWUP_ADJUDICATIONS_V1.json',
    'CURRENT_FIELD_WHOLE_HOLD_ADJUDICATIONS_V1.json', 'RUNTIME_PRIOR_REVIEW_OUTPUT_CHAIN_V1.json',
    'BIRTH_REJECTED_ROW_GUARD_RUNTIME_EVIDENCE_V1.json',
    'WIP_EXACT_FOLLOWUP_V23_APPLIED.json', 'WIP_EXACT_FOLLOWUP_V24_APPLIED.json']
archive_extra = '''
for selected_role, number in [('context_controls', 115), ('context_latin', 86)]:
    guide_path = inv.BASE / 'agents' / selected_role / 'birth_root11_independent_v1' / ('ROOT_DELIVERY_READER_TASK_' + str(number).zfill(3) + '_V1.md')
    copies.append(copy(guide_path, archive / 'delivery_reader_first_task_guides' / selected_role / guide_path.name))
for name in ['INPUT_DELIVERY_REJECTED_ROW_CPU_TESTS_20261104_V1.log', 'INPUT_DELIVERY_REJECTED_ROW_CPU_TESTS_20261104_V2.log']:
    test_log = AUDIT / name
    copies.append(copy(test_log, archive / 'tool_logs' / test_log.name))
delivery_path = inv.BASE / 'birth_root11_input_delivery_gated_v1' / 'v10' / 'complete.json'
delivery = inv.cache.read(delivery_path)
assert not delivery['failures'] and delivery['raw_errors'] == 0
assert delivery['counts']['INPUT_DELIVERED_BEFORE_REVIEW'] == 445
copies.append(copy(delivery_path, archive / 'input_delivery_gated_v10' / 'complete.json'))
for delivery_event in delivery['event_shards']:
    path = ROOT / delivery_event['path']
    assert inv.file_sha(path) == delivery_event['sha256']
    copies.append(copy(path, archive / 'input_delivery_gated_v10' / 'event_archive' / path.name))
for delivery_shard in delivery['shards']:
    metadata.append(pin(ROOT / delivery_shard['path']))
negative_path = inv.BASE / 'birth_root11_input_delivery_gated_v1' / 'v9' / 'complete.json'
negative = inv.cache.read(negative_path)
assert negative['raw_errors'] == 2 and len(negative['failures']) == 2
copies.append(copy(negative_path, archive / 'input_delivery_gated_v9_negative' / 'complete.json'))
for item in negative['event_shards'] + negative['shards']:
    metadata.append(pin(ROOT / item['path']))
'''
counts = dict(snapshots=0, message=0, metadata=0, archive=0)
for node in ast.walk(tree):
    if not isinstance(node, ast.Assign):
        continue
    targets = [target.id for target in node.targets if isinstance(target, ast.Name)]
    if 'new_snapshots' in targets:
        node.value = ast.parse(repr(snapshots), mode='eval').body
        counts['snapshots'] += 1
    if 'message' in targets:
        node.value = ast.Constant(message)
        counts['message'] += 1
    if 'extra' in targets:
        assert isinstance(node.value, ast.List)
        node.value.elts += [ast.Constant(name) for name in extra]
        counts['metadata'] += 1
    if 'archive_extra' in targets:
        node.value = ast.Constant(archive_extra)
        counts['archive'] += 1
assert set(counts.values()) == {1}


class Versions(ast.NodeTransformer):
    def visit_Constant(self, node):
        if isinstance(node.value, str) and node.value in mapping:
            return ast.copy_location(ast.Constant(value=mapping[node.value]), node)
        return node


tree = Versions().visit(tree)
ast.fix_missing_locations(tree)
exec(compile(tree, str(frozen), 'exec'), {'__file__': __file__, '__name__': 'followup_exact_checkpoint'})
