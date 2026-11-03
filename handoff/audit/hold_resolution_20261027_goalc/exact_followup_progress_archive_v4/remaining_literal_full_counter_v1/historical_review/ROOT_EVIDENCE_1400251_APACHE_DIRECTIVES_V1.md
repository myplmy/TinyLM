# 1400251의 네 directive 개행 경계

총괄이 지정 original 전문과 실제 한 줄의 네 directive·인수를 읽었다. 또한 Apache2.4 공식 [설정 문법](https://httpd.apache.org/docs/2.4/configuring.html)과 [인증 핵심 directive 문서](https://httpd.apache.org/docs/2.4/mod/mod_authn_core.html)의 문법/예시를 실제 확인했다. 이것은 원 발행판 전체의 현재성 검증이나 서버 실행이 아니다.

한 줄에는 순서대로 AuthName, AuthUserFile, AuthType, require가 있고 각 값도 채워져 있다. AuthName의 따옴표 인수는 공백을 포함한 하나의 인수이며, 다른 세 값도 실제 그대로 있다. 공식 문법은 한 줄에 한 directive이며, 현재 네 directive와 인수의 대응은 소실 표적 추정 없이 구분된다.

따라서 이 정확 ID의 정확 해당 한 줄만 AuthUserFile/AuthType/require 직전에 개행을 넣어 네 줄로 복원할 수 있다. 이름·대소문자·따옴표·문자열·경로·인수·순서는 모두 원문 그대로 보존한다. 다른 명령/주석/조건부 코드의 개행을 일반 허용하는 근거가 아니다. 새 directive나 보안 설정은 추가하지 않는다.

AuthUserFile 경로 설명과 AuthName 프롬프트 설명은 원문 맥락대로 보존한다. 오래된 암호 방식·브라우저 동작을 현대 문서에 맞춰 조용히 바꾸지 않는다. 서버/htpasswd/PHP 실행·설치·배포는 하지 않는다. 새 전체 TXT/원형 sidecar/새5행 리뷰와 full diff를 저장하고, 총괄이 해당 줄 외 비공백 동일성과 네 행의 값 대응을 후속 확인한다.
