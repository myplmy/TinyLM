# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1322754
original SHA-256: 676BF9C74DB9DDFE25A8CAAC9A2F84A87991B1FD7134EACC0A1B6FD6B1166025
candidate SHA-256: 676BF9C74DB9DDFE25A8CAAC9A2F84A87991B1FD7134EACC0A1B6FD6B1166025
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [11, 11]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 11]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322754_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322754_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322754_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322754_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322754_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322754_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322754_0011.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1322788
original SHA-256: F2D3EC1EF8B1D8767235C505E17A9703A06EAA4F20AE64A499189239C42AF081
candidate SHA-256: F2D3EC1EF8B1D8767235C505E17A9703A06EAA4F20AE64A499189239C42AF081
원문 frame 패킷: [1, 24]
최종 full_diff 패킷: [48, 48]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 48]
후보 중복만 있는 생략 가능 패킷: [25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322788_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322788_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322788_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322788_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322788_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322788_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322788_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322788_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322788_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322788_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322788_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322788_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322788_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322788_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322788_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322788_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322788_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322788_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322788_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322788_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322788_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322788_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322788_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322788_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322788_0048.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1322791
original SHA-256: 8D06795FDF00FDC0095866A3244538C7B46E2A8AA89BF3ABC8936F3E4588ED54
candidate SHA-256: 8D06795FDF00FDC0095866A3244538C7B46E2A8AA89BF3ABC8936F3E4588ED54
원문 frame 패킷: [1, 10]
최종 full_diff 패킷: [19, 19]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 19]
후보 중복만 있는 생략 가능 패킷: [11, 12, 13, 14, 15, 16, 17, 18]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322791_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322791_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322791_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322791_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322791_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322791_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322791_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322791_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322791_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322791_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322791_0019.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1322904
original SHA-256: A8DAE486617C1576C3ED8EC079BFEFEE54A7B44EC5DCC8ED1980BAFA3DC5E94F
candidate SHA-256: A8DAE486617C1576C3ED8EC079BFEFEE54A7B44EC5DCC8ED1980BAFA3DC5E94F
원문 frame 패킷: [1, 12]
최종 full_diff 패킷: [24, 24]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 24]
후보 중복만 있는 생략 가능 패킷: [13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322904_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322904_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322904_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322904_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322904_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322904_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322904_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322904_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322904_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322904_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322904_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322904_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1322904_0024.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1323518
original SHA-256: 199605DE7971B0CA567E1DB81AE209721D49035E62D32FD6E867027861B2DDBA
candidate SHA-256: 199605DE7971B0CA567E1DB81AE209721D49035E62D32FD6E867027861B2DDBA
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1323518_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1323518_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_093_counter_v1/reading_packets_v1/expanded_train_1323518_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

