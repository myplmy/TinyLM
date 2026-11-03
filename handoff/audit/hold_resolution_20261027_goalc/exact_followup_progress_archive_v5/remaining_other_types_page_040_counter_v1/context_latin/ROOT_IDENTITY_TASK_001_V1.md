# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:487333
original SHA-256: BD079F7D158EA275D031E9C2DF4D1F8ED0AC6000C8BE5231795C41627BB38789
candidate SHA-256: 3EC519C707964FC3AF1DE916FE9883522E9FF43D57C0CD7D60FF08B10C3B4B40
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:487463
original SHA-256: ECBE6441037CC020601D665A891EB45E545070030CD6F538871A7AF838700E6F
candidate SHA-256: ECBE6441037CC020601D665A891EB45E545070030CD6F538871A7AF838700E6F
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_040_counter_v1/reading_packets_v1/expanded_train_487463_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_040_counter_v1/reading_packets_v1/expanded_train_487463_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_040_counter_v1/reading_packets_v1/expanded_train_487463_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_040_counter_v1/reading_packets_v1/expanded_train_487463_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_040_counter_v1/reading_packets_v1/expanded_train_487463_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:487511
original SHA-256: 6123A83D8D745F5EA07C5F2FE5EAC95B169DE64901DB425A65736BAB98FD3A7E
candidate SHA-256: 6E3D3822FA3A9226D413A3B48D2C3BECEE357503D4F573EA63E71A038020440F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:487576
original SHA-256: 81315DA89C6896F2701C1346ABCE2457A736A09D2208CA358793E5D67192A63C
candidate SHA-256: 5D0F74EEC9BB111D623EB1AA7D06A7D0B249F816CBF9F29F90A03CACF3C96F3C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:487795
original SHA-256: 37EB92AA407F3AA8219518D4064070E1DE0C784CF681DF68EA84C08311CBA2BB
candidate SHA-256: 25AA6DA59FAC6FA8DC4E4E1C16E8A88C76B81D730478F03012A0D0266DF7B384
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

