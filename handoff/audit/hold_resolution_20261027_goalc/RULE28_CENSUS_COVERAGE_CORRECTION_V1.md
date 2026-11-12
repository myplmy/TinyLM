# 대기열 밖 잔여 수의 현재 재계산

규칙28 첫 실행은 모든 원문 검증과492개 후보 metadata 저장 뒤, 과거 ROOT32에서의
`대기열 밖914개`를 현재 ROOT34에도 고정한 마지막 검사에서 실패했다. 후보본문은 쓰지 않았다.
V2는 같은 원문을 모두 다시 검증하고 기존492개 metadata 행이 재생성 결과와 같은지 대조해
기존815202B shard를 읽기 전용으로 재사용했다. 원문·후보·기존 shard/manifest를 덮지 않았다.

실제 현재 값은 ROOT34 HOLD66790고유 중 두 고정 대기열에65911개, 그 밖879개다.
ROOT32의66411/914에서 바뀐 차이는 대기열 안500개와 밖35개의 채택이다.
V2 소스 설명의 `Nine later counter sources`는 계수 전 추측이 잘못 남은 것이며 정정한다.
숫자의 정본은 `RULE28_DECLARED_NAME_LIST_CENSUS_V1.json`의 실제 전량 재계산이다.

V2는 두 index의 모든 SHA 고정 manifest를 순회해 `seen == current_HOLD_hashes & queued_hashes`를
검증했다. 밖879개를 처리했다고 세지 않고 별도 미처리/기검토 상태 연결이 필요하다.
새 규칙 후보407고유545위치는 아직 채택 전이며, 기존478규칙/HOLD나 공식cache15 수치를 바꾸지 않는다.
과거 실행 로그와 물리 shard manifest는 실패 당시 근거로 보존하고, V2의 새 논리 manifest는
최종 census 보고서에서 사용한다. 같은 metadata를 새 데이터 디렉터리에 복제하지 않았다.
