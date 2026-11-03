# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:419671
original SHA-256: CB1E4FFFFAA79BF71137FEB336D419C003277CA60020F7565F6AA8F9D9A09C23
candidate SHA-256: CB1E4FFFFAA79BF71137FEB336D419C003277CA60020F7565F6AA8F9D9A09C23
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_035_packet_v1.py --source-id expanded_train:419671 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_035_packet_v1.py --source-id expanded_train:419671 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_035_packet_v1.py --source-id expanded_train:419671 --packet 3 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_035_packet_v1.py --source-id expanded_train:419671 --packet 5 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:419704
original SHA-256: 6ED1A596E0010C0A1714AEB1C80DDA8DA1DFB4C4D7A5DB0879DE3E4FB70EB8D4
candidate SHA-256: 6ED1A596E0010C0A1714AEB1C80DDA8DA1DFB4C4D7A5DB0879DE3E4FB70EB8D4
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [10, 10]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 10]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8, 9]
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_035_packet_v1.py --source-id expanded_train:419704 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_035_packet_v1.py --source-id expanded_train:419704 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_035_packet_v1.py --source-id expanded_train:419704 --packet 3 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_035_packet_v1.py --source-id expanded_train:419704 --packet 4 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_035_packet_v1.py --source-id expanded_train:419704 --packet 5 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_035_packet_v1.py --source-id expanded_train:419704 --packet 10 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:419734
original SHA-256: 95013453066361DD4FFA0B163DBE9E341C154BA5FD2F4FA5FB886334118470A6
candidate SHA-256: 95013453066361DD4FFA0B163DBE9E341C154BA5FD2F4FA5FB886334118470A6
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_035_packet_v1.py --source-id expanded_train:419734 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_035_packet_v1.py --source-id expanded_train:419734 --packet 2 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:419870
original SHA-256: D55DB27CA791BC91FA2223696846C732EECDEE86B80C66C8C88E9FA05E05A088
candidate SHA-256: F94091E24DC8745665E7CCD452ED1BC7F3FD3E1A06226C598AECA6FB7029D8AA
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:420000
original SHA-256: 02043C947DE2D317E06AD7BE7EDCB7BC4F7E4A578289FB60E50B21C75085B04C
candidate SHA-256: 0C9DAD62D4D4D98B3434F8CADFF3E969A5B45AFFEF8647B0EE6705FBFAAA54A0
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

