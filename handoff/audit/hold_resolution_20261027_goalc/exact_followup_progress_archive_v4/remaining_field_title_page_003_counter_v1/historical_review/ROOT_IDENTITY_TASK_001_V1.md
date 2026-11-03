# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:14921
original SHA-256: D9C5ACA990D8AC54983C757D58A173362A4BD5E183ED37A24816E58C674A76DE
candidate SHA-256: D9C5ACA990D8AC54983C757D58A173362A4BD5E183ED37A24816E58C674A76DE
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_003_counter_v1/reading_packets_v1/expanded_train_14921_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:14929
original SHA-256: 63827383CE552538F31E3F3760033F754ACC66E347F1DCC6EF4C50925189D35C
candidate SHA-256: 63827383CE552538F31E3F3760033F754ACC66E347F1DCC6EF4C50925189D35C
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_003_counter_v1/reading_packets_v1/expanded_train_14929_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:14939
original SHA-256: AEF07E4D2E815B457EC130B5B0649CFC8BB078E6CDFF3C513598BEE271147B2E
candidate SHA-256: AEF07E4D2E815B457EC130B5B0649CFC8BB078E6CDFF3C513598BEE271147B2E
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_003_counter_v1/reading_packets_v1/expanded_train_14939_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:14948
original SHA-256: A7BD468D99951C3CB333A50A5BE1A40C78D903B210D88A0F220DA8EA3B600290
candidate SHA-256: 7956136522A339E801F816FA478F0B286980B3F3644226F1A110E2032F8A09C0
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:14950
original SHA-256: 34E1225E39CD0285C0DB8A541953C547F471CB47B296B04413C41568277CAA7C
candidate SHA-256: 50FEFCBA66B684B77E2452AF46E9DE88D8B88D3BDFB5AE6AB3E0C590E947BA8E
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

