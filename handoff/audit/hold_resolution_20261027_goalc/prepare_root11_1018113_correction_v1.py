"""Give the original assigned author exact unchanged inputs for a semantic fix."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

ident = 'expanded_train:1018113'
contract = inv.cache.read(AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json')
source_path = AUDIT / 'EXACT_SELECTION_RUNTIME_GUARDS_V10.json'
source = next(row for row in inv.cache.read(source_path)['records'] if row['id'] == ident)
assert ident not in contract['restricted_ids'] and source['original_text_sha256'] not in contract['restricted_hashes']
assert source['clean_text_sha256'] == '8F07F8FDDC939027E280B2F32162C5ADEE7BD18C9D7B5674A20CBE92B7073E04'
assigned = next(row for row in inv.cache.read(inv.BASE / 'semantic_field_counter_v1/manifest.json')['rows'] if row['id'] == ident)
assert assigned['role'] == 'context_latin'
directory = inv.BASE / 'agents/context_latin/root11_ordered_corrections_v1'
directory.mkdir(exist_ok=False)
pins = {}
for label, path, sha in [('original', ROOT / source['original_comparison_source'], source['original_text_sha256']),
                          ('selected_root11', ROOT / source['body'], source['clean_text_sha256'])]:
    assert path.is_file() and not path.is_symlink() and inv.file_sha(path) == sha
    target = directory / ('expanded_train_1018113_' + label + '.txt')
    with target.open('xb') as stream: stream.write(path.read_bytes())
    assert inv.file_sha(target) == sha
    target.chmod(0o444)
    pins[label] = {'path': str(target.relative_to(ROOT)), 'sha256': sha}
working = directory / 'expanded_train_1018113_working_v1.txt'
with working.open('xb') as stream: stream.write((ROOT / pins['selected_root11']['path']).read_bytes())
assert inv.file_sha(working) == source['clean_text_sha256']
guide = directory / 'ROOT_TASK_1018113_V1.md'
text = '''# ROOT11의 1018113 독립 의미검토 보완

지정 역할=context_latin, 지정 ID=expanded_train:1018113 하나다. 이 폴더의 두 readonly 입력과 새 working/새 TXT MD만 허용한다. 코드/시험/해시/통계/Git/웹/다른역할/보호자료는 금지다.

총괄이 원문/선택본문 전문과 전체diff를 실제 읽었다. 기존 캐시는 덮지 않는다. 아래의 실제 잔존 문제만 새 본문/원형 sidecar/리뷰로 보완한다.

1. arity의 실제 문자열과 URL은 채워져 있지만 `[arity]https://en.wikipedia.org/wiki/Arity)`로 링크 괄호가 깨져 있다. 같은 anchor/URL을 올바른 링크 구문으로만 복구한다.
2. Select의 `in this example p is called the selection predicate.`는 실제 예제의 p 표기/식 자체가 없고 SQL에도 p 식별자는 없다. 그 직접 의존 최소 문장만 원형 sidecar로 분리한다. R의 명명된 설명·완결한 일반 정의·SQL·결과 문장은 보존한다.
3. Union/Set Difference/Cartesian Product의 원래 표제가 빠져 인접 연산으로 잘못 읽힐 위험이 있다. 본문 실제 UNION SQL, set differences라는 이름, cartesian product라는 이름 및 앞의 실제 여섯 연산 목록과 연결되는 이 세 표제만 재사용해 각 원래 단락의 소유를 분명히 한다. 새 수식이나 정의를 쓰지 않는다.
4. Project의 실제 일반 정의와 Rename의 명명된 설명은 남긴다. 기호를 아직 정의하지 않은 것처럼 보인다는 이유만으로 완결한 일반 매개변수 서술까지 삭제하지 않는다. 없는 실제 수식/예제를 새로 채우지 않는다.
5. 마지막 Top comments (0)은 댓글 UI이며 그 줄만 원형 sidecar로 분리한다. 저자의 동기/불확실성/게시물 계획·채워진 참조는 보존한다.
6. SELECT * EMPLOYEES WHERE...라는 원저자의 원형에는 FROM이 없다. 그것을 추출 오류나 문법 버그라고 자동 선택하지 말고 원형 보존한다. 실행/교정/SQL 재작성은 금지다.

readonly 입력: expanded_train_1018113_original.txt / expanded_train_1018113_selected_root11.txt
새 작업 사본: expanded_train_1018113_working_v1.txt
리뷰: 새 review_001.md에 ID/REVISE_TEXT/전문과diff 판독근거/실제 출력TXT명/원형 sidecar와 이유를 기록한다. 기존 입력/기존 캐시/기존 선택본문은 변경하지 않는다. 본문 안에는 검수메모를 넣지 않는다.
'''
with guide.open('x', encoding='utf-8') as stream: stream.write(text)
inv.write_json(AUDIT / 'ROOT11_1018113_CORRECTION_INPUTS_V1.json', {
    'status': 'UNCHANGED_ASSIGNED_INPUTS_FOR_LUNA_CORRECTION_NOT_NEW_ADMISSION', 'id': ident, 'role': 'context_latin',
    'input_pins': pins, 'working': str(working.relative_to(ROOT)), 'working_initial_sha256': source['clean_text_sha256'],
    'guide': {'path': str(guide.relative_to(ROOT)), 'sha256': inv.file_sha(guide)},
    'root_original_selected_full_read_tool_chunk': '538c0c', 'cleaned_prose_authored_by_root': 0,
    'cache_changed': False, 'goal_complete': False, 'training_authorized': False})
print(json.dumps({'role':'context_latin','id':ident,'scope':str(guide)},ensure_ascii=False))
