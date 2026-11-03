# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:843765
original SHA-256: 51F6EA79F0FC05825C4B087301B814DBA12613B291A5CE2CA0E68A021A3068C4
candidate SHA-256: 51F6EA79F0FC05825C4B087301B814DBA12613B291A5CE2CA0E68A021A3068C4
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_065_counter_v1/reading_packets_v1/expanded_train_843765_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_065_counter_v1/reading_packets_v1/expanded_train_843765_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_065_counter_v1/reading_packets_v1/expanded_train_843765_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:843868
original SHA-256: 55757C12BF71BE49D38F766B697A4E56DA5DBA90970D6AED70BA72D04C2B43A9
candidate SHA-256: 7B9F847411FBC7471DE550A21A025CB948036BD1C590D7B4254D7EB5F0323A89
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:844123
original SHA-256: 6F81789813CD9867150EDB30B136C28EC00935E9BBD65EB8067045151E51E725
candidate SHA-256: 6F81789813CD9867150EDB30B136C28EC00935E9BBD65EB8067045151E51E725
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_065_counter_v1/reading_packets_v1/expanded_train_844123_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_065_counter_v1/reading_packets_v1/expanded_train_844123_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:844639
original SHA-256: 369FE688447639CAB2B7663E470073783A3C7F7515C407A26C02657B9BA0C318
candidate SHA-256: 48B911EA7EA637479D3A8D01A8E724436571F7FB955FC49DDD60969EACD30D59
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:844815
original SHA-256: E4EFCBB0A5F1E681F3FC8AA9FA1F2D59876ED64E2A3ABFF8BEE6AB7FC62006C2
candidate SHA-256: E4EFCBB0A5F1E681F3FC8AA9FA1F2D59876ED64E2A3ABFF8BEE6AB7FC62006C2
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_065_counter_v1/reading_packets_v1/expanded_train_844815_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_065_counter_v1/reading_packets_v1/expanded_train_844815_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_065_counter_v1/reading_packets_v1/expanded_train_844815_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_065_counter_v1/reading_packets_v1/expanded_train_844815_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_065_counter_v1/reading_packets_v1/expanded_train_844815_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

