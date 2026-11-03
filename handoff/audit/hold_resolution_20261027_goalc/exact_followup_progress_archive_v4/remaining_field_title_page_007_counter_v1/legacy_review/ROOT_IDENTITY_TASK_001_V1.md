# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:100028
original SHA-256: 064B724B59C6FAB6D499DC76EF6CA4A450C8A454456A5FE62DC1FB39DCFC4FDB
candidate SHA-256: 064B724B59C6FAB6D499DC76EF6CA4A450C8A454456A5FE62DC1FB39DCFC4FDB
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_100028_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:100127
original SHA-256: 22191D1689AA4E90CE6F474C308AB545B2491491F78FF4C29C671D925FE73E98
candidate SHA-256: BDA2B7F11C09F2C4F49B88CCF3EF24261AF0155A991826A3840A1F78D33A01A9
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:100608
original SHA-256: 0838574B0225A41ABC81E9023C999D611D83C61AA9B9A9EDDF3DAE5F7B4F9A25
candidate SHA-256: 0838574B0225A41ABC81E9023C999D611D83C61AA9B9A9EDDF3DAE5F7B4F9A25
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_100608_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_100608_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:101768
original SHA-256: AC9223B10F0168E9D5729501D18C676EBA1D7B04AA120868945C202E6FA49675
candidate SHA-256: C279782209782E7349305DC769C1C9E4ECBA87FE19C76C0291DEC305BD6DBAEB
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:102304
original SHA-256: 91156BD9B487F7DF8F2CE0676BC99688A52BC0B6889B0FCBA7CD9EF4EFAF372D
candidate SHA-256: 57185919492C33857C4B523C45CC83689AFBF61370ACC7C942E6724E0EAF7270
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

