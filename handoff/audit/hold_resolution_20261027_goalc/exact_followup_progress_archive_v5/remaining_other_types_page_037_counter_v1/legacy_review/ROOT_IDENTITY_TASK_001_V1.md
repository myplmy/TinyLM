# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:446229
original SHA-256: A5F6B7437B1C62A69A41065231A04B1731C08CBE65F843CA9E99BFDFF2D5C4F8
candidate SHA-256: A5F6B7437B1C62A69A41065231A04B1731C08CBE65F843CA9E99BFDFF2D5C4F8
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_037_counter_v1/reading_packets_v1/expanded_train_446229_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_037_counter_v1/reading_packets_v1/expanded_train_446229_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:446332
original SHA-256: DC98BF4272DDE755F7972D72C8440E1D2484F3EDB71665C4953B6C40842E291D
candidate SHA-256: CCCBDAD4A39988623E052FA03AC94E6977796E5E8281504ADAA489BFB9F7F962
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:446452
original SHA-256: 51178648BE9EEE90BE56A83487F78FF465385BA752F4D3865631EFD4A0356271
candidate SHA-256: 33FD641E8CABBDD0F245155A5E63CB2C6002295C4F0C8ECBE6F06F2C44D58C30
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:446455
original SHA-256: 309CC11E0F4F81FB9E7F47629B3F51E6027F336FC65046121AFEC9A40B6E4958
candidate SHA-256: C08DF2507618D7A18858FE7FEA3FE3618564B2B55C2578B7ABE8219A09BFFB06
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:446562
original SHA-256: 1B56893E8E4D66966FCC9F234F5050C60D904D072402D4E9D7446238E613DCA2
candidate SHA-256: 1B56893E8E4D66966FCC9F234F5050C60D904D072402D4E9D7446238E613DCA2
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_037_counter_v1/reading_packets_v1/expanded_train_446562_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_037_counter_v1/reading_packets_v1/expanded_train_446562_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

