# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:386803
original SHA-256: 36DE5E31528E1D518FEE06D07BE0028ED2CBA1202B147C237748E4BA0D464882
candidate SHA-256: 6C5A77916AE206202ABCA7A1708E4AA5E2A0CCE389142EE3C428F876C3EE6E09
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:386804
original SHA-256: 826CC06544846C93BAD57E1E53EC01376F7981E49B9C2A5ACC63D9F37BCF6FD0
candidate SHA-256: 826CC06544846C93BAD57E1E53EC01376F7981E49B9C2A5ACC63D9F37BCF6FD0
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_386804_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_386804_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_386804_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:386981
original SHA-256: 6CB96447040E53A33DD3C14CAE00ED7917EA0643A6448CA0CE52AF11267A90CE
candidate SHA-256: 952817B56EBB191287DC3CED2B4BC7C81F3D0B637E7A5986C7AB94C96C97EEE9
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:387059
original SHA-256: F97F69B5FFC11E433E9C6AE77D03DE4B16B4D991DA125D07DEDDFEA326790FE4
candidate SHA-256: F97F69B5FFC11E433E9C6AE77D03DE4B16B4D991DA125D07DEDDFEA326790FE4
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387059_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387059_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387059_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387059_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:387246
original SHA-256: 5CE4A5D47FA146609EA09555B5C9C0B56E18A90310AEBF930B68E0293F5AAE52
candidate SHA-256: 5CE4A5D47FA146609EA09555B5C9C0B56E18A90310AEBF930B68E0293F5AAE52
원문 frame 패킷: [1, 25]
최종 full_diff 패킷: [49, 49]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 49]
후보 중복만 있는 생략 가능 패킷: [26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387246_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387246_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387246_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387246_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387246_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387246_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387246_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387246_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387246_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387246_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387246_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387246_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387246_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387246_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387246_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387246_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387246_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387246_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387246_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387246_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387246_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387246_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387246_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387246_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387246_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387246_0049.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

