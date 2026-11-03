# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:792235
original SHA-256: 45771F2088A10E6DF5A8FE31E7743BD543E4EC942CB19991B8E20F1200C4E627
candidate SHA-256: 8F329F2B3438A05B49787F47C42A5C9464CE6FE478385C1008E1203718099AC0
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:792561
original SHA-256: 14024EE57623B29488B50104FA0762AF5C19EB8E3AED5A953B11FC86F58A9559
candidate SHA-256: 14024EE57623B29488B50104FA0762AF5C19EB8E3AED5A953B11FC86F58A9559
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_792561_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:792590
original SHA-256: E98ED7B17DE4B34C89CD7A9E92B08DBE1499208199E7DD837961279F1A41042B
candidate SHA-256: E98ED7B17DE4B34C89CD7A9E92B08DBE1499208199E7DD837961279F1A41042B
원문 frame 패킷: [1, 16]
최종 full_diff 패킷: [32, 32]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 32]
후보 중복만 있는 생략 가능 패킷: [17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_792590_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_792590_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_792590_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_792590_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_792590_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_792590_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_792590_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_792590_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_792590_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_792590_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_792590_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_792590_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_792590_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_792590_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_792590_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_792590_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_792590_0032.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:792610
original SHA-256: 5027B6180A536819DDA4D2769BE91FA830320A7F7DB5F45EBB90C47496619110
candidate SHA-256: 368616C5BE2A6F2EB553069AC10C82AC279A3F45547119493D36928B4561968C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:792661
original SHA-256: 47A5859CAAFD87FE64BCA35509B409F4B4C663FA6728D0EEC5B624162E54FA30
candidate SHA-256: 66D4ABAAA2E1454D5CC709ADBD17DF1AAFB35B579C8F4EDCE0B62643C97A811B
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

