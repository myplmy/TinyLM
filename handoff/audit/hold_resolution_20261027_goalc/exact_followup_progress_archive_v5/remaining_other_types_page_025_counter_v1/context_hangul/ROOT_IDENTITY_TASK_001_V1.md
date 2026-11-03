# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:282657
original SHA-256: 64B97E99CE8A25C270FAAF0A86C298ED6D610D24C1CBCECA0796496411B6418B
candidate SHA-256: 64B97E99CE8A25C270FAAF0A86C298ED6D610D24C1CBCECA0796496411B6418B
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282657_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282657_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282657_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282657_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:282784
original SHA-256: F337E9AAC76ADFFA34EF16314E02796647D48B95081E06469553B8307363735E
candidate SHA-256: F337E9AAC76ADFFA34EF16314E02796647D48B95081E06469553B8307363735E
원문 frame 패킷: [1, 13]
최종 full_diff 패킷: [26, 26]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 26]
후보 중복만 있는 생략 가능 패킷: [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282784_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282784_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282784_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282784_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282784_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282784_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282784_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282784_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282784_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282784_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282784_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282784_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282784_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282784_0026.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:282872
original SHA-256: CA4EB1B681E281A38C4E9606801E4BE598A016B3ECEE777E960EE9381F3CE0F5
candidate SHA-256: CA4EB1B681E281A38C4E9606801E4BE598A016B3ECEE777E960EE9381F3CE0F5
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282872_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282872_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282872_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:282944
original SHA-256: 7F46394B6ADF9AA0694CC15858DB85999DAEAB092E932B99F81560C1C969145A
candidate SHA-256: 7F46394B6ADF9AA0694CC15858DB85999DAEAB092E932B99F81560C1C969145A
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282944_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282944_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:282995
original SHA-256: 3AC25EBB85FE325FF0E80A0A9C37567A44263BF78ED10813E64A6D2CE8A888F9
candidate SHA-256: 3AC25EBB85FE325FF0E80A0A9C37567A44263BF78ED10813E64A6D2CE8A888F9
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282995_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282995_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282995_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282995_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_025_counter_v1/reading_packets_v1/expanded_train_282995_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

