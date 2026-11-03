# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:136170
original SHA-256: 51EA3A7C436B866A1E6D5E3C83A42F9A6A4875532DDCCA548F06F7B177A32E1A
candidate SHA-256: F313CC5A6C68922595337152F13EAF0FBE24ED643540100C65E406BAB7A6730A
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:136235
original SHA-256: 37C449CC5A3BE78AEA014C9F6D97E3C6E6BA4BD078F9A59FB94C1428EA4B1656
candidate SHA-256: 37C449CC5A3BE78AEA014C9F6D97E3C6E6BA4BD078F9A59FB94C1428EA4B1656
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136235_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136235_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136235_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:136368
original SHA-256: 032232EF05F7277A295692F40798E7E90037759D76FB4624DB99BE4EB3F5184F
candidate SHA-256: 032232EF05F7277A295692F40798E7E90037759D76FB4624DB99BE4EB3F5184F
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136368_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136368_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:136434
original SHA-256: BA14747A46A88F2A4CDCB8E131A66C868A9B3415ABC6D5EA02336B9AB7270FC2
candidate SHA-256: BA14747A46A88F2A4CDCB8E131A66C868A9B3415ABC6D5EA02336B9AB7270FC2
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136434_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:136493
original SHA-256: F1B93E343533017D9637465E96BC6E270927002B38BAB239B078EE7A18A86BF4
candidate SHA-256: F1B93E343533017D9637465E96BC6E270927002B38BAB239B078EE7A18A86BF4
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136493_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136493_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136493_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136493_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136493_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

