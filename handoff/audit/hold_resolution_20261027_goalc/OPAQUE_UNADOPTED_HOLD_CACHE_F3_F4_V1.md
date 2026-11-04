# 미채택 HOLD의 본문 없는 전역 계수

기존 캐시의 `pick`은 부모 상태3의 현재 roster 판정이 HOLD이면 원문 text를 반환하지만, 실제 작성기는 HOLD에서 text를 직렬화하지 않고 위치·원형 SHA·판정만 기록한다. `original_signals`와 경계는 scan에 이미 있다. 따라서 미채택 HOLD의 body decode는 채택 본문 재현이나 토큰 계수에 필요하지 않다. 기존 restricted guard도 이 경로에서 빈 text를 사용한다. 읽은 호출부는 guarded cache1~5, resolution cache/partial cache, hold cache, corpus cache의 build/verify다.

| 안 | 내용 | 장점 | 단점 | 영향도 | 수행비용 |
|---|---|---|---|---|---|
| A | V4 민감 ID/SHA만 새 cache adapter에 반영 | 기존 경로 최소 변경 | 다른 미채택 HOLD를 새로 분류할 때 실행 중 전역 캐시를 다시 중단할 수 있음 | 신규 adapter와 보호계약 | 낮음 |
| B | V4 보호를 유지하고 현재 roster HOLD의 모든 부모 위치를 metadata만으로 고정하여 body decode 전에 투영 | 원형을 보존하며 불필요한 HOLD 본문 처리를 없앰 | 전체 위치 결합과 독립 계수, projection 회귀 검증이 추가됨 | 새 adapter·새 metadata 계약·새 캐시만 | 중간 |
| C | 채택분만 증분 캐시에 덧붙이고 기존 전체 consumer 생략 | 당장 생성량 감소 | EOS·기존 본문·중복·분할 경계 전체 증거가 달라짐 | 전역 검증 계약 재설계 | 높음 |

권장 B. 예를 들어 ROOT28/roster20의 미채택106236위치는 그대로 HOLD로 남으며, 이를 불량·민감 자료로 재분류하지 않는다. 실제 민감9 ID/10 SHA/15 부모 위치의 V4 규칙은 별도로 유지한다. 채택 KEEP/EDIT의 원문 비교·코드 guard·인코딩과 전체 consumer는 기존대로 수행한다. 속도 개선은 아직 측정하지 않았다.

| 파일·경로 | 예정 동작 | 권한 근거 | NOT_RUN·제외 |
|---|---|---|---|
| 이 audit의 새 opaque helper·producer·fixture test·계약 | 현재 roster HOLD와 기존 text-free 부모 ledger를 결합 | 사용자 전체 정제 A–E, 새 CPU 파생 캐시·검증 허가 | 원형 덮기·보호 원문 decode·TXT 작성0 |
| 이 audit의 새 guarded cache6·scope·실행기 | V4와 선택된 opaque 계약을 고정하고 전체 build/consumer 재사용 | 같은 지시의 CPU 구현·전체 계수 | 기존 cache12 재실행·덮기0 |
| 자기 WIP·공개 조정 MD | 실제 구현/검증/미실행 구분 | 사용자 작업 재개·tmp 교통정리 지시 | 타 세션 전용 경로·프로세스0 |

| 축 | 영향 | 내용 |
|---|---|---|
| 코드 | 있음 | 새 inputs의 iter_scan과 새 engine의 HOLD 불변식만 추가한다. 기존 parser/guard/engine을 재사용하고 함수 시그니처는 바꾸지 않는다. |
| 데이터 | 있음 | 새 계약에 현재 roster의 정확 SHA와 모든 HOLD 부모 위치 metadata를 저장한다. 기존 raw·캐시·리뷰를 변경하지 않는다. |
| 테스트 | 있음 | metadata identity, 양쪽 판정, 알 수 없는 별칭, restricted 구별, accepted source의 기존 decode, HOLD를 KEEP로 승격하는 실패 경로를 확인한다. 새 전역 캐시 뒤 기존 전체5proof와 독립 delta를 요구한다. |
| 정본 문서 | 제한 | 중간 audit/WIP에 상태를 남기며 최종 정본 연쇄와 핸드오프는 목표E의 미완료 작업이다. 공유09를 수정하지 않는다. |
| 기술부채·순서 | 있음 | 현재 roster마다 새 계약을 고정한다. 일반 HOLD에 restricted 표식을 붙이지 않는다. 전체 consumer를 줄이는 최적화는 하지 않는다. |
| GPU·학습 소유권 | 없음 | CPU1/CUDA 비움이며 모델·학습 실행0이다. |
| 데이터 범위·비교 조건 | 있음 | 승인된 잔여460695의 기존 parent만 읽고 새300M·TinyDataset은 제외한다. 학습 풀 변경 승인이 아니다. |
| 증거 수준·문서 연쇄 | 있음 | fixture, metadata 검산, 전체 cache/consumer 증거를 나눠 기록한다. 구현을 실측 속도 개선이나 내용 복구 완료로 표시하지 않는다. |

종합: opaque는 캐시에서 본문을 사용하지 않는다는 뜻이다. 실제 원문 검토·정제·각 역할의 전량 읽기는 계속 필요하다. 미채택을 삭제하거나 검토 완료로 세지 않는다.
