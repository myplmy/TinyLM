# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:963386
original SHA-256: C29E37BBDF3998DDD067B83A7073F4E109B1314D0C0FCC4AFF23DB823476BFC0
candidate SHA-256: C29E37BBDF3998DDD067B83A7073F4E109B1314D0C0FCC4AFF23DB823476BFC0
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_963386_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:963408
original SHA-256: 5F1C426C647E65206BE64B48377A85ABACCE0D5B721E21730E7244D361B6383C
candidate SHA-256: 6C1522E3D25FD4CB96A8ABC120E596A740E04519998CD9EF967E14891F88FA2A
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:963522
original SHA-256: 8BFBFAFA273F00009F0611DD9C26D041715FD4E5E4D7089D008AE920AFA7E243
candidate SHA-256: EA0695FBD785DD6D5E155F9A3E696C71CEFFCB6AC8E3DE1498225580E81AA52B
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:963836
original SHA-256: 2DB49C21C16FF2D040918BB0EB9D0E2CB09C32E5F51984DFFD30CE9E4CDA2BA9
candidate SHA-256: 2DB49C21C16FF2D040918BB0EB9D0E2CB09C32E5F51984DFFD30CE9E4CDA2BA9
원문 frame 패킷: [1, 9]
최종 full_diff 패킷: [17, 17]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 17]
후보 중복만 있는 생략 가능 패킷: [10, 11, 12, 13, 14, 15, 16]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_963836_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_963836_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_963836_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_963836_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_963836_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_963836_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_963836_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_963836_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_963836_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_963836_0017.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:963882
original SHA-256: 0602D6B09C7B52BC23233CA0B2961A49A825611F0D55AB95D26FC2A0ACB63A63
candidate SHA-256: 0602D6B09C7B52BC23233CA0B2961A49A825611F0D55AB95D26FC2A0ACB63A63
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_963882_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_963882_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_963882_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_963882_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

