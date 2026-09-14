# A06 v05:24 text-only 보정 사전 변경 계획

- source SHA-256 (보정 전): `75D7CE503780EA817832696204C5311EA44CFA0421F0629A823A11CB712C403F`
- registry SHA-256: `9507368F33308521F4B445264C2B65341398C664DA9BA6C8D39E4BEFAD8C0B0F`
- locator: `stage2_(16)relational_composition_high_density_train_v05.source.psv:24`
- primary·relations·other_type·행 순서와 registry는 보존한다. text만 보정한다.

| 항목 | 내용 |
|---|---|
| 사후 감사 신호 | `FACT_CHAIN_WEAK`: decision/action 및 consequence/limit 단서 부족 |
| 기존 text | 고부하 누수 경보 분류는 누수 감시기가 보내는 압력 저하 신호를 수질 계측기 이상과 구분해, 관리자가 펌프 정지 필요 여부를 판단하도록 돕는 분류 기준이다. 잘못된 경보 때문에 급수를 멈추지 않게 한다. |
| 변경 text | 고부하 누수 경보 분류는 누수 감시기가 보내는 압력 저하 신호를 수질 계측기 이상과 구분해, 관리자가 펌프를 멈출지 계속 돌릴지 결정하도록 돕는 분류 기준이다. 실제 누수가 아닌 경보로 급수를 중단하는 일을 방지한다. |
| 의미 근거 | 두 설비 신호의 분류·경계를 유지하면서 구체 선택과 급수 중단 방지 결과를 밝혀 감사 신호를 해소한다. |

원복용 source 행:

```text
고부하 누수 경보 분류|classification,boundary,function||고부하 누수 경보 분류는 누수 감시기가 보내는 압력 저하 신호를 수질 계측기 이상과 구분해, 관리자가 펌프 정지 필요 여부를 판단하도록 돕는 분류 기준이다. 잘못된 경보 때문에 급수를 멈추지 않게 한다.
```
