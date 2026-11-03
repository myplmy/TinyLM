# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:695621
original SHA-256: 192BD44810D65D168FC2297254E0D71EB0F5D288DC37C26331671ACF84CF7FEB
candidate SHA-256: 1793E54356349C9793BDD6EBECB1C20FA550E504B8373251EC686D5DA102550F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:695735
original SHA-256: C95F2C663E408E5F88F8FE9DE26173094BF3B0EAC5E59A44B631672A74F66610
candidate SHA-256: AB45F26EF7CF6AB8E77C9DC2B1359A928D1B407CA74DF5938FB3A26882FA4EDC
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:695865
original SHA-256: 1AB0D44BD66C4F8EB286E992D8C03D5AFA2AABC3DE8F0C60364F11FEBAF81105
candidate SHA-256: 1AB0D44BD66C4F8EB286E992D8C03D5AFA2AABC3DE8F0C60364F11FEBAF81105
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_023_counter_v1/reading_packets_v1/expanded_train_695865_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_023_counter_v1/reading_packets_v1/expanded_train_695865_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_023_counter_v1/reading_packets_v1/expanded_train_695865_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_023_counter_v1/reading_packets_v1/expanded_train_695865_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:696214
original SHA-256: E44409CE1080DDDC0615EE40ABC5D9704F5647E7B273AA672A2E6A47B4D2DD6C
candidate SHA-256: E44409CE1080DDDC0615EE40ABC5D9704F5647E7B273AA672A2E6A47B4D2DD6C
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_023_counter_v1/reading_packets_v1/expanded_train_696214_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_023_counter_v1/reading_packets_v1/expanded_train_696214_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:696722
original SHA-256: 96AD1A73F79EC1796F34B435FB4ED4493B47039E0CED6C1633E6EDF6389D6BEB
candidate SHA-256: 96AD1A73F79EC1796F34B435FB4ED4493B47039E0CED6C1633E6EDF6389D6BEB
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_023_counter_v1/reading_packets_v1/expanded_train_696722_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

