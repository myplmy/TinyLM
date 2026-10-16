# 실패 CPU 시도의 해시 일치 재구성 소스

이 두 `.py.txt`는 실행 전 관측 스냅샷이 아니다. v2에서 기록된 수리 패치를 역적용하고 실제 v1의896행 manifest에 남은 원SHA와 일치함을 검산한 재구성본이다.
원로그 `101_log_20261017_P106B_Stage4dw0W_night_falcon_cpu_020312.txt`와 근거 `test_result/evidence/p106b_night_falcon_v1_source_reconstruction.json`을 함께 읽는다.

원래 QA/생성답·가중치가 아니라 프로젝트 자체의 작은 재현 소스이므로, 실제 원형의 Git제외 local 디렉터리 대신 여기에서 추적한다.
활성 스크립트가 아니며 복원하려면 원래 `scripts/` 위치·별도 출력 namespace와 자산을 맞춰야 한다. 옛 부분 HF를 덮어쓰거나 기존 명령을 무단 재실행하지 않는다.

v1은 CPU가중치 로딩 후 빈set 진단값 JSON직렬화에서 실패했으며 모델 forward/GPU/optimizer/update/체크포인트 저장은0이다. 이를 성공한 모델 실행의 근거로 쓰지 않는다.
