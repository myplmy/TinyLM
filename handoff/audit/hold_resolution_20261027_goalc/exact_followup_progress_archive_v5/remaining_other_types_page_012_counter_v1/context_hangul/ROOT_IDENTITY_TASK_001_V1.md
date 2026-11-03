# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:114215
original SHA-256: BA5D9D617F54FE398C865275F285227718A9BAE241ACAFB03675D3C4FF36EC8C
candidate SHA-256: BA5D9D617F54FE398C865275F285227718A9BAE241ACAFB03675D3C4FF36EC8C
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_012_counter_v1/reading_packets_v1/expanded_train_114215_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:114254
original SHA-256: 07D200F755C9D928D05FAAE3775B68E2CFCB466AE062400CD463A2137ED2E5DC
candidate SHA-256: 07D200F755C9D928D05FAAE3775B68E2CFCB466AE062400CD463A2137ED2E5DC
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_012_counter_v1/reading_packets_v1/expanded_train_114254_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:114316
original SHA-256: D5F1E28A11B467AAD8B90A731C9086B7EAA559CE34A4B317B423EA0C4EDDAAD3
candidate SHA-256: 8D1DB057DC8FCBE324AB06DCBEBE4C8CF2016BA195463EA04E99241D7570D652
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:114317
original SHA-256: 11B97766895A52E62F26817CA30A3397B07DA76697DF1F47B1AFF90C19442D24
candidate SHA-256: 11B97766895A52E62F26817CA30A3397B07DA76697DF1F47B1AFF90C19442D24
원문 frame 패킷: [1, 10]
최종 full_diff 패킷: [19, 19]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 19]
후보 중복만 있는 생략 가능 패킷: [11, 12, 13, 14, 15, 16, 17, 18]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_012_counter_v1/reading_packets_v1/expanded_train_114317_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_012_counter_v1/reading_packets_v1/expanded_train_114317_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_012_counter_v1/reading_packets_v1/expanded_train_114317_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_012_counter_v1/reading_packets_v1/expanded_train_114317_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_012_counter_v1/reading_packets_v1/expanded_train_114317_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_012_counter_v1/reading_packets_v1/expanded_train_114317_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_012_counter_v1/reading_packets_v1/expanded_train_114317_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_012_counter_v1/reading_packets_v1/expanded_train_114317_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_012_counter_v1/reading_packets_v1/expanded_train_114317_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_012_counter_v1/reading_packets_v1/expanded_train_114317_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_012_counter_v1/reading_packets_v1/expanded_train_114317_0019.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:114362
original SHA-256: 87D8A2C407E61F62ADD37C828A116C0864D7A55ABC972CA9EF75A94B6439E6C9
candidate SHA-256: E172F51607EF64CFBB0CCD98D46F40E502C236271833D9CC1C735BA3B0CF071A
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

