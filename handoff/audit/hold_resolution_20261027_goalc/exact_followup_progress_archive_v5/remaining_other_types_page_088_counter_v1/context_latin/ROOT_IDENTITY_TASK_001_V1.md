# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1239615
original SHA-256: 9878D09DEA6A4CE476B276D202D9707CF9AC9223F824BBB2C8B1940C3D3C639E
candidate SHA-256: 9878D09DEA6A4CE476B276D202D9707CF9AC9223F824BBB2C8B1940C3D3C639E
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_088_counter_v1/reading_packets_v1/expanded_train_1239615_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1239818
original SHA-256: AED931A7AF30E87051A3304DB4B666C36D2304C68A29C0930F3B8780B1F0F305
candidate SHA-256: AED931A7AF30E87051A3304DB4B666C36D2304C68A29C0930F3B8780B1F0F305
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_088_counter_v1/reading_packets_v1/expanded_train_1239818_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1239822
original SHA-256: C1BDBA9A1FD3339D92C5E9431B2D737D615D5F201A13C7E71A12977E42AE2203
candidate SHA-256: C1BDBA9A1FD3339D92C5E9431B2D737D615D5F201A13C7E71A12977E42AE2203
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_088_counter_v1/reading_packets_v1/expanded_train_1239822_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1239911
original SHA-256: B31072066A0739566B7EBAB103412A2389E3C059C84EC07A52DE6A841E7ADE05
candidate SHA-256: E5AF168DC26F62BD9B956C5981DEFF2E96681F786DE18791F8B01EB0E5CE8C00
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1240067
original SHA-256: D45C8FA684C393939AD35FBB343FB5F4E71E61D073ACD727B6879CD1FDC1EC4D
candidate SHA-256: D45C8FA684C393939AD35FBB343FB5F4E71E61D073ACD727B6879CD1FDC1EC4D
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_088_counter_v1/reading_packets_v1/expanded_train_1240067_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_088_counter_v1/reading_packets_v1/expanded_train_1240067_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_088_counter_v1/reading_packets_v1/expanded_train_1240067_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

