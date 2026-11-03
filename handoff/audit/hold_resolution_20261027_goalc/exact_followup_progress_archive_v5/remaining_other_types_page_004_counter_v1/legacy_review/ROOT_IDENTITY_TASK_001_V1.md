# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:39362
original SHA-256: 77E35EFD5F8117C553D1A356A2A0735648FFE8B8230990D80A31F61AB0306FE7
candidate SHA-256: 77E35EFD5F8117C553D1A356A2A0735648FFE8B8230990D80A31F61AB0306FE7
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39362_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:39574
original SHA-256: B62BC8C6316EEF07EC712178C82B30874023574397B232554B0D2A45BBFD6A5D
candidate SHA-256: B62BC8C6316EEF07EC712178C82B30874023574397B232554B0D2A45BBFD6A5D
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39574_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39574_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39574_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:39632
original SHA-256: A5FDCCB77498CC34BCB845D144389A2162E92E274FAD02DFECF15DE17F5DDC0A
candidate SHA-256: A5FDCCB77498CC34BCB845D144389A2162E92E274FAD02DFECF15DE17F5DDC0A
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39632_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39632_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:39634
original SHA-256: 6CAF6C823D13E7A4F066B5625392D668196579E7BADDEDE8BE4B8A138A457601
candidate SHA-256: 6CAF6C823D13E7A4F066B5625392D668196579E7BADDEDE8BE4B8A138A457601
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39634_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39634_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39634_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39634_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39634_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:39781
original SHA-256: 82B8BC5B90C4F0B03125F08879D626BF1791930561735AD6C68842D556788FA9
candidate SHA-256: 82B8BC5B90C4F0B03125F08879D626BF1791930561735AD6C68842D556788FA9
원문 frame 패킷: [1, 11]
최종 full_diff 패킷: [22, 22]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 22]
후보 중복만 있는 생략 가능 패킷: [12, 13, 14, 15, 16, 17, 18, 19, 20, 21]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39781_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39781_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39781_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39781_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39781_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39781_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39781_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39781_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39781_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39781_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39781_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_004_counter_v1/reading_packets_v1/expanded_train_39781_0022.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

