"""Reuse literal admission without changing any guard, with an accurate reason."""
from pathlib import Path
import hashlib

frozen = Path(__file__).with_name('admit_closed_literal_rule_batch_v1.py')
raw = frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == '41F6BA7F9C9A4A2B363A73EF896C5C949008DB1732BEF0CC92E22BA367A21343'
code = raw.decode('utf-8')
for old, new in [
    ('기존 본문과 분류 값을 보존하고 실제 빈 별칭·빈 EOF 표제만 정리했다. 독립 문자 proof와 추가 문맥 반례·저장 리뷰를 모두 확인했다.',
     '독립 확인한 마지막 typed 분류 블록에서 동일 비수치 태그의 첫 출현과 모든 다른 값을 순서대로 보존하고 후속 동일 태그만 정리했다. 별칭·빈 표제 외 본문과 숫자·조건·인용·코드는 보존했다. 문항·답안 후보는 이 규칙으로 채택하지 않았다.'),
    ('[config_path,Path(__file__),scope,guard.CONTRACT,', '[config_path,Path(__file__),frozen,scope,guard.CONTRACT,'),
]:
    assert code.count(old) == 1
    code = code.replace(old, new)
exec(compile(code, str(frozen), 'exec'), dict(__name__='__main__', __file__=str(Path(__file__)), frozen=frozen))
