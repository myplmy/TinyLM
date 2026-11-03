# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1071080
original SHA-256: B0B08B8E73AFFD683AF337203E66068F3E6655CDCA2EC66BF5668D56E3BEB4BA
candidate SHA-256: B0B08B8E73AFFD683AF337203E66068F3E6655CDCA2EC66BF5668D56E3BEB4BA
원문 frame 패킷: [1, 10]
최종 full_diff 패킷: [20, 20]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20]
후보 중복만 있는 생략 가능 패킷: [11, 12, 13, 14, 15, 16, 17, 18, 19]
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_078_packet_v1.py --source-id expanded_train:1071080 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_078_packet_v1.py --source-id expanded_train:1071080 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_078_packet_v1.py --source-id expanded_train:1071080 --packet 3 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_078_packet_v1.py --source-id expanded_train:1071080 --packet 4 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_078_packet_v1.py --source-id expanded_train:1071080 --packet 5 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_078_packet_v1.py --source-id expanded_train:1071080 --packet 6 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_078_packet_v1.py --source-id expanded_train:1071080 --packet 7 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_078_packet_v1.py --source-id expanded_train:1071080 --packet 8 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_078_packet_v1.py --source-id expanded_train:1071080 --packet 9 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_078_packet_v1.py --source-id expanded_train:1071080 --packet 10 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_078_packet_v1.py --source-id expanded_train:1071080 --packet 20 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1071132
original SHA-256: 111D235F3237A15706CF159B23105FA7552F9B343E155ABDFB89F228EF047B25
candidate SHA-256: 53E67A4DAFBF1448C7284138B114B20FA60FE7108C653F9B0D400E31646BDAF5
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1071147
original SHA-256: C845EE0BAC1A7B990F17C61C2552D8C4FFA9A2A66DEFEDE23E21CD938C88FDA3
candidate SHA-256: 528E01E021A05A518688DDB20D47AB5DAB5BB1C599AD1C02F4E379E80106A93F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1071179
original SHA-256: ED77CC90BF88586B7ACE91CE28ACD0B7D776490E17325C4AE3EF89B1B7C3B3E5
candidate SHA-256: ED77CC90BF88586B7ACE91CE28ACD0B7D776490E17325C4AE3EF89B1B7C3B3E5
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_078_packet_v1.py --source-id expanded_train:1071179 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_078_packet_v1.py --source-id expanded_train:1071179 --packet 2 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1071195
original SHA-256: 2CDE7C0072FA1595CE47B6CC7B88D4FF4AB7F62D2F105074110E1C390A547BD6
candidate SHA-256: 2F6F93EF862D0C69E28A6AB5FF2EAB00125F0457109295618744EB3A8A24A435
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

