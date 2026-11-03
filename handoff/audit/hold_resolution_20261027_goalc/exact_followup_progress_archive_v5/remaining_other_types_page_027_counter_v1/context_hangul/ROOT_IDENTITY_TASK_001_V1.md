# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:308619
original SHA-256: 113DC4D741A7098CA4E8B9CE234DAF26DC98FF8176E92A7CEFC1A2296C3A0EBA
candidate SHA-256: 2704F9F6DD6D7BECDA2C6FF4A62099B0AC64AB18C0FF0D68A82E6F397959236E
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:308659
original SHA-256: A2EAB0A01C5B3D175A6382EDBC2C020F46C7686A176ECA5575D9A62B294432A7
candidate SHA-256: A2EAB0A01C5B3D175A6382EDBC2C020F46C7686A176ECA5575D9A62B294432A7
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [9, 9]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 9]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_308659_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_308659_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_308659_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_308659_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_308659_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_308659_0009.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:308706
original SHA-256: C888C95FBF28F5805E6748E586399A4D58AE8DBF5FB6797EDBB4EEFA57E3EABA
candidate SHA-256: C888C95FBF28F5805E6748E586399A4D58AE8DBF5FB6797EDBB4EEFA57E3EABA
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_308706_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_027_counter_v1/reading_packets_v1/expanded_train_308706_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:308708
original SHA-256: 353FC4BDC2A2331D667BEF37AF841BA180A6C3A514928386DF79659EB1D6316E
candidate SHA-256: D274513F90E4E55E1A0E90653C5A4A40E1ECE335CC6261F31F5DB4CAF277972F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:308862
original SHA-256: 295614198DE919F25B16E0F657D2854EF4A7046F8DFA2FC8412A8E26638BB15B
candidate SHA-256: 7D0680DDF6B773470790D8FB520D1F1C97EFB9146E904AA010AC6DAADCCEF33B
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

