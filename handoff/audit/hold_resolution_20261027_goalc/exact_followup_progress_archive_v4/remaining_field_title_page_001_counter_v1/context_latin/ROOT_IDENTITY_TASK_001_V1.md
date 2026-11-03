# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:159
original SHA-256: E4FFDF2B78CB6A7AAB1AB63F43B0E84E6C9B4A45F67B851B7D43C3E01009267A
candidate SHA-256: 9482B5700AA5BB904EF8B4EDAF8353D905A65D72F8016178198ADD8DBD85B132
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1691
original SHA-256: 6464044ECBE2C0FBDF3DB873838BAAA8666634DE7CE78F05E21DE749B0A59A8C
candidate SHA-256: 6464044ECBE2C0FBDF3DB873838BAAA8666634DE7CE78F05E21DE749B0A59A8C
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_001_counter_v1/reading_packets_v1/expanded_train_1691_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_001_counter_v1/reading_packets_v1/expanded_train_1691_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_001_counter_v1/reading_packets_v1/expanded_train_1691_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_001_counter_v1/reading_packets_v1/expanded_train_1691_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1877
original SHA-256: 84C25CABEF6AD1E83C606C01165F3ABCD7FD75BCD4819342A88588E328634618
candidate SHA-256: 9F2FFB598CA005A682131E936D49BDEF949B0AE08183C5A058A1D1176E46526C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:196
original SHA-256: 30169D892F512C1EEC2FB41DA760F9BDFF573BEAEC81115F7D0EFBC0ABD9A49B
candidate SHA-256: 30169D892F512C1EEC2FB41DA760F9BDFF573BEAEC81115F7D0EFBC0ABD9A49B
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_001_counter_v1/reading_packets_v1/expanded_train_196_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_001_counter_v1/reading_packets_v1/expanded_train_196_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:201
original SHA-256: 29FC849AE55AC95D0EF5BAAA9364EAB7776C0BA257E3742C8EAA173943403FE3
candidate SHA-256: 26B1FDCAC2D2F6911EBF862EFBE720910446DB1AC80588A7F294D920DA89826A
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

