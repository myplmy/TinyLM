"""Reuse the exact save planner for the resumed source-review checkpoint."""
from pathlib import Path
import ast

AUDIT = Path(__file__).resolve().parent
frozen = AUDIT / 'prepare_exact_followup_checkpoint_v7.py'
tree = ast.parse(frozen.read_text(encoding='utf-8'))
mapping = {
    '767f408e8af1c0e85c39d6b747c822aec97f88cf': 'ae2233ac4c8cb05f13a786e1ed798699e07efb31',
    'exact_followup_progress_archive_v7': 'exact_followup_progress_archive_v9',
    'EXACT_FOLLOWUP_PROGRESS_ARCHIVE_V7.json': 'EXACT_FOLLOWUP_PROGRESS_ARCHIVE_V9.json',
    'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V7.json': 'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V9.json',
    'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V6.json': 'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V8.json',
    'EXACT_FOLLOWUP_PROGRESS_COMMIT_MESSAGE_V7.txt': 'EXACT_FOLLOWUP_PROGRESS_COMMIT_MESSAGE_V9.txt',
    'EXACT_FOLLOWUP_PROGRESS_SAVE_MANIFEST_V7.json': 'EXACT_FOLLOWUP_PROGRESS_SAVE_MANIFEST_V9.json',
    'ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V7.json': 'ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V12.json',
    'ROOT_LITERAL_REVIEWED_NONADMISSIONS_V2.json': 'ROOT_LITERAL_REVIEWED_NONADMISSIONS_V3.json',
}
snapshots = [('remaining_literal_full_counter_v1', 'v20'),
    ('remaining_field_title_page_001_counter_v1', 'v8'),
    ('remaining_field_title_page_002_counter_v1', 'v8'),
    ('remaining_field_title_page_003_counter_v1', 'v6'),
    ('remaining_field_title_page_004_counter_v1', 'v5'),
    ('remaining_field_title_page_005_counter_v1', 'v1'),
    ('birth_root11_independent_v1', 'v11')]
message = chr(10).join(['데이터: 잔여 판독과 의미 보완 근거를 이어 저장한다', '',
    '- literal1793의1783본문후보와10개별HOLD를확정연결하고이후field1041리뷰와출생독립755리뷰를동결한다.',
    '- 총괄26개실제판독에서발견한18개문제의교체본문과초기19개출생보완안의후속판단을검증한다.',
    '- 기존반복80개의독립원문·버전·역할근거를재사용하고기록연결을자동의미승인으로쓰지않는다.',
    '- 109206자사전의7줄수정밖바이트보존과원문·후보보존및초안이력의미확인을구분한다.',
    '- Latin1353입력/2122패킷고정reader와동일초기사본을검증하고단계혼동/판독전리뷰/영화누락오인의정정을보존한다.',
    '- 새draft와확정판을구분하고입력전문·수정전체차이·문맥·바이트검산절차로반복비용을줄인다.',
    '- 대량본문·캐시·보호자료·타세션변경은제외하며공식H110173과전체A-E미완료를유지한다.',
    '- 다섯역할과전체정제는계속진행하고중간저장을완료/일시중지/추가300M승인으로바꾸지않는다.', ''])
extra_metadata = [
    'LITERAL_FULL_FIRST_READING_RECONCILIATION_V1.json',
    'BIRTH_ROOT11_SECOND_READING_PREPARATION_V1.json', 'BIRTH_ROOT11_SCOPED_READER_VERIFIED_V1.json',
    'BIRTH_CONTROLS_INITIAL_COPIES_VERIFIED_V1.json',
    'BIRTH_ROOT11_LATIN_SCOPED_READER_VERIFIED_V1.json', 'BIRTH_LATIN_INITIAL_COPIES_VERIFIED_V1.json',
    'BIRTH_SECOND_REPAIR_SOURCE_ADJUDICATION_V2.json', 'ROOT11_AND_BIRTH_SAVED_REVIEW_COVERAGE_BRIDGE_V4.json',
    'EXISTING_REPEAT_ORDERED_FLAG_REVIEW_BINDINGS_V1.json', 'FIELD_46845_EXACT_LOCAL_EDITS_VERIFIED_V1.json',
    'AUTHOR_DRAFT_AND_REVIEW_CLAIM_INCIDENTS_20261103_V1.json', 'WIP_EXACT_FOLLOWUP_V20_APPLIED.json',
    'SCOPED_CONTEXT_LATIN_BIRTH_ROOT11_INPUTS_V1.json']
snapshot_loops = messages = group_lists = metadata_lists = archive_insertions = 0
guide_copy_code = '''
for selected_role, names in {
    'context_controls': ('ROOT_BINDING_AND_OUTPUT_RULES_V2.md', 'ROOT_PENDING_REPAIRS_20261103_V1.md'),
    'context_latin': ('ROOT_PENDING_REPAIRS_20261103_V1.md', 'ROOT_FIXED_LATIN_READER_ADOPTION_V1.md',
                      'ROOT_FIXED_READER_SCOPE_V1.md', 'ROOT_UNCHANGED_INITIAL_COPIES_V1.md'),
}.items():
    for guide_name in names:
        guide_path = inv.BASE / 'agents' / selected_role / 'birth_root11_independent_v1' / guide_name
        copies.append(copy(guide_path, archive / 'birth_role_guides' / selected_role / guide_name))
'''
for node in ast.walk(tree):
    if isinstance(node, ast.For) and isinstance(node.target, ast.Tuple) and [ast.unparse(t) for t in node.target.elts] == ['group', 'version']:
        node.iter = ast.parse(repr(snapshots), mode='eval').body
        snapshot_loops += 1
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'body' for t in node.targets):
        node.value = ast.Constant(message)
        messages += 1
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'groups' for t in node.targets):
        assert isinstance(node.value, ast.List)
        node.value.elts += [ast.Constant('root11_flag_' + number + '_correction_v1') for number in
                           ('1075729', '1198608', '1251896', '129557', '151', '261707', '327633', '937040')]
        group_lists += 1
    if isinstance(node, ast.For) and isinstance(node.target, ast.Name) and node.target.id == 'name' and isinstance(node.iter, ast.Tuple):
        if any(isinstance(v, ast.Constant) and v.value == 'ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V7.json' for v in node.iter.elts):
            node.iter.elts += [ast.Constant(name) for name in extra_metadata]
            metadata_lists += 1
nodes = []
for node in tree.body:
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) and ast.unparse(node.value.func) == 'inv.write_json':
        if any(isinstance(v, ast.Constant) and v.value == 'EXACT_FOLLOWUP_PROGRESS_ARCHIVE_V7.json' for v in ast.walk(node.value.args[0])):
            nodes.extend(ast.parse(guide_copy_code).body)
            archive_insertions += 1
    nodes.append(node)
tree.body = nodes
assert (snapshot_loops, messages, group_lists, metadata_lists, archive_insertions) == (1, 1, 1, 1, 1)


class Versions(ast.NodeTransformer):
    def visit_Constant(self, node):
        if isinstance(node.value, str) and node.value in mapping:
            return ast.copy_location(ast.Constant(value=mapping[node.value]), node)
        return node


tree = Versions().visit(tree)
ast.fix_missing_locations(tree)
exec(compile(tree, str(frozen), 'exec'), {'__file__': __file__, '__name__': 'resumed_exact_save'})
