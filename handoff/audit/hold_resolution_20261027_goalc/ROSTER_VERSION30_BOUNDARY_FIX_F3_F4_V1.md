# 버전30이310으로 바뀌는 기존 생성기 경계 수정

ROOT44/roster31의 최초 builder는 새 캐시/원장 생성 전에 nonexistent roster310을 읽으려다 실패했다.
기존 생성기가 prefix+'3'을 경계 없이 치환해 이미 넣은 prior roster30도 310으로 바꾼 것이 원인이다.
실패 로그와 기존 코드·원형·후보·캐시는 그대로 보존한다.

대안 A는 동결된 old1~4와 hash계약을 모두 바꾸는 것이다. B는 정확 검증된 기존 생성기의 단 한 치환문에
버전 뒤 숫자 경계를 추가하고 기존 join/guard/전량 verifier를 재사용하는 것이다. C는 잘못된310 alias나 사본을 만들어
통과시키는 것으로 거짓 계보와 큰 사본을 만든다. B를 적용한다.

v5는 기존v4 registry SHA와v1 원문SHA를 먼저 실제 검증한다. process-local compile에서 검증된 v1 prefix의
정확 한 치환문만 '(?![0-9])' 경계로 바꾸고 변환은1회인지 확인한다. hash를 속이거나 old파일/registry를 수정하지 않는다.
생성된 prefix SHA와 v5/동결코드/계약/config/시험 SHA를 새 binding에 남겨 실제 producer를 추적한다.
기존13제한ID/25hash/21alias와3승인안전파생본문 경계는 그대로다.
30→31/31→32/300 보존/29→30/단자리/anchor drift의5회귀와 독립297539행 비교를 수행한다.
이 수정은 버전 경계뿐이며 새 source/body 승인, numeric/code waiver, GPU·모델·학습·Git 외부상태 변경이 아니다.
