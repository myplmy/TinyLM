# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:570593
original SHA-256: CB46E0C79F8EA764FB3F96B33E367ED881E4298ED6A702EC8B06307AE0D1D441
candidate SHA-256: D831EC196052880ECCEBA3782892965B5B73AEB84D752ECB9DC255F5F08FBFAF
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:570881
original SHA-256: E6D565AE20FC6F3D6C2A333201F86DE0FBEC9CA98E0A01D7F8BB2D44A1EB22E9
candidate SHA-256: E6D565AE20FC6F3D6C2A333201F86DE0FBEC9CA98E0A01D7F8BB2D44A1EB22E9
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [9, 9]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 9]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8]
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_020_packet_v1.py --source-id expanded_train:570881 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_020_packet_v1.py --source-id expanded_train:570881 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_020_packet_v1.py --source-id expanded_train:570881 --packet 3 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_020_packet_v1.py --source-id expanded_train:570881 --packet 4 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_020_packet_v1.py --source-id expanded_train:570881 --packet 5 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_020_packet_v1.py --source-id expanded_train:570881 --packet 9 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:573718
original SHA-256: 38151EE0A0FBB27C8B1C9D84A391A7AC0A9D8FC0D4606C1D5F18B04EEAEE8957
candidate SHA-256: 75B7A298AB253E941439F441CBC2A8914D5B5ED4E465E178D76E5B6D52851F23
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:574603
original SHA-256: 7BF852A62EEA1B3DECEEE2992ACBD9EF26A7EA51C4475FE7A5D0E5294111C09F
candidate SHA-256: 198A66FF9140A5542657D8EF9B46535DF209A0F1A68A0DA03AB4D06C8C3E7B51
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:574606
original SHA-256: A0B61908E2CA7606674698B366BDFE381550B2D36A36B31C0231FCD2AFA77BFA
candidate SHA-256: E684234A408886D1DC6169C64DCED5EACC39159406E6C9129864F07F1F801DFA
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

