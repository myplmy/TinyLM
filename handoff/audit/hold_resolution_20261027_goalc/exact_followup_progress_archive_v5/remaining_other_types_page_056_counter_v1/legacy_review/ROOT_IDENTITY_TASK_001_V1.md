# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:716854
original SHA-256: 22A676E75009B04F88AC4F25F3F80780E8BDD52A146F1675762B4FAC788888BA
candidate SHA-256: 22A676E75009B04F88AC4F25F3F80780E8BDD52A146F1675762B4FAC788888BA
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_056_counter_v1/reading_packets_v1/expanded_train_716854_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:717400
original SHA-256: 8F2F3BD0A495E5844A8F809DD119E0C6204918E171CE50DDAE55D54E491A6B8A
candidate SHA-256: E6A867EFE5A4380673E3C35001F94451319818A09B3EEDC503F3E27B7AB01E59
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:717630
original SHA-256: 5389EC1B9DE001876AF7719798193BDF07C64B18A4A759065040789506DC2741
candidate SHA-256: 5389EC1B9DE001876AF7719798193BDF07C64B18A4A759065040789506DC2741
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_056_counter_v1/reading_packets_v1/expanded_train_717630_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:717642
original SHA-256: 79FF248EEDF5E56CD2E35AE882A14B779EA82C97DD500E1E3A29F68A8A832130
candidate SHA-256: 79FF248EEDF5E56CD2E35AE882A14B779EA82C97DD500E1E3A29F68A8A832130
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_056_counter_v1/reading_packets_v1/expanded_train_717642_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_056_counter_v1/reading_packets_v1/expanded_train_717642_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_056_counter_v1/reading_packets_v1/expanded_train_717642_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_056_counter_v1/reading_packets_v1/expanded_train_717642_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_056_counter_v1/reading_packets_v1/expanded_train_717642_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:717653
original SHA-256: 4802ED86CEADC75A545ADF5976DFD74C62AE50FF58705C7E0C165F7D9F0FD70C
candidate SHA-256: 4802ED86CEADC75A545ADF5976DFD74C62AE50FF58705C7E0C165F7D9F0FD70C
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_056_counter_v1/reading_packets_v1/expanded_train_717653_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

