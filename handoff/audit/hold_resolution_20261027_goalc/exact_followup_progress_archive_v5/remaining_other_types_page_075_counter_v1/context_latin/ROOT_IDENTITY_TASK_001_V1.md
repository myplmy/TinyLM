# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1028680
original SHA-256: AF12CE9F8AC39BE93590033907879E9800D1B027BAFF5E88AA71B25D38F90422
candidate SHA-256: D129DFA6A4207AF21799CC21F876D40623E429F0C98D914041C97D397B2A5BAE
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1028688
original SHA-256: 78F3060CEE57483A034894D3321B5EFADA61D27705532261BF189A4453E2DB85
candidate SHA-256: 7E4EBF901EF7550887D2582B2538C396E0B6BCEB22D92E495EADD3C72C6465C5
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1028747
original SHA-256: F905215E40D634D8BF1C6DB1D5D06E147AC8C4BE0259F32705EB01C2489AEE2B
candidate SHA-256: F905215E40D634D8BF1C6DB1D5D06E147AC8C4BE0259F32705EB01C2489AEE2B
원문 frame 패킷: [1, 24]
최종 full_diff 패킷: [47, 47]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 47]
후보 중복만 있는 생략 가능 패킷: [25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028747_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028747_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028747_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028747_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028747_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028747_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028747_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028747_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028747_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028747_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028747_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028747_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028747_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028747_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028747_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028747_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028747_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028747_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028747_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028747_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028747_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028747_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028747_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028747_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028747_0047.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1028798
original SHA-256: 53500A25630DA3FA54ACCF0EAD96C241CD72D949A67E901A6550659FDA709A9D
candidate SHA-256: 53500A25630DA3FA54ACCF0EAD96C241CD72D949A67E901A6550659FDA709A9D
원문 frame 패킷: [1, 18]
최종 full_diff 패킷: [36, 36]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 36]
후보 중복만 있는 생략 가능 패킷: [19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028798_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028798_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028798_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028798_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028798_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028798_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028798_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028798_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028798_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028798_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028798_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028798_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028798_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028798_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028798_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028798_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028798_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028798_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028798_0036.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1028801
original SHA-256: BD4D983250529B7B2833001C7A2EC7AB1D3B91034A048722CA907AE182FC7F01
candidate SHA-256: BD4D983250529B7B2833001C7A2EC7AB1D3B91034A048722CA907AE182FC7F01
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028801_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028801_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028801_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028801_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1028801_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

