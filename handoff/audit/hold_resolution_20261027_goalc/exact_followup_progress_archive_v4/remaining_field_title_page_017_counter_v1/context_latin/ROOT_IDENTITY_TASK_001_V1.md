# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:452401
original SHA-256: 7097BF819AF32F6B4E24900822E486108FFC3B31265E18545EC2315A8A9A2374
candidate SHA-256: 705562A1D285072F6C8B6D45453E649906415E31727F9B0EF125D2F9D1070023
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:452640
original SHA-256: 46057EF6E111F75174D4318F67536766F12E330699DB4BD06FB1326D9D5D3F8A
candidate SHA-256: 46057EF6E111F75174D4318F67536766F12E330699DB4BD06FB1326D9D5D3F8A
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_017_counter_v1/reading_packets_v1/expanded_train_452640_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_017_counter_v1/reading_packets_v1/expanded_train_452640_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_017_counter_v1/reading_packets_v1/expanded_train_452640_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:452769
original SHA-256: FE768B68007E83DFABD536938BD456511600421909F8C35B2C5FB3979D929665
candidate SHA-256: 8B9AECAB7B67DAE03A29B2C53A4CCF13136E4583A45C112A265F5FF3058B5BC8
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:453569
original SHA-256: 0B1E0E2D7C4F758551011270122DE9B0E0D9DF2C1671BADCB49EB71913B0DF21
candidate SHA-256: 0B1E0E2D7C4F758551011270122DE9B0E0D9DF2C1671BADCB49EB71913B0DF21
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_017_counter_v1/reading_packets_v1/expanded_train_453569_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:453657
original SHA-256: C3D2D07316E8BA20344FE200E0119BD2243B353AE6B8B163053809B69311F26A
candidate SHA-256: C3D2D07316E8BA20344FE200E0119BD2243B353AE6B8B163053809B69311F26A
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_017_counter_v1/reading_packets_v1/expanded_train_453657_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

