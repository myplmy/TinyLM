# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:14918
original SHA-256: 65810C3FF2A68D88A8D5821CDA4EBFF0CA496598B234B5AC167F7C02313E1CFD
candidate SHA-256: 22D7B1A43D4186BF58F67E736334D83A78002090E703BB78E56D9BAB17E7D77D
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:14919
original SHA-256: B7611061827BD58515ED52AAEA0609F7324D9A0C9BA0012C565699D8D63288A6
candidate SHA-256: 9A4A9F53C0FC3C16EBF5E291132FB50C235C5E3DF1846BDC438F3F1C11966A8B
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:14931
original SHA-256: 4FD9822EEFBBA882910EE0D6C05DC791885D6759711B8728DD7D0DF1FE13C0E8
candidate SHA-256: 4FD9822EEFBBA882910EE0D6C05DC791885D6759711B8728DD7D0DF1FE13C0E8
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_003_counter_v1/reading_packets_v1/expanded_train_14931_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:14936
original SHA-256: 300FD505A4C094C89C91663015B99A96754B5E7FE69E10B8515420A5C3772917
candidate SHA-256: 300FD505A4C094C89C91663015B99A96754B5E7FE69E10B8515420A5C3772917
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_003_counter_v1/reading_packets_v1/expanded_train_14936_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:14942
original SHA-256: 6A7DBF66D0E83468AF99FF3F2C2D5429EC564608DE6148048DC0B171937F7A32
candidate SHA-256: E3FB516ACF71841FD25C61BB2697B40F25171E464D79A6107B96301CFAF976A6
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

