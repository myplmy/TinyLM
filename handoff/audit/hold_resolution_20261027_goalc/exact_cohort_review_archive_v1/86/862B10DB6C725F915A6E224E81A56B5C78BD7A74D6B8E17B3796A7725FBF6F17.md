# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:180856
original SHA-256: 2D970074003265E48EFA208424C4149B488A461FD4E62EA8750708AF3066DFB6
candidate SHA-256: A2F1A2E56E063BBCA4EFDECF0B569654CDE90ED47E7E1E79030BBEAF5EE1F8BB
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:181570
original SHA-256: 59C2DE6FA66CAA4A51859F58F474EE48C7B97D9F7781603D68B138CD788529AD
candidate SHA-256: 59C2DE6FA66CAA4A51859F58F474EE48C7B97D9F7781603D68B138CD788529AD
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_010_counter_v1/reading_packets_v1/expanded_train_181570_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:181668
original SHA-256: 79670F3825628C2D8647B84A66C5E02EED6A8C185E64F0D8FA093042A1DAE96B
candidate SHA-256: EF86D2B4196CE0575276837D4ADFC8A9296DCE44D3260D1347713A1719F66AE3
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:181705
original SHA-256: A7967E1DE60FADAF549B8155FDD90A51CA43AD82A760225268175CF46AA571DE
candidate SHA-256: A7967E1DE60FADAF549B8155FDD90A51CA43AD82A760225268175CF46AA571DE
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_010_counter_v1/reading_packets_v1/expanded_train_181705_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_010_counter_v1/reading_packets_v1/expanded_train_181705_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:181880
original SHA-256: 0ACAFA16C46CCEDFDE7B631FCC09D653F946F8CEBEAFA58190DA3F50649881CD
candidate SHA-256: 785283A628E4E2E5A45D4560CA7566429D3790A19B147783879A1A8FF3C13303
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

