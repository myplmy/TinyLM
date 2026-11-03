# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1151000
original SHA-256: 2081591A9A914A506C8034C487E714F105D43A0EAFE1016230B74337E457B551
candidate SHA-256: 2081591A9A914A506C8034C487E714F105D43A0EAFE1016230B74337E457B551
원문 frame 패킷: [1, 7]
최종 full_diff 패킷: [14, 14]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 14]
후보 중복만 있는 생략 가능 패킷: [8, 9, 10, 11, 12, 13]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1151000_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1151000_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1151000_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1151000_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1151000_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1151000_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1151000_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1151000_0014.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1151434
original SHA-256: 9BE6A37C0E06FB278AB71809C77031CA59A50D2AC6BC146E88CF60FBAF0CCAD8
candidate SHA-256: 9BE6A37C0E06FB278AB71809C77031CA59A50D2AC6BC146E88CF60FBAF0CCAD8
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1151434_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1151434_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1151434_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1151462
original SHA-256: ED7FB703ED574221B8B883F64C850CE7A4F14EA15683051FE29A6F96BAFA740E
candidate SHA-256: ED7FB703ED574221B8B883F64C850CE7A4F14EA15683051FE29A6F96BAFA740E
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_083_counter_v1/reading_packets_v1/expanded_train_1151462_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1151714
original SHA-256: B7A771459CAED78D41A0CF558163ECFA5E3BD1E3465797B56C28B98FE2516063
candidate SHA-256: 3F9EF1D47D1E3407148123496AA543D0620ABBF4A4992B3B86E9A54D11793F82
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1152035
original SHA-256: 81DA9D5E64FE23FCFDC9750BE9D2CDEC0CBB31C3151007EDB791EF790315996E
candidate SHA-256: C71BA46FA36B474ADEB6B4E84BAD1485296A23159C1E4651D25FA6B4F14E3160
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

