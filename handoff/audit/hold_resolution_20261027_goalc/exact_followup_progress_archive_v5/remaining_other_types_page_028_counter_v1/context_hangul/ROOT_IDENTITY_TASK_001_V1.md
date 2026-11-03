# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:320267
original SHA-256: 7F7B57A871966223CB1EE8B4B81E6E2331AA5E2C611C58C380BAD3827A7AF2FD
candidate SHA-256: 610B7FA9B0CEF46C378AE62EA919D28A60DEB5BDD1C9CAFC4CAD71FAF1C62DB2
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:320378
original SHA-256: F3A29550A444D5C23A4BC73CEB95F26EF667D142EE47CC819DED12D3F1F5065C
candidate SHA-256: 9D6CE029360F1D2E50F28AF5DE14A236CAFCD76C18B9DB6020D15F69F27F2081
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:320401
original SHA-256: 0C9D76AD0B9C5852E9CC8BCD23BD28D4382E0496147A452F686C39902253CF0B
candidate SHA-256: 5CC6D771658C75852C99DB7BD8E02C1F651ACFE7506C78002EC3A67EAFF3DD55
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:320474
original SHA-256: 752A78712107BAB51093B4928625091ECD8EF25EAA5BDACBC8DD6F7F91B39C87
candidate SHA-256: 1B8A03B6A932B90A09840E6D7CB3BDFCC777E66DA8ED05778CB6210FBB71FBA8
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:320492
original SHA-256: 4798A66DA6F5A877F39D0E68DD4DABEDF081F9EBBF5B41125B327FB373FF4629
candidate SHA-256: 1C9952818AE16FDB405866DFD3F3B32976F7F94E90FFA59A7FCADF86D79262F2
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

