# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:651343
original SHA-256: 6B1AE690370291431A16E919C9C94C821209E2B9E8B95CA9E793F5137E1C5131
candidate SHA-256: 6B1AE690370291431A16E919C9C94C821209E2B9E8B95CA9E793F5137E1C5131
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651343_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:651595
original SHA-256: 6C671FCECE0B82D1F83443B8E3EB26F4CFAECAC94CAFE4A6EC34D60BDCBBABA6
candidate SHA-256: D6E61C3EAB7C553FD1CCBA891BBA710EF5DA3D9F7DDB6C64B403BB1A71201381
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:651667
original SHA-256: 1D96146513FD6F4AE2DBCDC7232C401EB3BB3DA99EA95732BBFE74A1F78DC86C
candidate SHA-256: 1D96146513FD6F4AE2DBCDC7232C401EB3BB3DA99EA95732BBFE74A1F78DC86C
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [12, 12]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 12]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10, 11]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651667_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651667_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651667_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651667_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651667_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651667_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651667_0012.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:651751
original SHA-256: F0D1643C5E6C104436D445104DD4F91382545A081E2B52FB3894D2E82957F1A3
candidate SHA-256: DA7ED2EDA7CED40F78CAD76FC381B02E69D352865606B31F3201AD74DD625F27
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:651909
original SHA-256: 6BEA2462DDE3DC200132E8684D8370FD94F87D1F91961FA68A9983EA62C0CAEC
candidate SHA-256: 6CD61687CF8D2F5044FD4A1C36904D166A0CFE18B65365C0643E410F71A470FE
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

