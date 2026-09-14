# A06 v02 의미 재서술 사전 변경 계획 — 12~21행 (2026-09-14)

## 사전 조건

- source v02 SHA-256: `B90F7D8B178BE3C99E6DF918788615D351818BED260CFC1E8B4130DBF1EEE406`
- registry SHA-256: `57081D03F38E7E1612462A45F0B7324D52DD07A001EFAA97B00962F1370E9457`
- source의 concept·text와 동일 locator registry의 `primary`만 변경한다. relations·other_type·registry의 다른 field와 비대상 행은 보존한다.

| locator | 새 concept | relations 보존 | 재서술 기준 |
|---|---|---|---|
| v02:12 | 환기와 양액 보충이 겹칠 때의 운전 순서 | boundary, comparison, state | 온도 하락·수위 하락·창 개방 폭의 실제 비교 |
| v02:13 | 순환팬 예외 운전의 사전 확인 절차 | process, boundary, role | 야간 센서·창 위치·작업자 확인의 순서 |
| v02:14 | 양액 수위와 환기 상태가 엇갈릴 때의 제어 기준 | state, contrast, comparison | 수위·수온·재배동 온도 기준의 대비 |
| v02:15 | 배수 기록과 압력 경보의 처리 순서 | classification, boundary, function | 유량과 압력의 서로 다른 원인 분류 |
| v02:16 | 수분 경보와 환기 명령이 충돌할 때의 창 조정 | process, state, contrast | 두 신호 재확인과 관수·환기 우선 결정 |
| v02:17 | 관수 복귀와 베드 점검이 겹칠 때의 승인 기준 | boundary, role, attribute, other | `동시 개입 분리 불가`를 실제 보류 조건으로 설명 |
| v02:18 | 한랭 예보 중 순환팬 운전 확인 | boundary, comparison, state | 실내 하강 속도·외기 예보의 비교 |
| v02:19 | 차광막 복귀와 환기창 복귀의 순서 | process, boundary, role | 차광막·환기창·관수 밸브의 안전 순서 |
| v02:20 | 기상 예보와 팬 기록이 엇갈릴 때의 판단 | state, contrast, comparison | 현재 온도와 예보 온도의 비교 |
| v02:21 | 관수 지시와 압력 경보가 함께 올 때의 보류 기준 | classification, boundary, function | 건조 알림과 저압 경보의 원인 분리 |

원복용 registry backup은 apply 직전에 A06 전용 machine 경로에 만들고, updater가 target 10개와 비대상 바이트 보존을 사전 검증한다. v01·package·다른 영역·공용 파일은 제외한다.
