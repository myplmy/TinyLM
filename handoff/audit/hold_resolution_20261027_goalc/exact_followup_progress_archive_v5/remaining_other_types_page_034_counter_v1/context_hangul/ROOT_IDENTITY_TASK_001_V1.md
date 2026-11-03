# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:403960
original SHA-256: 321C64A1210CDD3F8D3234D67B201148ADA3D55B490FD8574B8AC7B390B4F465
candidate SHA-256: 321C64A1210CDD3F8D3234D67B201148ADA3D55B490FD8574B8AC7B390B4F465
원문 frame 패킷: [1, 37]
최종 full_diff 패킷: [74, 75]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 74, 75]
후보 중복만 있는 생략 가능 패킷: [38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_403960_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_403960_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_403960_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_403960_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_403960_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_403960_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_403960_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_403960_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_403960_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_403960_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_403960_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_403960_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_403960_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_403960_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_403960_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_403960_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_403960_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_403960_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_403960_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_403960_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_403960_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_403960_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_403960_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_403960_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_403960_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_403960_0026.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_403960_0027.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_403960_0028.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_403960_0029.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_403960_0030.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_403960_0031.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_403960_0032.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_403960_0033.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_403960_0034.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_403960_0035.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_403960_0036.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_403960_0037.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_403960_0074.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_403960_0075.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:404248
original SHA-256: FB405832E463A2C23578C86660631BCF152D651A9DDA036168280F8451A4B1E3
candidate SHA-256: 09493195B9898989737DEFFCD7C51B1E00AED1CB761FBA6C31DE3511CEEE5453
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:404444
original SHA-256: 4218B7420995CF37B458C18DDD3AF2A90314260F3653E17D5F497447BB99F82A
candidate SHA-256: 4218B7420995CF37B458C18DDD3AF2A90314260F3653E17D5F497447BB99F82A
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [9, 9]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 9]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_404444_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_404444_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_404444_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_404444_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_404444_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_404444_0009.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:404684
original SHA-256: F60CA6858C83B07F37813F5B7A7D958D3586D61B766B687D09BE7223A42198D2
candidate SHA-256: F60CA6858C83B07F37813F5B7A7D958D3586D61B766B687D09BE7223A42198D2
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_404684_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:404791
original SHA-256: 98E3B5947829C0206A11E4C60BBC8CE8D8851E17D21F7AC5A10795B39DE794CF
candidate SHA-256: 98E3B5947829C0206A11E4C60BBC8CE8D8851E17D21F7AC5A10795B39DE794CF
원문 frame 패킷: [1, 15]
최종 full_diff 패킷: [29, 29]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 29]
후보 중복만 있는 생략 가능 패킷: [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_404791_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_404791_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_404791_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_404791_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_404791_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_404791_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_404791_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_404791_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_404791_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_404791_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_404791_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_404791_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_404791_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_404791_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_404791_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_404791_0029.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

