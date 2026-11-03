# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:814352
original SHA-256: 5868CA2C24804D2D8B53CEF4DB5AE61310FCB55D328C2A7D13C9078872A55A9C
candidate SHA-256: 5868CA2C24804D2D8B53CEF4DB5AE61310FCB55D328C2A7D13C9078872A55A9C
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_063_counter_v1/reading_packets_v1/expanded_train_814352_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:814376
original SHA-256: EDA47443853CB222FC02D6392FE5D8205D1D60D9DC12FFD90C64EC35F4646BDC
candidate SHA-256: EDA47443853CB222FC02D6392FE5D8205D1D60D9DC12FFD90C64EC35F4646BDC
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_063_counter_v1/reading_packets_v1/expanded_train_814376_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:814457
original SHA-256: D60CA9B46C7769E2D896D2A09CD1F37D7921EF37AF8A8D7D260770E6FD292D0F
candidate SHA-256: D60CA9B46C7769E2D896D2A09CD1F37D7921EF37AF8A8D7D260770E6FD292D0F
원문 frame 패킷: [1, 14]
최종 full_diff 패킷: [27, 27]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 27]
후보 중복만 있는 생략 가능 패킷: [15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_063_counter_v1/reading_packets_v1/expanded_train_814457_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_063_counter_v1/reading_packets_v1/expanded_train_814457_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_063_counter_v1/reading_packets_v1/expanded_train_814457_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_063_counter_v1/reading_packets_v1/expanded_train_814457_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_063_counter_v1/reading_packets_v1/expanded_train_814457_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_063_counter_v1/reading_packets_v1/expanded_train_814457_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_063_counter_v1/reading_packets_v1/expanded_train_814457_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_063_counter_v1/reading_packets_v1/expanded_train_814457_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_063_counter_v1/reading_packets_v1/expanded_train_814457_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_063_counter_v1/reading_packets_v1/expanded_train_814457_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_063_counter_v1/reading_packets_v1/expanded_train_814457_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_063_counter_v1/reading_packets_v1/expanded_train_814457_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_063_counter_v1/reading_packets_v1/expanded_train_814457_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_063_counter_v1/reading_packets_v1/expanded_train_814457_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_063_counter_v1/reading_packets_v1/expanded_train_814457_0027.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:814465
original SHA-256: 8653E3310438DB72B2EAD6D48C42012A0BB6B5EE7E354B750FBC3DF777CB0FC0
candidate SHA-256: 26DC6849D9B03CE764070B7DCCA6873F3F7E71CDACF4C05BE2F057B7A4A9E36D
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:814830
original SHA-256: C212965C0411355E8D1A7C9E7E2D8FE7816616AC8200BC001763CCEF5C8BF3D4
candidate SHA-256: C212965C0411355E8D1A7C9E7E2D8FE7816616AC8200BC001763CCEF5C8BF3D4
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_063_counter_v1/reading_packets_v1/expanded_train_814830_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

