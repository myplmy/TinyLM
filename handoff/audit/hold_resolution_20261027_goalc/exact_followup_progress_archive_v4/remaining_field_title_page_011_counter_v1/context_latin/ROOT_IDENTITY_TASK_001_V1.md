# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:212412
original SHA-256: 397D95907DA2F4F76510C18CDB3FDE2872FC6E6DDE1CCB925A8CE46ADA163440
candidate SHA-256: 397D95907DA2F4F76510C18CDB3FDE2872FC6E6DDE1CCB925A8CE46ADA163440
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_011_counter_v1/reading_packets_v1/expanded_train_212412_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:215337
original SHA-256: 3AD6EA69D8BF50A4E27F11F048A80DFD0BBE29CF7A886CF59CD1796B5252A955
candidate SHA-256: 5E60817812DA8545C4D7A04378652B8FE5C505F40133252BCB657BCDB37AC209
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:215423
original SHA-256: AD5C7B5079BEC44F3447C45209BB8E03E2437466262254B51028FF532CEFC743
candidate SHA-256: AD5C7B5079BEC44F3447C45209BB8E03E2437466262254B51028FF532CEFC743
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_011_counter_v1/reading_packets_v1/expanded_train_215423_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_011_counter_v1/reading_packets_v1/expanded_train_215423_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:215708
original SHA-256: A75E26D65B74B86EC187B3D0EFBFDB5FA04717288789F18A6F201972D4385505
candidate SHA-256: 62ED64A80683E5BFCA1D6DD3625B160013794BD2FA5DD25760B97BFF57D93CFB
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:216275
original SHA-256: 010C064428D3D75DB60275AE91916A6B80C81C4653F569284B918A87762C393B
candidate SHA-256: 010C064428D3D75DB60275AE91916A6B80C81C4653F569284B918A87762C393B
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_011_counter_v1/reading_packets_v1/expanded_train_216275_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

