# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:651329
original SHA-256: 0C487DC5FBF2141FC61D852BA497E1246C430BBDA25B9D435F3D0B88D9BD4D21
candidate SHA-256: 0C487DC5FBF2141FC61D852BA497E1246C430BBDA25B9D435F3D0B88D9BD4D21
원문 frame 패킷: [1, 11]
최종 full_diff 패킷: [21, 21]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 21]
후보 중복만 있는 생략 가능 패킷: [12, 13, 14, 15, 16, 17, 18, 19, 20]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651329_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651329_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651329_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651329_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651329_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651329_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651329_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651329_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651329_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651329_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651329_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651329_0021.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:651337
original SHA-256: A9E2CCEDBBB4B18D1B085274CFC4A1D719FD193CC59A00FD0CC790C6BB805E0A
candidate SHA-256: 503C9B61599002608E9A9DAE1B6E208E7366E30023D9CFDA6B07683029015191
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:651463
original SHA-256: 92DE3BE44938412D36BD78DD8C522CE52F26BB2199DDF8C9A786EF11160D6355
candidate SHA-256: 92DE3BE44938412D36BD78DD8C522CE52F26BB2199DDF8C9A786EF11160D6355
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651463_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651463_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651463_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651463_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651463_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:651538
original SHA-256: FF354854B5DA24D07C5FAA732C908AD149C4B750A44D8948E621911A467A34F4
candidate SHA-256: FF354854B5DA24D07C5FAA732C908AD149C4B750A44D8948E621911A467A34F4
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [12, 12]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 12]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10, 11]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651538_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651538_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651538_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651538_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651538_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651538_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651538_0012.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:651584
original SHA-256: 23BDDB84815D65FCE1DD0CE2F4445EED864B1D0C4693B41F34821799723D0366
candidate SHA-256: 23BDDB84815D65FCE1DD0CE2F4445EED864B1D0C4693B41F34821799723D0366
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_051_counter_v1/reading_packets_v1/expanded_train_651584_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

