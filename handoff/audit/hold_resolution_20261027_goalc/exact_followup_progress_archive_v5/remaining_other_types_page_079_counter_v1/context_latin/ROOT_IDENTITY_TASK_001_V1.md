# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1086535
original SHA-256: 2228CB78BF88E7D23BBE859A9A817D8E7A5090AB8B45AC55669D8CFBA18AA80D
candidate SHA-256: 1193C76AA11AB8F5FF7E427C33B3F37AA1255F4523E3BD1CD2F2A056E39D190C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1086790
original SHA-256: AC44AE1C6044530BE52656B20C40ECE4AF24D0BB828BC5409284BF6C1C4DBF32
candidate SHA-256: D630DE7618A49F9E5BB7B9D70E51478354982FEAD7EAD4DC9A8011F4BF6BCB3D
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1086817
original SHA-256: 015E0332780EEFF34710D723428F1202FB083F8D0AB1DE54B121E510F5B00C92
candidate SHA-256: 5EBBA42DFFFBF784596F7748A8D269E0DC4870643423A94C936773C8DE91D5FB
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1087280
original SHA-256: 88D8C59A5E236998366471E4AAD1609CC02A73DA2D3469168EF530FAF68C0C65
candidate SHA-256: 88D8C59A5E236998366471E4AAD1609CC02A73DA2D3469168EF530FAF68C0C65
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [10, 10]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 10]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8, 9]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_079_counter_v1/reading_packets_v1/expanded_train_1087280_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_079_counter_v1/reading_packets_v1/expanded_train_1087280_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_079_counter_v1/reading_packets_v1/expanded_train_1087280_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_079_counter_v1/reading_packets_v1/expanded_train_1087280_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_079_counter_v1/reading_packets_v1/expanded_train_1087280_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_079_counter_v1/reading_packets_v1/expanded_train_1087280_0010.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1087288
original SHA-256: 5329FEB916D29CC8173FADBE77CA02CC8ADDA3A8737C66700483DD90E0577787
candidate SHA-256: 8A1C01356F4ABDD71F8B4EF710F62D3390D0A93F2FD4C3D5093624175435E587
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

