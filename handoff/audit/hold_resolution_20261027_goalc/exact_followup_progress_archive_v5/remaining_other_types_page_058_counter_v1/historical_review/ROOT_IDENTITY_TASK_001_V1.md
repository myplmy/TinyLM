# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:747808
original SHA-256: A8E503BD53A176EB8CA489587F560FCC3B4F7DCBA8C769A0FB8A3799491F1D7D
candidate SHA-256: A8E503BD53A176EB8CA489587F560FCC3B4F7DCBA8C769A0FB8A3799491F1D7D
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_747808_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_747808_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_747808_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:748611
original SHA-256: E2643014EEE58156186448AA89F02240BB3883E9B87778DF3BE2C6EE6EE0C89A
candidate SHA-256: E2643014EEE58156186448AA89F02240BB3883E9B87778DF3BE2C6EE6EE0C89A
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 9]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8, 9]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_748611_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_748611_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_748611_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_748611_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_748611_0008.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_748611_0009.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:748766
original SHA-256: D099D24CD8BDFD8BCE7193D501ACE1D8EFE5DC0AD4993EFFD7B70A76E3E28F98
candidate SHA-256: D099D24CD8BDFD8BCE7193D501ACE1D8EFE5DC0AD4993EFFD7B70A76E3E28F98
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [11, 11]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 11]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_748766_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_748766_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_748766_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_748766_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_748766_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_748766_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_748766_0011.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:748971
original SHA-256: F379EEA1E2289B8CEFBEE06EAFD30DB40187F4EEBF1D9ECECA58A84D3D47500E
candidate SHA-256: F379EEA1E2289B8CEFBEE06EAFD30DB40187F4EEBF1D9ECECA58A84D3D47500E
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_748971_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_748971_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_748971_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_748971_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_748971_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:749004
original SHA-256: E46F393182E3BCAC3B930C7BA2454A9FD257647ADFDC0F68CB3168191AF76039
candidate SHA-256: E46F393182E3BCAC3B930C7BA2454A9FD257647ADFDC0F68CB3168191AF76039
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_749004_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_749004_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_749004_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_749004_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

