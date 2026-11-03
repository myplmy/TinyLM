# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:694977
original SHA-256: 71325903866B4FF7F339C38F904FE0BB571FF37066D9C7BD8628B3B96428AF89
candidate SHA-256: C08BCCC9A14E6D6600E5E2E247C0E05A09AF47FE59843D54486CC7A565582CBA
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:695659
original SHA-256: B1F30877C22E276E891B687DA28269C6D2116ED7BEE5A3B2E77654C142EE1C83
candidate SHA-256: 06ECF8A3B67F1860E9677FF186AD91DDAF8ED4B8D522965CE68B611D74798B8D
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:695760
original SHA-256: 6A4645BA50F2A81B2D243E360BA73887661D4DB850CDF7037FFFE064C065ED5A
candidate SHA-256: 6A4645BA50F2A81B2D243E360BA73887661D4DB850CDF7037FFFE064C065ED5A
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_023_packet_v1.py --source-id expanded_train:695760 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:696304
original SHA-256: E66E561D4F469C1C717E91B64E45E15A4E4C58701AB463BEF9BA442E433C8D19
candidate SHA-256: E66E561D4F469C1C717E91B64E45E15A4E4C58701AB463BEF9BA442E433C8D19
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_023_packet_v1.py --source-id expanded_train:696304 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:696551
original SHA-256: 4659199D2B6A385EF25B2E22D59A5125332CC312A6B9135E55D0222A436827D2
candidate SHA-256: 4659199D2B6A385EF25B2E22D59A5125332CC312A6B9135E55D0222A436827D2
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_023_packet_v1.py --source-id expanded_train:696551 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

