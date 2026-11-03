# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:48586
original SHA-256: 81DA9E46402BD7524E15E9D1817DB95F3409D3566F3F00604D95E3E042BAD82A
candidate SHA-256: 81DA9E46402BD7524E15E9D1817DB95F3409D3566F3F00604D95E3E042BAD82A
원문 frame 패킷: [1, 9]
최종 full_diff 패킷: [17, 17]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 17]
후보 중복만 있는 생략 가능 패킷: [10, 11, 12, 13, 14, 15, 16]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48586_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48586_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48586_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48586_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48586_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48586_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48586_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48586_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48586_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48586_0017.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:48592
original SHA-256: 3ACA4C7E582B340B9320C501F2826EE5A6007FB496ED34866C1E6D446883C847
candidate SHA-256: 3ACA4C7E582B340B9320C501F2826EE5A6007FB496ED34866C1E6D446883C847
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48592_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48592_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48592_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48592_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48592_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:48627
original SHA-256: FF8FFB5370298CF2BC9729387C0C73C05F0D12BF27EEBA25532D782B74DB25F4
candidate SHA-256: FF8FFB5370298CF2BC9729387C0C73C05F0D12BF27EEBA25532D782B74DB25F4
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48627_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48627_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48627_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:48881
original SHA-256: CA6B90FBC3C448464F4922EAF7423507D0AAB434803366C4C55E52A8F44B57B5
candidate SHA-256: 3715DF07CCD3DDA41EDBACCE08301F60F22959255632326592DFE00C8C0BAE51
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:48917
original SHA-256: 047466D82EF861048B9E55EDEBFF9E6D59B7CA51F10E1C11C44C6369DBD60665
candidate SHA-256: 8BBA6B43F6DE46AA9CCFA9022D3061B492F06468F5AC09E990B19BB87B4AB893
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

