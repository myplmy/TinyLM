"""Reuse the preceding explicit archive/save planner for the next bounded save."""
from pathlib import Path
import ast

AUDIT = Path(__file__).resolve().parent
frozen = AUDIT / 'prepare_exact_followup_checkpoint_v7.py'
tree = ast.parse(frozen.read_text(encoding='utf-8'))
mapping = {
    '767f408e8af1c0e85c39d6b747c822aec97f88cf': '0e237187d722fa9fa63ac195aa58d1e1581301ab',
    'exact_followup_progress_archive_v7': 'exact_followup_progress_archive_v8',
    'EXACT_FOLLOWUP_PROGRESS_ARCHIVE_V7.json': 'EXACT_FOLLOWUP_PROGRESS_ARCHIVE_V8.json',
    'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V7.json': 'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V8.json',
    'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V6.json': 'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V7.json',
    'EXACT_FOLLOWUP_PROGRESS_COMMIT_MESSAGE_V7.txt': 'EXACT_FOLLOWUP_PROGRESS_COMMIT_MESSAGE_V8.txt',
    'EXACT_FOLLOWUP_PROGRESS_SAVE_MANIFEST_V7.json': 'EXACT_FOLLOWUP_PROGRESS_SAVE_MANIFEST_V8.json',
    'ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V7.json': 'ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V10.json',
    'ROOT_LITERAL_REVIEWED_NONADMISSIONS_V2.json': 'ROOT_LITERAL_REVIEWED_NONADMISSIONS_V3.json',
}
snapshots = [('remaining_literal_full_counter_v1', 'v20'),
    ('remaining_field_title_page_001_counter_v1', 'v7'),
    ('remaining_field_title_page_002_counter_v1', 'v7'),
    ('remaining_field_title_page_003_counter_v1', 'v3'),
    ('remaining_field_title_page_004_counter_v1', 'v1'),
    ('birth_root11_independent_v1', 'v4')]
message = chr(10).join(['데이터: 출생 교차 검토와 추가 의미 보완을 저장한다', '',
    '- literal1793의1783본문후보와10개별HOLD를대조하고미결경계/연결오류0을기록한다.',
    '- field709리뷰와출생최종본문독립2차160저장/2547미저장을캐시채택과구분한다.',
    '- 총괄직접21판독에서발견한14문제의새수정본문까지실제검산하고미채택상태를유지한다.',
    '- root/출생독립검토기록의중복을빼고585flag중147기록연결/438기록없음을계수한다.',
    '- 헤더없는리뷰4거부의복구와영화크레딧2건판독오인의바이트검산·철회이력을보존한다.',
    '- 새판독기/배정/초기사본과원형자료는SHA색인으로잇고대량본문/보호자료/타세션변경은제외한다.',
    '- 전체정제는진행중이며중간저장을완료/일시중지/학습승인으로바꾸지않는다.', ''])
snapshot_loops = message_assignments = group_lists = metadata_lists = 0
extra_metadata = ['LITERAL_FULL_FIRST_READING_RECONCILIATION_V1.json',
    'BIRTH_ROOT11_SECOND_READING_PREPARATION_V1.json', 'BIRTH_ROOT11_SCOPED_READER_VERIFIED_V1.json',
    'BIRTH_CONTROLS_INITIAL_COPIES_VERIFIED_V1.json', 'ROOT11_AND_BIRTH_SAVED_REVIEW_COVERAGE_BRIDGE_V2.json',
    'FIELD_PAGE002_HEADER_FOUR_REJECTS_RECOVERY_V1.json',
    'BIRTH_READER_INITIAL_MOVIE_CREDIT_DISCREPANCY_CHECK_V1.json',
    'DERIVED_WRITE_INCIDENTS_RECONCILIATION_20261103_V2.json']
for node in ast.walk(tree):
    if isinstance(node, ast.For) and isinstance(node.target, ast.Tuple) and [ast.unparse(x) for x in node.target.elts] == ['group', 'version']:
        node.iter = ast.parse(repr(snapshots), mode='eval').body
        snapshot_loops += 1
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'body' for t in node.targets):
        node.value = ast.Constant(message)
        message_assignments += 1
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'groups' for t in node.targets):
        assert isinstance(node.value, ast.List)
        node.value.elts += [ast.Constant('root11_flag_' + digits + '_correction_v1')
                            for digits in ('1075729', '1198608', '1251896', '129557')]
        group_lists += 1
    if isinstance(node, ast.For) and isinstance(node.target, ast.Name) and node.target.id == 'name' and isinstance(node.iter, ast.Tuple):
        if any(isinstance(v, ast.Constant) and v.value == 'ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V7.json' for v in node.iter.elts):
            node.iter.elts += [ast.Constant(name) for name in extra_metadata]
            metadata_lists += 1
assert (snapshot_loops, message_assignments, group_lists, metadata_lists) == (1, 1, 1, 1)


class Versions(ast.NodeTransformer):
    def visit_Constant(self, node):
        if isinstance(node.value, str) and node.value in mapping:
            return ast.copy_location(ast.Constant(mapping[node.value]), node)
        return node


tree = Versions().visit(tree)
ast.fix_missing_locations(tree)
exec(compile(tree, str(frozen), 'exec'), {'__file__': __file__, '__name__': 'next_explicit_save'})
