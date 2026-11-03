# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:344526
original SHA-256: A02B8C7E2A96BB59D34D95A4F7B868D9B1D943230B5693BDD2EC3DA089541B97
candidate SHA-256: 49F627271DAC3257A95EC0CEAE5D7711AB7A8E80E653533B42A91C604667992E
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:344954
original SHA-256: 92CDBFD271B695FB045DA86D8D481E0019BB742BD6DB592C9C68385CE067DF7B
candidate SHA-256: D621712425D1C0B1E4F6710C8DDBACC6DCDBAC2E291BFF574307F843F0E2ACD2
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:345291
original SHA-256: 7752DCFEA089730E00CAC3F607344F00A691478ACD6374429142CFE83DC89808
candidate SHA-256: 7752DCFEA089730E00CAC3F607344F00A691478ACD6374429142CFE83DC89808
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_030_counter_v1/reading_packets_v1/expanded_train_345291_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_030_counter_v1/reading_packets_v1/expanded_train_345291_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_030_counter_v1/reading_packets_v1/expanded_train_345291_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_030_counter_v1/reading_packets_v1/expanded_train_345291_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:345314
original SHA-256: C55115D67CAC3E9B0E0B88E17799242485A1F0087A900A050B4B83F535D2B86B
candidate SHA-256: C55115D67CAC3E9B0E0B88E17799242485A1F0087A900A050B4B83F535D2B86B
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_030_counter_v1/reading_packets_v1/expanded_train_345314_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:345534
original SHA-256: A15F2123523A4D161AD278A7B305FD87669F557B7D74D22FAE1C4C2553D8F801
candidate SHA-256: 3553CF6CF47EF35382774079BF104CC07BF6EE3CB10AE8B0A74692F965205494
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

