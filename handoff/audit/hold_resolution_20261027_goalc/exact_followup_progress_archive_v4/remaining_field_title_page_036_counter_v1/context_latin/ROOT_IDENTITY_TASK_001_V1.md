# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1307853
original SHA-256: 93FEFE9AA1856AD7E4C51FB0452BB662F9508A738F500E9D8F8C76791DAF68F9
candidate SHA-256: 93FEFE9AA1856AD7E4C51FB0452BB662F9508A738F500E9D8F8C76791DAF68F9
원문 frame 패킷: [1, 12]
최종 full_diff 패킷: [24, 24]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 24]
후보 중복만 있는 생략 가능 패킷: [13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1307853_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1307853_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1307853_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1307853_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1307853_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1307853_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1307853_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1307853_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1307853_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1307853_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1307853_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1307853_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1307853_0024.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1309633
original SHA-256: D63F5A8C59035A27A6AABAA31A16A0F13C96FDBC5505731275E4C8702D164EBF
candidate SHA-256: D63F5A8C59035A27A6AABAA31A16A0F13C96FDBC5505731275E4C8702D164EBF
원문 frame 패킷: [1, 10]
최종 full_diff 패킷: [20, 20]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20]
후보 중복만 있는 생략 가능 패킷: [11, 12, 13, 14, 15, 16, 17, 18, 19]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1309633_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1309633_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1309633_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1309633_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1309633_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1309633_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1309633_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1309633_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1309633_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1309633_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1309633_0020.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1309851
original SHA-256: FE904B3BD6B3F8348E73A8D320D97A1DC1D94DDB1EA72E91B8880777034808B5
candidate SHA-256: FE904B3BD6B3F8348E73A8D320D97A1DC1D94DDB1EA72E91B8880777034808B5
원문 frame 패킷: [1, 24]
최종 full_diff 패킷: [47, 47]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 47]
후보 중복만 있는 생략 가능 패킷: [25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1309851_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1309851_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1309851_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1309851_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1309851_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1309851_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1309851_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1309851_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1309851_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1309851_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1309851_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1309851_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1309851_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1309851_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1309851_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1309851_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1309851_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1309851_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1309851_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1309851_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1309851_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1309851_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1309851_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1309851_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1309851_0047.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1321002
original SHA-256: 2B8003682C28A0BA3675113F4B298CD6584355CEDD55016B806BE8B27B767EB9
candidate SHA-256: 2B8003682C28A0BA3675113F4B298CD6584355CEDD55016B806BE8B27B767EB9
원문 frame 패킷: [1, 13]
최종 full_diff 패킷: [25, 25]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 25]
후보 중복만 있는 생략 가능 패킷: [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1321002_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1321002_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1321002_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1321002_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1321002_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1321002_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1321002_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1321002_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1321002_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1321002_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1321002_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1321002_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1321002_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1321002_0025.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1326316
original SHA-256: 109E72CD51531AFDEE9A49D343DE6C4E7F0448CF3859CFC4C4A4B3CBAFF204C4
candidate SHA-256: 109E72CD51531AFDEE9A49D343DE6C4E7F0448CF3859CFC4C4A4B3CBAFF204C4
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [9, 9]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 9]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1326316_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1326316_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1326316_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1326316_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1326316_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_036_counter_v1/reading_packets_v1/expanded_train_1326316_0009.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

