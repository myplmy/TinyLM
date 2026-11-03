# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1255515
original SHA-256: 67644ED693E56D5E3BDF6FA5E865817511E23A77174D4E13A1FFB8571A85935A
candidate SHA-256: 7FBDCD4EBDBB854F8EC032D26F480A210AA86DAE10421CBAFB48308BE2A37EE2
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1255617
original SHA-256: 2FF4D1C635F7FD1B72EC323668AB391E615DFF2309087BB413183CF1DCBD32F9
candidate SHA-256: D5A1D5B6C14735D632A5870575E2858F4AC5D772CA8F51F56003DBDB03A32F5E
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1255623
original SHA-256: 2B947A4F1E9E088BB661BF26502131185E38C1019C0C1D3BC56CED55096A435B
candidate SHA-256: 2B947A4F1E9E088BB661BF26502131185E38C1019C0C1D3BC56CED55096A435B
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_035_counter_v1/reading_packets_v1/expanded_train_1255623_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1255647
original SHA-256: C42FC2F4B29C819E0B7BC6F180C02CE982A35BBDF2A4E39D9934E8610C625A89
candidate SHA-256: AD857C92E3294C9BE5433E9C19C3546DFADE9A2B66D0D77F868A386F33E22486
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1255721
original SHA-256: CFAAF0E9FEC363CAE2B8960CD45395F60AA989C8ADB3F5E0338A5519D5EDC8AA
candidate SHA-256: 7C650CE044BE9DB570FFB4FE986E579E8C30061AFD66B7560786E5275C912A28
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

