# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:927839
original SHA-256: 1403CCCAE6200FCC891A8213DA908FE5BC314429F51A528AD30E6B128027CF07
candidate SHA-256: 1403CCCAE6200FCC891A8213DA908FE5BC314429F51A528AD30E6B128027CF07
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_028_packet_v1.py --source-id expanded_train:927839 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_028_packet_v1.py --source-id expanded_train:927839 --packet 2 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:930195
original SHA-256: AF81272DBAB5A85E9E52490B5E6810C252A11A99EF65E5335BA5E0C59EA542EE
candidate SHA-256: FB03722E696C5E9549D078D3B35AE753058111B322C4A344CE6C58893B6F9206
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:930248
original SHA-256: 490C00C545FB4F4D439015BCB8CE2A79896EDA04E87C44278AED042D605FFB31
candidate SHA-256: 490C00C545FB4F4D439015BCB8CE2A79896EDA04E87C44278AED042D605FFB31
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_028_packet_v1.py --source-id expanded_train:930248 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:930920
original SHA-256: DCAFFD28356E3FE4537048AC6BC615816775C6DBC58AC1219695C6D4DDAA63FF
candidate SHA-256: 678E8ADFBC23131C62299A7C8F1F07336B1EC0B47C575E92E74934AC21F37E06
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:932176
original SHA-256: 8D4AE1397292E5CC9D33772795BB4153D37E7D5E5A15966C392ECF3A28DED0EB
candidate SHA-256: 3731DED17BC8C147FA22396792752D20D3ACC322413ED9A47E0AC4D4DDAD2DFC
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

