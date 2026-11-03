# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:28632
original SHA-256: D452F2DF5F817231CECAE1E044A18498D3BD004C480A43FD48B2796324BB6D60
candidate SHA-256: D452F2DF5F817231CECAE1E044A18498D3BD004C480A43FD48B2796324BB6D60
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_004_counter_v1/reading_packets_v1/expanded_train_28632_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:28688
original SHA-256: 95BCCE88209DF73F9FF49C68435A58237A4A9F8635696143EE86908F47F01408
candidate SHA-256: 95BCCE88209DF73F9FF49C68435A58237A4A9F8635696143EE86908F47F01408
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_004_counter_v1/reading_packets_v1/expanded_train_28688_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:28702
original SHA-256: C8ADE0AD79E7EB25CEC02AD57EA7853A45E00F43B08A36B10A93D768E55780B0
candidate SHA-256: 3E66A5850D0D6680F6BB3F79AF5F6E9E957B55DDB9E3D6ADF8D529D8896AA443
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:29417
original SHA-256: 3C69A1E8F470C42E4D0CB4384FA166F3DA57862C8CE5A769056E1EFB62800802
candidate SHA-256: BCA372D0B450D52D42D04C3DC11031B1D670C98DB844862236ED1DC5D4276EC7
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:29470
original SHA-256: B91E5A61F3EBD3EE4AB9BDA2B4AE26EAB446160E23A1AED06C46FF16DC611CCD
candidate SHA-256: CCF56B304D13CB58116A22D58219910D81DD7758DC273F45474BF86D0E00DC89
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

