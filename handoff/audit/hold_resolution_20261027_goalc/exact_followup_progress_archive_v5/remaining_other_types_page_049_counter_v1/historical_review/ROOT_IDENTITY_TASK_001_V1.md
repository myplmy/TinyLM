# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:622120
original SHA-256: 7BA115FE45B1E0FEC712B8A65EBB898E029F9EFDCCE71ECFB1B70DDA90F900AD
candidate SHA-256: CC043EDF5D2E8B1A7275D523B4C330F81CFDBB8B63AD23C8C882A7A7EA329B1B
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:622164
original SHA-256: 8E35288D2D904AD2EA37647C197537DC4FFE1B44FC37DAC8A07B14D8BD73E1CE
candidate SHA-256: 8E35288D2D904AD2EA37647C197537DC4FFE1B44FC37DAC8A07B14D8BD73E1CE
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622164_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:622194
original SHA-256: 87A514C623A84E4A3819B5B4A4447F19449145D8D8DFA2C2D92522FDE46FD526
candidate SHA-256: 87A514C623A84E4A3819B5B4A4447F19449145D8D8DFA2C2D92522FDE46FD526
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [11, 11]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 11]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622194_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622194_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622194_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622194_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622194_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622194_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622194_0011.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:622377
original SHA-256: DEAAC44460B8C1553B6931FCC7F21D3C99FB124CDFCEE4ED75CF9018D5E956E4
candidate SHA-256: DEAAC44460B8C1553B6931FCC7F21D3C99FB124CDFCEE4ED75CF9018D5E956E4
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [9, 9]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 9]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622377_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622377_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622377_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622377_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622377_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622377_0009.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:622654
original SHA-256: 4D0E1F8AA9BBB95C952EED57AF8799197FD42BD56B0F7DDEB197C035521E013E
candidate SHA-256: C4B09410FC59B840291C0283D4DE51AB7CC007A28C5D042B2AB357C92E06FECA
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

