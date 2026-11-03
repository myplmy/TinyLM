# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:546624
original SHA-256: A106D4AAC985068E254E44841544B5581254B903CE9E52AB6D3B55B598C0EB1E
candidate SHA-256: A106D4AAC985068E254E44841544B5581254B903CE9E52AB6D3B55B598C0EB1E
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_044_counter_v1/reading_packets_v1/expanded_train_546624_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_044_counter_v1/reading_packets_v1/expanded_train_546624_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_044_counter_v1/reading_packets_v1/expanded_train_546624_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_044_counter_v1/reading_packets_v1/expanded_train_546624_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_044_counter_v1/reading_packets_v1/expanded_train_546624_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:546686
original SHA-256: 5C22FDAE3C3D81A91A9288A6F041519B36B1A41236A32CECB40E05C8914F9CB1
candidate SHA-256: 5C22FDAE3C3D81A91A9288A6F041519B36B1A41236A32CECB40E05C8914F9CB1
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_044_counter_v1/reading_packets_v1/expanded_train_546686_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_044_counter_v1/reading_packets_v1/expanded_train_546686_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_044_counter_v1/reading_packets_v1/expanded_train_546686_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_044_counter_v1/reading_packets_v1/expanded_train_546686_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_044_counter_v1/reading_packets_v1/expanded_train_546686_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:546900
original SHA-256: 5D761B9F04C90393E027EE0F4953CDC64B4A89093A8726C0450200C520691A75
candidate SHA-256: 5D761B9F04C90393E027EE0F4953CDC64B4A89093A8726C0450200C520691A75
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_044_counter_v1/reading_packets_v1/expanded_train_546900_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_044_counter_v1/reading_packets_v1/expanded_train_546900_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:547477
original SHA-256: D8AF7FE3F21FF447EE6B943C0629692EA5CFD80D7822C8DF6F09BE0D20D95144
candidate SHA-256: 42AC96D110A1C7B00474A77210CEB2B6C6E1E566690F8564C3F8E680B36C2CD2
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:547699
original SHA-256: B13E6C8B5C6F022200CA85407202A3A7EBBB87880CE53CEADD2ADE986A9031F2
candidate SHA-256: CF2706FBBEF6F33B7F469D81FD5F233C3D3E69158C68A677A1128397324CCA01
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

