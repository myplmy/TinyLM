# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:401002
original SHA-256: 931B896180A8B8BF1BE3B50CBE894F7DF47D190912546AAAD8DB12065128BE83
candidate SHA-256: CE5060C220BE7441D885DA110C42BE7F1F13B574B98BEACC5118ABEEDEEC0623
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:402565
original SHA-256: DBD9C6FD5BAEDAE7FE5B7268E449BF88AE6F8CD99BF324356A86888586D5FBC7
candidate SHA-256: DBD9C6FD5BAEDAE7FE5B7268E449BF88AE6F8CD99BF324356A86888586D5FBC7
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_402565_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:403537
original SHA-256: 761482921252CF5BC95CDD5D7DAB2AFBD5870F125206AACBBCC7D9E84D76FD6D
candidate SHA-256: 14AE14BDEFB56E3E66F5B77DDFF47FF2D22AF411FA3169C505E1CA6036EA68E7
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:403717
original SHA-256: 735F351AC0A3FC9486D5FB9721C52BF339D3113BF49D8D27074033C93F96F343
candidate SHA-256: D1596AA326C993BF0BF4108B96362F8188950BB8F88D492E86BF3ED65C92ED03
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:404291
original SHA-256: DF4AC9CFD166BBCD2D76AE57EB21BB683727F8E4352BC9AF220B78648C9FD792
candidate SHA-256: FE45E7275CEE40B1332CD7C4C136219888B7B84964B17226DC91BC13A2B987E3
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

