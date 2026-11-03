# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1361390
original SHA-256: 5F2217815DBF3E6B02E13B887F132A0EB68E3F94386B8C4CC1C2516E029CB7C6
candidate SHA-256: 5F2217815DBF3E6B02E13B887F132A0EB68E3F94386B8C4CC1C2516E029CB7C6
원문 frame 패킷: [1, 15]
최종 full_diff 패킷: [30, 30]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 30]
후보 중복만 있는 생략 가능 패킷: [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361390_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361390_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361390_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361390_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361390_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361390_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361390_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361390_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361390_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361390_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361390_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361390_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361390_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361390_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361390_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361390_0030.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1361402
original SHA-256: 4E21B9E7B693F9D96A5A56A304589CB033AD89E2E11D5D7DA52098F78E785A89
candidate SHA-256: 4E21B9E7B693F9D96A5A56A304589CB033AD89E2E11D5D7DA52098F78E785A89
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361402_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361402_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361402_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361402_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361402_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1361827
original SHA-256: DDEA12F4E3A4A621B4794A7F4D94587C68AFBD2E4BA2CACF5B413EAE83F69DC7
candidate SHA-256: DDEA12F4E3A4A621B4794A7F4D94587C68AFBD2E4BA2CACF5B413EAE83F69DC7
원문 frame 패킷: [1, 11]
최종 full_diff 패킷: [22, 22]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 22]
후보 중복만 있는 생략 가능 패킷: [12, 13, 14, 15, 16, 17, 18, 19, 20, 21]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361827_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361827_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361827_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361827_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361827_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361827_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361827_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361827_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361827_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361827_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361827_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361827_0022.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1361913
original SHA-256: 64AB162292E18277A670246EB6E9B15D15BD15347F8620E5D8EFD183F8B278EB
candidate SHA-256: 64AB162292E18277A670246EB6E9B15D15BD15347F8620E5D8EFD183F8B278EB
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [11, 11]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 11]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361913_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361913_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361913_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361913_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361913_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361913_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1361913_0011.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1362010
original SHA-256: 5B21EC31925682EDB3B9725D1B9E7554735C5006AEE084DDBDF3AA8A94693966
candidate SHA-256: 5B21EC31925682EDB3B9725D1B9E7554735C5006AEE084DDBDF3AA8A94693966
원문 frame 패킷: [1, 7]
최종 full_diff 패킷: [14, 14]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 14]
후보 중복만 있는 생략 가능 패킷: [8, 9, 10, 11, 12, 13]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1362010_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1362010_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1362010_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1362010_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1362010_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1362010_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1362010_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_095_counter_v1/reading_packets_v1/expanded_train_1362010_0014.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

