# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:913355
original SHA-256: DB99687EE90B103836B94E555C74D63DB1723365CB379DF3519835566A1A58EA
candidate SHA-256: DB99687EE90B103836B94E555C74D63DB1723365CB379DF3519835566A1A58EA
원문 frame 패킷: [1, 20]
최종 full_diff 패킷: [39, 39]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 39]
후보 중복만 있는 생략 가능 패킷: [21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913355_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913355_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913355_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913355_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913355_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913355_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913355_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913355_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913355_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913355_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913355_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913355_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913355_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913355_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913355_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913355_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913355_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913355_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913355_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913355_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913355_0039.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:913710
original SHA-256: 43B7E5F8200A40E41C71AD6DD31A29DF4B96D0BC9BFE5D06C4FEA094D726E832
candidate SHA-256: 43B7E5F8200A40E41C71AD6DD31A29DF4B96D0BC9BFE5D06C4FEA094D726E832
원문 frame 패킷: [1, 57]
최종 full_diff 패킷: [114, 114]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 114]
후보 중복만 있는 생략 가능 패킷: [58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0026.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0027.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0028.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0029.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0030.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0031.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0032.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0033.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0034.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0035.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0036.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0037.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0038.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0039.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0040.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0041.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0042.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0043.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0044.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0045.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0046.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0047.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0048.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0049.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0050.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0051.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0052.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0053.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0054.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0055.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0056.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0057.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913710_0114.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:913857
original SHA-256: 96664B1BD41116D82576D59ACBAFB58FC1E1546EEB8C8C0EE9B60040C75B12FA
candidate SHA-256: 96664B1BD41116D82576D59ACBAFB58FC1E1546EEB8C8C0EE9B60040C75B12FA
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913857_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913857_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913857_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913857_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913857_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:913871
original SHA-256: A25A0A69459456B20B4F07D27972DF7CAA7DB520A87E1AA2682CF41A5E8EEDF0
candidate SHA-256: A25A0A69459456B20B4F07D27972DF7CAA7DB520A87E1AA2682CF41A5E8EEDF0
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [12, 12]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 12]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10, 11]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913871_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913871_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913871_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913871_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913871_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913871_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913871_0012.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:913922
original SHA-256: AE6951E846AE6D4FBF549BC4DF164E326FF14E5E5C5C591806925CE0A898AA5E
candidate SHA-256: AE6951E846AE6D4FBF549BC4DF164E326FF14E5E5C5C591806925CE0A898AA5E
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913922_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913922_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913922_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_913922_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

