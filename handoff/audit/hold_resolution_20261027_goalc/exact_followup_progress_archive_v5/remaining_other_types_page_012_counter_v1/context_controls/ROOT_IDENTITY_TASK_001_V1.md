# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:114284
original SHA-256: 50B19097A7F95B4D95704EA4EB32D1D097EF9BDD170DF03BCAF33D3B30DD2A97
candidate SHA-256: 50B19097A7F95B4D95704EA4EB32D1D097EF9BDD170DF03BCAF33D3B30DD2A97
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_012_packet_v1.py --source-id expanded_train:114284 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:114293
original SHA-256: 8317DF745EBF4FD07C972D3282132458C7F2C8173E544A5CBFFFC7C7FA2FDFB6
candidate SHA-256: 8317DF745EBF4FD07C972D3282132458C7F2C8173E544A5CBFFFC7C7FA2FDFB6
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_012_packet_v1.py --source-id expanded_train:114293 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:114387
original SHA-256: 9316B16F0930B9F67C306D8A22331ECC83EE462DD5705D510ACAE921CC98FFCE
candidate SHA-256: 1DAFC3D41462E6EBE87CA51772718ECA74752F4E26CB271973B36A6CAC7C975B
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:114436
original SHA-256: E67F3B72CA597C5B795219E11F8E1D4860F49C43B6CA8BD9C15A496F416F2169
candidate SHA-256: E124196C9DE2990D31A0679FDBDFFF9C4239CE7C51D56B5DC572AE44723B6CF0
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:114467
original SHA-256: 10DC7026E946D87E7A77F7AE1ACD6B544E512A573FEAE6E96B50BF38A48AA89D
candidate SHA-256: 9401DB211A47669EFEDEA26B995C6312760A46374D5B0A55FCE947ED6C69DFCD
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

