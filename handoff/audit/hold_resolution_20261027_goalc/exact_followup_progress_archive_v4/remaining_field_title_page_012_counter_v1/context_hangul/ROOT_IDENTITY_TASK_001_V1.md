# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:241075
original SHA-256: 69038E93777355E308430F6FE00968A5898785667E417D7E7DBB66A36E0704FD
candidate SHA-256: 632FFCF7DE89391DB6EE74F90FAFD032AD2F5C1ECC091A3546C1336EB9EAFA3C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:241324
original SHA-256: CA988FD7F37F2EBCCD3B8D125EB8C883122266F20C484050980ABA3A9E13B1F9
candidate SHA-256: CA988FD7F37F2EBCCD3B8D125EB8C883122266F20C484050980ABA3A9E13B1F9
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_012_counter_v1/reading_packets_v1/expanded_train_241324_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:241516
original SHA-256: DC2F884035EFF078C030DF9A8EA5E4CF32568D6F20EFC662E84A8619A3B3E3F2
candidate SHA-256: DC2F884035EFF078C030DF9A8EA5E4CF32568D6F20EFC662E84A8619A3B3E3F2
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_012_counter_v1/reading_packets_v1/expanded_train_241516_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:241791
original SHA-256: 8C4410F828011EE5E49AD82A7E23F1CD595AC91B70BDCEFF1180EBD68B9C17EC
candidate SHA-256: 8C4410F828011EE5E49AD82A7E23F1CD595AC91B70BDCEFF1180EBD68B9C17EC
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_012_counter_v1/reading_packets_v1/expanded_train_241791_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:241857
original SHA-256: 0FA10EBDC43006C3661DB5035F7EE20FA060364E8A2A9D167D85EA589F8FE595
candidate SHA-256: B3BD2097BBAB1868A467D6DFCC968C0E36499460B44AAAE48575D62807CE7C73
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

