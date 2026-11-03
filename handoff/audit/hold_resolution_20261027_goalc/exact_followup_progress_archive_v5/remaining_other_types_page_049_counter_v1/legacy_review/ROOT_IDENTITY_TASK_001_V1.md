# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:621915
original SHA-256: C880C1C48F7D86855D79F20A5AE7B13123B285A162B5E8AA03CB2689D5B9BC44
candidate SHA-256: C880C1C48F7D86855D79F20A5AE7B13123B285A162B5E8AA03CB2689D5B9BC44
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_621915_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_621915_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_621915_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_621915_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:621977
original SHA-256: D27F958F77953EB371C32916FF82929219F0A147C59D0126E695B956D530044C
candidate SHA-256: D27F958F77953EB371C32916FF82929219F0A147C59D0126E695B956D530044C
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_621977_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_621977_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_621977_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:622018
original SHA-256: 41B530D50D617E8C250A4E2992BF20A418082E758802F2B176DEA9FE0E32E3AD
candidate SHA-256: CD3C25E78544A7BF542D1AD1665964EEABE2F9DEBDDDD97CEF898E2D5B22C688
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:622322
original SHA-256: 88BDC3C97C9CC4D5013D4B52E48F57A6406BB6ADEE5D6384C3BD7B4F06988E2B
candidate SHA-256: 57B9AE353AAD95E7C59A0C284443C8A7BCCBCC090A1FACD6C6E084394BBE5D45
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:622416
original SHA-256: D0A486F5C360B388A019C454B15AEBB2B494CD374AE799BDBE328072B1B77588
candidate SHA-256: D0A486F5C360B388A019C454B15AEBB2B494CD374AE799BDBE328072B1B77588
원문 frame 패킷: [1, 8]
최종 full_diff 패킷: [15, 15]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 15]
후보 중복만 있는 생략 가능 패킷: [9, 10, 11, 12, 13, 14]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622416_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622416_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622416_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622416_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622416_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622416_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622416_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622416_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_049_counter_v1/reading_packets_v1/expanded_train_622416_0015.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

