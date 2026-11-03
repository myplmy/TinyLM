# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:873202
original SHA-256: D50035E7FEE02831F01D60657C4D28345188ACDFB6FA0C70152AE3D0C87C0BDD
candidate SHA-256: D50035E7FEE02831F01D60657C4D28345188ACDFB6FA0C70152AE3D0C87C0BDD
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_027_counter_v1/reading_packets_v1/expanded_train_873202_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_027_counter_v1/reading_packets_v1/expanded_train_873202_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:873545
original SHA-256: 58B9C02BA7F8E36F278181AB6FAA5066818CDDC8514216B05203C0446D6B6425
candidate SHA-256: 58B9C02BA7F8E36F278181AB6FAA5066818CDDC8514216B05203C0446D6B6425
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_027_counter_v1/reading_packets_v1/expanded_train_873545_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:873638
original SHA-256: 6A1C9A23F0CE2E504D81C3C31287323BAEFDA39EDF70242503E33E196AADC701
candidate SHA-256: 6A1C9A23F0CE2E504D81C3C31287323BAEFDA39EDF70242503E33E196AADC701
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_027_counter_v1/reading_packets_v1/expanded_train_873638_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:873847
original SHA-256: 06368BF4C1663F94ECF4E1A354155CCCFA12B3BB649D30FDABC417D2632218EC
candidate SHA-256: B408D3A82D51ACE8E0C43C461D5FE1A8A4CDEAF402177BAC5207EA81BBC7BF7D
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:874145
original SHA-256: B95FA3B5BE37CDEA57FD8DDF639E387068755790C1B6CBB246A3684DC76B7B76
candidate SHA-256: DD16F217672EAA4CFB708193B57999BDC0A69FB293EF701F038713A62977CBBA
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

