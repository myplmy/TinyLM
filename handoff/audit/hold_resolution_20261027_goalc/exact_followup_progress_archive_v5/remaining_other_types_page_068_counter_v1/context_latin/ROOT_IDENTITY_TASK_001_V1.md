# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:895879
original SHA-256: F9A10D51F9ECDDA03A6D8AF8655633C07E9D55FEF7A792B44F9D3ACA7DB948BE
candidate SHA-256: F9A10D51F9ECDDA03A6D8AF8655633C07E9D55FEF7A792B44F9D3ACA7DB948BE
원문 frame 패킷: [1, 7]
최종 full_diff 패킷: [13, 13]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 13]
후보 중복만 있는 생략 가능 패킷: [8, 9, 10, 11, 12]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_895879_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_895879_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_895879_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_895879_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_895879_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_895879_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_895879_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_895879_0013.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:896263
original SHA-256: B44D734E90212A0B49C6E5ABA63F9AAE145D544653A049C98BE85AE2CC037E72
candidate SHA-256: B44D734E90212A0B49C6E5ABA63F9AAE145D544653A049C98BE85AE2CC037E72
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_896263_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_896263_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_896263_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:896597
original SHA-256: B7F0090D6A9183999BD62690136AE8BDD333982922653D47B1DE3D7BA0405E20
candidate SHA-256: 10DFEC7FA4E3D14B695DAC87FE41A65030939B822DC8FF149FC4CC497FCD5C38
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:896658
original SHA-256: 515E153631C538845C03764C7E77EB4D8A0F9E58D7DC75D739E79F919C96F468
candidate SHA-256: 65D675CA9F7B9A3274E723386AE80472528882C563555CAD240210C732CFCCC2
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:896720
original SHA-256: 8ABA3B0706C1E2EE181E1A81A389FD1254840321A0C71808E3426A8860A92107
candidate SHA-256: 8ABA3B0706C1E2EE181E1A81A389FD1254840321A0C71808E3426A8860A92107
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_896720_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_896720_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_896720_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_896720_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_068_counter_v1/reading_packets_v1/expanded_train_896720_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

