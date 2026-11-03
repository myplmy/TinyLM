# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:71294
original SHA-256: A6F81717C2771373E97866DD924A39AC3EB63CD55BFCEDB2C99C133BE93F20E4
candidate SHA-256: A6F81717C2771373E97866DD924A39AC3EB63CD55BFCEDB2C99C133BE93F20E4
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_006_counter_v1/reading_packets_v1/expanded_train_71294_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:71650
original SHA-256: CD30DD3D74A8E2D04472C067EC9F270F9D9CE2B72BC603B016E0A1FEB621701B
candidate SHA-256: 1725FCE336602833647BF3B2AF241B5018F50948FE0BF0C8C499473DCBD1C2C8
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:71831
original SHA-256: 9399311B65BB3FF2FD4C661443AF7C45D955062B394035D47CABBF0FA3771C28
candidate SHA-256: 085A6933131639375655E507F03247E661B875954FC4E793114F7D70D1D27BA7
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:72391
original SHA-256: 6319A6262B2E8F03A4AE2075624945C6E8BC4346359D9C336C9724F06A2720DE
candidate SHA-256: C10B7B6C6770691E95BD0454E3A513A73C17BE006AD5A15A4E7DDFBDCFB8159F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:72632
original SHA-256: B98C1D7FA0B17FC99C5C9A9C40EBCDF01C7BE588931C26D7EA4E23AC9A326A08
candidate SHA-256: 7630B26B64E7D3E2573BCFEBA56A0D22C20716E7DD675069F9BBFF31766B1245
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

