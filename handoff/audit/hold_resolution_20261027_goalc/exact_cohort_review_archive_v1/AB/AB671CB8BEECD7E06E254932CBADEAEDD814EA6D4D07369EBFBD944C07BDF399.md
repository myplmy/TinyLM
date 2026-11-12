# 정확 입력 전문 판독 연결 TASK_017

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:515272
original SHA-256: 65AAB0BC7E97892B3B609E8D570B650F3245812DBE237E92F9B7885FC2397489
candidate SHA-256: 65AAB0BC7E97892B3B609E8D570B650F3245812DBE237E92F9B7885FC2397489
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_018_counter_v1/reading_packets_v1/expanded_train_515272_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:515349
original SHA-256: FE8AEB6131ACA194611B030AFE1E4D105195B7A222005CF208B0871B0A51277B
candidate SHA-256: 641CAE1EA31D53BD7E8FA3ADABD5D7212D0B812977B90869690CC2449C260244
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:515534
original SHA-256: 164BA6D4F60061682FEF6565BF820C5B91C4AE647D29A17DE1D055C54BBA1AEF
candidate SHA-256: 164BA6D4F60061682FEF6565BF820C5B91C4AE647D29A17DE1D055C54BBA1AEF
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_018_counter_v1/reading_packets_v1/expanded_train_515534_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:515820
original SHA-256: 404BBB2730B455182F24EE0771464C34663A65C090F29F5D77128351B8B993FA
candidate SHA-256: 404BBB2730B455182F24EE0771464C34663A65C090F29F5D77128351B8B993FA
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_018_counter_v1/reading_packets_v1/expanded_train_515820_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_018_counter_v1/reading_packets_v1/expanded_train_515820_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_018_counter_v1/reading_packets_v1/expanded_train_515820_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_018_counter_v1/reading_packets_v1/expanded_train_515820_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_018_counter_v1/reading_packets_v1/expanded_train_515820_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:516051
original SHA-256: F9CA3660C13072DF9C695DBB8102A4384CAEEE562F1287A79B97F0B8237C2E11
candidate SHA-256: 9D2ECEA65FFD0B8BFCCC7D850F6A45E5229425F50F69E8BD0952546E586468C6
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

