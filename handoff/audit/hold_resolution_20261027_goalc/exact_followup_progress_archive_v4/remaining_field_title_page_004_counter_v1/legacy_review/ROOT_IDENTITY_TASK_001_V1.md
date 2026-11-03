# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:28703
original SHA-256: E87B987EC05D45010BA089F6BDCA351A0963A1086267E3570060C90F2A21E0C5
candidate SHA-256: 273309B8A8CEFC1E727E015AA56E24373F94ED4F1ECE2139534627411940A854
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:29006
original SHA-256: F62089755FB6CAEA932D70633B093AD0C0B8EAFB15A098B2BAAEA6B6D46763C6
candidate SHA-256: F62089755FB6CAEA932D70633B093AD0C0B8EAFB15A098B2BAAEA6B6D46763C6
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_004_counter_v1/reading_packets_v1/expanded_train_29006_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_004_counter_v1/reading_packets_v1/expanded_train_29006_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:29112
original SHA-256: D8A372F61FC58518208A1CC2C5660136C8FAC3E5E67F5D83390C7A1FE527AA8D
candidate SHA-256: D8A372F61FC58518208A1CC2C5660136C8FAC3E5E67F5D83390C7A1FE527AA8D
원문 frame 패킷: [1, 16]
최종 full_diff 패킷: [32, 32]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 32]
후보 중복만 있는 생략 가능 패킷: [17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_004_counter_v1/reading_packets_v1/expanded_train_29112_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_004_counter_v1/reading_packets_v1/expanded_train_29112_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_004_counter_v1/reading_packets_v1/expanded_train_29112_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_004_counter_v1/reading_packets_v1/expanded_train_29112_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_004_counter_v1/reading_packets_v1/expanded_train_29112_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_004_counter_v1/reading_packets_v1/expanded_train_29112_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_004_counter_v1/reading_packets_v1/expanded_train_29112_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_004_counter_v1/reading_packets_v1/expanded_train_29112_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_004_counter_v1/reading_packets_v1/expanded_train_29112_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_004_counter_v1/reading_packets_v1/expanded_train_29112_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_004_counter_v1/reading_packets_v1/expanded_train_29112_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_004_counter_v1/reading_packets_v1/expanded_train_29112_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_004_counter_v1/reading_packets_v1/expanded_train_29112_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_004_counter_v1/reading_packets_v1/expanded_train_29112_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_004_counter_v1/reading_packets_v1/expanded_train_29112_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_004_counter_v1/reading_packets_v1/expanded_train_29112_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_004_counter_v1/reading_packets_v1/expanded_train_29112_0032.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:29376
original SHA-256: 86D378036C65D70A5157F6875574C0687DB5609FE169FB7DDA24B59FC7FB0E57
candidate SHA-256: 86D378036C65D70A5157F6875574C0687DB5609FE169FB7DDA24B59FC7FB0E57
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_004_counter_v1/reading_packets_v1/expanded_train_29376_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:29412
original SHA-256: 2C2552EA804FB2E69773C3609F6A8EEF62BE912E50C5C8B1A200C990014BA1E4
candidate SHA-256: 2C2552EA804FB2E69773C3609F6A8EEF62BE912E50C5C8B1A200C990014BA1E4
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_004_counter_v1/reading_packets_v1/expanded_train_29412_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

