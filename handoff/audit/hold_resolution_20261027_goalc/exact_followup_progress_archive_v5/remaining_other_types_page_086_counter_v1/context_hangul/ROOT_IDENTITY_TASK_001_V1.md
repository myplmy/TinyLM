# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1201781
original SHA-256: 2B7DE79E715A782AB73A4FF12E06318E69F687C6B3E9563E6761845BA365E90D
candidate SHA-256: 2B7DE79E715A782AB73A4FF12E06318E69F687C6B3E9563E6761845BA365E90D
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1201781_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1201781_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1201781_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1201781_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1201781_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1201979
original SHA-256: AA57D8FD3F324EAA3B2EFE98DFF19A4C49D9AB4C94F7DE24F79E7241221512F3
candidate SHA-256: AA57D8FD3F324EAA3B2EFE98DFF19A4C49D9AB4C94F7DE24F79E7241221512F3
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [9, 9]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 9]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1201979_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1201979_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1201979_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1201979_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1201979_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1201979_0009.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1202012
original SHA-256: 8F965D5782732E3318AB4AA9B92197AF24CAD1306F8EF6BA6C10F3AED588703A
candidate SHA-256: 8F965D5782732E3318AB4AA9B92197AF24CAD1306F8EF6BA6C10F3AED588703A
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202012_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202012_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202012_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202012_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1202177
original SHA-256: 21CB19D4DE47FEE92C5C8BB24D9DA39C5416C18B83792692EEDFFBBE353267BE
candidate SHA-256: 21CB19D4DE47FEE92C5C8BB24D9DA39C5416C18B83792692EEDFFBBE353267BE
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202177_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202177_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202177_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202177_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202177_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1202695
original SHA-256: 3D111BF8642D36CDC9C361246AC5F04C045D929463A9CE63103A875A7327540C
candidate SHA-256: 3D111BF8642D36CDC9C361246AC5F04C045D929463A9CE63103A875A7327540C
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202695_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_086_counter_v1/reading_packets_v1/expanded_train_1202695_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

