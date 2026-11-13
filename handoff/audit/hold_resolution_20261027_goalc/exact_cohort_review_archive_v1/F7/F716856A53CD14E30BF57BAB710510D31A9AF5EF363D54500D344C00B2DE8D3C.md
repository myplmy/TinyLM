# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:523539
original SHA-256: 5855B1A76BB92CA7D0F1F441CFD5B7F7D60181C51519C97BCB95D9AF8617280C
candidate SHA-256: D26BA62CD6FFF72A627748E9F4C9B03D8E3A53B816ACE6352215C44163752550
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:523874
original SHA-256: E5C046225B4118DD11E1AADBC10E21DE8ED904C3655DE4375C4159E022B7F2F5
candidate SHA-256: E5C046225B4118DD11E1AADBC10E21DE8ED904C3655DE4375C4159E022B7F2F5
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_019_counter_v1/reading_packets_v1/expanded_train_523874_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_019_counter_v1/reading_packets_v1/expanded_train_523874_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_019_counter_v1/reading_packets_v1/expanded_train_523874_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:524154
original SHA-256: 42671F0B75E13C63B692810155E333C0183961730135517F1D9DE5057EB1B015
candidate SHA-256: 95199CE4D892972E148D333EF25EC3C21002ACEB31F146A16232A908E8E50E1F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:524213
original SHA-256: 3833973CDC139A8E9982D0EBD2F925DA44D831633E0E472F330EBD455EBA4FEB
candidate SHA-256: AD6BEBE7247617F9FBF7750E7C5A9B550902418A2C84AE0F3B33CDF662241300
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:525195
original SHA-256: DE4BCCB0D412BEBF2A6579ACF4E28134550FE085A389DC42209F1DCC39996885
candidate SHA-256: 1EC347D7D0EDEAD298AF9788C36D4B42C13838C0BD65AE98014790306BA9E368
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

