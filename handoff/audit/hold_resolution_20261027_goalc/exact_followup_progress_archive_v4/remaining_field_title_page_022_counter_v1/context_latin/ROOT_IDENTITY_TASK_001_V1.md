# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:663664
original SHA-256: 568DE452E2801B1DA71060AEB5C19B59746FD9A8B37F334ECE61655253B68665
candidate SHA-256: C97E43B3D9879F55D1A8B80D9A1FE7204347AA920FEC343A73DAA8644C27829F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:663838
original SHA-256: 3E9537E16D7B5803F6C94D952E1F7F3306FF53D0F249C7790349811F86AF53F0
candidate SHA-256: 3A478778BFC359B87CEDC83DB3407C1BC02DBE57D345745EA3470E3DFCDA2B07
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:664024
original SHA-256: BD5A16450C18110C60DD4AC509F7182F6E6FF8AFEC414E0DE3A8AFC0FC1B0164
candidate SHA-256: BD5A16450C18110C60DD4AC509F7182F6E6FF8AFEC414E0DE3A8AFC0FC1B0164
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_022_counter_v1/reading_packets_v1/expanded_train_664024_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_022_counter_v1/reading_packets_v1/expanded_train_664024_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_022_counter_v1/reading_packets_v1/expanded_train_664024_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:664119
original SHA-256: 1370776FA81E56ADF23621CE3FE6627CCEC3F3BDF797FBE8B2238F55F7E93A74
candidate SHA-256: DAED335DE9C8603416F04024C76120D3C359AA8EAD92FC577A921AC51A32C6A4
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:664214
original SHA-256: 66FB2E0543AF5C88A1BD2FCD215FFA483307D594A9CA84EFCAC4822DF33894A8
candidate SHA-256: 66FB2E0543AF5C88A1BD2FCD215FFA483307D594A9CA84EFCAC4822DF33894A8
원문 frame 패킷: [1, 19]
최종 full_diff 패킷: [37, 37]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 37]
후보 중복만 있는 생략 가능 패킷: [20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_022_counter_v1/reading_packets_v1/expanded_train_664214_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_022_counter_v1/reading_packets_v1/expanded_train_664214_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_022_counter_v1/reading_packets_v1/expanded_train_664214_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_022_counter_v1/reading_packets_v1/expanded_train_664214_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_022_counter_v1/reading_packets_v1/expanded_train_664214_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_022_counter_v1/reading_packets_v1/expanded_train_664214_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_022_counter_v1/reading_packets_v1/expanded_train_664214_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_022_counter_v1/reading_packets_v1/expanded_train_664214_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_022_counter_v1/reading_packets_v1/expanded_train_664214_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_022_counter_v1/reading_packets_v1/expanded_train_664214_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_022_counter_v1/reading_packets_v1/expanded_train_664214_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_022_counter_v1/reading_packets_v1/expanded_train_664214_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_022_counter_v1/reading_packets_v1/expanded_train_664214_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_022_counter_v1/reading_packets_v1/expanded_train_664214_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_022_counter_v1/reading_packets_v1/expanded_train_664214_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_022_counter_v1/reading_packets_v1/expanded_train_664214_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_022_counter_v1/reading_packets_v1/expanded_train_664214_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_022_counter_v1/reading_packets_v1/expanded_train_664214_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_022_counter_v1/reading_packets_v1/expanded_train_664214_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_022_counter_v1/reading_packets_v1/expanded_train_664214_0037.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

