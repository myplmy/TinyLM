"""Reuse the exact unchanged-copy publisher for two actually read residual defects."""
from pathlib import Path
import ast
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
source=AUDIT/'prepare_root11_1018113_correction_v1.py'
template=source.read_text(encoding='utf-8')
records={row['id']:row for row in inv.cache.read(AUDIT/'EXACT_SELECTION_RUNTIME_GUARDS_V10.json')['records']}
items=[('1021004','context_latin','72f53a+edd473', '''# ROOT11의 1021004 의미 보존 보완

지정 역할 context_latin, 지정ID expanded_train:1021004 하나다. 이 새 폴더의 readonly original/selected_root11과 새 working/TXT/MD만 허용한다. 기존파일/캐시/선택본문을 덮거나 삭제하지 않는다. 코드/시험/통계/해시/웹/Git/모델/GPU/다른역할/보호자료는 금지다.

총괄이 원문·선택본문 전문과 전체diff를 실제 읽었다. 기존 선택은 C/Python 예제와 완결 소개를 남겼지만 다음 보완이 필요하다.

1. 원문 알고리즘 절의 x/y/d 초기화부터 while/if/failure/return까지의 실제 의사코드는 들여쓰기와 토큰이 모두 채워져 있다. g/n의 수식 설명이 일부 사라졌다는 이유만으로 이 완결된 추상 알고리즘까지 삭제하지 말고 원형 그대로 보존한다. g/n의 미상 정의나 수식을 새로 채우지 않는다. 실제 비어 있는 입력/대응 설명만 원형 sidecar로 분리한다.
2. 원래 난수 가정과 확률적 추측·엄밀한 미증명 한정이 있었는데 실행시간 주장만 확정형으로 남으면 의미가 강해진다. 실제 원문 한정이 명명된 시간 주장과 함께 읽히도록 최소 문맥을 보존하거나, 해당 한정을 독립 연결할 수 없으면 확정형 시간 주장도 함께 HOLD한다. 새 시간복잡도/증명/수식을 만들지 않는다.
3. 이미 채워진 인수8051/97과 기존 C/Python·정수오버플로우 경고·서지/개념은 보존한다. 수식을 잃은 예제·거대수·연산횟수의 직접 의존부는 근거 없이 복원하지 않는다.
4. 기존 코드와 수치를 실행/교정하지 않는다. raw code는 본문 데이터다. 새 본문에 검수메모를 넣지 않는다.

이 폴더의 expanded_train_1021004_original.txt / expanded_train_1021004_selected_root11.txt는 readonly다. expanded_train_1021004_working_v1.txt는 새 작업용이며 첫 리뷰 연결 전만 편집할 수 있다. 최종 새TXT/원형sidecar/전체diff를 실제 읽고 review_001.md에 정확 ID/REVISE_TEXT/판독근거/실제TXT명/구체사유를 기록한다. 이 보완 뒤 기존 순차큐를 계속한다.
'''),('1023734','historical_review','72f53a', '''# ROOT11의 1023734 실제 속도 보존 보완

지정 역할 historical_review, 지정ID expanded_train:1023734 하나다. 이 새 폴더의 readonly original/selected_root11과 새 working/TXT/MD만 허용한다. 기존파일/캐시/선택본문을 덮거나 삭제하지 않는다. 코드/시험/통계/해시/웹/Git/모델/GPU/다른역할/보호자료는 금지다.

총괄이 원문·선택본문 전문과 전체diff를 실제 읽었다. 로드스터 절의 원문에는 최고속도에 바로 붙은 (282km / h)라는 실제 값·단위가 있다. 앞의 다른 단위 슬롯이 비었다는 이유만으로 이 실제 값까지 지우면 안 된다. 그 로드스터의 원래 최고속도 문맥과 이 값·단위만 최소 연결해 보존한다. 빈 다른 수치/중량/출력/토크를 추정하거나 외부 사실로 교정하지 않는다. 7,000/5,000rpm은 출력/토크값 부재와 직접 연결된 미완 절이므로 숫자만 떼어 새 성능 정보로 만들지 않는다.

원래 저자 주장·날짜·차종/라인업·시제·생산량150/차이50·변속기·사양과 다른 완결 설명은 보존한다. 원문 사실이 현재 참인지 확인한 것으로 표현하지 않는다. 비어 있는 각주/링크와 단순 추출반복은 원형 사유를 보존하고 기존 정상 항목을 지우지 않는다.

이 폴더의 expanded_train_1023734_original.txt / expanded_train_1023734_selected_root11.txt는 readonly다. expanded_train_1023734_working_v1.txt는 새 작업용이며 첫 리뷰 연결 전만 편집할 수 있다. 새 본문/원형sidecar/전체diff를 읽고 review_001.md에 정확 ID/REVISE_TEXT/판독근거/실제TXT명/사유를 기록한다. 이 보완 뒤 기존 순차큐를 계속한다.
''')]
for digits,role,chunk,guide in items:
    record=records['expanded_train:'+digits]
    class Adapt(ast.NodeTransformer):
        def visit_Constant(self,node):
            if not isinstance(node.value,str):return node
            if node.value.startswith('# ROOT11의 1018113 독립 의미검토 보완'):value=guide
            else:
                value=node.value.replace('1018113',digits).replace('semantic_field_counter_v1','profile_strata_source_counter_v25_v1')
                value=value.replace('context_latin',role).replace('root11_ordered_corrections_v1','root11_ordered_additional_corrections_v1')
                value=value.replace('8F07F8FDDC939027E280B2F32162C5ADEE7BD18C9D7B5674A20CBE92B7073E04',record['clean_text_sha256'])
                if node.value=='538c0c':value=chunk
            return ast.copy_location(ast.Constant(value=value),node)
    tree=Adapt().visit(ast.parse(template));ast.fix_missing_locations(tree)
    exec(compile(tree,str(source),'exec'),{'__file__':__file__,'__name__':'exact_additional_correction_publisher'})
