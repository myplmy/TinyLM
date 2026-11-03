# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:828566
original SHA-256: 166CF67A9082C4A829E175F048512468AAA33BEEF1FE957EAE2FCB532E6E04C7
candidate SHA-256: 166CF67A9082C4A829E175F048512468AAA33BEEF1FE957EAE2FCB532E6E04C7
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [9, 9]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 9]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828566_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828566_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828566_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828566_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828566_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828566_0009.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:828611
original SHA-256: 33275A6CDECE68E159FEDE05F42F0E23ED20547A6E30917B391A5B73FD4DA8E2
candidate SHA-256: 311A3DA28230E0F96D8E2E0F59CA6E6E49BA48BC3A34272A1E2B08DAB3D04C62
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:828683
original SHA-256: 48D9EF2CE4C4F043BAF1F96C19C93D805D44E5F5B92482011FCCD37F1A7C40D3
candidate SHA-256: 2E457CEB12D49B61442D3FD7F213134A4E0365C3861AABF0B7DBD4AAED2625CA
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:828874
original SHA-256: C91EAE9F945C1FF4922AE3461FE94BB1E4CA2B1B9F4D9F84D8F17A163397338E
candidate SHA-256: C91EAE9F945C1FF4922AE3461FE94BB1E4CA2B1B9F4D9F84D8F17A163397338E
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828874_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_064_counter_v1/reading_packets_v1/expanded_train_828874_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:828884
original SHA-256: 92A1CD3A097EE6C128274312A00B89566BF218AC04633854638653A2B4BBDE07
candidate SHA-256: 01CB4BCE966542FC991241FACA81D4F1E69C34F636C9376F09279051D2C401E3
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

