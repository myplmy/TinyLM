# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:930151
original SHA-256: 1BF1939100CACE6EB9AF2D7546860EE119CF3E85D9D32E6B4EE4E803A660FC9D
candidate SHA-256: 1BF1939100CACE6EB9AF2D7546860EE119CF3E85D9D32E6B4EE4E803A660FC9D
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_070_counter_v1/reading_packets_v1/expanded_train_930151_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_070_counter_v1/reading_packets_v1/expanded_train_930151_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_070_counter_v1/reading_packets_v1/expanded_train_930151_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_070_counter_v1/reading_packets_v1/expanded_train_930151_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:930187
original SHA-256: F750A597F674A473D3FC339E91E12CB0D57A6EF5A6D9A5E7854CDF0A3AF73689
candidate SHA-256: F750A597F674A473D3FC339E91E12CB0D57A6EF5A6D9A5E7854CDF0A3AF73689
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_070_counter_v1/reading_packets_v1/expanded_train_930187_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:931223
original SHA-256: 6EA9F58266EAEA0857C8D7422F5D3A2083274A2A9F34C24D7311D417867095B8
candidate SHA-256: 07A7B434DB5F0E7931C4F8A75516830DF0892FF9A1D7FFB2673155F74EBFE306
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:931302
original SHA-256: 2876BC34D389331E1EC57A45609281EB78AE1C28CF7C890B766F9494431906A6
candidate SHA-256: 2876BC34D389331E1EC57A45609281EB78AE1C28CF7C890B766F9494431906A6
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_070_counter_v1/reading_packets_v1/expanded_train_931302_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_070_counter_v1/reading_packets_v1/expanded_train_931302_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:931461
original SHA-256: CB3A8A3652D5B95A5C9846BA9387D0A51EC0BCB7A8EB7BD5B59E320A0E7B5679
candidate SHA-256: 7FC19963816F7698F544FF8E1A95D65E299CF631B15DFC0E4CFEE26C883BF7BF
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

