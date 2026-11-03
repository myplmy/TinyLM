# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:733678
original SHA-256: 9FF026995BA6254B721CE61B09FA40560B23C9FA2CE07D1053726728E8341AB4
candidate SHA-256: 9FF026995BA6254B721CE61B09FA40560B23C9FA2CE07D1053726728E8341AB4
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_057_counter_v1/reading_packets_v1/expanded_train_733678_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_057_counter_v1/reading_packets_v1/expanded_train_733678_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_057_counter_v1/reading_packets_v1/expanded_train_733678_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_057_counter_v1/reading_packets_v1/expanded_train_733678_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:733730
original SHA-256: EC4458843CD180FD227F2E05EFAF6F8029A4A016D40CE2C76B972E6481411DEB
candidate SHA-256: 85E34ECA0392BB34D08324762B1BD1E98029FE802EAEC5660DC6407FE510C4F6
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:733736
original SHA-256: 32A5DD20F4F8A082BD6922A67FD52FFDC44A022BB96A01EF1101B2D82E9F3CAA
candidate SHA-256: 32A5DD20F4F8A082BD6922A67FD52FFDC44A022BB96A01EF1101B2D82E9F3CAA
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_057_counter_v1/reading_packets_v1/expanded_train_733736_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:733779
original SHA-256: 50BEC5C2224974FE3BD6A81D257EF073170A3C177942158B012ED70C37C51FB1
candidate SHA-256: 7281BD3E48EC9F77E2EDD77D40ADE2D560063CB53DE007F8C101A29A38976BEB
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:733965
original SHA-256: 4A6FC682BC089EC3C38234BC6657200CD8501C37C6ADD8E345B5A33BB315474F
candidate SHA-256: F17CD2336DA2188FE5BFFE180B33470B20903057A3AC59548EC4623319DB7B98
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

