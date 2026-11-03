# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:663732
original SHA-256: DB5139C30B45B2E9EAA5BA8A7CC5C558D9B156B05FE492FB333C3AC4AD492C32
candidate SHA-256: AAE613187BE61FB4C90CDAD362DF3021870087328933498B06651A7965D12681
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:663750
original SHA-256: F2EA4B8D2AEB096051A84AA9E0D152FE65E4668E68EA33FEFDB7EE4C9A2D320A
candidate SHA-256: F2EA4B8D2AEB096051A84AA9E0D152FE65E4668E68EA33FEFDB7EE4C9A2D320A
원문 frame 패킷: [1, 7]
최종 full_diff 패킷: [13, 13]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 13]
후보 중복만 있는 생략 가능 패킷: [8, 9, 10, 11, 12]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663750_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663750_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663750_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663750_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663750_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663750_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663750_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_052_counter_v1/reading_packets_v1/expanded_train_663750_0013.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:664007
original SHA-256: F1ACB67243E6E4E3531F7FA0D122500B64E6FE541457C42C7B3518D4A774C562
candidate SHA-256: FF28E0D40A2C09C0A43A4AD658443119AB375A0171545DCE6920C6F39760F675
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:664138
original SHA-256: 71E513427932E63C2A3BE74B5C1C077CA89BA579E0C8278CBD7B905171C739C6
candidate SHA-256: 9246BA113EFBB8E212B9899B9AD7CF8FF25055F0ED240F0F283C1CC5662C9432
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:664142
original SHA-256: 69362F6564E9AF71033C3E11C83FA8FF79FCBC831F4CA3469EE70F74789EB75F
candidate SHA-256: FBC7CFD1BD14A1CD7A42B3F4268C8932FE2EAB3CA891126C1CFFDF48C14C3ECE
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

