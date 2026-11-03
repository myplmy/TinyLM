# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:895923
original SHA-256: C925721839202626CD3B60135DC93545A921128FC57A22D1AAAE3B9AAB15DFA8
candidate SHA-256: BFA9C36C19883F05860BFE2AE0814DD67A9EB7757221E90B2D6B40DB21BE162C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:896016
original SHA-256: 688B16BD89922E84E30CBFE181B4DFFA5216F5B3737D6987D3DB65990875153C
candidate SHA-256: 688B16BD89922E84E30CBFE181B4DFFA5216F5B3737D6987D3DB65990875153C
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_896016_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_896016_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_896016_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_896016_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:896739
original SHA-256: 7636F0BDC3062481D485E4CD5E5D0E588D8B6D50660411E0B95AF42AE79A1467
candidate SHA-256: 60D00256E5BA48F7E53F1AEA253A66CE5A76B51716834A0E32687CDE03D0934C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:896774
original SHA-256: 8EDDCB3569B5C12E84A80A5491F9AEC4EBB482E39A54EE4F3343EA346B079144
candidate SHA-256: 6ABBFFFDC2C298FBDA035285A6F47E38A956DFF653C5E72DEDD517E260992ECD
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:896842
original SHA-256: 2F6674CDBAFCC94F31AD50AF3BDC86EC66254407A735040633C8E437C382B840
candidate SHA-256: 2F6674CDBAFCC94F31AD50AF3BDC86EC66254407A735040633C8E437C382B840
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_896842_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_896842_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_896842_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

