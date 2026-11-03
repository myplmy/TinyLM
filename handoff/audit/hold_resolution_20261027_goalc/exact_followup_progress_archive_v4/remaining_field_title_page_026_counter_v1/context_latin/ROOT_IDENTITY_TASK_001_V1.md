# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:830139
original SHA-256: 64CAC2457CD9D17D9D9E8710CAA5B239DAFD13716392EF83EED2B8C4DE282B38
candidate SHA-256: 64CAC2457CD9D17D9D9E8710CAA5B239DAFD13716392EF83EED2B8C4DE282B38
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_830139_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:830485
original SHA-256: CABB1EC2CEE38E372C37909AD3C29AEA77D0CADB26A6181A39589FC2FDAE1942
candidate SHA-256: 84BF63D4C638A6E86DA4FF1425FE0EB6F7CF2EC0B22A07CA289CB4B8A093FB38
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:830919
original SHA-256: D3DFC2CDEC19E5EB5567F4DB26A7921F79D6ECCE3EB74CEF5460869A1451F41F
candidate SHA-256: D3DFC2CDEC19E5EB5567F4DB26A7921F79D6ECCE3EB74CEF5460869A1451F41F
원문 frame 패킷: [1, 12]
최종 full_diff 패킷: [24, 24]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 24]
후보 중복만 있는 생략 가능 패킷: [13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_830919_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_830919_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_830919_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_830919_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_830919_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_830919_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_830919_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_830919_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_830919_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_830919_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_830919_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_830919_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_830919_0024.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:830990
original SHA-256: BCDA04F7FB072A6B8B14BBA5DBF31A985AA532C93345BF54CD14CAB68146B562
candidate SHA-256: BCDA04F7FB072A6B8B14BBA5DBF31A985AA532C93345BF54CD14CAB68146B562
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_830990_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_830990_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_830990_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:831145
original SHA-256: 74834D55674F3814E71C2483BBF509A2D24748CAF2EEAF2D798C5368153CF820
candidate SHA-256: 74834D55674F3814E71C2483BBF509A2D24748CAF2EEAF2D798C5368153CF820
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_026_counter_v1/reading_packets_v1/expanded_train_831145_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

