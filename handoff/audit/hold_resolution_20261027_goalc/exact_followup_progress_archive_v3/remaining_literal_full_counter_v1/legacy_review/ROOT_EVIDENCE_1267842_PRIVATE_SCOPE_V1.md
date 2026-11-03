# 1267842: private 오버라이드 주장 범위

총괄이 Oracle의 Java SE8 언어명세8.4.8.3을 실제 확인했다. 2058행의 설명은 private 메서드가 기술적 의미에서 숨김/오버라이드 대상이 아니며 같은서명 메서드 선언과 구별됨을 명시한다. 같은명세100행 및8.4.3.3은 final 메서드의 오버라이드/숨김 불가를 명시한다. 이 출처는 한 명세 계보이며 독립된 두 실험/사실검증으로 세지 않는다.
- https://docs.oracle.com/javase/specs/jls/se8/html/jls-8.html#jls-8.4.8.3
- https://docs.oracle.com/javase/specs/jls/se8/html/jls-8.html#jls-8.4.3.3

기존 목록의 final 메서드 주장은 유지한다. `A subclass can override private methods as well as public or protected ones.`의 private까지 포함한 직접 일반화 문장만 원형 HOLD한다. public/protected의 다른 완결 설명은 유지하되 이 문장에서 private를 지우고 새 보편명제를 만들거나 can을cannot으로 치환하지 않는다. 동일서명 선언을 오버라이드로 새로 해설하지 않는다.

Luna가 새 전체 TXT·원형 sidecar·TASK017 전체5행 새 리뷰를 작성한다. 원문과 이전 결과는 보존한다. Java 컴파일/실행·전체 문서 사실검증·모델학습의 증거가 아니다.
