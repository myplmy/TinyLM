# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:243306
original SHA-256: E11367D98DD54CFBF36B13A43A2B3C313A27566B58DDCF1DDF8F6267183693DB
candidate SHA-256: E11367D98DD54CFBF36B13A43A2B3C313A27566B58DDCF1DDF8F6267183693DB
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_243306_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:243339
original SHA-256: 9A0BD1CFB3ECBF204CDA02E556BF660B749CC2B58F5DB18846F7B0CE942A8929
candidate SHA-256: 9A0BD1CFB3ECBF204CDA02E556BF660B749CC2B58F5DB18846F7B0CE942A8929
원문 frame 패킷: [1, 15]
최종 full_diff 패킷: [29, 29]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 29]
후보 중복만 있는 생략 가능 패킷: [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_243339_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_243339_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_243339_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_243339_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_243339_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_243339_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_243339_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_243339_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_243339_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_243339_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_243339_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_243339_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_243339_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_243339_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_243339_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_243339_0029.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:243854
original SHA-256: 8A17DA151C349A609C6403E05087890B51DEE56862C1D039E3D53E30C82FA74C
candidate SHA-256: DC1B507E595649D3841BC77F84AE4F34C2AF1AD310978162B7C732D09BC69F25
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:243926
original SHA-256: 6252EBA62CE92DACCD361250ADA57DBE9EE669CE213E4595568E187A206C1B4E
candidate SHA-256: 6252EBA62CE92DACCD361250ADA57DBE9EE669CE213E4595568E187A206C1B4E
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_243926_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_243926_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_243926_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:244039
original SHA-256: 2BF152519046736F70ED265B9335853D77FF23D523045D501D8A9D61AED26292
candidate SHA-256: 2BF152519046736F70ED265B9335853D77FF23D523045D501D8A9D61AED26292
원문 frame 패킷: [1, 31]
최종 full_diff 패킷: [62, 62]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 62]
후보 중복만 있는 생략 가능 패킷: [32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_244039_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_244039_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_244039_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_244039_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_244039_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_244039_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_244039_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_244039_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_244039_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_244039_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_244039_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_244039_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_244039_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_244039_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_244039_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_244039_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_244039_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_244039_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_244039_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_244039_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_244039_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_244039_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_244039_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_244039_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_244039_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_244039_0026.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_244039_0027.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_244039_0028.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_244039_0029.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_244039_0030.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_244039_0031.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_244039_0062.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

