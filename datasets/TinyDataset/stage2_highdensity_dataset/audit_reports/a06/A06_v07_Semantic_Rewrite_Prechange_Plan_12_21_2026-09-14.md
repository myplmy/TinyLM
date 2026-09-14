# A06 v07:12~21 의미·자연성 재서술 사전 변경 계획

## 범위·보존

- source SHA-256: `4098108EBF3655C676CD27D78C784270A6D876E608F564B503BDAF9DEA18BA5A`
- registry SHA-256: `E38F6AD8ADB920AA4964680624FB8B45246BB51F6B63C81B94548BC533ECEFE8`
- locator는 `stage2_(16)relational_composition_high_density_train_v07.source.psv:12~21`으로 고정한다. source concept/text와 같은 locator registry primary 외 field·행 순서·relations·other_type는 보존한다.
- v01, 다른 영역, package train/val, manifest, 중앙 원장, checkpoint, 공용 감사기는 수정하지 않는다. registry 원복 전체 바이트는 반영 직전 backup `A06_registry_before_v07_semantic_rewrite_12_21_2026-09-14.jsonl`에 보존한다.

| line | 기존 concept → 새 concept | relations | 직접 재서술 근거 |
|---:|---|---|---|
| 12 | 상태 점검표에서 복구 담당자로 이어지는 야간 점검 경로 — 범위 확인 → 야간 상태 점검의 자동 복귀 보류 | `part_of,state,attribute,other` | 복구 과정에서 동시 조치의 원인을 분리하지 못해 보류한다. |
| 13 | 부하 계측기와 자동 확장기 사이의 우천 관찰 연결 — 운영 인계 → 부하 계측기 경보의 자동 확장 인계 | `process,role,state` | 담당자가 부하 경보를 받아 증설 여부를 다음 운영자에게 인계한다. |
| 14 | 복구 담당자 판독 뒤 상태 점검표에 전달되는 장기 관찰 — 회복 판정 → 복구 담당자의 복구 완료 점검 기록 | `part_of,process,role` | 복구 과정의 완료 단계에서 담당자가 서비스 상태를 점검표에 남긴다. |
| 15 | 요청 대기열에서 오류 로그까지 백업 저장소로 확인하는 긴급 확인 — 경로 보존 → 요청 대기열 오류 급증 시 백업 경로 분류 | `process,classification,attribute` | 대기열 길이와 오류 비율을 기준으로 백업 경로 전환 대상을 분류한다. |
| 16 | 정기 운전에 따른 캐시 계층·배포 승인·상태 점검표 순차 흐름 — 결과 검증 → 캐시 점검 후 배포 승인 상태 갱신 | `process,state,function` | 캐시 기능 점검 결과로 배포 승인 상태를 갱신한다. |
| 17 | 백업 저장소에서 장애 통보로 이어지는 저부하 운전 경로 — 영향 검토 → 백업 저장소 지연과 장애 통보 시각 대조 | `process,role,comparison` | 담당자가 복제 지연과 통보 시각을 비교해 전환 여부를 판단한다. |
| 18 | 자동 확장기와 서비스 노드 사이의 고부하 운전 연결 — 예외 점검 → 고부하 서비스 노드의 자동 확장 대기 상태 | `part_of,state,attribute` | 복구 과정에서 CPU 사용률과 대기 요청 수가 높을 때 증설 대기 상태를 유지한다. |
| 19 | 트래픽 분배기 판독 뒤 상태 점검표에 전달되는 경계 직전 — 독립 확인 → 트래픽 분배기 경보의 상태 점검 인계 | `process,role,state` | 운영자가 분배기 경보와 대상 노드를 확인해 다음 교대자에게 점검을 넘긴다. |
| 20 | 서비스 노드에서 자동 확장기까지 캐시 계층으로 확인하는 현장 재검 — 분기 기록 → 서비스 노드 오류의 자동 확장 현장 점검 | `part_of,process,role` | 담당자가 노드 오류와 캐시 부하를 확인해 자동 확장의 필요를 판단한다. |
| 21 | 비상 전환에 따른 장애 통보·백업 저장소·오류 로그 순차 흐름 — 중간 판정 → 비상 전환 시 백업 저장소 오류 분류 | `process,classification,attribute` | 복제 지연과 오류 코드에 따라 즉시 전환·대기 대상을 분류한다. |

## 새 text

| line | text |
|---:|---|
| 12 | 야간에 자동 확장으로 노드를 늘리는 동안 캐시 정리도 시작되어 오류율과 응답 시간이 함께 변할 때, 야간 상태 점검의 자동 복귀 보류는 장애 복구 과정에서 원인을 나누지 못한 보류 상태다. 동시 개입 분리 불가 때문에 자동 복귀를 완료로 처리하지 않아 장애 재발을 막는다. |
| 13 | 부하 계측기가 CPU 사용률과 대기 요청 수의 상승을 알릴 때, 부하 계측기 경보의 자동 확장 인계는 당직 운영자가 확인된 부하 수치를 다음 운영자에게 넘겨 증설 여부를 판단하게 하는 과정이다. 새 운영자가 수치를 확인하기 전에는 자동 확장을 실행하지 않아 불필요한 노드 증설을 막는다. |
| 14 | 서비스 오류율이 낮아지고 복구 작업이 끝난 뒤, 복구 담당자의 복구 완료 점검 기록은 장애 대응 과정의 마지막 단계로서 복구 담당자가 서비스 상태와 남은 경보를 점검표에 적는 과정이다. 기록이 없으면 복구를 완료로 처리하지 않아 같은 장애의 재발을 막는다. |
| 15 | 요청 대기열 길이가 급증하고 오류 로그에 시간 초과가 반복될 때, 요청 대기열 오류 급증 시 백업 경로 분류는 운영자가 백업 경로로 전환할 요청과 현재 경로에서 재시도할 요청을 분류하는 과정이다. 대기열 길이와 오류 비율이 회복되기 전에는 전환을 풀지 않아 오류 확산을 막는다. |
| 16 | 캐시 적중률과 오래된 응답 비율을 점검한 뒤, 캐시 점검 후 배포 승인 상태 갱신은 캐시 계층의 정상 기능을 확인해 배포 승인 상태를 갱신하는 과정이다. 적중률이 낮으면 승인을 보류 상태로 남겨 배포 영향과 캐시 장애가 섞이는 것을 막는다. |
| 17 | 백업 저장소의 복제 지연이 길어지고 장애 통보가 늦게 들어올 때, 백업 저장소 지연과 장애 통보 시각 대조에서 장애 대응 담당자는 두 기록의 시각과 지연 시간을 비교한다. 지연 원인이 확인되기 전에는 백업 경로로 전환하지 않아 최신 데이터 누락을 막는다. |
| 18 | 서비스 노드의 CPU 사용률과 대기 요청 수가 모두 높을 때, 고부하 서비스 노드의 자동 확장 대기 상태는 장애 복구 과정에서 새 노드 증설을 준비하는 상태다. 부하 수치가 확인되기 전에는 노드를 정상 경로에 넣지 않아 요청 실패 확산을 막는다. |
| 19 | 트래픽 분배기에서 연결 오류 경보가 나오고 상태 점검표가 생성될 때, 트래픽 분배기 경보의 상태 점검 인계는 당직 운영자가 대상 노드와 오류 수를 확인해 다음 교대자에게 점검을 넘기는 과정이다. 점검이 끝나기 전에는 경로를 바꾸지 않아 정상 노드까지 차단되는 일을 막는다. |
| 20 | 서비스 노드 오류가 늘고 캐시 대기열도 길어질 때, 서비스 노드 오류의 자동 확장 현장 점검은 장애 복구 과정의 일부로서 복구 담당자가 오류율과 캐시 부하를 확인해 증설 필요를 판단하는 과정이다. 두 수치가 맞지 않으면 자동 확장을 실행하지 않아 비용 증가를 막는다. |
| 21 | 비상 전환 뒤 백업 저장소의 복제 지연과 오류 로그의 코드가 함께 바뀔 때, 비상 전환 시 백업 저장소 오류 분류는 운영자가 즉시 전환할 서비스와 복제 완료를 기다릴 서비스를 분류하는 과정이다. 복제 지연이 큰 서비스는 전환을 보류해 최신 데이터 손실을 막는다. |

## 원복 source 행

```text
상태 점검표에서 복구 담당자로 이어지는 야간 점검 경로 — 범위 확인|part_of,state,attribute,other|동시 개입 분리 불가|앞 단계의 값을 받은 뒤 다음 담당이 조치를 선택하는 연결에서 상태 점검표에서 복구 담당자로 이어지는 야간 점검 경로 — 범위 확인은 드러난다. 마지막 결과만 보고 출발점을 거꾸로 추정하지 않는다. 동시 개입 분리 불가 항목은 확인된 관계만 확정하게 한다.
부하 계측기와 자동 확장기 사이의 우천 관찰 연결 — 운영 인계|process,role,state||운영 기록을 시간순으로 놓으면 부하 계측기와 자동 확장기 사이의 우천 관찰 연결 — 운영 인계는 중간 전달이 보인다. 전달자가 바뀌어도 각 단계의 책임을 구분한다.
복구 담당자 판독 뒤 상태 점검표에 전달되는 장기 관찰 — 회복 판정|part_of,process,role||센서 값과 작업 명령을 함께 읽으면 복구 담당자 판독 뒤 상태 점검표에 전달되는 장기 관찰 — 회복 판정은 각 고리가 이어지는 이유를 확인할 수 있다. 한 고리의 결과를 다른 고리의 원인으로 확대하지 않는다.
요청 대기열에서 오류 로그까지 백업 저장소로 확인하는 긴급 확인 — 경로 보존|process,classification,attribute||현장 기록에서는 요청 대기열에서 오류 로그까지 백업 저장소로 확인하는 긴급 확인 — 경로 보존은 입력, 판정, 실행이 차례로 보인다. 어느 한 단계가 누락되면 다음 관계는 미확정으로 둔다.
정기 운전에 따른 캐시 계층·배포 승인·상태 점검표 순차 흐름 — 결과 검증|process,state,function||경로 점검 결과 정기 운전에 따른 캐시 계층·배포 승인·상태 점검표 순차 흐름 — 결과 검증은 앞 단계와 다음 단계가 모두 확인될 때만 연결을 확정한다. 일부 기록만으로 전체 경로를 채우지 않는다.
백업 저장소에서 장애 통보로 이어지는 저부하 운전 경로 — 영향 검토|process,role,comparison||처리 순서가 적힌 목록에서 백업 저장소에서 장애 통보로 이어지는 저부하 운전 경로 — 영향 검토는 앞뒤 관계를 분리한다. 누락된 확인은 결과와 같은 의미로 취급하지 않는다.
자동 확장기와 서비스 노드 사이의 고부하 운전 연결 — 예외 점검|part_of,state,attribute||대기 중인 작업표에서 자동 확장기와 서비스 노드 사이의 고부하 운전 연결 — 예외 점검은 앞선 관찰과 후속 조치가 맞물린다. 순서를 바꾸어 기록하지 않는다.
트래픽 분배기 판독 뒤 상태 점검표에 전달되는 경계 직전 — 독립 확인|process,role,state||관측표를 보면 트래픽 분배기 판독 뒤 상태 점검표에 전달되는 경계 직전 — 독립 확인은 신호에서 판단을 거쳐 실행으로 이어진다. 각 단계의 기록을 따로 남겨 중간 관계를 건너뛰지 않는다.
서비스 노드에서 자동 확장기까지 캐시 계층으로 확인하는 현장 재검 — 분기 기록|part_of,process,role||현장 담당자는 서비스 노드에서 자동 확장기까지 캐시 계층으로 확인하는 현장 재검 — 분기 기록은 신호·판정·조작의 방향을 화살표로 표시한다. 뒤 단계의 기록이 앞 단계를 자동으로 증명하지는 않는다.
비상 전환에 따른 장애 통보·백업 저장소·오류 로그 순차 흐름 — 중간 판정|process,classification,attribute||교대 인계 때 비상 전환에 따른 장애 통보·백업 저장소·오류 로그 순차 흐름 — 중간 판정은 경로를 처음부터 다시 대조한다. 중간 확인이 남아 있을 때만 마지막 상태를 연결한다.
```

## 원복 registry locator 행

```jsonl
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":12,"primary":"상태 점검표에서 복구 담당자로 이어지는 야간 점검 경로 — 범위 확인","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":13,"primary":"부하 계측기와 자동 확장기 사이의 우천 관찰 연결 — 운영 인계","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":14,"primary":"복구 담당자 판독 뒤 상태 점검표에 전달되는 장기 관찰 — 회복 판정","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":15,"primary":"요청 대기열에서 오류 로그까지 백업 저장소로 확인하는 긴급 확인 — 경로 보존","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":16,"primary":"정기 운전에 따른 캐시 계층·배포 승인·상태 점검표 순차 흐름 — 결과 검증","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":17,"primary":"백업 저장소에서 장애 통보로 이어지는 저부하 운전 경로 — 영향 검토","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":18,"primary":"자동 확장기와 서비스 노드 사이의 고부하 운전 연결 — 예외 점검","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":19,"primary":"트래픽 분배기 판독 뒤 상태 점검표에 전달되는 경계 직전 — 독립 확인","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":20,"primary":"서비스 노드에서 자동 확장기까지 캐시 계층으로 확인하는 현장 재검 — 분기 기록","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":21,"primary":"비상 전환에 따른 장애 통보·백업 저장소·오류 로그 순차 흐름 — 중간 판정","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
```

## 적용 전제

- 10개 locator의 현재 source concept과 registry primary가 각각 위 원문과 정확히 일치해야 한다.
- 새 concept은 v01~v52 전체 source에서 exact duplicate가 없어야 한다.
- 동일 변경 묶음으로 source concept/text와 registry primary만 갱신한 뒤, 행 수·locator·primary 정합성·비대상 registry 행 바이트 동일성을 검증한다.
