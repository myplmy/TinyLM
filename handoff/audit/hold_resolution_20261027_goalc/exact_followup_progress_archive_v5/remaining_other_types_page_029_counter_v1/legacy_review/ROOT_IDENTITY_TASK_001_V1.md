# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:332189
original SHA-256: 3A5346D95BCDA61F654C7964EE7B0659094B8F17BCA9DCD0AFF4D2A1CC222CD1
candidate SHA-256: 3A5346D95BCDA61F654C7964EE7B0659094B8F17BCA9DCD0AFF4D2A1CC222CD1
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [9, 9]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 9]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_029_counter_v1/reading_packets_v1/expanded_train_332189_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_029_counter_v1/reading_packets_v1/expanded_train_332189_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_029_counter_v1/reading_packets_v1/expanded_train_332189_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_029_counter_v1/reading_packets_v1/expanded_train_332189_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_029_counter_v1/reading_packets_v1/expanded_train_332189_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_029_counter_v1/reading_packets_v1/expanded_train_332189_0009.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:332380
original SHA-256: FC3C28B8804623E7BCEA2EA81948B7A69628DC0F03F100B173D8E928DE9B4862
candidate SHA-256: 3DF39355B8046B63589E62AF45EB6E52CB23E7035DF41150D7580179103D74F5
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:332399
original SHA-256: B66495D21203B25C891DBA8C93531F72F50F994FEBF15569E7326A06B4D19937
candidate SHA-256: B66495D21203B25C891DBA8C93531F72F50F994FEBF15569E7326A06B4D19937
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_029_counter_v1/reading_packets_v1/expanded_train_332399_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_029_counter_v1/reading_packets_v1/expanded_train_332399_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_029_counter_v1/reading_packets_v1/expanded_train_332399_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:332415
original SHA-256: 60278881C9B6BE5C9D16EFC0A69C2A58E5D0E5CC68751413DEDA76A6AC6E8F8C
candidate SHA-256: 60278881C9B6BE5C9D16EFC0A69C2A58E5D0E5CC68751413DEDA76A6AC6E8F8C
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [10, 10]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 10]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8, 9]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_029_counter_v1/reading_packets_v1/expanded_train_332415_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_029_counter_v1/reading_packets_v1/expanded_train_332415_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_029_counter_v1/reading_packets_v1/expanded_train_332415_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_029_counter_v1/reading_packets_v1/expanded_train_332415_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_029_counter_v1/reading_packets_v1/expanded_train_332415_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_029_counter_v1/reading_packets_v1/expanded_train_332415_0010.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:332424
original SHA-256: 54B131EE533B757A376BAA51133684EAA90C01FAF61465A628E7E7485138336A
candidate SHA-256: 54B131EE533B757A376BAA51133684EAA90C01FAF61465A628E7E7485138336A
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_029_counter_v1/reading_packets_v1/expanded_train_332424_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_029_counter_v1/reading_packets_v1/expanded_train_332424_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_029_counter_v1/reading_packets_v1/expanded_train_332424_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_029_counter_v1/reading_packets_v1/expanded_train_332424_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

