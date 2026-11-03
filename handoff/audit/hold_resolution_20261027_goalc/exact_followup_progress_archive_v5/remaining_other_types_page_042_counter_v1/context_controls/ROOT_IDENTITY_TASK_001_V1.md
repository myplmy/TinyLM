# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:515456
original SHA-256: DDB4B6C47C3EB7E4987CEB773452E6DB2B42C0210B6EA1E3341F92A3066BD84C
candidate SHA-256: DDB4B6C47C3EB7E4987CEB773452E6DB2B42C0210B6EA1E3341F92A3066BD84C
원문 frame 패킷: [1, 10]
최종 full_diff 패킷: [19, 19]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 19]
후보 중복만 있는 생략 가능 패킷: [11, 12, 13, 14, 15, 16, 17, 18]
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_042_packet_v1.py --source-id expanded_train:515456 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_042_packet_v1.py --source-id expanded_train:515456 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_042_packet_v1.py --source-id expanded_train:515456 --packet 3 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_042_packet_v1.py --source-id expanded_train:515456 --packet 4 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_042_packet_v1.py --source-id expanded_train:515456 --packet 5 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_042_packet_v1.py --source-id expanded_train:515456 --packet 6 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_042_packet_v1.py --source-id expanded_train:515456 --packet 7 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_042_packet_v1.py --source-id expanded_train:515456 --packet 8 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_042_packet_v1.py --source-id expanded_train:515456 --packet 9 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_042_packet_v1.py --source-id expanded_train:515456 --packet 10 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_042_packet_v1.py --source-id expanded_train:515456 --packet 19 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:515642
original SHA-256: A624F36724DC36765FF0E3E4F2702460DAD33281E78ADD51CFF905FF7E2E8A02
candidate SHA-256: 68ACFD501032452A32E1197FE309A974FFB964F445C3D9867E7301FFF96C816A
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:515728
original SHA-256: 708FB95C38C9EC2FD4C25CA05A733312F5BD3A8C8E22A47CDFFB7DA3F4305F8A
candidate SHA-256: 9AE7C20B1BBD045FF9A61CD71A0EA2288CB8C07D57C346040517CCD91B293464
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:515753
original SHA-256: EE85986DE47E87B84B97714EC2BA7DC964E6B14B2CB097C20B2D0A27C9EF745E
candidate SHA-256: EE85986DE47E87B84B97714EC2BA7DC964E6B14B2CB097C20B2D0A27C9EF745E
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6, 7]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_042_packet_v1.py --source-id expanded_train:515753 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_042_packet_v1.py --source-id expanded_train:515753 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_042_packet_v1.py --source-id expanded_train:515753 --packet 3 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_042_packet_v1.py --source-id expanded_train:515753 --packet 6 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_042_packet_v1.py --source-id expanded_train:515753 --packet 7 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:515763
original SHA-256: 5A2F8CF2972108B0ED456C20E19FD843391641455788DA61D68F6A4ECDD39C80
candidate SHA-256: 5A2F8CF2972108B0ED456C20E19FD843391641455788DA61D68F6A4ECDD39C80
원문 frame 패킷: [1, 9]
최종 full_diff 패킷: [18, 18]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 18]
후보 중복만 있는 생략 가능 패킷: [10, 11, 12, 13, 14, 15, 16, 17]
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_042_packet_v1.py --source-id expanded_train:515763 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_042_packet_v1.py --source-id expanded_train:515763 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_042_packet_v1.py --source-id expanded_train:515763 --packet 3 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_042_packet_v1.py --source-id expanded_train:515763 --packet 4 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_042_packet_v1.py --source-id expanded_train:515763 --packet 5 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_042_packet_v1.py --source-id expanded_train:515763 --packet 6 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_042_packet_v1.py --source-id expanded_train:515763 --packet 7 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_042_packet_v1.py --source-id expanded_train:515763 --packet 8 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_042_packet_v1.py --source-id expanded_train:515763 --packet 9 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_042_packet_v1.py --source-id expanded_train:515763 --packet 18 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

