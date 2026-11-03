# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1144864
original SHA-256: 87FBCC6F253F1978242AADF303C667CA7A65EA8D120AC2464BC3CB4693CD0CD2
candidate SHA-256: 1E4CBEE351F7EB20CC71CEA2D816EE4F949DD9AAEC7490AC5FE62763103D6995
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1145354
original SHA-256: 57B507897C484A3D5ABBD903E3B6D906C042153562C5D6ED368BA8E01214F7E2
candidate SHA-256: 57B507897C484A3D5ABBD903E3B6D906C042153562C5D6ED368BA8E01214F7E2
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_032_counter_v1/reading_packets_v1/expanded_train_1145354_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_032_counter_v1/reading_packets_v1/expanded_train_1145354_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_032_counter_v1/reading_packets_v1/expanded_train_1145354_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1145735
original SHA-256: 408D4CB4248154FB7B8BD14E17B45908B9CD458A6719F5EB83C013FFBD91B237
candidate SHA-256: 408D4CB4248154FB7B8BD14E17B45908B9CD458A6719F5EB83C013FFBD91B237
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_032_counter_v1/reading_packets_v1/expanded_train_1145735_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_032_counter_v1/reading_packets_v1/expanded_train_1145735_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1146590
original SHA-256: D3A710EDF4BB261BCE8751DA2ECE60215B2F5579A584081B192DC37562E563ED
candidate SHA-256: D3A710EDF4BB261BCE8751DA2ECE60215B2F5579A584081B192DC37562E563ED
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_032_counter_v1/reading_packets_v1/expanded_train_1146590_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1146596
original SHA-256: EDF190FA069366AC5454F095178CFCDE4D38F28B89DA33AA25F6E132ADCECCF6
candidate SHA-256: 428D3E0DCCA535B65615F94D33865F73802D3E2A9A353C4EC37C4AEDAA9FD530
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

