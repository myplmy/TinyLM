# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:359334
original SHA-256: 3449D8D193C071AC5EEBF2DCE263F9FCD81799E969331A4CA988A9F2B7CBD6DD
candidate SHA-256: D65D2B928ABB79D9361D04FCF6DA98A27F42BCB37298235B010DE53DDC287CDA
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:359539
original SHA-256: 3F64B3AB71015B3A5DE91E6CE5842C6D554158A3657E804BBCEDEB8DA398ECC2
candidate SHA-256: 3F64B3AB71015B3A5DE91E6CE5842C6D554158A3657E804BBCEDEB8DA398ECC2
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_031_counter_v1/reading_packets_v1/expanded_train_359539_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_031_counter_v1/reading_packets_v1/expanded_train_359539_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_031_counter_v1/reading_packets_v1/expanded_train_359539_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:359622
original SHA-256: 87B2B6CF778DE2D18C5F46E313723987488EA886D013BE2D5610EEA1B7570915
candidate SHA-256: 7880E99656A0649E72EB69592CD18E352AC2A4579D26C24C824B1AC9585D13F8
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:359913
original SHA-256: 56528B436D6D3F880E804C552D1D36A740FDEEB33793D7A1A2079D05468203CF
candidate SHA-256: 19941D3EA9F8E6F11188504842B563119CCB7E133CEADF1FE80ABE04D4DD0709
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:360284
original SHA-256: 2DD90897D5241DBB8BB28FBC5D3B9CECDEA7F34FEE57F97C02B89564BD349E7A
candidate SHA-256: 2DD90897D5241DBB8BB28FBC5D3B9CECDEA7F34FEE57F97C02B89564BD349E7A
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_031_counter_v1/reading_packets_v1/expanded_train_360284_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

