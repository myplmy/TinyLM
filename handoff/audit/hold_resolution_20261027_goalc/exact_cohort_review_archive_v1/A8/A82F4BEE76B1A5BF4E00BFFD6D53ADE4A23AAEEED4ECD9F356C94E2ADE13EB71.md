# 정확 입력 전문 판독 연결 TASK_015

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:475232
original SHA-256: 75DEF3AB7BFA7A76A079BB1D76ADC79B3EC237D99FD6E249B3145E40A37B5C5F
candidate SHA-256: 75DEF3AB7BFA7A76A079BB1D76ADC79B3EC237D99FD6E249B3145E40A37B5C5F
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_017_counter_v1/reading_packets_v1/expanded_train_475232_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:475787
original SHA-256: C05444854F05873667D4453B4CFD379905290284FB1D040D7DC718D87B6995E8
candidate SHA-256: D6872983BD8533DBC87C31D8FB72D7C5F22E02D322F542E129BF5957BC73CFF6
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:475901
original SHA-256: 44AE4446DC25C00122962E7DFB92CEC2747E6D76D78ECD2A4EE017DB8C8FAE61
candidate SHA-256: 44AE4446DC25C00122962E7DFB92CEC2747E6D76D78ECD2A4EE017DB8C8FAE61
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_017_counter_v1/reading_packets_v1/expanded_train_475901_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:475910
original SHA-256: 16D816E86ADF778AF7BB27E8F5B33BF958618F7C877EF8AAEB26578DB630739B
candidate SHA-256: 16D816E86ADF778AF7BB27E8F5B33BF958618F7C877EF8AAEB26578DB630739B
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_017_counter_v1/reading_packets_v1/expanded_train_475910_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:475914
original SHA-256: 45BA4712F41DE5806E1EF9F51730A7B7B465737B544BEC035E666946E9FDB289
candidate SHA-256: 45BA4712F41DE5806E1EF9F51730A7B7B465737B544BEC035E666946E9FDB289
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_017_counter_v1/reading_packets_v1/expanded_train_475914_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

