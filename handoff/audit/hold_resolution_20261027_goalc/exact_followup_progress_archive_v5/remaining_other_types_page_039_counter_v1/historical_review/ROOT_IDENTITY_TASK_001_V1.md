# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:474490
original SHA-256: 1CF33AE5976C4F82B745F04F914273258F6409D92C6DE681D3C7C902A7BFEE1A
candidate SHA-256: DC41ACC8A9D822B7159A7C59BAB79ED7A49BCBDAC06D3A2745A71012B009C493
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:474719
original SHA-256: D8D349484EC7754428AB3D4EEE26CA34C1C72E5F732D2F5BECCE488DF1B77DA2
candidate SHA-256: D8D349484EC7754428AB3D4EEE26CA34C1C72E5F732D2F5BECCE488DF1B77DA2
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474719_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474719_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474719_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474719_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474719_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:474801
original SHA-256: B36921751ED008F69CF5DE095974D77157629F1E465BCDF98EBD2952BC5B8526
candidate SHA-256: B36921751ED008F69CF5DE095974D77157629F1E465BCDF98EBD2952BC5B8526
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474801_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474801_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474801_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474801_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474801_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:474920
original SHA-256: CE92E7A8D1377E452F5D20106EC65D8ADFDE7189F72CB4FBBD5FE9E687D889AC
candidate SHA-256: CE92E7A8D1377E452F5D20106EC65D8ADFDE7189F72CB4FBBD5FE9E687D889AC
원문 frame 패킷: [1, 19]
최종 full_diff 패킷: [37, 37]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 37]
후보 중복만 있는 생략 가능 패킷: [20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474920_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474920_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474920_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474920_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474920_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474920_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474920_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474920_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474920_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474920_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474920_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474920_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474920_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474920_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474920_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474920_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474920_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474920_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474920_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474920_0037.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:474949
original SHA-256: 4AF333E8E8094A44ACC2E73ECCE57724B8E6495EA59E9C1E0766F0891A805FC6
candidate SHA-256: DAB096C0BA1374007BAEDE2FBA17C4B376519770687CA6E129FFA326BFC9063D
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

