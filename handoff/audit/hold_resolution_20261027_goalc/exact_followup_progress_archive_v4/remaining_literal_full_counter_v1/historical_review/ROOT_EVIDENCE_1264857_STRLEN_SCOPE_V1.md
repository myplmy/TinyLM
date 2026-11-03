# 1264857: strlen 귀속 한 문장

총괄은 PHP 공식 매뉴얼의 Description/Return Values를 실제 확인했다. 이 문서는 strlen의 반환값을 문자열의 바이트 길이라고 정의하며 문자열을 지정 길이로 자르는 기능이라고 하지 않는다. 사용자 노트·다른 함수의 예제는 이번 판정에 쓰지 않는다.
- https://www.php.net/manual/en/function.strlen.php

원문의 말미 `PHP uses strlen() to truncate a string to a set limit of characters.`라는 직접 기능 귀속 한 문장만 원형 HOLD한다. 이를 substr/mb_substr 등 다른 함수명으로 추정 치환하거나 새 예제를 만들지 않는다. 앞의 독립적으로 완결된 원문 설명·실제 코드·조건은 유지한다. 원문의 출처 라벨을 PHP 공식문서로 변경하거나 원문 전체 기술 검증으로 확대하지 않는다.

Luna가 새 전체 TXT·원형 sidecar·TASK013 전체5행 새 리뷰로 연결한다. 원형·이전 리뷰를 덮지 않는다. 실제 API 실행/모델/학습은 하지 않았다.
