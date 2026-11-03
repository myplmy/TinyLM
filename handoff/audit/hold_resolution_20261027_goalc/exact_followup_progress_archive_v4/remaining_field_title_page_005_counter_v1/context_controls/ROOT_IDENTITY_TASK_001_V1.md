# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:50564
original SHA-256: FF23E7C2DB75EDCFBCAAB96E2F8A975DAF88244C42CAB4C97870EA60A7CF1FB4
candidate SHA-256: FF23E7C2DB75EDCFBCAAB96E2F8A975DAF88244C42CAB4C97870EA60A7CF1FB4
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_005_packet_v1.py --source-id expanded_train:50564 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_005_packet_v1.py --source-id expanded_train:50564 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_005_packet_v1.py --source-id expanded_train:50564 --packet 4 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:50626
original SHA-256: A166362776E5180622B2CD2A9FCFA4A6BB904649DB4FC3546A90555137C8D71F
candidate SHA-256: A490B077FDDA3D18D9C604A9F0C37D3BF3ED3C5854A80557406AE5F09AF34E70
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:50794
original SHA-256: F68B0BF6C182A426F880A395565CF1D8A1E8C809B7C260AE465F8ADFCB374604
candidate SHA-256: 030C2A43CF922502F906F0F13119E392ACB978E43EE72C14CA7CEF04C5B2F9EA
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:50930
original SHA-256: A744D8512D2787E57486C56943D6B450F126C71D7622B32AF77BA18EB9A424F8
candidate SHA-256: A744D8512D2787E57486C56943D6B450F126C71D7622B32AF77BA18EB9A424F8
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_005_packet_v1.py --source-id expanded_train:50930 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:51184
original SHA-256: 3C7BC2475D631380A5D1829167A870AE649F44DFCD41C7898492F67671112A67
candidate SHA-256: 3C7BC2475D631380A5D1829167A870AE649F44DFCD41C7898492F67671112A67
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_005_packet_v1.py --source-id expanded_train:51184 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

