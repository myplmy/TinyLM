# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:452511
original SHA-256: AA76C6F96773F1CE012A5BB6A367603D11C3C676D24B7244568D1294BAA92401
candidate SHA-256: AA76C6F96773F1CE012A5BB6A367603D11C3C676D24B7244568D1294BAA92401
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_017_counter_v1/reading_packets_v1/expanded_train_452511_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:452686
original SHA-256: C38D4EB1A97D844353D73DA99BB035F4253CF9031157A7B1B342A0264EFFA533
candidate SHA-256: 111B534818E82E6A688192EBFD3A999E2DF45129A30FE3A37920383DC4EBDE94
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:452785
original SHA-256: 60E7A94558922A949249A70A485F59A69DC763020D25EDF37A34943C5430F8B1
candidate SHA-256: 60E7A94558922A949249A70A485F59A69DC763020D25EDF37A34943C5430F8B1
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_017_counter_v1/reading_packets_v1/expanded_train_452785_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:452793
original SHA-256: 968235AA77F8856D330436A04F284567AB49466354CBC5D5732644B42F535B42
candidate SHA-256: 968235AA77F8856D330436A04F284567AB49466354CBC5D5732644B42F535B42
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_017_counter_v1/reading_packets_v1/expanded_train_452793_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:453055
original SHA-256: 4DF75AFF406F6444953870DA87520CB5DB0C68D0C78B678D29ADD99F6DF8C210
candidate SHA-256: 330838AC88CCE08FEC23CCCCC976578C369FAEA2B093D76AE9097561F7085851
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

