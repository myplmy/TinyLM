# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:100043
original SHA-256: 21A7D4DE6DC42EE83F24357DC04EAFC16E040224FB7D7ED344BFF31C05506B57
candidate SHA-256: AE29706D4A384503A532F94DAF75575C73A30D970352A5EAA5A4440DF212E43B
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:100147
original SHA-256: 1437BF431A280E76BEA98672A29C6BE84D404B159FD5B78CE1E8CC0E8C50AFE8
candidate SHA-256: 1437BF431A280E76BEA98672A29C6BE84D404B159FD5B78CE1E8CC0E8C50AFE8
원문 frame 패킷: [1, 20]
최종 full_diff 패킷: [40, 40]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 40]
후보 중복만 있는 생략 가능 패킷: [21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100147_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100147_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100147_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100147_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100147_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100147_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100147_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100147_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100147_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100147_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100147_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100147_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100147_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100147_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100147_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100147_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100147_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100147_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100147_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100147_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100147_0040.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:100193
original SHA-256: D192D0C35B4E6B40A5891775464ED64AB9EA469B12AAD260267E0007CB1F6DB7
candidate SHA-256: D192D0C35B4E6B40A5891775464ED64AB9EA469B12AAD260267E0007CB1F6DB7
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100193_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:100205
original SHA-256: 55676E6D2DA03D00D35D23CE05BD65B3790B7766EB65180C13576E4E06F4AE63
candidate SHA-256: 30D47400B9DA0E5A63AE8FDA5BDBCF461D55E9B386A9FFF44960EB606B7D9317
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:100537
original SHA-256: E2A134CECC0C025B0DF42FCE57CAED6A36E233AC5046766917A92EB4526F91D2
candidate SHA-256: 4AFAADF1297E1BD757B8E4C16426F5C512F2436289C961739B5586E104054F0B
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

