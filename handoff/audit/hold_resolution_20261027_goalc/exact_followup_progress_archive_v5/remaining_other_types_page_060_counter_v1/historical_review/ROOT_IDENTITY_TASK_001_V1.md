# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:782281
original SHA-256: CA1F82957E09578B0F5EBBC4A7008EF35792B55D01920B2E0EAF72B91318712F
candidate SHA-256: CA1F82957E09578B0F5EBBC4A7008EF35792B55D01920B2E0EAF72B91318712F
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_060_counter_v1/reading_packets_v1/expanded_train_782281_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_060_counter_v1/reading_packets_v1/expanded_train_782281_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_060_counter_v1/reading_packets_v1/expanded_train_782281_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_060_counter_v1/reading_packets_v1/expanded_train_782281_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_060_counter_v1/reading_packets_v1/expanded_train_782281_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:782332
original SHA-256: 5955A8C4D85BC82036C48C0BDDFCDEE5B4622C2CB6DECEF0817ED14E3D99946D
candidate SHA-256: 5955A8C4D85BC82036C48C0BDDFCDEE5B4622C2CB6DECEF0817ED14E3D99946D
원문 frame 패킷: [1, 23]
최종 full_diff 패킷: [45, 45]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 45]
후보 중복만 있는 생략 가능 패킷: [24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_060_counter_v1/reading_packets_v1/expanded_train_782332_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_060_counter_v1/reading_packets_v1/expanded_train_782332_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_060_counter_v1/reading_packets_v1/expanded_train_782332_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_060_counter_v1/reading_packets_v1/expanded_train_782332_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_060_counter_v1/reading_packets_v1/expanded_train_782332_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_060_counter_v1/reading_packets_v1/expanded_train_782332_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_060_counter_v1/reading_packets_v1/expanded_train_782332_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_060_counter_v1/reading_packets_v1/expanded_train_782332_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_060_counter_v1/reading_packets_v1/expanded_train_782332_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_060_counter_v1/reading_packets_v1/expanded_train_782332_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_060_counter_v1/reading_packets_v1/expanded_train_782332_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_060_counter_v1/reading_packets_v1/expanded_train_782332_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_060_counter_v1/reading_packets_v1/expanded_train_782332_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_060_counter_v1/reading_packets_v1/expanded_train_782332_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_060_counter_v1/reading_packets_v1/expanded_train_782332_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_060_counter_v1/reading_packets_v1/expanded_train_782332_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_060_counter_v1/reading_packets_v1/expanded_train_782332_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_060_counter_v1/reading_packets_v1/expanded_train_782332_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_060_counter_v1/reading_packets_v1/expanded_train_782332_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_060_counter_v1/reading_packets_v1/expanded_train_782332_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_060_counter_v1/reading_packets_v1/expanded_train_782332_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_060_counter_v1/reading_packets_v1/expanded_train_782332_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_060_counter_v1/reading_packets_v1/expanded_train_782332_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_060_counter_v1/reading_packets_v1/expanded_train_782332_0045.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:782604
original SHA-256: C7581CC054FA859DD29492353940FBBAAD21C4D1D79D8FB761F3FAFB89B9F274
candidate SHA-256: C7581CC054FA859DD29492353940FBBAAD21C4D1D79D8FB761F3FAFB89B9F274
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [10, 10]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 10]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8, 9]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_060_counter_v1/reading_packets_v1/expanded_train_782604_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_060_counter_v1/reading_packets_v1/expanded_train_782604_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_060_counter_v1/reading_packets_v1/expanded_train_782604_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_060_counter_v1/reading_packets_v1/expanded_train_782604_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_060_counter_v1/reading_packets_v1/expanded_train_782604_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_060_counter_v1/reading_packets_v1/expanded_train_782604_0010.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:782800
original SHA-256: 46ECFE6E2C405CEC20F75636884976C51B8160974DC0DE2625302F8A5C679AE9
candidate SHA-256: 03D8B1066D0DBC10140CC12F1823A9C6654D05F3846E2E4A9DC6C479A2567CDB
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:782845
original SHA-256: 0F22E6E262A1E0939644BFD7CD3A44A9197E5E594C9DD7FB1EADDEBFA90250E1
candidate SHA-256: 0F22E6E262A1E0939644BFD7CD3A44A9197E5E594C9DD7FB1EADDEBFA90250E1
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_060_counter_v1/reading_packets_v1/expanded_train_782845_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_060_counter_v1/reading_packets_v1/expanded_train_782845_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_060_counter_v1/reading_packets_v1/expanded_train_782845_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

