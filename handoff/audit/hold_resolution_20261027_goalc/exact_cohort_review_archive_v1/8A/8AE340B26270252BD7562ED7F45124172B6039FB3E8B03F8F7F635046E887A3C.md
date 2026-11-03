# 서로 다른 입력의 정확 고정 읽기 명령: TASK_059

아래 source-id는 원문/후보/diff가 다른 ID가 아니다. 같은 지정 ID의 모든 연속 frame을 뜻한다.
후보가 원문과 다르므로 원문 전문·후보 전문·전체diff를 모든 패킷 순서대로 읽는다. 동일입력 생략 계획을 적용하지 않는다.
2000문자 패킷이므로 piece는1이고 출력예산8000 이상을 쓴다. 실제 논리 END/EOF를 각각 확인한다.
실제 원문 입력은 아래 기존 고정 reader만 허용한다. raw cat/sed/검색/다른Python/코드·registry 열기는 금지다.
이 문서와 자기 정확 TASK/리뷰는 literal cat으로 읽을 수 있다. 자기 새TXT/MD만 작성하며 내용 판독 전 행은 미판독으로 명시한다.

## expanded_train:795112
원문SHA: 6CA548738B81651097BD090818D123F364FC07178ECAE2A6D804E27B9CF3BE59
후보SHA: 40B492DD66683B6E3C22A644242E93D957203AF823C13E9B3728BFAE111568CF
필수 전체 패킷 수: 4
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_literal_packet_v1.py --source-id expanded_train:795112 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_literal_packet_v1.py --source-id expanded_train:795112 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_literal_packet_v1.py --source-id expanded_train:795112 --packet 3 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_literal_packet_v1.py --source-id expanded_train:795112 --packet 4 --piece 1
```

