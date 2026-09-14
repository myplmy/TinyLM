# A06 v02 의미 재서술 사전 변경 계획 — 42~51행 (2026-09-14)

- source v02 SHA-256: `F698C07C5FA07041016942DC5339AAF7D7D05332BA8F9CCCA0DC3EE1C1D4B749`
- registry SHA-256: `3B234F84DC101CCCE35339D8F1F2CF907826B1205F6D9DA51CEA30C065B6A6FC`
- 같은 locator의 source concept·text와 registry primary만 변경한다. relation labels·other_type·비대상 bytes와 registry 비-primary field는 보존한다.

| locator | 새 concept | 관계 | 의미 근거 |
|---|---|---|---|
| v02:42 | 한랭 예보와 팬 운전이 겹칠 때의 속도 조정 | boundary, comparison, state | 외기 예보·실내 온도·팬 속도 선택 |
| v02:43 | 차광막 복구 중 환기창을 보류하는 절차 | process, boundary, role | 장치 위치 확인·모터 역할·순서 제한 |
| v02:44 | 함수율 변화와 팬 운전 예보를 함께 보는 기준 | state, contrast, comparison | 수분 변화와 온도 예보의 상충 비교 |
| v02:45 | 관수 밸브와 베드 급수의 대체 수원 분류 | classification, boundary, function | 수원 상태·밸브·베드 처방의 분류 |
| v02:46 | 건조 경보와 환기 제어가 충돌할 때의 팬 보류 | process, state, contrast | 함수율·습도·팬 기동의 재판정 |
| v02:47 | 배수 압력 복구와 세척 작업의 충돌 조정 | boundary, role, attribute | 압력·유량·정비자의 작업 분리 |
| v02:48 | 환기창 우선 운전 뒤 양액 보충을 재검토하는 기준 | boundary, comparison, state | 환기 상태·수위·온도 차 비교 |
| v02:49 | 정비 기록과 팬 복귀 상태를 확인하는 절차 | process, boundary, role | 정비자 기록·실제 장치 상태의 분리 |
| v02:50 | 비상 전원 대기 중 양액 보충과 환기 명령의 순서 | state, contrast, comparison | 전원·수위·환기 명령의 우선 비교 |
| v02:51 | 배수 압력 경보와 베드 관수 기록이 상충할 때의 보류 | classification, boundary, function, other | `식별 기록 상충`과 별도 확인 경로 |

updater candidate·A06 backup·post-audit만 사용한다. v01 package, 다른 영역, 공용 경로는 변경하지 않는다.
