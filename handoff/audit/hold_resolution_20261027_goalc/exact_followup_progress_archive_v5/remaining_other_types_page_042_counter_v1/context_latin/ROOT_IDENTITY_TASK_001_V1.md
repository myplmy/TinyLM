# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:515369
original SHA-256: 1436B2A035238BF199ED984BF71D6C791643DF873C6727A1D12235301CE04B9A
candidate SHA-256: 1436B2A035238BF199ED984BF71D6C791643DF873C6727A1D12235301CE04B9A
원문 frame 패킷: [1, 17]
최종 full_diff 패킷: [33, 34]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 33, 34]
후보 중복만 있는 생략 가능 패킷: [18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515369_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515369_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515369_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515369_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515369_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515369_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515369_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515369_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515369_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515369_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515369_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515369_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515369_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515369_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515369_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515369_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515369_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515369_0033.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515369_0034.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:515507
original SHA-256: 13D3F81C85E00046745DF66B15119942CFB8FDC3D1E33E0F404AA08438887391
candidate SHA-256: 65DD5EC0561C15D76F3024333C287683C73DB46B782131A21BA1E8EB5902A250
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:515616
original SHA-256: 25D83736A9D2EA7D9A37AEAEBFA848CA26040EC81092736401CC4CB96B26C857
candidate SHA-256: 25D83736A9D2EA7D9A37AEAEBFA848CA26040EC81092736401CC4CB96B26C857
원문 frame 패킷: [1, 8]
최종 full_diff 패킷: [16, 16]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 16]
후보 중복만 있는 생략 가능 패킷: [9, 10, 11, 12, 13, 14, 15]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515616_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515616_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515616_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515616_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515616_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515616_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515616_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515616_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515616_0016.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:515814
original SHA-256: 71B88D0EC8D40CE970512A5A4A3F73776F8FE5520882C92D350F76F4FC8A71F4
candidate SHA-256: 0CB29EC54D90172AE88AFD6882B82CE278C8C0724927772860BBC0B169A8DE61
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:515831
original SHA-256: 3762A9B8D1FB32C5290E0BBED162EA25D053050BA233B40C7E1E09226C9E28D4
candidate SHA-256: 3762A9B8D1FB32C5290E0BBED162EA25D053050BA233B40C7E1E09226C9E28D4
원문 frame 패킷: [1, 10]
최종 full_diff 패킷: [19, 19]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 19]
후보 중복만 있는 생략 가능 패킷: [11, 12, 13, 14, 15, 16, 17, 18]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515831_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515831_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515831_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515831_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515831_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515831_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515831_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515831_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515831_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515831_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_042_counter_v1/reading_packets_v1/expanded_train_515831_0019.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

