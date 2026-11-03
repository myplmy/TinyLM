# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:271277
original SHA-256: 8B86F8911E8A10FBC853EAC72F43EEFCE33075501D9F9615E91AAE69B2ADD40F
candidate SHA-256: 6E546D4898DA81F338D189B1FC75FFC62701343C1471D2C96C1AE15E7CC16AD4
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:271344
original SHA-256: F92DB0CB7534307250DE794B6E1991B9161BEC7ED8CA6A45B5BAB02877266CEE
candidate SHA-256: B9F090FC92E6E03752217C245B798BBB0DC73201A9336A41703F7ACC32615779
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:271349
original SHA-256: E244711EC642085368F3856CCCC5AD64BB49C540626324407DE0C0D1C31B989E
candidate SHA-256: 3E1BA9DC0EED05918425C8F5BC8C3D0A1DDF6CF8EAB944CF4E96FA2266A75E38
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:271529
original SHA-256: 12AB42889456D4B05561A4B5436B9DB59E2FDF4A1A1041A54BC316B31135C909
candidate SHA-256: 4883F1750B2369BA1B4F912EDFBF0DC139121F27E76538E15F1208CDFBF2718E
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:272177
original SHA-256: 15BFBAC7B97AF596EB90FC7DB2EF07074932DD8BE84565E525E04FDF94AB8FB0
candidate SHA-256: 15BFBAC7B97AF596EB90FC7DB2EF07074932DD8BE84565E525E04FDF94AB8FB0
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_013_counter_v1/reading_packets_v1/expanded_train_272177_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

