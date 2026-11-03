# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:73648
original SHA-256: 2A34352AAEED02AC9F159C4CE44EBFD1188C8695E1BA85C4A0373B529D0C8AFD
candidate SHA-256: 2A34352AAEED02AC9F159C4CE44EBFD1188C8695E1BA85C4A0373B529D0C8AFD
원문 frame 패킷: [1, 9]
최종 full_diff 패킷: [17, 17]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 17]
후보 중복만 있는 생략 가능 패킷: [10, 11, 12, 13, 14, 15, 16]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_008_counter_v1/reading_packets_v1/expanded_train_73648_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_008_counter_v1/reading_packets_v1/expanded_train_73648_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_008_counter_v1/reading_packets_v1/expanded_train_73648_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_008_counter_v1/reading_packets_v1/expanded_train_73648_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_008_counter_v1/reading_packets_v1/expanded_train_73648_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_008_counter_v1/reading_packets_v1/expanded_train_73648_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_008_counter_v1/reading_packets_v1/expanded_train_73648_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_008_counter_v1/reading_packets_v1/expanded_train_73648_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_008_counter_v1/reading_packets_v1/expanded_train_73648_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_008_counter_v1/reading_packets_v1/expanded_train_73648_0017.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:73713
original SHA-256: 68D46D44CFB56B2B1B73FF1E79E4FE0445759278173BE56B0E2420EB412B3526
candidate SHA-256: 68D46D44CFB56B2B1B73FF1E79E4FE0445759278173BE56B0E2420EB412B3526
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_008_counter_v1/reading_packets_v1/expanded_train_73713_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:73730
original SHA-256: 40CE36655458D313F6DB3BC547DA257E8F8160049C4D6EF19AD6D2EF3A93AE99
candidate SHA-256: 22533E71B7FF4161989B89947209099DED51BA5A97A825B9E8668D048F34C938
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:74061
original SHA-256: A3C940EF5E85A07386E10482BC95578E2F91BFD23BFEB210BA107CAFCF15BC72
candidate SHA-256: A3C940EF5E85A07386E10482BC95578E2F91BFD23BFEB210BA107CAFCF15BC72
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_008_counter_v1/reading_packets_v1/expanded_train_74061_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_008_counter_v1/reading_packets_v1/expanded_train_74061_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_008_counter_v1/reading_packets_v1/expanded_train_74061_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_008_counter_v1/reading_packets_v1/expanded_train_74061_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:74350
original SHA-256: DF4A1271D3CC137A91BA66E54D896DBAAA2D197C9DA36171A89A185D7874FAE4
candidate SHA-256: F97A180BDF1D75D18A53C867CBCAEE9AE5005A591E0814945A1B2E6EF2C0899C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

