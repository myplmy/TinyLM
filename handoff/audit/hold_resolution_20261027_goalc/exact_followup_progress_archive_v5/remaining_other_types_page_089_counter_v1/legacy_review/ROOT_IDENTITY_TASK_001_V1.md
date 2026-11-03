# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1252737
original SHA-256: A82FA2051850BA8062299B87B5CA569BCEE5416F6FF9854C62132F8D554F585F
candidate SHA-256: A82FA2051850BA8062299B87B5CA569BCEE5416F6FF9854C62132F8D554F585F
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_089_counter_v1/reading_packets_v1/expanded_train_1252737_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1252878
original SHA-256: 8B68DFA1385A9FB2E2796830A0E045C12537B5DC71395F882FC0305B95CE5779
candidate SHA-256: 8B68DFA1385A9FB2E2796830A0E045C12537B5DC71395F882FC0305B95CE5779
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_089_counter_v1/reading_packets_v1/expanded_train_1252878_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_089_counter_v1/reading_packets_v1/expanded_train_1252878_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_089_counter_v1/reading_packets_v1/expanded_train_1252878_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_089_counter_v1/reading_packets_v1/expanded_train_1252878_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1252886
original SHA-256: 3644141AACA6BEE6134D9F219ACE9D937E4A05A76867AAB27B2C57A0EA321441
candidate SHA-256: 3644141AACA6BEE6134D9F219ACE9D937E4A05A76867AAB27B2C57A0EA321441
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_089_counter_v1/reading_packets_v1/expanded_train_1252886_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1253257
original SHA-256: 16FA1B8E814E1438BCE317C541147AFE50A5BAD79DF08B1802E82B45E61AEAC2
candidate SHA-256: 16FA1B8E814E1438BCE317C541147AFE50A5BAD79DF08B1802E82B45E61AEAC2
원문 frame 패킷: [1, 7]
최종 full_diff 패킷: [14, 14]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 14]
후보 중복만 있는 생략 가능 패킷: [8, 9, 10, 11, 12, 13]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_089_counter_v1/reading_packets_v1/expanded_train_1253257_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_089_counter_v1/reading_packets_v1/expanded_train_1253257_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_089_counter_v1/reading_packets_v1/expanded_train_1253257_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_089_counter_v1/reading_packets_v1/expanded_train_1253257_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_089_counter_v1/reading_packets_v1/expanded_train_1253257_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_089_counter_v1/reading_packets_v1/expanded_train_1253257_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_089_counter_v1/reading_packets_v1/expanded_train_1253257_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_089_counter_v1/reading_packets_v1/expanded_train_1253257_0014.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1253271
original SHA-256: AA7EF7C6A1573597D3F3557569560639999A93ACF07CDEB6ADF896C749321A94
candidate SHA-256: 4C1E8A699BEA99212CFA9C618AC192D9F6F2F0CEBF6B095EC5D037183D6BB157
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

