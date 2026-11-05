# 새 발견 두 원문의 본문 없는 보류 경계

현재 전체 정제 승인 안에서 32895와74587 두 행을 원형 추가 판독 없이 분리한다. 앞선 guard4와 cache15 증거는 변경하지 않는다. 32895는 핵물질 처리 절차 우려, 74587은 일반 역사·사양 외에 구체 부품 조작과 조준·사용 지침까지 발견된 사례다. 해당 분야의 모든 문서를 민감으로 확정하는 규칙이 아니다. 일반 JIT 설명825214는 이 제한에 넣지 않는다.

| 안 | 내용 | 장점 | 단점 | 영향/비용 |
|---|---|---|---|---|
| A | 기존 문자 지시만으로 두 ID를 건너뜀 | 즉시 가능 | 다른 ID·후보 SHA·부모 alias 우회 감지 부족 | 구현 낮음/재발 위험 |
| B | 원형을 다시 열어 새 부분 본문 작성 | 일반 본문 회복 가능성 | 불필요한 위험 세부 재노출·판독 미완 | 데이터 영향 큼/판독 비용 큼 |
| C | metadata 계보를 기존 guard에 누적하고 새 판독·수집 전 차단 | ID·원형/후보SHA·부모alias 연결, 본문 추가 판독0 | 새 entry/collector/다음 cache에 계약 결합 필요 | 국소 코드/검증 중간 |

권장 및 수행: C. 이미 발견한 부분 외에 추가 원문을 열지 않고 독립 작업을 계속한다. 전체 HOLD를 민감으로 재분류하지 않는다. 새 본문을 작성하지 않는다.

| 파일·경로 | 동작 | 권한 근거 | 제외 |
|---|---|---|---|
| 본 audit의 prepare_guarded_metadata_contract_v5.py·GUARDED_SOURCE_METADATA_CONTRACT_V5.json | 새 코드·metadata 계약 | goal1·6의 CPU 전처리/관련 구현·시험, 현재 전체정제 재개 | raw/후보/packet 열기·해시0 |
| 본 audit의 active_guard_v5_preflight_v1.py·scoped_lossless_review_entry_v4.py·새 scope/wrapper V5·tmp/hold-*-lossless-v5 | 새 판독 전 metadata 차단 | 동일5역할/동일허용 입력의 보호 보강 | .agents/.codex 수정0·권한 확대0 |
| 본 audit의 collect_root12_counter_v8.py·시험·새 snapshot | 기존수집 재사용+두 정확 metadata HOLD | goal1·6 CPU 검증 | corpus TXT작성0·원형덮기0 |
| 본 audit의 advance_counter_selection_v4.py·collect_exact_reviews_guarded_v9.py·advance_reviewed_roster_v3.py | 기존선택/수집/원장조인 재사용에 guard5 선결만 결합 | 같은 goal1·6과 전체잔여정제 승인 | 새2행 본문채택0·원형덮기0·기존3안전파생본문 변경0 |
| 다음 full cache | 지금 실행하지 않음 | 선택/roster/opaque/census 누적 뒤 한 번 생성 | guard5 선결·전체동시1 |

| 축 | 영향 |
|---|---|
| 코드 | 기존 metadata projector/observer/strict collector/무손실 core 재사용. 새2행만 metadata branch. 기존 파일 고정SHA 불변. |
| 데이터 | 기존 guard4 모든 ID/SHA/metadata 그대로 + 두 source 원형/후보SHA와 부모alias 추가. 원형·기존 캐시 변경0. |
| 시험 | 원형/후보SHA/alias/잘못된 역할 차단, 새보류행 채택거절, 기존 정상판독/무손실21회귀 유지. |
| 정본 | 진행WIP·감사근거만 현재 갱신. 최종 재계측/학습재개 판정 전 METHODS/기준표/COMPASS 종결 갱신은 미완. 모델 지표 영향 없음. |
| 부채·우선순위 | frozen guard4 경로를 새 허가로 읽지 않는다. 이후 모든 reader/수집/선택/다음 cache는 guard5 사전검사 또는 exact metadata disjointness 필요. 반복 전체 캐시 생성 금지. |
| GPU/모델 | CPU metadata·텍스트만. GPU·학습·모델 로딩 없음. |
| 소유권 | 원형/고정후보/로그/캐시/타세션·TinyDataset 보존. 정확 새 audit/tmp만 작성. |
| 비교조건 | 기존 토크나이저·분할·학습풀 의미 변경 없음. 보호행은 HOLD 유지. |
| 증거수준 | guard 통과는 전체 사실검증·학습품질·보안 sandbox 증명이 아님. filename observer는 프로세스 내부 진단. |
| 문서연쇄 | 공식 cache15 H105824 유지, ROOT30의344위치는 다음캐시 검증전 미반영. 전체 A–E 미완. |
