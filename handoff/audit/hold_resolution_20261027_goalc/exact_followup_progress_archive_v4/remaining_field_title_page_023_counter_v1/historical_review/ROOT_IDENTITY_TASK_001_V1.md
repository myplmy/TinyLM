# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:694872
original SHA-256: 409040C769330700C2BE67D9899617D15D5B8CFC253C5D2CD24C6D6D2B4EB2E7
candidate SHA-256: 409040C769330700C2BE67D9899617D15D5B8CFC253C5D2CD24C6D6D2B4EB2E7
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_023_counter_v1/reading_packets_v1/expanded_train_694872_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_023_counter_v1/reading_packets_v1/expanded_train_694872_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_023_counter_v1/reading_packets_v1/expanded_train_694872_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_023_counter_v1/reading_packets_v1/expanded_train_694872_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:694995
original SHA-256: 478CB0AFC6FDA54BA331BD427FC33D43F258CC4232822DD3E048771B9F1AE17A
candidate SHA-256: 478CB0AFC6FDA54BA331BD427FC33D43F258CC4232822DD3E048771B9F1AE17A
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_023_counter_v1/reading_packets_v1/expanded_train_694995_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:695047
original SHA-256: 50C7E78EB8CCE20D41353331F0F7272954063432A7895318EB67B9C9DFD6B492
candidate SHA-256: 1579ECA0EF98CFDD1B4893D724EA677CF30E495762B071F6575E7A9572EACC64
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:695113
original SHA-256: 17B86DFCC23F0D0A4DC9F29BD0D4FE20FBA114568912D4264972B7909D7908B5
candidate SHA-256: 63C6CA3A248DBAAAB27DA3A345F20C15ECE896E1FC54268F3B7C585B970C5327
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:695754
original SHA-256: 9E745E7E5AE3ED22C8C2AC68A27FB05597C8612B4014D620A400690BEEA16F63
candidate SHA-256: 02904F8ED20DB6479B1DA05130B22F629E4B7C33E9768E4FB92202571BFC8F5C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

