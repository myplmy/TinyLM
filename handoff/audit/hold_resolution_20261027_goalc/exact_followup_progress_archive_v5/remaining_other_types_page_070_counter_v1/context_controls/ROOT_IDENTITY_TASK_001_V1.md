# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:930240
original SHA-256: 45A0E50248C968E8801C3F79ACD0A164432EF12E58721A0B594762BB24BACC7E
candidate SHA-256: 6C716D9AD7A85A26F110780540C5C909854144848554C6D76AD9F93B01AF288E
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:930480
original SHA-256: 90398E959B28F40341512854711260B85927E7D6763BEA1C6E44D884AD2D65E3
candidate SHA-256: 608343EAD6BEB2801AB0EE50A2B0AD31275EDFA92F7F9E3E89F6094088C9A904
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:930517
original SHA-256: 4C71F1225BDC80C34D7FB407574117A8CE58FB41B64EA5CBBB63F3FC313D67BC
candidate SHA-256: 4C71F1225BDC80C34D7FB407574117A8CE58FB41B64EA5CBBB63F3FC313D67BC
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_070_packet_v1.py --source-id expanded_train:930517 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_070_packet_v1.py --source-id expanded_train:930517 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_other_types_page_070_packet_v1.py --source-id expanded_train:930517 --packet 3 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:931393
original SHA-256: 523B4EAD41F8C45F428B57AF3F9B7ADE95EBFBA8F48021C89643634EBC5FAB34
candidate SHA-256: BA69A2D72DCD766E1FA5DB4BE2A1ECC5A8F8AE0181DD2F4E1650C2D5E5BA686C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:931547
original SHA-256: CE2B6406C7E730B4647C8821B259F83B2148CABE9D725965B0604C43BAF17F66
candidate SHA-256: 2D7D48E56FC4CFB0F9F6E64BA8FAEB6360625B1F8CA35249714DDBE600A4E024
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

