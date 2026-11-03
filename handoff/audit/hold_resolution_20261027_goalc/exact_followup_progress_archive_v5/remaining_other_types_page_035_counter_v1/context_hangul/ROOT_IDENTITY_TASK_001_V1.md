# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:419513
original SHA-256: 0BE75167A0C48D330B483E3B5BFE674FA0B95255F2F441453F687EBFF74AC956
candidate SHA-256: 0BE75167A0C48D330B483E3B5BFE674FA0B95255F2F441453F687EBFF74AC956
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419513_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419513_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:419515
original SHA-256: 399355C368ED85D43535BF669C1FACF16F10EB5DD54623B25E554514E687F503
candidate SHA-256: 399355C368ED85D43535BF669C1FACF16F10EB5DD54623B25E554514E687F503
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419515_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419515_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:419541
original SHA-256: EB36704AF0933AE03A085B1B9E4AB722D50725A2DC4412BA970AEEFB881AF155
candidate SHA-256: B503031992DD944D04EAD359B27C372FF88AF0211D088EC6D58E9D99452FBF5F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:419586
original SHA-256: EF489358BADCC2DD8717706AA9887E1473E3FF7CE7DD68702C4F17C213F657DB
candidate SHA-256: EF489358BADCC2DD8717706AA9887E1473E3FF7CE7DD68702C4F17C213F657DB
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419586_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419586_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419586_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419586_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419586_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:419775
original SHA-256: 70B729E5B40C63D3EA536824B5B4C8C879653D1B7BCDFF016F11912EADC433C3
candidate SHA-256: 70B729E5B40C63D3EA536824B5B4C8C879653D1B7BCDFF016F11912EADC433C3
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419775_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419775_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_035_counter_v1/reading_packets_v1/expanded_train_419775_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

