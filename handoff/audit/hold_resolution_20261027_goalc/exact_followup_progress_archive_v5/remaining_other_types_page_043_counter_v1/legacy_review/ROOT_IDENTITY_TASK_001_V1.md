# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:529218
original SHA-256: 8CDEF24276FA587D9F3B95E8EAE0D1C1F231A46FC6C7A5DA815CAAD8526E7B21
candidate SHA-256: 8CDEF24276FA587D9F3B95E8EAE0D1C1F231A46FC6C7A5DA815CAAD8526E7B21
원문 frame 패킷: [1, 8]
최종 full_diff 패킷: [15, 15]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 15]
후보 중복만 있는 생략 가능 패킷: [9, 10, 11, 12, 13, 14]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_043_counter_v1/reading_packets_v1/expanded_train_529218_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_043_counter_v1/reading_packets_v1/expanded_train_529218_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_043_counter_v1/reading_packets_v1/expanded_train_529218_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_043_counter_v1/reading_packets_v1/expanded_train_529218_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_043_counter_v1/reading_packets_v1/expanded_train_529218_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_043_counter_v1/reading_packets_v1/expanded_train_529218_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_043_counter_v1/reading_packets_v1/expanded_train_529218_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_043_counter_v1/reading_packets_v1/expanded_train_529218_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_043_counter_v1/reading_packets_v1/expanded_train_529218_0015.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:529360
original SHA-256: 3DBA2805A20B60B890E12FEE8E695CB5CFB03D902CD47D46BFBDABFD7EE07DCB
candidate SHA-256: 3DBA2805A20B60B890E12FEE8E695CB5CFB03D902CD47D46BFBDABFD7EE07DCB
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5, 6]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_043_counter_v1/reading_packets_v1/expanded_train_529360_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_043_counter_v1/reading_packets_v1/expanded_train_529360_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_043_counter_v1/reading_packets_v1/expanded_train_529360_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_043_counter_v1/reading_packets_v1/expanded_train_529360_0005.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_043_counter_v1/reading_packets_v1/expanded_train_529360_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:529364
original SHA-256: B62EF58BFDF426B448EE35C6C97136681F141004B19F0ADA533EC8379344ACF7
candidate SHA-256: DC134BFB312C22A772AC26916E74C310D1BB66B3244400E734B86A7E8BA57FA9
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:529553
original SHA-256: B5071EB2C5C5566C9FDD94736232CD42FED56F809A9CB9EE006A55DB237EA14E
candidate SHA-256: BA8B7AF61082B729263BEA0F344115CDBE38E5C210A70DE0D1A563AE81902C46
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:529617
original SHA-256: 50AB287A33B72758BEAB1C230D65CE01D3E54A968D1C119D537A1217BE58B900
candidate SHA-256: 50AB287A33B72758BEAB1C230D65CE01D3E54A968D1C119D537A1217BE58B900
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_043_counter_v1/reading_packets_v1/expanded_train_529617_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_043_counter_v1/reading_packets_v1/expanded_train_529617_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_043_counter_v1/reading_packets_v1/expanded_train_529617_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_043_counter_v1/reading_packets_v1/expanded_train_529617_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_043_counter_v1/reading_packets_v1/expanded_train_529617_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

