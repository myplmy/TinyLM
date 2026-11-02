"""List complete assigned coordinate-table strata without changing any body."""
from collections import defaultdict
from pathlib import Path
import json
import re

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'data_cache/p106b_hold_resolution_v1_20261027_goalc'
GROUP=BASE/'repeat_named_roles_counter_v2'
target=GROUP/'ROOT_MEDIATION_V2.md'
assert not target.exists()
manifest=json.loads((GROUP/'manifest.json').read_text(encoding='utf-8'))
by_role=defaultdict(list)
for row in manifest['rows']:
    with (ROOT/row['original']['path']).open(encoding='utf-8') as stream:
        prefix=stream.read(1500)
    if re.match(r'^(북위|남위|동경|서경)[ ]*[0-9]+도',prefix) and '|-' in prefix:
        by_role[row['role']].append(row['id'])
lines=['# 좌표 경로표와 다른 결손의 추가 중재','',
 'ROOT_MEDIATION_V1 및 START/TASK의 정확 입력 경계와 함께 읽는다. 아래 목록은 지정732 안에서 도입부 형태를 읽어 분류한 표 전량이며 전체 내용 판독/정제/채택 증거가 아니다. 자기 역할의 ID만 자기 TASK에 있는 정확 입력으로 읽고 다른 역할 입력을 따라가지 않는다.','',
 '표에 실제 채워진 바다/섬/주/지명·방향·거리·순서·축·셀 구조는 유지한다. 빈 국가/좌표는 추정하지 않는다. 미상 소유국을 받는 고립 조사만 제거하면 실제 명명된 섬/방향이 완결될 때는 그 좁은 서식만 분리할 수 있다. 관리/분쟁/영유권 주체 자체가 없으면 해당 미상 관계절을 원형 sidecar에 보류한다.','',
 '행에 실제 명명 대상이 있으면 그 행의 거리/방향은 독립적으로 이해될 수 있다. 대상 없는 빈 행의 약7km/8km만으로 통과 지역을 만들지 않는다. 두 지명이 하나의 불완결 관계절 안에만 있다면 관련성 없는 이름 목록으로 바꾸지 않고 그 관계절 전체를 원형에 보존한다.','',
 '도입부와 표제가 서로 다른 경도/위도 숫자를 주는 경우 하나를 자동 선택하거나 표 전체를 특정 값에 연결하지 않는다. 정확 좁은 경계를 총괄에 질문하고 다른 독립 TASK를 계속한다. 305748의131/130은 별도 중재 대상이다.','',
 '반복 역할이 정상이어도 원래 수식/변수/대상/조건 결손이 남아 있으면 전체 후보 수용으로 종결하지 않는다. 실제 독립 본문/표를 보존하면서 미상 식과 직접 의존부만 새 sidecar로 분리하고 새 전체 TXT를 작성한다. 이미 완결한 설명은 수식이 없다는 이유만으로 버리지 않는다. 예외/미결을 근거 열에 적고 출력 열에는 정확 TXT basename 하나만 쓴다.','',
 '원형과 이전 리뷰는 덮지 않는다. 앞서 수용한 자기 표에서 추가 결손을 발견하면 새 본문과 전체5행 교정 리뷰를 남긴다. 다음 자기 TASK에서도 이 경계를 적용한다. 전체 다른 유형을 현재 표 규칙으로 자동 해제하지 않는다.','']
for role,ids in sorted(by_role.items()):
    lines.extend(['## '+role,'',', '.join(ids),''])
with target.open('x',encoding='utf-8') as stream:
    stream.write(chr(10).join(lines))
print(json.dumps(dict(assigned_coordinate_tables={role:len(ids) for role,ids in by_role.items()},
    body_changed=0,cache_admitted=0),ensure_ascii=False))
