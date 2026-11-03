# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1197763
original SHA-256: A1E36D99B00E81D99AEBF097D67E6B369D021A398520F579E05177E7FF744A22
candidate SHA-256: A1E36D99B00E81D99AEBF097D67E6B369D021A398520F579E05177E7FF744A22
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1197763_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1199486
original SHA-256: F53390265F600245B6B574026AAB1061FF72C7AC06EE2B5359645EE16C8BCB07
candidate SHA-256: F53390265F600245B6B574026AAB1061FF72C7AC06EE2B5359645EE16C8BCB07
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_033_counter_v1/reading_packets_v1/expanded_train_1199486_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1200371
original SHA-256: 12227FEB4E6C383528534BD7536155C391907BDA36A7BF0FA20154C9F9EA7D9A
candidate SHA-256: 3CEC32BB2BEF1AC83F56AB4510BB2AFA46712D3FEFFB764BDCB0FF73738938D3
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1200374
original SHA-256: D60D04C262498D728B5418E97C3A96A36F1874A98C4F0F2FB099286DC1DE0CAB
candidate SHA-256: 290D77584BCC1997889485719DDEC5CCE85D6A217F3FEF7F91517CD8C9F8F7AC
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1200455
original SHA-256: F4EA4273E0154856477C71BA6211DB6259D48FAB9FFD05484D2E8F6BFAFA3D0F
candidate SHA-256: 7EFCFF989AC8F1976D3FF429E95CD4D4DED7191A2CD8AAC5AECAB52CDA1640DA
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

