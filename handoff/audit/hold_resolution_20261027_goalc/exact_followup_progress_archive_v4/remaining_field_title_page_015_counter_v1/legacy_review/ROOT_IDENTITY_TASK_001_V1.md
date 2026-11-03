# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:350405
original SHA-256: 6D3F8C0C2F2E26B5C047A06B2D4233B5BDEBEAAE0EFBFD0A0CF09C26A0AE8012
candidate SHA-256: B23C942C79C9299EBD908FC7AAAB01D94D402A07F186B247649FB04FD7A5CFE4
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:350874
original SHA-256: 861E5211745C22A166FE8A1096683056CFC08D88B848E224F4AB3FDABFA527DB
candidate SHA-256: 8C5599499A7184E5D07D85A2A505A29BACD2714DAE2F407004F9EA1D1E642951
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:351191
original SHA-256: 8A4D889E787AB3627F9457940EB2D4D9351C0F3D5B7AFB384A6C817AC2028F8B
candidate SHA-256: 9BD87BB6565611DE97364FC63119AD3C018CF9184A83BAC8793D4A46B54C7268
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:351321
original SHA-256: 9775DEFA5F5E481DBF2F6038F231A6C36ECA5C439BBAFC027FE91A4106E5DACB
candidate SHA-256: 9775DEFA5F5E481DBF2F6038F231A6C36ECA5C439BBAFC027FE91A4106E5DACB
원문 frame 패킷: [1, 22]
최종 full_diff 패킷: [43, 43]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 43]
후보 중복만 있는 생략 가능 패킷: [23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_015_counter_v1/reading_packets_v1/expanded_train_351321_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_015_counter_v1/reading_packets_v1/expanded_train_351321_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_015_counter_v1/reading_packets_v1/expanded_train_351321_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_015_counter_v1/reading_packets_v1/expanded_train_351321_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_015_counter_v1/reading_packets_v1/expanded_train_351321_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_015_counter_v1/reading_packets_v1/expanded_train_351321_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_015_counter_v1/reading_packets_v1/expanded_train_351321_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_015_counter_v1/reading_packets_v1/expanded_train_351321_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_015_counter_v1/reading_packets_v1/expanded_train_351321_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_015_counter_v1/reading_packets_v1/expanded_train_351321_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_015_counter_v1/reading_packets_v1/expanded_train_351321_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_015_counter_v1/reading_packets_v1/expanded_train_351321_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_015_counter_v1/reading_packets_v1/expanded_train_351321_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_015_counter_v1/reading_packets_v1/expanded_train_351321_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_015_counter_v1/reading_packets_v1/expanded_train_351321_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_015_counter_v1/reading_packets_v1/expanded_train_351321_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_015_counter_v1/reading_packets_v1/expanded_train_351321_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_015_counter_v1/reading_packets_v1/expanded_train_351321_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_015_counter_v1/reading_packets_v1/expanded_train_351321_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_015_counter_v1/reading_packets_v1/expanded_train_351321_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_015_counter_v1/reading_packets_v1/expanded_train_351321_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_015_counter_v1/reading_packets_v1/expanded_train_351321_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_015_counter_v1/reading_packets_v1/expanded_train_351321_0043.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:351875
original SHA-256: 07D437736ACAEC96B442F1897A354C4966A19163C83BE07D9D356C5F55BEAF9B
candidate SHA-256: D3FF0B6F196BE043D6CC2555A9BD1A3C226F9DDBE3E45EC8615E6191FCFBE12C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

