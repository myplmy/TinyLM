# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1041629
original SHA-256: 899C7E18B86878B627DB78DB582C95C34B4D876A2447E644FF89127A2D7540C1
candidate SHA-256: AB19F9AB6088865ED222C7B51C6AB4FCDF424BFAE50B38E00E7B6C58714046A7
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1041916
original SHA-256: 11DAEFA103498A811787FF13BD5DBE9CB417AFE2DE3C98BC55D6C1A66F9B674A
candidate SHA-256: FE1F9FAB204E614CA6FBED90673307A2D6D2885EC80B32B9ABC80D41F1F99EE6
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1042098
original SHA-256: F7BF48C516D42A469138615872BF4716AD147D99658727F1880B73666B8A86E1
candidate SHA-256: F7BF48C516D42A469138615872BF4716AD147D99658727F1880B73666B8A86E1
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_030_counter_v1/reading_packets_v1/expanded_train_1042098_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_030_counter_v1/reading_packets_v1/expanded_train_1042098_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_030_counter_v1/reading_packets_v1/expanded_train_1042098_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1042366
original SHA-256: 8CA3B74F34312933CC7D02EE690A73EF06F4AD9F2C6968318AEC3C3A8DC47F02
candidate SHA-256: 8CA3B74F34312933CC7D02EE690A73EF06F4AD9F2C6968318AEC3C3A8DC47F02
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_030_counter_v1/reading_packets_v1/expanded_train_1042366_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1042469
original SHA-256: A58886113DD297F54A7A21DFB4C70DCD8B90BD03D7E29E411DF2017F6CB614C3
candidate SHA-256: AE053FB80F1AA29A775951FA046F2E40B52B43A7689840645EAD58721B97640F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

