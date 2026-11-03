# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1381573
original SHA-256: F682ABBD28E43587CA3FDD551510D210C2E2D0DD288F035FACC7A879A209FF49
candidate SHA-256: F682ABBD28E43587CA3FDD551510D210C2E2D0DD288F035FACC7A879A209FF49
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381573_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381573_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381573_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1381801
original SHA-256: 3A095FB06A224B1C90D87B6DA362B4425C2B76081871C37F1BB294D6DA0B2D97
candidate SHA-256: 3A095FB06A224B1C90D87B6DA362B4425C2B76081871C37F1BB294D6DA0B2D97
원문 frame 패킷: [1, 19]
최종 full_diff 패킷: [37, 37]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 37]
후보 중복만 있는 생략 가능 패킷: [20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381801_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381801_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381801_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381801_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381801_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381801_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381801_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381801_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381801_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381801_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381801_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381801_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381801_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381801_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381801_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381801_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381801_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381801_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381801_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381801_0037.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1381908
original SHA-256: C432EAB8AEE621B2E7EC78AC88DA322F283EB9A8F9FBBCCC56A049AFB0A8C7D3
candidate SHA-256: C432EAB8AEE621B2E7EC78AC88DA322F283EB9A8F9FBBCCC56A049AFB0A8C7D3
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381908_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381908_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381908_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1381908_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1382009
original SHA-256: 0A30377256AB6163A47C057BAD3145A2FDD190FDF253B1DAFBA52BAC0D61B503
candidate SHA-256: 0A30377256AB6163A47C057BAD3145A2FDD190FDF253B1DAFBA52BAC0D61B503
원문 frame 패킷: [1, 7]
최종 full_diff 패킷: [14, 14]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 14]
후보 중복만 있는 생략 가능 패킷: [8, 9, 10, 11, 12, 13]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382009_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382009_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382009_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382009_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382009_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382009_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382009_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382009_0014.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1382247
original SHA-256: C022DA96F6AC1BF81E892973B8BD13C54A425BF0888F006014FFFC72EFA1C726
candidate SHA-256: C022DA96F6AC1BF81E892973B8BD13C54A425BF0888F006014FFFC72EFA1C726
원문 frame 패킷: [1, 11]
최종 full_diff 패킷: [22, 22]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 22]
후보 중복만 있는 생략 가능 패킷: [12, 13, 14, 15, 16, 17, 18, 19, 20, 21]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382247_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382247_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382247_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382247_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382247_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382247_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382247_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382247_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382247_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382247_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382247_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_096_counter_v1/reading_packets_v1/expanded_train_1382247_0022.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

