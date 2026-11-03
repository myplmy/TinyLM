# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:930231
original SHA-256: DDBCA321BDA185E7D09C940A09F5ECA42E37FB817896562E6A707D0F726569EB
candidate SHA-256: DDBCA321BDA185E7D09C940A09F5ECA42E37FB817896562E6A707D0F726569EB
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_070_counter_v1/reading_packets_v1/expanded_train_930231_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_070_counter_v1/reading_packets_v1/expanded_train_930231_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:930700
original SHA-256: E1A596CC74E9EDC89253493CED7B04B98293097600B7DB4DF55A6ED6DCCCA67B
candidate SHA-256: E1A596CC74E9EDC89253493CED7B04B98293097600B7DB4DF55A6ED6DCCCA67B
원문 frame 패킷: [1, 9]
최종 full_diff 패킷: [17, 17]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 17]
후보 중복만 있는 생략 가능 패킷: [10, 11, 12, 13, 14, 15, 16]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_070_counter_v1/reading_packets_v1/expanded_train_930700_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_070_counter_v1/reading_packets_v1/expanded_train_930700_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_070_counter_v1/reading_packets_v1/expanded_train_930700_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_070_counter_v1/reading_packets_v1/expanded_train_930700_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_070_counter_v1/reading_packets_v1/expanded_train_930700_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_070_counter_v1/reading_packets_v1/expanded_train_930700_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_070_counter_v1/reading_packets_v1/expanded_train_930700_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_070_counter_v1/reading_packets_v1/expanded_train_930700_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_070_counter_v1/reading_packets_v1/expanded_train_930700_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_070_counter_v1/reading_packets_v1/expanded_train_930700_0017.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:930871
original SHA-256: 349F66A00D337F1512028A6015FE39423E4EB2CF23CB9121F00F2E58AB682167
candidate SHA-256: 5F50307B05C8C2509E1927A988BA6EC89F8722144D6EB08F12E7C9339FA5F5BA
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:931067
original SHA-256: CD9AD9B6D5C186C1136683569CCB7EC15FE86BF49886F34AE5C18E6F30073D3C
candidate SHA-256: 11FE3EA660B12843C37161CE7C1DE74ED8F0387E3AC35D10F72F24FBFFEADCEC
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:931124
original SHA-256: E55ECCAB0D76AA8F720BC10322E9E774C4F05C833B2F4D05345A5EDA4464EC6D
candidate SHA-256: 14DB16B2DC48B66732E415B3C4072A1087BCC360C4690CB179A9214754CE8876
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

