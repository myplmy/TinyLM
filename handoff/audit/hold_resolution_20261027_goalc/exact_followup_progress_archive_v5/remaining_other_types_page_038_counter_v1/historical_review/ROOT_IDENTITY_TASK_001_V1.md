# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:461184
original SHA-256: D8AAA7C55E8FCF8CCE80E473C790AAEBAF2CA60368E56CBF2A169B9F7C5FB4C4
candidate SHA-256: D8AAA7C55E8FCF8CCE80E473C790AAEBAF2CA60368E56CBF2A169B9F7C5FB4C4
원문 frame 패킷: [1, 31]
최종 full_diff 패킷: [61, 61]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 61]
후보 중복만 있는 생략 가능 패킷: [32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461184_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461184_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461184_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461184_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461184_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461184_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461184_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461184_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461184_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461184_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461184_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461184_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461184_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461184_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461184_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461184_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461184_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461184_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461184_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461184_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461184_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461184_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461184_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461184_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461184_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461184_0026.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461184_0027.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461184_0028.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461184_0029.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461184_0030.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461184_0031.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_461184_0061.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:461205
original SHA-256: F32EFDFCA5C876ACC2C02DF22AF2AF29E28C95F71DE705C4AE5317F2CEEF1273
candidate SHA-256: 85B7065B8861C230F36D2129DB5CA62A88E83191AF7A2390BED295C11D81ABC3
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:462223
original SHA-256: 071B4E027C2EE5FD8C8D463C6ED0F22D1B9442E519148D256B4B2871D1AF7F9C
candidate SHA-256: 071B4E027C2EE5FD8C8D463C6ED0F22D1B9442E519148D256B4B2871D1AF7F9C
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_462223_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_462223_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:462396
original SHA-256: 86DA4D2E9EBC24B0F690DA44209A9E893FDA966EB3581B024BFF1A6477CA7FB4
candidate SHA-256: 86DA4D2E9EBC24B0F690DA44209A9E893FDA966EB3581B024BFF1A6477CA7FB4
원문 frame 패킷: [1, 8]
최종 full_diff 패킷: [15, 16]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 15, 16]
후보 중복만 있는 생략 가능 패킷: [9, 10, 11, 12, 13, 14]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_462396_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_462396_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_462396_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_462396_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_462396_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_462396_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_462396_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_462396_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_462396_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_462396_0016.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:462406
original SHA-256: 29438B59A2632D6D9BB26311144972511E9FDC80C2E714F4C7DCC4EF8BC491AA
candidate SHA-256: 29438B59A2632D6D9BB26311144972511E9FDC80C2E714F4C7DCC4EF8BC491AA
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_038_counter_v1/reading_packets_v1/expanded_train_462406_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

