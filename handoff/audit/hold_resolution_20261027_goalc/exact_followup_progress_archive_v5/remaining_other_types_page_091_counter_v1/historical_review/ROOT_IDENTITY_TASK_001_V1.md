# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1284221
original SHA-256: 2356C1413B9B5F1D96390397BBC70C51E7900353D27DBBE2E14DA8A080B01EEE
candidate SHA-256: 2356C1413B9B5F1D96390397BBC70C51E7900353D27DBBE2E14DA8A080B01EEE
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284221_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284221_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284221_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284221_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1284246
original SHA-256: 4F29289DAE7BC64258EADFC60853A1D1D791F7AE9AD30695000DAB77376C08EB
candidate SHA-256: 4F29289DAE7BC64258EADFC60853A1D1D791F7AE9AD30695000DAB77376C08EB
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [10, 10]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 10]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8, 9]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284246_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284246_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284246_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284246_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284246_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284246_0010.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1284342
original SHA-256: 6FD79705465909CED526CBAEE3BA259A3E8A07D67E38E7D58D72C24A82911B2E
candidate SHA-256: 6FD79705465909CED526CBAEE3BA259A3E8A07D67E38E7D58D72C24A82911B2E
원문 frame 패킷: [1, 33]
최종 full_diff 패킷: [65, 65]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 65]
후보 중복만 있는 생략 가능 패킷: [34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284342_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284342_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284342_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284342_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284342_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284342_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284342_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284342_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284342_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284342_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284342_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284342_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284342_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284342_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284342_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284342_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284342_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284342_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284342_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284342_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284342_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284342_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284342_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284342_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284342_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284342_0026.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284342_0027.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284342_0028.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284342_0029.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284342_0030.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284342_0031.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284342_0032.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284342_0033.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284342_0065.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1284437
original SHA-256: 07D061EC5F359F5D170C821454B5A83841B4101424E4FEBD7B21B279226E5159
candidate SHA-256: 07D061EC5F359F5D170C821454B5A83841B4101424E4FEBD7B21B279226E5159
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [11, 11]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 11]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284437_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284437_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284437_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284437_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284437_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284437_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284437_0011.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1284510
original SHA-256: 20158F1141B3F295027F59A37E32EA86B06A0E419BC4BFC2631E5A3C0932A9D0
candidate SHA-256: 20158F1141B3F295027F59A37E32EA86B06A0E419BC4BFC2631E5A3C0932A9D0
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284510_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284510_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_091_counter_v1/reading_packets_v1/expanded_train_1284510_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

