# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:515290
original SHA-256: AFDC5EF4CB4E22D624756864C6574011FD659C371F1684CC159C7BA46BC2ECD0
candidate SHA-256: AFDC5EF4CB4E22D624756864C6574011FD659C371F1684CC159C7BA46BC2ECD0
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515290_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:515390
original SHA-256: E7944E424F8571F1C061AD3ED6273DE7E81BA93388924D7E02BEBA2D87705A2A
candidate SHA-256: E7944E424F8571F1C061AD3ED6273DE7E81BA93388924D7E02BEBA2D87705A2A
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515390_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515390_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515390_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:515394
original SHA-256: A5335722491BE2E759420BBCD9C85E1CE3FF0754B41DAA0A88646BD0D7D747A2
candidate SHA-256: A5335722491BE2E759420BBCD9C85E1CE3FF0754B41DAA0A88646BD0D7D747A2
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [10, 10]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 10]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8, 9]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515394_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515394_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515394_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515394_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515394_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515394_0010.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:515497
original SHA-256: 2B98235E5FD934DCD3EC44C8BE184547DD3C57FAC4CB424B48B120A98BBB29DD
candidate SHA-256: 2B98235E5FD934DCD3EC44C8BE184547DD3C57FAC4CB424B48B120A98BBB29DD
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515497_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515497_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515497_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:515827
original SHA-256: D3176FD6E111DE9609A0BC7F248ED37D68F3DDF43F3F0AC46EBF034EE1C39548
candidate SHA-256: D3176FD6E111DE9609A0BC7F248ED37D68F3DDF43F3F0AC46EBF034EE1C39548
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515827_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515827_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515827_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

