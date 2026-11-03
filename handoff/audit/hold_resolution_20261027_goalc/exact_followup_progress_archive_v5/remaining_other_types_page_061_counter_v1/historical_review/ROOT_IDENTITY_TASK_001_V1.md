# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:792302
original SHA-256: 6C0C028701AB80AE1253D2DD4E811713A45DDF395981934F940ABC4059825FC4
candidate SHA-256: 6F9E240E9847F00FF55B640AB5733CDA9AE3F9DC74187DAD3BF04EE7B659A03E
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:792666
original SHA-256: C3AEF85409689273B875EB6CD50F8216976AED4D4A9D4623680046E935C08D43
candidate SHA-256: 9E48F930C7E05C66273E25A3975233B768B11633054F597D0020F371B2D094E3
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:792682
original SHA-256: BE8187A8814DE504AF4EDBF9D9859EC9EA13CD06802674C77A1A45623F204871
candidate SHA-256: BE8187A8814DE504AF4EDBF9D9859EC9EA13CD06802674C77A1A45623F204871
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_792682_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:792951
original SHA-256: 3E49C141A124709B6E37B010352714A5966C3E140A23072E2A6F818B0401F56B
candidate SHA-256: 4BDE20B76756BDAAD4823E17F606E881193896C8947558C169172EE02E6AC65D
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:793003
original SHA-256: FC3E169A388C8AF016064D934A8A9A607E836D4B032A65DA97235AAEB7FDA576
candidate SHA-256: FC3E169A388C8AF016064D934A8A9A607E836D4B032A65DA97235AAEB7FDA576
원문 frame 패킷: [1, 33]
최종 full_diff 패킷: [65, 65]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 65]
후보 중복만 있는 생략 가능 패킷: [34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_793003_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_793003_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_793003_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_793003_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_793003_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_793003_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_793003_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_793003_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_793003_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_793003_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_793003_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_793003_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_793003_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_793003_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_793003_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_793003_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_793003_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_793003_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_793003_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_793003_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_793003_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_793003_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_793003_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_793003_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_793003_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_793003_0026.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_793003_0027.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_793003_0028.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_793003_0029.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_793003_0030.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_793003_0031.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_793003_0032.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_793003_0033.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_793003_0065.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

