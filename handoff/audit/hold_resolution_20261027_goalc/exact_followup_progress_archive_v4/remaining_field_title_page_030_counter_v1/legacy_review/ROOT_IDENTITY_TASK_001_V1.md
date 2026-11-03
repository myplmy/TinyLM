# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1042217
original SHA-256: A09E99A91F7DD0F3922013E7C61F0F3F36EFE661434B0B9FE4C732BF1BD91D60
candidate SHA-256: 5354FDDA020555606802A63BB1488BBB2990482749A38C9BBBEC37A530D08EEE
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1042311
original SHA-256: 4CD98DFE9D56D9F769E61EFE60323A081E39BB244E1003C0D7C2B8DC3E027312
candidate SHA-256: 912A4DAE1D46AE7EE9D94C56F4038C19FD7205931BFB0C28577BE18C7091C856
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1042781
original SHA-256: 4AFDE40950B6ED4333911CF6BF8D91501E182C0C2612BB8F639EB5DEBCF15897
candidate SHA-256: 34CA4CB8EE8BD55454D3E4FC40DACC7CE1260A7215AF323435B88E3588D2C7BF
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1043334
original SHA-256: A068EEB20E58D6903402C05E6A4C2FC0B5C183C84D5835F57F3E48432B43F5B7
candidate SHA-256: A068EEB20E58D6903402C05E6A4C2FC0B5C183C84D5835F57F3E48432B43F5B7
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_030_counter_v1/reading_packets_v1/expanded_train_1043334_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1043689
original SHA-256: 60C2D842637CF5FDC4B731901F77ED7E5998C09AF01BD4ABF744647DB3D4E1BA
candidate SHA-256: 60C2D842637CF5FDC4B731901F77ED7E5998C09AF01BD4ABF744647DB3D4E1BA
원문 frame 패킷: [1, 7]
최종 full_diff 패킷: [13, 13]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 13]
후보 중복만 있는 생략 가능 패킷: [8, 9, 10, 11, 12]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_030_counter_v1/reading_packets_v1/expanded_train_1043689_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_030_counter_v1/reading_packets_v1/expanded_train_1043689_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_030_counter_v1/reading_packets_v1/expanded_train_1043689_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_030_counter_v1/reading_packets_v1/expanded_train_1043689_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_030_counter_v1/reading_packets_v1/expanded_train_1043689_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_030_counter_v1/reading_packets_v1/expanded_train_1043689_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_030_counter_v1/reading_packets_v1/expanded_train_1043689_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_030_counter_v1/reading_packets_v1/expanded_train_1043689_0013.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

