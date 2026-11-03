# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:332308
original SHA-256: 45594A221B1805D0539B600188A998170993C8F27E5BA410DB9BD4C77DB90B7C
candidate SHA-256: 45594A221B1805D0539B600188A998170993C8F27E5BA410DB9BD4C77DB90B7C
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_029_counter_v1/reading_packets_v1/expanded_train_332308_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_029_counter_v1/reading_packets_v1/expanded_train_332308_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:333159
original SHA-256: 7AF60B2EC63068B00535BE36835F6E165F3B0C3147E10F64B0C9BC763982D6D6
candidate SHA-256: BA3DBD186F22C83ED6009C9CBB8EC65A82F672CDEBCFEFA8EE53085F08691FC2
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:333299
original SHA-256: 4D81183239522DC72C5FD02CF23FF6ECA55D2FFC98E65EE5D16C44E90C17DC29
candidate SHA-256: 4D81183239522DC72C5FD02CF23FF6ECA55D2FFC98E65EE5D16C44E90C17DC29
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_029_counter_v1/reading_packets_v1/expanded_train_333299_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:333327
original SHA-256: 921263526F6B3DFF18726F8E5B88FEC0D67C1F1532D8CD0084AB238D09B904E4
candidate SHA-256: 921263526F6B3DFF18726F8E5B88FEC0D67C1F1532D8CD0084AB238D09B904E4
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_029_counter_v1/reading_packets_v1/expanded_train_333327_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:333334
original SHA-256: FF24BD450E7BB5B4FDC9536B24EE490AA13DDFAD1BD0FCAD1DDEF28B6B513FCE
candidate SHA-256: FF24BD450E7BB5B4FDC9536B24EE490AA13DDFAD1BD0FCAD1DDEF28B6B513FCE
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_029_counter_v1/reading_packets_v1/expanded_train_333334_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

