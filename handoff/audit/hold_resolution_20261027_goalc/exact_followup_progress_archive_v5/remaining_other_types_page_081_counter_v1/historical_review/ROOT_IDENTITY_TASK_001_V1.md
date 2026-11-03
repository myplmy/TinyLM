# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1116736
original SHA-256: D5186D8AD938909EE5AB8A8C814762D5814B005FB418F37363237E403DD3A3AB
candidate SHA-256: D5186D8AD938909EE5AB8A8C814762D5814B005FB418F37363237E403DD3A3AB
원문 frame 패킷: [1, 12]
최종 full_diff 패킷: [23, 23]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 23]
후보 중복만 있는 생략 가능 패킷: [13, 14, 15, 16, 17, 18, 19, 20, 21, 22]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1116736_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1116736_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1116736_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1116736_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1116736_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1116736_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1116736_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1116736_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1116736_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1116736_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1116736_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1116736_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1116736_0023.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1116743
original SHA-256: 3858DC639F141A49F024354C3C95A01FAEA86EB517529B019A4BACB836812C56
candidate SHA-256: 3858DC639F141A49F024354C3C95A01FAEA86EB517529B019A4BACB836812C56
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1116743_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1116869
original SHA-256: CEB80C2679B42EDEEC42C271A316EB427E00B554B85C58CB9F48874C4EFA91D4
candidate SHA-256: CEB80C2679B42EDEEC42C271A316EB427E00B554B85C58CB9F48874C4EFA91D4
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1116869_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1116869_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1116869_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1116869_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1116874
original SHA-256: 934BD4700BA824C8B90E43E2E05CE1D987B5CB4C117B985A12FFB76ED36FB7D8
candidate SHA-256: 934BD4700BA824C8B90E43E2E05CE1D987B5CB4C117B985A12FFB76ED36FB7D8
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1116874_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1116874_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1116874_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1117068
original SHA-256: 8D23E992831A7391CA1DBA2EAF9CAEBB53D43C010C3FA7D7E8698DEE30AFD91C
candidate SHA-256: 8D23E992831A7391CA1DBA2EAF9CAEBB53D43C010C3FA7D7E8698DEE30AFD91C
원문 frame 패킷: [1, 8]
최종 full_diff 패킷: [15, 15]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 15]
후보 중복만 있는 생략 가능 패킷: [9, 10, 11, 12, 13, 14]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1117068_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1117068_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1117068_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1117068_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1117068_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1117068_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1117068_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1117068_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1117068_0015.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

