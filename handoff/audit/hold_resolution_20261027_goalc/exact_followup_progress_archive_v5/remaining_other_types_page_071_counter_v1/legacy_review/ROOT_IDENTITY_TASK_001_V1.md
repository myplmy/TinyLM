# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:946849
original SHA-256: 9FC1B0B724CF874754C4C591DECDF4732A1FBC9DC536F32B71C1A72886B27881
candidate SHA-256: 9FC1B0B724CF874754C4C591DECDF4732A1FBC9DC536F32B71C1A72886B27881
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_946849_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_946849_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:947041
original SHA-256: 527B49E3CD1AFB3B824173F180143AB1E7327A4EC17DD3A2767E4AF4CE63584D
candidate SHA-256: 527B49E3CD1AFB3B824173F180143AB1E7327A4EC17DD3A2767E4AF4CE63584D
원문 frame 패킷: [1, 13]
최종 full_diff 패킷: [25, 25]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 25]
후보 중복만 있는 생략 가능 패킷: [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947041_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947041_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947041_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947041_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947041_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947041_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947041_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947041_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947041_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947041_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947041_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947041_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947041_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947041_0025.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:947291
original SHA-256: 9503C7F890A47FDB3005D36E6B9848FD50E6395DF4A40045BE1A2ABAB7E1976B
candidate SHA-256: 9503C7F890A47FDB3005D36E6B9848FD50E6395DF4A40045BE1A2ABAB7E1976B
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 9]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8, 9]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947291_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947291_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947291_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947291_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947291_0008.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947291_0009.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:947414
original SHA-256: C7B9BF02C0643054C93817088AE26EAC2F50890175EEB1F1C6C3400A392BBA24
candidate SHA-256: C7B9BF02C0643054C93817088AE26EAC2F50890175EEB1F1C6C3400A392BBA24
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [10, 10]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 10]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8, 9]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947414_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947414_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947414_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947414_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947414_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947414_0010.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:947423
original SHA-256: C537C6C936A6448CB51EBB8708A7E922EB539BCA0BFCBE0FBDD91BD7A6E135A7
candidate SHA-256: C537C6C936A6448CB51EBB8708A7E922EB539BCA0BFCBE0FBDD91BD7A6E135A7
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [9, 9]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 9]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947423_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947423_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947423_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947423_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947423_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947423_0009.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

