"""Reuse the frozen exact input publisher for four actually read followups."""
from pathlib import Path
import ast

AUDIT = Path(__file__).resolve().parent
cases = {
    '151': ('historical_review',
            '이미 원문과 저장본문 전문을 총괄이 대조했다. 표가 빠진 뒤 내용 없이 성질 표제 앞에 남은 독립 중복 소제목 르장드르 다항식만 분리한다. 수직관계의 첫 따라서 접속어는 직접 앞의 식이 보류됐으므로 접속어만 정리하고 실제 직교성, 구간[-1,1], 스튀름리우빌 조건과 노름의 불확실성 한정은 보존한다. 수식이나 누락된 적분경로를 복구하지 않는다.'),
    '261707': ('context_latin',
               '원문은 파인먼 도형에 해당하는 산란진폭 성분을 s채널/t채널/u채널로 부른다고 실제 서술한다. 현재문은 파인먼 도형의 소유관계를 빠뜨렸다. 이 실제 도형-진폭-채널 관계만 원래 명칭으로 보존하고 누락된 도형의 모양이나 수식을 추정하지 않는다. s/t/u와 에너지제곱/운동량제곱, +−−−, 질량껍질/운동량보존,2차원2→2/신속도 조건과 독립 서술은 그대로 남긴다.'),
    '327633': ('context_latin',
               '실제 비교 설명 앞의 즉 접속어는 바로 앞 포함관계 수식이 보류되어 소유를 잃었으므로 접속어만 정리한다. 콤팩트공간/연속미분가능/연속함수의 아닐수있다는 부정과 조건은 보존한다. 실제 전변동 설명과1차원 맥락, f/[a,b]/가산개/거의어디서나/르베그적분가능은 그대로 남기고 새로운 정의역/노름/수식은 넣지 않는다.'),
    '937040': ('context_controls',
               '현재 본문에 남은 관련활동 카드 네 개의 단어중간/문장중간 끊김만 보류한다: Picasso 뒤 Create a portrait collage ins, worry dolls 뒤 These minipeople hold important p, ornaments 뒤 These holiday ornaments are light and unbreakable, 의 미완결 절, puppet 뒤 Young writers put the puppet arms로 끝나는 미완결 절. 각 줄의 앞 완결문장과 전체 재활용수업/원문질문/도구명/조건,완결된Kwanzaa·산호·VanGogh카드와1903제조문장은 보존한다. 원형의 실제 아포스트로피와 문자열을 확인하고 누락 접미사나 동작을 추정하지 않는다. 이937040한건에 한해 이 새 자기폴더의 readonly원문/selected_root11/working 사본은 cat/sed로 직접 전문 판독을 허용한다. 기존 birth범위의 고정reader 제한은 그대로다.'),
}
observation_chunks = {'151': '7ef77d', '261707': '7ef77d',
                      '327633': '38031c', '937040': '38031c'}
frozen = AUDIT / 'prepare_root11_four_followup_repairs_v1.py'
tree = ast.parse(frozen.read_text(encoding='utf-8'))
kept, removed = [], []
for node in tree.body:
    names = {t.id for t in node.targets if isinstance(t, ast.Name)} if isinstance(node, ast.Assign) else set()
    if names & {'cases', 'proof'}:
        removed.append(sorted(names)[0])
    elif isinstance(node, ast.Assert) and any(isinstance(t, ast.Name) and t.id == 'proof' for t in ast.walk(node.test)):
        removed.append('old_observation_assertion')
    else:
        kept.append(node)
assert sorted(removed) == ['cases', 'old_observation_assertion', 'proof']
tree.body = kept


class CurrentGrant(ast.NodeTransformer):
    def visit_Constant(self, node):
        if node.value == 'e067ff':
            return ast.copy_location(ast.Subscript(value=ast.Name(id='observation_chunks', ctx=ast.Load()),
                                                   slice=ast.Name(id='digits', ctx=ast.Load()), ctx=ast.Load()), node)
        if isinstance(node.value, str):
            value = node.value.replace('현재 field TASK', '현재 판독 TASK').replace('다음 field TASK', '다음 TASK')
            return ast.copy_location(ast.Constant(value=value), node)
        return node


tree = CurrentGrant().visit(tree)
ast.fix_missing_locations(tree)
exec(compile(tree, str(frozen), 'exec'),
     {'__file__': __file__, '__name__': 'four_reused_repeat_followups',
      'cases': cases, 'observation_chunks': observation_chunks})
