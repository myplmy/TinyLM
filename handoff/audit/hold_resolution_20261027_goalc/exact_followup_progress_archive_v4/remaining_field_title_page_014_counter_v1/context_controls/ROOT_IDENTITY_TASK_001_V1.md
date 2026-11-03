# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:308289
original SHA-256: A2F8A0314EA8843F0F84E35170CA83EFB34DD2FBFD5E38016C066B74D725DE5B
candidate SHA-256: A2F8A0314EA8843F0F84E35170CA83EFB34DD2FBFD5E38016C066B74D725DE5B
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_014_packet_v1.py --source-id expanded_train:308289 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_014_packet_v1.py --source-id expanded_train:308289 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_014_packet_v1.py --source-id expanded_train:308289 --packet 3 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_014_packet_v1.py --source-id expanded_train:308289 --packet 6 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:309321
original SHA-256: 5E41A1F393266E16B380704185BE538C48C70340FDD947760B62E6461FA254AB
candidate SHA-256: 615076C404A0A0572258DAB935AC3783043F266D0C044D903B2B835C2D33D771
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:309324
original SHA-256: FFB840D406DE53378039FB5FAB053299D008A4637D3B10C859848B58288A9C38
candidate SHA-256: FFB840D406DE53378039FB5FAB053299D008A4637D3B10C859848B58288A9C38
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_014_packet_v1.py --source-id expanded_train:309324 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_014_packet_v1.py --source-id expanded_train:309324 --packet 2 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:309357
original SHA-256: F78E9CF228F5B15D44D61EF91A89D7F053F7988E1465B9C59DDFF7939915CF1E
candidate SHA-256: 89103B542BA3AF72FD2A77AAC0F0D1C6BE842A4141AC2CC152F710EE51C6CB00
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:310229
original SHA-256: B0DCB9825CCEC1D883ACE8FEF8F12DA9AF77D5BCE0CF7496C04A482E7CDCE5BD
candidate SHA-256: 46D3C65565A38BCA4A0D06D8ABF5AAF583DF12821D360DDD1599EA72D37E48A4
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

