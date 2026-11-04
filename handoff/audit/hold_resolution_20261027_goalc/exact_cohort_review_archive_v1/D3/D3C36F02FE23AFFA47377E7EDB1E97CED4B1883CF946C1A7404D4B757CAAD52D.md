# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:180595
original SHA-256: 2136B6CC3766C806292A8476F1771BF007C6BCD48BB6F7311D6498A18D28981E
candidate SHA-256: 89ACD283DCA6AA0402AF6FD961E5AF45678C9B96F605A1070BF62C927437019A
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:180693
original SHA-256: 303BB2E9F86D18BDB1A40D293C75C0DA263C2CF09E8903082AA7906B2FB426DC
candidate SHA-256: 303BB2E9F86D18BDB1A40D293C75C0DA263C2CF09E8903082AA7906B2FB426DC
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_010_packet_v1.py --source-id expanded_train:180693 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_010_packet_v1.py --source-id expanded_train:180693 --packet 2 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:180743
original SHA-256: 57D06AD3E80CDA92110AC5699366387AE1DD155EA5747B29AA59B61DDCD4E428
candidate SHA-256: 5183D1857C8EB41E720614F4CCD9E1B41F95D9CD241344F6D4A4CAB163F467F8
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:181377
original SHA-256: 14C3B45349E9614A75D1D11C5C1CEC01D309187161367D9E8A7E4E7F93B62887
candidate SHA-256: 14C3B45349E9614A75D1D11C5C1CEC01D309187161367D9E8A7E4E7F93B62887
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_010_packet_v1.py --source-id expanded_train:181377 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:181556
original SHA-256: 484C59377D5844D0E6DCBB0D44C572B3140E466BB8BE2EE43726B24B19002E3B
candidate SHA-256: EF2139A62D97812EC590253E955469518DFFE305228F6838F43C80767673EFC0
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

