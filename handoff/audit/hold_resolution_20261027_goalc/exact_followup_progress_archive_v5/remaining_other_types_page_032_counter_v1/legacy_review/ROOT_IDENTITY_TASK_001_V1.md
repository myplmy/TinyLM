# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:373238
original SHA-256: 658A515C3E10B9684833DC6AB56FB414D0D16010F370660A8D1132A67BE2E9C3
candidate SHA-256: 658A515C3E10B9684833DC6AB56FB414D0D16010F370660A8D1132A67BE2E9C3
원문 frame 패킷: [1, 13]
최종 full_diff 패킷: [25, 25]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 25]
후보 중복만 있는 생략 가능 패킷: [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373238_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373238_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373238_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373238_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373238_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373238_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373238_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373238_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373238_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373238_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373238_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373238_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373238_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373238_0025.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:373377
original SHA-256: 7CF6080DA9E09493B48E4494723F5673BD733B16A977E854763A72286CB8E425
candidate SHA-256: 7CF6080DA9E09493B48E4494723F5673BD733B16A977E854763A72286CB8E425
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373377_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373377_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373377_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373377_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:373543
original SHA-256: ACA32F0734F900652918F295A6856A04F57939C4C591DA5BE6B68DF9981FB484
candidate SHA-256: ACA32F0734F900652918F295A6856A04F57939C4C591DA5BE6B68DF9981FB484
원문 frame 패킷: [1, 7]
최종 full_diff 패킷: [14, 14]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 14]
후보 중복만 있는 생략 가능 패킷: [8, 9, 10, 11, 12, 13]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373543_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373543_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373543_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373543_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373543_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373543_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373543_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373543_0014.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:373641
original SHA-256: 5E137C897BD1DB4AE93B240E84FF896D485E8A3DA8AC21770FF8950592803B30
candidate SHA-256: 5E137C897BD1DB4AE93B240E84FF896D485E8A3DA8AC21770FF8950592803B30
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373641_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373641_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373641_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:373974
original SHA-256: 41DBD00161D032D96BFCF2F64F2D2DE64AB0C0BE85511B80342C63E5ED467401
candidate SHA-256: 41DBD00161D032D96BFCF2F64F2D2DE64AB0C0BE85511B80342C63E5ED467401
원문 frame 패킷: [1, 25]
최종 full_diff 패킷: [49, 49]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 49]
후보 중복만 있는 생략 가능 패킷: [26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373974_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373974_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373974_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373974_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373974_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373974_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373974_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373974_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373974_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373974_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373974_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373974_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373974_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373974_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373974_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373974_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373974_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373974_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373974_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373974_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373974_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373974_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373974_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373974_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373974_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373974_0049.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

