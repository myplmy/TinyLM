"""Record actual root context judgments without admitting diagnostic bodies."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
sys.path.insert(0, str(AUDIT))
from exact_manifest_review_row_binding_v1 import load_parser

pins = {}


def read(path):
    assert not path.is_symlink()
    assert path.resolve().is_relative_to(BASE) or path.resolve().is_relative_to(AUDIT)
    payload = path.read_bytes()
    assert 0 < len(payload) < 20_000_000
    pins[str(path.relative_to(ROOT))] = hashlib.sha256(payload).hexdigest().upper()
    return payload


contract = json.loads(read(AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'))
assert pins[str((AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json').relative_to(ROOT))] == (
    'CE929E1C714E5419A78FF22481A6F990F0B27C813204F4B3B94CC8D58E73D6EF')
diagnostic = json.loads(read(AUDIT / 'ROOT11_BIRTH_SEMANTIC_SPAN_DIAGNOSTICS_V1.json'))
assert diagnostic['counts']['flagged_sources'] == 34
resolve, parse, _ = load_parser()

# These explanations were authored after the listed actual tool outputs were read.
# They are not inferred automatically from the detector or from the review verdict.
contexts = {
    120410: ('6e4795', 'CONFLICTING_BIRTH_YEARS',
             '리드·분류1292와 본문1291이 상충한다. 두 무조건 연도만 분리하고 리옹·부모·1322년1월3일 사망을 보존한다.'),
    121135: ('6e4795', 'REVIEW_DESCRIPTION_CORRECTION_PENDING',
             '1839와 약력1840을 실제 후보는 모두 분리하고9월7일·장소·가족을 유지한다. 리뷰가1840도 보존했다고 잘못 서술하므로 본문 불변의 한 행 설명 교정을 요청했다.'),
    144106: ('9c4b80', 'CONFLICTING_BIRTH_YEARS',
             '리드1486/1487·본문1476·분류1486을 선택하지 않고 분리한다. 사망1526년8월4일·장소·가족·탐험 경력은 유지한다.'),
    299959: ('9c4b80', 'CONFLICTING_BIRTH_YEARS',
             '리드·분류1018과 본문1020의 출생연도만 분리한다. 부모·출생 관계·1042년6월8일 사망과 통치 연혁은 유지한다.'),
    84493: ('728183', 'LEXICAL_BOUNDARY_FALSE_POSITIVE',
            '1855년 전라북도의 전은 시간관계 후치사가 아니라 지명 첫 글자이다. 1855/1854 연도 보류 뒤 전라북도 고창군 죽림리 당촌 및 원문 나이는 유지한다.'),
    110507: ('c9e159,6eadd1', 'DEPENDENT_CONFLICT_OR_QUALIFIED_SOURCE_PRESERVED',
             '즉위9년후와 재위8년은 직접 충돌해 둘 다 원형 보류한다.1512–1520 재위·1520 사망과 본문의1470년경 한정을 유지하고 무조건1470 리드·분류만 보류한다.'),
    111732: ('9c4b80', 'QUALIFIED_BIRTH_SOURCE_PRESERVED',
             '1573이 아니라는 이설·생년 불명·1584년12세 기록에 따른1573 추정을 그대로 유지하고 무조건 리드·분류만 보류한다. 나이를 새로 역산하지 않는다.'),
    192706: ('9c4b80', 'QUALIFIED_BIRTH_SOURCE_PRESERVED',
             '1722년5월3일에 태어났다고도 한다는 한정은 유지하고 무조건1719를 보류한다. 충돌 사망 월일은 양쪽 보류하고 공통1745·사망·27세·1734년 괄호를 보존한다.'),
    194297: ('7d33aa', 'QUALIFIED_BIRTH_SOURCE_PRESERVED',
             '1722년7월11일에 태어났다고도 한다는 한정은 유지하고 무조건1720을 보류한다.1765년11월3일 사망 역할·46세·직접 생애 관계는 유지한다.'),
    22530: ('7d33aa', 'QUALIFIED_BIRTH_SOURCE_PRESERVED',
            '본문1235년경은 유지하고 리드·분류의 무조건1235만 보류한다. 빌라니의 귀속된1303년10월12일 인용은 그대로이며 인용 밖 경쟁 사망 월일만 보류한다.'),
    277265: ('c9e159,6eadd1', 'DEPENDENT_CONFLICT_OR_QUALIFIED_SOURCE_PRESERVED',
             '3년뒤인1934의3년은 상충1931/1932 출생에 직접 의존해 분리한다. 실제1934 이주·장소·교육·사망은 유지하며 나이·출생을 계산해 채우지 않는다.'),
    520439: ('728183', 'LEXICAL_BOUNDARY_FALSE_POSITIVE',
             '23일 전기의자의 전은 전기의자의 첫 글자이다. 경쟁 사망 월일을 보류한 뒤 전기의자·1927년 처형·각 인물 관계가 유지된다.'),
    538092: ('728183', 'LEXICAL_BOUNDARY_FALSE_POSITIVE',
             '1953년 전라남도의 전은 지명 첫 글자이다.1953/1954 출생연도 분리 뒤 전라남도 장흥·6개월만의 익산 이주가 유지된다.'),
    695195: ('7d33aa', 'CONFLICTING_BIRTH_YEARS',
             '1513 리드·분류와1512 본문을 함께 보류한다. 갈루초·부모·1566년4월16일 사망과 실제14세·22세·53세를 유지하고 역산하지 않는다.'),
    79984: ('7d33aa', 'BODY_LABEL_CORRECTION_PENDING',
            '1919와1918 출생연도 보류는 타당하다. 후보 리드의 앞이 빈 ~1995년3월30일을 실제 사망 역할로 닫는 한 위치 교정을 요청했다.'),
    810478: ('112b8e,61919d', 'QUALIFIED_BIRTH_SOURCE_PRESERVED',
             '원문의 여러 생년설·1039 유력설 및 출처가 명시된 사망 기록을 유지하고 단정1039 리드·분류만 보류했다. 이미 완료한 두 후속의 실제 전차이·본문 증거를 동일 SHA로 재사용한다.'),
    81208: ('7d33aa', 'BODY_LABEL_CORRECTION_PENDING',
            '1879/1880설 문맥은 유지하고 단정1879만 분리한다. 남은 음력8월21일과1955년6월1일에 원문 출생/사망 역할을 각각 명시하는 한 위치 교정을 요청했다.'),
    183863: ('c6b887', 'CONFLICTING_BIRTH_YEARS',
             '1568/1566 출생과1637/1636 사망연도는 선택하지 않는다.1월21일·출생지·부모 및1636년에 시작한 전쟁과 전사 관계는 그대로이며 새 사망연도를 만들지 않는다.'),
    314339: ('728183', 'LEXICAL_BOUNDARY_FALSE_POSITIVE',
             '1849년 전쟁의 전은 전쟁의 첫 글자이다.1849/1848 사망연도를 보류한 뒤 전쟁 종결·귀가·사망 관계와1807년 입대12세를 그대로 유지한다.'),
    45295: ('728183', 'LEXICAL_BOUNDARY_FALSE_POSITIVE',
            '1898년 전남의 전은 지명 첫 글자이다.1898/1888 출생연도 분리 뒤 전남 출생과1950년10월13일 사망을 유지한다.'),
    688560: ('c9e159,6eadd1', 'DEPENDENT_CONFLICT_OR_QUALIFIED_SOURCE_PRESERVED',
             '그5개월뒤1956년10월 사망은 경쟁12월30일·1951 분류와 함께 직접 의존 구간으로 보류한다. 실제1956년5월 학위·사망 사실·연혁을 유지하고 근거 없는 후보의 날짜/선거연도 교정을 원형으로 돌렸다.'),
    817488: ('3d769e', 'CONFLICTING_BIRTH_YEARS',
             '리드·분류1938과 생애1951 출생연도를 모두 분리한다. 광주 출생지·2015년4월27일 사망·법조 경력·귀속된 판결과 조건은 유지한다.'),
    139681: ('c6b887', 'BODY_LABEL_CORRECTION_PENDING',
             '단정1263과 그에 직접 의존한 가계 추론을 분리하고1262설·독립 가족 정보는 유지한다. 리드의 빈 쉼표와 앞이 빈 ~를 좁게 닫되1302년 두 사망일설·각 음력 대응은 그대로 유지하도록 요청했다.'),
    180112: ('c6b887', 'QUALIFIED_BIRTH_SOURCE_PRESERVED',
             '무조건1759를 보류하고1761년에 태어났다고도 한다는 원문 한정·1793년10월23일 사망·35세와 생애를 유지한다.'),
    199965: ('c6b887', 'QUALIFIED_BIRTH_SOURCE_PRESERVED',
             '무조건1486을 보류하고 원문1484 또는1491 이설·연호·1531년9월8일 사망·음력 대응·46세를 유지한다.'),
    203845: ('c6b887', 'QUALIFIED_BIRTH_SOURCE_PRESERVED',
             '무조건1707을 보류하고1708년에 태어났다고도 한다는 한정은 유지한다.9월24일과8월29일 사망은 선택·변환 없이 보류하고1745·엔쿄2년·가메다·39세를 보존한다.'),
    276009: ('6a8aa4', 'QUALIFIED_BIRTH_SOURCE_PRESERVED',
             '리드·분류의 단정1494만 보류한다. 본문의1494에 태어났다고 하나1504설도 있다는 한정과 출생지 이설·음력4월20일(1556년5월28일) 사망·경력은 유지한다.'),
    341392: ('c9e159,6eadd1,cad2da,ecddd0', 'IDENTITY_HOLD_METADATA_CORRECTED',
             '12세·32세는 이우/이간과 가족표 귀속이 미확정인 세 기록 안에 있어 기록 전체를 원형 보류한다. 실제 발화가 없다는 sidecar 오류는 발화는 있고 닫는 인용부호가 없다는 한 문장으로 교정했다. 본문은 불변이다.'),
    355073: ('6a8aa4,d45fa0', 'BODY_INFORMATION_RESTORATION_PENDING',
             '조건부1478/지문1479 문맥과11세는 유지한다. 출생연도 분리와 함께 빠진 리드의 명시 사망1488년8월20일(음력7월14일)을 원문 표시 그대로 복원하도록 요청했다. 새 역법 변환이 아니다.'),
    45156: ('6a8aa4', 'QUALIFIED_BIRTH_SOURCE_PRESERVED',
            '단정1543 리드·본문·분류만 보류하고1544설·생일 미상·한성부·가족·1599년1월5일 사망·독립 생애와 참고문헌을 유지한다.'),
    466251: ('6a8aa4', 'QUALIFIED_BIRTH_SOURCE_PRESERVED',
             '단정1073 리드·분류를 분리하고 대략1073쯤으로 추측된다는 본문·부모·생애를 유지한다. 리드에서 빠진1118년11월28일은 본문에 같은 사망 관계로 남아 있다.'),
    55286: ('6a8aa4,d45fa0', 'QUALIFIED_BIRTH_SOURCE_PRESERVED',
            '무조건 리드·분류1898을 보류하고1898년생으로 일설에는1889년생이라는 이설 문맥을 그대로 둔다.1983년11월22일 사망은 본문에 장소·관계와 함께 남아 있다.'),
    58676: ('3d769e', 'QUALIFIED_BIRTH_SOURCE_PRESERVED',
            '생년 불명·1879설/1883설과 이름·출생지 불확실성은 유지하고 무조건1879 리드·분류만 보류한다.1915년11월4일 사망·37세·경력을 보존한다.'),
    653732: ('3d769e', 'CONFLICTING_BIRTH_YEARS',
             '1959 리드·분류와 본명 출생문1964를 함께 보류한다. 출생지·본명·2010년4월18일 사망 역할과 실제 사망 보도의 귀속·조건은 그대로 유지한다.'),
}
assert set(contexts) == {int(row['id'].split(':')[1]) for row in diagnostic['rows']}
texts = {}
rows = []
for row in diagnostic['rows']:
    ident = row['id']
    assert ident not in contract['restricted_ids']
    assert row['original']['sha256'] not in contract['restricted_hashes']
    values = {}
    for label in ('original', 'body'):
        payload = read(ROOT / row[label]['path'])
        assert hashlib.sha256(payload).hexdigest().upper() == row[label]['sha256']
        values[label] = payload.decode('utf-8')
    review = read(ROOT / row['review']['archive'])
    assert hashlib.sha256(review).hexdigest().upper() == row['review']['sha256']
    matching = [entry for entry in parse(review) if resolve(entry['cells'][0]) == ident]
    assert len(matching) == 1
    number = int(ident.split(':')[1])
    actual, decision, reason = contexts[number]
    texts[number] = values
    rows.append(dict(id=ident, original=row['original'], body=row['body'], review=row['review'],
                     diagnostic_flags=row['flags'], context_decision=decision, reason=reason,
                     actual_root_context_read_outputs=actual.split(','),
                     whole_long_original_re_read_claimed=False, root_adopted=False, cache_admitted=False))

directory = BASE / 'agents/context_latin/birth_root11_independent_v1'
old_hold = read(directory / 'hold_341392_task137_v1.md').decode('utf-8')
new_hold = read(directory / 'hold_341392_task137_v2.md').decode('utf-8')
assert old_hold.split('## 판독 및 경계', 1)[0] == new_hold.split('## 판독 및 경계', 1)[0]
old_sentence = '두 번째 문장은 인용 예고 뒤 실제 발화가 없는 채 끝나고, 마지막 기록의 무자 서술은 앞의 명시 가족표와 연결할 근거가 없다.'
new_sentence = '두 번째 문장에는 실제로 `후령군의 모가 태종에게 쫓겨난 사람인데, 대군들이 복(服)을 입어야 하는가.`라는 발화가 있으나 인용부호가 닫히지 않았다. 마지막 기록의 무자 서술은 앞의 명시 가족표와 연결할 근거가 없다.'
assert old_hold.count(old_sentence) == 1
assert old_hold.replace(old_sentence, new_sentence, 1) == new_hold
speech = '후령군의 모가 태종에게 쫓겨난 사람인데, 대군들이 복(服)을 입어야 하는가.'
assert speech in texts[341392]['original'] and '나이 12세' in new_hold and '나이가 32세' in new_hold
body341 = read(directory / 'reviewed_341392_task137_v1.txt')
assert hashlib.sha256(body341).hexdigest().upper() == '01F4F8539B629B7CD111CF31316AC86731A4F5FD58117E25CCD944AC62F970F7'
before = {resolve(entry['cells'][0]): entry for entry in parse(read(directory / 'review_137_v2.md'))}
after = {resolve(entry['cells'][0]): entry for entry in parse(read(directory / 'review_137_v4.md'))}
assert len(before) == len(after) == 5 and set(before) == set(after)
assert all(before[key]['raw'] == after[key]['raw'] for key in before if key != 'expanded_train:341392')
assert after['expanded_train:341392']['cells'][3] == str(directory / 'reviewed_341392_task137_v1.txt')
assert '](' + str(directory / 'hold_341392_task137_v2.md') + ')' in after['expanded_train:341392']['raw']
read(directory / 'review_137_v3.md')  # Preserve the rejected label/target mismatch, not as the selection.

prior_followup = json.loads(read(AUDIT / 'TWO_BIRTH_FOLLOWUPS_810478_95554_VERIFIED_V1.json'))
assert prior_followup['new_root_or_cache_adoptions'] == 0
assert prior_followup['input_pins'][str((BASE / 'agents/context_controls/birth_root11_independent_v1/expanded_train_810478_reviewed_task232_v1.txt').relative_to(ROOT))] == (
    next(row['body']['sha256'] for row in rows if row['id'] == 'expanded_train:810478'))

counts = dict(Counter(row['context_decision'] for row in rows))
pending = [row['id'] for row in rows if row['context_decision'].endswith('_PENDING')]
assert len(rows) == 34 and set(pending) == {
    'expanded_train:121135', 'expanded_train:79984', 'expanded_train:81208',
    'expanded_train:139681', 'expanded_train:355073'}
read(Path(__file__).resolve())
result = dict(status='ROOT_SOURCE_CONTEXT_ADJUDICATION_WITH_FIVE_SCOPED_FOLLOWUPS_PENDING',
              diagnostic_sources=34, context_explained_without_followup=29,
              source_scoped_followups_pending=5, pending_ids=pending,
              counts=counts, rows=rows, input_pins=pins,
              corrected_341392_sidecar_only=True, corrected_341392_body_unchanged=True,
              corrected_341392_other_review_rows_unchanged=4,
              reused_810478_source_and_body_followup=True,
              automatic_flag_waivers=0, new_root_or_cache_adoptions=0,
              independent_whole_2707_semantic_pass_claimed=False,
              goal_complete=False, training_authorized=False)
out = AUDIT / 'ROOT11_BIRTH_FLAG_CONTEXT_ADJUDICATION_V1.json'
with out.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps(dict(status=result['status'], sources=34, explained=29,
                     pending=pending, counts=counts, root_adopted=0), ensure_ascii=False))
