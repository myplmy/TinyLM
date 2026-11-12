# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:453144
original SHA-256: 21BDC09E2BBC344DADE2F2C55A7F377C95B6EA2FD548CFC63D20768C10A48928
candidate SHA-256: AE355DC830F7FFA40ECC20D5060BCB3ADE18E71908D754A6A1424913CDDA6660
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:453380
original SHA-256: CA05C29673284DEF8D0810F87C9748E5603C4EEBF931F731A8E199E5FA568843
candidate SHA-256: CA05C29673284DEF8D0810F87C9748E5603C4EEBF931F731A8E199E5FA568843
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_017_counter_v1/reading_packets_v1/expanded_train_453380_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:453774
original SHA-256: 9D580D36C62FF41BA7DBE8A30635AE94ABFD3924AA921C9226E618F92FC9F333
candidate SHA-256: BCE076B934F6565FDB4C947EC34638E87DA18473E5C02B518077D4B2484D1B0A
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:454251
original SHA-256: C2723C87C4FCC56A88039D8A6D78B1C8CD7A33EA2750558A155D20F70D944E00
candidate SHA-256: C2723C87C4FCC56A88039D8A6D78B1C8CD7A33EA2750558A155D20F70D944E00
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_017_counter_v1/reading_packets_v1/expanded_train_454251_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:455097
original SHA-256: E2CC1E9491AC19E7CCAEDFCF02E0A08CF72BBCFB10458805F45704DB6823FCAC
candidate SHA-256: E2CC1E9491AC19E7CCAEDFCF02E0A08CF72BBCFB10458805F45704DB6823FCAC
원문 frame 패킷: [1, 13]
최종 full_diff 패킷: [26, 26]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 26]
후보 중복만 있는 생략 가능 패킷: [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_017_counter_v1/reading_packets_v1/expanded_train_455097_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_017_counter_v1/reading_packets_v1/expanded_train_455097_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_017_counter_v1/reading_packets_v1/expanded_train_455097_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_017_counter_v1/reading_packets_v1/expanded_train_455097_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_017_counter_v1/reading_packets_v1/expanded_train_455097_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_017_counter_v1/reading_packets_v1/expanded_train_455097_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_017_counter_v1/reading_packets_v1/expanded_train_455097_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_017_counter_v1/reading_packets_v1/expanded_train_455097_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_017_counter_v1/reading_packets_v1/expanded_train_455097_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_017_counter_v1/reading_packets_v1/expanded_train_455097_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_017_counter_v1/reading_packets_v1/expanded_train_455097_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_017_counter_v1/reading_packets_v1/expanded_train_455097_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_017_counter_v1/reading_packets_v1/expanded_train_455097_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_017_counter_v1/reading_packets_v1/expanded_train_455097_0026.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

