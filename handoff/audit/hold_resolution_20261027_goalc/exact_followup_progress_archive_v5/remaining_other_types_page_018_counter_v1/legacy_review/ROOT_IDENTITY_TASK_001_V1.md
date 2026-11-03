# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:190051
original SHA-256: 5DD90CCEAD7B8965D918F7A54E25D672CC5982ECAAE3603D8E40DC0C5F3630C2
candidate SHA-256: 5DD90CCEAD7B8965D918F7A54E25D672CC5982ECAAE3603D8E40DC0C5F3630C2
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190051_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190051_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190051_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190051_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190051_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:190398
original SHA-256: 3F7C69BBC9A7CE6BACBEAE910CD87928D23573BB2C0ACC531BB7AD8D8BF05386
candidate SHA-256: 3F7C69BBC9A7CE6BACBEAE910CD87928D23573BB2C0ACC531BB7AD8D8BF05386
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190398_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190398_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190398_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190398_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:190500
original SHA-256: 3F620D87A3EB02384339CD87AD5C6E0543130A78DDED98F25BB3F3B1A96AE2D7
candidate SHA-256: 0BF88FFDB9712AA958A97D1BA44B03DFF1D5C2FACA5E8BF66772C73B30E3CAEC
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:190511
original SHA-256: D7E6F1FBC2B97570A3A1F04421E6C291F1866093FA90109E605875F4AC81355F
candidate SHA-256: 39202C1126A056231901240F16FB455C938938CF020EDCEA57AC7188F64FE789
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:190784
original SHA-256: 9387FCAADF1487786B56C1A7416CA22B051589B0427D650BCAA1666A2D5F3475
candidate SHA-256: 9387FCAADF1487786B56C1A7416CA22B051589B0427D650BCAA1666A2D5F3475
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190784_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190784_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

