"""Reuse the verified fixed reader publisher for the existing Latin assignment."""
from pathlib import Path
import ast

AUDIT = Path(__file__).resolve().parent
frozen = AUDIT / 'prepare_birth_root11_fixed_reader_v1.py'
tree = ast.parse(frozen.read_text(encoding='utf-8'))
mapping = {
    'context_controls': 'context_latin',
    'BIRTH_ROOT11_SCOPED_READER_VERIFIED_V1.json': 'BIRTH_ROOT11_LATIN_SCOPED_READER_VERIFIED_V1.json',
    'SCOPED_CONTEXT_CONTROLS_BIRTH_ROOT11_INPUTS_V1.json': 'SCOPED_CONTEXT_LATIN_BIRTH_ROOT11_INPUTS_V1.json',
    'read_context_controls_birth_root11_packet_v1.py': 'read_context_latin_birth_root11_packet_v1.py',
    '# 출생 최종본문 독립2차: controls 읽기 허가': '# 출생 최종본문 독립2차: Latin 읽기 허가',
    '현재 literal의 실제 남은 중재를 마감한 뒤 이 START_HERE와 TASK_001부터 마지막 TASK까지 순차 진행한다.':
        '현재 읽는 TASK를 마감한 뒤 정확 다음 TASK부터 이 고정 명령으로 진행한다. 이미 완료한 TASK를 도구 전환 때문에 다시 읽지 않는다.',
    '최대4개의 독립 reader 호출을 functions.exec에서 함께 실행할 수 있다. 모든 결과의 순서·출력끝·누락/잘림을 확인한다.':
        '한 exec에서 한 패킷만 호출하고 출력 예산을10000토큰 이상으로 둔다. 출력끝·논리순서와 잘림 여부를 확인한다.',
}
seen = {key: 0 for key in mapping}
count_replacements = 0


class LatinAssignment(ast.NodeTransformer):
    def visit_Constant(self, node):
        global count_replacements
        if isinstance(node.value, str) and node.value in mapping:
            seen[node.value] += 1
            return ast.copy_location(ast.Constant(value=mapping[node.value]), node)
        if isinstance(node.value, int) and not isinstance(node.value, bool) and node.value == 1354:
            count_replacements += 1
            return ast.copy_location(ast.Constant(value=1353), node)
        return node


tree = LatinAssignment().visit(tree)
assert all(value == 1 for value in seen.values()) and count_replacements == 1
ast.fix_missing_locations(tree)
exec(compile(tree, str(frozen), 'exec'),
     {'__file__': __file__, '__name__': 'latin_fixed_reader_publication'})
