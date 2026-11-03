# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:344681
original SHA-256: E384E90C77C460B386ECDCD85354D07073BFD93F109A9AB047F6790C296AC2C6
candidate SHA-256: 84C4FCB829F5E94DF8F2FD46EED4A3A60D0F743C8285D7EDA45938FB6C45808D
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:344739
original SHA-256: F8A48EB6DA89D88337C33F37B3E937C7D3B62EEBA02242C9705CDE7A2CFD6113
candidate SHA-256: C36A2FB3AC685B295C903CA5C42B3FF23973711CE5833A466016B47EDB71C908
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:344826
original SHA-256: 47FC3E84784E11F4CFC97F1B0BBF27A73FDE832C5BCCBED4222E97D70827AF52
candidate SHA-256: 47FC3E84784E11F4CFC97F1B0BBF27A73FDE832C5BCCBED4222E97D70827AF52
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_030_counter_v1/reading_packets_v1/expanded_train_344826_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_030_counter_v1/reading_packets_v1/expanded_train_344826_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_030_counter_v1/reading_packets_v1/expanded_train_344826_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:344848
original SHA-256: 6D47A5A333A805E3941F6FF22DB62451407BD5D53C226591576247B99F6400FB
candidate SHA-256: 4E89AEE16EA13ED7633388D4C580EE6B2286B5B8C183590D126A3B4C4B1D1C67
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:344921
original SHA-256: 7C1EA42DAB78283E399C474DA47944743F819062F08F9F43EC9D86E5CA9AD090
candidate SHA-256: 7C1EA42DAB78283E399C474DA47944743F819062F08F9F43EC9D86E5CA9AD090
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_030_counter_v1/reading_packets_v1/expanded_train_344921_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_030_counter_v1/reading_packets_v1/expanded_train_344921_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_030_counter_v1/reading_packets_v1/expanded_train_344921_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

