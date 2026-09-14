# A06 v07:32~41 의미·자연성 재서술 사전 변경 계획

## 범위·보존

- source SHA-256: `9DD737E59DB677440AE444B6EB4185939F0CD9ADEA13059C13BDA0112BBCBAEB`
- registry SHA-256: `96B45DFF9C946E5F09D4C726F2FB8B5FD10D8443907F099F491E0AE3E52CD7F7`
- locator는 `stage2_(16)relational_composition_high_density_train_v07.source.psv:32~41`으로 고정한다. source concept/text와 같은 locator registry primary 외 field·행 순서·relations·other_type는 보존한다.
- v01, 다른 영역, package train/val, manifest, 중앙 원장, checkpoint, 공용 감사기는 수정하지 않는다. registry 원복 전체 바이트는 반영 직전 backup `A06_registry_before_v07_semantic_rewrite_32_41_2026-09-14.jsonl`에 보존한다.

| line | 기존 concept → 새 concept | relations | 직접 재서술 근거 |
|---:|---|---|---|
| 32 | 서비스 노드에서 자동 확장기로 이어지는 자동 복귀 경로 — 경로 보존 → 서비스 노드 오류 복구의 자동 확장 인계 | `part_of,process,role` | 복구 담당자가 서비스 노드 오류를 확인해 자동 확장 조치를 인계한다. |
| 33 | 장애 통보와 백업 저장소 사이의 임시 차단 연결 — 결과 검증 → 장애 통보 시 백업 저장소 접근 차단 분류 | `process,classification,attribute` | 복제 지연과 오류율로 차단·계속 접근 대상을 분류한다. |
| 34 | 배포 승인 판독 뒤 캐시 계층에 전달되는 정상 복귀 — 영향 검토 → 배포 승인 후 캐시 정상 복귀 확인 | `process,state,function` | 캐시 기능 수치로 정상 복귀 상태를 확인한다. |
| 35 | 오류 로그에서 요청 대기열까지 부하 계측기로 확인하는 교차 확인 — 예외 점검 → 오류 로그와 부하 계측기 대기열 대조 | `process,role,comparison` | 담당자가 오류 수·대기열 길이·CPU 사용률을 비교한다. |
| 36 | 대체 경로에 따른 상태 점검표·복구 담당자·서비스 노드 순차 흐름 — 독립 확인 → 대체 서비스 노드의 복구 상태 인계 | `part_of,state,attribute` | 복구 과정의 대체 노드 오류율·부하 상태를 다음 교대자에게 인계한다. |
| 37 | 부하 계측기에서 자동 확장기로 이어지는 승인 전 경로 — 분기 기록 → 부하 경보 확인 뒤 자동 확장 승인 절차 | `process,role,state` | 운영자가 부하 경보를 확인한 뒤 자동 확장을 승인한다. |
| 38 | 복구 담당자와 상태 점검표 사이의 승인 후 연결 — 중간 판정 → 복구 담당자의 상태 점검표 승인 기록 | `part_of,process,role` | 담당자가 복구 과정의 점검표를 검토하고 승인 기록을 남긴다. |
| 39 | 요청 대기열 판독 뒤 오류 로그에 전달되는 저부하 운전 — 신호 전달 → 대기열 저부하 확인의 경로 분류 | `process,classification,attribute` | 대기열 길이와 오류율이 낮을 때 현재·백업 경로 대상을 분류한다. |
| 40 | 캐시 계층에서 배포 승인까지 상태 점검표로 확인하는 보류 해제 — 대상 추적 → 캐시 회복 뒤 배포 승인 보류 해제 | `process,state,function` | 캐시 기능과 부하 수치가 회복된 뒤 배포 보류를 해제한다. |
| 41 | 새벽 판독에 따른 백업 저장소·장애 통보·트래픽 분배기 순차 흐름 — 순서 기록 → 백업 지연과 장애 통보의 새벽 교대 대조 | `process,role,comparison` | 교대 담당자가 복제 지연·통보 시각·분배기 오류를 비교한다. |

## 새 text

| line | text |
|---:|---|
| 32 | 서비스 노드 오류가 줄어들고 자동 확장기가 추가 노드를 제안할 때, 서비스 노드 오류 복구의 자동 확장 인계는 장애 복구 과정의 일부로서 복구 담당자가 오류율과 남은 용량을 다음 운영자에게 넘기는 과정이다. 인계받은 운영자가 수치를 확인하기 전에는 노드를 늘리지 않아 불필요한 비용을 막는다. |
| 33 | 장애 통보 뒤 백업 저장소의 복제 지연과 서비스 오류율이 함께 올라갈 때, 장애 통보 시 백업 저장소 접근 차단 분류는 운영자가 차단할 서비스와 계속 접근할 서비스를 분류하는 과정이다. 복제 지연이 큰 서비스는 접근을 제한해 최신 데이터 누락을 막는다. |
| 34 | 배포 승인이 끝난 뒤 캐시 적중률이 오르고 오래된 응답 비율이 낮아질 때, 배포 승인 후 캐시 정상 복귀 확인은 캐시 계층의 정상 기능을 확인하는 과정과 그 상태를 말한다. 두 수치가 회복되기 전에는 새 배포를 승인하지 않아 캐시 부하 급증을 막는다. |
| 35 | 오류 로그의 시간 초과 수가 늘고 요청 대기열 길이와 CPU 사용률도 함께 변할 때, 오류 로그와 부하 계측기 대기열 대조에서 장애 대응 담당자는 세 기록의 시각과 수치를 비교한다. 수치가 서로 맞지 않으면 대기열 제한을 해제하지 않아 오류 재발을 막는다. |
| 36 | 대체 서비스 노드가 요청을 받기 시작한 뒤 오류율과 CPU 사용률이 보고될 때, 대체 서비스 노드의 복구 상태 인계는 장애 복구 과정의 일부로서 새 노드의 부하 상태를 다음 교대자에게 넘기는 상태 점검이다. 오류율이 남아 있으면 노드를 정상 경로에 넣지 않아 요청 실패 확산을 막는다. |
| 37 | 부하 계측기가 CPU 사용률과 대기 요청 수의 상승을 알릴 때, 부하 경보 확인 뒤 자동 확장 승인 절차는 운영자가 확인된 부하 수치를 검토해 자동 확장을 승인하는 과정이다. 승인 전에는 새 노드를 추가하지 않아 설정 충돌과 불필요한 비용을 막는다. |
| 38 | 복구 작업이 끝나고 상태 점검표에 오류율과 경보 해제 시각이 기록될 때, 복구 담당자의 상태 점검표 승인 기록은 장애 대응 과정의 일부로서 복구 담당자가 점검 결과를 검토해 승인 내용을 남기는 과정이다. 기록이 없으면 복구를 완료로 처리하지 않아 같은 장애의 재발을 막는다. |
| 39 | 요청 대기열 길이와 오류율이 모두 낮아질 때, 대기열 저부하 확인의 경로 분류는 운영자가 현재 경로에 남길 요청과 백업 경로를 종료할 요청을 분류하는 과정이다. 저부하 수치가 이어지기 전에는 백업 경로를 닫지 않아 재차 늘어난 요청을 막는다. |
| 40 | 캐시 적중률과 처리 가능 용량이 정상 범위로 돌아올 때, 캐시 회복 뒤 배포 승인 보류 해제는 캐시 계층의 확장 기능을 다시 켜고 배포 승인 상태를 해제하는 과정이다. 두 수치가 확인되기 전에는 보류를 해제하지 않아 캐시 부하 급증을 막는다. |
| 41 | 새벽 교대 때 백업 저장소의 복제 지연, 장애 통보 시각, 트래픽 분배기의 연결 오류가 함께 기록될 때, 백업 지연과 장애 통보의 새벽 교대 대조는 교대 담당자가 세 기록의 시각과 수치를 비교하는 과정이다. 수치가 맞지 않으면 백업 경로 전환을 해제하지 않아 최신 데이터 누락을 막는다. |

## 원복 source 행

```text
서비스 노드에서 자동 확장기로 이어지는 자동 복귀 경로 — 경로 보존|part_of,process,role||앞 단계의 값을 받은 뒤 다음 담당이 조치를 선택하는 연결에서 서비스 노드에서 자동 확장기로 이어지는 자동 복귀 경로 — 경로 보존은 드러난다. 마지막 결과만 보고 출발점을 거꾸로 추정하지 않는다.
장애 통보와 백업 저장소 사이의 임시 차단 연결 — 결과 검증|process,classification,attribute||운영 기록을 시간순으로 놓으면 장애 통보와 백업 저장소 사이의 임시 차단 연결 — 결과 검증은 중간 전달이 보인다. 전달자가 바뀌어도 각 단계의 책임을 구분한다.
배포 승인 판독 뒤 캐시 계층에 전달되는 정상 복귀 — 영향 검토|process,state,function||센서 값과 작업 명령을 함께 읽으면 배포 승인 판독 뒤 캐시 계층에 전달되는 정상 복귀 — 영향 검토는 각 고리가 이어지는 이유를 확인할 수 있다. 한 고리의 결과를 다른 고리의 원인으로 확대하지 않는다.
오류 로그에서 요청 대기열까지 부하 계측기로 확인하는 교차 확인 — 예외 점검|process,role,comparison||현장 기록에서는 오류 로그에서 요청 대기열까지 부하 계측기로 확인하는 교차 확인 — 예외 점검은 입력, 판정, 실행이 차례로 보인다. 어느 한 단계가 누락되면 다음 관계는 미확정으로 둔다.
대체 경로에 따른 상태 점검표·복구 담당자·서비스 노드 순차 흐름 — 독립 확인|part_of,state,attribute||경로 점검 결과 대체 경로에 따른 상태 점검표·복구 담당자·서비스 노드 순차 흐름 — 독립 확인은 앞 단계와 다음 단계가 모두 확인될 때만 연결을 확정한다. 일부 기록만으로 전체 경로를 채우지 않는다.
부하 계측기에서 자동 확장기로 이어지는 승인 전 경로 — 분기 기록|process,role,state||처리 순서가 적힌 목록에서 부하 계측기에서 자동 확장기로 이어지는 승인 전 경로 — 분기 기록은 앞뒤 관계를 분리한다. 누락된 확인은 결과와 같은 의미로 취급하지 않는다.
복구 담당자와 상태 점검표 사이의 승인 후 연결 — 중간 판정|part_of,process,role||대기 중인 작업표에서 복구 담당자와 상태 점검표 사이의 승인 후 연결 — 중간 판정은 앞선 관찰과 후속 조치가 맞물린다. 순서를 바꾸어 기록하지 않는다.
요청 대기열 판독 뒤 오류 로그에 전달되는 저부하 운전 — 신호 전달|process,classification,attribute||관측표를 보면 요청 대기열 판독 뒤 오류 로그에 전달되는 저부하 운전 — 신호 전달은 신호에서 판단을 거쳐 실행으로 이어진다. 각 단계의 기록을 따로 남겨 중간 관계를 건너뛰지 않는다.
캐시 계층에서 배포 승인까지 상태 점검표로 확인하는 보류 해제 — 대상 추적|process,state,function||현장 담당자는 캐시 계층에서 배포 승인까지 상태 점검표로 확인하는 보류 해제 — 대상 추적은 신호·판정·조작의 방향을 화살표로 표시한다. 뒤 단계의 기록이 앞 단계를 자동으로 증명하지는 않는다.
새벽 판독에 따른 백업 저장소·장애 통보·트래픽 분배기 순차 흐름 — 순서 기록|process,role,comparison||교대 인계 때 새벽 판독에 따른 백업 저장소·장애 통보·트래픽 분배기 순차 흐름 — 순서 기록은 경로를 처음부터 다시 대조한다. 중간 확인이 남아 있을 때만 마지막 상태를 연결한다.
```

## 원복 registry locator 행

```jsonl
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":32,"primary":"서비스 노드에서 자동 확장기로 이어지는 자동 복귀 경로 — 경로 보존","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":33,"primary":"장애 통보와 백업 저장소 사이의 임시 차단 연결 — 결과 검증","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":34,"primary":"배포 승인 판독 뒤 캐시 계층에 전달되는 정상 복귀 — 영향 검토","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":35,"primary":"오류 로그에서 요청 대기열까지 부하 계측기로 확인하는 교차 확인 — 예외 점검","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":36,"primary":"대체 경로에 따른 상태 점검표·복구 담당자·서비스 노드 순차 흐름 — 독립 확인","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":37,"primary":"부하 계측기에서 자동 확장기로 이어지는 승인 전 경로 — 분기 기록","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":38,"primary":"복구 담당자와 상태 점검표 사이의 승인 후 연결 — 중간 판정","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":39,"primary":"요청 대기열 판독 뒤 오류 로그에 전달되는 저부하 운전 — 신호 전달","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":40,"primary":"캐시 계층에서 배포 승인까지 상태 점검표로 확인하는 보류 해제 — 대상 추적","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
{"source_file":"stage2_(16)relational_composition_high_density_train_v07.source.psv","source_line":41,"primary":"새벽 판독에 따른 백업 저장소·장애 통보·트래픽 분배기 순차 흐름 — 순서 기록","term_kind":"constructed_scenario","definition":"클라우드 서비스 부하·장애 대응에서 다중 홉 관계 연결과 방향 보존을(를) 판정하는 관계 조합 개념","provenance_kind":"internal_family_reservation","provenance_ref":"S2-A06-T-007","review_status":"generated_pending_semantic_review"}
```

## 적용 전제

- 10개 locator의 현재 source concept과 registry primary가 각각 위 원문과 정확히 일치해야 한다.
- 새 concept은 v01~v52 전체 source에서 exact duplicate가 없어야 한다.
- 동일 변경 묶음으로 source concept/text와 registry primary만 갱신한 뒤, 행 수·locator·primary 정합성·비대상 registry 행 바이트 동일성을 검증한다.
