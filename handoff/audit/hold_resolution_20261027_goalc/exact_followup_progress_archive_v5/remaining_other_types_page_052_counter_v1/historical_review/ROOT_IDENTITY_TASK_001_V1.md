# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:663682
original SHA-256: AA9EE5C533D25669D4B0524725B25EA4B9E4FF03EB6B1692ADE5F92E231903FC
candidate SHA-256: AA9EE5C533D25669D4B0524725B25EA4B9E4FF03EB6B1692ADE5F92E231903FC
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663682_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663682_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663682_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663682_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663682_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:663713
original SHA-256: 04A58AC635B989F272ED30B6F5F95976A21962EFD005B939E6E80AF2487E938E
candidate SHA-256: 3DB4D040B7DDCB86EEA6BF8D488AC88537FC0597FC64E02EA4C8674F3E6D435A
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:663831
original SHA-256: 595EDFB10E2069A995FDB2E9BD63D665CB3B3821621DEE58BBC5D44961B2D3EE
candidate SHA-256: 4C508389EB034F26EEE11E621DF11DE75D08C678B12DDE3E56BC10DC36667140
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:663884
original SHA-256: C7F458BF216BA772EF1E23E31A72D0E81984DE3E2A6DF701E494574CD3EBD94D
candidate SHA-256: C7F458BF216BA772EF1E23E31A72D0E81984DE3E2A6DF701E494574CD3EBD94D
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663884_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663884_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663884_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663884_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:664207
original SHA-256: 9E566CF49FF3BA3306C8DD78FB026BC26A0B7EF893ADC92F0E2A67A5F7E8BF17
candidate SHA-256: 9E566CF49FF3BA3306C8DD78FB026BC26A0B7EF893ADC92F0E2A67A5F7E8BF17
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_664207_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_664207_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_664207_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

