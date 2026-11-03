# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:802146
original SHA-256: 2ABD6D3B84E7F1A14FB0C9EA3144451D31B2BBC6FA4DECB6341BE4EAD6F1025E
candidate SHA-256: 2ABD6D3B84E7F1A14FB0C9EA3144451D31B2BBC6FA4DECB6341BE4EAD6F1025E
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [11, 11]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 11]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_062_counter_v1/reading_packets_v1/expanded_train_802146_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_062_counter_v1/reading_packets_v1/expanded_train_802146_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_062_counter_v1/reading_packets_v1/expanded_train_802146_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_062_counter_v1/reading_packets_v1/expanded_train_802146_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_062_counter_v1/reading_packets_v1/expanded_train_802146_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_062_counter_v1/reading_packets_v1/expanded_train_802146_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_062_counter_v1/reading_packets_v1/expanded_train_802146_0011.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:802336
original SHA-256: 6538E131137B0699B1D2D403D4D95CBF28B71E148A000091EE5C084DC41F1C3B
candidate SHA-256: 0F5D7F85E9BFE85CC454D1C627872F911E980A0AE480619250F14FB9ED3BFB8A
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:802355
original SHA-256: 5CDD033D601659E9BAE1B6256BC5737FCEB5F14D2FA7FC597B0EEED03BE6C4CD
candidate SHA-256: 5CDD033D601659E9BAE1B6256BC5737FCEB5F14D2FA7FC597B0EEED03BE6C4CD
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_062_counter_v1/reading_packets_v1/expanded_train_802355_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_062_counter_v1/reading_packets_v1/expanded_train_802355_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:802370
original SHA-256: 90F6C17CBD78F3AD1872EDBE92E3D1F1D3470B327DAF515EFCCD1AC54AFE027C
candidate SHA-256: 90F6C17CBD78F3AD1872EDBE92E3D1F1D3470B327DAF515EFCCD1AC54AFE027C
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_062_counter_v1/reading_packets_v1/expanded_train_802370_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_062_counter_v1/reading_packets_v1/expanded_train_802370_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_062_counter_v1/reading_packets_v1/expanded_train_802370_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:802418
original SHA-256: 485FFF45945E1F42ABD6489B6D39D7E79CB36923C80EB65B2F1C07E0ADD9356F
candidate SHA-256: 485FFF45945E1F42ABD6489B6D39D7E79CB36923C80EB65B2F1C07E0ADD9356F
원문 frame 패킷: [1, 11]
최종 full_diff 패킷: [22, 22]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 22]
후보 중복만 있는 생략 가능 패킷: [12, 13, 14, 15, 16, 17, 18, 19, 20, 21]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_062_counter_v1/reading_packets_v1/expanded_train_802418_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_062_counter_v1/reading_packets_v1/expanded_train_802418_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_062_counter_v1/reading_packets_v1/expanded_train_802418_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_062_counter_v1/reading_packets_v1/expanded_train_802418_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_062_counter_v1/reading_packets_v1/expanded_train_802418_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_062_counter_v1/reading_packets_v1/expanded_train_802418_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_062_counter_v1/reading_packets_v1/expanded_train_802418_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_062_counter_v1/reading_packets_v1/expanded_train_802418_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_062_counter_v1/reading_packets_v1/expanded_train_802418_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_062_counter_v1/reading_packets_v1/expanded_train_802418_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_062_counter_v1/reading_packets_v1/expanded_train_802418_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_062_counter_v1/reading_packets_v1/expanded_train_802418_0022.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

