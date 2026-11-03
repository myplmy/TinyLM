# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1003630
original SHA-256: FAFD06EE634457AAFA22B1CCF5D9B8E7F3A8B2F8913D9F7E1250F2BD59BCF16B
candidate SHA-256: FAFD06EE634457AAFA22B1CCF5D9B8E7F3A8B2F8913D9F7E1250F2BD59BCF16B
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_029_counter_v1/reading_packets_v1/expanded_train_1003630_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_029_counter_v1/reading_packets_v1/expanded_train_1003630_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_029_counter_v1/reading_packets_v1/expanded_train_1003630_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1005100
original SHA-256: E9C611EE6F3C492EC8B1BEB0EB5AA6BC330B45A9FDEAFFB4B652DC4FEF9B8C18
candidate SHA-256: E9C611EE6F3C492EC8B1BEB0EB5AA6BC330B45A9FDEAFFB4B652DC4FEF9B8C18
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [10, 10]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 10]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8, 9]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_029_counter_v1/reading_packets_v1/expanded_train_1005100_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_029_counter_v1/reading_packets_v1/expanded_train_1005100_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_029_counter_v1/reading_packets_v1/expanded_train_1005100_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_029_counter_v1/reading_packets_v1/expanded_train_1005100_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_029_counter_v1/reading_packets_v1/expanded_train_1005100_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_029_counter_v1/reading_packets_v1/expanded_train_1005100_0010.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1006160
original SHA-256: 5AA3FCFA1C90A77D511090CC64B21C7F5E5D8D0687E056EE128D9EAE46FC74F8
candidate SHA-256: B33ECE0ECAD4FCB40BE39A88813FBAA4F6A50A7F98C1BEE0891ACC72EB853EC3
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1009561
original SHA-256: B8B0CDE935FA705E8EE82C3A9866F8DE8FAD960E2B606A3EF7E0D16988EDF66A
candidate SHA-256: B8B0CDE935FA705E8EE82C3A9866F8DE8FAD960E2B606A3EF7E0D16988EDF66A
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_029_counter_v1/reading_packets_v1/expanded_train_1009561_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_029_counter_v1/reading_packets_v1/expanded_train_1009561_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_029_counter_v1/reading_packets_v1/expanded_train_1009561_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_029_counter_v1/reading_packets_v1/expanded_train_1009561_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1009751
original SHA-256: B6F490C61105B6354B366C1AB21EB2312EEAA69D15A95A647247AA7C6295AE8B
candidate SHA-256: B6F490C61105B6354B366C1AB21EB2312EEAA69D15A95A647247AA7C6295AE8B
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_029_counter_v1/reading_packets_v1/expanded_train_1009751_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

