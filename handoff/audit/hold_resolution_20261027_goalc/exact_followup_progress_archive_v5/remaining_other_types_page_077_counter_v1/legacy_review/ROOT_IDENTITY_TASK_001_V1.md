# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1060502
original SHA-256: 0ACA064521F150A9880FAB150AF9ED7B26168F665B457D9F6DDF3DF40DC81CBC
candidate SHA-256: 0ACA064521F150A9880FAB150AF9ED7B26168F665B457D9F6DDF3DF40DC81CBC
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060502_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060502_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1060966
original SHA-256: E9B61BF8E7FDFEC37522D5871FD183F161B98AFD316F5E65A90F281A5DF49597
candidate SHA-256: E9B61BF8E7FDFEC37522D5871FD183F161B98AFD316F5E65A90F281A5DF49597
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060966_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1060995
original SHA-256: 0826CA2FE07E7ADB86026F709525F95B2B8352752CC088A9D296A9A729340A6C
candidate SHA-256: 0826CA2FE07E7ADB86026F709525F95B2B8352752CC088A9D296A9A729340A6C
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1060995_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1061461
original SHA-256: 4E1E3E1612B6EBF6DE47A0F18C671D2304A5BB75F7B91B5B225E40BA44BF05AF
candidate SHA-256: 4E1E3E1612B6EBF6DE47A0F18C671D2304A5BB75F7B91B5B225E40BA44BF05AF
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [9, 9]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 9]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1061461_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1061461_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1061461_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1061461_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1061461_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1061461_0009.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1061578
original SHA-256: 7C432500B1604FA03CE9354220B346242E4C4E5C02CF2BA1AF34BE9DE30A82AA
candidate SHA-256: 7C432500B1604FA03CE9354220B346242E4C4E5C02CF2BA1AF34BE9DE30A82AA
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1061578_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1061578_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_077_counter_v1/reading_packets_v1/expanded_train_1061578_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

