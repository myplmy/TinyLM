# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:501749
original SHA-256: B4D78A76421FDD35FD158478B97602B38220A7F4C627C4E637763FAA5E9C9E3B
candidate SHA-256: B4D78A76421FDD35FD158478B97602B38220A7F4C627C4E637763FAA5E9C9E3B
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_041_counter_v1/reading_packets_v1/expanded_train_501749_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_041_counter_v1/reading_packets_v1/expanded_train_501749_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_041_counter_v1/reading_packets_v1/expanded_train_501749_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:501753
original SHA-256: 91A076B51C86EF101C6997EC216C6AF4BBB237E4055F4378D0B6C79C086FC18D
candidate SHA-256: 91A076B51C86EF101C6997EC216C6AF4BBB237E4055F4378D0B6C79C086FC18D
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_041_counter_v1/reading_packets_v1/expanded_train_501753_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_041_counter_v1/reading_packets_v1/expanded_train_501753_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_041_counter_v1/reading_packets_v1/expanded_train_501753_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_041_counter_v1/reading_packets_v1/expanded_train_501753_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_041_counter_v1/reading_packets_v1/expanded_train_501753_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:501938
original SHA-256: D394845302344CD97A07545359EB811F679A22C171EFEA96DDD0347857A12181
candidate SHA-256: 34D1349A75451F6E7A9D2A3B683A48DD57264315E6A681909377F153A02D5D2F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:501957
original SHA-256: 5D204C56FACACF0BEC113E18B609EB1CF8DD9053D1F0F9A0D0949E8F8D8ECE61
candidate SHA-256: 5D204C56FACACF0BEC113E18B609EB1CF8DD9053D1F0F9A0D0949E8F8D8ECE61
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_041_counter_v1/reading_packets_v1/expanded_train_501957_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_041_counter_v1/reading_packets_v1/expanded_train_501957_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_041_counter_v1/reading_packets_v1/expanded_train_501957_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_041_counter_v1/reading_packets_v1/expanded_train_501957_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:502137
original SHA-256: 2BA53E9F6D9FFC31BED7998D7722B9B9FEFAAD5D3C0D01E58682E3F6E365215F
candidate SHA-256: 2BA53E9F6D9FFC31BED7998D7722B9B9FEFAAD5D3C0D01E58682E3F6E365215F
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_041_counter_v1/reading_packets_v1/expanded_train_502137_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

