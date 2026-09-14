# A06 v02 의미 재서술 사전 변경 계획 — 22~31행 (2026-09-14)

- source v02 SHA-256: `98E127BBBC3963515ACA0D728A9248536F39CC522234D5623FE9A37BF8A01FE2`
- registry SHA-256: `6C284DC813C7F5D88821B1932E04D92C1A21AF2503A7B20D93407D08A9380F2C`
- source concept·text와 동일 locator registry `primary`만 고치며, relations·other_type·registry 비-primary field·비대상 행은 보존한다.

| locator | 새 concept | relations 보존 | 행별 의미 근거 |
|---|---|---|---|
| v02:22 | 함수율 센서 경보와 제어 명령의 승인 순서 | process, state, contrast | 건조 경보·정기 환기·승인 순서를 구분 |
| v02:23 | 배수 압력 예외 운전의 종료 기준 | boundary, role, attribute | 압력계·유량·정비 담당자의 종료 판단 |
| v02:24 | 기상 예보에 따른 환기와 양액 보충의 구분 | boundary, comparison, state | 습도 예보·수위 비교·서로 다른 조치 |
| v02:25 | 순환팬 복귀 전에 확인하는 작업 기록 | process, boundary, role | 정비 완료·공구 확인·팬 기동 차단 |
| v02:26 | 양액 보충과 환기 명령이 겹칠 때의 제어 보류 | state, contrast, comparison | 온실 온도·양액 수위의 비교와 보류 |
| v02:27 | 야간 배수와 압력 점검의 분리 기준 | classification, boundary, function | 세척 알림·저압 경보의 별도 분류 |
| v02:28 | 함수율 경보와 환경 제어 명령의 승인 비교 | process, state, contrast | 건조 경보·습도 제어·재확인 절차 |
| v02:29 | 교대 인계 때 베드 수분과 밸브 위치를 확인하는 기준 | boundary, role, attribute | 인계자·수분값·밸브 위치의 교차 확인 |
| v02:30 | 팬 운전 기록과 기상 예보가 엇갈릴 때의 인계 기준 | boundary, comparison, state | 현재 온도·외기 예보의 우선 판단 |
| v02:31 | 차광막 복귀 중 관수 밸브를 보류하는 절차 | process, boundary, role | 차광막 위치·환기창·밸브 구동 순서 |

updater candidate와 apply 직전 A06 전용 registry backup이 원복 자료다. v01 package·다른 영역·공용 경로는 변경하지 않는다.
