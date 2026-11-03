# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:10016
original SHA-256: 98B627C249AEFCF021B8A322BF143CF042290B6E209774411D61D1B665F7D765
candidate SHA-256: 9A9B70F6A623BF1C3D94CAFA8945B9A18C907775265BFAF534ECE33E406DE7E3
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:10170
original SHA-256: BF04B74B79DECE390BA6E9D7111D43A2B1054F9F0F850BDB6172580D9388305C
candidate SHA-256: 04517CC126E93F6B072A4004C78A1D37FC70D150D5EB8954BFFAAE08059C70A4
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:144
original SHA-256: A4C72992BC262306DA8DB0799BB0B253BF786583877D2ADDD4DB2C1F4B521C1D
candidate SHA-256: 6DE48DB8F365F1910CACAA818B49782320B6840B8C49F03F7925AF00E0953C02
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1673
original SHA-256: 71D872879469324C7C85DFE48151C8AD8478AA80B0D21328C33E98E13623D017
candidate SHA-256: 5E89E6975F414D3104DC1ABF3F0222F87735C7A20186C6A1AFDAF8DB29034478
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1676
original SHA-256: 5AFE427D95E2E53B0F576C84F9802718F46E793A046180AD7FE723BF7AB24F4B
candidate SHA-256: CF6D59476E5DE1CCE04ECAF8E67099180C7F7900B9978FA9B2EF166AAE82AB8F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

