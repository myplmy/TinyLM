# TASK256 도구 호출 오류 기록

첫 다중 파일 저장 시도는 functions.exec의 JavaScript 파서에서 실패했다: SyntaxError: Unexpected identifier '조안'. 이 시도는 exec_command를 호출하기 전에 종료되어 셸 명령은 실행되지 않았고 파일도 변경하지 않았다. 원인은 JS 템플릿 문자열 안에 Markdown 인라인 코드용 백틱을 그대로 넣은 작성 오류였다. 백틱을 제거한 다음 저장 호출은 성공했다. 이 실패 시도는 파일 판독이나 편집으로 세지 않는다.

두 번째 저장 시도도 같은 JS 템플릿 문자열을 사용해 파서 단계에서 실패했다: SyntaxError: Unexpected identifier 'functions'. exec_command는 호출되지 않았고 파일은 변경되지 않았다. 원인은 오류 메모 본문에 백틱을 그대로 넣은 것이었다. 이후 백틱 없는 세 번째 호출에서 새 v2 TXT와 이 노트를 저장했다.
