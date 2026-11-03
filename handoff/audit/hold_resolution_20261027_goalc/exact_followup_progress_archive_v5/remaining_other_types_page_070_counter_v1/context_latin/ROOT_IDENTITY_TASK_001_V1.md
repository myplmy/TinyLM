# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:930097
original SHA-256: CC833A7CB0515DE6BAD7471461E7BCC05CE12D8012298509BAA7DF4B3A9D6B09
candidate SHA-256: 3BB406276EA382B4C70B77A6B9B28048AC3FAF62329EA7203DBB08C4383BFBC7
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:930159
original SHA-256: 92907D9396B636CE3D0CFCDC745997BB418812910A1095B2E4962ADADC475408
candidate SHA-256: 92907D9396B636CE3D0CFCDC745997BB418812910A1095B2E4962ADADC475408
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_070_counter_v1/reading_packets_v1/expanded_train_930159_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_070_counter_v1/reading_packets_v1/expanded_train_930159_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:930191
original SHA-256: A9AB080CCB609208663F2F9251A7DA8BA4E089C9294FD323C0051D3D202E0A89
candidate SHA-256: A9AB080CCB609208663F2F9251A7DA8BA4E089C9294FD323C0051D3D202E0A89
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_070_counter_v1/reading_packets_v1/expanded_train_930191_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:930638
original SHA-256: 56F08D3FC5792FA3EA748CF57C5F772C3F16EE4DE1119F74B0F3F9E4F914B6DB
candidate SHA-256: 1909366AFCE14CF72A3576F14D1C9FEB2EDC3DEC67825D79408887BA3C7E7C9D
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:930690
original SHA-256: 538E3989792D73C2A5F991ED15182F475D158F43D8030DFF5C234A2C2E8B1E20
candidate SHA-256: B774CC7258FDF32BDB1C69272674CACBBFF6F872B50214B665EF45121DE36C24
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

