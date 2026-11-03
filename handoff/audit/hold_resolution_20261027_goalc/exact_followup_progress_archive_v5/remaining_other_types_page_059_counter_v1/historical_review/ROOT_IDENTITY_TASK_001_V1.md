# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:765107
original SHA-256: 62FDCE1A0E660DBE3FDD16F59277ABDB3239442982F0C4F551B36668798DF4FD
candidate SHA-256: 62FDCE1A0E660DBE3FDD16F59277ABDB3239442982F0C4F551B36668798DF4FD
원문 frame 패킷: [1, 12]
최종 full_diff 패킷: [24, 24]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 24]
후보 중복만 있는 생략 가능 패킷: [13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765107_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765107_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765107_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765107_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765107_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765107_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765107_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765107_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765107_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765107_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765107_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765107_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765107_0024.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:765171
original SHA-256: F86FF3C2C8CA654A58CFABDB2D637C4B53CBF2C9AC4E747CA81D518BB9D5D28D
candidate SHA-256: F86FF3C2C8CA654A58CFABDB2D637C4B53CBF2C9AC4E747CA81D518BB9D5D28D
원문 frame 패킷: [1, 10]
최종 full_diff 패킷: [20, 20]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20]
후보 중복만 있는 생략 가능 패킷: [11, 12, 13, 14, 15, 16, 17, 18, 19]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765171_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765171_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765171_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765171_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765171_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765171_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765171_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765171_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765171_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765171_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765171_0020.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:765320
original SHA-256: 8619A6F65FF58267BBDEAB014CE6A4B5A2B5901573AA6A4A0E2D05E54495F58A
candidate SHA-256: 726D029B83C4C480DAB762633F545C35E7232F308C7DCF1EE2BE6BCFFEE5B031
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:765437
original SHA-256: F89F6F5AC17A91AC17E9CD61C69C9E7B1513FE11001876F50ABA046D9EEDD03C
candidate SHA-256: 3F78E6BC17ADF8808DE3C90A9A251F83E808FF00354AB8E32C792FA6C6BE6B7E
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:765542
original SHA-256: C83AADD7A09078F9ED754F1BE3C2EAD9D355B4E16D7C46A1F767F3BDE461AEC9
candidate SHA-256: C83AADD7A09078F9ED754F1BE3C2EAD9D355B4E16D7C46A1F767F3BDE461AEC9
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765542_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765542_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765542_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_059_counter_v1/reading_packets_v1/expanded_train_765542_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

