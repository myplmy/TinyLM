"""Reuse the frozen safe-copy publisher for five new root-observed defects."""
from pathlib import Path
import ast
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

notes = {
    '104207': '임달식의 실제 한자명 林達植을 원형대로 복원한다. 도입1963년과 분류1964년이라는 두 상충 출생연도 표시만 함께 원형 sidecar로 분리한다. 실제10월9일·선수/감독 경력·각 조건/징계 기간·살아있는사람·학력/다른분류는 보존한다. 어느 해가 참인지 선택하지 않는다.',
    '1056327': '어즈양주웨이의 도입1987년과 분류1978년이라는 두 상충 출생연도 표시만 함께 원형 sidecar로 분리한다. 실제10월2일·아나운서/학력/2009년 경력·살아있는사람과 다른분류는 보존한다. 없는 한자명을 만들지 않는다.',
    '1056993': '오마르 하킴의 도입1959/분류1958뿐 아니라 초기생애의1959년 출생 표시도 같은 상충 필드다. 선택문에 남은 그 출생연도만 원형 sidecar로 분리하고 실제2월12일·뉴욕 출생지·부친 하산 하킴·다섯살/4,5년 후·경력·명명 작품/인물·모든 채워진 관련자료/분류는 그대로 보존한다. 관련없는 역사/활동 날짜에 같은 숫자가 있더라도 전역 치환하지 않는다.',
    '1060163': '알래스카 썬더퍽의 도입1985년과 분류1981년이라는 두 상충 출생연도 표시만 함께 원형 sidecar로 분리한다. 실제 영문명 Alaska Thunderfuck·3월6일·음악/대회순위·작품명과연도·살아있는사람/다른분류는 전부 보존한다.',
    '106989': '샤오자이의 실제 도입 출생지 중국 베이징이 삭제됐다. 이 출생지와 기존4월10일의 원래 관계를 새 본문에 복원한다. 이미 분리한 상충 출생연도1980/1977은 둘 다 sidecar에 유지하고 사실을 고르지 않는다. 베이징시출신 분류가 별도로 있다는 이유로 실제 출생지를 버리지 않는다. 경력·포지션·정확 제목/출처/FIFA 날짜·다른분류는 보존한다. 값없는 클럽통계/국제골 절에 귀속된 마지막업데이트 원형은 sidecar에 유지한다.',
}
records = {r['id']: r for r in inv.cache.read(AUDIT / 'EXACT_SELECTION_RUNTIME_GUARDS_V10.json')['records']}
source = AUDIT / 'prepare_root11_1018113_correction_v1.py'
template = source.read_text(encoding='utf-8')
for digits in notes:
    assert not (inv.BASE / 'agents/context_hangul' / ('root11_birth_' + digits + '_correction_v2')).exists()
    assert not (AUDIT / ('ROOT11_' + digits + '_CORRECTION_INPUTS_V1.json')).exists()

for digits, note in notes.items():
    record = records['expanded_train:' + digits]
    guide = chr(10).join([
        '# ROOT11 출생프로필 ' + digits + '의 독립 검토 보완', '',
        '총괄이 이 정확 원문·ROOT11 선택문 전문과 전체diff를 실제 읽고 결함을 확인했다. 실제 정제문은 Luna가 새 버전 TXT로 작성한다.',
        '이번 지정역할은 context_hangul이고 이 폴더의 원형 사본/기존선택 사본/초기working과 자기 새 TXT/MD만 허용한다. 다른역할·바깥원문·JSON·코드·시험·통계·해시·웹·Git·모델·GPU는 금지다.',
        '두 readonly 입력은 expanded_train_' + digits + '_original.txt / expanded_train_' + digits + '_selected_root11.txt 이다. 기존 파일은 덮거나 삭제하지 않는다. 새 출력 이름은 아직 없는 새 버전으로만 만든다.', '', note, '',
        '원문·선택문과 새본문·원형sidecar/전체diff를 실제 EOF까지 확인하고 review_001.md에 ID/REVISE_TEXT/실제판독범위/정확TXT명/구체사유를5열로 쓴다. 이미 읽은 입력을 동일한 다른경로로 중복 판독할 필요는 없다.',
        '이 정확 폴더 안 자기 TXT/MD의 이름은 rg --files로 조회할 수 있다. 별도 PROGRESS_LOG_V1.md는 append-only로 허용한다. 5건을 마치고 이전 field page003의 다음 실제 미완료 TASK로 복귀한다.', ''])

    class Adapt(ast.NodeTransformer):
        def visit_Constant(self, node):
            if not isinstance(node.value, str):
                return node
            if node.value.startswith('# ROOT11의 1018113 독립 의미검토 보완'):
                value = guide
            else:
                value = node.value.replace('1018113', digits).replace('context_latin', 'context_hangul')
                value = value.replace('root11_ordered_corrections_v1', 'root11_birth_' + digits + '_correction_v2')
                value = value.replace('8F07F8FDDC939027E280B2F32162C5ADEE7BD18C9D7B5674A20CBE92B7073E04', record['clean_text_sha256'])
                if node.value == '538c0c':
                    value = '88e40e' if digits == '1056993' else '451c21'
            return ast.copy_location(ast.Constant(value=value), node)

    tree = ast.parse(template)
    filtered, removed = [], 0
    for node in tree.body:
        old_assignment = isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'assigned' for t in node.targets)
        old_role_assert = isinstance(node, ast.Assert) and any(isinstance(t, ast.Name) and t.id == 'assigned' for t in ast.walk(node.test))
        if old_assignment or old_role_assert:
            removed += 1
        else:
            filtered.append(node)
    assert removed == 2  # This is an explicit new root grant, not the old author's assignment.
    tree.body = filtered
    tree = Adapt().visit(tree)
    ast.fix_missing_locations(tree)
    exec(compile(tree, str(source), 'exec'), {'__file__': __file__, '__name__': 'five_exact_birth_copies'})
print('five exact unchanged source/selected pairs and initial working copies prepared; cleaned prose authored by root=0')
