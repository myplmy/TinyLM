# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:946803
original SHA-256: 02D09C2E8895DF2D1BD5DCFC63340AA35A3D59503A09E539B76765E7E0909A91
candidate SHA-256: 02D09C2E8895DF2D1BD5DCFC63340AA35A3D59503A09E539B76765E7E0909A91
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_946803_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_946803_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:946831
original SHA-256: E322EB6099C6EFD362DB0D89067B15838BA6F6A5B11253F4555956F81D2619E4
candidate SHA-256: C60AB0BF0FE574F0FAA6C0EF279EE5696D446D40358205F2F1052A40F25EFADF
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:946944
original SHA-256: 47658DD3932C979625251BDD379C05449A17ED572ACC587747C684EF71E40FEF
candidate SHA-256: 8E5C7573DCC97414E8D8B9C4F0B385C8D8F09B9DF605291099F00077138091C8
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:947105
original SHA-256: 83BE4C0F8AE05020C5DC50D34C52F02B2F6531191CA7CAE2BF92EE5908B86794
candidate SHA-256: 83BE4C0F8AE05020C5DC50D34C52F02B2F6531191CA7CAE2BF92EE5908B86794
원문 frame 패킷: [1, 8]
최종 full_diff 패킷: [15, 15]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 15]
후보 중복만 있는 생략 가능 패킷: [9, 10, 11, 12, 13, 14]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947105_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947105_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947105_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947105_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947105_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947105_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947105_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947105_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_071_counter_v1/reading_packets_v1/expanded_train_947105_0015.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:947110
original SHA-256: C4933F26C1EA36F6F496C4B675000CA06E29FD9E8EF181F00B98CC913C29BCCA
candidate SHA-256: 4FD03C79AB720F91F25715A5A82AA9E4D9728D63B80E6AFF7A6387AF21E24E67
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

