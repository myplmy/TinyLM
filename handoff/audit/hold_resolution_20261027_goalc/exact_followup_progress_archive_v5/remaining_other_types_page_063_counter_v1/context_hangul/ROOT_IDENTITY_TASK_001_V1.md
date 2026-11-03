# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:814239
original SHA-256: 65BFBA2594166D16958DA14CD2FB391D7F5FA97F42FB4B3FD2D3BC9855924D5A
candidate SHA-256: 38619BBAE3E1599C97CEA1842D58AB758CA27D48D8A1EDEFA7AA689D25591278
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:814289
original SHA-256: C0DF12A425ED73B1B307DCB00A0447FF0E525A0BD69165BA1FD7E1C092FE3D5A
candidate SHA-256: 6F4F2444236D5040E4D5A2A205D277318323A686F2CF2F2A9B16A4A702E0BC95
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:814482
original SHA-256: FCC2CC1D661BAE6FA27BD3551243C40B05E2F5A1D87E0E0148F8D4B9F188421C
candidate SHA-256: FCC2CC1D661BAE6FA27BD3551243C40B05E2F5A1D87E0E0148F8D4B9F188421C
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_063_counter_v1/reading_packets_v1/expanded_train_814482_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_063_counter_v1/reading_packets_v1/expanded_train_814482_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_063_counter_v1/reading_packets_v1/expanded_train_814482_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_063_counter_v1/reading_packets_v1/expanded_train_814482_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:814544
original SHA-256: 6805A3482A12C26239F73F6B35AF42BB5FD68EBC819C1EB8D9B098477B8F77F4
candidate SHA-256: E1633C0715D0761F3E69AD9453742B41CF25F4EFD968779FC125A71DBADC9875
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:814587
original SHA-256: 16A026E4DF905A309093BC73960D71F3D6115A1D1B0EBEF04D6777D15BA056DF
candidate SHA-256: 41FC066BA22483B7B71645D1C83895184589595265E1FA3A21D7BDCC16E58CB9
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

