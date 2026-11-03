"""Reuse the exact safe-copy publisher for four independently observed repairs."""
from pathlib import Path
import ast
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

cases = {
    '1075729': ('legacy_review', '공식사이트뒤에같은296 GTB표제만다섯줄반복되고행별주체/값/관계는없다. 그꼬리다섯줄을원형sidecar로분리하고정상차종명/역사/명명공식사이트/엔진/배터리/중량/14초/게임·모터스포츠내용은선택문그대로보존한다. 의미없는반복이라고전체본문의같은차종명을전역삭제하지않는다.2022년예정등원저자의당시주장을현재사실로고치지않고빈출력/속도/가속목표를채우지않는다.'),
    '1198608': ('legacy_review', '선택문의연혁표제뒤에는생산제품표제전까지내용이없다. 이빈연혁표제만원형sidecar로분리한다. 앞의실제1999년2월26일/창업자/2003/2005/인증내용과뒤의다섯생산부문및모든제품명/분류는기존바이트그대로지킨다.'),
    '1251896': ('legacy_review', '원문과선택문의REPL기록은실제>>>프롬프트세개와명시된두32결과가한줄로붙어있다. 기존토큰/문자열/따옴표/값은그대로두고프롬프트와그뒤실제결과의유일한행경계만개행으로복원한다. 새사용자입력32나추가출력/>>>/실행결과를생성하지않는다. Python2.x/raw_input조건과원래두연습문제는그대로유지한다. 프로그램을실행하거나정답예제를작성하지않는다.'),
    '129557': ('context_hangul', '원문의전자기장텐서 Fμν의성분예고를분리하면서실제기호 Fμν까지사라졌다. 그원래동일대상표기만기존본문의명명소개에보존한다. 기호를새성분식이나표값으로확장하지않는다. 완결된정의/퍼텐셜/미분형식관계·E/B/c/Eb/Bab/ta/∇a∧t와-+++조건및분류는그대로지킨다. 없는성분식/지표를생성하거나과학사실을정정하지않는다.'),
}
records = {r['id']: r for r in inv.cache.read(AUDIT / 'EXACT_SELECTION_RUNTIME_GUARDS_V10.json')['records']}
proof = inv.cache.read(AUDIT / 'ROOT11_INDEPENDENT_ORDERED_SEMANTIC_REVIEW_V8.json')
assert all(any(r['id'] == 'expanded_train:' + digits and r['observation_tool_chunk'] == 'e067ff'
               for r in proof['rows']) for digits in cases)
template_path = AUDIT / 'prepare_root11_1018113_correction_v1.py'
template = template_path.read_text(encoding='utf-8')
for digits, (role, _) in cases.items():
    assert not (inv.BASE / 'agents' / role / ('root11_flag_' + digits + '_correction_v1')).exists()
    assert not (AUDIT / ('ROOT11_' + digits + '_CORRECTION_INPUTS_V1.json')).exists()
for digits, (role, note) in cases.items():
    record = records['expanded_train:' + digits]
    guide = chr(10).join([
        '# ROOT11 최종본문의 추가 보완: ' + digits, '',
        '총괄이 원문·기존 선택문과 전체diff를 실제 읽고 이 좁은 문제를 확인했다. 실제 새 TXT/MD는 지정 Luna가 작성한다.',
        '지정 역할=' + role + '. 입력은 이 새 자기 폴더의 두 readonly original/selected_root11 사본과 초기working이다. 쓰기는 이 폴더의 아직 없는 새 TXT/MD만 허용한다.',
        '기존 원문/선택문/캐시/다른 역할/보호자료/코드/시험/통계/해시/웹/Git/모델/GPU는 금지다.', '', note, '',
        '원문/기존선택 전문과 새본문 전문/전체diff를 실제 EOF까지 대조하고 review_001.md에 ID/REVISE_TEXT/실제판독범위/정확TXT basename/원형 sidecar와 사유를5열로 기록한다.',
        '자기 폴더의 파일명은 rg --files로 볼 수 있고 PROGRESS_LOG를 append-only로 쓸 수 있다. 같은 본문을 다른 경로로 반복 읽을 필요는 없다.',
        '현재 field TASK를 읽는 중이면 그TASK부터 마감한뒤 이보완을 처리하고 원래 다음 field TASK로 복귀한다. 중간저장/한TASK종료로 전체goal을 멈추지 않는다.', ''])

    class Adapt(ast.NodeTransformer):
        def visit_Constant(self, node):
            if not isinstance(node.value, str):
                return node
            if node.value.startswith('# ROOT11의 1018113 독립 의미검토 보완'):
                value = guide
            else:
                value = node.value.replace('1018113', digits).replace('context_latin', role)
                value = value.replace('root11_ordered_corrections_v1', 'root11_flag_' + digits + '_correction_v1')
                value = value.replace('8F07F8FDDC939027E280B2F32162C5ADEE7BD18C9D7B5674A20CBE92B7073E04', record['clean_text_sha256'])
                if node.value == '538c0c':
                    value = 'e067ff'
            return ast.copy_location(ast.Constant(value=value), node)

    tree = ast.parse(template)
    nodes, removed = [], 0
    for node in tree.body:
        old_assignment = isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'assigned' for t in node.targets)
        old_role_assert = isinstance(node, ast.Assert) and any(isinstance(t, ast.Name) and t.id == 'assigned' for t in ast.walk(node.test))
        if old_assignment or old_role_assert:
            removed += 1
        else:
            nodes.append(node)
    assert removed == 2  # The explicit new role grant above owns these new folders.
    tree.body = nodes
    tree = Adapt().visit(tree)
    ast.fix_missing_locations(tree)
    exec(compile(tree, str(template_path), 'exec'), {'__file__': __file__, '__name__': 'four_fixed_input_publishers'})
print('4 exact original/selected input pairs copied; root-authored cleaned bodies=0; adopted=0')
