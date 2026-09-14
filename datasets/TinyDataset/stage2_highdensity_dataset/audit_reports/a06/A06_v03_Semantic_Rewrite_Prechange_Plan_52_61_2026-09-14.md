# A06 v03 의미 재서술 사전 변경 계획 — locator 52~61 (2026-09-14)

- precondition: source v03 `71C2A45A53DBE2D32A56EE18ABCD2088AF072302844B48B1A2ED91A79229D5DE`, registry `43FCB877D893297EFF95DC8B0A974159175D1FA4C72739501CF10D5FB185E08D`.
- source line 52~61의 `concept`·`text`와 정확히 같은 locator registry `primary` 10개만 변경한다. relations, `other_type`, non-primary registry field, 순서 및 비대상 바이트는 보존한다.

| locator | 새 concept | relations | 판단 |
|---|---|---|---|
| 52 | 관수 밸브 기록이 끊긴 배수관 부분 관계의 보류 | part_of, state, other | 밸브 기록 공백과 동시 개입 때문에 배수관 부분 관계를 확정하지 않는다. |
| 53 | 새벽 제어기 기록과 탱크 수위 연결을 미확인으로 두는 상태 | state, boundary, other | 새벽의 한 번뿐인 명령·수위 기록은 보충 경로로 확정하지 않는다. |
| 54 | 압력 조절 표본 부족 시 차광 모터 연결을 보류하는 절차 | process, other, role | 압력 변화와 차광 조작을 예외 승인으로 묶지 않는다. |
| 55 | 환기창 기록이 없는 베드 상태의 분류 | classification, boundary, state | 환기창 기록 없이 베드 온도만으로 환기 상태를 분류하지 않는다. |
| 56 | 작업 기록만 있을 때 압력 조절 상태 비교를 보류하는 기준 | state, comparison, other | 작업표만으로 압력 센서값을 같은 조정 상태로 비교하지 않는다. |
| 57 | 탱크 관측 공백에서 제어기 명령을 해석하는 경계 | process, boundary, attribute | 수위·농도 공백에서 제어기 명령의 결과를 해석하지 않는다. |
| 58 | 정기 운전에서 배수관과 밸브의 부분 관계 보류 | part_of, state, other | 다음 입력이 없는 정기 운전의 배관·밸브 부분 관계를 보류한다. |
| 59 | 수분 표본 부족 시 순환팬 연결을 보류하는 상태 | state, boundary, other | 중간 수분 관측이 없을 때 팬 운전과 수분 변화의 연결을 보류한다. |
| 60 | 베드 기록이 없는 차광 모터 출처를 확인하는 절차 | process, other, role | 모터 조작의 출처를 베드 상태로 추정하지 않고 작업자 기록을 확인한다. |
| 61 | 순환팬 기록만 있을 때 압력 조절 상태를 분류하지 않는 기준 | classification, boundary, state | 팬 기록만으로 압력 조절기의 회복 상태를 분류하지 않는다. |

각 행의 새 text는 구체적 결측·대상·담당자 판단·오판 방지 결과를 독립적으로 담는다. 반영 시 updater가 target 10·비대상 7,790 registry 행 byte 보존을 확인하고 backup은 `A06_registry_before_v03_semantic_rewrite_52_61_2026-09-14.jsonl`로 남긴다.
