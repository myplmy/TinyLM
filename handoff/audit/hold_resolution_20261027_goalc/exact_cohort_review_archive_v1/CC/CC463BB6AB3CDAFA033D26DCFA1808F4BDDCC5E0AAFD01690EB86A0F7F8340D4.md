# 정확 입력 전문 판독 연결 TASK_011

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:79080
original SHA-256: 758005677DAB6EEF82ED2E569C825B5119160CA8F57A5C36313A5369542D16A7
candidate SHA-256: 289D2DD2C5CB1E47DA0DA365EC8C4FF37EF5E11898AD67BB10716413F15862C0
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:79096
original SHA-256: F827C40311A1F6C5CD0931BD11E27FD7F7F755AACB75499132B31F923FF9C7C7
candidate SHA-256: 82F2861B5E4FC830AE85DB51059EB89DC1D1ED6C36B4BA338B794131F8044A66
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:79283
original SHA-256: 41CDB1BE74E6ECAD93292CD5048FF9C7B35F5533C7ABFFF7399D6D8496594D69
candidate SHA-256: 09F738A1B3F632304EF12C8C23EBC93672835A2422DB899F2E4A8BDD75650D16
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:79494
original SHA-256: C66F0DAC0D1B67529075407D01DAACD80341FF6134664E56BF654D3F73E1581D
candidate SHA-256: 1834488A8E642BB12774DCD49803CDE599CBF889932AEA238A69AE71AA06537B
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:79754
original SHA-256: BF1E708987F561777AAAC5B74C4D936BF5B3AFFD24AFAB2513AD00BD1FB70C14
candidate SHA-256: BF1E708987F561777AAAC5B74C4D936BF5B3AFFD24AFAB2513AD00BD1FB70C14
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_006_counter_v1/reading_packets_v1/expanded_train_79754_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

