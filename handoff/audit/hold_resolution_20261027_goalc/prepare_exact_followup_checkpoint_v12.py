"""One-pass reuse of the frozen v7 planner; no chained namespace substitutions."""
from pathlib import Path
import ast

AUDIT = Path(__file__).resolve().parent
frozen = AUDIT / 'prepare_exact_followup_checkpoint_v7.py'
tree = ast.parse(frozen.read_text(encoding='utf-8'))
previous_plan = ast.parse((AUDIT / 'prepare_exact_followup_checkpoint_v11.py').read_text(encoding='utf-8'))
values = {}
for node in previous_plan.body:
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        if node.targets[0].id in {'snapshots', 'extra', 'archive_extra'}:
            values[node.targets[0].id] = ast.literal_eval(node.value)
assert set(values) == {'snapshots', 'extra', 'archive_extra'}
v9_plan = ast.parse((AUDIT / 'prepare_exact_followup_checkpoint_v9.py').read_text(encoding='utf-8'))
for node in v9_plan.body:
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        if node.targets[0].id in {'extra_metadata', 'guide_copy_code'}:
            values[node.targets[0].id] = ast.literal_eval(node.value)
assert set(values) == {'snapshots', 'extra', 'archive_extra', 'extra_metadata', 'guide_copy_code'}
mapping = {
    '767f408e8af1c0e85c39d6b747c822aec97f88cf': '2f811836774ababf680c5d64a0f6c8825280935c',
    'exact_followup_progress_archive_v7': 'exact_followup_progress_archive_v12',
    'EXACT_FOLLOWUP_PROGRESS_ARCHIVE_V7.json': 'EXACT_FOLLOWUP_PROGRESS_ARCHIVE_V12.json',
    'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V7.json': 'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V12.json',
    'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V6.json': 'EXACT_FOLLOWUP_PROGRESS_LARGE_LOCAL_V10.json',
    'EXACT_FOLLOWUP_PROGRESS_COMMIT_MESSAGE_V7.txt': 'EXACT_FOLLOWUP_PROGRESS_COMMIT_MESSAGE_V12.txt',
    'EXACT_FOLLOWUP_PROGRESS_SAVE_MANIFEST_V7.json': 'EXACT_FOLLOWUP_PROGRESS_SAVE_MANIFEST_V12.json',
    'ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V7.json': 'ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V12.json',
    'ROOT_LITERAL_REVIEWED_NONADMISSIONS_V2.json': 'ROOT_LITERAL_REVIEWED_NONADMISSIONS_V3.json',
}
message = chr(10).join(['데이터: 잔여 판독과 거부 행 검증 근거를 저장한다', '',
    '- 필드1382/18237과 생년독립1440/2707의 고정 집계 및 공식잔여H110173을 구분한다.',
    '- 출력연결 거부 두 행을 격리하는 새 검증기를 CPU28회귀와 실제 음성 스냅샷으로 검증한다.',
    '- 불변 이벤트 접두로445행의 입력전달 선결을 확인하고 의미승인과 구분한다.',
    '- 새 네 보완 본문의 조건·단위·원형 인용과 허용변경 밖 바이트를 검산한다.',
    '- 두 필드 원형의 개별 전체HOLD와 패킷분할 오인의 정정 근거를 보존한다.',
    '- 이전/현재 리뷰·본문 소유연쇄5건을 찾아 기록경로390/585를 연결한다.',
    '- 준비기v11의 이름충돌 실패와 부분사본은 보존하고 단일변환v12로 저장한다.',
    '- 원형·대량본문·캐시·보호자료·타세션변경·push/PR은 제외한다.',
    '- 다섯 역할과 전체정제는 계속하며 중간저장을 완료·일시중지·학습승인으로 바꾸지 않는다.', ''])
extra = list(dict.fromkeys(values['extra_metadata'] + values['extra'] + [
    'BIRTH_INPUT_DELIVERY_CURRENT_RUNTIME_EVIDENCE_V1.json',
    'ORDERED_FLAG_OLD_PATH_PROVENANCE_AUDIT_V2.json',
    'ORDERED_FLAG_EXISTING_REVIEW_REUSE_SUMMARY_V1.json']))
counts = dict(snapshot=0, message=0, groups=0, metadata=0, archive=0)
for node in ast.walk(tree):
    if isinstance(node, ast.For) and isinstance(node.target, ast.Tuple) and [ast.unparse(t) for t in node.target.elts] == ['group', 'version']:
        node.iter = ast.parse(repr(values['snapshots']), mode='eval').body
        counts['snapshot'] += 1
    if isinstance(node, ast.Assign):
        targets = [target.id for target in node.targets if isinstance(target, ast.Name)]
        if 'body' in targets:
            node.value = ast.Constant(message)
            counts['message'] += 1
        if 'groups' in targets:
            node.value.elts += [ast.Constant('root11_flag_' + number + '_correction_v1') for number in
                ('1075729', '1198608', '1251896', '129557', '151', '261707', '327633', '937040')]
            counts['groups'] += 1
    if isinstance(node, ast.For) and isinstance(node.target, ast.Name) and node.target.id == 'name' and isinstance(node.iter, ast.Tuple):
        if any(isinstance(v, ast.Constant) and v.value == 'ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V7.json' for v in node.iter.elts):
            node.iter.elts += [ast.Constant(name) for name in extra]
            counts['metadata'] += 1
nodes = []
for node in tree.body:
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) and ast.unparse(node.value.func) == 'inv.write_json':
        if any(isinstance(v, ast.Constant) and v.value == 'EXACT_FOLLOWUP_PROGRESS_ARCHIVE_V7.json' for v in ast.walk(node.value.args[0])):
            nodes += ast.parse(values['guide_copy_code'] + chr(10) + values['archive_extra']).body
            counts['archive'] += 1
    nodes.append(node)
tree.body = nodes
assert set(counts.values()) == {1}


class Versions(ast.NodeTransformer):
    def visit_Constant(self, node):
        if isinstance(node.value, str) and node.value in mapping:
            return ast.copy_location(ast.Constant(value=mapping[node.value]), node)
        return node


tree = Versions().visit(tree)
ast.fix_missing_locations(tree)
exec(compile(tree, str(frozen), 'exec'), {'__file__': __file__, '__name__': 'single_pass_exact_checkpoint'})
