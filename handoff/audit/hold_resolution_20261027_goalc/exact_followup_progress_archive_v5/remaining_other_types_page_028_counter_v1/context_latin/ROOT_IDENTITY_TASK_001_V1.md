# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:320199
original SHA-256: 4595300408CD7786FB4B91EE1A24F072E02435670B0C4DEF6C99F308217E8234
candidate SHA-256: 4595300408CD7786FB4B91EE1A24F072E02435670B0C4DEF6C99F308217E8234
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_028_counter_v1/reading_packets_v1/expanded_train_320199_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:320236
original SHA-256: A08087BECA569D2184E5F746D69E7BF0B48DDDA2BC7B8E478E43C84248FD60F3
candidate SHA-256: A08087BECA569D2184E5F746D69E7BF0B48DDDA2BC7B8E478E43C84248FD60F3
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_028_counter_v1/reading_packets_v1/expanded_train_320236_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_028_counter_v1/reading_packets_v1/expanded_train_320236_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:320242
original SHA-256: 646BA69E7202428E19D244FBC34CDA36BD453A38E2EEEFC7F47817691E66D06B
candidate SHA-256: 646BA69E7202428E19D244FBC34CDA36BD453A38E2EEEFC7F47817691E66D06B
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_028_counter_v1/reading_packets_v1/expanded_train_320242_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:320468
original SHA-256: B09479E459840D5D54553E7D445197EC29F0EDD7116534475D0B75FC0D691C67
candidate SHA-256: 9A62A9476095C79BCB96F3235F505176E6C4C70C60FE06BDFB3684F42D7AE428
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:320497
original SHA-256: FB68D6F5F1A394C1453C335C163359C0EB58F243A5E9386A4E02E69A255F9B91
candidate SHA-256: C2C624D4739CDA102E0999DA759DD38C1EDC7E1A6B46E32B633290D55916543C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

