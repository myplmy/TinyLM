# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1086473
original SHA-256: CC38C1069086614BD305DABC8E01EC68567F7957ED90F4802339CA7E9DCE9DB2
candidate SHA-256: 30D3FE0CB3199FFE6A0319A0AC5ADF185A5BE0AF4359A3ADF2365F8001A1B437
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1086764
original SHA-256: 4C82328C71BAB8EB14F80F5B1061234295826FCB1E5D85F8A703662741A656EF
candidate SHA-256: B99AFB8EBE7E56194511EFAE9F681FB6CEECD124B1A52AF5967ED4D084601BF9
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1086792
original SHA-256: 44216613F7BEAF8C1992A4284825ED81B3919688112DF2B106507E4F3372CBD3
candidate SHA-256: 197D45040A19C5AE7E16AE8C780B358B9D602C639227B4F96E802B31EA8DA5CA
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1086968
original SHA-256: 16755BFD79E70864EAB2838518BECD55FA0116EED3A582F758793CB7DBCADA58
candidate SHA-256: 16755BFD79E70864EAB2838518BECD55FA0116EED3A582F758793CB7DBCADA58
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [11, 11]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 11]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_079_counter_v1/reading_packets_v1/expanded_train_1086968_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_079_counter_v1/reading_packets_v1/expanded_train_1086968_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_079_counter_v1/reading_packets_v1/expanded_train_1086968_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_079_counter_v1/reading_packets_v1/expanded_train_1086968_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_079_counter_v1/reading_packets_v1/expanded_train_1086968_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_079_counter_v1/reading_packets_v1/expanded_train_1086968_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_079_counter_v1/reading_packets_v1/expanded_train_1086968_0011.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1087080
original SHA-256: FE94876BEE9F3A3B03FA46DB6E24851FED4F823DEA3CE32B9CB225AE80A1ABC8
candidate SHA-256: FE94876BEE9F3A3B03FA46DB6E24851FED4F823DEA3CE32B9CB225AE80A1ABC8
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_079_counter_v1/reading_packets_v1/expanded_train_1087080_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_079_counter_v1/reading_packets_v1/expanded_train_1087080_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_079_counter_v1/reading_packets_v1/expanded_train_1087080_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_079_counter_v1/reading_packets_v1/expanded_train_1087080_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_079_counter_v1/reading_packets_v1/expanded_train_1087080_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

