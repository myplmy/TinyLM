# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:190292
original SHA-256: 4617215F24707C76E2C388732741EDD91B656BD65EF0F576BCA1F58B38A3C28E
candidate SHA-256: 4617215F24707C76E2C388732741EDD91B656BD65EF0F576BCA1F58B38A3C28E
원문 frame 패킷: [1, 20]
최종 full_diff 패킷: [39, 39]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 39]
후보 중복만 있는 생략 가능 패킷: [21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190292_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190292_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190292_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190292_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190292_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190292_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190292_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190292_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190292_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190292_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190292_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190292_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190292_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190292_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190292_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190292_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190292_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190292_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190292_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190292_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190292_0039.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:190352
original SHA-256: 52FB952B43EECCB8FB3C390371CD7735371BAC98388B330ABDCD8C5D5100091E
candidate SHA-256: 48C7B4EE232B8C87159335769F3316B5C4FB95628EA077193924C395D41C7FBC
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:190694
original SHA-256: E08AE3DFF077EE1C2D57609C8F6BED92F9918D78F2444F79B4322DA8F775AC2E
candidate SHA-256: C57B52D91AD2E6A7759FE27309092CDA91232CFB533B9AE64D7ED44693BEBDEB
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:190707
original SHA-256: 761BA7E5E9E425538194790B9E35D6221324ED023FB46508E0ED40EE170B7646
candidate SHA-256: 761BA7E5E9E425538194790B9E35D6221324ED023FB46508E0ED40EE170B7646
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [12, 12]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 12]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10, 11]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190707_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190707_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190707_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190707_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190707_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190707_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190707_0012.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:190850
original SHA-256: C20C0A64F212E80B2C65773BAF60CCE33020D9425372593A5B2376D0D36C7A96
candidate SHA-256: C20C0A64F212E80B2C65773BAF60CCE33020D9425372593A5B2376D0D36C7A96
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [10, 11]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 10, 11]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8, 9]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190850_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190850_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190850_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190850_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190850_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190850_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190850_0011.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

