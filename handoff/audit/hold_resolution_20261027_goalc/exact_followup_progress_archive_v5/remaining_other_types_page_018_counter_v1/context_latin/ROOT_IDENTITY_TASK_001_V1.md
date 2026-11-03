# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:190049
original SHA-256: 380BA5FA50418E47722AB6DB85A4FE3EE3409775C90BB8DE34395240039DC1DE
candidate SHA-256: 380BA5FA50418E47722AB6DB85A4FE3EE3409775C90BB8DE34395240039DC1DE
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190049_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:190050
original SHA-256: 8592378D01DC209FDC7CEB2B4DDE75EFF614DDA742B690C9E0B096C19C4A0C27
candidate SHA-256: 4C70C60D5AD6884F0D71D45F8B5AB75AD457DF80427C8DEAB25D6D68CBEC0020
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:190159
original SHA-256: 577387C6EDB14C67C860EF04735968797139A6EAD6351FCD41B34FA14310EA26
candidate SHA-256: 577387C6EDB14C67C860EF04735968797139A6EAD6351FCD41B34FA14310EA26
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190159_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190159_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190159_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190159_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:190331
original SHA-256: 2E9CA73938215EECDBCFBEBFE77F14321749909D1CC8F1DDAF63424C14CDB41C
candidate SHA-256: 0E456966C4ECA811B1C5A6D8BF5A16C010CCDB2A7D80A4332B50B97F6AC4F62B
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:190388
original SHA-256: EDC2D262DB2C73B3BFDC001F7D6D069FE5F46A07DE3A472595DCBD2AA2CE30B9
candidate SHA-256: EDC2D262DB2C73B3BFDC001F7D6D069FE5F46A07DE3A472595DCBD2AA2CE30B9
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190388_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190388_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_018_counter_v1/reading_packets_v1/expanded_train_190388_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

