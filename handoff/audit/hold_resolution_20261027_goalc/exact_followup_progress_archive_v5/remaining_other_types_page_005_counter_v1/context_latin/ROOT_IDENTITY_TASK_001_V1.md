# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:48578
original SHA-256: 4B6D76840EF99B778FD68C5D86836750745D639F12519C9E86D72D51E7471DDD
candidate SHA-256: E9E291B0C4BC01F1AAFDFA0C3CF3D19EEC8E9371A8A066A932570E17A528EC5B
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:48605
original SHA-256: 9CD19FD85DFF98BA9670C802248289FF9F186E5FB453FA4F413BF514FD5586D7
candidate SHA-256: 9CD19FD85DFF98BA9670C802248289FF9F186E5FB453FA4F413BF514FD5586D7
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48605_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48605_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:48648
original SHA-256: 89C322A6B33D61F97469C9CBBD5B3EECCA995F5070CE402337F107125CA41FCA
candidate SHA-256: 89C322A6B33D61F97469C9CBBD5B3EECCA995F5070CE402337F107125CA41FCA
원문 frame 패킷: [1, 7]
최종 full_diff 패킷: [13, 13]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 13]
후보 중복만 있는 생략 가능 패킷: [8, 9, 10, 11, 12]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48648_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48648_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48648_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48648_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48648_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48648_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48648_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48648_0013.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:48664
original SHA-256: 9D3864F18C494D0E113CBD384995398181205F5B78740C395EE4637F58898FF4
candidate SHA-256: 9D3864F18C494D0E113CBD384995398181205F5B78740C395EE4637F58898FF4
원문 frame 패킷: [1, 10]
최종 full_diff 패킷: [19, 19]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 19]
후보 중복만 있는 생략 가능 패킷: [11, 12, 13, 14, 15, 16, 17, 18]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48664_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48664_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48664_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48664_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48664_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48664_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48664_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48664_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48664_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48664_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48664_0019.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:48684
original SHA-256: 67F82FA86301F49E140C286898E8CAE9E6A7C79385644FBBF0B14A0E7E065EEA
candidate SHA-256: 67F82FA86301F49E140C286898E8CAE9E6A7C79385644FBBF0B14A0E7E065EEA
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48684_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48684_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_005_counter_v1/reading_packets_v1/expanded_train_48684_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

