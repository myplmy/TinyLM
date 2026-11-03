# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:387079
original SHA-256: 58D9ABE714939CBA87A85C0A006E0A6552CE42A2C6A2A37DDC2D498D809455C2
candidate SHA-256: 58D9ABE714939CBA87A85C0A006E0A6552CE42A2C6A2A37DDC2D498D809455C2
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387079_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:387569
original SHA-256: 719E97DC9B136F596724D209B8F6313FC8EC4946066D2B569649F5923FF55F1A
candidate SHA-256: 55428A69812360D98CDB67064C4ACD8FDEF162529B71FCA86B952EEB2C9006B2
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:387604
original SHA-256: 51EAE9EA383B6C656F806E09FC81ADDCADCCD0DBA8894679A92E303B63E7A073
candidate SHA-256: 51EAE9EA383B6C656F806E09FC81ADDCADCCD0DBA8894679A92E303B63E7A073
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387604_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387604_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387604_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387604_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:387622
original SHA-256: 73F0891D8E0DAA66CFA6ACCE8B0CBEE8EEBB68E315817A224088D9DC5665292B
candidate SHA-256: 73F0891D8E0DAA66CFA6ACCE8B0CBEE8EEBB68E315817A224088D9DC5665292B
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387622_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387622_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387622_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387622_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_033_counter_v1/reading_packets_v1/expanded_train_387622_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:387700
original SHA-256: EC65381460FCCEE4586CF954AFC0DDA18145440E3699344CEEB957BE326C7ABE
candidate SHA-256: ABEDAF09565C0AE2AA685366873EEC5C10A82A5D95DCB3878A5486A57F466E85
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

