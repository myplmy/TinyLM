# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:24085
original SHA-256: 6D15D95C1E1675F5E39DAF1CCB929752D331DE303D3577CC4CE4276871281F12
candidate SHA-256: 336AA5A737D604075B17D0A6C01BB7C9E2E7C0619C701331C7EF1796D9084E5A
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:24150
original SHA-256: BA8236B72BB9159134B2931DA3C2ED066EAC4F5BC77ECE1DE28FC850459AC193
candidate SHA-256: BA8236B72BB9159134B2931DA3C2ED066EAC4F5BC77ECE1DE28FC850459AC193
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_003_counter_v1/reading_packets_v1/expanded_train_24150_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_003_counter_v1/reading_packets_v1/expanded_train_24150_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_003_counter_v1/reading_packets_v1/expanded_train_24150_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_003_counter_v1/reading_packets_v1/expanded_train_24150_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:24218
original SHA-256: 687E3F01F0844AB45F4E79434CE2D0A55702781D6D9E3A7A2B941CEFFEDBCE3B
candidate SHA-256: 687E3F01F0844AB45F4E79434CE2D0A55702781D6D9E3A7A2B941CEFFEDBCE3B
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_003_counter_v1/reading_packets_v1/expanded_train_24218_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_003_counter_v1/reading_packets_v1/expanded_train_24218_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_003_counter_v1/reading_packets_v1/expanded_train_24218_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:24224
original SHA-256: CD6212E6092D15E33E8DF1D0B90F6302903C19C3E441DFF1B7D032E8CEEBFB5E
candidate SHA-256: 5DF813515E2ADF7122B7B626F8D17F96BE5BE069FA28B005186F9EA27EFC4113
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:24595
original SHA-256: C33A7F1D34BB2C571A65C72054E2B2723B4C18792CB71EC9F6E8D888F5E83387
candidate SHA-256: 6E4802AFE9841A344B02DCC389EA95A178AFF1EE1474CA91A15D346E74DBD701
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

