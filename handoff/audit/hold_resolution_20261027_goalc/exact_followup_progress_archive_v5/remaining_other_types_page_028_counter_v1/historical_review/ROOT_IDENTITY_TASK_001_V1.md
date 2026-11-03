# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:320464
original SHA-256: 1E34CB2221D9A8DB6A096E4669AE30F48F103608DB84C9F4D4411E01C0DBD8E4
candidate SHA-256: E202D5E8CF39AF35492073A04A514061929CD5EF553E61FDB010AE00F9A1AEA5
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:320551
original SHA-256: A9A4F2BD14785C1DF6607C65B48A1C266DA15A8BCE188E9CB7168A1BE6A58694
candidate SHA-256: F9C7977D0C6CCC9C6820706363B1855190BAE935A3864CA4D982B19B92E8BCD0
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:320615
original SHA-256: 6C1433BDA635ECB8DAD4565A5B24C4A3FCC57CAA31BA96CB82CF54C08652C0C7
candidate SHA-256: 6C1433BDA635ECB8DAD4565A5B24C4A3FCC57CAA31BA96CB82CF54C08652C0C7
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_028_counter_v1/reading_packets_v1/expanded_train_320615_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_028_counter_v1/reading_packets_v1/expanded_train_320615_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_028_counter_v1/reading_packets_v1/expanded_train_320615_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:320644
original SHA-256: 24AB0D2449A569D6BADCBA5CB554CA2D3EADACD28DCB390A7B1C01CEBCE1385D
candidate SHA-256: 24AB0D2449A569D6BADCBA5CB554CA2D3EADACD28DCB390A7B1C01CEBCE1385D
원문 frame 패킷: [1, 16]
최종 full_diff 패킷: [31, 31]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 31]
후보 중복만 있는 생략 가능 패킷: [17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_028_counter_v1/reading_packets_v1/expanded_train_320644_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_028_counter_v1/reading_packets_v1/expanded_train_320644_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_028_counter_v1/reading_packets_v1/expanded_train_320644_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_028_counter_v1/reading_packets_v1/expanded_train_320644_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_028_counter_v1/reading_packets_v1/expanded_train_320644_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_028_counter_v1/reading_packets_v1/expanded_train_320644_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_028_counter_v1/reading_packets_v1/expanded_train_320644_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_028_counter_v1/reading_packets_v1/expanded_train_320644_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_028_counter_v1/reading_packets_v1/expanded_train_320644_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_028_counter_v1/reading_packets_v1/expanded_train_320644_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_028_counter_v1/reading_packets_v1/expanded_train_320644_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_028_counter_v1/reading_packets_v1/expanded_train_320644_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_028_counter_v1/reading_packets_v1/expanded_train_320644_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_028_counter_v1/reading_packets_v1/expanded_train_320644_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_028_counter_v1/reading_packets_v1/expanded_train_320644_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_028_counter_v1/reading_packets_v1/expanded_train_320644_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_028_counter_v1/reading_packets_v1/expanded_train_320644_0031.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:320654
original SHA-256: B5F24EE543AC967ABA176388BD0ADBDCD76865207151276C04594D96ACF0248C
candidate SHA-256: B5F24EE543AC967ABA176388BD0ADBDCD76865207151276C04594D96ACF0248C
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_028_counter_v1/reading_packets_v1/expanded_train_320654_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_028_counter_v1/reading_packets_v1/expanded_train_320654_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

