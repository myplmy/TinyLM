# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:148771
original SHA-256: 09FB98EF9952C4524CEE1C472965C1516FC2B6FDC31E5ACDE2A2EEBE67AD8CD3
candidate SHA-256: 09FB98EF9952C4524CEE1C472965C1516FC2B6FDC31E5ACDE2A2EEBE67AD8CD3
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_015_packet_v1.py --source-id expanded_train:148771 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_015_packet_v1.py --source-id expanded_train:148771 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_015_packet_v1.py --source-id expanded_train:148771 --packet 3 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_015_packet_v1.py --source-id expanded_train:148771 --packet 4 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:148791
original SHA-256: DF5945B34BF280157F5287099A6EA6AF2893BC495EE002E6360ED218A6C40D2F
candidate SHA-256: 4949A4D906385CADF95E0BF5A7B32C661FFBDF7A10486201062D5A5A7D983F06
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:148869
original SHA-256: BA831EDB5E8D54766404FC445A0757AF02417F4A32D4A6F9C0CBB610F940A52F
candidate SHA-256: E4933CAB05EE2834A1F4D0818E23729CEEA5B7713A310B16FEA9966A70D397DB
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:148876
original SHA-256: 91F8581BCF34CFF9376FD286C1E695CC8870E7155354A6AE758F990850631270
candidate SHA-256: 197463482FE4DC8AD64F65AD3E7B5CDD77EC4DC518096E7ED5ABE58C4A1CB6D4
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:149040
original SHA-256: 92295618F567A7CDBDCD01F1B7204059E0987141F5BD3A8FA1750DFD8A0F68AF
candidate SHA-256: 1CDC14F4A41A379833BA24188CE7C0BFCA5F99913DD9EAA339458AAF9488D00F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

