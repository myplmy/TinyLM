# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1302849
original SHA-256: 6AF87391DF18EA2E3C2F8BA8C8EA4A4E4DF0D984AD61BA5E7EA5015B4FAB4503
candidate SHA-256: 6AF87391DF18EA2E3C2F8BA8C8EA4A4E4DF0D984AD61BA5E7EA5015B4FAB4503
원문 frame 패킷: [1, 16]
최종 full_diff 패킷: [31, 31]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 31]
후보 중복만 있는 생략 가능 패킷: [17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_092_counter_v1/reading_packets_v1/expanded_train_1302849_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_092_counter_v1/reading_packets_v1/expanded_train_1302849_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_092_counter_v1/reading_packets_v1/expanded_train_1302849_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_092_counter_v1/reading_packets_v1/expanded_train_1302849_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_092_counter_v1/reading_packets_v1/expanded_train_1302849_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_092_counter_v1/reading_packets_v1/expanded_train_1302849_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_092_counter_v1/reading_packets_v1/expanded_train_1302849_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_092_counter_v1/reading_packets_v1/expanded_train_1302849_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_092_counter_v1/reading_packets_v1/expanded_train_1302849_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_092_counter_v1/reading_packets_v1/expanded_train_1302849_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_092_counter_v1/reading_packets_v1/expanded_train_1302849_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_092_counter_v1/reading_packets_v1/expanded_train_1302849_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_092_counter_v1/reading_packets_v1/expanded_train_1302849_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_092_counter_v1/reading_packets_v1/expanded_train_1302849_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_092_counter_v1/reading_packets_v1/expanded_train_1302849_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_092_counter_v1/reading_packets_v1/expanded_train_1302849_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_092_counter_v1/reading_packets_v1/expanded_train_1302849_0031.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1303718
original SHA-256: 53649DCAE671348CC60BAFF269DA9F271522EEE85595D7F311B234A9435D639D
candidate SHA-256: 53649DCAE671348CC60BAFF269DA9F271522EEE85595D7F311B234A9435D639D
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_092_counter_v1/reading_packets_v1/expanded_train_1303718_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_092_counter_v1/reading_packets_v1/expanded_train_1303718_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_092_counter_v1/reading_packets_v1/expanded_train_1303718_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_092_counter_v1/reading_packets_v1/expanded_train_1303718_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1303765
original SHA-256: 6517234B880222EB5696E285BAAAC02EB678DD74B0DF6E8E37009AD30EF67BB1
candidate SHA-256: 6517234B880222EB5696E285BAAAC02EB678DD74B0DF6E8E37009AD30EF67BB1
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_092_counter_v1/reading_packets_v1/expanded_train_1303765_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_092_counter_v1/reading_packets_v1/expanded_train_1303765_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_092_counter_v1/reading_packets_v1/expanded_train_1303765_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1303784
original SHA-256: 5F0864D7ED1724BC27A0D7B9058BF1DEFDE746472983C274DF0F8FF14EB54F9E
candidate SHA-256: 5F0864D7ED1724BC27A0D7B9058BF1DEFDE746472983C274DF0F8FF14EB54F9E
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_092_counter_v1/reading_packets_v1/expanded_train_1303784_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_092_counter_v1/reading_packets_v1/expanded_train_1303784_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1304082
original SHA-256: 823211241B373FCF39F0545657AC93DB07CF84075B2E6467D07A0BED32C59DED
candidate SHA-256: 823211241B373FCF39F0545657AC93DB07CF84075B2E6467D07A0BED32C59DED
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [12, 12]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 12]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10, 11]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_092_counter_v1/reading_packets_v1/expanded_train_1304082_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_092_counter_v1/reading_packets_v1/expanded_train_1304082_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_092_counter_v1/reading_packets_v1/expanded_train_1304082_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_092_counter_v1/reading_packets_v1/expanded_train_1304082_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_092_counter_v1/reading_packets_v1/expanded_train_1304082_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_092_counter_v1/reading_packets_v1/expanded_train_1304082_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_092_counter_v1/reading_packets_v1/expanded_train_1304082_0012.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

