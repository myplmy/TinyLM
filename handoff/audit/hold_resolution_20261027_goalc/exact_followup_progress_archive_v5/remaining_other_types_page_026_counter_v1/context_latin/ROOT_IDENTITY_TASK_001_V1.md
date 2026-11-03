# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:294458
original SHA-256: 20557944DA9E43B00E09D56F10622A8132233DFFF890105F56A4D3FD50F17676
candidate SHA-256: 20557944DA9E43B00E09D56F10622A8132233DFFF890105F56A4D3FD50F17676
원문 frame 패킷: [1, 7]
최종 full_diff 패킷: [13, 13]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 13]
후보 중복만 있는 생략 가능 패킷: [8, 9, 10, 11, 12]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294458_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294458_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294458_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294458_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294458_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294458_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294458_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294458_0013.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:294772
original SHA-256: FE7485938055F17BAC4365203F00C237C72ADDA94AA2BA3449DFFCA72B00ADE3
candidate SHA-256: 611AE899F04335DB8869D19FC759C5674B0CFD7753792A73C933AA16E566F3A3
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:294790
original SHA-256: E8F60400B7D26F3A01A2706C874119E279E0D85C8AB1F4C53AE7A9FEF8E01E1F
candidate SHA-256: DE50D76C5B3F2BF84D65A5FE65AA43D927E54B316FD8322F74516F935444F973
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:294820
original SHA-256: 78B52ADD9992F4D935906F77D90AAD2FB28BA3BB1E3E83C5D9DD302553F26460
candidate SHA-256: 78B52ADD9992F4D935906F77D90AAD2FB28BA3BB1E3E83C5D9DD302553F26460
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294820_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294820_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_026_counter_v1/reading_packets_v1/expanded_train_294820_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:294911
original SHA-256: 3C12995C5C68895FED10489293710EF19829365E0945DB084A1E513399E4090D
candidate SHA-256: CCBAF1D3EFBC009F4E7E1B2D27449233CB59786761006D5EB5C6A8C8761A5A67
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

