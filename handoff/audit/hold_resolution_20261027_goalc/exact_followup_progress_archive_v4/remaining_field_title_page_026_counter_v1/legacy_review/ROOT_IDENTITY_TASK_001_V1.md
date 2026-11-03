# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:830104
original SHA-256: E8A064DA8FCD8192F52EFFA7CAB1723906ECF8DDFCD04EE95C37B33DC10B03E3
candidate SHA-256: E8A064DA8FCD8192F52EFFA7CAB1723906ECF8DDFCD04EE95C37B33DC10B03E3
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_830104_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:831535
original SHA-256: A444404ED918B37F376E69C9F42C65DCA02676B414149AC1CEED4F4EE45B18F5
candidate SHA-256: A444404ED918B37F376E69C9F42C65DCA02676B414149AC1CEED4F4EE45B18F5
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_831535_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:831873
original SHA-256: 467D31E5B023678C8E658D59335DE058BDC250D4A3C216C89546070F4A8C81E6
candidate SHA-256: 467D31E5B023678C8E658D59335DE058BDC250D4A3C216C89546070F4A8C81E6
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_831873_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_831873_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:832475
original SHA-256: 221F11BE9272BC8D809FE69BBD2CB2846C722A26DF1D0AFAD541E91050A95278
candidate SHA-256: 221F11BE9272BC8D809FE69BBD2CB2846C722A26DF1D0AFAD541E91050A95278
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_832475_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_832475_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:832550
original SHA-256: 4A9D75EF5DDCAFCC9662AE02676C4738E10B6600543FDCC1826CEB5C8A19FC72
candidate SHA-256: 4A9D75EF5DDCAFCC9662AE02676C4738E10B6600543FDCC1826CEB5C8A19FC72
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_832550_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_832550_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_832550_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_832550_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_832550_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

