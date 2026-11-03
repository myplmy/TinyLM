# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:148767
original SHA-256: 63628531E6F85C19329B072CF798E39CEB632ADED02F23BF0E5DF86123709F78
candidate SHA-256: 7DEA43CE435EBFAA988E895B05CC61FC93954BA1B36EC65B80B76EA4CDEF8731
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:148774
original SHA-256: 443496C0DE004AF0D3C582374BED803BD118A79192E9D1F0AAE57FBCC63EA023
candidate SHA-256: 7DE3F1AB2BB8883456B481AD1B522467A47B435C3A6B40F0DC40EC7590C26B05
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:148979
original SHA-256: CB72F86463057A6A925BD62D427878AA73CB68A6D380644705C4C993A846B285
candidate SHA-256: 9AA22F9E7D30E55284C25C04C3A668C7B1B3D083878A33E1A283550E151D8347
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:149104
original SHA-256: E51040957519A0A50DD0179EDDA1CEA561A8BBCB24F907F8F2D6ABF7AAF1D0B2
candidate SHA-256: CEC53E17825EE86F99B1D57F332A86AF1CB00BEDA45BC437382BCE1CBA1F7D77
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:149201
original SHA-256: 286497E39FE8F44D6B671DA0F174EABC2035C3A61C99E52E4B15B82652B8CABC
candidate SHA-256: 286497E39FE8F44D6B671DA0F174EABC2035C3A61C99E52E4B15B82652B8CABC
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149201_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149201_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_149201_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

