# A06 v05:62~71 r2 text 보정 사전 변경 계획

## 범위·보존

- source v05 SHA-256: `C2FE65EB132B9D88E6FF22526D09EC53CC5276F9AA4BCD7978EC55D6BDEB6FA6`
- registry SHA-256: `7C0F8E813DF9F050610FBB8E56F90552DA5E514DC22D83F56B96741A70779992`
- 65·66행의 text만 직접 보정한다. concept, relations, other_type, locator, 행 순서와 registry 모든 field는 보존한다.
- v01, 다른 영역, package train/val, manifest, 중앙 원장, checkpoint, 공용 감사기는 수정하지 않는다.

| line | 관계·감사 후보 | 원문 의미 검토 | 보정 방침 |
|---:|---|---|---|
| 65 | `state,contrast,comparison,other`; `RELATION_CUE_GAPS` | `대체 경로 기록 결측`과 주입 보류의 근거는 있으나, 평상·비상 주입 중 어느 전환을 보류하는지가 불명확하다. | 농도 확인 전 평상 주입에서 저유량 비상 주입으로 바꾸지 않는다고 명시해 상태·대조·비교를 모두 근거화한다. |
| 66 | `classification,boundary,function`; `FACT_CHAIN_WEAK` | 누수/응집 불량 분류와 우회 판단의 연결이 일반론으로 끝난다. | 분류 결과별 실제 보류·선택 행동과 처리수 보존 결과를 명시한다. |

## 원복 source 행

```text
염소 주입 비상 운전 보류|state,contrast,comparison,other|대체 경로 기록 결측|염소 주입기 기록이 비어 있고 배수문 개방 지시만 남았을 때, 염소 주입 비상 운전 보류는 당직자가 평상 주입과 저유량 비상 주입을 비교하는 보류 상태다. 대체 경로 기록 결측 때문에 농도 확인 전에는 비상 주입을 시작하지 않아 과염소 방류를 막는다.
응집조 수질 경보 분류 기준|classification,boundary,function||응집조 탁도 경보가 울리고 누수 감시기에도 알림이 뜰 때, 응집조 수질 경보 분류 기준은 운영자가 관로 누수와 실제 응집 불량을 구분하는 기준이다. 이 기준은 여과지 우회가 필요한지 판단하게 하여 정상 수질의 물을 버리지 않게 한다.
```
