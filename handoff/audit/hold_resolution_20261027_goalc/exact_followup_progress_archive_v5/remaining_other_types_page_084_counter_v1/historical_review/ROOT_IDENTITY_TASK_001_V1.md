# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1167816
original SHA-256: 43FE392065252C0D104C38D7FA46EC10F117DDA1CD9D3C19D324A04DBCE885CA
candidate SHA-256: 7C8A0BA1FC5495AC5D2ADEBADEEC002115CEDEB7B9BFE231EFC1420EBD141B0E
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1167864
original SHA-256: F1BC30F13D7D33C61D6C571A55028222284076A6E8BEAA595D7A497B1B838860
candidate SHA-256: 32449B414573E519D48E2315435911099317057597416D8729E1045E325C4C5A
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1168009
original SHA-256: A565BF7C1A4A7EA5534FE0477E0FB556BB5F07358A2BD3F81CAD713F25D51CA4
candidate SHA-256: A565BF7C1A4A7EA5534FE0477E0FB556BB5F07358A2BD3F81CAD713F25D51CA4
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [11, 11]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 11]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_084_counter_v1/reading_packets_v1/expanded_train_1168009_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_084_counter_v1/reading_packets_v1/expanded_train_1168009_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_084_counter_v1/reading_packets_v1/expanded_train_1168009_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_084_counter_v1/reading_packets_v1/expanded_train_1168009_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_084_counter_v1/reading_packets_v1/expanded_train_1168009_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_084_counter_v1/reading_packets_v1/expanded_train_1168009_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_084_counter_v1/reading_packets_v1/expanded_train_1168009_0011.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1168160
original SHA-256: 9C143E5C3113F9C968E6D0B1E9C9D76B317E7BDE0CDCF86D21E01383D04633CC
candidate SHA-256: 9C143E5C3113F9C968E6D0B1E9C9D76B317E7BDE0CDCF86D21E01383D04633CC
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_084_counter_v1/reading_packets_v1/expanded_train_1168160_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_084_counter_v1/reading_packets_v1/expanded_train_1168160_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_084_counter_v1/reading_packets_v1/expanded_train_1168160_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_084_counter_v1/reading_packets_v1/expanded_train_1168160_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1168336
original SHA-256: 1B1AF2C09CF2BF67C46C0CFB6A98A1BB71FB4A6CA81F6504D3FA551D4EC61303
candidate SHA-256: E4967B2B10F7706B8194504F5DA4D7595881AB71B89EC527758A0A2D31B48BCD
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

