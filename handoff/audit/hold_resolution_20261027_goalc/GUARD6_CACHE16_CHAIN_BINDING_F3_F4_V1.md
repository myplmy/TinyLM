# 최신 선택과 cache9 실행 연결

cache15의 전체 처리·소비자 검산 엔진과 소유 프로세스 수명 관리를 재사용한다.
새 연결은 metadata 전용 census의 runtime pin과 실제 worker 양쪽을 cache9에 맞추는 것이다.
cache9의 guard6, 동일한 세 승인 파생본만 재사용하는 계약, 보호 원문 접근 차단을 유지한다.

| 안 | 영향과 비용 |
|---|---|
| 기존 cache7 worker를 그대로 실행 | 새 guard와 실제 실행 코드가 일치하지 않음 |
| 기존 frozen worker의 두 import와 census import만 cache9로 연결 | 계산·프로세스 수명은 유지하며 현재 계약을 실행함 |
| 전체 캐시 엔진 재작성 | 검증 범위와 구현 비용이 커짐 |

두 번째 안을 사용한다. 기존 코드 파일과 기존 캐시를 수정하지 않는다.
새 namespace cache16 하나를 생성하고 성공한 실제 build exit0 뒤 consumer를 실행한다.
원형·후보·parent census 사본을 새로 저장하지 않는다. census는 기존 manifest를 참조하고
460695위치와 입력ID를 metadata만 재계수한다. parent의 본문 필드는 decode하지 않는다.

검증은 cache9 실제 초기화·일반 guard 위임까지 포함한15개 회귀와 새 연결의 실제
설정·pin 사전검사를 사용한다. build·consumer는 각각 실제 프로세스 종료값과 별도
증거로 판정한다. 사전검사만으로 cache16 생성·의미 완료·학습 승인을 주장하지 않는다.
과거 제한 비교본 읽기 시도는 observer가 읽기 전에 차단했으며 해당 부정 증거를 보존한다.
새 경로는 그 비교본을 다시 읽거나 해시하지 않고 기존 승인 근거와 세 파생본 SHA만 쓴다.

관련 소유 범위는 이 감사 폴더의 두 새 adapter, cache16 namespace와 matching
roster/opaque/reference census 설정·검증 증거뿐이다. 다른 세션, 모델, GPU,
추가300M, 원형 덮기·삭제와 외부 Git 변경은 포함하지 않는다.
