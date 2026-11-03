# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1264882
original SHA-256: 6E41A5D6BFA5A5F60F363F7E7C051E263BA9E1C464B7CF2B9C627197F37907EF
candidate SHA-256: 6E41A5D6BFA5A5F60F363F7E7C051E263BA9E1C464B7CF2B9C627197F37907EF
원문 frame 패킷: [1, 7]
최종 full_diff 패킷: [13, 13]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 13]
후보 중복만 있는 생략 가능 패킷: [8, 9, 10, 11, 12]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_090_counter_v1/reading_packets_v1/expanded_train_1264882_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_090_counter_v1/reading_packets_v1/expanded_train_1264882_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_090_counter_v1/reading_packets_v1/expanded_train_1264882_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_090_counter_v1/reading_packets_v1/expanded_train_1264882_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_090_counter_v1/reading_packets_v1/expanded_train_1264882_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_090_counter_v1/reading_packets_v1/expanded_train_1264882_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_090_counter_v1/reading_packets_v1/expanded_train_1264882_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_090_counter_v1/reading_packets_v1/expanded_train_1264882_0013.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1265313
original SHA-256: D275170FC2405D2B43C9E17AE20B89A68132772E72355FEF484C65F678174AAF
candidate SHA-256: D275170FC2405D2B43C9E17AE20B89A68132772E72355FEF484C65F678174AAF
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_090_counter_v1/reading_packets_v1/expanded_train_1265313_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1265574
original SHA-256: 54CBD6C5594898E5E4DF93BA1D8112BF8F5D40C5AD0D83E60602AB6F8BCEDFE9
candidate SHA-256: 54CBD6C5594898E5E4DF93BA1D8112BF8F5D40C5AD0D83E60602AB6F8BCEDFE9
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [11, 11]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 11]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_090_counter_v1/reading_packets_v1/expanded_train_1265574_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_090_counter_v1/reading_packets_v1/expanded_train_1265574_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_090_counter_v1/reading_packets_v1/expanded_train_1265574_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_090_counter_v1/reading_packets_v1/expanded_train_1265574_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_090_counter_v1/reading_packets_v1/expanded_train_1265574_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_090_counter_v1/reading_packets_v1/expanded_train_1265574_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_090_counter_v1/reading_packets_v1/expanded_train_1265574_0011.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1265643
original SHA-256: A49A01E3065374DA57703838350A3D697975BD5CD4ACF02A3A06CF98FD487AEF
candidate SHA-256: 37ADA7A3F97E7C7637530417024A298A356772CD684E2A26ABCCF34EC0EAFD7F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1265733
original SHA-256: 54BC3ABB7E7B45A23CC2D0461E64A2A51423D5E8144415C75C573F8F45F8472A
candidate SHA-256: 9BFCC8C5FF7C66238621392FCF85013C26A2287A22E52624E493146E2A65C035
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

