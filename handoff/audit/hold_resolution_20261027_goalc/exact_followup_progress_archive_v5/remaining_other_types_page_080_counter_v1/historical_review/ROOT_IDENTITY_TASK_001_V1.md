# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1101648
original SHA-256: FA8806FD9FBDD67C4BE3D54C59A330794FA7C650706DF45C9FF89962055842D5
candidate SHA-256: FA8806FD9FBDD67C4BE3D54C59A330794FA7C650706DF45C9FF89962055842D5
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101648_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101648_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1101783
original SHA-256: D982855EA9C27DC75DC4D0BD4E9078C0B3490FA48654871B4E2E17E7C4E9BD36
candidate SHA-256: D982855EA9C27DC75DC4D0BD4E9078C0B3490FA48654871B4E2E17E7C4E9BD36
원문 frame 패킷: [1, 34]
최종 full_diff 패킷: [68, 68]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 68]
후보 중복만 있는 생략 가능 패킷: [35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101783_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101783_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101783_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101783_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101783_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101783_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101783_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101783_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101783_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101783_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101783_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101783_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101783_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101783_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101783_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101783_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101783_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101783_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101783_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101783_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101783_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101783_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101783_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101783_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101783_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101783_0026.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101783_0027.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101783_0028.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101783_0029.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101783_0030.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101783_0031.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101783_0032.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101783_0033.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101783_0034.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1101783_0068.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1102369
original SHA-256: 82AF23D9AF94BF7AE2516C20F2253A20C9543A4E9A878F06796CE8C4381436A6
candidate SHA-256: 3CBA70C603825A3BA2AB3CFF5890C2D78A7EB76659ED47A75E6D9FD81A862543
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1102610
original SHA-256: CE90FBC844C1F753FE1747C072B5D9267F238505EF21DD79F77D3900238E5319
candidate SHA-256: F74B687C0C068FFA382379D908490646AF766858987AE31A278C15001A71F7F8
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1102809
original SHA-256: 1EF0FD06A711B72C4F4D05F088DF03AF8AF614C7639B17067E9CE793A3921B05
candidate SHA-256: 1EF0FD06A711B72C4F4D05F088DF03AF8AF614C7639B17067E9CE793A3921B05
원문 frame 패킷: [1, 11]
최종 full_diff 패킷: [21, 22]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 21, 22]
후보 중복만 있는 생략 가능 패킷: [12, 13, 14, 15, 16, 17, 18, 19, 20]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102809_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102809_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102809_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102809_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102809_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102809_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102809_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102809_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102809_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102809_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102809_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102809_0021.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_080_counter_v1/reading_packets_v1/expanded_train_1102809_0022.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

