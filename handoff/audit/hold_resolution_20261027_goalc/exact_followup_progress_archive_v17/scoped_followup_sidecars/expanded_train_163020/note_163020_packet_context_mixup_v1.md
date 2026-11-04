# expanded_train:163020 — 판독 보고 혼동 정정

2026-11-04에 보낸 163020 패킷 불일치 보고는 잘못이었다. 같은 page009에서 앞서 판독한 161287 포여 열거 정리의 `구슬` 문맥을 163020에 혼동해 잘못 귀속했다. 163020은 《80일간의 세계 일주》 원문이며, 총괄이 확인한 바에 따르면 `구슬`은 이 ID에 없다.

총괄의 실제 대조 결과 original/candidate는 동일한 7,777자 본문이다. 이 ID의 original frame은 packet 0001–0004, candidate frame은 0004–0008, final full_diff는 packet 0008에 있다. 기존 identity 계획대로 original 0001–0004와 final diff 0008을 읽고 candidate-only packets 0005–0007은 생략했다. 지정 input/identity 문서를 수정하지 않았다.

앞선 불일치 보고는 철회한다. `expanded_train_163020_task009_v1.txt`와 `hold_163020_task009_v1.md`는 원문·후보를 바꾸지 않은 자기 작업 출력이며, 이 정정 시점에는 아직 리뷰와 연결하지 않은 상태다.
