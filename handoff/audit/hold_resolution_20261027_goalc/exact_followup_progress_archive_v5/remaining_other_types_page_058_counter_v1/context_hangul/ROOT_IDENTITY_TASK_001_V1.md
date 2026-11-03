# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:747896
original SHA-256: A7296A6A6A1FA484B61A4D1D129B59F11C2BBFAF66172738011532B6FF91928A
candidate SHA-256: 1EB7CA7829B68CDBD2DB1AC96B1DFFA5EBCA0024C057E992D88C4DAED30C0B95
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:747936
original SHA-256: 791812A73A16B4690DB3D364F6A6E16314FD65D2845AC46AD8477E5C5DCAB4DA
candidate SHA-256: D86ABE8A00B665C7EBE2501B7704ACB6530EF9D6392BC0244A28064C0B114305
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:748206
original SHA-256: 3C1851EF75E98522064B391A0DA9DE5B6F2D4DC0E236985277F3BCDAC41D875B
candidate SHA-256: EA28D947CCA087468CB410BE8283DB6CCDCCFE46F7A5731027AC333756CB9995
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:748247
original SHA-256: 09268AE575FF3D3823E39D962AB59F8BDBF2272FCE33CC374C5CB6719B6AD333
candidate SHA-256: D8920B6DF136CCE112F00AFAAB0793598BD578098552823774374804181EEB8B
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:748993
original SHA-256: CB2F79CC0E8EDF05DB76FA6AF9404F64046CDD31EAC183185AA523D0F3127F48
candidate SHA-256: CB2F79CC0E8EDF05DB76FA6AF9404F64046CDD31EAC183185AA523D0F3127F48
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_748993_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_748993_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_748993_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_058_counter_v1/reading_packets_v1/expanded_train_748993_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

