# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1028647
original SHA-256: BB8030DABFDCEAF65FE65397AF3C469CDBCBCCFEFAA72E53E42F459419167711
candidate SHA-256: 8B16A0A65A0CD5AC5576616E8842A710155D626E3032208CF2B263E1681E66F7
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1028767
original SHA-256: 4A2211C6644A363D3865D706337B4111DA3CD52A16D374CDB87ED49F9AD81401
candidate SHA-256: 61DB71D98C26CC3EAEA95D73AD777EBFF2EB533EEAE7495CE351AE2FAA271B73
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1028803
original SHA-256: 5E0CFC9D6FF0A3F6CCB8CA1E12B09B5557A909318750AE4B325DB27798EC8882
candidate SHA-256: 5E0CFC9D6FF0A3F6CCB8CA1E12B09B5557A909318750AE4B325DB27798EC8882
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028803_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028803_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028803_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1028855
original SHA-256: C99A56781C97D807F6176E799D64C7BE936D9FC7569F9253E835653084604BD9
candidate SHA-256: C99A56781C97D807F6176E799D64C7BE936D9FC7569F9253E835653084604BD9
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028855_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028855_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028855_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028855_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028855_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1028977
original SHA-256: 89A9B9EEB2D646415C47119D74CEDD9636684A71905EF4091E8FFFCE82741BFE
candidate SHA-256: 89A9B9EEB2D646415C47119D74CEDD9636684A71905EF4091E8FFFCE82741BFE
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028977_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028977_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028977_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

