# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1080401
original SHA-256: 7D2F2FD9C7444D4410302F666C6BEFCB85A539A6FCD0B1251BAAF2748125CD59
candidate SHA-256: 7D2F2FD9C7444D4410302F666C6BEFCB85A539A6FCD0B1251BAAF2748125CD59
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1080401_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1080448
original SHA-256: CAF99EC947E642F1A363228E41479E6FD43355C01CD5150EE7332A4FC625904A
candidate SHA-256: CAF99EC947E642F1A363228E41479E6FD43355C01CD5150EE7332A4FC625904A
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1080448_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1081100
original SHA-256: 17CA2F96F61C29C838B557BAE8E065243FB5F3894FBEA9A8FFD019584E7597BF
candidate SHA-256: E7985232286488EAA769E6CF5C6E681969E53CCF3CD43512F34DC1968A51C895
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1081149
original SHA-256: 1CCAC5B7420876EED4F5F8CF45FA20D1E0D42DC19E68A1C0F4015B248EDDCDF0
candidate SHA-256: 1CCAC5B7420876EED4F5F8CF45FA20D1E0D42DC19E68A1C0F4015B248EDDCDF0
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1081149_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1081149_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1081355
original SHA-256: 839CBB8D6A99498293113F390843CC2712C65AA07AFFE921C236E3DA521DFF16
candidate SHA-256: 839CBB8D6A99498293113F390843CC2712C65AA07AFFE921C236E3DA521DFF16
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1081355_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1081355_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1081355_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1081355_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1081355_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

