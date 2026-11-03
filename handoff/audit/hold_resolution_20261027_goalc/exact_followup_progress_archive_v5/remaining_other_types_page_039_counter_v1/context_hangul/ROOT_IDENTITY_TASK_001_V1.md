# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:474430
original SHA-256: 9F48D878AA94CAD27A4FD1FE40047FBB35676D64D443D8CAC224030C30AA0AA8
candidate SHA-256: FF032C49CDF32388C009F9B5E2A45A11F743130D5636D7A20AD5637102D8D2E7
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:474657
original SHA-256: 235E868DB0EC6F769574CF8C1C42FF6093AEB16028176001A2B349437AD2FAB6
candidate SHA-256: 235E868DB0EC6F769574CF8C1C42FF6093AEB16028176001A2B349437AD2FAB6
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5, 6]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474657_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474657_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474657_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474657_0005.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474657_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:474950
original SHA-256: AD887FDC75216E974D4D2EC08A34762EDD5DB6819B8181E648E303CE082EECA5
candidate SHA-256: AD887FDC75216E974D4D2EC08A34762EDD5DB6819B8181E648E303CE082EECA5
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474950_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474950_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_039_counter_v1/reading_packets_v1/expanded_train_474950_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:475119
original SHA-256: 383D828E313D9E0B9F82C44BAD763E54FAC26E6010A8C28EE6FFC74BC7BD530B
candidate SHA-256: 68AD722581C0E31DD45C757D15F13202F5231BFD0F0FCE7F014FF4BEFA9C1424
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:475226
original SHA-256: D93E8826CFD86A1C49569420D8832C5929168EED078385C0D6C4612541DB75DB
candidate SHA-256: AB021A7E4DBAE4872C3925007E2D3F151B552973793B1D1CCFB8E86B3D349A92
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

