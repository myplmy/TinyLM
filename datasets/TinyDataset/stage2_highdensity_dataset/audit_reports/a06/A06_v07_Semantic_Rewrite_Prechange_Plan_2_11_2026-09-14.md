# A06 v07:2~11 의미·자연성 재서술 사전 변경 계획

## 범위·보존

- source SHA-256: `F3005B6832FBFBF02E4CF70727F0FA43467A39D4CCD38321390E96D17A296438`
- registry SHA-256: `E625DE4D9D95F43FDA547F01C09D2C436528C5CA1F1D8AA8DC6F49F9FFCC42A0`
- locator는 `stage2_(16)relational_composition_high_density_train_v07.source.psv:2~11`으로 고정한다. source concept/text와 같은 locator registry primary 외 field·행 순서·relations·other_type는 보존한다.
- v01, 다른 영역, package train/val, manifest, 중앙 원장, checkpoint, 공용 감사기는 수정하지 않는다. registry 원복 전체 바이트는 반영 직전 backup `A06_registry_before_v07_semantic_rewrite_2_11_2026-09-14.jsonl`에 보존한다.

| line | 기존 concept → 새 concept | relations | 직접 재서술 근거 |
|---:|---|---|---|
| 2 | 복구 담당자에서 상태 점검표로 이어지는 자동 복귀 경로 — 독립 확인 → 복구 담당자의 상태 점검표 갱신 | `part_of,process,role` | 장애 대응의 마무리 단계에서 담당자가 상태와 재발 여부를 기록한다. |
| 3 | 요청 대기열과 오류 로그 사이의 임시 차단 연결 — 분기 기록 → 오류 로그 기반 요청 대기열 임시 차단 분류 | `process,classification,attribute` | 대기열 길이와 오류 비율로 차단·계속 처리 대상을 분류한다. |
| 4 | 캐시 계층 판독 뒤 배포 승인에 전달되는 경보 누적 — 중간 판정 → 캐시 경보 누적에 따른 배포 승인 보류 | `process,state,function` | 캐시 감시기가 반복 경보를 전달하고 배포 담당자가 보류 상태를 유지한다. |
| 5 | 백업 저장소에서 장애 통보까지 트래픽 분배기로 확인하는 교차 확인 — 신호 전달 → 장애 통보 시 트래픽 분배기 백업 경로 대조 | `process,role,comparison` | 담당자가 분배기 요청 수와 백업 복제 지연을 비교한다. |
| 6 | 대체 경로에 따른 자동 확장기·서비스 노드·복구 담당자 순차 흐름 — 대상 추적 → 자동 확장 뒤 서비스 노드 복구 상태 확인 | `part_of,state,attribute` | 복구 과정의 확장 뒤 노드 상태와 부하 수치를 확인한다. |
| 7 | 트래픽 분배기에서 상태 점검표로 이어지는 승인 전 경로 — 순서 기록 → 트래픽 분배기 상태 점검 승인 절차 | `process,role,state` | 운영자가 점검표를 확인한 뒤 경로 변경을 승인한다. |
| 8 | 서비스 노드와 자동 확장기 사이의 승인 후 연결 — 상태 묶음 → 서비스 노드 증설 승인 절차 | `part_of,process,role` | 장애 복구의 일부로 담당자가 자동 확장 제안을 확인해 증설을 승인한다. |
| 9 | 장애 통보 판독 뒤 백업 저장소에 전달되는 우회 승인 — 우선 처리 → 장애 통보 뒤 백업 저장소 우회 승인 분류 | `process,classification,attribute` | 복제 지연과 오류율로 즉시 우회와 대기 대상을 분류한다. |
| 10 | 배포 승인에서 캐시 계층까지 자동 확장기로 확인하는 보류 해제 — 연결 확인 → 배포 승인 뒤 캐시 계층 확장 보류 해제 | `process,state,function` | 캐시 기능과 확장 조건을 확인한 뒤 보류 상태를 해제한다. |
| 11 | 새벽 판독에 따른 오류 로그·요청 대기열·부하 계측기 순차 흐름 — 출처 대조 → 오류 로그와 대기열 부하의 교대 대조 | `process,role,comparison` | 교대 담당자가 오류 코드·대기열 길이·부하 수치를 대조한다. |

## 새 text

| line | text |
|---:|---|
| 2 | 서비스 노드의 오류율이 정상 범위로 돌아온 뒤, 복구 담당자의 상태 점검표 갱신은 장애 대응 과정의 마지막 단계로서 복구 담당자가 서비스 상태와 재발 여부를 점검표에 기록하는 절차다. 점검 결과가 빠지면 자동 복귀를 완료로 처리하지 않아 같은 장애의 재발을 막는다. |
| 3 | 요청 대기열 길이가 늘고 오류 로그에 시간 초과가 반복될 때, 오류 로그 기반 요청 대기열 임시 차단 분류는 운영자가 차단이 필요한 대기열과 계속 처리할 대기열을 분류하는 과정이다. 대기열 길이와 오류 비율이 회복되기 전에는 차단을 풀지 않아 오류 확산을 막는다. |
| 4 | 캐시 적중률이 떨어지고 오래된 응답 비율이 계속 늘 때, 캐시 경보 누적에 따른 배포 승인 보류는 캐시 감시기가 반복 경보를 모아 배포 담당자에게 전달하는 과정과 그 보류 상태를 말한다. 경보가 해소되기 전에는 새 배포를 승인하지 않아 장애 원인과 배포 영향이 섞이는 것을 막는다. |
| 5 | 장애 통보가 들어온 뒤 트래픽 분배기가 백업 저장소로 보낸 요청 수와 복제 지연이 다르게 나타날 때, 장애 통보 시 트래픽 분배기 백업 경로 대조에서 장애 대응 담당자는 두 기록의 시각과 수치를 비교한다. 복제 지연이 확인되기 전에는 백업 경로로 전환하지 않아 최신 데이터 누락을 막는다. |
| 6 | 자동 확장기가 서비스 노드를 추가한 뒤 새 노드의 오류율과 CPU 사용률이 함께 보고될 때, 자동 확장 뒤 서비스 노드 복구 상태 확인은 장애 복구 과정의 일부로서 운영자가 두 수치를 확인하는 상태 점검이다. 오류율이 남아 있으면 노드를 정상 경로에 넣지 않아 요청 실패 확산을 막는다. |
| 7 | 트래픽 분배기의 연결 오류가 늘어 상태 점검표가 생성될 때, 트래픽 분배기 상태 점검 승인 절차는 운영자가 점검표의 오류 수와 대상 노드를 확인한 뒤 경로 변경을 승인하는 과정이다. 승인이 나기 전에는 새 노드로 요청을 보내지 않아 장애 구간 확대를 막는다. |
| 8 | 서비스 노드의 CPU 사용률이 계속 높아 자동 확장기가 증설을 제안할 때, 서비스 노드 증설 승인 절차는 장애 복구 과정의 일부로서 복구 담당자가 남은 용량과 오류율을 확인해 증설을 승인하는 과정이다. 승인 없이 노드를 늘리지 않아 불필요한 비용과 설정 충돌을 막는다. |
| 9 | 장애 통보 뒤 백업 저장소의 복제 지연과 서비스 오류율이 함께 올라갈 때, 장애 통보 뒤 백업 저장소 우회 승인 분류는 운영자가 즉시 우회할 서비스와 복제 완료를 기다릴 서비스를 분류하는 과정이다. 복제 지연이 큰 서비스는 우회를 보류해 최신 데이터 손실을 막는다. |
| 10 | 배포 승인이 끝난 뒤 캐시 대기열 길이와 자동 확장기의 처리 가능 용량이 정상 범위로 돌아올 때, 배포 승인 뒤 캐시 계층 확장 보류 해제는 캐시 계층의 확장 기능을 다시 켜는 과정과 그 상태 변화를 말한다. 두 수치가 확인되기 전에는 보류를 해제하지 않아 캐시 부하 급증을 막는다. |
| 11 | 새벽 교대 때 오류 로그의 시간 초과 수와 요청 대기열 길이, 부하 계측기의 CPU 사용률이 함께 변할 때, 오류 로그와 대기열 부하의 교대 대조는 교대 담당자가 세 기록의 시각과 수치를 비교하는 과정이다. 수치가 서로 맞지 않으면 대기열 제한을 해제하지 않아 오류 재발을 막는다. |

## 원복 source 행

```text
복구 담당자에서 상태 점검표로 이어지는 자동 복귀 경로 — 독립 확인|part_of,process,role||앞 단계의 값을 받은 뒤 다음 담당이 조치를 선택하는 연결에서 복구 담당자에서 상태 점검표로 이어지는 자동 복귀 경로 — 독립 확인은 드러난다. 마지막 결과만 보고 출발점을 거꾸로 추정하지 않는다.
요청 대기열과 오류 로그 사이의 임시 차단 연결 — 분기 기록|process,classification,attribute||운영 기록을 시간순으로 놓으면 요청 대기열과 오류 로그 사이의 임시 차단 연결 — 분기 기록은 중간 전달이 보인다. 전달자가 바뀌어도 각 단계의 책임을 구분한다.
캐시 계층 판독 뒤 배포 승인에 전달되는 경보 누적 — 중간 판정|process,state,function||센서 값과 작업 명령을 함께 읽으면 캐시 계층 판독 뒤 배포 승인에 전달되는 경보 누적 — 중간 판정은 각 고리가 이어지는 이유를 확인할 수 있다. 한 고리의 결과를 다른 고리의 원인으로 확대하지 않는다.
백업 저장소에서 장애 통보까지 트래픽 분배기로 확인하는 교차 확인 — 신호 전달|process,role,comparison||현장 기록에서는 백업 저장소에서 장애 통보까지 트래픽 분배기로 확인하는 교차 확인 — 신호 전달은 입력, 판정, 실행이 차례로 보인다. 어느 한 단계가 누락되면 다음 관계는 미확정으로 둔다.
대체 경로에 따른 자동 확장기·서비스 노드·복구 담당자 순차 흐름 — 대상 추적|part_of,state,attribute||경로 점검 결과 대체 경로에 따른 자동 확장기·서비스 노드·복구 담당자 순차 흐름 — 대상 추적은 앞 단계와 다음 단계가 모두 확인될 때만 연결을 확정한다. 일부 기록만으로 전체 경로를 채우지 않는다.
트래픽 분배기에서 상태 점검표로 이어지는 승인 전 경로 — 순서 기록|process,role,state||처리 순서가 적힌 목록에서 트래픽 분배기에서 상태 점검표로 이어지는 승인 전 경로 — 순서 기록은 앞뒤 관계를 분리한다. 누락된 확인은 결과와 같은 의미로 취급하지 않는다.
서비스 노드와 자동 확장기 사이의 승인 후 연결 — 상태 묶음|part_of,process,role||대기 중인 작업표에서 서비스 노드와 자동 확장기 사이의 승인 후 연결 — 상태 묶음은 앞선 관찰과 후속 조치가 맞물린다. 순서를 바꾸어 기록하지 않는다.
장애 통보 판독 뒤 백업 저장소에 전달되는 우회 승인 — 우선 처리|process,classification,attribute||관측표를 보면 장애 통보 판독 뒤 백업 저장소에 전달되는 우회 승인 — 우선 처리는 신호에서 판단을 거쳐 실행으로 이어진다. 각 단계의 기록을 따로 남겨 중간 관계를 건너뛰지 않는다.
배포 승인에서 캐시 계층까지 자동 확장기로 확인하는 보류 해제 — 연결 확인|process,state,function||현장 담당자는 배포 승인에서 캐시 계층까지 자동 확장기로 확인하는 보류 해제 — 연결 확인은 신호·판정·조작의 방향을 화살표로 표시한다. 뒤 단계의 기록이 앞 단계를 자동으로 증명하지는 않는다.
새벽 판독에 따른 오류 로그·요청 대기열·부하 계측기 순차 흐름 — 출처 대조|process,role,comparison||교대 인계 때 새벽 판독에 따른 오류 로그·요청 대기열·부하 계측기 순차 흐름 — 출처 대조는 경로를 처음부터 다시 대조한다. 중간 확인이 남아 있을 때만 마지막 상태를 연결한다.
```

## 원복 registry locator 행

```jsonl
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":2,"primary":"복구 담당자에서 상태 점검표로 이어지는 자동 복귀 경로 — 독립 확인","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":3,"primary":"요청 대기열과 오류 로그 사이의 임시 차단 연결 — 분기 기록","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":4,"primary":"캐시 계층 판독 뒤 배포 승인에 전달되는 경보 누적 — 중간 판정","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":5,"primary":"백업 저장소에서 장애 통보까지 트래픽 분배기로 확인하는 교차 확인 — 신호 전달","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":6,"primary":"대체 경로에 따른 자동 확장기·서비스 노드·복구 담당자 순차 흐름 — 대상 추적","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":7,"primary":"트래픽 분배기에서 상태 점검표로 이어지는 승인 전 경로 — 순서 기록","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":8,"primary":"서비스 노드와 자동 확장기 사이의 승인 후 연결 — 상태 묶음","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":9,"primary":"장애 통보 판독 뒤 백업 저장소에 전달되는 우회 승인 — 우선 처리","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":10,"primary":"배포 승인에서 캐시 계층까지 자동 확장기로 확인하는 보류 해제 — 연결 확인","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":11,"primary":"새벽 판독에 따른 오류 로그·요청 대기열·부하 계측기 순차 흐름 — 출처 대조","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
```

## 적용 전제

- 10개 locator의 현재 source concept과 registry primary가 각각 위 원문과 정확히 일치해야 한다.
- 새 concept은 v01~v52 전체 source에서 exact duplicate가 없어야 한다.
- 동일 변경 묶음으로 source concept/text와 registry primary만 갱신한 뒤, 행 수·locator·primary 정합성·비대상 registry 행 바이트 동일성을 검증한다.
