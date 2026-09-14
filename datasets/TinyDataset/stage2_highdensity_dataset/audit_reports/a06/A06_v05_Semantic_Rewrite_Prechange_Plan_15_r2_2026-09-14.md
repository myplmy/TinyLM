# A06 v05:15 text-only 보정 사전 변경 계획

- source SHA-256 (보정 전): `08C85485286FC379810EA900608C6B236C63F3CB44E3CB82D6ACFD811610B27C`
- registry SHA-256: `DBFB297A47A037B165629EDD4D1DA7AEE82EA803288D5E9AB6477ED952262FAA`
- locator: `stage2_(16)relational_composition_high_density_train_v05.source.psv:15`
- `concept`와 relations·other_type·행 순서는 보존한다. text만 바꾸므로 registry는 수정하지 않는다.

| 항목 | 내용 |
|---|---|
| 사후 감사 신호 | `FACT_CHAIN_WEAK`: decision/action, consequence/limit 부족; `comparison` cue 부족 |
| 기존 text | 여과지 예외 운전 기간은 당직자가 여과지 압력과 탁도 값을 비교해 우회 운전을 계속할지 결정하는 승인 상태다. 압력이 정상 범위로 돌아오면 예외 운전과 평상 운전을 구분해 우회 지시를 종료한다. |
| 변경 text | 여과지 예외 운전 기간은 당직자가 여과지 압력과 탁도 값을 비교해 평상 운전보다 우회 운전이 안전한지 선택하는 승인 상태다. 압력이 높을 때에는 우회 운전을 유지하고, 정상 범위로 돌아오면 예외 운전과 평상 운전을 구분해 부적합한 물의 통과를 방지한다. |
| 의미 근거 | `선택`으로 실제 판단을, `평상 운전보다`·`압력이 높을 때`로 비교 축을, `유지`·`방지`로 결과와 제한을 밝혀 관계·상태 의미를 보존한다. |

원복용 source 행:

```text
여과지 예외 운전 기간|boundary,comparison,state||여과지 예외 운전 기간은 당직자가 여과지 압력과 탁도 값을 비교해 우회 운전을 계속할지 결정하는 승인 상태다. 압력이 정상 범위로 돌아오면 예외 운전과 평상 운전을 구분해 우회 지시를 종료한다.
```
