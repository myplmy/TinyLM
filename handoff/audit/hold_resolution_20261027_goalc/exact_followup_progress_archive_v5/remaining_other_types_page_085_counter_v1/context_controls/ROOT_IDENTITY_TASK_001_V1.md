# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1183422
original SHA-256: F9F596992257A77655F4D453572CBCAFF171112DE57520488DE5A2528F0E2F11
candidate SHA-256: F9F596992257A77655F4D453572CBCAFF171112DE57520488DE5A2528F0E2F11
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_085_packet_v1.py --source-id expanded_train:1183422 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1183579
original SHA-256: A0A3DDD1CC2C1D34B2627F6809C48A186DD3533E1D911501407A21036DCE5555
candidate SHA-256: A0A3DDD1CC2C1D34B2627F6809C48A186DD3533E1D911501407A21036DCE5555
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_085_packet_v1.py --source-id expanded_train:1183579 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_085_packet_v1.py --source-id expanded_train:1183579 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_085_packet_v1.py --source-id expanded_train:1183579 --packet 4 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1183806
original SHA-256: 96A6B1E560E1F99F7EF08C6FC8A342C24528E53B663E14CEC8B65FF3814F9521
candidate SHA-256: 4F7FF5FFCFC400EE151674B029268097F65B2AA287A6FCCB19CA1146DB3464BC
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1183836
original SHA-256: A9864A20F099F77848BF976ADFF3F25D8D162494FBED1423BBCA900EE6C0CB37
candidate SHA-256: D3B5F56531171DF28FB4FC6F583755E9536336CA366512DE77DBAE291DB54418
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1183857
original SHA-256: 8918BD5AE2C98E6AD291EED939D6CB640C5CA4454FBA78CDD1DDF9FEEF76FFC6
candidate SHA-256: 16BA433E0194DB23D9DAF405500BB8CD39F4105062CF006259132CCBAC93778D
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

