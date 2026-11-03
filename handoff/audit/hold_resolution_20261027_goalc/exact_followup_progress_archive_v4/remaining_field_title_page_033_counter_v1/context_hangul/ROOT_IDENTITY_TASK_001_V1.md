# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1196655
original SHA-256: 7D26D4E0661D1ACBF39B3A9A0FC951B78F82FDDDFC07B63CE2D58CE3068E0602
candidate SHA-256: 64EABFE2453989016B6252D0738B33F6E54C08990750B45A6CF97CC8CCC35D8B
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1197760
original SHA-256: B4492B77B28D08CBEAAE8BEEF54CE4980E4F0FBFF3074B2BBE285EEA7D018459
candidate SHA-256: B4492B77B28D08CBEAAE8BEEF54CE4980E4F0FBFF3074B2BBE285EEA7D018459
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1197760_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1199912
original SHA-256: 21940D680E131BEA59788F53A4EC36BF34248A7B7FE5660463CBEAD2A5EE4DC5
candidate SHA-256: 21940D680E131BEA59788F53A4EC36BF34248A7B7FE5660463CBEAD2A5EE4DC5
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1199912_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1199912_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1199926
original SHA-256: 15B97226984848A39FCCCF056BF683C7755CCE45A6CFCEE8DBADB09D2033E328
candidate SHA-256: E0D91B66A48F0848D6C316488A108061FAE17A44F028EE0343F31FA0C733561F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1200314
original SHA-256: B8EA78384192235666CA2C752BE034C30B13C540BA8076ACB472A563CBF78C8C
candidate SHA-256: 1430A75D8025DE1F593359B685E215ED0A99E2C2DAF386F1BF8EA6A88C0F54D5
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

