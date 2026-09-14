# A06 v05:12~21 의미·자연성 재서술 사전 변경 계획

## 범위와 precondition

- source: `sources/train/stage2_(16)relational_composition_high_density_train_v05.source.psv`
- registry: `sources/term_registry/stage2_(16)relational_composition_train_registry_v01_v52.jsonl`
- source SHA-256 (변경 전): `A19A840B7F88C193745C0F78E5FA5EADC71DF90F5AE04EE599DA3D07734AD6D5`
- registry SHA-256 (변경 전): `3A18F70EEAF82CDACA0A53B61BEE923696ED999365B26C13D495E9C636F54AC1`
- locator는 `source_file + source_line`으로 고정한다. 행 삽입·삭제·순서 변경은 하지 않는다.
- `relations`, `other_type`, registry의 `primary` 이외 field, v01, 다른 영역, package train/val, manifest, 중앙 원장, checkpoint, 공용 감사기는 변경하지 않는다.

## locator별 직접 재서술

| line | 기존 concept | 새 concept | relations 보존 | 의미·자연성 판단 근거 |
|---:|---|---|---|---|
| 12 | 방류 기록과 수질 계측기의 대체 경로 충돌 조정 — 순서 기록 | 방류 기록 확인 순서 | `classification,boundary,function` | 표식형 복합어를 실제 업무 절차 명사구로 줄이고, 서로 다른 기록을 구분해 판단 순서를 정하는 기능을 본문에 명시한다. |
| 13 | 원수 유입구 우선 응집조 예외의 발생 직후 경로 — 상태 묶음 | 응집조 우회 승인 뒤 확인 절차 | `process,state,contrast` | 불명확한 상태 묶음 대신 승인 뒤 밸브·우회관 상태를 대조하는 시간적 확인 절차를 설명한다. |
| 14 | 승인 후에서 수질 계측기와 방류 기록을 가르는 수압 센서 기준 — 우선 처리 | 수압 센서 승인 기준 | `boundary,role,attribute,other` | 어색한 `승인 후에서`과 표식을 제거하고, 관리자가 수압 값을 기준으로 자동 우회를 가르는 판단과 동시 개입 분리 불가의 한계를 남긴다. |
| 15 | 운영 당직표 기록과 여과지 지시의 예외 기간 우선순위 — 연결 확인 | 여과지 예외 운전 기간 | `boundary,comparison,state` | 기록행위 표식이 아니라 실제 승인 상태인 예외 운전 기간으로 바꾸고 압력·탁도 비교와 정상 운전으로의 복귀 경계를 쓴다. |
| 16 | 정수 펌프와 수압 센서가 만날 때 방류 기록을 보류하는 판단 — 출처 대조 | 방류 기록 보류 결정 | `process,boundary,role` | 비인격적 `만날 때` 합성어와 불투명한 출처 대조를 없애고, 유량·센서 불일치 때 운영자가 고장과 오차를 구분하는 보류 결정을 쓴다. |
| 17 | 염소 주입기와 배수문의 새벽 판독 충돌 조정 — 범위 확인 | 새벽 염소 주입 조정 | `state,contrast,comparison` | 인공적인 범위 확인 표식을 제거하고 농도·개방 기록 충돌 때 평상량보다 낮은 임시량을 선택하는 상태를 구체화한다. |
| 18 | 응집조 우선 누수 감시기 예외의 부분 회복 경로 — 운영 인계 | 누수 경보 인계 절차 | `classification,boundary,function` | 부분 회복 경로라는 추상 명칭 대신 누수 경보를 구분해 교대자에게 전달하는 실제 업무 절차와 그 목적을 쓴다. |
| 19 | 우천 관찰에서 저수조와 방류 기록을 가르는 배수문 기준 — 회복 판정 | 우천 배수문 전환 기준 | `process,state,contrast` | 길고 부자연스러운 수식 연쇄를 우천 시 배수문 전환 기준으로 줄이고, 수위 상태와 평상 방류의 대조를 독립 문장으로 만든다. |
| 20 | 누수 감시기 기록과 응집조 지시의 대체 자원 우선순위 — 경로 보존 | 응집조 대체 수원 선택 순서 | `boundary,role,attribute` | 대체 자원·경로 보존 표식을 실제 수원 선택 순서로 바꾸고, 운영자가 수위·탁도를 읽어 경보 원인을 구분하는 내용을 남긴다. |
| 21 | 배수문과 염소 주입기가 만날 때 여과지를 보류하는 판단 — 결과 검증 | 여과지 보류 판단 | `boundary,comparison,state` | 비인격적 결합과 결과 검증 표식을 제거하고, 장치 변경 시각·농도 차이를 확인할 때까지 가동을 보류하는 경계를 적는다. |

## 새 본문 초안

| line | 새 text |
|---:|---|
| 12 | 방류 기록 확인 순서는 수질 계측기 값과 수문 개방 기록이 서로 다를 때, 운영자가 두 기록을 별도 자료로 구분해 방류 판단에 먼저 쓸 기록을 정하는 절차다. 잘못된 방류를 막기 위해 이 순서를 적용한다. |
| 13 | 응집조 우회 승인 뒤 확인 절차에서는 담당자가 원수 유입구의 밸브 상태와 우회관 개방 상태를 대조한 뒤, 승인 시각 이후의 유입량만 정상 운전 기록에 반영한다. 승인 전에 흘린 물은 별도 기록으로 남겨 혼동을 막는다. |
| 14 | 수압 센서 승인 기준은 관리자가 수질 계측기와 방류 기록 사이의 수압 값 차이를 확인해 자동 우회가 허용되는지 가르는 기준이다. 두 설비가 같은 시각에 압력을 바꾼 경우에는 동시 개입 분리 불가로 분류하고, 원인을 확정하지 않는다. |
| 15 | 여과지 예외 운전 기간은 당직자가 여과지 압력과 탁도 값을 비교해 우회 운전을 계속할지 결정하는 승인 상태다. 압력이 정상 범위로 돌아오면 예외 운전과 평상 운전을 구분해 우회 지시를 종료한다. |
| 16 | 방류 기록 보류 결정은 정수 펌프 유량과 수압 센서 값이 같은 시간대에 맞지 않을 때 운영자가 내린 조치다. 운영자는 펌프 고장과 센서 오차를 구분할 때까지 방류량 보고를 보류하여 잘못된 수질 보고를 막는다. |
| 17 | 새벽 염소 주입 조정은 염소 주입기 농도 기록과 배수문 개방 기록이 충돌할 때, 당직자가 평상 주입량보다 낮은 임시 주입량을 선택하는 보류 상태다. 두 기록이 일치할 때까지 자동 주입 대신 수동 주입을 유지한다. |
| 18 | 누수 경보 인계 절차는 응집조 우회 운전 중 발생한 누수 경보를 정수 운영 경보와 구분해 다음 교대자에게 전달하기 위해 사용한다. 인계자는 우회관을 닫기 전 확인할 항목을 정리해 펌프 정지를 방지한다. |
| 19 | 우천 배수문 전환 기준은 폭우 때 저수조 수위와 방류 기록이 서로 다른지 확인한 뒤, 관리자가 배수문을 열지 말지 정하는 기준이다. 수위가 높아진 상태에서는 평상 방류 대신 저수조 저장을 유지해 넘침을 막는다. |
| 20 | 응집조 대체 수원 선택 순서는 누수 감시기 기록이 원수 부족을 알릴 때, 운영자가 수위와 탁도 값을 보고 어느 예비 수원을 먼저 쓸지 정하는 기준이다. 운영자는 관로 손상 경보와 단순 수위 저하를 구분해 잘못된 취수를 막는다. |
| 21 | 여과지 보류 판단은 배수문 개방 여부와 염소 주입 농도가 동시에 바뀌어 수질 결과를 비교할 수 없을 때 적용하는 임시 운전 상태다. 관리자는 두 장치의 변경 시각을 구분한 뒤, 농도 차이가 확인될 때까지 여과지 가동을 보류해 부적합한 물의 방류를 막는다. |

## 원복용 원문

### source 행

```text
방류 기록과 수질 계측기의 대체 경로 충돌 조정 — 순서 기록|classification,boundary,function||두 담당자의 표가 다를 때 방류 기록과 수질 계측기의 대체 경로 충돌 조정 — 순서 기록은 어느 표가 최신인지 확인한다. 최신이라는 판단과 내용의 타당성은 별도로 남긴다.
원수 유입구 우선 응집조 예외의 발생 직후 경로 — 상태 묶음|process,state,contrast||판정 담당은 원수 유입구 우선 응집조 예외의 발생 직후 경로 — 상태 묶음은 일치하는 기록과 어긋난 기록을 나누고 예외가 승인됐는지 확인한다. 승인되지 않은 예외는 실행 근거가 아니다.
승인 후에서 수질 계측기와 방류 기록을 가르는 수압 센서 기준 — 우선 처리|boundary,role,attribute,other|동시 개입 분리 불가|관리자는 승인 후에서 수질 계측기와 방류 기록을 가르는 수압 센서 기준 — 우선 처리는 기본 순서가 예외 승인으로 바뀐 지점을 표시한다. 변경되지 않은 단계는 원래 순서를 유지한다. 동시 개입 분리 불가 항목은 확인된 관계만 확정하게 한다.
운영 당직표 기록과 여과지 지시의 예외 기간 우선순위 — 연결 확인|boundary,comparison,state||예외 목록을 검토하면서 운영 당직표 기록과 여과지 지시의 예외 기간 우선순위 — 연결 확인은 통상 처리와 제한 처리를 갈라 적는다. 한 번의 예외를 영구 규칙으로 만들지 않는다.
정수 펌프와 수압 센서가 만날 때 방류 기록을 보류하는 판단 — 출처 대조|process,boundary,role||기본 경로가 열려 있어도 정수 펌프와 수압 센서가 만날 때 방류 기록을 보류하는 판단 — 출처 대조는 예외 조건이 충족되면 일부 조치를 보류한다. 보류 범위와 적용 시점을 함께 기록한다.
염소 주입기와 배수문의 새벽 판독 충돌 조정 — 범위 확인|state,contrast,comparison||두 기록을 대조하면 염소 주입기와 배수문의 새벽 판독 충돌 조정 — 범위 확인은 기본 지시와 예외 지시를 분리해 우선순위를 정한다. 서로 다른 출처를 하나의 사실로 합치지 않는다.
응집조 우선 누수 감시기 예외의 부분 회복 경로 — 운영 인계|classification,boundary,function||경보가 겹친 상황에서는 응집조 우선 누수 감시기 예외의 부분 회복 경로 — 운영 인계는 먼저 확인할 조건을 정하고 나머지는 대기시킨다. 조건이 풀리면 대기 항목을 다시 판정한다.
우천 관찰에서 저수조와 방류 기록을 가르는 배수문 기준 — 회복 판정|process,state,contrast||교대 기록에서 우천 관찰에서 저수조와 방류 기록을 가르는 배수문 기준 — 회복 판정은 우선순위와 적용 범위를 다시 확인해 충돌을 숨기지 않는다. 같은 대상에 두 지시를 동시에 부여하지 않는다.
누수 감시기 기록과 응집조 지시의 대체 자원 우선순위 — 경로 보존|boundary,role,attribute||운영표에는 누수 감시기 기록과 응집조 지시의 대체 자원 우선순위 — 경로 보존은 먼저 적용할 규칙과 나중에 살필 예외가 함께 적힌다. 충돌한 근거의 출처를 남긴다.
배수문과 염소 주입기가 만날 때 여과지를 보류하는 판단 — 결과 검증|boundary,comparison,state||정책 기록과 현장 신호가 맞지 않으면 배수문과 염소 주입기가 만날 때 여과지를 보류하는 판단 — 결과 검증은 충돌한 두 관계를 병렬로 보존한다. 한쪽을 지우고 단일 경로로 만들지 않는다.
```

### registry JSONL 행

```jsonl
{"source_file":"stage2_(16)relational_composition_high_density_train_v05.source.psv","source_line":12,"primary":"방류 기록과 수질 계측기의 대체 경로 충돌 조정 — 순서 기록","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-005","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v05.source.psv","source_line":13,"primary":"원수 유입구 우선 응집조 예외의 발생 직후 경로 — 상태 묶음","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-005","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v05.source.psv","source_line":14,"primary":"승인 후에서 수질 계측기와 방류 기록을 가르는 수압 센서 기준 — 우선 처리","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-005","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v05.source.psv","source_line":15,"primary":"운영 당직표 기록과 여과지 지시의 예외 기간 우선순위 — 연결 확인","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-005","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v05.source.psv","source_line":16,"primary":"정수 펌프와 수압 센서가 만날 때 방류 기록을 보류하는 판단 — 출처 대조","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-005","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v05.source.psv","source_line":17,"primary":"염소 주입기와 배수문의 새벽 판독 충돌 조정 — 범위 확인","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-005","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v05.source.psv","source_line":18,"primary":"응집조 우선 누수 감시기 예외의 부분 회복 경로 — 운영 인계","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-005","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v05.source.psv","source_line":19,"primary":"우천 관찰에서 저수조와 방류 기록을 가르는 배수문 기준 — 회복 판정","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-005","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v05.source.psv","source_line":20,"primary":"누수 감시기 기록과 응집조 지시의 대체 자원 우선순위 — 경로 보존","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-005","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v05.source.psv","source_line":21,"primary":"배수문과 염소 주입기가 만날 때 여과지를 보류하는 판단 — 결과 검증","term_kind":"constructed_scenario","definition":"도시 상수도 정수·배수 운영에서 관계 충돌·우선순위·예외 통합을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-005","review_status":"generated_pending_semantic_review"}
```
