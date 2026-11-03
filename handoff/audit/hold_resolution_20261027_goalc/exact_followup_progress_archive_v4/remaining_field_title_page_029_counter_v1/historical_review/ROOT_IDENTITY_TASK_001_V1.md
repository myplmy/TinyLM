# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1000444
original SHA-256: 25B65553E631EE529FE1AC836198992C6BE5A83C515212F7E7F0010FFC011927
candidate SHA-256: 25B65553E631EE529FE1AC836198992C6BE5A83C515212F7E7F0010FFC011927
원문 frame 패킷: [1, 12]
최종 full_diff 패킷: [23, 23]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 23]
후보 중복만 있는 생략 가능 패킷: [13, 14, 15, 16, 17, 18, 19, 20, 21, 22]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_029_counter_v1/reading_packets_v1/expanded_train_1000444_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_029_counter_v1/reading_packets_v1/expanded_train_1000444_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_029_counter_v1/reading_packets_v1/expanded_train_1000444_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_029_counter_v1/reading_packets_v1/expanded_train_1000444_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_029_counter_v1/reading_packets_v1/expanded_train_1000444_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_029_counter_v1/reading_packets_v1/expanded_train_1000444_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_029_counter_v1/reading_packets_v1/expanded_train_1000444_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_029_counter_v1/reading_packets_v1/expanded_train_1000444_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_029_counter_v1/reading_packets_v1/expanded_train_1000444_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_029_counter_v1/reading_packets_v1/expanded_train_1000444_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_029_counter_v1/reading_packets_v1/expanded_train_1000444_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_029_counter_v1/reading_packets_v1/expanded_train_1000444_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_029_counter_v1/reading_packets_v1/expanded_train_1000444_0023.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1005185
original SHA-256: 2B93C4A8AD0DB2E15C970D5B534A3193DE6B11280625FDD0BF8438A33A0328D8
candidate SHA-256: 2B93C4A8AD0DB2E15C970D5B534A3193DE6B11280625FDD0BF8438A33A0328D8
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 4, 5]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_029_counter_v1/reading_packets_v1/expanded_train_1005185_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_029_counter_v1/reading_packets_v1/expanded_train_1005185_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_029_counter_v1/reading_packets_v1/expanded_train_1005185_0004.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_029_counter_v1/reading_packets_v1/expanded_train_1005185_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1005749
original SHA-256: A8C308E7334432A5143D8A5CCE8337108869586F528D5A39533F3DAF76494957
candidate SHA-256: 657AFFABE99051598461EAD4BF0D5467EA0A4F28D7ADCCAEACD454CDDE04B1F9
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1006081
original SHA-256: 2560A47EAA6A18CF2B374164FF29922DE31BD655058373ACA5083D6DD4B9F490
candidate SHA-256: 889BE4474DE41D71BA06E7F734DBC0145A126EFB9FF2643E0228353BCC52EC33
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1006526
original SHA-256: 36AC19D57613915D817B4C6E05D7FA4C66180B0CFDC53731538D8204139D5D60
candidate SHA-256: F87D373786CB4A7DCC7B3C175C4DA90FB861D3950F1DE2F1541E686D1E268AD1
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

