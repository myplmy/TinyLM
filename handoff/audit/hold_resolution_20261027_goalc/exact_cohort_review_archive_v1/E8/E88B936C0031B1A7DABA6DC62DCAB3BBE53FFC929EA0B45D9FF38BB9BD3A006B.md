# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:112247
original SHA-256: C9371225C53E0D7F36763956D0B416C51FF16F56B8F25049893FD364A0459A5F
candidate SHA-256: 8C08F1AD9D45ABB7D2B8A6557697D16FAC4AEE6936115BCFC613C13BD8F1E9D7
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:112270
original SHA-256: 84AB64270E4BB6C94ABAE3A708F5B0C54DC5D89735F66B3A2B61D369F100ADCE
candidate SHA-256: 84AB64270E4BB6C94ABAE3A708F5B0C54DC5D89735F66B3A2B61D369F100ADCE
원문 frame 패킷: [1, 10]
최종 full_diff 패킷: [19, 19]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 19]
후보 중복만 있는 생략 가능 패킷: [11, 12, 13, 14, 15, 16, 17, 18]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_008_counter_v1/reading_packets_v1/expanded_train_112270_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_008_counter_v1/reading_packets_v1/expanded_train_112270_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_008_counter_v1/reading_packets_v1/expanded_train_112270_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_008_counter_v1/reading_packets_v1/expanded_train_112270_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_008_counter_v1/reading_packets_v1/expanded_train_112270_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_008_counter_v1/reading_packets_v1/expanded_train_112270_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_008_counter_v1/reading_packets_v1/expanded_train_112270_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_008_counter_v1/reading_packets_v1/expanded_train_112270_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_008_counter_v1/reading_packets_v1/expanded_train_112270_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_008_counter_v1/reading_packets_v1/expanded_train_112270_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_008_counter_v1/reading_packets_v1/expanded_train_112270_0019.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:112336
original SHA-256: 13706AD37B9126CC332BA80F7279B685EF3BBDE2AE139296D859DFB183251344
candidate SHA-256: D03665AEDE78B3D5F82B479050DF6C90D006121325D945265A5A57EA8C9C65D7
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:112888
original SHA-256: CDEA53F9B1111AAEAAC05D81DDFD66F3E1F4A9EB1DCA4C00C75F4AEB707B7771
candidate SHA-256: CDEA53F9B1111AAEAAC05D81DDFD66F3E1F4A9EB1DCA4C00C75F4AEB707B7771
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_008_counter_v1/reading_packets_v1/expanded_train_112888_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_008_counter_v1/reading_packets_v1/expanded_train_112888_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:112989
original SHA-256: 8ACE5876F2023EA0CB0B813DD61E6446D15CA68B3C6F3D86CB8761DD01D49570
candidate SHA-256: 50D119F4791406226BFA214665E6DCE33BCF08D90E1D2FE29265BDCAAC6C5A4C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

