# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1252694
original SHA-256: F7FFFC522678C5C250C26199EF09B22BBF0F68F3E2024BEDC50D3440E4A700E3
candidate SHA-256: 6484ED3F40D9119982A987FAF2611251E1AF0D8A10FBDB73504976702E6D86E0
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1252765
original SHA-256: 5B7A7D78E4D209FA659FA06B4400D36ACA0C035B018F30FA8465BCAA27D634B5
candidate SHA-256: 5B7A7D78E4D209FA659FA06B4400D36ACA0C035B018F30FA8465BCAA27D634B5
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_089_counter_v1/reading_packets_v1/expanded_train_1252765_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_089_counter_v1/reading_packets_v1/expanded_train_1252765_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_089_counter_v1/reading_packets_v1/expanded_train_1252765_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1252803
original SHA-256: BFB1CE608226ACAAE9F72614B14F116AE16DAE45A3ADA8D1BC3F611555C540C0
candidate SHA-256: BFB1CE608226ACAAE9F72614B14F116AE16DAE45A3ADA8D1BC3F611555C540C0
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_089_counter_v1/reading_packets_v1/expanded_train_1252803_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_089_counter_v1/reading_packets_v1/expanded_train_1252803_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_089_counter_v1/reading_packets_v1/expanded_train_1252803_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_089_counter_v1/reading_packets_v1/expanded_train_1252803_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1253166
original SHA-256: 42E51CF95F2F15A628A4B05BF24E8FA6AC943CDAFCFF83FAC939F4F20A0FB59A
candidate SHA-256: 42E51CF95F2F15A628A4B05BF24E8FA6AC943CDAFCFF83FAC939F4F20A0FB59A
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_089_counter_v1/reading_packets_v1/expanded_train_1253166_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_089_counter_v1/reading_packets_v1/expanded_train_1253166_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_089_counter_v1/reading_packets_v1/expanded_train_1253166_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_089_counter_v1/reading_packets_v1/expanded_train_1253166_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1253212
original SHA-256: 4C99D6B0886FAFF0B269D22B0123991FD9E0422A24A1B8883EE995CB928B330E
candidate SHA-256: 4C99D6B0886FAFF0B269D22B0123991FD9E0422A24A1B8883EE995CB928B330E
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_089_counter_v1/reading_packets_v1/expanded_train_1253212_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

