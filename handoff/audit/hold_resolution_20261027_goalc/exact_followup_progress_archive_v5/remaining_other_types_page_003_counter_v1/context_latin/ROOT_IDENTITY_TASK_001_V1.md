# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:24086
original SHA-256: 9FF5B44324B45A0415C5F3EE319ED730F3D851FB7CFE3F6585EE0977306E0415
candidate SHA-256: 81566C94636DA0E85CB213DDA06830981A6CD78409C88E8030EA7BABCBF8A532
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:24207
original SHA-256: 4EBCC3773105D13481AFC5B6C52A620389367BAAFD563E08A1C2A5534C2927F1
candidate SHA-256: 7569DD98ABEB7CBB23F3A93164DE4E12D45008FEC4DEE5BD4F3292DD8D2374BD
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:24240
original SHA-256: AD34277AB24B9A3C5B1006FEB5FFE44CDE476E85F7849EC66A1A293F139D70A4
candidate SHA-256: C4C4EFB18754E28AB7058FE870EA71F572813D335C139BD08E1F31DDAD28A6B3
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:24326
original SHA-256: 39A8E1FAB2A69DEC0C4863C424A0E5E70DE8AC0872C60933B1D243FAFE12BE1E
candidate SHA-256: 39A8E1FAB2A69DEC0C4863C424A0E5E70DE8AC0872C60933B1D243FAFE12BE1E
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_003_counter_v1/reading_packets_v1/expanded_train_24326_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_003_counter_v1/reading_packets_v1/expanded_train_24326_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:24329
original SHA-256: DB4DD185E22FF2CAB8EF48D188E3DBDCCAB43E8B508C201FF920E5AA5ED6E9A4
candidate SHA-256: 4F314B4A257AA985973059DBA7E27C9AA7355A17A28DE780E886BEEBE09ACE90
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

