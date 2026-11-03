# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:103791
original SHA-256: 3E547CB13AC4775D3F8DAA954C3C2C027AF976A9747DCC9B3393AA86FBE2EBBE
candidate SHA-256: 3E547CB13AC4775D3F8DAA954C3C2C027AF976A9747DCC9B3393AA86FBE2EBBE
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_011_counter_v1/reading_packets_v1/expanded_train_103791_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:103793
original SHA-256: 076D4AB2A66B6BDABF7E0923263869F57F47C340777F900914E927AD171D2B10
candidate SHA-256: 076D4AB2A66B6BDABF7E0923263869F57F47C340777F900914E927AD171D2B10
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_011_counter_v1/reading_packets_v1/expanded_train_103793_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:103799
original SHA-256: D472DA6A37EDB4F12D5D8B3387096CC61F7990E6B2CEDD76A216D91BE7C5A879
candidate SHA-256: D472DA6A37EDB4F12D5D8B3387096CC61F7990E6B2CEDD76A216D91BE7C5A879
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_011_counter_v1/reading_packets_v1/expanded_train_103799_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:103816
original SHA-256: 732E8CFE8BDB6FA036BF9F1F83ADA0E751749A87DB667B1A79DEF5C7D5DCCA84
candidate SHA-256: 732E8CFE8BDB6FA036BF9F1F83ADA0E751749A87DB667B1A79DEF5C7D5DCCA84
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_011_counter_v1/reading_packets_v1/expanded_train_103816_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:103862
original SHA-256: C1B83FDD6ED079312EF28102D8A7983C39E2AF95D14F2EA4467AD1571550CD1D
candidate SHA-256: C1B83FDD6ED079312EF28102D8A7983C39E2AF95D14F2EA4467AD1571550CD1D
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_011_counter_v1/reading_packets_v1/expanded_train_103862_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_011_counter_v1/reading_packets_v1/expanded_train_103862_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

