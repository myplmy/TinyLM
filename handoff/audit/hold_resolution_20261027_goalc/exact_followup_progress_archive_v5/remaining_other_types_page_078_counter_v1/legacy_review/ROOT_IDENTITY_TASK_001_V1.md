# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1071035
original SHA-256: A0DCC0A5058CB9ECFFDE90BBE210245A60851FEB3A3999C4E61AAD9656A1CD6F
candidate SHA-256: A0DCC0A5058CB9ECFFDE90BBE210245A60851FEB3A3999C4E61AAD9656A1CD6F
원문 frame 패킷: [1, 11]
최종 full_diff 패킷: [22, 22]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 22]
후보 중복만 있는 생략 가능 패킷: [12, 13, 14, 15, 16, 17, 18, 19, 20, 21]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071035_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071035_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071035_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071035_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071035_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071035_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071035_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071035_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071035_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071035_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071035_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071035_0022.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1071312
original SHA-256: D22F2D95C7B1ABF54664E6EED20842D206E59B49C117AC11D611FBDB3CAD5E87
candidate SHA-256: F12BF440EFC032BAB22CB0E705E1570BCCD97227CFC34CFA688CAD53A1FFA582
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1071393
original SHA-256: 133BFA370289392604858F930109F104C02EEBF07EA65B35A7C51D582FABFA52
candidate SHA-256: 133BFA370289392604858F930109F104C02EEBF07EA65B35A7C51D582FABFA52
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071393_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1071414
original SHA-256: A9CBEFF4446281AD761315B952B383FD466CB0828837F9827CF1468D69DC2BAA
candidate SHA-256: A9CBEFF4446281AD761315B952B383FD466CB0828837F9827CF1468D69DC2BAA
원문 frame 패킷: [1, 7]
최종 full_diff 패킷: [13, 13]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 13]
후보 중복만 있는 생략 가능 패킷: [8, 9, 10, 11, 12]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071414_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071414_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071414_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071414_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071414_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071414_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071414_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_078_counter_v1/reading_packets_v1/expanded_train_1071414_0013.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1071552
original SHA-256: 8EA6FF9F3B2BC0FAF3A7601F7F7FD5C0013A31D9F79AC36534E4A1BA5765B73B
candidate SHA-256: 98915C232283EC57671AC00D3A6CDCE0F0CADB1B7C41B8DC67CAE5BBC6499818
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

