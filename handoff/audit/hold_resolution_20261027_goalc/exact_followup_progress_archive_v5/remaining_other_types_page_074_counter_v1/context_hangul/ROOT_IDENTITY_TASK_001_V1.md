# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1009830
original SHA-256: 2CDFCEEE6526CAC6EF184CE52A0559ED22DB1B618AB72593030DEA16403BD94E
candidate SHA-256: 2CDFCEEE6526CAC6EF184CE52A0559ED22DB1B618AB72593030DEA16403BD94E
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1009830_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1009830_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1010171
original SHA-256: D9128CD3B7A20D14518B298987F04CDC622DB592F7D750218F0261C5263D50F3
candidate SHA-256: D9128CD3B7A20D14518B298987F04CDC622DB592F7D750218F0261C5263D50F3
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1010171_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1010718
original SHA-256: 6F75C8E23FE3CB356F8B6DED3C01CEB9731BB7B0BDF9F789711EEF0F568C6476
candidate SHA-256: 6F75C8E23FE3CB356F8B6DED3C01CEB9731BB7B0BDF9F789711EEF0F568C6476
원문 frame 패킷: [1, 15]
최종 full_diff 패킷: [30, 30]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 30]
후보 중복만 있는 생략 가능 패킷: [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1010718_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1010718_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1010718_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1010718_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1010718_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1010718_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1010718_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1010718_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1010718_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1010718_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1010718_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1010718_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1010718_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1010718_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1010718_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_074_counter_v1/reading_packets_v1/expanded_train_1010718_0030.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1011652
original SHA-256: 7AF2D1F43467864D5F1D13D10038F2AF89C2F634244864F2F7957B8E7F1EC6FC
candidate SHA-256: 28FDB923B45CC240E9BE054B2323884A91EE7DF85B604E8B74DE40466A3259A7
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1011654
original SHA-256: D26A618EC148EBA72C7FB2B058D17770EE3ABB923FBAE034B50B42504D4A96A5
candidate SHA-256: 951C079EA345DD34F4D4CC744E9EB1D2A59AD572412087C06E83E4FA8E65181B
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

