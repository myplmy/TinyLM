# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:786540
original SHA-256: DD877D3D7D1F50BC3652477C42DCE8F34725072016605F2A5145CBDDE45B4451
candidate SHA-256: DD877D3D7D1F50BC3652477C42DCE8F34725072016605F2A5145CBDDE45B4451
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_025_counter_v1/reading_packets_v1/expanded_train_786540_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:787508
original SHA-256: BCB1C8EC7B7213F9C3BF3DD01121B5FF760575F6CA53DC6702CCEEFA82F7ED62
candidate SHA-256: BCB1C8EC7B7213F9C3BF3DD01121B5FF760575F6CA53DC6702CCEEFA82F7ED62
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_025_counter_v1/reading_packets_v1/expanded_train_787508_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:787932
original SHA-256: 3B800B7E33E39B6D3D6791206EAC12CF8F2723189CA39DF9E5119D58D1834FD2
candidate SHA-256: 3B800B7E33E39B6D3D6791206EAC12CF8F2723189CA39DF9E5119D58D1834FD2
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_025_counter_v1/reading_packets_v1/expanded_train_787932_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_025_counter_v1/reading_packets_v1/expanded_train_787932_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:788581
original SHA-256: 14A096267491637FC81CC2CACDF8B199F236136F1F6CB4AAAA61379DED9125C9
candidate SHA-256: 8C7C18EF03DB1C843AFAA8E73DF63EB5E1F300538EFAC31F5F57BFF11494991E
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:788946
original SHA-256: 373D3B0EF2A11259ECD8840FA33D58D0A1A68174785C4FF20C00471EFAD8FDBC
candidate SHA-256: C3FACBFA3420C7A56053E4414B5F474B8DFBAF7AED07A9F958BFDDAF4A63EFAD
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

