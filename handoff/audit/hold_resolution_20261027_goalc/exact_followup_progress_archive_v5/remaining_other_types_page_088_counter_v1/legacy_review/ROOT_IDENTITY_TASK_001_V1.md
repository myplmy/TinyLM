# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1239158
original SHA-256: ADE3CE6EC40B8AAFB8A036AE72E2ACC1CC03803D816CAD368C6CB9EB502A443F
candidate SHA-256: ADE3CE6EC40B8AAFB8A036AE72E2ACC1CC03803D816CAD368C6CB9EB502A443F
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_088_counter_v1/reading_packets_v1/expanded_train_1239158_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1239208
original SHA-256: 221D17C957ECE4A46AE5640952CB9B878817F50D0F17774F623A4647189CB004
candidate SHA-256: 221D17C957ECE4A46AE5640952CB9B878817F50D0F17774F623A4647189CB004
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_088_counter_v1/reading_packets_v1/expanded_train_1239208_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_088_counter_v1/reading_packets_v1/expanded_train_1239208_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_088_counter_v1/reading_packets_v1/expanded_train_1239208_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_088_counter_v1/reading_packets_v1/expanded_train_1239208_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1239328
original SHA-256: 9675A20B7CDABA89F8F4C4CDE31FF0971F0BA307C4F297143C07603CF3605EA9
candidate SHA-256: 533F1988F243D55A802EFF7C46DB7BF6CE0BBA851400598754C848008CCF289F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1239599
original SHA-256: AF84293858E83B14713D6EF71719F7C411B0A078FADC6F334E3E2FB0B9A3284D
candidate SHA-256: 701C351D5CF23406C7B604EF75F8A151940526044D625120031491A1171830BF
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1239807
original SHA-256: CEC70C744593EE4049333DF0206812BF3F428BD48961986996EE91550EB5512B
candidate SHA-256: CEC70C744593EE4049333DF0206812BF3F428BD48961986996EE91550EB5512B
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_088_counter_v1/reading_packets_v1/expanded_train_1239807_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

