# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:161337
original SHA-256: 7834AC6F320A6D0D8F70805F876AF7D4DA4D9B32DDF037EB5974ECED45900149
candidate SHA-256: 7834AC6F320A6D0D8F70805F876AF7D4DA4D9B32DDF037EB5974ECED45900149
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [11, 11]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 11]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10]
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_016_packet_v1.py --source-id expanded_train:161337 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_016_packet_v1.py --source-id expanded_train:161337 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_016_packet_v1.py --source-id expanded_train:161337 --packet 3 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_016_packet_v1.py --source-id expanded_train:161337 --packet 4 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_016_packet_v1.py --source-id expanded_train:161337 --packet 5 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_016_packet_v1.py --source-id expanded_train:161337 --packet 6 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_016_packet_v1.py --source-id expanded_train:161337 --packet 11 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:161411
original SHA-256: EE12FA239F392C7B5DDB23FD6C9D313825D1D86DA77506910570D9D904BA964D
candidate SHA-256: FCAA32284CD984B9AE9258957C04D08C92365D1187A9D866EAF2D6D57BE42336
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:161456
original SHA-256: A675165B8387CEAC88BEACCF2F6D5B42D893DB1C24A7492FF3FE9465DCF05EB4
candidate SHA-256: D5AE29E3455EF0A99B238BF1385FFDB154ED03360B0F5C787B40CB9641160F2D
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:161526
original SHA-256: 481E7EF56E6C69A3FB30BADABF589C04966EA21F7A64873E46590CD00F4CA3AB
candidate SHA-256: CCB16813067A53C3EEF3453C5C84068CF248AFD77BA0CC092DBD49D4E28ABABA
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:161697
original SHA-256: C084386D168C1F79DD82AE3287807ADD3D181AC1304B89436C54C3C3B67B6B21
candidate SHA-256: 5EE5D560953A4B965A20833219EFE35A19E327F3B4AD54622CF0E83A7389F496
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

