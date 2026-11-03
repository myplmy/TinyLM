# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1183507
original SHA-256: 59B415B156630CFB983A8558B04E1E718706F35213A5D72662602F5AC848F2F3
candidate SHA-256: 3BC4E1ADF751F0FBE4429C9F56FB171237E5010BC8EA34BC1B9F402F092E1CF2
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1183711
original SHA-256: DC99ED47F5B371160AD5BF526F118E6CC0BEB8F0E6CD1D778FA0C0E548DC45D3
candidate SHA-256: DC99ED47F5B371160AD5BF526F118E6CC0BEB8F0E6CD1D778FA0C0E548DC45D3
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_085_counter_v1/reading_packets_v1/expanded_train_1183711_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1183765
original SHA-256: D44EBA84CA2297FFC441D6A5E1655C5D6355DAD399BE92C2EDD7A15ACBF1BA3D
candidate SHA-256: D44EBA84CA2297FFC441D6A5E1655C5D6355DAD399BE92C2EDD7A15ACBF1BA3D
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_085_counter_v1/reading_packets_v1/expanded_train_1183765_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_085_counter_v1/reading_packets_v1/expanded_train_1183765_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_085_counter_v1/reading_packets_v1/expanded_train_1183765_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1183889
original SHA-256: 58360FEEC9AA377C63BEDDD3D9EE2DF84CBC018FF5F9BE53DFD101E2C7CA4FAD
candidate SHA-256: 58360FEEC9AA377C63BEDDD3D9EE2DF84CBC018FF5F9BE53DFD101E2C7CA4FAD
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_085_counter_v1/reading_packets_v1/expanded_train_1183889_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_085_counter_v1/reading_packets_v1/expanded_train_1183889_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_085_counter_v1/reading_packets_v1/expanded_train_1183889_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_085_counter_v1/reading_packets_v1/expanded_train_1183889_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_085_counter_v1/reading_packets_v1/expanded_train_1183889_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1184851
original SHA-256: C782F29E9A8A7C9A3FB1B922582B03B9F43966F7290FE01AFDC5ACAAE903FEA5
candidate SHA-256: C782F29E9A8A7C9A3FB1B922582B03B9F43966F7290FE01AFDC5ACAAE903FEA5
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_085_counter_v1/reading_packets_v1/expanded_train_1184851_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

