# 정확 입력 전문 판독 연결 TASK_007

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:157841
original SHA-256: E17E7A28A3CE384666C7BDAAB295D8A52057CB50C287013D54DD13A8086B29F0
candidate SHA-256: 32F39C52FB6A354AB5A62318E28C8B0272F1666CEA533B21FF23B9CE405C3DF6
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:157873
original SHA-256: 3C9A83CD6351CF5F733E14C7B6EDEA73DB86B0CBF4E585D02B4802DCBF46A904
candidate SHA-256: 3C9A83CD6351CF5F733E14C7B6EDEA73DB86B0CBF4E585D02B4802DCBF46A904
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_157873_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:157986
original SHA-256: E46AEF92EA51C7A6CCCF776746EB2E032625095D90F04EE392D28CD325454206
candidate SHA-256: E46AEF92EA51C7A6CCCF776746EB2E032625095D90F04EE392D28CD325454206
원문 frame 패킷: [1, 7]
최종 full_diff 패킷: [14, 14]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 14]
후보 중복만 있는 생략 가능 패킷: [8, 9, 10, 11, 12, 13]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_157986_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_157986_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_157986_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_157986_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_157986_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_157986_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_157986_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_009_counter_v1/reading_packets_v1/expanded_train_157986_0014.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:158254
original SHA-256: 4922B6D7D88C11ACA9354140569741994AEC32C8C4C0D82336720777D461D0AC
candidate SHA-256: 36C35A5D9704F8DDE7FB557CF255433AC61F35B1DE5FD7C8680D492823EA71E9
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:158536
original SHA-256: 558FA0E01508B4148B9FF05D6F2D3F05A3457E72A7F97C1CB708E0C0281F107D
candidate SHA-256: 718B5AF9F9C0DE0B7E2AB3DDF7B562DB8AFD7BB2A838C9967924C21640BAA388
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

