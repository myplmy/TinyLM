# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:403900
original SHA-256: 7A2F371F04EEEFAA16872CFDFB0229350498B0014CD5A39AA503E4496C8C88BB
candidate SHA-256: 37FC79D70C86CD307BA8165CF5D0113AB22670A266B346D9D4361537A2524A42
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:404160
original SHA-256: 6363230B2C3918764065F21CCECC3D9477494A1757EA756988E1AFFE0DEF53B4
candidate SHA-256: 6363230B2C3918764065F21CCECC3D9477494A1757EA756988E1AFFE0DEF53B4
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_404160_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:404617
original SHA-256: 88E13C61661D6C29034038D292BA10D03AD350F9B5DBB0EEA0C028D54E35079C
candidate SHA-256: 88E13C61661D6C29034038D292BA10D03AD350F9B5DBB0EEA0C028D54E35079C
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_404617_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:405108
original SHA-256: 111996771F3FF4E18864A445A6B94B2B5829CE34898B2263E53A9688A5FECDEA
candidate SHA-256: B9DD5967976E9EA57FC990178B41F70F4AB666B22D561B94B333D572E0D1C6DC
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:405266
original SHA-256: 814AB63CCAB59DE42EBC43ECB128350184AC7C3C4CDFC5D853CC133135FB274E
candidate SHA-256: 814AB63CCAB59DE42EBC43ECB128350184AC7C3C4CDFC5D853CC133135FB274E
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_405266_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_405266_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_034_counter_v1/reading_packets_v1/expanded_train_405266_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

