# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:695251
original SHA-256: C5F1BB9CF4D801365BAA705D464050D955E1DB18D6401803F49835A4A2913792
candidate SHA-256: 125D575B50889050E1A9AFBAF68DA60B4807A2E40AB6B30F3ED4A13E88310921
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:695311
original SHA-256: B028EB5C81AC0CEFAFFA255C231E47328262FA0F820840C6D2BDFC4FFF182C72
candidate SHA-256: B028EB5C81AC0CEFAFFA255C231E47328262FA0F820840C6D2BDFC4FFF182C72
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_023_counter_v1/reading_packets_v1/expanded_train_695311_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:696031
original SHA-256: 232EA969359D19E97C00FA3630D2330E8EACC1EC195B7BA80DAB5F600EEE6617
candidate SHA-256: B46041CC7643243705879DC5929183FF852D90C06486C426FD44F01B9344BCD7
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:696127
original SHA-256: 7F2D4B33539EFC97FAB204F174D59EE6B4C0F1D9578ABE8660313AC44A709B2E
candidate SHA-256: EF898027ABDA9888E015AEBF40FE0C12D729AAA2C608FC0F4916BEF0E9A0C41C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:697241
original SHA-256: 743045A34173474DA9392F50349987BD745BE9D0511EDA2A0B76A659C31798A9
candidate SHA-256: 743045A34173474DA9392F50349987BD745BE9D0511EDA2A0B76A659C31798A9
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_023_counter_v1/reading_packets_v1/expanded_train_697241_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_023_counter_v1/reading_packets_v1/expanded_train_697241_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_023_counter_v1/reading_packets_v1/expanded_train_697241_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_023_counter_v1/reading_packets_v1/expanded_train_697241_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

