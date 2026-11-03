# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:608003
original SHA-256: 73D299984B1B3C537FCC5B6A79D182708B18EE0013586441AFB153AC8E77FCE7
candidate SHA-256: 73D299984B1B3C537FCC5B6A79D182708B18EE0013586441AFB153AC8E77FCE7
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_048_counter_v1/reading_packets_v1/expanded_train_608003_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:608020
original SHA-256: 1833C8DCAF7CC67EFABA26FEBE52BDC92C491D499D1EE0BD292357EFB28E13BD
candidate SHA-256: 2993B53627EC2F683292505A951635B713ACDB29238636395072A9422E8B30D2
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:608031
original SHA-256: 749237F59F28DF897202D95B432F51DF3DD64E3D9D34B06302F4B051D1DA1477
candidate SHA-256: 749237F59F28DF897202D95B432F51DF3DD64E3D9D34B06302F4B051D1DA1477
원문 frame 패킷: [1, 12]
최종 full_diff 패킷: [24, 24]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 24]
후보 중복만 있는 생략 가능 패킷: [13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_048_counter_v1/reading_packets_v1/expanded_train_608031_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_048_counter_v1/reading_packets_v1/expanded_train_608031_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_048_counter_v1/reading_packets_v1/expanded_train_608031_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_048_counter_v1/reading_packets_v1/expanded_train_608031_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_048_counter_v1/reading_packets_v1/expanded_train_608031_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_048_counter_v1/reading_packets_v1/expanded_train_608031_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_048_counter_v1/reading_packets_v1/expanded_train_608031_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_048_counter_v1/reading_packets_v1/expanded_train_608031_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_048_counter_v1/reading_packets_v1/expanded_train_608031_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_048_counter_v1/reading_packets_v1/expanded_train_608031_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_048_counter_v1/reading_packets_v1/expanded_train_608031_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_048_counter_v1/reading_packets_v1/expanded_train_608031_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_048_counter_v1/reading_packets_v1/expanded_train_608031_0024.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:608053
original SHA-256: 7A8560A2E71EEC52AAEA846A54181819C7EEB8F8314736BB51D279D1F1E39402
candidate SHA-256: 51C9161969C4E4DDFD71C437D050166169C95FCC345D538429ECA0E427C29B0F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:608157
original SHA-256: 3EF5F36FBF8557BBBC9FA05079FE7C5B4691A55DFF7BB15B3440B8A556ABCC3A
candidate SHA-256: 3EF5F36FBF8557BBBC9FA05079FE7C5B4691A55DFF7BB15B3440B8A556ABCC3A
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_048_counter_v1/reading_packets_v1/expanded_train_608157_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_048_counter_v1/reading_packets_v1/expanded_train_608157_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

