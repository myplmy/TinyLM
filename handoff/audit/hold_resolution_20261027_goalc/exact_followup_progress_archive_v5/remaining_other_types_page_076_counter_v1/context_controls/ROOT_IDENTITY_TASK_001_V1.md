# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1046150
original SHA-256: 8E2D1E9E41B83E250AA1C157427BBFC49A0871DDD60D0ABB3002B41C1F454B5F
candidate SHA-256: 8E2D1E9E41B83E250AA1C157427BBFC49A0871DDD60D0ABB3002B41C1F454B5F
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_076_packet_v1.py --source-id expanded_train:1046150 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1046750
original SHA-256: B447C8133EAEA75AD0BBEAC4309E096AAB803CCD55B823526445C691CCDEB64C
candidate SHA-256: D6B8ABE9E5DF87CB135C779D87DED759D6A95C56FF30E86E9692B6CAE7A25D62
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1046790
original SHA-256: 2571FD14B4D1BB674C12CC9DF0DF9C6804E0154E034A4BF28ADCE0389EB4A468
candidate SHA-256: 2571FD14B4D1BB674C12CC9DF0DF9C6804E0154E034A4BF28ADCE0389EB4A468
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_076_packet_v1.py --source-id expanded_train:1046790 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_076_packet_v1.py --source-id expanded_train:1046790 --packet 2 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1047063
original SHA-256: C33CE749C8CFC59EF8FDF2C0E0596CA2359521B199CDEF61E5DFD99073CED3F1
candidate SHA-256: 3FF499ABE666E77F0F1C51EB1F996ADA25203BCA7F0C0BC3A4AED09DBD9A8CBB
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1047204
original SHA-256: 2ED56C73DAA7586C2C8AB7CF2C02832A15C3A41AC07CF5EB9D7D2E4C9B31D6CE
candidate SHA-256: 2ED56C73DAA7586C2C8AB7CF2C02832A15C3A41AC07CF5EB9D7D2E4C9B31D6CE
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_076_packet_v1.py --source-id expanded_train:1047204 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

