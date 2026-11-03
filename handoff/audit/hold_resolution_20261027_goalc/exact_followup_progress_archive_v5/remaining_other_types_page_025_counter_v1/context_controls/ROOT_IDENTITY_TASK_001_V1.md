# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:282598
original SHA-256: F9F3A1E632547FEF36B17A2FB4085FAAE7CF8467572BB3A33D9DBC3D9F80E122
candidate SHA-256: C2D47D137C336798399118C27F7BF89A19666110AD30C53215C6CE0C95DA31D4
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:282647
original SHA-256: 802CA8E35F7F33BF114B9C1E5D2330F4055152D384AA6E85EE56DCDACFF53FF9
candidate SHA-256: A9EEFCEB80BD2CB55E2AE971BDB287186572EAECD047CA62D25C307AC9BD5375
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:282675
original SHA-256: 2A2E5D5C4CFBC57CF6ED5CCF81258E8A97B9005B08B3C2D64CD9E156F55A6316
candidate SHA-256: 2A2E5D5C4CFBC57CF6ED5CCF81258E8A97B9005B08B3C2D64CD9E156F55A6316
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [11, 11]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 11]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10]
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_025_packet_v1.py --source-id expanded_train:282675 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_025_packet_v1.py --source-id expanded_train:282675 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_025_packet_v1.py --source-id expanded_train:282675 --packet 3 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_025_packet_v1.py --source-id expanded_train:282675 --packet 4 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_025_packet_v1.py --source-id expanded_train:282675 --packet 5 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_025_packet_v1.py --source-id expanded_train:282675 --packet 6 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_025_packet_v1.py --source-id expanded_train:282675 --packet 11 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:283035
original SHA-256: CFD9C55B0C2A2C902624ED1FD7DE377CF1689AC92AEE47805FAB5D0F613CBC5A
candidate SHA-256: BD22E7CAEABC2A4F56B3314A9419AE5C60683AAC767D9ECA0AE781F08951005C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:283356
original SHA-256: 57DC668AA8DF0B5213D5504FAA7E24D86A9A4F800711A0F14D14163231A1EBAC
candidate SHA-256: 57DC668AA8DF0B5213D5504FAA7E24D86A9A4F800711A0F14D14163231A1EBAC
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_025_packet_v1.py --source-id expanded_train:283356 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

