# 정확 입력 전문 판독 연결 TASK_016

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:258694
original SHA-256: 6443C3B55FD78AE9D1B38CD76F8EB7D7195D7E191F12DE060B5F6B13256F1D5F
candidate SHA-256: B434B3927317E9DC416250C23C28E04719798F50FCE226E4093DAB3A616929EC
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:259423
original SHA-256: D1196F3D259DFB6BA0AC01DFE23C81A034B60A2854C435FE43C620447E6DD329
candidate SHA-256: 7259A5192A7E4C7E9BD8C4E9B74D4A8B11003F3A479AA6D2C49868B786140A1E
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:259663
original SHA-256: 6F57BA517947D3DE5BD90C8E029619FB114B9FAF19503010688C825BA65940AB
candidate SHA-256: 6F57BA517947D3DE5BD90C8E029619FB114B9FAF19503010688C825BA65940AB
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_012_counter_v1/reading_packets_v1/expanded_train_259663_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_012_counter_v1/reading_packets_v1/expanded_train_259663_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:259951
original SHA-256: FC6584676B0E9F8048F63F09594C26C5ADDC4A98D020879742BCDF7582834F9F
candidate SHA-256: C8D29B6A17293135492C9E3149AEA0CCCF2FB2B14198E1D12D04411734BC0411
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:260041
original SHA-256: B8EEBC04383357E67C9B96CFC70AC0D4D8C18FFD41EE5B7C3BF4B3A8EB33FC40
candidate SHA-256: B8EEBC04383357E67C9B96CFC70AC0D4D8C18FFD41EE5B7C3BF4B3A8EB33FC40
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_012_counter_v1/reading_packets_v1/expanded_train_260041_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

