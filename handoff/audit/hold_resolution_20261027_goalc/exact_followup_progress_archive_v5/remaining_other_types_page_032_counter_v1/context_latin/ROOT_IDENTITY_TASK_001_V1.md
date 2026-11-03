# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:373240
original SHA-256: D99CDB1DFBBF6F8F0BF4F5A461070760BA4BC87891FC99E0D0EC33F87317A5A5
candidate SHA-256: D99CDB1DFBBF6F8F0BF4F5A461070760BA4BC87891FC99E0D0EC33F87317A5A5
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373240_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373240_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:373256
original SHA-256: ACED227ED703172F13DD5C6EFF906FBBA7805A62E21B55D4E986A1E9950D51C0
candidate SHA-256: ACED227ED703172F13DD5C6EFF906FBBA7805A62E21B55D4E986A1E9950D51C0
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373256_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373256_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:373351
original SHA-256: 9E0EEE66B52AEFC337248212B9554A946980C911CC28ED223F9B7F1372E14724
candidate SHA-256: 9E0EEE66B52AEFC337248212B9554A946980C911CC28ED223F9B7F1372E14724
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373351_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:373404
original SHA-256: 1F5F733892EBB3FEB6E8424AED0057D71DF4CD76D966ECD0A7F0E3B12A8B6090
candidate SHA-256: 1F5F733892EBB3FEB6E8424AED0057D71DF4CD76D966ECD0A7F0E3B12A8B6090
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_032_counter_v1/reading_packets_v1/expanded_train_373404_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:373660
original SHA-256: A88E1718B57AB78D77D7EF29B4E6E28348E1E0AAE0D53BBFA421075DA31C7E85
candidate SHA-256: 374E050ED9F7EDC67519D0541A074587BF51A87CDC5EEE8274AFC8E16F569D4C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

