# 정확 입력 전문 판독 연결 TASK_009

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:110283
original SHA-256: 0B2ED109CA4B78628359B5BEB38BD92E7C84B9A66440F0715B0CA0C44A3B2357
candidate SHA-256: 0B2ED109CA4B78628359B5BEB38BD92E7C84B9A66440F0715B0CA0C44A3B2357
원문 frame 패킷: [1, 37]
최종 full_diff 패킷: [73, 73]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 73]
후보 중복만 있는 생략 가능 패킷: [38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110283_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110283_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110283_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110283_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110283_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110283_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110283_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110283_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110283_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110283_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110283_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110283_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110283_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110283_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110283_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110283_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110283_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110283_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110283_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110283_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110283_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110283_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110283_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110283_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110283_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110283_0026.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110283_0027.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110283_0028.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110283_0029.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110283_0030.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110283_0031.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110283_0032.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110283_0033.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110283_0034.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110283_0035.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110283_0036.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110283_0037.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110283_0073.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:110301
original SHA-256: 45C4E8227F5C36E16ACEB96EA4D772BBE87967CFD821495F8D9533236D4AE4BF
candidate SHA-256: FED8A4C6B51A4FCF694070DB1244E966139554D4451423C7209FA54492957B45
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:110394
original SHA-256: C1FB6B5C46FEDD373265CDF9BDF7EA0411248A300B44300DF9567C346C30DE63
candidate SHA-256: C1FB6B5C46FEDD373265CDF9BDF7EA0411248A300B44300DF9567C346C30DE63
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110394_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110394_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110394_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_110394_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:110627
original SHA-256: 57136598F98BB27489E4C5430707F47854E87C5318888BE8FDF08A7013A31864
candidate SHA-256: 9A28EF16EBAAF069106A2748F9BE71CC0758D2EEEA699227F2ADC39C0C64B65F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:110697
original SHA-256: 59EC770D113ADA0165ADEB90D708E8ACDEFD2838C8EF3924DF9188C29E661B06
candidate SHA-256: 762CA51B89CF35E6E2D5F48AB8374B1F766CA4113D5BA8BA140D51A63738A5BE
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

