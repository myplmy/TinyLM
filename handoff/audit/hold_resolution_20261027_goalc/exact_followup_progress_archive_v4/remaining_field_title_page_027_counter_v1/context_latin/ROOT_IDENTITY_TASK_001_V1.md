# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:875485
original SHA-256: 0D8729727F6D018AEA5C74E92443A9DF3830C156D8C3E07017046E89CBDBDDD1
candidate SHA-256: 0D8729727F6D018AEA5C74E92443A9DF3830C156D8C3E07017046E89CBDBDDD1
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_027_counter_v1/reading_packets_v1/expanded_train_875485_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_027_counter_v1/reading_packets_v1/expanded_train_875485_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_027_counter_v1/reading_packets_v1/expanded_train_875485_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_027_counter_v1/reading_packets_v1/expanded_train_875485_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:875489
original SHA-256: 519014E90390E78D66EE76B7EBB32AC5A967D77A589164A1592EC0FE2AA85629
candidate SHA-256: D45B259937E3D3CAF474198532C1BE3499845DAE123897B18B9A632FDFDD5BB8
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:876003
original SHA-256: 454319CBF43FF08B61F9CFDBF9A3122BDF1C68A5CE602CE84286C97D2393536E
candidate SHA-256: C6AC7C953F7048804EA3C08B7E2C15872B0ED1C3423D2F061668918648826D7B
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:876070
original SHA-256: DF7BD416405EA524CD0684CD17005276E0CD91335BC03EA68A6534B1FE25EB02
candidate SHA-256: DF7BD416405EA524CD0684CD17005276E0CD91335BC03EA68A6534B1FE25EB02
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_027_counter_v1/reading_packets_v1/expanded_train_876070_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:876917
original SHA-256: E89EBE91CDE37582D10E8FDC55017F02601835FFA2A17BB2AF672C9790DE143D
candidate SHA-256: 66E136F708673A349774038818C8B83C1A708922F5144318C071C4CFA1341065
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

