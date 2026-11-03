# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:308667
original SHA-256: E916B8E057009668965BF2FEB9938BCAE5436E8E0F8B87D639F1D6DFE58FCE94
candidate SHA-256: B6E89D892AAFD5E3F66077AE4FB70548AF1F2889713B5FF2955B2E897C7A54A0
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:308735
original SHA-256: 41AC825E952956D93E824294689C952D71FA425F9F16D8437E6721ABA45BDB90
candidate SHA-256: 41AC825E952956D93E824294689C952D71FA425F9F16D8437E6721ABA45BDB90
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_308735_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_308735_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_308735_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_308735_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_308735_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:308778
original SHA-256: F1B7F1854CFC627D4539586D59339382FC0155C80BB05EE216F17BD72DB1AF0E
candidate SHA-256: F1B7F1854CFC627D4539586D59339382FC0155C80BB05EE216F17BD72DB1AF0E
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_308778_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_308778_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_308778_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:308781
original SHA-256: FAF8D9401538B8313875195163F6C3601725646770D2E0F07ECF050C2D2B60E8
candidate SHA-256: FAF8D9401538B8313875195163F6C3601725646770D2E0F07ECF050C2D2B60E8
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_308781_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_308781_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_308781_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:308806
original SHA-256: E4B8BAA51072E2E8B5A8C71BF0B160A91F4E99612792E2A49B0C129C522FE404
candidate SHA-256: E4B8BAA51072E2E8B5A8C71BF0B160A91F4E99612792E2A49B0C129C522FE404
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_308806_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_308806_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_308806_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

