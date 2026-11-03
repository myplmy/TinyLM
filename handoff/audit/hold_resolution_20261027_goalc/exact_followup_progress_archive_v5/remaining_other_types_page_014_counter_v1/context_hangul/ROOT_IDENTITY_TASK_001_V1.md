# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:136171
original SHA-256: 6B85182BC74AC0313B084FBBB66E74669131499240EC0137CC854014A421E721
candidate SHA-256: C909969983F978C55F8765F347FD9AA3D46490E640B89CCFC61D2539C7A248C1
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:136272
original SHA-256: 9D5CC38AD1DC3C1762681209A5BCC2AC6BF91D5C1261D7E35790BE4F803C807F
candidate SHA-256: E55DC9AC2A24799EC4C7FFE6978630DE4AFF908D670792CD2197EF84693684E5
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:136318
original SHA-256: BEF444DEC5D3032F2B170A9C437821AE9C8119DDCE3FB153AABBEDF4D20DC0FD
candidate SHA-256: FEBE696C485562DEABBD2A40106B420C28082597EF61D9FD867A6CB990E77F43
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:136562
original SHA-256: DC9941E89E1A06E1A3C5B007EE59A9A9EB8A2607150FBF9FBF8569C21F464A13
candidate SHA-256: DC9941E89E1A06E1A3C5B007EE59A9A9EB8A2607150FBF9FBF8569C21F464A13
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136562_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136562_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136562_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_014_counter_v1/reading_packets_v1/expanded_train_136562_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:136724
original SHA-256: A62E8D1FF0513A6785B62332AD2E57CBA94F53958A7D1A5FA789A2E7106C44EC
candidate SHA-256: B86A5220DD9196ABDE06A0E67DA8B4E68919F8F7E5A6847B2ADE98AC5F0381F0
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

