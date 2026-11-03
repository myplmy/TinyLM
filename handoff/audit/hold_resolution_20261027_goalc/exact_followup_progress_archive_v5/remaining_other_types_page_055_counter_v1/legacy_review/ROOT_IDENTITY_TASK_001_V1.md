# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:703556
original SHA-256: 305D7317675B61918066CB1516AA09993ADA949EB8547AD8EF059EC184CF82F5
candidate SHA-256: 80409165F075AF44803CEB9386746B674B36CB035437A4A3B24DA162A599ADE5
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:703715
original SHA-256: 82769066CB6642836CC7F9CC93E98B0BEC815B2F26ADEF3F2AA21F06D3343F6E
candidate SHA-256: AB651CEF74F6AA84381F195203466EB49A2907F1F68AB8E14047F832AB11961F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:703772
original SHA-256: 9B4CF3252DBC129D650EF48E0ACE6344D4CB4DF5117CE262EDCEBBD8103FFBA5
candidate SHA-256: 9B4CF3252DBC129D650EF48E0ACE6344D4CB4DF5117CE262EDCEBBD8103FFBA5
원문 frame 패킷: [1, 14]
최종 full_diff 패킷: [28, 28]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 28]
후보 중복만 있는 생략 가능 패킷: [15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_055_counter_v1/reading_packets_v1/expanded_train_703772_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_055_counter_v1/reading_packets_v1/expanded_train_703772_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_055_counter_v1/reading_packets_v1/expanded_train_703772_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_055_counter_v1/reading_packets_v1/expanded_train_703772_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_055_counter_v1/reading_packets_v1/expanded_train_703772_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_055_counter_v1/reading_packets_v1/expanded_train_703772_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_055_counter_v1/reading_packets_v1/expanded_train_703772_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_055_counter_v1/reading_packets_v1/expanded_train_703772_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_055_counter_v1/reading_packets_v1/expanded_train_703772_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_055_counter_v1/reading_packets_v1/expanded_train_703772_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_055_counter_v1/reading_packets_v1/expanded_train_703772_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_055_counter_v1/reading_packets_v1/expanded_train_703772_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_055_counter_v1/reading_packets_v1/expanded_train_703772_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_055_counter_v1/reading_packets_v1/expanded_train_703772_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_055_counter_v1/reading_packets_v1/expanded_train_703772_0028.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:703908
original SHA-256: 2EC381E9CC17CCF569DB95AF62AE68A3AD16AD28493962C0CBECE0A8D28F3062
candidate SHA-256: 8C6144E4D8DE5A41AB6349665B52B5B131001C387302D640E8A16508852E2BBD
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:703991
original SHA-256: 9F82FC0208516875DD622E5EE3CF2105D913E12AADCA4C7B5DA8EC2D633D3E2F
candidate SHA-256: 9F82FC0208516875DD622E5EE3CF2105D913E12AADCA4C7B5DA8EC2D633D3E2F
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_055_counter_v1/reading_packets_v1/expanded_train_703991_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_055_counter_v1/reading_packets_v1/expanded_train_703991_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_055_counter_v1/reading_packets_v1/expanded_train_703991_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

