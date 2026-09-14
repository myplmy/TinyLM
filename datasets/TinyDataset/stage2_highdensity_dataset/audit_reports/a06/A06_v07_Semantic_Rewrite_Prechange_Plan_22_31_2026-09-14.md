# A06 v07:22~31 의미·자연성 재서술 사전 변경 계획

## 범위·보존

- source SHA-256: `5B646C0FFA1858C528B0D5BF1918E894C208800050644306F5C6C2027F4127E0`
- registry SHA-256: `05B100B441B3DFEAF6B176928683BFA2C419DC877FAC418345249B2A044DAF65`
- locator는 `stage2_(16)relational_composition_high_density_train_v07.source.psv:22~31`으로 고정한다. source concept/text와 같은 locator registry primary 외 field·행 순서·relations·other_type는 보존한다.
- v01, 다른 영역, package train/val, manifest, 중앙 원장, checkpoint, 공용 감사기는 수정하지 않는다. registry 원복 전체 바이트는 반영 직전 backup `A06_registry_before_v07_semantic_rewrite_22_31_2026-09-14.jsonl`에 보존한다.

| line | 기존 concept → 새 concept | relations | 직접 재서술 근거 |
|---:|---|---|---|
| 22 | 배포 승인에서 캐시 계층으로 이어지는 복구 직후 경로 — 신호 전달 → 배포 승인 뒤 캐시 확장 기능 재개 | `process,state,function` | 캐시 부하와 처리 용량을 확인한 뒤 확장 기능을 재개한다. |
| 23 | 오류 로그와 요청 대기열 사이의 예방 점검 연결 — 대상 추적 → 오류 로그와 요청 대기열 예방 점검 대조 | `process,role,comparison` | 담당자가 오류 코드와 대기열 길이를 비교해 제한 여부를 판단한다. |
| 24 | 상태 점검표 판독 뒤 복구 담당자에 전달되는 중앙 표본 — 순서 기록 → 상태 점검표 기반 복구 담당자 부하 확인 | `part_of,state,attribute` | 복구 과정에서 담당자가 점검표의 오류율·CPU 사용률을 확인한다. |
| 25 | 부하 계측기에서 자동 확장기까지 요청 대기열로 확인하는 후속 입력 — 상태 묶음 → 요청 대기열 부하 경보의 증설 인계 | `process,role,state` | 담당자가 대기열 부하 경보를 인계해 증설 여부를 판단한다. |
| 26 | 경계 직전에 따른 복구 담당자·상태 점검표·배포 승인 순차 흐름 — 우선 처리 → 복구 완료 전 상태 점검표 배포 승인 확인 | `part_of,process,role` | 담당자가 점검표를 확인한 뒤 복구 과정의 배포 승인을 결정한다. |
| 27 | 요청 대기열에서 오류 로그로 이어지는 경계 이후 경로 — 연결 확인 → 요청 대기열 오류율 기준 경로 분류 | `process,classification,attribute` | 오류율과 대기열 길이로 현재·백업 경로 대상을 분류한다. |
| 28 | 캐시 계층과 배포 승인 사이의 예외 기간 연결 — 출처 대조 → 캐시 장애 시 배포 승인 보류 | `process,state,function` | 캐시 기능 오류가 지속될 때 배포 승인 상태를 보류한다. |
| 29 | 백업 저장소 판독 뒤 장애 통보에 전달되는 배치 변경 — 범위 확인 → 부분 복제 기록의 장애 통보 대조 | `process,role,comparison,other` | 담당자가 부분 복제 기록과 통보 시각을 비교하되 표본 한계를 명시한다. |
| 30 | 자동 확장기에서 서비스 노드까지 복구 담당자로 확인하는 다음 교대 — 운영 인계 → 자동 확장 후 서비스 노드 부하 상태 인계 | `part_of,state,attribute` | 복구 과정의 새 노드 부하·오류율을 다음 교대자에게 인계한다. |
| 31 | 수동 전환에 따른 트래픽 분배기·상태 점검표·장애 통보 순차 흐름 — 회복 판정 → 수동 전환 뒤 트래픽 분배기 상태 점검 인계 | `process,role,state` | 담당자가 수동 전환 뒤 분배기 상태를 확인해 다음 교대자에게 넘긴다. |

## 새 text

| line | text |
|---:|---|
| 22 | 배포 승인이 끝난 뒤 캐시 대기열 길이와 자동 확장기의 처리 가능 용량이 정상 범위로 돌아올 때, 배포 승인 뒤 캐시 확장 기능 재개는 캐시 계층의 확장 기능을 다시 켜는 과정과 그 상태 변화를 말한다. 두 수치가 확인되기 전에는 기능을 재개하지 않아 캐시 부하 급증을 막는다. |
| 23 | 오류 로그에 시간 초과가 늘고 요청 대기열 길이도 증가할 때, 오류 로그와 요청 대기열 예방 점검 대조에서 장애 대응 담당자는 오류 코드와 대기열 길이의 시각·수치를 비교한다. 수치가 함께 높으면 대기열 제한을 유지해 오류 확산을 막는다. |
| 24 | 상태 점검표에 새 서비스 노드의 오류율과 CPU 사용률이 함께 기록될 때, 상태 점검표 기반 복구 담당자 부하 확인은 장애 복구 과정의 일부로서 복구 담당자가 두 수치를 확인하는 상태 점검이다. 오류율이 남아 있으면 노드를 정상 경로에 넣지 않아 요청 실패 확산을 막는다. |
| 25 | 요청 대기열 길이와 CPU 사용률이 임계값을 넘을 때, 요청 대기열 부하 경보의 증설 인계는 당직 운영자가 확인된 부하 수치를 다음 운영자에게 넘겨 노드 증설 여부를 판단하게 하는 과정이다. 인계받은 운영자가 수치를 확인하기 전에는 자동 확장을 실행하지 않아 불필요한 비용을 막는다. |
| 26 | 복구 작업 뒤 상태 점검표에 오류율과 캐시 적중률이 기록될 때, 복구 완료 전 상태 점검표 배포 승인 확인은 장애 대응 과정의 일부로서 복구 담당자가 점검 결과를 확인해 배포 승인을 결정하는 과정이다. 오류율이 남아 있으면 승인을 보류해 장애 원인과 배포 영향이 섞이는 것을 막는다. |
| 27 | 요청 대기열 길이와 오류율이 함께 오를 때, 요청 대기열 오류율 기준 경로 분류는 운영자가 현재 경로에서 재시도할 요청과 백업 경로로 보낼 요청을 분류하는 과정이다. 오류율이 확인되기 전에는 전환을 풀지 않아 오류 확산을 막는다. |
| 28 | 캐시 적중률이 급락하고 오래된 응답 비율이 늘 때, 캐시 장애 시 배포 승인 보류는 캐시 계층의 오류를 확인해 배포 승인 상태를 보류하는 과정이다. 캐시 기능이 회복되기 전에는 새 배포를 승인하지 않아 장애 원인과 배포 영향이 섞이는 것을 막는다. |
| 29 | 백업 저장소의 일부 복제 기록만 남고 장애 통보 시각이 다를 때, 부분 복제 기록의 장애 통보 대조에서 장애 대응 담당자는 확인된 복제 시각과 통보 시각을 비교한다. 부분 표본의 해석 한계 때문에 복제 완료로 단정하지 않아 최신 데이터 누락을 막는다. |
| 30 | 자동 확장기가 새 서비스 노드를 추가한 뒤 오류율과 CPU 사용률이 보고될 때, 자동 확장 후 서비스 노드 부하 상태 인계는 장애 복구 과정의 일부로서 새 노드의 부하 상태를 다음 교대자에게 넘기는 상태 점검이다. 오류율이 남아 있으면 노드를 정상 경로에 넣지 않아 요청 실패 확산을 막는다. |
| 31 | 수동 전환 뒤 트래픽 분배기의 연결 오류와 대상 노드 상태가 바뀔 때, 수동 전환 뒤 트래픽 분배기 상태 점검 인계는 당직 운영자가 두 상태를 확인해 다음 교대자에게 점검을 넘기는 과정이다. 점검이 끝나기 전에는 경로를 다시 바꾸지 않아 정상 노드까지 차단되는 일을 막는다. |

## 원복 source 행

```text
배포 승인에서 캐시 계층으로 이어지는 복구 직후 경로 — 신호 전달|process,state,function||앞 단계의 값을 받은 뒤 다음 담당이 조치를 선택하는 연결에서 배포 승인에서 캐시 계층으로 이어지는 복구 직후 경로 — 신호 전달은 드러난다. 마지막 결과만 보고 출발점을 거꾸로 추정하지 않는다.
오류 로그와 요청 대기열 사이의 예방 점검 연결 — 대상 추적|process,role,comparison||운영 기록을 시간순으로 놓으면 오류 로그와 요청 대기열 사이의 예방 점검 연결 — 대상 추적은 중간 전달이 보인다. 전달자가 바뀌어도 각 단계의 책임을 구분한다.
상태 점검표 판독 뒤 복구 담당자에 전달되는 중앙 표본 — 순서 기록|part_of,state,attribute||센서 값과 작업 명령을 함께 읽으면 상태 점검표 판독 뒤 복구 담당자에 전달되는 중앙 표본 — 순서 기록은 각 고리가 이어지는 이유를 확인할 수 있다. 한 고리의 결과를 다른 고리의 원인으로 확대하지 않는다.
부하 계측기에서 자동 확장기까지 요청 대기열로 확인하는 후속 입력 — 상태 묶음|process,role,state||현장 기록에서는 부하 계측기에서 자동 확장기까지 요청 대기열로 확인하는 후속 입력 — 상태 묶음은 입력, 판정, 실행이 차례로 보인다. 어느 한 단계가 누락되면 다음 관계는 미확정으로 둔다.
경계 직전에 따른 복구 담당자·상태 점검표·배포 승인 순차 흐름 — 우선 처리|part_of,process,role||경로 점검 결과 경계 직전에 따른 복구 담당자·상태 점검표·배포 승인 순차 흐름 — 우선 처리는 앞 단계와 다음 단계가 모두 확인될 때만 연결을 확정한다. 일부 기록만으로 전체 경로를 채우지 않는다.
요청 대기열에서 오류 로그로 이어지는 경계 이후 경로 — 연결 확인|process,classification,attribute||처리 순서가 적힌 목록에서 요청 대기열에서 오류 로그로 이어지는 경계 이후 경로 — 연결 확인은 앞뒤 관계를 분리한다. 누락된 확인은 결과와 같은 의미로 취급하지 않는다.
캐시 계층과 배포 승인 사이의 예외 기간 연결 — 출처 대조|process,state,function||대기 중인 작업표에서 캐시 계층과 배포 승인 사이의 예외 기간 연결 — 출처 대조는 앞선 관찰과 후속 조치가 맞물린다. 순서를 바꾸어 기록하지 않는다.
백업 저장소 판독 뒤 장애 통보에 전달되는 배치 변경 — 범위 확인|process,role,comparison,other|부분 표본의 해석 한계|관측표를 보면 백업 저장소 판독 뒤 장애 통보에 전달되는 배치 변경 — 범위 확인은 신호에서 판단을 거쳐 실행으로 이어진다. 각 단계의 기록을 따로 남겨 중간 관계를 건너뛰지 않는다. 부분 표본의 해석 한계 항목은 확인된 관계만 확정하게 한다.
자동 확장기에서 서비스 노드까지 복구 담당자로 확인하는 다음 교대 — 운영 인계|part_of,state,attribute||현장 담당자는 자동 확장기에서 서비스 노드까지 복구 담당자로 확인하는 다음 교대 — 운영 인계는 신호·판정·조작의 방향을 화살표로 표시한다. 뒤 단계의 기록이 앞 단계를 자동으로 증명하지는 않는다.
수동 전환에 따른 트래픽 분배기·상태 점검표·장애 통보 순차 흐름 — 회복 판정|process,role,state||교대 인계 때 수동 전환에 따른 트래픽 분배기·상태 점검표·장애 통보 순차 흐름 — 회복 판정은 경로를 처음부터 다시 대조한다. 중간 확인이 남아 있을 때만 마지막 상태를 연결한다.
```

## 원복 registry locator 행

```jsonl
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":22,"primary":"배포 승인에서 캐시 계층으로 이어지는 복구 직후 경로 — 신호 전달","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":23,"primary":"오류 로그와 요청 대기열 사이의 예방 점검 연결 — 대상 추적","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":24,"primary":"상태 점검표 판독 뒤 복구 담당자에 전달되는 중앙 표본 — 순서 기록","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":25,"primary":"부하 계측기에서 자동 확장기까지 요청 대기열로 확인하는 후속 입력 — 상태 묶음","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":26,"primary":"경계 직전에 따른 복구 담당자·상태 점검표·배포 승인 순차 흐름 — 우선 처리","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":27,"primary":"요청 대기열에서 오류 로그로 이어지는 경계 이후 경로 — 연결 확인","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":28,"primary":"캐시 계층과 배포 승인 사이의 예외 기간 연결 — 출처 대조","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":29,"primary":"백업 저장소 판독 뒤 장애 통보에 전달되는 배치 변경 — 범위 확인","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":30,"primary":"자동 확장기에서 서비스 노드까지 복구 담당자로 확인하는 다음 교대 — 운영 인계","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":31,"primary":"수동 전환에 따른 트래픽 분배기·상태 점검표·장애 통보 순차 흐름 — 회복 판정","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
```

## 적용 전제

- 10개 locator의 현재 source concept과 registry primary가 각각 위 원문과 정확히 일치해야 한다.
- 새 concept은 v01~v52 전체 source에서 exact duplicate가 없어야 한다.
- 동일 변경 묶음으로 source concept/text와 registry primary만 갱신한 뒤, 행 수·locator·primary 정합성·비대상 registry 행 바이트 동일성을 검증한다.
