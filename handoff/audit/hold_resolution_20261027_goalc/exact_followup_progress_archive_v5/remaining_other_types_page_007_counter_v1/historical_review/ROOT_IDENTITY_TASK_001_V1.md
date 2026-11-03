# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:61965
original SHA-256: 107D62A511F674692CAF646A035D17196C49D6CB90ED5E7168287F445C25883B
candidate SHA-256: 107D62A511F674692CAF646A035D17196C49D6CB90ED5E7168287F445C25883B
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_007_counter_v1/reading_packets_v1/expanded_train_61965_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:62183
original SHA-256: 55D5657EAB74CBB50ABA4CFB61A83E22B9E42E5C5BB5FA3ED91DC767D8C32AE9
candidate SHA-256: 55D5657EAB74CBB50ABA4CFB61A83E22B9E42E5C5BB5FA3ED91DC767D8C32AE9
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_007_counter_v1/reading_packets_v1/expanded_train_62183_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:62302
original SHA-256: B9BC4937ED41AB50962AB032A0A7357484E446DE467D7B5E87C9BAE6E958C201
candidate SHA-256: 2D7A2CF690B9EA40341726FC352BA06E20B31732539C8453029F19B719BE86B6
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:62536
original SHA-256: 883C64CD963E71E2B2499825DA351B0F7E1647C2B6A133E6B38E5A8136684B9E
candidate SHA-256: 0D9761BD0BC3B4552F380933A10765262129CF00A729AD169ED70B4A2A435E1F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:62586
original SHA-256: 539C4B6A695F6A2CC9BCE5F0C0C47548937E5D04C8AE9661080A162575AEDC15
candidate SHA-256: A10023D33EAF54AB89B40BEFC40C68C73E65570C7C786DFAB84361FA4F5C0A4E
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

