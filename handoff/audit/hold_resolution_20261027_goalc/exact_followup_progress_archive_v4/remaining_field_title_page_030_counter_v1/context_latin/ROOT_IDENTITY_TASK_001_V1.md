# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1041767
original SHA-256: C3DEF30497ACDB5E4BDC4074A8EDE58D5C5B88FD222F7514BA04190181228785
candidate SHA-256: 08538777A20588AE9F7FEEA9AD97A615997D0AE519FFEAF2F54FEFB005740A50
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1041918
original SHA-256: 73F49BFB12423B4BCF40E23D2B586DFBC575BF802CC7F8B2119B28E63CCDCA1F
candidate SHA-256: 73F49BFB12423B4BCF40E23D2B586DFBC575BF802CC7F8B2119B28E63CCDCA1F
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_030_counter_v1/reading_packets_v1/expanded_train_1041918_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1042202
original SHA-256: A3C2AC1CDBA8D7809F4BA90416232D3CC34C0AA9FF785BF57B42AA00A57AC0CD
candidate SHA-256: 1280B233CE2CE88C8F5D3664576D24530BE7E0F6D0DCBABC772D731008C7B28C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1042211
original SHA-256: B9BF7FD799D49D2A5FA7DBEB6236938BFDB4BDFE4C17BEBA8B2F2305DCF11FD6
candidate SHA-256: B9BF7FD799D49D2A5FA7DBEB6236938BFDB4BDFE4C17BEBA8B2F2305DCF11FD6
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_030_counter_v1/reading_packets_v1/expanded_train_1042211_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_030_counter_v1/reading_packets_v1/expanded_train_1042211_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1042266
original SHA-256: 240446B887E631069E3A6D476483629126D6559FFF1B965C01CEDB547189FB44
candidate SHA-256: 240446B887E631069E3A6D476483629126D6559FFF1B965C01CEDB547189FB44
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_030_counter_v1/reading_packets_v1/expanded_train_1042266_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

