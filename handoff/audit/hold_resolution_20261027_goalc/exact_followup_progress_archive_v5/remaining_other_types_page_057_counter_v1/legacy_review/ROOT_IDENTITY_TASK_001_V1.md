# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:733634
original SHA-256: 6D86399D4595E992A1A2B1CC20146A84D2053B5CA88EECCE92C4DD91BD862CB0
candidate SHA-256: 837D4F1ADB9A21D100B6F8EB9422F97702C2063D445BEC96F0BAC6CEB640FC59
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:733673
original SHA-256: 7EA87FFE0A8C95106A91155D2544ED959C2CB4CAB7500BDEBA3E94D6F263AFD9
candidate SHA-256: 7EA87FFE0A8C95106A91155D2544ED959C2CB4CAB7500BDEBA3E94D6F263AFD9
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_057_counter_v1/reading_packets_v1/expanded_train_733673_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:733729
original SHA-256: D7A46A135756241F28EED3D23DD6A576A204B2E8AC1AF9ECD2338B20BAB1BBB4
candidate SHA-256: DB87F3C5E2AEB2510E727E846B0BB5FC85E9849B8774C0AE9111171BDAF863F7
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:733982
original SHA-256: F594E922B9B91B79410DF920CC1F80BCE2438806671E90D2220CC8673C60B0B1
candidate SHA-256: F594E922B9B91B79410DF920CC1F80BCE2438806671E90D2220CC8673C60B0B1
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_057_counter_v1/reading_packets_v1/expanded_train_733982_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_057_counter_v1/reading_packets_v1/expanded_train_733982_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:734059
original SHA-256: 60F8F2F6B8DB860ABC004AAC261E98A922BEBCE4A788DF056B00B42A0A957CBE
candidate SHA-256: CE9BB60AAFA449D19A32514D7F361A3885E220F307B0FB61307AE138AFE34FBF
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

