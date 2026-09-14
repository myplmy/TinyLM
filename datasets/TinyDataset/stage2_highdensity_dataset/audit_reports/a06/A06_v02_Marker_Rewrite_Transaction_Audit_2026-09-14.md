# A06 v02 표식형 primary 재서술 — 10 locator 트랜잭션 감사

## 결과

v02의 source line 2~11과 같은 10 registry locator를 함께 갱신했다. source의 실제 필드는 legacy PSV `concept`, registry의 대조 복사값은 `primary`이며, `source_file + source_line` locator·relations·other_type·행 순서는 보존했다.

| 항목 | 수정 전 | 수정 후 | 판정 |
|---|---:|---:|---|
| v02 source SHA-256 | `7E732D...BBFB647` | `FEAC96...7A25CA` | 변경 10행 반영 |
| registry SHA-256 | `15A942...D98C29` | `3AD693...EC17EE` | 변경 10 locator 반영 |
| source / registry records | 7,800 / 7,800 | 7,800 / 7,800 | PASS |
| source-only / registry-only locator | 0 / 0 | 0 / 0 | PASS |
| source concept ↔ registry primary 불일치 | 0 | 0 | PASS |
| registry 비대상 행 바이트 불일치 | — | 0 | PASS |
| target 비-primary registry field 변경 | — | 0 | PASS |
| v01 source SHA-256 | `9607FA...74F610` | 동일 | PASS |

## 안전한 갱신 경로

1. v02:2~11의 기존·신규 concept, relations 보존, 원복 원문을 [사전 변경 계획](A06_v02_Marker_Rewrite_Prechange_Plan_2026-09-14.md)에 확정했다.
2. A06 전용 updater를 비정본 12행 fixture에서 실행했다. 지정 10 locator만 수정하고 비대상 byte mismatch 0을 확인했다.
3. 실제 registry 후보 7,800행을 생성해 JSON parse 오류 0, target 10행, 비대상 행 byte mismatch 0, 비-primary field 변화 0을 확인했다.
4. source 10행을 직접 재서술한 뒤 검증된 registry 후보를 같은 디렉터리 rename으로 적용했다. 적용 전 registry recovery snapshot은 그대로 보존했다.

`definition`과 `review_status`는 이번 10행에서 개념의 의미 범주가 바뀌지 않았고, 영역 전체 semantic review를 완료한 것도 아니므로 변경하지 않았다.

## 판정 범위

트랜잭션과 구조는 통과했다. A06 전체 자연성·TF-IDF·Jaccard·조사 감사는 v02~v52 표식형 primary 재서술이 끝난 뒤에만 다시 수행한다. package·checkpoint·manifest projection은 source-only 범위 밖이므로 실행하지 않았다.

상세 기계 결과: [A06_v02_Marker_Rewrite_Transaction_Audit_2026-09-14.json](../machine/a06/A06_v02_Marker_Rewrite_Transaction_Audit_2026-09-14.json)
