# TASK262 도구 호출 오류 기록

첫 파일 저장을 위한 functions.exec 스크립트가 JavaScript 파서에서 실패했다: SyntaxError: Unexpected identifier '남자'. exec_command 이전 단계에서 종료되어 셸 명령은 실행되지 않았고 파일은 변경되지 않았다. JS 템플릿 문자열의 본문에 Markdown 인라인 코드 백틱을 그대로 넣은 작성 오류였다. 백틱 없는 재시도는 성공해 sidecar와 review_262.md를 저장했다. 실패 호출은 판독·편집으로 세지 않는다.
