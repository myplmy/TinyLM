# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1060677
original SHA-256: C622462455F6145C230D451E864DCBDAD15F39BEFA70F4B976AC83B03CED9058
candidate SHA-256: C622462455F6145C230D451E864DCBDAD15F39BEFA70F4B976AC83B03CED9058
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060677_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060677_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060677_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1060837
original SHA-256: 9BE34D8F3CCC54447E1E5924D8B93EA2F865F3FE53EF27012A231EA245611EC4
candidate SHA-256: 9BE34D8F3CCC54447E1E5924D8B93EA2F865F3FE53EF27012A231EA245611EC4
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060837_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060837_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1060848
original SHA-256: 42A10A908CA7BC360AE3C730B91654EA8883C4E7C7F995F2C6B81CCBBFB49918
candidate SHA-256: 42A10A908CA7BC360AE3C730B91654EA8883C4E7C7F995F2C6B81CCBBFB49918
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060848_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060848_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060848_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1060880
original SHA-256: 79B80EC2A1B5F9801A9A842DE2598277BEC332BD190AF04CF94480EE0079F702
candidate SHA-256: 79B80EC2A1B5F9801A9A842DE2598277BEC332BD190AF04CF94480EE0079F702
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060880_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060880_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060880_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060880_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1060927
original SHA-256: 333EA4B806E225642E297E859974E62AA1F1AFB1355CDF6C12C6E2849E688D34
candidate SHA-256: FCEF654B603CFC3AD1BEEDBAE4984D1B720A0293804128C1F463EA3278D85568
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

