# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:561084
original SHA-256: 53DB2880EF5377E87C8854C91D24FA98B51737D39CE30E2C5B83A8834383D1BA
candidate SHA-256: 53DB2880EF5377E87C8854C91D24FA98B51737D39CE30E2C5B83A8834383D1BA
원문 frame 패킷: [1, 17]
최종 full_diff 패킷: [33, 33]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 33]
후보 중복만 있는 생략 가능 패킷: [18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561084_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561084_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561084_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561084_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561084_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561084_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561084_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561084_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561084_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561084_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561084_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561084_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561084_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561084_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561084_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561084_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561084_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561084_0033.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:561116
original SHA-256: ECC2C30C0E7FEC2AF60977201510E325CCB8869229B4F6FCAEEDDF37DFD22B42
candidate SHA-256: 64766B0AD08DAF86B4CB0B402FC25D42A202B412B28A28DA098B2A12B543A928
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:561176
original SHA-256: 8471A688EDDF434F25F66410004CEA162F3085BD61E60CA4BAED6B7AE94691CA
candidate SHA-256: 8471A688EDDF434F25F66410004CEA162F3085BD61E60CA4BAED6B7AE94691CA
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561176_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:561285
original SHA-256: BC70C324149936367E28F3CDAEB312DBE213FCC843E2C6BBF3CEB9B979886697
candidate SHA-256: BC70C324149936367E28F3CDAEB312DBE213FCC843E2C6BBF3CEB9B979886697
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561285_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561285_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561285_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561285_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561285_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:561323
original SHA-256: 3818EDAA038EB2503AEB4F404719F74CCEFEC583FA32DCB6A12B6FCC5CBDBD5B
candidate SHA-256: 3818EDAA038EB2503AEB4F404719F74CCEFEC583FA32DCB6A12B6FCC5CBDBD5B
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [9, 9]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 9]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561323_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561323_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561323_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561323_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561323_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_045_counter_v1/reading_packets_v1/expanded_train_561323_0009.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

