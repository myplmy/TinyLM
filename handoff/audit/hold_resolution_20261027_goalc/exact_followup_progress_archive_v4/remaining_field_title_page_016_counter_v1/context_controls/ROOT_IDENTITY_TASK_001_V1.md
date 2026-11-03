# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:401265
original SHA-256: 6798F89B9BBAB8C5FA2340EBF73A59243366B7D78652135810FB4146DEDADA3B
candidate SHA-256: 6798F89B9BBAB8C5FA2340EBF73A59243366B7D78652135810FB4146DEDADA3B
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6, 7]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_016_packet_v1.py --source-id expanded_train:401265 --packet 1 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_016_packet_v1.py --source-id expanded_train:401265 --packet 2 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_016_packet_v1.py --source-id expanded_train:401265 --packet 3 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_016_packet_v1.py --source-id expanded_train:401265 --packet 6 --piece 1
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_016_packet_v1.py --source-id expanded_train:401265 --packet 7 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:401587
original SHA-256: D8EBB897A5DCF831957977D19441643116FCE2584B19C6A8F27D69AD2EF076EC
candidate SHA-256: B07D66FD1B1E868862C0FDF4492A9E36018825167793AD881C3F19B0049AB944
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:402261
original SHA-256: 9C9BEBF16F2546DDA481A2B9880C329C13CC48481D5A3E09E63CF0A495E40BA9
candidate SHA-256: 791634AC37F73ED3F7FBD00589C5BFDE2C7452D41843CD485D63D0D60DE17672
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:402280
original SHA-256: 41129817C338A33E858D00217995755084F54366D813EF5C21C691D51E3C7260
candidate SHA-256: 7C55B0F711C526418264CB6BF723BB4FE8C3C2AEBECD191B1EE90F6358C79919
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:402429
original SHA-256: 69023DA4C5DBB4461A079360B90506F6B7F4D93BAAA24429C7DA443068FE7DF0
candidate SHA-256: 11990581E91CBA2D9D091014B1307CD22A71944D33F55AE5E8E627F27771F1EC
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

