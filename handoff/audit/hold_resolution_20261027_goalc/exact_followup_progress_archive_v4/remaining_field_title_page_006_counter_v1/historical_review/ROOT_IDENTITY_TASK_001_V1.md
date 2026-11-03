# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:71629
original SHA-256: 13E9960DC61165AA583215D7EC0CF8170AA1A9FF5455A19CBABE6C6877F2EB8F
candidate SHA-256: F0C2D85FA2AD3C5230F8847C4310200F0157AA89BA2D21FD39F946259F1ECF49
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:71722
original SHA-256: A3B85D9426087572E4AF744EE45DB3C23314A2D0B7EE9D5D2F7DC58A371F33FA
candidate SHA-256: 005CAA0A09D05D4570B7741C6AF5A6B956B60D95FADEF07B4B63108026B9680D
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:72063
original SHA-256: 1631BAFE4C1FE7BE1D6EB3FC5872FB4D47909103D76EE51E6DB8EBADC8FF484F
candidate SHA-256: C45C5A7334640B6E8D3DF43E037D7EF5CD535B9E8E7617374600B3461B254437
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:72091
original SHA-256: 2CE8E735FE9717081C6E263786F18F9766047ADB6B559EE29CC17CA7ED71E91A
candidate SHA-256: C107C5CDF2B9809B878C9AF13147CB57C4315AB237F0B1028E02DFE01EFCA57C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:72262
original SHA-256: BD7EDE98E4D2BED5D6523A011CC9F8D4FFBEE4BE8E565C0BF9D467C762F0D090
candidate SHA-256: BD7EDE98E4D2BED5D6523A011CC9F8D4FFBEE4BE8E565C0BF9D467C762F0D090
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_006_counter_v1/reading_packets_v1/expanded_train_72262_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_006_counter_v1/reading_packets_v1/expanded_train_72262_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_006_counter_v1/reading_packets_v1/expanded_train_72262_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

