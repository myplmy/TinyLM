# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:873048
original SHA-256: A14E3D7B36DA756A071BBA7FEB8C66CB13D1F791E92702CC42E7F58946CC3182
candidate SHA-256: 1BEAAF31B9777247CABD3AA6670BD9DCD5171D3A0B98C1E59C3A2453C9A71EE2
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:873678
original SHA-256: CB4A9EF3493E632A8BD410EFA546BE1182C86C1761CCDD3EE6F96021C2AD4E8D
candidate SHA-256: 02BB8B35DC73B00CC479E947EEDF16CE8891A82733D2F4AD61A3380C6C3EEC70
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:874326
original SHA-256: 82457AA6790DC62AE50A8FBE66BA0F1745348EDB46F240EF9478E827F78E4099
candidate SHA-256: 82457AA6790DC62AE50A8FBE66BA0F1745348EDB46F240EF9478E827F78E4099
원문 frame 패킷: [1, 12]
최종 full_diff 패킷: [24, 24]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 24]
후보 중복만 있는 생략 가능 패킷: [13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_027_counter_v1/reading_packets_v1/expanded_train_874326_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_027_counter_v1/reading_packets_v1/expanded_train_874326_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_027_counter_v1/reading_packets_v1/expanded_train_874326_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_027_counter_v1/reading_packets_v1/expanded_train_874326_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_027_counter_v1/reading_packets_v1/expanded_train_874326_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_027_counter_v1/reading_packets_v1/expanded_train_874326_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_027_counter_v1/reading_packets_v1/expanded_train_874326_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_027_counter_v1/reading_packets_v1/expanded_train_874326_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_027_counter_v1/reading_packets_v1/expanded_train_874326_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_027_counter_v1/reading_packets_v1/expanded_train_874326_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_027_counter_v1/reading_packets_v1/expanded_train_874326_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_027_counter_v1/reading_packets_v1/expanded_train_874326_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_027_counter_v1/reading_packets_v1/expanded_train_874326_0024.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:876153
original SHA-256: E3DC2B095375C4FD7EFE0946F84BC52138549D239BC75A6F24716B5B2EB4A2E0
candidate SHA-256: E3DC2B095375C4FD7EFE0946F84BC52138549D239BC75A6F24716B5B2EB4A2E0
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_027_counter_v1/reading_packets_v1/expanded_train_876153_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:877049
original SHA-256: B6B27AA2A2FBB6CB9BB5443B337856951EDD2BB378D5DCBA9D8F4571EF8EFC45
candidate SHA-256: 8D4E02871811D6EFCE0108162EDDCB774EC15FAAB6AEA7710EE9CF75FDC8277A
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

