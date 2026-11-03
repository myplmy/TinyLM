# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:593518
original SHA-256: 8901322EFF9E93629DD259D5D0858C8E2321F8C77165DE9F8B4A198A4F4D95E7
candidate SHA-256: 6163D5212E459E8984958BB36688D11860699EA9706F882923578743E94AD211
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:593865
original SHA-256: E32D9D9BAB879F967AAC679F65941864D5208F9A7A1FCF7C312FBCA5ADF9E36A
candidate SHA-256: 1C5B8C95BA358CF3597E16DE3F4A2E3BCD17BD558CD989AF4E2DD5341288E1C9
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:594060
original SHA-256: EE73784938DC29BD34551C084F2249A713C5906C3E8A74CD92CE2A03CBF7C0A7
candidate SHA-256: EE73784938DC29BD34551C084F2249A713C5906C3E8A74CD92CE2A03CBF7C0A7
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_047_counter_v1/reading_packets_v1/expanded_train_594060_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:594112
original SHA-256: E9294FF7A3477832354B39648196F910158D1ABFBCCE44554F68DAEBB88D7471
candidate SHA-256: 012B8AF135D70EDD124A706F43B1B35CEC366260EBE6757E9DB0CE184D75A73D
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:594280
original SHA-256: ABA07A7E8F046162C8CD8825ED53D6BCBFF643384BAB1CD90AD74BCB279BA82C
candidate SHA-256: ABA07A7E8F046162C8CD8825ED53D6BCBFF643384BAB1CD90AD74BCB279BA82C
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_047_counter_v1/reading_packets_v1/expanded_train_594280_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_047_counter_v1/reading_packets_v1/expanded_train_594280_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_047_counter_v1/reading_packets_v1/expanded_train_594280_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_047_counter_v1/reading_packets_v1/expanded_train_594280_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

