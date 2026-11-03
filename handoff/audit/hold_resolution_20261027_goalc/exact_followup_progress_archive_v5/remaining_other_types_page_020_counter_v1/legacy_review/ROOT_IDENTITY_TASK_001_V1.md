# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:217933
original SHA-256: DC3DF813AD09D66C5747284982E1EC8D820F02AB0B8B4A1EF899522079C2B687
candidate SHA-256: DC3DF813AD09D66C5747284982E1EC8D820F02AB0B8B4A1EF899522079C2B687
원문 frame 패킷: [1, 23]
최종 full_diff 패킷: [45, 45]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 45]
후보 중복만 있는 생략 가능 패킷: [24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217933_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217933_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217933_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217933_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217933_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217933_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217933_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217933_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217933_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217933_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217933_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217933_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217933_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217933_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217933_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217933_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217933_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217933_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217933_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217933_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217933_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217933_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217933_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_217933_0045.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:217965
original SHA-256: 91FA0A4C8B01FEEFBF0BC014F9D6E1E01DC2744E3FDE9EDB2212DCCE73F07EA2
candidate SHA-256: 2B5BECAC5549AB575D9FD71E94ED183E089D9B3754FB8124B360BE97B60CDE01
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:218014
original SHA-256: 31C58A08BF4D6E5E2EB6801E5C71836FBC4A9ECD4208827CDDAD872689FCAC5D
candidate SHA-256: F1D55811FCE57FB63F9ACE8547A99D6A54FF0112D13C620E3711E41A3A5B735D
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:218052
original SHA-256: 8692A142E2C2062C7A5945C984739B323A7CC2F5E20A341200501773CDE12495
candidate SHA-256: 8692A142E2C2062C7A5945C984739B323A7CC2F5E20A341200501773CDE12495
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_218052_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_218052_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_218052_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_218052_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_020_counter_v1/reading_packets_v1/expanded_train_218052_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:218060
original SHA-256: B94D67D855D3C2DC9183D4669A8762B2CCEDF559EFB57AEDD00EB44695D37872
candidate SHA-256: 9621A94A791A86B4D5F72984BBB13C36C08FBD8EAF4ECFECD79A7DA52D88E6E8
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

