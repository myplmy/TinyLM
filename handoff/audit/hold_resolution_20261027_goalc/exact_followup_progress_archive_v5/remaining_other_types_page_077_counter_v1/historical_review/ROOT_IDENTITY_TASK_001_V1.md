# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1060579
original SHA-256: D7F34398884A5FAEDB43AA3F1C36AED8DE4790C185B530602E0FB36767BE5E21
candidate SHA-256: D7F34398884A5FAEDB43AA3F1C36AED8DE4790C185B530602E0FB36767BE5E21
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060579_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060579_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060579_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060579_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060579_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1060596
original SHA-256: 17AB73D9C58E46F7930BE2BEF2FA0F27B814B9FC916C8D79AB16F18F6A5FEA27
candidate SHA-256: 17AB73D9C58E46F7930BE2BEF2FA0F27B814B9FC916C8D79AB16F18F6A5FEA27
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060596_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1060647
original SHA-256: 9753FC2D7C49F7A91F60A5CB8AF94B8A0CC97541B53C7915E1121F2F794296D0
candidate SHA-256: 3E20C1652CC7F11F3FBA15D70752BBEF727E49941D6AFD157078E63C4070B29E
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1061016
original SHA-256: 0A0315F88BAAE09A1E72CA7EB49371D6AAF20096F0D1591889F89E6C269E457C
candidate SHA-256: 0A0315F88BAAE09A1E72CA7EB49371D6AAF20096F0D1591889F89E6C269E457C
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1061016_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1061090
original SHA-256: D3131B1CBF86E34A41F00BB9EE65E525371A6B5CC1D9DA734E90ED39B422AC76
candidate SHA-256: D3131B1CBF86E34A41F00BB9EE65E525371A6B5CC1D9DA734E90ED39B422AC76
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1061090_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1061090_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

