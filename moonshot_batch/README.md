# Moonshot 사용자 실행 배치

이 폴더의 `.bat`만 PM 실험을 실행한다. 일반 루트 큐에는 넣지 않는다.

실행 순서와 중단 조건은
[`PM000__MOONSHOT__LATIN_GQA__PLAN.md`](../plan/PM000__MOONSHOT__LATIN_GQA__PLAN.md)를 따른다.
모든 배치는 먼저 현재 브랜치와 namespace를 정적으로 확인하고, 로그를
`moonshot_result/`로만 보낸다.

AI는 이 폴더의 `.bat`를 실행하지 않는다.

현재 재검증 순서:

1. 사용자가 저장소 루트의 `run_smoke_check.bat` 실행
2. 사용자가 `run_PM000__MOONSHOT__Stage0B_postrefactor.bat` 실행
3. 두 결과 분석과 전체-smoke 예외 방침이 기록되기 전에는 Stage1을 실행하지 않음
