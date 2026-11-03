# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:431195
original SHA-256: D8F1CB48D188EE548632402B3E0F096FA33A77466423CC66E7B663B87FA2B962
candidate SHA-256: 9EDB51D0EE79708E7318C719389DECA626EA3F71A7D7567F72A7AFB026A36CE0
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:431404
original SHA-256: 82DB697866A7EB8ED3C3DFFC6685D969F6578A2699A243FDF597F7E0BF60AD97
candidate SHA-256: 82DB697866A7EB8ED3C3DFFC6685D969F6578A2699A243FDF597F7E0BF60AD97
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [11, 11]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 11]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431404_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431404_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431404_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431404_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431404_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431404_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431404_0011.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:431707
original SHA-256: 4CD3D5F291995284F2A91711DDF14DB1A4B93DE0BAAA70501C6B0F77F8C09E35
candidate SHA-256: 4CD3D5F291995284F2A91711DDF14DB1A4B93DE0BAAA70501C6B0F77F8C09E35
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431707_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431707_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_036_counter_v1/reading_packets_v1/expanded_train_431707_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:432143
original SHA-256: 3E1E00B018AF995E191A1CF29169130E652D18C8AB3410E356F4215CC4AC5421
candidate SHA-256: 93002F58AD36C3542CC7BACFD599B4F824FD6A09D4038BF7098D9FFB4D835F38
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:432266
original SHA-256: 5D2FE6BC6073C23FB350FFEB619CB4B6D96ABBDF0DCD99322E899EE46D09908E
candidate SHA-256: 0303E0FC2A58712CF3451D01DD1436F669CFDE106A33140EDFA723B2E68B640C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

