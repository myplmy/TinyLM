# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1341811
original SHA-256: 306ECEA7D4978A037974A8B9781BB0FF722A1E21965B645F182C3A8E93F9D16A
candidate SHA-256: 306ECEA7D4978A037974A8B9781BB0FF722A1E21965B645F182C3A8E93F9D16A
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1341811_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1341811_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1341811_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1341968
original SHA-256: F341BE1DA79DB10EBBEC9EA07A3ABEED982F372D73EE2932FF8F078A7CECDBE5
candidate SHA-256: F341BE1DA79DB10EBBEC9EA07A3ABEED982F372D73EE2932FF8F078A7CECDBE5
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1341968_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1341968_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1341968_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1341968_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1341968_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1342055
original SHA-256: 9938116B027C769F687408D31BBA5C2FC803C37C7F169A727CE6530E43F5D412
candidate SHA-256: 9938116B027C769F687408D31BBA5C2FC803C37C7F169A727CE6530E43F5D412
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342055_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342055_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342055_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342055_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1342896
original SHA-256: F5EDE8BC9E3F286956305B5F12F8E173FA18BFD887DCDBF97F4FEFFC1EC56765
candidate SHA-256: F5EDE8BC9E3F286956305B5F12F8E173FA18BFD887DCDBF97F4FEFFC1EC56765
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342896_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342896_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342896_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342896_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1342896_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1343794
original SHA-256: 86FA8FAA7996B1E2B0FAF8DF35F4CD92040D615B31E1B4E5AAC4CDFC2F0C123F
candidate SHA-256: 86FA8FAA7996B1E2B0FAF8DF35F4CD92040D615B31E1B4E5AAC4CDFC2F0C123F
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [10, 10]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 10]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8, 9]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1343794_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1343794_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1343794_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1343794_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1343794_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_094_counter_v1/reading_packets_v1/expanded_train_1343794_0010.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

