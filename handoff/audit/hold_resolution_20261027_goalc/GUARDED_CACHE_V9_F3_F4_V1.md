# guard6와 기존 캐시 엔진의 연결

목표 §1·6 및 현재 파생 캐시 생성·검증 허가 안에서 CPU 구현·metadata 검사만 먼저 수행한다.
기존 GUARDED_CACHE_V8_F3_F4_V1.md의 원형·캐시·세 안전 파생본·opaque HOLD 경계를 유지한다.

| 안 | 내용 | 장점 | 위험·영향 | 비용 |
|---|---|---|---|---|
| A | guard5 캐시8을 그대로 사용 | 구현 없음 | 새 실제 차단360211/별칭을 계약 전체에 반영하지 못함 | 낮음이나 부적합 |
| B | 캐시8 엔진을 재사용하며 guard6 metadata·두 alias·선택 차단을 누적 | 기존 엔진/소비 검증 재사용 | 전 구간에서 같은 계약이 설치됐는지 확인 필요 | 중간 |
| C | 캐시 엔진을 다시 작성 | 구조 단순화 가능 | 직렬화·EOS·원문계보 회귀 범위 확대 | 높음 |

선택 B. guard6의13제한ID·25SHA·21부모metadata와 기존3안전파생본의 이전선택 불변을 함께 검사한다.
이전 guard5의 두 새 항목/4alias는 그대로 확인하고, 실제필터360211/historical360215 두 alias를 추가한다.
원형/패킷 payload를 새로 읽거나 복호화·재해시하지 않는다. 일반 HOLD는 민감자료로 재분류하지 않는다.
기존 ROOT가 승인한 EXCLUDE는 이전 선택의 정확한 행·원문SHA와 일치하고 body/hash가 없을 때만
그 제외 판정을 유지한다. 계약에 기록한 더 오래된 부모 HOLD와 후속 ROOT 제외를 구분한다.
새 실제필터 ID·alias·원문/packet SHA는 이전 행을 빌려도 HOLD만 허용한다.
새 제한자료를 임의 EXCLUDE로 바꾸거나 본문을 선택하는 예외는 없다.

경로: audit의 새 캐시9 어댑터·metadata 회귀·핀 보고만 신설. 이후 확정 선택/roster와 일치한
새 opaque/참조census/코드핀을 만든 뒤 별도 cache16 출력에 build·consumer를 한 번 수행한다.
기존 캐시·원형·로그·체크포인트·모델·GPU·학습·타 세션은 변경하지 않는다.
metadata/핀 검증 PASS를 실제 cache16 또는 모델 품질 PASS로 쓰지 않는다.
호출은 기존 cache8 API와 같고 새로운 전량 ledger 사본을 만들지 않는다. 실제 캐시 산출물은20MB미만
조각과 manifest로 연결하며 원래 출처·split·토크나이저·EOS·문서경계와 채택/HOLD 분리를 소비 검증한다.
관련 선택·roster·cache·WIP·결과·METHODS·COMPASS는 실제 최종 검증값으로 묶음 갱신한다.
