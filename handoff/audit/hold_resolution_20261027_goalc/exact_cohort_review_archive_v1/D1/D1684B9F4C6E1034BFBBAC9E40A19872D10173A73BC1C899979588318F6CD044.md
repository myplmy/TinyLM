# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:241493
original SHA-256: DD3A7AE2D1C566403C227BF71DE407B506C5B797F8435DB17C4EC45A31D97317
candidate SHA-256: 80B5377B2AE03D73A88607AE88CE0E34D29EACCD1887423D632ADB5D81F307D8
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:241558
original SHA-256: F2BCE92E22436E33AEEEF815A41E33912394F5343D42649A988E939F631B1572
candidate SHA-256: F2BCE92E22436E33AEEEF815A41E33912394F5343D42649A988E939F631B1572
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_012_counter_v1/reading_packets_v1/expanded_train_241558_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_012_counter_v1/reading_packets_v1/expanded_train_241558_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_012_counter_v1/reading_packets_v1/expanded_train_241558_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:241613
original SHA-256: 952C9E4EF715CCAFB8B65A2F763CEA30FF1689116DDC6726A2B5CD28B1CCA9CD
candidate SHA-256: 952C9E4EF715CCAFB8B65A2F763CEA30FF1689116DDC6726A2B5CD28B1CCA9CD
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_012_counter_v1/reading_packets_v1/expanded_train_241613_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_012_counter_v1/reading_packets_v1/expanded_train_241613_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_012_counter_v1/reading_packets_v1/expanded_train_241613_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:241620
original SHA-256: EAA6D678D5A74871AF70C220F17803AD919BB32A404AE4FB8F6C237B9933148C
candidate SHA-256: 5CD5DAA54CBDFB05BA59FCC79941AB8F75BE1ACB721668B907AFC65665B05D13
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:241943
original SHA-256: C15D04D80E2918F0CDAAA565B681618CFB86C24D653CFEBE8834B0143DB7A952
candidate SHA-256: C15D04D80E2918F0CDAAA565B681618CFB86C24D653CFEBE8834B0143DB7A952
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_012_counter_v1/reading_packets_v1/expanded_train_241943_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_012_counter_v1/reading_packets_v1/expanded_train_241943_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_012_counter_v1/reading_packets_v1/expanded_train_241943_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

