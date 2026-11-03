# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:930179
original SHA-256: 8FD1915527C4AAA86C18CE87C3AE9D775F74FE2FC199D1D4CE1588ECEF3A952E
candidate SHA-256: 8DD9370BC957B0FCD3FD0382C6F352945B2BFE55E5F5C54333A78A801CD6274A
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:930330
original SHA-256: 5F50F05CF852E2C20815151E7236F67F7F171F632702D6AD4FB5F90599628223
candidate SHA-256: 5F50F05CF852E2C20815151E7236F67F7F171F632702D6AD4FB5F90599628223
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_070_counter_v1/reading_packets_v1/expanded_train_930330_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_070_counter_v1/reading_packets_v1/expanded_train_930330_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_070_counter_v1/reading_packets_v1/expanded_train_930330_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_070_counter_v1/reading_packets_v1/expanded_train_930330_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:930391
original SHA-256: C43F80274A15A353139C0A83E3DF8DABAFC5D9A3C89F72E92BC2E5EE2E4FFA44
candidate SHA-256: C43F80274A15A353139C0A83E3DF8DABAFC5D9A3C89F72E92BC2E5EE2E4FFA44
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_070_counter_v1/reading_packets_v1/expanded_train_930391_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:930533
original SHA-256: A230CD94AC57CB683FBCD74C64C065F6BE6E572CBB763EF3839019AEDDA69721
candidate SHA-256: 40BA0723A98B002161DE856D5B7BA9591B74773A156AAF83BB88FC4B458654FF
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:930686
original SHA-256: 796F9B8BD40013577D525EA8BD7B34CA53BE8F24CCA263A602C08F5669548E19
candidate SHA-256: EDBBDCD0992124E096393DB1CFF8095BED123AC76D50294B5E9BB87F7E234291
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

