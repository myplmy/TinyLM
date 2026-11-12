# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:452408
original SHA-256: 7837095E1AF63D290CBB7993F73AB4727714FE3ADD9159DE300F0CC0E7A51322
candidate SHA-256: D5E3C1716F2A43CF67210C6463E1A22E407AE039C2BC819ABFF31FBD9382C9F6
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:453749
original SHA-256: 846BB77E882AAD69495F34BB35581D599C934EB4BA1A7C6EC20E7B1C68A4188C
candidate SHA-256: E9D8D5EB7F532B94E48A100AC929E1B165CEFF3D6C7DC53369420BE48034B9B9
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:453860
original SHA-256: E52285603CE4B37DD8D24A817B478BF5A793CAD55BA9E6882C5FC076A533BBEC
candidate SHA-256: 6442595B131C600ED18E560C6802D554DCA4D45AB32B2889160C8740F7908CC4
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:454313
original SHA-256: AC7AB5AAC063C7BDF859A60BA1A9AFE684A1BB2B376AC58EFCEAF4DF99ADA92F
candidate SHA-256: AC7AB5AAC063C7BDF859A60BA1A9AFE684A1BB2B376AC58EFCEAF4DF99ADA92F
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_017_packet_v1.py --source-id expanded_train:454313 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:455571
original SHA-256: E926A4B1F68C1A14506104C494A701AB969C9922C48C826F180170D7B4525177
candidate SHA-256: E926A4B1F68C1A14506104C494A701AB969C9922C48C826F180170D7B4525177
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_017_packet_v1.py --source-id expanded_train:455571 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

