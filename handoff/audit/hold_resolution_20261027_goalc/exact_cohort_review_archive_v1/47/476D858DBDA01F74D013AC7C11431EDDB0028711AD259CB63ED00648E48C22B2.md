# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:100108
original SHA-256: 72211B378AA6BAFD1F9C4BECE2869337370B0BA624D12D1CF06C94CB0998C815
candidate SHA-256: 0C13CADF5E1244F7C57819F8A8A718EAED9AB281A4EC5FBE4E11D8A0499F5513
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:100587
original SHA-256: A47322723636E65411553306175FA6661C0CB43AC4EFC611D58F929815F8DFB2
candidate SHA-256: 9A90C0FFB9F39F70D567E92BECFC57BD78B5DE1D7FE47F13347783E60C46C1A4
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:100935
original SHA-256: 646F76B564586B1467613FD9F79404D10CAF6222A6928EFCA0543B169B3D5C5F
candidate SHA-256: 646F76B564586B1467613FD9F79404D10CAF6222A6928EFCA0543B169B3D5C5F
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_100935_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_100935_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:101509
original SHA-256: 86736148C07BA4DFD583B75F1914ED5F2A603A579CD6134EA33025CD87E83942
candidate SHA-256: 7832CC66AF74701ECF51B11C03F81EECF2CF60936C4F68759A24CB70B9305756
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:102069
original SHA-256: 94860B9DA16AB9ED194EA5FF937D99FE227E7428DC3E5A4532FECD94D3C79A81
candidate SHA-256: 4A83AC0B377E5675388AFEEF3222899995BF4824BBB2304D66568C521C42CCDE
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

