# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:282471
original SHA-256: CBB72E1CCB6E143A44B7F8F38DC2F5B570F5753867AB8664D0095B923B35E038
candidate SHA-256: CBB72E1CCB6E143A44B7F8F38DC2F5B570F5753867AB8664D0095B923B35E038
원문 frame 패킷: [1, 30]
최종 full_diff 패킷: [59, 59]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 59]
후보 중복만 있는 생략 가능 패킷: [31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282471_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282471_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282471_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282471_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282471_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282471_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282471_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282471_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282471_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282471_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282471_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282471_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282471_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282471_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282471_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282471_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282471_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282471_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282471_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282471_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282471_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282471_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282471_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282471_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282471_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282471_0026.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282471_0027.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282471_0028.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282471_0029.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282471_0030.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282471_0059.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:282794
original SHA-256: 44730EAF94A84A140D2859DB633B77B53FEE4F4339F32A03DD7BAD179AFB4E82
candidate SHA-256: 6A44FAC89D2914303064D82F17AAD1DDB34771A37520AFAD4BC04F033B8188DB
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:282817
original SHA-256: 6F1930B87FD2399B22C3A4A6D1F48BC623796C7A369ECE7DB44958F982676409
candidate SHA-256: 96966E58368C9A703F6B74698D6F14272AB909CD7D8415EE01655CC0322FAF14
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:282864
original SHA-256: BCD7E0E14A040F1706B6EB9CEB170E8A2F63A6AD60098DAA1A4A4EACE46B1B9E
candidate SHA-256: BCD7E0E14A040F1706B6EB9CEB170E8A2F63A6AD60098DAA1A4A4EACE46B1B9E
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282864_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282864_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282864_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:283088
original SHA-256: 3E19D3E3C6692AD16896209BF9124C3538A5AD4D696FED8F4B33094CA662B1D4
candidate SHA-256: 3E19D3E3C6692AD16896209BF9124C3538A5AD4D696FED8F4B33094CA662B1D4
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_283088_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

