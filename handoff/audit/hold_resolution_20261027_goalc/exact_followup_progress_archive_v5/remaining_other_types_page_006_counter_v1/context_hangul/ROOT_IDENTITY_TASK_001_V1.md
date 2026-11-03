# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:59684
original SHA-256: C6DCBBA2097E4B0779CC1306BE216D061D98A09D14793E913CE9FC3ABBFBB3D8
candidate SHA-256: C6DCBBA2097E4B0779CC1306BE216D061D98A09D14793E913CE9FC3ABBFBB3D8
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_59684_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_59684_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:59849
original SHA-256: 585BDEB0808ABC7ACAC3CBEA799D95F38AE527AE7720047C2809138CAE2650CE
candidate SHA-256: D30ACB25F1A4BD81090FCA30C81BCA5BBAD607F44B4007765C0BB5D34D70A5F1
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:60063
original SHA-256: 4C54C2CC8A15A4A4B5BB4879DF88137F33524817A22F371F13A0BDD52647552D
candidate SHA-256: A3B64D1884F4AD489F8A5E50B9678970F23CBAA0A59547D4B05891A1FAFACBB0
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:60135
original SHA-256: 68D09CCDCFCAC3074108604A53398FCA1015A2FDE4F7EC4E52B3983579E71B08
candidate SHA-256: 68D09CCDCFCAC3074108604A53398FCA1015A2FDE4F7EC4E52B3983579E71B08
원문 frame 패킷: [1, 49]
최종 full_diff 패킷: [97, 98]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 97, 98]
후보 중복만 있는 생략 가능 패킷: [50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0026.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0027.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0028.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0029.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0030.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0031.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0032.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0033.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0034.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0035.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0036.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0037.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0038.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0039.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0040.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0041.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0042.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0043.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0044.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0045.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0046.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0047.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0048.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0049.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0097.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_006_counter_v1/reading_packets_v1/expanded_train_60135_0098.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:60147
original SHA-256: E83E1A80F5170F3291FD370DA2A2AFFC345A6EB90A820A6937D16DCFDB27D970
candidate SHA-256: C9516AA8D859C8F437BA41C9D9492C31B8A0DE4DC3B15A808E4C5574463AAD40
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

