# A06 v05:82~91 r3 text 보정 사전 변경 계획

## 범위·보존

- source v05 SHA-256: `3C05706AF73A9C10258C166AE8A2BBF009E22A2826448BC770834E69235F6CF0`
- registry SHA-256: `B08D3D752D27AB21B5A1F1A85B06FE52C0E036417C3526522D84D088ECE024FD`
- 90행 text만 직접 보정한다. concept, relations, other_type, locator, 행 순서와 registry 모든 field는 보존한다.

| line | 관계·감사 후보 | 원문 의미 검토 | 보정 방침 |
|---:|---|---|---|
| 90 | `classification,boundary,function`; `FACT_CHAIN_WEAK` | 분류별 점검의 대상은 썼지만, 인계가 실행 순서로 이어지는 동사가 약하다. | 누수면 관로 점검을 우선 배정하고, 응집 불량이면 응집조 점검으로 전환한다고 명시한다. |

## 원복 source 행

```text
응집조 누수 경보 인계 분류|classification,boundary,function||교대 시 응집조 탁도 기록과 누수 감시기 경보가 서로 다를 때, 응집조 누수 경보 인계 분류는 운영자가 실제 누수와 응집 불량을 구분하는 분류 기준이다. 운영자는 누수로 분류하면 다음 당직자에게 관로를 먼저 점검하도록 인계하고, 응집 불량이면 응집조를 점검하게 해 경보 원인을 놓치지 않는다.
```
