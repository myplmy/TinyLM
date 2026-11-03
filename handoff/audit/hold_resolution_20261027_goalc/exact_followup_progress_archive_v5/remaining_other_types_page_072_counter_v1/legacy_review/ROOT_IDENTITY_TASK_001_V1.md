# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:963499
original SHA-256: 36817F14B2203BECBD0FF5584DAE3470E8424DFDAFB7B9E923C67B1B1871601A
candidate SHA-256: 36817F14B2203BECBD0FF5584DAE3470E8424DFDAFB7B9E923C67B1B1871601A
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_963499_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:964161
original SHA-256: 3F83E20F5AEA56D01D2DA82C4FDBF544995B48BFA7B1426027F7BE0CBAC630D2
candidate SHA-256: DAB7091BE9CEA308609EC1916B818E5904640D23C459B072652291056EE18D77
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:964294
original SHA-256: 5828455672F78FB68B123ED3B13ABF3136508E6BCDB29439FD9DBAFB0384FBF0
candidate SHA-256: 5828455672F78FB68B123ED3B13ABF3136508E6BCDB29439FD9DBAFB0384FBF0
원문 frame 패킷: [1, 13]
최종 full_diff 패킷: [25, 26]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 25, 26]
후보 중복만 있는 생략 가능 패킷: [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_964294_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_964294_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_964294_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_964294_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_964294_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_964294_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_964294_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_964294_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_964294_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_964294_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_964294_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_964294_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_964294_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_964294_0025.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_072_counter_v1/reading_packets_v1/expanded_train_964294_0026.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:964297
original SHA-256: 864782F2EA5BA147E15055839D44DFED52177A42DB1FC048C165E4B90138E153
candidate SHA-256: 27833375C69F9FA7A8D22062133703AD600961B4F7124CA834F29FF100C251A7
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:964338
original SHA-256: 20F0AACD73BDC12DDCD54D2808A9C994F71238B831382CEE0CACBDB2F51B48C9
candidate SHA-256: 62776D922183A04B2D8F98CEDEE0364B423E3BF299EC2CFF840105421D77360E
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

