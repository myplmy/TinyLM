# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:24250
original SHA-256: E30B4862D9572ED6125BA8D5FBE1E2FD10B3F835414FFA91DD831B5C429436B6
candidate SHA-256: E30B4862D9572ED6125BA8D5FBE1E2FD10B3F835414FFA91DD831B5C429436B6
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_003_counter_v1/reading_packets_v1/expanded_train_24250_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:24330
original SHA-256: 536A238D9BD4A45569745723E5E5FB8D1FEB9C8E4B656F21BA96296EF2382D3E
candidate SHA-256: 536A238D9BD4A45569745723E5E5FB8D1FEB9C8E4B656F21BA96296EF2382D3E
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_003_counter_v1/reading_packets_v1/expanded_train_24330_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_003_counter_v1/reading_packets_v1/expanded_train_24330_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_003_counter_v1/reading_packets_v1/expanded_train_24330_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_003_counter_v1/reading_packets_v1/expanded_train_24330_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:24568
original SHA-256: 97EF3BB8CFBA8646A1660182AA4286E36356D63B59F27680A9A5722B242E27B0
candidate SHA-256: 7A51741DAB397412F493053C50BDC342491EAF7DC2B6A9D18A0256452035811F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:24640
original SHA-256: 2A2EE3771125D1A9E03520170CB3143870142C940C6D93B083FA24A160DB84B0
candidate SHA-256: D7174819FF15470F01DE8409C25596FF4E784DDA2B7BA4A373181372C5799366
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:24679
original SHA-256: 965070EA067C1E9EE4748FFB43C787618ED3D33184CAEE13E11F06FFFBCF4305
candidate SHA-256: 4D71C65C0EDFD18280E15DA21B9D0943DE65C3A84CD9325F524B2826F02D7AE9
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

