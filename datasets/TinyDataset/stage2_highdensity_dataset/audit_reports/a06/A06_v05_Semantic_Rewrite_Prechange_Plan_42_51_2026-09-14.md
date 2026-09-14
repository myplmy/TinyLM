# A06 v05:42~51 의미·자연성 재서술 사전 변경 계획

## 범위와 보존 조건

- source SHA-256: `9328270908AD476E56B5FEE07D1717224FFED2ADA7D3D9F343CD666CE89D4DE7`
- registry SHA-256: `CDDBCE4AA2C2ADA966227D48422F569E4CA8A6FF1933A25383B58645831BD891`
- locator `stage2_(16)relational_composition_high_density_train_v05.source.psv:42~51`만 바꾸며 행 삽입·삭제·순서 변경은 하지 않는다.
- source concept/text와 같은 locator registry primary만 바꾸고 relations·other_type·registry 비-primary field·v01·다른 영역·package train/val·manifest·중앙 원장·checkpoint·공용 감사기는 보존한다.
- registry의 원복 전체 바이트는 반영 직전 backup `A06_registry_before_v05_semantic_rewrite_42_51_2026-09-14.jsonl`로 보존한다.

| line | 기존 concept → 새 concept | relations | 직접 재서술 요지 |
|---:|---|---|---|
| 42 | 응집조와 누수 감시기의 대체 경로 충돌 조정 — 분기 기록 → 응집조 누수 대응 분류 | `classification,boundary,function` | 우회 밸브 조작과 실제 누수를 분류하고 운전자가 대응을 고르는 기능을 쓴다. |
| 43 | 저수조 우선 방류 기록 예외의 승인 전 경로 — 중간 판정 → 저수조 방류 예외 승인 절차 | `process,state,contrast` | 수위 상한·빈 방류 기록 때 승인 전 보류 상태와 평상 방류와 다른 제한을 쓴다. |
| 44 | 승인 후에서 누수 감시기와 응집조를 가르는 정수 펌프 기준 — 신호 전달 → 정수 펌프 운전 승인 기준 | `boundary,role,attribute` | 압력값·수위의 불일치에서 관리자가 누수와 유입량 조절을 구분한다. |
| 45 | 배수문 기록과 염소 주입기 지시의 현장 인계 우선순위 — 대상 추적 → 배수문 인계 우선순위 | `boundary,comparison,state` | 교대 때 기록과 지시를 대조해 승인된 운전 상태를 인계한다. |
| 46 | 수압 센서와 정수 펌프가 만날 때 응집조를 보류하는 판단 — 순서 기록 → 응집조 가동 보류 결정 | `process,boundary,role` | 압력·유량이 동시에 바뀐 뒤 운영자가 고장/원수 부족을 구분하고 가동을 보류한다. |
| 47 | 여과지와 운영 당직표의 새벽 판독 충돌 조정 — 상태 묶음 → 여과지 새벽 운전 조정 | `state,contrast,comparison` | 새벽 교대의 탁도 차이에서 평상·임시 운전 상태를 비교한다. |
| 48 | 방류 기록 우선 수질 계측기 예외의 통신 재시도 경로 — 우선 처리 → 수질 계측기 통신 재시도 기준 | `classification,boundary,function,other` | 통신 오류와 식별 기록 상충을 분류하고 재전송 기능의 경계를 쓴다. |
| 49 | 우천 관찰에서 원수 유입구와 응집조를 가르는 운영 당직표 기준 — 연결 확인 → 우천 응집조 유입 조절 | `process,state,contrast` | 우천 신호 뒤 유입량을 조절하고 평상 유입과 다른 상태를 쓴다. |
| 50 | 수질 계측기 기록과 방류 기록 지시의 교대 기록 우선순위 — 출처 대조 → 교대 방류 기록 확인 | `boundary,role,attribute` | 교대자가 수치·시각을 대조해 측정 기록과 지시 기록을 구분한다. |
| 51 | 운영 당직표와 여과지가 만날 때 염소 주입기를 보류하는 판단 — 범위 확인 → 염소 주입 보류 결정 | `boundary,comparison,state` | 여과지 상태와 당직 지시가 충돌할 때 농도를 비교해 보류하는 승인 상태를 쓴다. |

## 새 text

| line | text |
|---:|---|
| 42 | 응집조 누수 대응 분류는 우회 밸브를 연 뒤 누수 감시기 경보가 울릴 때, 신호를 실제 관로 누수와 밸브 조작으로 구분하는 분류 방식이다. 운영자가 분류에 맞는 대응을 고르게 해 불필요한 유입 차단을 막는다. |
| 43 | 저수조 수위가 상한에 가까운데 방류 기록이 비어 있으면, 저수조 방류 예외 승인 절차는 관리자가 배수문을 닫은 보류 상태에서 현장 확인을 받는 과정이다. 승인 전에는 평상 방류와 달리 유입량을 늘리지 않아 넘침을 막는다. |
| 44 | 정수 펌프 운전 승인 기준은 누수 감시기의 압력 값과 응집조 수위가 서로 어긋날 때 관리자가 적용하는 기준이다. 관리자는 관로 누수와 원수 유입량 조절을 구분한 뒤 펌프 출력 변경을 승인해 수위 급락을 막는다. |
| 45 | 배수문 인계 우선순위는 교대자가 배수문 개방 기록과 염소 주입 지시를 대조해 어느 지시가 현재 승인 상태인지 정하는 기준이다. 평상 운전보다 낮은 배수량이 승인됐으면 그 상태를 먼저 인계해 농도 변동을 막는다. |
| 46 | 수압 센서값과 정수 펌프 유량이 같은 시각에 바뀌면, 응집조 가동 보류 결정은 운영자가 펌프 고장과 원수 부족을 구분할 때까지 응집제 투입을 멈추는 절차다. 원인이 확인되기 전에는 가동을 재개하지 않아 과투입을 막는다. |
| 47 | 여과지 새벽 운전 조정은 새벽 교대에서 여과지 탁도 기록과 당직 지시가 다를 때 적용하는 보류 상태다. 당직자는 평상 탁도보다 높은 값이면 임시 저유량 운전을 선택하고, 두 기록이 일치할 때 정상 운전으로 바꾼다. |
| 48 | 수질 계측기 통신 재시도 기준은 방류 기록과 계측기 식별자가 다를 때 오류를 통신 지연과 식별 기록 상충으로 분류하는 기준이다. 운영자는 올바른 장치가 확인된 경우에만 재전송을 실행하도록 해 다른 지점의 수치를 덮어쓰지 않게 한다. |
| 49 | 비가 계속된 뒤 우천 응집조 유입 조절은 당직자가 원수 유입구 수위와 응집조 혼탁도를 확인해 유입량을 낮추는 과정이다. 우천 상태에서는 평상 유입 대신 낮은 유입을 유지해 침전지 넘침을 막는다. |
| 50 | 교대 방류 기록 확인은 새 교대자가 수질 계측기 농도와 방류량 시각을 대조해 측정 기록과 운전 지시를 구분하는 절차다. 담당자는 수치가 다른 경우 방류 변경을 보류해 잘못된 보고를 막는다. |
| 51 | 여과지 압력과 당직 지시가 충돌하면, 염소 주입 보류 결정은 관리자가 현재 농도와 평상 농도를 비교해 주입을 멈추는 승인 상태다. 여과지가 안정될 때까지 자동 주입 대신 보류를 유지해 과다 주입을 막는다. |

## 원복 source 행

```text
응집조와 누수 감시기의 대체 경로 충돌 조정 — 분기 기록|classification,boundary,function||두 담당자의 표가 다를 때 응집조와 누수 감시기의 대체 경로 충돌 조정 — 분기 기록은 어느 표가 최신인지 확인한다. 최신이라는 판단과 내용의 타당성은 별도로 남긴다.
저수조 우선 방류 기록 예외의 승인 전 경로 — 중간 판정|process,state,contrast||판정 담당은 저수조 우선 방류 기록 예외의 승인 전 경로 — 중간 판정은 일치하는 기록과 어긋난 기록을 나누고 예외가 승인됐는지 확인한다. 승인되지 않은 예외는 실행 근거가 아니다.
승인 후에서 누수 감시기와 응집조를 가르는 정수 펌프 기준 — 신호 전달|boundary,role,attribute||관리자는 승인 후에서 누수 감시기와 응집조를 가르는 정수 펌프 기준 — 신호 전달은 기본 순서가 예외 승인으로 바뀐 지점을 표시한다. 변경되지 않은 단계는 원래 순서를 유지한다.
배수문 기록과 염소 주입기 지시의 현장 인계 우선순위 — 대상 추적|boundary,comparison,state||예외 목록을 검토하면서 배수문 기록과 염소 주입기 지시의 현장 인계 우선순위 — 대상 추적은 통상 처리와 제한 처리를 갈라 적는다. 한 번의 예외를 영구 규칙으로 만들지 않는다.
수압 센서와 정수 펌프가 만날 때 응집조를 보류하는 판단 — 순서 기록|process,boundary,role||기본 경로가 열려 있어도 수압 센서와 정수 펌프가 만날 때 응집조를 보류하는 판단 — 순서 기록은 예외 조건이 충족되면 일부 조치를 보류한다. 보류 범위와 적용 시점을 함께 기록한다.
여과지와 운영 당직표의 새벽 판독 충돌 조정 — 상태 묶음|state,contrast,comparison||두 기록을 대조하면 여과지와 운영 당직표의 새벽 판독 충돌 조정 — 상태 묶음은 기본 지시와 예외 지시를 분리해 우선순위를 정한다. 서로 다른 출처를 하나의 사실로 합치지 않는다.
방류 기록 우선 수질 계측기 예외의 통신 재시도 경로 — 우선 처리|classification,boundary,function,other|식별 기록 상충|경보가 겹친 상황에서는 방류 기록 우선 수질 계측기 예외의 통신 재시도 경로 — 우선 처리는 먼저 확인할 조건을 정하고 나머지는 대기시킨다. 조건이 풀리면 대기 항목을 다시 판정한다. 식별 기록 상충 항목은 확인된 관계만 확정하게 한다.
우천 관찰에서 원수 유입구와 응집조를 가르는 운영 당직표 기준 — 연결 확인|process,state,contrast||교대 기록에서 우천 관찰에서 원수 유입구와 응집조를 가르는 운영 당직표 기준 — 연결 확인은 우선순위와 적용 범위를 다시 확인해 충돌을 숨기지 않는다. 같은 대상에 두 지시를 동시에 부여하지 않는다.
수질 계측기 기록과 방류 기록 지시의 교대 기록 우선순위 — 출처 대조|boundary,role,attribute||운영표에는 수질 계측기 기록과 방류 기록 지시의 교대 기록 우선순위 — 출처 대조는 먼저 적용할 규칙과 나중에 살필 예외가 함께 적힌다. 충돌한 근거의 출처를 남긴다.
운영 당직표와 여과지가 만날 때 염소 주입기를 보류하는 판단 — 범위 확인|boundary,comparison,state||정책 기록과 현장 신호가 맞지 않으면 운영 당직표와 여과지가 만날 때 염소 주입기를 보류하는 판단 — 범위 확인은 충돌한 두 관계를 병렬로 보존한다. 한쪽을 지우고 단일 경로로 만들지 않는다.
```

## 원복 registry locator 행

```jsonl
{"source_file":"stage2_(16)relational_composition_high_density_train_v05.source.psv","source_line":42,"primary":"응집조와 누수 감시기의 대체 경로 충돌 조정 — 분기 기록"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v05.source.psv","source_line":43,"primary":"저수조 우선 방류 기록 예외의 승인 전 경로 — 중간 판정"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v05.source.psv","source_line":44,"primary":"승인 후에서 누수 감시기와 응집조를 가르는 정수 펌프 기준 — 신호 전달"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v05.source.psv","source_line":45,"primary":"배수문 기록과 염소 주입기 지시의 현장 인계 우선순위 — 대상 추적"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v05.source.psv","source_line":46,"primary":"수압 센서와 정수 펌프가 만날 때 응집조를 보류하는 판단 — 순서 기록"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v05.source.psv","source_line":47,"primary":"여과지와 운영 당직표의 새벽 판독 충돌 조정 — 상태 묶음"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v05.source.psv","source_line":48,"primary":"방류 기록 우선 수질 계측기 예외의 통신 재시도 경로 — 우선 처리"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v05.source.psv","source_line":49,"primary":"우천 관찰에서 원수 유입구와 응집조를 가르는 운영 당직표 기준 — 연결 확인"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v05.source.psv","source_line":50,"primary":"수질 계측기 기록과 방류 기록 지시의 교대 기록 우선순위 — 출처 대조"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v05.source.psv","source_line":51,"primary":"운영 당직표와 여과지가 만날 때 염소 주입기를 보류하는 판단 — 범위 확인"}
```
