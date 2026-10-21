# 2026-10-21 사용자 6항 준비 작업의 허용범위와 영향도

- 원장: `handoff/WIP_20261021_작업원장.md`, session `01a0b33b-d14e-7c40-ada8-229a1f97eabd`.
- 권한: 사용자 현재 지시(1)~(6). 최초 CPU+GPU 특례는 2026-10-21 21:00 KST였으며, 사용자 추가 승인 「23시까지 사용 연장 허가」에 따라 같은 날 23:00 KST(14:00 UTC)로 연장했다. 8시간 장기 생산은 남은 승인 시간을 넘으므로 이번에는 실행하지 않는다.
- 타 원장20260914/16 및 interactive dirty는 현재 작업과 분리한다.

|경로|동작|권한 근거|제외|
|---|---|---|---|
|기존 코드/결과/작은manifest|읽기 감사|1~4|보호 TinyDataset/타 작업 변경|
|scripts/p106b_source_cleanup.py 및 전용test|신설/검증|3의 전처리 수행|기존 prepare/캐시 변경|
|data_cache/p106b_native_cleanup_v1_s1337|새 작은 정리 pilot|3|원문 전체 정리/비오염/품질 PASS 주장|
|HF/sft_ready/p106b_luna_augmentation_v1_s1337|Luna 번역·재표현 초안|4~5|미검수 자동 train 승격|
|review_request/20261021_*|읽기 쉬운 Q-A 검수문서|9|복잡한 JSON만 검수 요청|
|새 생산/실험 controller와 전용tests/SH|8h/증분재개·본실험 준비|5|입력대기/원형덮어쓰기/미구현 성공|
|기존 실험계획·결과·기준표·COMPASS·목록|정확한 신규 절|5~8|과거 음성/PASS 재작성|
|명시 파일 Git index/로컬 commit|한국어 커밋|6|push/PR/무관 dirty 일괄추가|

## 방법 비교

|안|내용|이득|위험/비용|
|---|---|---|---|
|A 채택|원형 보존·명확한 마크업만 정리·불명 구조 보존/후행검수|코드/수식/정상목록 손상 최소화|전량 의미 정제나 품질 보증은 아님|
|B 비채택|모든 angle/wiki/list 패턴을 강제 제거|많은 문자 제거 가능|코드·부정·표·정상목록 손상 위험|
|C 보류|원 URL에서 전체 재수집/재추출|원문 계보·추출 품질 개선 가능|외부 취득/시간/별도 자원 승인 필요|

코드·데이터·테스트·정본 문서에 영향이 있으나제품 기본은 바꾸지 않는다. 자료량·원문토큰·assistant지도·고유root를 구분한다. 새코드의 fixture PASS는 본모델/75M완성의 증거가 아니다. 준비된 실험은구현/preflight가 닫힌 단계만 큐에 등록한다.

## 최종 범위·선별 보관

- 사용자추가지시10은기존반증에이전트를문헌/아이디어역할로재배정해 primary웹조회·TinyLM호환성·세후보를 docs/review/20261021_레이어생략과_초기값대체_문헌검토.md에정리했다. 새가중치개입0.
- 해당시점완료5런처는정확명령·SHA·Git복구점을f5c6d7f와 DONE_LAUNCHER_SOURCE.json에보존한뒤삭제했다. 기존Stage4u1은완료소유근거부족으로보존했다. CP/원로그삭제0.
- evidence는실제영수증·원형보고·source/meta/SHA를담는작은재현근거다. 전량원자료·체크포인트·캐시를Git에저장하지않는다. 중간중복snapshot4묶음은로컬보존/정확ignore하고최종18개metadata만선별staging했다. 원형CRLF인한파일은정확바이트속성으로SHA를보존했다.
- frontier의중간template와실패정적감사도프로세스이력으로별도보존한다. 최종판정은이번handoff에명시한정확marker와 FINAL_STATIC_AUDIT만사용하며중간REVIEW_REQUIRED를최종결론으로읽지않는다.
- 최종정적68PASS/6NOT_RUN/오류0·raw49closure0·C2/C3/독립인계검사0 뒤WIP를도구로-done마감했다. 23시뒤새실행승인은없다.
