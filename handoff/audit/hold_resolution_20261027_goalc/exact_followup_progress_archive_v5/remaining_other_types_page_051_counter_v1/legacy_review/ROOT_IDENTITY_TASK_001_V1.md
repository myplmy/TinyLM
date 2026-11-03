# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:651379
original SHA-256: D658A36EC3DD63D1D3A1179E3DEDD4DDCA9F484845E055A0FF0A1E95591CAB9E
candidate SHA-256: 77F9BF14AEE8D6A4CB822986D9144F8284EDC6861074C7C4DF338F59F0AAA394
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:651592
original SHA-256: 3CE7B96FF81BB1B58C04308823E095C19D3C4C012A63D00F3006A523961BF0E3
candidate SHA-256: 3CE7B96FF81BB1B58C04308823E095C19D3C4C012A63D00F3006A523961BF0E3
원문 frame 패킷: [1, 13]
최종 full_diff 패킷: [26, 27]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 26, 27]
후보 중복만 있는 생략 가능 패킷: [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651592_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651592_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651592_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651592_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651592_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651592_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651592_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651592_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651592_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651592_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651592_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651592_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651592_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651592_0026.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651592_0027.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:651624
original SHA-256: E3CDFE3A5E7FCF9140B991516397AD6303317735DC27E264C51445A653F08071
candidate SHA-256: 1A8D6DBE9AF553B3346B10B9EE2ADB208B06B9A96CD9381679C61C8B64FCEAA5
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:651731
original SHA-256: BA76F57FAF835E1B646A82E336507DF620EF09E71BAA6F3506A740CC8CBDD87E
candidate SHA-256: BA76F57FAF835E1B646A82E336507DF620EF09E71BAA6F3506A740CC8CBDD87E
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651731_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651731_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651731_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651731_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:651732
original SHA-256: F9CC0F8F4D8C4B2CF8F1CC040A81868539FCD3F6774FAF85439C86A34C2F07F8
candidate SHA-256: F9CC0F8F4D8C4B2CF8F1CC040A81868539FCD3F6774FAF85439C86A34C2F07F8
원문 frame 패킷: [1, 12]
최종 full_diff 패킷: [24, 24]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 24]
후보 중복만 있는 생략 가능 패킷: [13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651732_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651732_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651732_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651732_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651732_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651732_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651732_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651732_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651732_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651732_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651732_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651732_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651732_0024.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

