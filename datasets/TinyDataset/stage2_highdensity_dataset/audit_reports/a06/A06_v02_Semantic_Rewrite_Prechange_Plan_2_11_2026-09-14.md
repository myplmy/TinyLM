# A06 v02 의미 재서술 사전 변경 계획 — 2~11행 (2026-09-14)

## 범위와 사전 조건

- source: `sources/train/stage2_(16)relational_composition_high_density_train_v02.source.psv`
- registry: `sources/term_registry/stage2_(16)relational_composition_train_registry_v01_v52.jsonl`
- 수정 전 source v02 SHA-256: `F7928BA8311BA1249C7520186F330E062EE1BB7F57F74C124BCEAE55C669D3BE`
- 수정 전 registry SHA-256: `46F7BAC980C0C09F1E3F88B7524EF5F59435F84D2CCB3C9012F2D4D34CE98D1C`
- locator는 `source_file + source_line`으로 고정한다. source의 concept·text와 동일 locator registry의 `primary`만 변경한다. relations, other_type, registry의 definition/provenance/review_status 및 비대상 행은 변경하지 않는다.

## 변경표

| locator | 기존 concept | 새 concept | relations 보존 | 재서술 근거 |
|---|---|---|---|---|
| v02:2 | 양액 탱크와 환기창의 저부하 운전 충돌 조정 | 양액 보충과 환기 운전의 우선순위 | state, contrast, comparison | 수위·결로 위험·두 설비의 부하를 실제 비교 기준으로 명시 |
| v02:3 | 배수관 우선 압력 조절기의 부분 복구 기준 | 배수관 압력 제어의 부분 복구 기준 | classification, boundary, function | 복구 대상·점검 대상을 구분하고 과압 방지 기능을 밝힘 |
| v02:4 | 원격 관찰에서 함수율 센서와 환경 제어기를 구분하는 환기창 기준 | 원격 관찰에서 센서 값과 제어 명령을 가르는 기준 | process, state, contrast | 관측값과 실행 명령의 시간·역할 차이를 분명히 함 |
| v02:5 | 재배 베드 기록과 관수 밸브 지시 사이의 대체 자원 우선순위 | 관수 기록과 밸브 명령의 대체 수원 우선순위 | boundary, role, attribute | 수분값·수압값·담당자 판단을 연결 |
| v02:6 | 순환팬 운전과 기상 예보가 충돌할 때 양액 탱크 보충을 보류하는 판단 | 저온 예보 때 양액 보충을 미루는 판단 | boundary, comparison, state | 예보 최저기온과 탱크 수온의 비교로 보류 조건을 구체화 |
| v02:7 | 차광 모터와 환기창의 복구 직후 충돌 조정 | 차광막과 환기창을 순서대로 복구하는 절차 | process, boundary, role | 창 위치 확인→차광막 구동 순서와 간섭 방지 역할을 제시 |
| v02:8 | 기상 예보를 우선하는 순환팬 운전의 재검토 경로 | 기상 예보와 실내 온도가 다른 경우의 팬 운전 판단 | state, contrast, comparison | 예보와 센서 값의 상충을 실제 팬 속도 선택으로 연결 |
| v02:9 | 초기 입력에서 관수 밸브와 재배 베드를 구분하는 압력 조절기 기준 | 관수 밸브와 재배 베드의 압력 기록 구분 | classification, boundary, function | 공급 압력과 토양 수분을 분류하고 제어기 기능을 설명 |
| v02:10 | 전원 대기 상태에서 환경 제어기 기록과 함수율 센서 지시의 우선순위 | 비상 전원 대기 중 센서 경보와 제어 기록의 우선순위 | process, state, contrast | 정전 대기·센서 경보·재개 조건을 독립적으로 명시 |
| v02:11 | 압력 조절기와 배수관의 지시가 충돌할 때 작업 기록을 보류하는 판단 | 압력 제어와 배수 작업이 겹칠 때의 기록 보류 | boundary, role, attribute | 배수 유량·공급 압력·임시 상태 기록을 연결 |

## 원복 자료

원문 source 행과 같은 locator의 registry JSON 원문은 이 계획 작성 직전의 A06 registry backup 및 source SHA-256으로 보존한다. 이번 묶음에 대해서는 updater가 target 10개·비대상 line byte mismatch 0·비-primary field 변화 0을 사전 확인한 candidate와, apply 직전 생성하는 A06 전용 registry backup을 함께 보존한다.

## 제외 확인

v01, A01~A05, 공용 `train/`·`val/`, manifest, 중앙 원장, checkpoint, 공용 감사기는 이 변경 묶음에서 읽기 전용이며 변경하지 않는다.
