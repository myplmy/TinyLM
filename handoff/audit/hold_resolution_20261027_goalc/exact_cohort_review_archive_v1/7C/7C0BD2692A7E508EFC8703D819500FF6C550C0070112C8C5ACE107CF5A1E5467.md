# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:28707
original SHA-256: D6CCDE65B5541791CDC1598512859DC73305CE2753364607567DABD11414BE39
candidate SHA-256: E7216E91EDF0943BF64DF3F4EA1104FCC01F502048F76E4ED0D40D6A5FD46EC0
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:28830
original SHA-256: 699790FA5EAE2B3AAC4640D56582F454B538B940FA5EE66C0AD32EBA403A2C09
candidate SHA-256: 4E6F2BF54E248BDC51BC579610A4D0F0B6F13E8C9ACDA31B34900992C7C7ADD0
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:29050
original SHA-256: 88B3FD3A6834ABF77396282672EA8AE119FC4F58CF8FB46B47565BCA44F08D2E
candidate SHA-256: 805D7D430B1DEE14C3C3D33442B3701689A077B0499752363B65F4362F15E13E
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:29347
original SHA-256: B976E0D064A0FC9AE58B2ACD8CE591C9266E921545A39B0B58BDEE4F3737D554
candidate SHA-256: B976E0D064A0FC9AE58B2ACD8CE591C9266E921545A39B0B58BDEE4F3737D554
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_004_counter_v1/reading_packets_v1/expanded_train_29347_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:30461
original SHA-256: 39CBB89FCD81060D75C044628A21D8FE3C4EA5C3B4D0EA439F314D03F520D649
candidate SHA-256: 16D84A3E3C6708AFD87ECF67A19E0300D051856F76B0F86A59C49A9ED41C3BA6
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

