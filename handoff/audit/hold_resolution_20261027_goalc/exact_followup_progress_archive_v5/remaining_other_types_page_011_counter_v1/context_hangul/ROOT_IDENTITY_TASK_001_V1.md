# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:103797
original SHA-256: BFDF7E3DA89681F12A4F319486C73001308786B0DDAB78B1AEEC9E6FB3487867
candidate SHA-256: BFDF7E3DA89681F12A4F319486C73001308786B0DDAB78B1AEEC9E6FB3487867
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_011_counter_v1/reading_packets_v1/expanded_train_103797_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:103806
original SHA-256: 59E03C332A88C03C080C48CE5C0FB9A62B2713547A4A05C9B6CACD36DA5A7240
candidate SHA-256: 59E03C332A88C03C080C48CE5C0FB9A62B2713547A4A05C9B6CACD36DA5A7240
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_011_counter_v1/reading_packets_v1/expanded_train_103806_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:103810
original SHA-256: 324BA3226909612A4F16F8D109DB9FA99D6CD9F634C45950CFD31165D95C83E0
candidate SHA-256: 324BA3226909612A4F16F8D109DB9FA99D6CD9F634C45950CFD31165D95C83E0
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_011_counter_v1/reading_packets_v1/expanded_train_103810_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:103898
original SHA-256: 7508005510D7CF72EE7E4F4D640B406E3B0FFB73B7D1C03A5B9E090A20FFBBB3
candidate SHA-256: 7508005510D7CF72EE7E4F4D640B406E3B0FFB73B7D1C03A5B9E090A20FFBBB3
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_011_counter_v1/reading_packets_v1/expanded_train_103898_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_011_counter_v1/reading_packets_v1/expanded_train_103898_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_011_counter_v1/reading_packets_v1/expanded_train_103898_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_011_counter_v1/reading_packets_v1/expanded_train_103898_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_011_counter_v1/reading_packets_v1/expanded_train_103898_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:104133
original SHA-256: ABFC8E151B7A9CB18BA4295768C2A3A21BADFA32DEDDE1C2B6F319A671152E85
candidate SHA-256: ABFC8E151B7A9CB18BA4295768C2A3A21BADFA32DEDDE1C2B6F319A671152E85
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_011_counter_v1/reading_packets_v1/expanded_train_104133_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

