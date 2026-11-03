# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:24128
original SHA-256: 5D6348412C9FB55A96E97AA75186AED8C7200D263FEF57C5A4D0AD984261D58C
candidate SHA-256: 41CB6DBA81D89B3F806AE1CE02D8670D62ABCF840C4399F16FDA06D36454D46C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:24274
original SHA-256: 8B6DCE8BFB178B8A7F4EF39F1024B044210E21FEFB7848098CAE82D7A4F5B00B
candidate SHA-256: 8B6DCE8BFB178B8A7F4EF39F1024B044210E21FEFB7848098CAE82D7A4F5B00B
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_003_packet_v1.py --source-id expanded_train:24274 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_003_packet_v1.py --source-id expanded_train:24274 --packet 2 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:24393
original SHA-256: C50471913024BD86A36DB3C8F1FE6FBA51925ADD5954C96F256FB1E0ED7EDC4E
candidate SHA-256: FB61DF44B780C75F1461D0C53615E52E9F272E4FD753FB9BCC8E247265FBB939
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:24407
original SHA-256: CC5994273384635E28CE2268D4AFE5BE490582CDE9D908A19B095832556C8502
candidate SHA-256: AA6F8C4233357FFD1145EF8D2CE89516187F899A36EAE4D42008B6359FDE6F9F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:24483
original SHA-256: 3A0DE4BA90A7E87E4858B7E80067A5C049642E426795DA725A81593C892F6CE1
candidate SHA-256: A42B7C6FEAD19309A58FE25ACB286EE122CA41DC2802074BF2A2E691E089182B
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

