# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:636405
original SHA-256: A282E3E8C7BF00590366AD427A6E97D7342A1436877283B691B6DB4D9E77E613
candidate SHA-256: A282E3E8C7BF00590366AD427A6E97D7342A1436877283B691B6DB4D9E77E613
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636405_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636405_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636405_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636405_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:636431
original SHA-256: 4B2F109C1B4B10AED609C5F959C8BA3A2A7C38BCA4AC187E560DE310A77934F6
candidate SHA-256: 4B2F109C1B4B10AED609C5F959C8BA3A2A7C38BCA4AC187E560DE310A77934F6
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636431_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:636578
original SHA-256: BAEBD4F32B48BD08E10B2AAD2825B49DB3EB44840A618FAF091D9AE446CBE2E5
candidate SHA-256: BAEBD4F32B48BD08E10B2AAD2825B49DB3EB44840A618FAF091D9AE446CBE2E5
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636578_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636578_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636578_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636578_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_050_counter_v1/reading_packets_v1/expanded_train_636578_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:636654
original SHA-256: 9182A58A5363BE75D5672EA4782F88AAC83E8C62DCD30B30CF66115CB0BEA1CE
candidate SHA-256: 84E86830CA0A0262339ECC7DAD6FFC0789A78712A5B9B498A207F31649BEB239
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:636670
original SHA-256: 0BEE3082A433C2303A1132E3D79838D7041155B61491C79EB76B7F16D08A91D1
candidate SHA-256: 3E73E2C1EC8236EE93B4905C2BD64D77D645C48A8A02A8239C1B0C5187E48F18
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

