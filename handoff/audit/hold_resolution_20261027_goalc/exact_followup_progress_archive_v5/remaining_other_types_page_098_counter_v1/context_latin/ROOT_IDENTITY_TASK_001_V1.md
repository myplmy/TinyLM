# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1420984
original SHA-256: 29072CE6C8788A6F096E79C4DA4E454795E38AE2ECFE7F77F86F6A73636F3E22
candidate SHA-256: 29072CE6C8788A6F096E79C4DA4E454795E38AE2ECFE7F77F86F6A73636F3E22
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1420984_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1420984_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1420984_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1421419
original SHA-256: A72DAE325F1961143DF099AA28FB0DDD468501003D3B54862DC3233EA34047C0
candidate SHA-256: A72DAE325F1961143DF099AA28FB0DDD468501003D3B54862DC3233EA34047C0
원문 frame 패킷: [1, 16]
최종 full_diff 패킷: [31, 31]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 31]
후보 중복만 있는 생략 가능 패킷: [17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421419_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421419_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421419_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421419_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421419_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421419_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421419_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421419_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421419_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421419_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421419_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421419_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421419_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421419_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421419_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421419_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421419_0031.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1421501
original SHA-256: E7F2F799BA47EE6A3C3CD4BAD0CDE0BEF727E2C8AF3B72821D39C24D1C6014AB
candidate SHA-256: E7F2F799BA47EE6A3C3CD4BAD0CDE0BEF727E2C8AF3B72821D39C24D1C6014AB
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421501_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421501_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421501_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421501_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421501_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1421990
original SHA-256: 31C5F73CF837D984E803D09AC8DF3BC49094811AE1DF576BF8B89694E2F0E2C3
candidate SHA-256: 31C5F73CF837D984E803D09AC8DF3BC49094811AE1DF576BF8B89694E2F0E2C3
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421990_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421990_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421990_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1423006
original SHA-256: 11705F70E14442B30509E667C5A359925CC375879B86BA2C69E802ABB6ACE220
candidate SHA-256: 11705F70E14442B30509E667C5A359925CC375879B86BA2C69E802ABB6ACE220
원문 frame 패킷: [1, 7]
최종 full_diff 패킷: [13, 13]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 13]
후보 중복만 있는 생략 가능 패킷: [8, 9, 10, 11, 12]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1423006_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1423006_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1423006_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1423006_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1423006_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1423006_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1423006_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1423006_0013.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

