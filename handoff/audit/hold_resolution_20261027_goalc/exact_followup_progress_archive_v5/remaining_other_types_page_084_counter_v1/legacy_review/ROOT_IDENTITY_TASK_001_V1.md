# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1167791
original SHA-256: 29CEB8B9A1C9F902E612DB90C4FA9921A94A1EA132F8F7BF3CB44987BB3DC98C
candidate SHA-256: 743B0CDABD035670398EFD644AFC2D626F417B6E83C547006632A30B4B6DAEA5
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1167829
original SHA-256: 07C46AE8277E7E8B9FB5DA728CBF4112CC17BBCC7F5401EF9F54D31CE5652BB4
candidate SHA-256: 07C46AE8277E7E8B9FB5DA728CBF4112CC17BBCC7F5401EF9F54D31CE5652BB4
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_084_counter_v1/reading_packets_v1/expanded_train_1167829_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_084_counter_v1/reading_packets_v1/expanded_train_1167829_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1167849
original SHA-256: 32EA5EB16A4018AC6BB87CF4F8AB371C4AA3B439C5ABD08DE26F54AAF3FA1DCD
candidate SHA-256: 915A7F1511936D2584F37E490BA8445EE2DC2E8B86D97EE041E85C50CC04A846
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1167910
original SHA-256: 6C37E0F63F929470AC3A69F3821E728D23BA3E5ABFDAC96255A6BEF90BC42F82
candidate SHA-256: 7893B845CDBE08E4D3FACC378BD602FA6155F28458C3A7877BF13E5BD03C20CB
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1167941
original SHA-256: 7140508B5F005DABEF7CDBBB5442099F2E57C64FA2F69471EE908ADA5CC68E08
candidate SHA-256: 7140508B5F005DABEF7CDBBB5442099F2E57C64FA2F69471EE908ADA5CC68E08
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_084_counter_v1/reading_packets_v1/expanded_train_1167941_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_084_counter_v1/reading_packets_v1/expanded_train_1167941_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

