# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:59662
original SHA-256: B2D6BCFE634D8F52D66B12EFBE913839B09DE3836BF8C3AF6B5D2DD5209BC6E9
candidate SHA-256: B2D6BCFE634D8F52D66B12EFBE913839B09DE3836BF8C3AF6B5D2DD5209BC6E9
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_59662_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:59772
original SHA-256: 2F6FD6475EACA247FE7CE1B0EA982286AA9263DBB31F5BE508EFC11212F8D1A2
candidate SHA-256: 2F6FD6475EACA247FE7CE1B0EA982286AA9263DBB31F5BE508EFC11212F8D1A2
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_59772_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_59772_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:59852
original SHA-256: FAAFB0C7F3D3D808B5A05137E10DF59C7EF28EA3257C5B098B3F5597BCA3FA80
candidate SHA-256: FAAFB0C7F3D3D808B5A05137E10DF59C7EF28EA3257C5B098B3F5597BCA3FA80
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_59852_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_59852_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:60003
original SHA-256: 578719C8CC6D5012C886D9A677A172D3C40FE80AF69A4E78E2AD36AF689DAC91
candidate SHA-256: 35854274787ECEA3F3479C29783851A6FDE3D70E7325B172CB389DB44A78FC31
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:60084
original SHA-256: F15E8689BDB9BECDB500449BD453659FC9186A9C1A7A0557B9E54BF2977145EA
candidate SHA-256: F15E8689BDB9BECDB500449BD453659FC9186A9C1A7A0557B9E54BF2977145EA
원문 frame 패킷: [1, 7]
최종 full_diff 패킷: [14, 14]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 14]
후보 중복만 있는 생략 가능 패킷: [8, 9, 10, 11, 12, 13]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60084_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60084_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60084_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60084_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60084_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60084_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60084_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60084_0014.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

