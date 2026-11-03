# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:843911
original SHA-256: 85803C59FCE66003444150216E0B0B21F8987395A1CEB8F8C2FC187248014369
candidate SHA-256: 12885EC7FD3F2CBDAC498962D629101A49802B054D83F9849F2EB685EAE4A188
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:843914
original SHA-256: 5C50E1538122E138D5AF947095D3E94B7B40FE50B538561C0C9C9E8D6F5FDE35
candidate SHA-256: DDB1090390221233498A92E6FAFA812CDADBF76E35E27B6179F322869BE74051
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:844268
original SHA-256: 6358E6EE64634ABA3762DDE0B9EF35D09FC77597992D193F23B1589441A2A5CD
candidate SHA-256: 6358E6EE64634ABA3762DDE0B9EF35D09FC77597992D193F23B1589441A2A5CD
원문 frame 패킷: [1, 9]
최종 full_diff 패킷: [17, 17]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 17]
후보 중복만 있는 생략 가능 패킷: [10, 11, 12, 13, 14, 15, 16]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_065_counter_v1/reading_packets_v1/expanded_train_844268_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_065_counter_v1/reading_packets_v1/expanded_train_844268_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_065_counter_v1/reading_packets_v1/expanded_train_844268_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_065_counter_v1/reading_packets_v1/expanded_train_844268_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_065_counter_v1/reading_packets_v1/expanded_train_844268_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_065_counter_v1/reading_packets_v1/expanded_train_844268_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_065_counter_v1/reading_packets_v1/expanded_train_844268_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_065_counter_v1/reading_packets_v1/expanded_train_844268_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_065_counter_v1/reading_packets_v1/expanded_train_844268_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_065_counter_v1/reading_packets_v1/expanded_train_844268_0017.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:844489
original SHA-256: A5E0CD70015CED87573A5D5C6EA28F01F0CBBC4E699C6F5125DD6B567B54341C
candidate SHA-256: A5E0CD70015CED87573A5D5C6EA28F01F0CBBC4E699C6F5125DD6B567B54341C
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_065_counter_v1/reading_packets_v1/expanded_train_844489_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_065_counter_v1/reading_packets_v1/expanded_train_844489_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_065_counter_v1/reading_packets_v1/expanded_train_844489_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:844767
original SHA-256: 7B36EEAEB5E2E3C65521F4CE726E1993BBEE9DFFB6E62E31FB6791350BCF1438
candidate SHA-256: 7B36EEAEB5E2E3C65521F4CE726E1993BBEE9DFFB6E62E31FB6791350BCF1438
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_065_counter_v1/reading_packets_v1/expanded_train_844767_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_065_counter_v1/reading_packets_v1/expanded_train_844767_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_065_counter_v1/reading_packets_v1/expanded_train_844767_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_065_counter_v1/reading_packets_v1/expanded_train_844767_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_065_counter_v1/reading_packets_v1/expanded_train_844767_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_065_counter_v1/reading_packets_v1/expanded_train_844767_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

