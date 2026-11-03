# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:10129
original SHA-256: F953A963F62FA872308D13439F66A208B36C2E310351330D633368A856643317
candidate SHA-256: 68FE318A71BABCFEB8DC4C776BE10560EBDD05D1A948814E0CDAA484E0CC3A6D
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:10166
original SHA-256: 9B182EF4B9BCEAC8DBB416E490FB6A357990DD8FFAF0859625E377D97B8AF98B
candidate SHA-256: 9B182EF4B9BCEAC8DBB416E490FB6A357990DD8FFAF0859625E377D97B8AF98B
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_001_counter_v1/reading_packets_v1/expanded_train_10166_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:117
original SHA-256: 0BB7D50035783F94D9ACC1ABFAE3594CB848359CF7DE71C3C5B5BE9C4C797E2D
candidate SHA-256: 739FAB5EB2E19C2A869519E46105FAFC32C0C530EDFDEF115AE534196F587ABA
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:143
original SHA-256: 23D42297CAC349E8D98C6E60659C57DBD27289DEA15A87B18FFB5614901472D6
candidate SHA-256: 791A59E18E7DB654E77C4C53757BF170191AC6F41C882E017BEF1F3840070119
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:170
original SHA-256: 364320DF346BF72DB49DFC330F3A812189D6048985EFD86E91F8A4DA36A5F96B
candidate SHA-256: 74F3515763E20ED53B9C359664546F7293A93613A053A6303C611590F86E2D85
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

