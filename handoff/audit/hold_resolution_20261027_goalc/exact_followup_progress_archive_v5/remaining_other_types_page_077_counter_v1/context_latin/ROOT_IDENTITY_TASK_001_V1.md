# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1060732
original SHA-256: F63A0D6BC3535943625151B5EAB198001051EC968181363DF7D527298DB6D523
candidate SHA-256: F63A0D6BC3535943625151B5EAB198001051EC968181363DF7D527298DB6D523
원문 frame 패킷: [1, 19]
최종 full_diff 패킷: [37, 37]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 37]
후보 중복만 있는 생략 가능 패킷: [20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060732_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060732_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060732_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060732_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060732_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060732_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060732_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060732_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060732_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060732_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060732_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060732_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060732_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060732_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060732_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060732_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060732_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060732_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060732_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060732_0037.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1060877
original SHA-256: AE16D737F7809C0314BDFE86372B53853B27C60A84295AC2928A1D6956539A61
candidate SHA-256: AE16D737F7809C0314BDFE86372B53853B27C60A84295AC2928A1D6956539A61
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060877_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060877_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060877_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1061005
original SHA-256: ADEB11B73E4A9C89EBA76862BDD54A4E5BC79BAE18628798AFC38722CA9C5522
candidate SHA-256: ADEB11B73E4A9C89EBA76862BDD54A4E5BC79BAE18628798AFC38722CA9C5522
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [11, 11]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 11]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1061005_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1061005_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1061005_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1061005_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1061005_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1061005_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1061005_0011.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1061118
original SHA-256: C0209C7A7BDEFA40D8696F77A8F664B266522E524E7D5F07323AC31168BECE60
candidate SHA-256: C0209C7A7BDEFA40D8696F77A8F664B266522E524E7D5F07323AC31168BECE60
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1061118_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1061118_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1061737
original SHA-256: B39B6031C353534619CC1C06AE615AB63A26082D448B441A5C5060E0AA3C988E
candidate SHA-256: B39B6031C353534619CC1C06AE615AB63A26082D448B441A5C5060E0AA3C988E
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1061737_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

