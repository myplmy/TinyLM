# A06 v05:22~31 의미·자연성 재서술 사전 변경 계획

## 범위와 보존 조건

- source: `sources/train/stage2_(16)relational_composition_high_density_train_v05.source.psv`
- registry: `sources/term_registry/stage2_(16)relational_composition_train_registry_v01_v52.jsonl`
- source SHA-256 (변경 전): `1D614650C7DFE5C229C571BD577AAC36B384789A2E3B78AD1F9EDD292FD9E7A3`
- registry SHA-256 (변경 전): `DBFB297A47A037B165629EDD4D1DA7AEE82EA803288D5E9AB6477ED952262FAA`
- locator는 `source_file + source_line`으로 고정하고 행 삽입·삭제·순서 변경은 하지 않는다.
- 각 locator의 `concept`와 source 본문, registry의 같은 locator `primary`만 바꾼다. relations·other_type·registry의 나머지 field·v01·다른 영역·package train/val·manifest·중앙 원장·checkpoint·공용 감사기는 보존한다.

## locator별 재서술

| line | 기존 concept | 새 concept | relations 보존 | 판단 근거 |
|---:|---|---|---|---|
| 22 | 수압 센서와 정수 펌프의 정기 운전 충돌 조정 — 영향 검토 | 정수 펌프 운전 조정 절차 | `process,boundary,role` | 표식형 기록 제목을 실제 운영 절차로 바꾸고, 낮은 압력값·운영자 판단·과부하 방지 결과를 명시한다. |
| 23 | 여과지 우선 운영 당직표 예외의 재검 표본 경로 — 예외 점검 | 여과지 우회 운전 재검 | `state,contrast,comparison` | 추상적인 표본 경로 대신 탁도 변화 때 우회·정상 기록을 대조하는 보류 상태와 유량 제한 결과를 쓴다. |
| 24 | 고부하 운전에서 방류 기록과 수질 계측기를 가르는 누수 감시기 기준 — 독립 확인 | 고부하 누수 경보 분류 | `classification,boundary,function` | 고부하 중 압력 저하 신호를 수질 계측 이상과 구분하는 분류 기준과 펌프 정지 판단 기능을 쓴다. |
| 25 | 원수 유입구 기록과 응집조 지시의 전원 대기 우선순위 — 분기 기록 | 전원 대기 중 응집조 운전 순서 | `process,state,contrast` | 정전 뒤의 전원 대기 상태와 평상 운전과 다른 유입량 제한 과정을 구체화한다. |
| 26 | 수질 계측기와 방류 기록이 만날 때 수압 센서를 보류하는 판단 — 중간 판정 | 수압 센서 점검 보류 | `boundary,role,attribute` | 비인격적 결합을 없애고 유량 수치 불일치 때 관리자가 누수와 계측 오차를 구분하는 판단을 쓴다. |
| 27 | 운영 당직표와 여과지의 비상 전환 충돌 조정 — 신호 전달 | 여과지 비상 전환 승인 | `boundary,comparison,state` | 설비 압력·탁도를 비교해 비상 전환을 승인하는 상태와 평상 운전과의 경계를 적는다. |
| 28 | 정수 펌프 우선 수압 센서 예외의 예비 경로 — 대상 추적 | 정수 펌프 예비 운전 확인 | `process,boundary,role` | 겹친 경보 때 운영자가 전원 부족과 실제 압력 저하를 구분해 예비 펌프 기동을 결정하는 절차를 쓴다. |
| 29 | 예방 점검에서 염소 주입기와 배수문을 가르는 저수조 기준 — 순서 기록 | 우천 저수조 수위 기준 | `state,contrast,comparison` | 폭우 전 수위·개방량 비교와 평상 수위보다 높은 상태에서 방류를 늦추는 결정으로 바꾼다. |
| 30 | 응집조 기록과 누수 감시기 지시의 후속 입력 우선순위 — 상태 묶음 | 응집조 입력 우선순위 | `classification,boundary,function` | 긴급 경보·정기 지시를 구분하는 분류 원칙과 응집제 투입을 늦춰야 할 상황을 알리는 기능을 적는다. |
| 31 | 저수조와 방류 기록이 만날 때 배수문을 보류하는 판단 — 우선 처리 | 배수문 보류 결정 | `process,state,contrast,other` | 수위 표본 부족이라는 구체 계기, 닫힌 상태, 추가 관측 대기, `부분 표본의 해석 한계`를 보존한다. |

## 새 text

| line | 새 text |
|---:|---|
| 22 | 수압 센서가 급격히 낮은 값을 보이면, 정수 펌프 운전 조정 절차에 따라 운영자가 센서 오류와 실제 압력 저하를 구분한 뒤 펌프 출력을 낮춘다. 이 절차는 관로 손상 여부를 확인하기 전 과부하 운전을 막는다. |
| 23 | 탁도 값이 이전 교대보다 높아지면, 여과지 우회 운전 재검은 담당자가 우회 운전 기록과 정상 여과 기록을 대조하는 보류 상태다. 오차가 확인될 때까지 더 낮은 유량으로 운전해 탁수 유입을 막는다. |
| 24 | 고부하 누수 경보 분류는 누수 감시기가 보내는 압력 저하 신호를 수질 계측기 이상과 구분해, 관리자가 펌프 정지 필요 여부를 판단하도록 돕는 분류 기준이다. 잘못된 경보 때문에 급수를 멈추지 않게 한다. |
| 25 | 정전 경보가 울린 뒤 전원 대기 중 응집조 운전 순서는 당직자가 원수 유입을 줄이고 응집제를 투입하지 않은 상태에서 비상 전원이 준비되었는지 확인하는 절차다. 전원이 복구되기 전에는 평상 운전과 달리 유입량을 늘리지 않아 넘침을 막는다. |
| 26 | 수압 센서 점검 보류는 수질 계측값과 방류 기록의 유량 수치가 서로 맞지 않을 때, 관리자가 센서 교체를 서두르지 않고 관로 누수와 계측 오차를 구분하는 판단이다. 원인이 확인될 때까지 방류량을 바꾸지 않는다. |
| 27 | 여과지 비상 전환 승인은 예비 여과지가 평상 여과지보다 낮은 압력으로만 가동될 때, 당직자가 두 설비의 탁도 값을 비교해 비상 전환을 허용하는 승인 상태다. 탁도가 기준을 넘으면 평상 운전 대신 예비 여과지를 유지해 불량 수질의 공급을 막는다. |
| 28 | 수압 센서 경보가 정수 펌프 경보와 겹치면, 정수 펌프 예비 운전 확인은 운영자가 전원 부족과 실제 압력 저하를 구분한 뒤 예비 펌프를 켤지 정하는 절차다. 확인 전에는 두 펌프를 함께 기동하지 않아 전력 과부하를 막는다. |
| 29 | 폭우 전 예방 점검에서 우천 저수조 수위 기준은 관리자가 저수조 수위와 배수문 개방량을 비교해 비상 방류 상태로 바꿀지 판단하는 기준이다. 평상 수위보다 높을 때에는 염소 주입량을 늘리지 않고 방류를 늦춰 역류를 막는다. |
| 30 | 응집조 입력 우선순위는 누수 감시기 경보와 운전 지시가 같은 시간에 들어올 때, 운영자가 긴급 경보와 정기 지시를 구분해 처리 순서를 정하는 분류 원칙이다. 이 원칙은 응집제 투입을 늦춰야 할 상황을 알리는 기능을 한다. |
| 31 | 저수조 수위 표본과 방류 기록이 어긋난 뒤, 배수문 보류 결정은 관리자가 배수문을 닫은 상태에서 추가 수위 측정을 기다리는 조치다. 부분 표본의 해석 한계 때문에 평상 방류 대신 관측이 끝날 때까지 개방하지 않아 갑작스러운 저수조 저하를 막는다. |

## 원복용 원문

### source 행

```text
수압 센서와 정수 펌프의 정기 운전 충돌 조정 — 영향 검토|process,boundary,role||두 담당자의 표가 다를 때 수압 센서와 정수 펌프의 정기 운전 충돌 조정 — 영향 검토는 어느 표가 최신인지 확인한다. 최신이라는 판단과 내용의 타당성은 별도로 남긴다.
여과지 우선 운영 당직표 예외의 재검 표본 경로 — 예외 점검|state,contrast,comparison||판정 담당은 여과지 우선 운영 당직표 예외의 재검 표본 경로 — 예외 점검은 일치하는 기록과 어긋난 기록을 나누고 예외가 승인됐는지 확인한다. 승인되지 않은 예외는 실행 근거가 아니다.
고부하 운전에서 방류 기록과 수질 계측기를 가르는 누수 감시기 기준 — 독립 확인|classification,boundary,function||관리자는 고부하 운전에서 방류 기록과 수질 계측기를 가르는 누수 감시기 기준 — 독립 확인은 기본 순서가 예외 승인으로 바뀐 지점을 표시한다. 변경되지 않은 단계는 원래 순서를 유지한다.
원수 유입구 기록과 응집조 지시의 전원 대기 우선순위 — 분기 기록|process,state,contrast||예외 목록을 검토하면서 원수 유입구 기록과 응집조 지시의 전원 대기 우선순위 — 분기 기록은 통상 처리와 제한 처리를 갈라 적는다. 한 번의 예외를 영구 규칙으로 만들지 않는다.
수질 계측기와 방류 기록이 만날 때 수압 센서를 보류하는 판단 — 중간 판정|boundary,role,attribute||기본 경로가 열려 있어도 수질 계측기와 방류 기록이 만날 때 수압 센서를 보류하는 판단 — 중간 판정은 예외 조건이 충족되면 일부 조치를 보류한다. 보류 범위와 적용 시점을 함께 기록한다.
운영 당직표와 여과지의 비상 전환 충돌 조정 — 신호 전달|boundary,comparison,state||두 기록을 대조하면 운영 당직표와 여과지의 비상 전환 충돌 조정 — 신호 전달은 기본 지시와 예외 지시를 분리해 우선순위를 정한다. 서로 다른 출처를 하나의 사실로 합치지 않는다.
정수 펌프 우선 수압 센서 예외의 예비 경로 — 대상 추적|process,boundary,role||경보가 겹친 상황에서는 정수 펌프 우선 수압 센서 예외의 예비 경로 — 대상 추적은 먼저 확인할 조건을 정하고 나머지는 대기시킨다. 조건이 풀리면 대기 항목을 다시 판정한다.
예방 점검에서 염소 주입기와 배수문을 가르는 저수조 기준 — 순서 기록|state,contrast,comparison||교대 기록에서 예방 점검에서 염소 주입기와 배수문을 가르는 저수조 기준 — 순서 기록은 우선순위와 적용 범위를 다시 확인해 충돌을 숨기지 않는다. 같은 대상에 두 지시를 동시에 부여하지 않는다.
응집조 기록과 누수 감시기 지시의 후속 입력 우선순위 — 상태 묶음|classification,boundary,function||운영표에는 응집조 기록과 누수 감시기 지시의 후속 입력 우선순위 — 상태 묶음은 먼저 적용할 규칙과 나중에 살필 예외가 함께 적힌다. 충돌한 근거의 출처를 남긴다.
저수조와 방류 기록이 만날 때 배수문을 보류하는 판단 — 우선 처리|process,state,contrast,other|부분 표본의 해석 한계|정책 기록과 현장 신호가 맞지 않으면 저수조와 방류 기록이 만날 때 배수문을 보류하는 판단 — 우선 처리는 충돌한 두 관계를 병렬로 보존한다. 한쪽을 지우고 단일 경로로 만들지 않는다. 부분 표본의 해석 한계 항목은 확인된 관계만 확정하게 한다.
```

### registry JSONL 행

```jsonl
{"source_file":"stage2_(16)relational_composition_high_density_train_v05.source.psv","source_line":22,"primary":"수압 센서와 정수 펌프의 정기 운전 충돌 조정 — 영향 검토","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-005","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v05.source.psv","source_line":23,"primary":"여과지 우선 운영 당직표 예외의 재검 표본 경로 — 예외 점검","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-005","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v05.source.psv","source_line":24,"primary":"고부하 운전에서 방류 기록과 수질 계측기를 가르는 누수 감시기 기준 — 독립 확인","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-005","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v05.source.psv","source_line":25,"primary":"원수 유입구 기록과 응집조 지시의 전원 대기 우선순위 — 분기 기록","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-005","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v05.source.psv","source_line":26,"primary":"수질 계측기와 방류 기록이 만날 때 수압 센서를 보류하는 판단 — 중간 판정","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-005","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v05.source.psv","source_line":27,"primary":"운영 당직표와 여과지의 비상 전환 충돌 조정 — 신호 전달","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-005","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v05.source.psv","source_line":28,"primary":"정수 펌프 우선 수압 센서 예외의 예비 경로 — 대상 추적","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-005","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v05.source.psv","source_line":29,"primary":"예방 점검에서 염소 주입기와 배수문을 가르는 저수조 기준 — 순서 기록","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-005","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v05.source.psv","source_line":30,"primary":"응집조 기록과 누수 감시기 지시의 후속 입력 우선순위 — 상태 묶음","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-005","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v05.source.psv","source_line":31,"primary":"저수조와 방류 기록이 만날 때 배수문을 보류하는 판단 — 우선 처리","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-005","review_status":"generated_pending_semantic_review"}
```
