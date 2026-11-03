# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:419480
original SHA-256: 0BDE9BD47D26FE43A664039CD056058906391B885BA5F17F241CFFD2EF316BFC
candidate SHA-256: 0BDE9BD47D26FE43A664039CD056058906391B885BA5F17F241CFFD2EF316BFC
원문 frame 패킷: [1, 11]
최종 full_diff 패킷: [22, 22]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 22]
후보 중복만 있는 생략 가능 패킷: [12, 13, 14, 15, 16, 17, 18, 19, 20, 21]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419480_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419480_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419480_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419480_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419480_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419480_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419480_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419480_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419480_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419480_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419480_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419480_0022.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:419491
original SHA-256: B271B93FC5ED5A464BF6AECCC6F5FE0797532D5249C01BAC2938F5D8C5AE59CE
candidate SHA-256: B271B93FC5ED5A464BF6AECCC6F5FE0797532D5249C01BAC2938F5D8C5AE59CE
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6, 7]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419491_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419491_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419491_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419491_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419491_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:419531
original SHA-256: 71408C7B1B1F1FDCE28024F6D0AE6C702B1CF1C80CA7FBA078389FB0C150D977
candidate SHA-256: 71408C7B1B1F1FDCE28024F6D0AE6C702B1CF1C80CA7FBA078389FB0C150D977
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [12, 12]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 12]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10, 11]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419531_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419531_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419531_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419531_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419531_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419531_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419531_0012.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:419565
original SHA-256: 1D84443330FE5301F4B7DF90E8CCEE3A4110FA87654C92FD0B38EC8837A4545F
candidate SHA-256: 9D0514D61EF5CAD86F40A820EE5D4AB415DD9CF80F61F6F9B930F54321397A42
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:419588
original SHA-256: 6CAA79DD3EB451ED6FD89B6E05599422F35B9FEBB2FAEC69D50E8C7B76B92A5E
candidate SHA-256: 6CAA79DD3EB451ED6FD89B6E05599422F35B9FEBB2FAEC69D50E8C7B76B92A5E
원문 frame 패킷: [1, 7]
최종 full_diff 패킷: [14, 14]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 14]
후보 중복만 있는 생략 가능 패킷: [8, 9, 10, 11, 12, 13]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419588_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419588_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419588_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419588_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419588_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419588_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419588_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419588_0014.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

