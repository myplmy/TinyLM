# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:148756
original SHA-256: F4A69D88915BB2238E6708FC655647279009F1FE737EBA0F2193C9235F38652B
candidate SHA-256: F4A69D88915BB2238E6708FC655647279009F1FE737EBA0F2193C9235F38652B
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_148756_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_148756_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:148868
original SHA-256: EA75BB68B62CE30B646268F87E825F1A493E69AAB79F4DE9298585C11C82B685
candidate SHA-256: EA75BB68B62CE30B646268F87E825F1A493E69AAB79F4DE9298585C11C82B685
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_148868_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:149092
original SHA-256: 2E0CB54B8FEE45DDC82460D811477505800A2A4FFAF7543704F438E7E192F29F
candidate SHA-256: 2E0CB54B8FEE45DDC82460D811477505800A2A4FFAF7543704F438E7E192F29F
원문 frame 패킷: [1, 43]
최종 full_diff 패킷: [86, 86]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 86]
후보 중복만 있는 생략 가능 패킷: [44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0026.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0027.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0028.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0029.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0030.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0031.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0032.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0033.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0034.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0035.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0036.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0037.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0038.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0039.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0040.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0041.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0042.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0043.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149092_0086.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:149292
original SHA-256: 35A3AEDDD1B339DF9F636058A0A96337D9300BEAC870BCE43DBA26B1F3D3C959
candidate SHA-256: 35A3AEDDD1B339DF9F636058A0A96337D9300BEAC870BCE43DBA26B1F3D3C959
원문 frame 패킷: [1, 24]
최종 full_diff 패킷: [47, 47]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 47]
후보 중복만 있는 생략 가능 패킷: [25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149292_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149292_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149292_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149292_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149292_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149292_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149292_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149292_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149292_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149292_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149292_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149292_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149292_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149292_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149292_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149292_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149292_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149292_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149292_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149292_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149292_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149292_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149292_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149292_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149292_0047.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:149475
original SHA-256: CAAD227FAC9071B1C98E65FCB2E277A538929B122AD93A7F536A4F2423C98507
candidate SHA-256: 7744C81D9A98A35885CAED2A75B9479CC60B7AB3D74AA054533ED340C694E267
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

