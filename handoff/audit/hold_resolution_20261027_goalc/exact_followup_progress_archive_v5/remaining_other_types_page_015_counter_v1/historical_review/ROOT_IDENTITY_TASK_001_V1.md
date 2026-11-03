# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:148779
original SHA-256: FD87EE1C834B6F87062707BB3B5C7CE26AB868F55CD22FFFE26757642B878993
candidate SHA-256: FD87EE1C834B6F87062707BB3B5C7CE26AB868F55CD22FFFE26757642B878993
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_148779_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_148779_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_148779_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:148786
original SHA-256: 5A34B5B1AD92FA08E2AEEF5F20F978F1C989C9B3D81B975FA31894B82DFEF3ED
candidate SHA-256: 5A34B5B1AD92FA08E2AEEF5F20F978F1C989C9B3D81B975FA31894B82DFEF3ED
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_148786_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_148786_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_148786_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_148786_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_015_counter_v1/reading_packets_v1/expanded_train_148786_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:148800
original SHA-256: C5BB17AEAB02EC4045897AC7A94056AA31ADD6575955F8AB14C887284D0834AA
candidate SHA-256: 7AFABB382FF8639F98A910918A8878C14708B20CE47DA091FC876D844C6228A6
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:148830
original SHA-256: 5B5D16ABF76121FAD08CE4007EF5092B4CC6C025A145EF0F8AEB84E9A086915E
candidate SHA-256: 3A354153E9545369E885EAB973ED236FE698716F8FD6B6291502119EE3591B08
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:148862
original SHA-256: 1D647A0EAF11D13D6D912E247FA9BB644DD988C8D6E24BB9A254A0E44FA22152
candidate SHA-256: FF52B676A9C73A818DC81AF5F9CB9C94FA8B01A6D3FFC1217A9BA98099232C07
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

