# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1421716
original SHA-256: 84AC084AA64CC540A6C87E1DC6A3C5DD640F5A9CF8705B3FB1E387E2C14CA52A
candidate SHA-256: 84AC084AA64CC540A6C87E1DC6A3C5DD640F5A9CF8705B3FB1E387E2C14CA52A
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421716_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421716_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421716_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421716_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421716_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1421749
original SHA-256: 1973E6BD78C72582634C789963BB84723028FED0F2A7C4FA435E7D5A6E18E908
candidate SHA-256: 1973E6BD78C72582634C789963BB84723028FED0F2A7C4FA435E7D5A6E18E908
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421749_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421749_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1421749_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1422239
original SHA-256: A0BA9A02884291886A77DEB3C678BCECBA92F0609860DB204821A0AE6FADA028
candidate SHA-256: A0BA9A02884291886A77DEB3C678BCECBA92F0609860DB204821A0AE6FADA028
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1422239_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1422239_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1422239_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1422239_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1422239_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1422341
original SHA-256: A7153D9F976AF5B2A3B6520BED64633BEC0845791340220CBB055C7DB5312939
candidate SHA-256: A7153D9F976AF5B2A3B6520BED64633BEC0845791340220CBB055C7DB5312939
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1422341_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1422341_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1422341_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1422670
original SHA-256: 1A196AEC8CF6F2AB714C19C181726247697DD6FE9D10F1364DDAF8B51B87FA78
candidate SHA-256: 1A196AEC8CF6F2AB714C19C181726247697DD6FE9D10F1364DDAF8B51B87FA78
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_098_counter_v1/reading_packets_v1/expanded_train_1422670_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

