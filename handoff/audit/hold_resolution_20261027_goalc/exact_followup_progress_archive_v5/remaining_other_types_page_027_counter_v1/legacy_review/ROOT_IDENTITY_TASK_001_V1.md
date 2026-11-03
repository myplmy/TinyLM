# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:308838
original SHA-256: 39182F39A28641B27FA01C0C67F2646F8B5F37AB0EA01F18F2030AA5C1BDD414
candidate SHA-256: 39182F39A28641B27FA01C0C67F2646F8B5F37AB0EA01F18F2030AA5C1BDD414
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_308838_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_308838_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_308838_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:308844
original SHA-256: CE9972B395F3BFCEE2580C5B8D596C06955C8EB1C1ADB2D9945D653C38BBD192
candidate SHA-256: CE9972B395F3BFCEE2580C5B8D596C06955C8EB1C1ADB2D9945D653C38BBD192
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_308844_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_308844_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_308844_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:308893
original SHA-256: F22AD9BCA00CC55BA6436B1F1DC3C088DACBA17B0C0CF98D143D59CF7413F394
candidate SHA-256: F22AD9BCA00CC55BA6436B1F1DC3C088DACBA17B0C0CF98D143D59CF7413F394
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_308893_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:309015
original SHA-256: 31013DCFBE7B9D534CB82ECF1A4EBCE2E9F2CEEEE31851E8709CF4D15E4FD15D
candidate SHA-256: 31013DCFBE7B9D534CB82ECF1A4EBCE2E9F2CEEEE31851E8709CF4D15E4FD15D
원문 frame 패킷: [1, 7]
최종 full_diff 패킷: [14, 14]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 14]
후보 중복만 있는 생략 가능 패킷: [8, 9, 10, 11, 12, 13]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_309015_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_309015_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_309015_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_309015_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_309015_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_309015_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_309015_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_309015_0014.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:309160
original SHA-256: D87E5EEF5751C00DDEEC9AEB2394EAB803BF29C3DE6F59763997DCCD633EF18D
candidate SHA-256: D87E5EEF5751C00DDEEC9AEB2394EAB803BF29C3DE6F59763997DCCD633EF18D
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [11, 11]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 11]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_309160_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_309160_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_309160_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_309160_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_309160_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_309160_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_309160_0011.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

