# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:241097
original SHA-256: A1F625FFDA089CA532CEBCB0F10397D8935579C30F2803DD758B8BD1FF1CFB51
candidate SHA-256: A1F625FFDA089CA532CEBCB0F10397D8935579C30F2803DD758B8BD1FF1CFB51
원문 frame 패킷: [1, 8]
최종 full_diff 패킷: [16, 16]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 16]
후보 중복만 있는 생략 가능 패킷: [9, 10, 11, 12, 13, 14, 15]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_012_counter_v1/reading_packets_v1/expanded_train_241097_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_012_counter_v1/reading_packets_v1/expanded_train_241097_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_012_counter_v1/reading_packets_v1/expanded_train_241097_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_012_counter_v1/reading_packets_v1/expanded_train_241097_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_012_counter_v1/reading_packets_v1/expanded_train_241097_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_012_counter_v1/reading_packets_v1/expanded_train_241097_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_012_counter_v1/reading_packets_v1/expanded_train_241097_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_012_counter_v1/reading_packets_v1/expanded_train_241097_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_012_counter_v1/reading_packets_v1/expanded_train_241097_0016.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:241143
original SHA-256: 7B5C4F5C9B4687E25171E6503AF47CAF503521A069251B04EF38C72DAC5C5EDF
candidate SHA-256: 7B5C4F5C9B4687E25171E6503AF47CAF503521A069251B04EF38C72DAC5C5EDF
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_012_counter_v1/reading_packets_v1/expanded_train_241143_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_012_counter_v1/reading_packets_v1/expanded_train_241143_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:241326
original SHA-256: A17FCCA8B030573B20A150ECF700CC3822AEB26ABFBC79DEA50736B1BBC36B44
candidate SHA-256: A17FCCA8B030573B20A150ECF700CC3822AEB26ABFBC79DEA50736B1BBC36B44
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_012_counter_v1/reading_packets_v1/expanded_train_241326_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:241583
original SHA-256: 78D49879F84699AF395278D792A083980DDD0228715EBC083DA2117E4639DE93
candidate SHA-256: 78D49879F84699AF395278D792A083980DDD0228715EBC083DA2117E4639DE93
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_012_counter_v1/reading_packets_v1/expanded_train_241583_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:241587
original SHA-256: 4FE7E79B7F8C1C2E0D0737C92B9643773B03850F7F4B1AFEB1BA53FA0DE418EB
candidate SHA-256: C7449663ED9677D218B86FDCA9191FEF274BC5FC63E731CDEBCC1564B60DE1D9
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

