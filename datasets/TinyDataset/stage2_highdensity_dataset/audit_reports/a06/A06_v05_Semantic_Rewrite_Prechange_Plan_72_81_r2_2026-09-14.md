# A06 v05:72~81 r2 text 보정 사전 변경 계획

## 범위·보존

- source v05 SHA-256: `FFC9F4D2B626569486D392C7DB0DF90A5ACBE457F31C6517B672701AFB1A93C2`
- registry SHA-256: `7291F6FCF1561FB2018AE521A41F20A7C6DB62C50EEB6B6B8CAEFBB9CA012533`
- 78행 text만 직접 보정한다. concept, relations, other_type, locator, 행 순서와 registry 모든 field는 보존한다.

| line | 관계·감사 후보 | 원문 의미 검토 | 보정 방침 |
|---:|---|---|---|
| 78 | `classification,boundary,function`; `FACT_CHAIN_WEAK` | 종료 기준이 우회 종료 판단을 돕는다고만 하여, 분류 결과에 따른 담당자의 실제 선택이 약하다. | 누수 지속/경보 해제 분류 뒤 우회 유지 또는 종료 선택과 그 결과를 직접 쓴다. |

## 원복 source 행

```text
응집조 경보 종료 판정 기준|classification,boundary,function||응집조 탁도 경보가 멈췄지만 누수 감시기 경보가 남아 있을 때, 응집조 경보 종료 판정 기준은 운영자가 경보 해제와 실제 누수 지속을 구분하는 분류 기준이다. 이 기준은 여과지 우회 종료 여부를 판단하게 하여 누수 상태에서 운전을 정상으로 되돌리지 않게 한다.
```
