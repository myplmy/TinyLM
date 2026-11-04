# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:212532
original SHA-256: A5CE6D7E39F7EB8BE04CA490EB0CBA764A89CFDC7FE3D219735775BDC8ADD414
candidate SHA-256: 834B3569B26D729B1073F597878C8DA454FD666484769DAA6B2123B5FAC4DC2A
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:212842
original SHA-256: 23961C525660F8C10E7714DE53764F2217338B5ACB5EED4E2D9B4A6D6BD600A2
candidate SHA-256: 23961C525660F8C10E7714DE53764F2217338B5ACB5EED4E2D9B4A6D6BD600A2
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_011_counter_v1/reading_packets_v1/expanded_train_212842_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:213743
original SHA-256: 935D10AC6C5063029A70FE36739F877EFDA00537DD8F43A522DA0058D024CBC2
candidate SHA-256: 935D10AC6C5063029A70FE36739F877EFDA00537DD8F43A522DA0058D024CBC2
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_011_counter_v1/reading_packets_v1/expanded_train_213743_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_011_counter_v1/reading_packets_v1/expanded_train_213743_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_011_counter_v1/reading_packets_v1/expanded_train_213743_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_011_counter_v1/reading_packets_v1/expanded_train_213743_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_011_counter_v1/reading_packets_v1/expanded_train_213743_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:213847
original SHA-256: B20A3B031B23F93FEF6E4A090D23A26A16E37F811B44FBD8AB34124820F0786F
candidate SHA-256: B20A3B031B23F93FEF6E4A090D23A26A16E37F811B44FBD8AB34124820F0786F
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_011_counter_v1/reading_packets_v1/expanded_train_213847_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:214226
original SHA-256: D9F4D208E955A9E68E72ECC7D4A5DB6F70E93F0567060CE23F2F8E2115C84849
candidate SHA-256: 9735973B4CE6C113A4E6C666A39AA5A15C24DB6A6DAED5A3E1EB6BA4F634F454
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

