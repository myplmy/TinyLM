# 완료 저자 결과의 변경분만 다시 프로파일링

현재 승인된 목표의 CPU 분석·관련 코드와 시험 범위다. 기존 profile1과 그 전량 source/body 검사를 재사용한다.
선택 A는 갱신 때마다 미채택 4천여 개 원형·최종을 전량 재계산하고 같은 metadata를 다시 저장하는 것이다.
선택 B는 원형 SHA별로 최종 SHA와 모든 리뷰의 경로·SHA 집합이 같은 이전 프로파일 행만 재사용하고 새/변경 행만 계산한다.
선택 C는 파일명·mtime이나 완료개수만으로 생략하는 것으로 새 수정본문·비판 리뷰를 놓칠 수 있다.
B를 적용한다. 최초 V2 프로파일은 실제 61.54초/metadata15,856,662B였으며, 새 실행 비용은 실제 종료 후 별도 기록한다.

이전 프로파일 producer SHA와 report/shard SHA를 검증한다. 새 동결 snapshot·보호/NEEDS_ROOT·원형SHA·저자 primary/리뷰 합의·전문EOF 검사는
기존 순서대로 거친 다음 동일 signature만 payload 열기 전에 생략한다. 새/수정본문, 같은 경로에서 내용이 바뀐 리뷰,
새 counter review, 리뷰 경로/개수 변경은 모두 재계산한다. 집합의 순서만 바뀐 것은 같은 증거다.
이전 행을 새 metadata에 복제하지 않으며 이전 report/shard로 계보를 연결한다. 생략 행은 새 처리량·새 최초판독이 아니다.
이것은 프로파일 진단만의 재사용이다. 실제 ROOT 채택과 cache build/consumer의 정확 원형·최종 SHA 검사를 생략하지 않는다.

영향은 audit profiler/config/report와 새 작은 metadata에 한정된다. 원형·후보·정제 TXT·토큰·기존 스냅샷은 불변이며
selection/roster/cache·모델·GPU·학습·분할·타세션·Git 외부 상태를 이 도구가 변경하지 않는다.
5개 cache invalidation 회귀로 변경 본문/새 리뷰/같은 리뷰 경로의 내용 변경/새 리뷰 경로의 무효화를 검사한다.
후속 readiness는 새 행에 기존 전량 literal/numeric/code/Unicode/style/order/delimiter·메모 gate를 다시 적용한다.
