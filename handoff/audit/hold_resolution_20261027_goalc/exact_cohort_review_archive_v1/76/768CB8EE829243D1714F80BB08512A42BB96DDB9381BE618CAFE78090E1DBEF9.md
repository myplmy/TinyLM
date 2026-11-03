# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:100517
original SHA-256: 8D838F55AB8937F17540324F5BF9A55FFD9B3E59A8D13EF40A37C3C07EB0809F
candidate SHA-256: 8D838F55AB8937F17540324F5BF9A55FFD9B3E59A8D13EF40A37C3C07EB0809F
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_100517_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_100517_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_100517_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_100517_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:100786
original SHA-256: 2526EB4E643FD9B93FB2013CCD09E7D271E76CC2E5A071EFF3495EC3BE3A1FBE
candidate SHA-256: 2526EB4E643FD9B93FB2013CCD09E7D271E76CC2E5A071EFF3495EC3BE3A1FBE
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_100786_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_100786_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_100786_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_100786_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:101074
original SHA-256: EC9C082F65961DD7EC52E2E6C59632A6FDDEEF549390980FD5537223DDED5765
candidate SHA-256: EC9C082F65961DD7EC52E2E6C59632A6FDDEEF549390980FD5537223DDED5765
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_101074_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_101074_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_101074_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:101631
original SHA-256: 2A92A736A48DC6C9A4C9BD0695725483C6EC6AEAB3AF8CC8658354B20F51660A
candidate SHA-256: 2A92A736A48DC6C9A4C9BD0695725483C6EC6AEAB3AF8CC8658354B20F51660A
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_101631_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:101666
original SHA-256: B35C5C359F49CF96947FBE73336197BEAAF0BD20939488F0EB817E7929BE9D01
candidate SHA-256: 6EF3C4BE4EB18B7E1918423F5435F805F93F339A6EA8EE1E244F5158B7C4A7C3
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

