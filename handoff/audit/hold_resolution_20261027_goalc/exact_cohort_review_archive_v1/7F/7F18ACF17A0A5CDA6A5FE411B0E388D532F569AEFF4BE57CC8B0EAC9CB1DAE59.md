# 정확 입력 전문 판독 연결 TASK_008

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:109296
original SHA-256: 755B02C4B6D21F3EE64071AF445E238909C4DDD204E80BCC53E5CAA3D43A3E3B
candidate SHA-256: E7654919FE11450252D2EEA93B958AE3F467E39E07E1E4008D2D3304FD4DDDFD
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:109369
original SHA-256: 1D12B5D2C848D81A7785944562A619D51896BC59B269B76C12093D5BDD05ACFF
candidate SHA-256: 1D12B5D2C848D81A7785944562A619D51896BC59B269B76C12093D5BDD05ACFF
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_109369_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_109369_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_109369_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:109713
original SHA-256: A25986C4FE3B8936CCB90BFC7EB25571ED694FA593363A9F4D6831B4D4A669C4
candidate SHA-256: A25986C4FE3B8936CCB90BFC7EB25571ED694FA593363A9F4D6831B4D4A669C4
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_109713_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_109713_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:109739
original SHA-256: 28BB657B6B0856EDD3B7FDCA8AB9BBD03D075690A0790F48E65A7F7793010212
candidate SHA-256: C4F4EE889A7872351C7DBD1BCCD7479482D11DA914CDCC1E128EDE3D18FE7DF3
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:109763
original SHA-256: 270C34BAD9CB1CEA591333F7B8E05F1C4E15E878DBF3B8F967712472F6D0B127
candidate SHA-256: B653A863E16B4BD26A55DFDDF49B4D2D2F7FAB976339AB2FD77D949CDBB0CCAC
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

