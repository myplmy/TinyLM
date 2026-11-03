# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1255495
original SHA-256: F383E8CC9F0B77B48083C3E872A46129E4B0E1CC156909463A3109FBAD076587
candidate SHA-256: 64713EE484562D23E7835374551122F1D62FE34C4A8959E32F9FA71418AE7BBD
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1255510
original SHA-256: CE5CF765897F1AD54589CCA3D10565C39B41A1C5F292127599419D1A230C75E0
candidate SHA-256: 994F3094FB41F0AF96E2873CB2782CA349371A209B2642937F4CF1CC62FA0AC5
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1255542
original SHA-256: ED429FF35E93FD5D7CBE37CE936063940CA1FEF81CDCCC15579FB593B4C6002D
candidate SHA-256: B9FA8BEC271D3AA72C321B59E0083965CC4DC51D55FCB12BF512D807C9B28D4B
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1255600
original SHA-256: E2895DA185EE5B28931ABF918CBC5FF0CB5A5AF53792DD4B99EB23141F617978
candidate SHA-256: E51031ED8257BFF57D91C55D32F0CFB9A176AC8FC9965F31194291B0AB257659
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1255622
original SHA-256: 39188B34FD98BF73F34FE4F20D50E32BF498816FE80C52415618BA53D04AE619
candidate SHA-256: 9534CB5EE504A4594C08470476DE3903DAE03C0C721576C62A9587E874B18344
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

