# A06 v02 의미 재서술 사전 변경 계획 — 72~81행 (2026-09-14)

- source SHA-256: `51C15BC5ED973496F21CF7D9AAB4EF53EF379AD695514DDEF1DDBAC54D5E4FBD`
- registry SHA-256: `D70A887A0A6F86FC3312FA912CDDFECF188ABD69B3E323AA0B4EDF850A8865CA`
- source concept·text 및 같은 locator registry primary만 변경; relations·other_type·registry 비-primary field와 비대상 행은 보존.

| locator | 새 concept |
|---|---|
| v02:72 | 환기와 양액 보충이 함께 필요한 때의 조정 기준 |
| v02:73 | 정비 기록 중 순환팬 통신을 재시도하는 절차 |
| v02:74 | 양액 수위와 환기 상태를 따로 판단하는 기준 |
| v02:75 | 배수 유량 기록과 압력 경보의 인계 순서 |
| v02:76 | 건조 경보와 환기창 명령이 겹칠 때의 보류 |
| v02:77 | 베드 수분 확인 뒤 관수 밸브를 복귀하는 절차 |
| v02:78 | 한랭 예보 뒤 팬 운전을 재검토하는 기준 |
| v02:79 | 정전 뒤 차광막과 환기창을 구분해 복구하는 절차 |
| v02:80 | 예보 변화 중 팬 속도를 다시 정하는 기준 |
| v02:81 | 관수 압력과 베드 수분 경보가 함께 올 때의 제어 보류 |

candidate·A06 전용 backup·post-audit만 사용하고 v01 package와 금지 경로는 변경하지 않는다.
