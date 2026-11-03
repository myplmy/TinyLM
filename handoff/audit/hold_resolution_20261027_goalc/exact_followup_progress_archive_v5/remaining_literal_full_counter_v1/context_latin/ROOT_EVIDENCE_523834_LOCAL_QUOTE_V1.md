# 523834 단일 호출과 평탄화된 예제의 구분

총괄이 실제 원문14–32줄을 읽고 실제 문자열을 확인했다. subprocess.call의 단일 예제에는 닫는 double quote가 있지만 그것을 감싸는 Python single quote의 마지막 하나가 없다. 바로 뒤 원 저자의 설명은 마지막 인수가 double quote로 감싼 문자열이고 다시 single quote로 감싼다고 명시하며, 실제 shell 표기도 같은 Hello World 문자열을 제시한다.

따라서 기존 마지막 double quote와 닫는 대괄호 사이에 single quote 한 개만 복원할 유일한 국소 근거가 있다. 이 조정 전에는 정적 parser가 거부하고 이후에는 실제 인수 두 값 espeak 및 double quote 양끝을 가진 Hello World!가 그대로인 호출로 해석됨을 총괄이 확인했다. 실행/음성출력/네트워크 호출은0이다. 실제 import와 call의 두 REPL prompt 사이 개행만 구분할 수 있다.

이 한 호출과 원래 명시 설명은 보존할 수 있다. 세 전체 bot 프로그램의 소실된 Python 블록/주석/시간필터 구조에 이 복원을 확대하지 않는다. GetFriends 부분은 실제 userlist 대입 호출과 User 속성 설명을 보존한다. 뒤 for/print와 여러 사용자 출력이 한 줄로 묶여 경계를 확정 못하면 그 출력 단위/직접 관찰만 원형 분리하고, 단순히 API 정의가 없다는 이유로 완결 호출까지 버리지 않는다. 사용자 이름을 추정해 새 record 행을 만들지 않는다.

기존 누락 표기와 대형 손상 코드/직접 결과는 sidecar에 보존하고 자기 TASK045의 다섯 행을 유지한 새 리뷰로 연결한다. 새 본문/전체diff를 확인한다. 자체 코드/시험/해시/웹/실행 권한은 추가되지 않는다.
