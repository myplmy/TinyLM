# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:50470
original SHA-256: 0CF0E180C8250F57B1FB471613554CA3C04B666F62F285F099FE380B5395DC2F
candidate SHA-256: 0CF0E180C8250F57B1FB471613554CA3C04B666F62F285F099FE380B5395DC2F
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_005_counter_v1/reading_packets_v1/expanded_train_50470_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_005_counter_v1/reading_packets_v1/expanded_train_50470_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_005_counter_v1/reading_packets_v1/expanded_train_50470_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:50866
original SHA-256: A725F3D84075D7B2C56D373DACEE6B14E950E7F5AEFC72393AA54E9E8EB5A6AE
candidate SHA-256: 81C8239321AA1867C7084466903A464EA132693099B4C027D134DF17F127779C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:50899
original SHA-256: B737093E1F3614B478FAEDC7865F40DD5F7DDF057301215E7C43CBD131CB1B09
candidate SHA-256: D1D1D5D0442E41DA4263345B3FDCF4BA224944036477F3733B45F83D882F4F15
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:50955
original SHA-256: 9E4BAFB83BF21803128A1575A4206869CA4A0BBE8B1626826CE40EC0B8A10F8B
candidate SHA-256: 9E4BAFB83BF21803128A1575A4206869CA4A0BBE8B1626826CE40EC0B8A10F8B
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_005_counter_v1/reading_packets_v1/expanded_train_50955_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:50962
original SHA-256: 636AB77CC7059342AF76279BA199967E92519891C89C3EF047A7A5AABD887F6F
candidate SHA-256: A5B48FB84F54D8A6E3E5DC0064CF1F9C4E948A56B97734D81156E41A0ADFAA63
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

