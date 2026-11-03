# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:678203
original SHA-256: AA266E7F16CFB1C0868EA4A4522433CD73A968FF407246CCE60BE5A80DA8CDAB
candidate SHA-256: AA266E7F16CFB1C0868EA4A4522433CD73A968FF407246CCE60BE5A80DA8CDAB
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [11, 11]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 11]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678203_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678203_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678203_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678203_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678203_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678203_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678203_0011.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:678239
original SHA-256: 37B035322FD698CBA6AC447D07729074751D27650E589CD85C4EBD73CC23276E
candidate SHA-256: 37B035322FD698CBA6AC447D07729074751D27650E589CD85C4EBD73CC23276E
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678239_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678239_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:678499
original SHA-256: 6F0BD2FDC3D4663A1DF9A5E56258DEEF29EDEDCF3A7AE0CBABF98D30A30F84BF
candidate SHA-256: 6F0BD2FDC3D4663A1DF9A5E56258DEEF29EDEDCF3A7AE0CBABF98D30A30F84BF
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678499_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678499_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:678788
original SHA-256: 50C15AAD15E76D7640B43B152B0253332F22CCA5C3D28D8B0FB0039E5EEC431D
candidate SHA-256: 50C15AAD15E76D7640B43B152B0253332F22CCA5C3D28D8B0FB0039E5EEC431D
원문 frame 패킷: [1, 34]
최종 full_diff 패킷: [68, 68]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 68]
후보 중복만 있는 생략 가능 패킷: [35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678788_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678788_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678788_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678788_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678788_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678788_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678788_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678788_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678788_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678788_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678788_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678788_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678788_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678788_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678788_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678788_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678788_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678788_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678788_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678788_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678788_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678788_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678788_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678788_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678788_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678788_0026.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678788_0027.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678788_0028.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678788_0029.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678788_0030.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678788_0031.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678788_0032.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678788_0033.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678788_0034.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678788_0068.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:678895
original SHA-256: 715A3E9F0850A6B5A4B6E5E4D2479560D44562338B845AAAB951C93AC655E428
candidate SHA-256: 715A3E9F0850A6B5A4B6E5E4D2479560D44562338B845AAAB951C93AC655E428
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_053_counter_v1/reading_packets_v1/expanded_train_678895_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

