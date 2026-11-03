# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:912389
original SHA-256: DA35BA15DD5C6529ADFE710343AA999EBC66E6934A089AB13183D0C4001B104E
candidate SHA-256: 88139BBFB04E9C1E68D16776307006FA93DC9B87D02A816550291D78770F13CC
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:912673
original SHA-256: 8B0E10EF243E9B487663FDEEE0E317DC2CD43C78E7AB65F89F11036373EE01CA
candidate SHA-256: F2D6FE2F51B246AC0794EBFB767850BEDDBB87FD229DC2AF39B1CCDD2C0FD73D
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:912877
original SHA-256: 142D2A9A9007DD8E1D00CDA19CBCF712946AE58DC5D484C0378C869750CC32AC
candidate SHA-256: 142D2A9A9007DD8E1D00CDA19CBCF712946AE58DC5D484C0378C869750CC32AC
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_912877_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:912919
original SHA-256: 03F68F332FE99CB7967A49CFB5849C35ECA87CC2B5D8300A6659C94822FD10EC
candidate SHA-256: 03F68F332FE99CB7967A49CFB5849C35ECA87CC2B5D8300A6659C94822FD10EC
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_069_counter_v1/reading_packets_v1/expanded_train_912919_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:913201
original SHA-256: 60EA1549F4748958B652303D2EBF8FBF15A75950E6D1C29671DFEE385DC7D5D7
candidate SHA-256: 0DC58FF7D6C4132FDD5E8461A839B6AB8E58553875A2C2FF91EC96033C64990C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

