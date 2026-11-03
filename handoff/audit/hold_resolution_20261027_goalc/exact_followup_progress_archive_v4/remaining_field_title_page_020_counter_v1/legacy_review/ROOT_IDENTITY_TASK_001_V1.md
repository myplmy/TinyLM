# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:569661
original SHA-256: 2956E5D1B4A511EECB7A1D90C8C283C24330E628AF78705AF3B4FF3C6B3BFF52
candidate SHA-256: 2956E5D1B4A511EECB7A1D90C8C283C24330E628AF78705AF3B4FF3C6B3BFF52
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_020_counter_v1/reading_packets_v1/expanded_train_569661_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:570014
original SHA-256: F9637D20DF11A5FB72DF582D787A571653913DBA874D5D219BE029809D8743E3
candidate SHA-256: F9637D20DF11A5FB72DF582D787A571653913DBA874D5D219BE029809D8743E3
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_020_counter_v1/reading_packets_v1/expanded_train_570014_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_020_counter_v1/reading_packets_v1/expanded_train_570014_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:570302
original SHA-256: 724B38993B9828B6FAD10EE79FDF2A66756DC53A83C01ED044B7AC4DDF133800
candidate SHA-256: D7B01F86A7E9F42D8F1AC6360FF5DD84711D276CA8CECA58E8887BFA21DAAF53
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:570484
original SHA-256: AC461D5381023B2C69FC917A45D2FBD84179CAB2D1570D87D2A91C9B9E3F80A1
candidate SHA-256: AC461D5381023B2C69FC917A45D2FBD84179CAB2D1570D87D2A91C9B9E3F80A1
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_020_counter_v1/reading_packets_v1/expanded_train_570484_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:570857
original SHA-256: 90D33AF415F701AC10F10FFED9531AC98077CA392E0529C455938ECEDBC0208C
candidate SHA-256: 90D33AF415F701AC10F10FFED9531AC98077CA392E0529C455938ECEDBC0208C
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_020_counter_v1/reading_packets_v1/expanded_train_570857_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_020_counter_v1/reading_packets_v1/expanded_train_570857_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

