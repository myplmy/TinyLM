# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:126783
original SHA-256: 4112A601436B486D393DF07713D0F2646E2902E9CAA11704D4E96163C7C576B4
candidate SHA-256: 79ED2A4DC110AAFD40CBC87ECC1E3EE9F8C5D34FBDB2BE75EE7F7F69CB4656BE
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:127009
original SHA-256: 1A72B08675327559A7220A660EC3B58A0ADD7085D9C44DD20652554360BC3C57
candidate SHA-256: 1A72B08675327559A7220A660EC3B58A0ADD7085D9C44DD20652554360BC3C57
원문 frame 패킷: [1, 8]
최종 full_diff 패킷: [15, 15]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 15]
후보 중복만 있는 생략 가능 패킷: [9, 10, 11, 12, 13, 14]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_127009_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_127009_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_127009_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_127009_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_127009_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_127009_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_127009_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_127009_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_127009_0015.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:127235
original SHA-256: 5DF6D7640201A2126B5F2C4DFCBE2D962E39F56B6ADB08CFE2D94C5532EC838A
candidate SHA-256: 5DF6D7640201A2126B5F2C4DFCBE2D962E39F56B6ADB08CFE2D94C5532EC838A
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_127235_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_127235_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:127482
original SHA-256: 966A7654149607DECF454E6BA9D32FCFDA2BC2A9580B50BF7DFA81CF65655FBA
candidate SHA-256: 966A7654149607DECF454E6BA9D32FCFDA2BC2A9580B50BF7DFA81CF65655FBA
원문 frame 패킷: [1, 18]
최종 full_diff 패킷: [35, 35]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 35]
후보 중복만 있는 생략 가능 패킷: [19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_127482_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_127482_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_127482_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_127482_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_127482_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_127482_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_127482_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_127482_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_127482_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_127482_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_127482_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_127482_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_127482_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_127482_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_127482_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_127482_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_127482_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_127482_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_127482_0035.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:127499
original SHA-256: 3958BA267689EBDCCDFFCD0F5A9472D73AB36E9AD207AC8B51C52734514B69FD
candidate SHA-256: 3C2F8D873C9F682A5D4DABF40E7239EC5A1BF2DB9B32E8A1BE714F1ACC363301
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

