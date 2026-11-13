# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:524129
original SHA-256: C564EA273C3C9EAAD89A02F0F0365CA3EB394685E713A9EC322B0E59F8083E91
candidate SHA-256: 7DDEC6512C49054C33C9C44F78BE57E72B91738C88C79D97A23FA3B2C284A0D8
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:524319
original SHA-256: 1F3A4DFB6F953FE5F78375AD8279A301D0D5A95AD837489F344700ED4B6F161A
candidate SHA-256: 1F3A4DFB6F953FE5F78375AD8279A301D0D5A95AD837489F344700ED4B6F161A
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_019_packet_v1.py --source-id expanded_train:524319 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:524488
original SHA-256: D4C055D6C8CBFF1E87D58C58E7C1A673519284F5D5860F87DBB14C8EE667AADC
candidate SHA-256: D4C055D6C8CBFF1E87D58C58E7C1A673519284F5D5860F87DBB14C8EE667AADC
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_019_packet_v1.py --source-id expanded_train:524488 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_019_packet_v1.py --source-id expanded_train:524488 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_019_packet_v1.py --source-id expanded_train:524488 --packet 3 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:524620
original SHA-256: 37FE155440FA6C478CDDA3928FAB20B1AFBC81CE198DE5045A52217154DEDD60
candidate SHA-256: B6D49CC250135E44972066C5514E9C5227BC45C878E22F5D027EDA0160AF7A4C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:524808
original SHA-256: 111CBB529B6D48D34F7AC05FC93D942BBDA709CD3CE1CC907D8C790854A21DB0
candidate SHA-256: 01CB8BEFDC86B132DA6AD4D9BC204C87803ACB3D98F7D31DA8D618FE78C8B839
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

