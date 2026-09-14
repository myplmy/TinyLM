# A06 v07:42~51 의미·자연성 재서술 사전 변경 계획

## 범위·보존

- source SHA-256: `F11E2D61586E10D5E99E301A617219E1642C1DBAF0E71E14009A55985D01500A`
- registry SHA-256: `41703F648731897FB83214301AA37853105628AAC457E5AA790889D1A9175199`
- locator는 `stage2_(16)relational_composition_high_density_train_v07.source.psv:42~51`으로 고정한다. source concept/text와 같은 locator registry primary 외 field·행 순서·relations·other_type는 보존한다.
- v01, 다른 영역, package train/val, manifest, 중앙 원장, checkpoint, 공용 감사기는 수정하지 않는다. registry 원복 전체 바이트는 반영 직전 backup `A06_registry_before_v07_semantic_rewrite_42_51_2026-09-14.jsonl`에 보존한다.

| line | 기존 concept → 새 concept | relations | 직접 재서술 근거 |
|---:|---|---|---|
| 42 | 자동 확장기에서 서비스 노드로 이어지는 야간 점검 경로 — 상태 묶음 → 야간 자동 확장 노드의 상태 점검 | `part_of,state,attribute` | 복구 과정에서 새 노드의 오류율·CPU 사용률을 확인한다. |
| 43 | 트래픽 분배기와 상태 점검표 사이의 우천 관찰 연결 — 우선 처리 → 트래픽 분배기 오류 우선 대응 인계 | `process,role,state` | 담당자가 분배기 오류와 대상 노드를 확인해 대응을 인계한다. |
| 44 | 서비스 노드 판독 뒤 자동 확장기에 전달되는 경보 누적 — 연결 확인 → 서비스 노드 경보의 자동 확장 요청 인계 | `part_of,process,role` | 복구 담당자가 서비스 노드 경보를 자동 확장 담당자에게 넘긴다. |
| 45 | 장애 통보에서 백업 저장소까지 오류 로그로 확인하는 긴급 확인 — 출처 대조 → 장애 통보 오류율 기반 백업 경로 분류 | `process,classification,attribute` | 오류율·복제 지연으로 백업 경로 전환 대상을 분류한다. |
| 46 | 정기 운전에 따른 배포 승인·캐시 계층·자동 확장기 순차 흐름 — 범위 확인 → 캐시 기록 상충 시 배포 승인 보류 | `process,state,function,other` | 캐시 수치와 배포 기록이 다를 때 기능 변경과 승인을 보류한다. |
| 47 | 오류 로그에서 요청 대기열로 이어지는 저부하 운전 경로 — 운영 인계 → 오류율 저하와 대기열 회복의 교대 대조 | `process,role,comparison` | 교대 담당자가 오류율과 대기열 길이의 회복 시각을 비교한다. |
| 48 | 상태 점검표와 복구 담당자 사이의 고부하 운전 연결 — 회복 판정 → 고부하 상태 점검표의 복구 조치 보류 | `part_of,state,attribute` | 복구 과정에서 CPU·대기열 수치가 높을 때 조치를 보류한다. |
| 49 | 부하 계측기 판독 뒤 자동 확장기에 전달되는 우회 승인 — 경로 보존 → 부하 계측기 경보의 우회 승인 절차 | `process,role,state` | 운영자가 부하 경보를 확인해 우회 경로를 승인한다. |
| 50 | 복구 담당자에서 상태 점검표까지 배포 승인으로 확인하는 현장 재검 — 결과 검증 → 복구 담당자의 배포 전 상태 점검 | `part_of,process,role` | 담당자가 배포 전 오류율·캐시 상태를 점검한다. |
| 51 | 비상 전환에 따른 요청 대기열·오류 로그·백업 저장소 순차 흐름 — 영향 검토 → 비상 전환 시 대기열 오류 백업 경로 분류 | `process,classification,attribute` | 대기열 길이·오류 코드·복제 지연으로 경로 대상을 분류한다. |

## 새 text

| line | text |
|---:|---|
| 42 | 야간에 자동 확장기가 새 서비스 노드를 추가한 뒤 오류율과 CPU 사용률이 보고될 때, 야간 자동 확장 노드의 상태 점검은 장애 복구 과정의 일부로서 새 노드의 부하 상태를 확인하는 점검이다. 오류율이 남아 있으면 노드를 정상 경로에 넣지 않아 요청 실패 확산을 막는다. |
| 43 | 트래픽 분배기에서 연결 오류가 늘고 상태 점검표가 생성될 때, 트래픽 분배기 오류 우선 대응 인계는 당직 운영자가 오류 수와 대상 노드를 확인해 다음 대응 담당자에게 조치를 넘기는 과정이다. 점검이 끝나기 전에는 경로를 바꾸지 않아 정상 노드까지 차단되는 일을 막는다. |
| 44 | 서비스 노드의 오류율이 높고 CPU 사용률도 임계값을 넘을 때, 서비스 노드 경보의 자동 확장 요청 인계는 장애 복구 과정의 일부로서 복구 담당자가 확인된 경보를 자동 확장 담당자에게 넘기는 과정이다. 담당자가 수치를 확인하기 전에는 노드를 추가하지 않아 불필요한 비용을 막는다. |
| 45 | 장애 통보 뒤 서비스 오류율과 백업 저장소의 복제 지연이 함께 올라갈 때, 장애 통보 오류율 기반 백업 경로 분류는 운영자가 백업 경로로 전환할 서비스와 현재 경로에서 재시도할 서비스를 분류하는 과정이다. 복제 지연이 큰 서비스는 전환을 보류해 최신 데이터 손실을 막는다. |
| 46 | 캐시 적중률은 정상인데 배포 기록에는 캐시 오류가 남아 있을 때, 캐시 기록 상충 시 배포 승인 보류는 캐시 계층의 기능 상태와 배포 승인 상태를 함께 보류하는 과정이다. 식별 기록 상충이 해소되기 전에는 새 배포를 승인하지 않아 장애 원인과 배포 영향이 섞이는 것을 막는다. |
| 47 | 오류 로그의 시간 초과 수가 줄고 요청 대기열 길이도 내려갈 때, 오류율 저하와 대기열 회복의 교대 대조에서 교대 담당자는 두 수치가 회복된 시각과 감소 폭을 비교한다. 회복 시각이 맞지 않으면 대기열 제한을 해제하지 않아 오류 재발을 막는다. |
| 48 | 상태 점검표에 CPU 사용률과 대기 요청 수가 모두 높게 나타날 때, 고부하 상태 점검표의 복구 조치 보류는 장애 복구 과정에서 자동 확장이나 경로 전환을 바로 실행하지 않는 보류 상태다. 부하 원인이 확인되기 전에는 조치를 바꾸지 않아 설정 충돌을 막는다. |
| 49 | 부하 계측기가 CPU 사용률과 대기 요청 수의 상승을 알릴 때, 부하 계측기 경보의 우회 승인 절차는 운영자가 확인된 부하 수치를 검토해 백업 경로 우회를 승인하는 과정이다. 승인 전에는 요청을 우회시키지 않아 최신 데이터가 없는 경로로의 전환을 막는다. |
| 50 | 배포를 승인하기 전 서비스 오류율과 캐시 적중률을 다시 확인할 때, 복구 담당자의 배포 전 상태 점검은 장애 복구 과정의 일부로서 복구 담당자가 점검 결과를 검토하는 과정이다. 오류율이 남아 있으면 배포를 승인하지 않아 장애 원인과 배포 영향이 섞이는 것을 막는다. |
| 51 | 비상 전환 뒤 요청 대기열 길이, 오류 로그의 코드, 백업 저장소의 복제 지연이 함께 바뀔 때, 비상 전환 시 대기열 오류 백업 경로 분류는 운영자가 백업 경로로 보낼 요청과 현재 경로에서 재시도할 요청을 분류하는 과정이다. 복제 지연이 큰 서비스는 전환을 보류해 최신 데이터 손실을 막는다. |

## 원복 source 행

```text
자동 확장기에서 서비스 노드로 이어지는 야간 점검 경로 — 상태 묶음|part_of,state,attribute||앞 단계의 값을 받은 뒤 다음 담당이 조치를 선택하는 연결에서 자동 확장기에서 서비스 노드로 이어지는 야간 점검 경로 — 상태 묶음은 드러난다. 마지막 결과만 보고 출발점을 거꾸로 추정하지 않는다.
트래픽 분배기와 상태 점검표 사이의 우천 관찰 연결 — 우선 처리|process,role,state||운영 기록을 시간순으로 놓으면 트래픽 분배기와 상태 점검표 사이의 우천 관찰 연결 — 우선 처리는 중간 전달이 보인다. 전달자가 바뀌어도 각 단계의 책임을 구분한다.
서비스 노드 판독 뒤 자동 확장기에 전달되는 경보 누적 — 연결 확인|part_of,process,role||센서 값과 작업 명령을 함께 읽으면 서비스 노드 판독 뒤 자동 확장기에 전달되는 경보 누적 — 연결 확인은 각 고리가 이어지는 이유를 확인할 수 있다. 한 고리의 결과를 다른 고리의 원인으로 확대하지 않는다.
장애 통보에서 백업 저장소까지 오류 로그로 확인하는 긴급 확인 — 출처 대조|process,classification,attribute||현장 기록에서는 장애 통보에서 백업 저장소까지 오류 로그로 확인하는 긴급 확인 — 출처 대조는 입력, 판정, 실행이 차례로 보인다. 어느 한 단계가 누락되면 다음 관계는 미확정으로 둔다.
정기 운전에 따른 배포 승인·캐시 계층·자동 확장기 순차 흐름 — 범위 확인|process,state,function,other|식별 기록 상충|경로 점검 결과 정기 운전에 따른 배포 승인·캐시 계층·자동 확장기 순차 흐름 — 범위 확인은 앞 단계와 다음 단계가 모두 확인될 때만 연결을 확정한다. 일부 기록만으로 전체 경로를 채우지 않는다. 식별 기록 상충 항목은 확인된 관계만 확정하게 한다.
오류 로그에서 요청 대기열로 이어지는 저부하 운전 경로 — 운영 인계|process,role,comparison||처리 순서가 적힌 목록에서 오류 로그에서 요청 대기열로 이어지는 저부하 운전 경로 — 운영 인계는 앞뒤 관계를 분리한다. 누락된 확인은 결과와 같은 의미로 취급하지 않는다.
상태 점검표와 복구 담당자 사이의 고부하 운전 연결 — 회복 판정|part_of,state,attribute||대기 중인 작업표에서 상태 점검표와 복구 담당자 사이의 고부하 운전 연결 — 회복 판정은 앞선 관찰과 후속 조치가 맞물린다. 순서를 바꾸어 기록하지 않는다.
부하 계측기 판독 뒤 자동 확장기에 전달되는 우회 승인 — 경로 보존|process,role,state||관측표를 보면 부하 계측기 판독 뒤 자동 확장기에 전달되는 우회 승인 — 경로 보존은 신호에서 판단을 거쳐 실행으로 이어진다. 각 단계의 기록을 따로 남겨 중간 관계를 건너뛰지 않는다.
복구 담당자에서 상태 점검표까지 배포 승인으로 확인하는 현장 재검 — 결과 검증|part_of,process,role||현장 담당자는 복구 담당자에서 상태 점검표까지 배포 승인으로 확인하는 현장 재검 — 결과 검증은 신호·판정·조작의 방향을 화살표로 표시한다. 뒤 단계의 기록이 앞 단계를 자동으로 증명하지는 않는다.
비상 전환에 따른 요청 대기열·오류 로그·백업 저장소 순차 흐름 — 영향 검토|process,classification,attribute||교대 인계 때 비상 전환에 따른 요청 대기열·오류 로그·백업 저장소 순차 흐름 — 영향 검토는 경로를 처음부터 다시 대조한다. 중간 확인이 남아 있을 때만 마지막 상태를 연결한다.
```

## 원복 registry locator 행

```jsonl
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":42,"primary":"자동 확장기에서 서비스 노드로 이어지는 야간 점검 경로 — 상태 묶음","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":43,"primary":"트래픽 분배기와 상태 점검표 사이의 우천 관찰 연결 — 우선 처리","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":44,"primary":"서비스 노드 판독 뒤 자동 확장기에 전달되는 경보 누적 — 연결 확인","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":45,"primary":"장애 통보에서 백업 저장소까지 오류 로그로 확인하는 긴급 확인 — 출처 대조","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":46,"primary":"정기 운전에 따른 배포 승인·캐시 계층·자동 확장기 순차 흐름 — 범위 확인","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":47,"primary":"오류 로그에서 요청 대기열로 이어지는 저부하 운전 경로 — 운영 인계","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":48,"primary":"상태 점검표와 복구 담당자 사이의 고부하 운전 연결 — 회복 판정","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":49,"primary":"부하 계측기 판독 뒤 자동 확장기에 전달되는 우회 승인 — 경로 보존","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":50,"primary":"복구 담당자에서 상태 점검표까지 배포 승인으로 확인하는 현장 재검 — 결과 검증","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":51,"primary":"비상 전환에 따른 요청 대기열·오류 로그·백업 저장소 순차 흐름 — 영향 검토","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
```

## 적용 전제

- 10개 locator의 현재 source concept과 registry primary가 각각 위 원문과 정확히 일치해야 한다.
- 새 concept은 v01~v52 전체 source에서 exact duplicate가 없어야 한다.
- 동일 변경 묶음으로 source concept/text와 registry primary만 갱신한 뒤, 행 수·locator·primary 정합성·비대상 registry 행 바이트 동일성을 검증한다.
