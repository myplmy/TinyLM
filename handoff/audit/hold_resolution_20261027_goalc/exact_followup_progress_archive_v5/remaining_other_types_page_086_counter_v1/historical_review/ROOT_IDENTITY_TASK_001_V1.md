# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1201807
original SHA-256: 1E9A3E96B5D9F3DBD831BB8A0BB706A52BB9BDD87BA5C933340957A5A8839924
candidate SHA-256: 1BAEC394B34DEDD7ECEC92EED3A995331FC48477BC71F42A14418B1D6DD5F722
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1201879
original SHA-256: 282C743903E890344D9FC9AF20DB513778E472DE5498F383BBA95FEDE33CE363
candidate SHA-256: 282C743903E890344D9FC9AF20DB513778E472DE5498F383BBA95FEDE33CE363
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1201879_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1201879_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1202023
original SHA-256: 12FB2E61E0EB81B492566B76BFDFC36BD6A4885AFE75D45AA556D3CB26152306
candidate SHA-256: 12FB2E61E0EB81B492566B76BFDFC36BD6A4885AFE75D45AA556D3CB26152306
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202023_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1202563
original SHA-256: 41F3A18653478F4D9CBC2809086C6638B219E157BDEC1C4F99B5A83DA6B8F015
candidate SHA-256: 41F3A18653478F4D9CBC2809086C6638B219E157BDEC1C4F99B5A83DA6B8F015
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202563_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202563_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202563_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202563_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1202653
original SHA-256: 7D974DA6BC169D63D8F0985462212C77EA916E9D72725A254402BC0C3D5B3956
candidate SHA-256: 9D20D84822AA0E08D91BEF6818E1C04E3EDD450F8BAD52EE1CD51A6D655D93D8
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

