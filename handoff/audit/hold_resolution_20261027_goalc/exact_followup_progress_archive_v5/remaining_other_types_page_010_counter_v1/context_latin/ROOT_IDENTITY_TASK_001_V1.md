# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:100004
original SHA-256: 5ABF0D35FE8F3ECAECEC8529150FABF8E7E9F434988D2187770FE460F32545C9
candidate SHA-256: 3921CDCF5AB9EDC22DE01C6F0216AF2FA9CB321805961F6F72ED53A084649C4E
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:100153
original SHA-256: E7E187C26153C1BA6A44638C0433BAEC6DA2929F08B2F2FB0BDCF613A5F69F71
candidate SHA-256: B81DB54E4518CA6EEE844373913D15B47B2C149D98D4304333FA0C0EE3491676
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:100161
original SHA-256: FB5E39114160E69E3C20D5B244C776DAB5D4D75BF218D01B7B595E5E5977C43A
candidate SHA-256: B50C07997E0FED6E3FC0D8A0E9B4120A69A420FC59D8172222CE8D14263FF3A8
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:100252
original SHA-256: 9C28F5F12AA146A883D8AD8FFF513FE8DDCD2114E9239C2C161CD303D80A57C8
candidate SHA-256: 9C28F5F12AA146A883D8AD8FFF513FE8DDCD2114E9239C2C161CD303D80A57C8
원문 frame 패킷: [1, 12]
최종 full_diff 패킷: [23, 23]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 23]
후보 중복만 있는 생략 가능 패킷: [13, 14, 15, 16, 17, 18, 19, 20, 21, 22]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100252_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100252_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100252_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100252_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100252_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100252_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100252_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100252_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100252_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100252_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100252_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100252_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100252_0023.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:100486
original SHA-256: CB48ABD8C3A7330F905D88675BAFAF63C7556DC68EC306238E3CE33427F3E033
candidate SHA-256: CB48ABD8C3A7330F905D88675BAFAF63C7556DC68EC306238E3CE33427F3E033
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_010_counter_v1/reading_packets_v1/expanded_train_100486_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

