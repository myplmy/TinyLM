# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:373186
original SHA-256: EC8B7720B580B3C87E65B4A57EBD682E262B3263F97EA8C31963966DD9FD001E
candidate SHA-256: 50030D191909F95789C0DE2E914AB84CF6D5D2EE7669028F604124217501096D
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:373188
original SHA-256: CAC64EDCE9E39814A0A99A9B03CD20D3FA31329101FC1045C38C23BA8DE91226
candidate SHA-256: CAC64EDCE9E39814A0A99A9B03CD20D3FA31329101FC1045C38C23BA8DE91226
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373188_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373188_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:374025
original SHA-256: 223731B2D3F1ED1A535815A1F09E008E0B6C8981CF0010FD54BD2AC82D8FFC4A
candidate SHA-256: 223731B2D3F1ED1A535815A1F09E008E0B6C8981CF0010FD54BD2AC82D8FFC4A
원문 frame 패킷: [1, 8]
최종 full_diff 패킷: [15, 15]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 15]
후보 중복만 있는 생략 가능 패킷: [9, 10, 11, 12, 13, 14]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_374025_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_374025_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_374025_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_374025_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_374025_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_374025_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_374025_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_374025_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_374025_0015.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:374523
original SHA-256: 427B0FE636CB6EDFB2263757023E6249DBB0658095D59ED7F33DCB666A70C973
candidate SHA-256: 427B0FE636CB6EDFB2263757023E6249DBB0658095D59ED7F33DCB666A70C973
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [12, 12]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 12]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10, 11]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_374523_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_374523_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_374523_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_374523_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_374523_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_374523_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_374523_0012.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:374571
original SHA-256: 071E4459CA260DD4CD5D211AD0624BB04B001E1C3429CF535BAA8C21C309F80B
candidate SHA-256: 071E4459CA260DD4CD5D211AD0624BB04B001E1C3429CF535BAA8C21C309F80B
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [10, 11]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 10, 11]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8, 9]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_374571_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_374571_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_374571_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_374571_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_374571_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_374571_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_374571_0011.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

