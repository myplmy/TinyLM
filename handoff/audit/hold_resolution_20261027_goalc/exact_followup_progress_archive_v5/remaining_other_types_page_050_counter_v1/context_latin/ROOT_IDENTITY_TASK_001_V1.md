# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:636417
original SHA-256: 06A5AD239FA618DC6E851A7889E49DBD43B546E56821D2A2802042FEDF7243DA
candidate SHA-256: 06A5AD239FA618DC6E851A7889E49DBD43B546E56821D2A2802042FEDF7243DA
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636417_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:636689
original SHA-256: 80C6611BF4255D242B47B1FD7A6D71982E87B13652E1EAA42C473B1F51C46753
candidate SHA-256: 80C6611BF4255D242B47B1FD7A6D71982E87B13652E1EAA42C473B1F51C46753
원문 frame 패킷: [1, 8]
최종 full_diff 패킷: [16, 16]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 16]
후보 중복만 있는 생략 가능 패킷: [9, 10, 11, 12, 13, 14, 15]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636689_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636689_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636689_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636689_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636689_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636689_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636689_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636689_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636689_0016.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:636822
original SHA-256: 7F3D4F3F2C4ABDDBB693FC66A7D8ADD5F7A2948F3F3B53EED365BE86168F27BF
candidate SHA-256: 5CEAEFD8D31799B2114E13423EFB057A0D37B77C9F4079C005DF3185D989F175
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:636959
original SHA-256: 6029E52EA752FB8C08721DE94839D95E09E9FA6E04EAB8F66FA5E78A5330008A
candidate SHA-256: 6029E52EA752FB8C08721DE94839D95E09E9FA6E04EAB8F66FA5E78A5330008A
원문 frame 패킷: [1, 13]
최종 full_diff 패킷: [25, 25]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 25]
후보 중복만 있는 생략 가능 패킷: [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636959_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636959_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636959_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636959_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636959_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636959_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636959_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636959_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636959_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636959_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636959_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636959_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636959_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636959_0025.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:637228
original SHA-256: 708730E6FFA2903D811E686F68A5655FEDF0045CD8F4FA6DA542808ACD5791BD
candidate SHA-256: 708730E6FFA2903D811E686F68A5655FEDF0045CD8F4FA6DA542808ACD5791BD
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_637228_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

