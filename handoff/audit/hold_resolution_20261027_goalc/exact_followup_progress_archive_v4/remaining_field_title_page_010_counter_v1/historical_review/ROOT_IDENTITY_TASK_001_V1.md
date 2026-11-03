# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:180517
original SHA-256: 757EB6A048092AA8DDC87709C23F134B21FA8582E741C769A7C7FB174A3FDE5F
candidate SHA-256: EF65CF59EE7B29B74F0169F87CD0C4FB32D14DF0BA67A5607CBE1055B324E066
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:181299
original SHA-256: FA2D0B2CFFD1E52BCE83A8F96449D612299766E00A5466309ED0B989D659B3AF
candidate SHA-256: DB9C9C118DEB814BF007A78F85896624E93376B6E1F473AB1705CAE563DCD165
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:181529
original SHA-256: 26A4265FC51AF9FE77354BB126E6068931ABC93EEDB14B7FDFCDC72409FD0428
candidate SHA-256: AAA4B0782FEFFD50BB1D60F0EA22326B4DF7B3025E9E0496979463AF4EE0B937
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:181551
original SHA-256: 5275819B4AA35212267E74D2307350A5F3DF36A7606F4F7D8A5371FEBF70722C
candidate SHA-256: 880F0C76FA180520E106F5C48046EB61E18C1B0ACB3CBB3528363B903B34614C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:181616
original SHA-256: 79D09CA0642AB09E678E76205BC9BB885FFB925764CE53527E7476CF3C8F34EF
candidate SHA-256: 79D09CA0642AB09E678E76205BC9BB885FFB925764CE53527E7476CF3C8F34EF
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_010_counter_v1/reading_packets_v1/expanded_train_181616_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

