# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:350450
original SHA-256: 9540AC61A00ED819BF525C13075A14EDFD7E478612B4B5A297A276307A82131D
candidate SHA-256: 9E3808F71D55D1C227B210051287136C1E8250B117C6BA6891F5A4100D985DFE
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:352023
original SHA-256: AEAC0A0292E288BCA7BB4C9760008209E4D580D4A0D35F776F11628C3BDA6D4A
candidate SHA-256: 8DEC42635DCA9860CAD993870A1630D986682C99E95257BAEE29D3BE5748DBF1
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:352034
original SHA-256: 75F00A3D4FE20C9FC1CAFDCD96107A510E2AD5F736A539D3C7C15FE98B1D284C
candidate SHA-256: 2726FCA4D23554432B748306B5D83AED97E8360700FCD7E8CA4C283DDB8EFC3C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:352244
original SHA-256: F81D5B423E6E54872B9A16C2E97FD4CDE2218753160391BFF262377CA771390D
candidate SHA-256: 580792213DC75FFFF2062240C32D0A8EF7FF550827DDB5CA06994F45293C8383
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:353018
original SHA-256: C70D85CEE35358331FFF97E59B382207C881EEF37F13DE47C1B97CDDF26AFB85
candidate SHA-256: 76F8B1E7745E6B8C900DD55C5E69B755D1254CD575CDBB8A08688FE446F5EFCA
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

