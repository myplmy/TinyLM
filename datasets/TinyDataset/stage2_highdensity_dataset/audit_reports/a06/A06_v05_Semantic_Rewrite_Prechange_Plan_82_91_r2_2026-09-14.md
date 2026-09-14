# A06 v05:82~91 r2 text 보정 사전 변경 계획

## 범위·보존

- source v05 SHA-256: `DF6DF95224AEA96FA02886A086129C03AF8955C0F695263829D4192F03D7346D`
- registry SHA-256: `B08D3D752D27AB21B5A1F1A85B06FE52C0E036417C3526522D84D088ECE024FD`
- 84·90행의 text만 직접 보정한다. concept, relations, other_type, locator, 행 순서와 registry 모든 field는 보존한다.

| line | 관계·감사 후보 | 원문 의미 검토 | 보정 방침 |
|---:|---|---|---|
| 84 | `classification,boundary,function`; `FACT_CHAIN_WEAK` | 기준이 출력 감소를 돕는다고만 하여 누수/전송 지연 분류 뒤 행동이 약하다. | 누수면 출력 감소, 전송 지연이면 출력 유지라는 선택을 명시한다. |
| 90 | `classification,boundary,function`; `FACT_CHAIN_WEAK` | 다음 당직자의 점검 순서가 일반론으로 끝난다. | 실제 누수와 응집 불량의 분류별 점검 대상과 인계 행동을 명시한다. |

## 원복 source 행

```text
고부하 누수 경보 판별 기준|classification,boundary,function||펌프 유량이 높은데 방류 기록과 수질 계측기 값이 다를 때, 고부하 누수 경보 판별 기준은 운영자가 관로 누수와 계측기 전송 지연을 구분하는 분류 기준이다. 이 기준은 운영자가 펌프 출력을 줄일지 결정하도록 도와 실제 누수 상태의 압력 저하를 줄인다.
응집조 누수 경보 인계 분류|classification,boundary,function||교대 시 응집조 탁도 기록과 누수 감시기 경보가 서로 다를 때, 응집조 누수 경보 인계 분류는 운영자가 실제 누수와 응집 불량을 구분하는 분류 기준이다. 이 분류는 다음 당직자가 먼저 점검할 설비를 정하도록 해 경보 원인을 놓치지 않게 한다.
```
