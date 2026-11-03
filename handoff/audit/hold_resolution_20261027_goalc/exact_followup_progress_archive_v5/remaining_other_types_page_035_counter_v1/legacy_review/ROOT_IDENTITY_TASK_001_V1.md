# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:419424
original SHA-256: 47246008D68EF8B681F864442D7DF9E9E0F39EC18D2EAECD487C4312A76CD7F8
candidate SHA-256: 47246008D68EF8B681F864442D7DF9E9E0F39EC18D2EAECD487C4312A76CD7F8
원문 frame 패킷: [1, 7]
최종 full_diff 패킷: [14, 14]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 14]
후보 중복만 있는 생략 가능 패킷: [8, 9, 10, 11, 12, 13]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419424_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419424_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419424_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419424_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419424_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419424_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419424_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419424_0014.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:419700
original SHA-256: 407B36E0B3440A6C262497BCA946F2EC139D70BEA9088A92AB6A0DA70ED326B6
candidate SHA-256: 407B36E0B3440A6C262497BCA946F2EC139D70BEA9088A92AB6A0DA70ED326B6
원문 frame 패킷: [1, 9]
최종 full_diff 패킷: [18, 18]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 18]
후보 중복만 있는 생략 가능 패킷: [10, 11, 12, 13, 14, 15, 16, 17]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419700_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419700_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419700_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419700_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419700_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419700_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419700_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419700_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419700_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419700_0018.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:419842
original SHA-256: 0CE710A27D8D4271821AA7E4498BF3B2B530A4D459E7281BBC3F2A5906511BC2
candidate SHA-256: 0CE710A27D8D4271821AA7E4498BF3B2B530A4D459E7281BBC3F2A5906511BC2
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419842_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:419845
original SHA-256: AC964CF78486948E18D3CC4157482F37D3C7656B373D3B59FA7388E28C111F27
candidate SHA-256: AC964CF78486948E18D3CC4157482F37D3C7656B373D3B59FA7388E28C111F27
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419845_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:420058
original SHA-256: 8F5D29472FFF9A9FF2453FFAA665AF5F2DE2B7E1326D02AED203E58930E572B3
candidate SHA-256: FB70823D992BC4D6C605A2073F250219F44053D16B6E250DD6F8DCFD7FB6652E
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

