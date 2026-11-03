# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:593385
original SHA-256: 0B0C4065AD09DC57987507352908B1FF0F507C6ED9179F4B5ADA6581CD07E20A
candidate SHA-256: B71D931E2BE4F728DFEE697D671844F8577935084EF0B85A7BE4F558FE83BDB7
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:593548
original SHA-256: ED09059A9606DA706B575BBBF3F81068C3AD16E90EE9FEA6EDF1272E4BBD77B0
candidate SHA-256: D0FE5C58D71FF13BB4D63361D4E48CCF4690577CF975C010509B539BA740BA54
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:593669
original SHA-256: BBB23AA10E5688EE5763C60D44E44840AE51C349885EF771EFAFBDFBAAD19B3E
candidate SHA-256: 9855DCAC32408358B452F884EAAADEFFCBDBAEBE1D82C1B9D94D52AC335E0CF0
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:593819
original SHA-256: B2869D95F04469C0FC990C0D93EB03DDF8C26600015798AD13CCECDD8D122043
candidate SHA-256: B2869D95F04469C0FC990C0D93EB03DDF8C26600015798AD13CCECDD8D122043
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_047_counter_v1/reading_packets_v1/expanded_train_593819_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_047_counter_v1/reading_packets_v1/expanded_train_593819_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_047_counter_v1/reading_packets_v1/expanded_train_593819_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_047_counter_v1/reading_packets_v1/expanded_train_593819_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:594118
original SHA-256: 2D6FEF93C043C84B813B634D538AB35E3DB57343FCB2F288185CAF1A837479C6
candidate SHA-256: 2D6FEF93C043C84B813B634D538AB35E3DB57343FCB2F288185CAF1A837479C6
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [10, 10]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 10]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8, 9]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_047_counter_v1/reading_packets_v1/expanded_train_594118_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_047_counter_v1/reading_packets_v1/expanded_train_594118_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_047_counter_v1/reading_packets_v1/expanded_train_594118_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_047_counter_v1/reading_packets_v1/expanded_train_594118_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_047_counter_v1/reading_packets_v1/expanded_train_594118_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_047_counter_v1/reading_packets_v1/expanded_train_594118_0010.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

