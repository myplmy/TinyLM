# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:308649
original SHA-256: C607A0EC0D5AF73DEF8E6C6F584F28CF28355CFCD9DEAE8010C7BD4FCB696AD7
candidate SHA-256: C607A0EC0D5AF73DEF8E6C6F584F28CF28355CFCD9DEAE8010C7BD4FCB696AD7
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_027_packet_v1.py --source-id expanded_train:308649 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_027_packet_v1.py --source-id expanded_train:308649 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_027_packet_v1.py --source-id expanded_train:308649 --packet 3 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_027_packet_v1.py --source-id expanded_train:308649 --packet 6 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:308865
original SHA-256: FF325646A9239467A849A94C4B57097B1A4281C6809214030363E55621A2881A
candidate SHA-256: AA076B9F1D6F07FA1FB98D9989FEB61809970EDE333F0F6B9E73F277995C16AC
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:309105
original SHA-256: CE7C18288EF54AF82BF886D96E0ACB9143AAC458B5B34D606F071E00F5756D09
candidate SHA-256: CE7C18288EF54AF82BF886D96E0ACB9143AAC458B5B34D606F071E00F5756D09
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_027_packet_v1.py --source-id expanded_train:309105 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:309188
original SHA-256: 75E7B6CC95465BB16D2F22B75411E16ECC3534342AFD6D45E7E10FFCE32822A3
candidate SHA-256: 01419D2A66CC22098B41C4E0EF211DBBBB904A41CF817156D5C21863178042FF
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:309413
original SHA-256: 941BAB7D7183557E9EDCF4BA085549925EA9320CB6BF5A061EADBCA8D9330EB4
candidate SHA-256: 2C7562C08B54BC8C713E2C438A50D0427D537CE5AA0953072D2ECD3CD598BD37
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

