# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:84693
original SHA-256: B9F895C166E458348D08E1D71B456F270A1CFD6552F7775F8303BE1FB313DEBE
candidate SHA-256: 31092CF74F2250619BE4553B7C886847C6C7BE816735B64908D7537CEF673150
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:84713
original SHA-256: 0B026385AE27073F8A3CAB7C7506B7A13263A44D9CA35690E06D4A1E6C78730B
candidate SHA-256: D03645B002CBC49ED78530CC8FE2CC9ADE80D76804DFED6672F85996C233823D
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:84746
original SHA-256: C131B38F0534B3ABEEC4A12CF62FEAE0FDEA268F826354A0433E614660CB45C0
candidate SHA-256: C131B38F0534B3ABEEC4A12CF62FEAE0FDEA268F826354A0433E614660CB45C0
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_009_counter_v1/reading_packets_v1/expanded_train_84746_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_009_counter_v1/reading_packets_v1/expanded_train_84746_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_009_counter_v1/reading_packets_v1/expanded_train_84746_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_009_counter_v1/reading_packets_v1/expanded_train_84746_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:84831
original SHA-256: 3B3AB5FFDD9C196B1D4C28CB9F05FC0932BD6F8D49E214BF99DC43CF39BB2FCF
candidate SHA-256: 3B3AB5FFDD9C196B1D4C28CB9F05FC0932BD6F8D49E214BF99DC43CF39BB2FCF
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_009_counter_v1/reading_packets_v1/expanded_train_84831_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:84899
original SHA-256: 338FBAEB966A02B44228BE35C92154D5A755929BE6E26C687821B9777BD32F56
candidate SHA-256: 338FBAEB966A02B44228BE35C92154D5A755929BE6E26C687821B9777BD32F56
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [9, 9]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 9]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_009_counter_v1/reading_packets_v1/expanded_train_84899_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_009_counter_v1/reading_packets_v1/expanded_train_84899_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_009_counter_v1/reading_packets_v1/expanded_train_84899_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_009_counter_v1/reading_packets_v1/expanded_train_84899_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_009_counter_v1/reading_packets_v1/expanded_train_84899_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_009_counter_v1/reading_packets_v1/expanded_train_84899_0009.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

