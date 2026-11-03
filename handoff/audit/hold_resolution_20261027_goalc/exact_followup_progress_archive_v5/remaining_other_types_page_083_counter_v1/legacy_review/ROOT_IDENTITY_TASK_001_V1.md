# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1151145
original SHA-256: E3BBC13CD2D6767298A96A621BD17436C540888899E7E4E579CB1A6805BCD06F
candidate SHA-256: E3BBC13CD2D6767298A96A621BD17436C540888899E7E4E579CB1A6805BCD06F
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1151145_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1151590
original SHA-256: ABFA137961691B0D81BB8AA9857FAC92157D4D3120B5F589D611A7D5ACC4B1D6
candidate SHA-256: 1790FB1B8362E50320F1221D4B37337DD29CBEB869082714F8EC9A8E0BB2B0D5
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1151846
original SHA-256: E71A29614FBB7A28DC4C6F050CB4F6E15A968766B14500D7A4561FD7FC16990F
candidate SHA-256: E71A29614FBB7A28DC4C6F050CB4F6E15A968766B14500D7A4561FD7FC16990F
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1151846_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1151846_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1151846_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1151846_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1151909
original SHA-256: 25EF2616B692250324932B8C87446A5083BE0AF2AF3D14012CBEB026D0C4BE63
candidate SHA-256: 25EF2616B692250324932B8C87446A5083BE0AF2AF3D14012CBEB026D0C4BE63
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1151909_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1152321
original SHA-256: F54F4CFE44DCEBC05CDA6E0150190ED56C1FA332DB824CFD5D450C33055BE0BC
candidate SHA-256: F54F4CFE44DCEBC05CDA6E0150190ED56C1FA332DB824CFD5D450C33055BE0BC
원문 frame 패킷: [1, 34]
최종 full_diff 패킷: [68, 68]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 68]
후보 중복만 있는 생략 가능 패킷: [35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1152321_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1152321_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1152321_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1152321_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1152321_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1152321_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1152321_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1152321_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1152321_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1152321_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1152321_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1152321_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1152321_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1152321_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1152321_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1152321_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1152321_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1152321_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1152321_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1152321_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1152321_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1152321_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1152321_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1152321_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1152321_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1152321_0026.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1152321_0027.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1152321_0028.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1152321_0029.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1152321_0030.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1152321_0031.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1152321_0032.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1152321_0033.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1152321_0034.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1152321_0068.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

