# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:72052
original SHA-256: 9150EADCEA05A1B5827F667AF4D7FA8C90F371C115680072FB15788592B94679
candidate SHA-256: 9150EADCEA05A1B5827F667AF4D7FA8C90F371C115680072FB15788592B94679
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_006_counter_v1/reading_packets_v1/expanded_train_72052_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_006_counter_v1/reading_packets_v1/expanded_train_72052_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_006_counter_v1/reading_packets_v1/expanded_train_72052_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:72160
original SHA-256: 1AD434376EE76A0BD3BB006FB7C93269ECDD77D6BE5C1215FB5F5D332C6676AE
candidate SHA-256: 1AD434376EE76A0BD3BB006FB7C93269ECDD77D6BE5C1215FB5F5D332C6676AE
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_006_counter_v1/reading_packets_v1/expanded_train_72160_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_006_counter_v1/reading_packets_v1/expanded_train_72160_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:72172
original SHA-256: 3BC8D2DF899B7AF48AAC718FF82F51617C87A4AF0C47EBC1550C134BFF14E865
candidate SHA-256: 3BC8D2DF899B7AF48AAC718FF82F51617C87A4AF0C47EBC1550C134BFF14E865
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_006_counter_v1/reading_packets_v1/expanded_train_72172_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_006_counter_v1/reading_packets_v1/expanded_train_72172_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_006_counter_v1/reading_packets_v1/expanded_train_72172_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_006_counter_v1/reading_packets_v1/expanded_train_72172_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_006_counter_v1/reading_packets_v1/expanded_train_72172_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:72258
original SHA-256: B585F806A481622753A4836E7739388F8D8EA3E6086088F5241C5D4519C89262
candidate SHA-256: 6CDA9D9B492726B665D61C5C680D37FEB741D2ED4EAD455B5D7A00D219D71F2C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:72645
original SHA-256: 25CC5525F3E6635EDF9A608D674649C8B8F6C14BF43A95B78BA50600DB2B811B
candidate SHA-256: 25CC5525F3E6635EDF9A608D674649C8B8F6C14BF43A95B78BA50600DB2B811B
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_006_counter_v1/reading_packets_v1/expanded_train_72645_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_006_counter_v1/reading_packets_v1/expanded_train_72645_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

