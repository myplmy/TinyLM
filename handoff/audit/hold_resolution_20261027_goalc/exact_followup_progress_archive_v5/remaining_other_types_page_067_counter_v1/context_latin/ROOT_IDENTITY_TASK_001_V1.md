# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:880813
original SHA-256: 891922DE07BCF995FA91618510D5130E958A3242EDECF85E29F533B7C86EF4DF
candidate SHA-256: 891922DE07BCF995FA91618510D5130E958A3242EDECF85E29F533B7C86EF4DF
원문 frame 패킷: [1, 6]
최종 full_diff 패킷: [12, 12]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 12]
후보 중복만 있는 생략 가능 패킷: [7, 8, 9, 10, 11]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880813_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880813_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880813_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880813_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880813_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880813_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880813_0012.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:880824
original SHA-256: AA8F7B8A2DBAB901952AD7922693BCB9A96893F4187C7DC11574BA6BE7C66736
candidate SHA-256: AA8F7B8A2DBAB901952AD7922693BCB9A96893F4187C7DC11574BA6BE7C66736
원문 frame 패킷: [1, 18]
최종 full_diff 패킷: [35, 35]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 35]
후보 중복만 있는 생략 가능 패킷: [19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880824_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880824_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880824_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880824_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880824_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880824_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880824_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880824_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880824_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880824_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880824_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880824_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880824_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880824_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880824_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880824_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880824_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880824_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880824_0035.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:880926
original SHA-256: E6F74457CB2ECE848AF7E4A974365B0787731F5D718E4E42BC333A9A217E0734
candidate SHA-256: E6F74457CB2ECE848AF7E4A974365B0787731F5D718E4E42BC333A9A217E0734
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880926_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880926_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880926_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_880926_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:881019
original SHA-256: 5953611E00D4087EF5BF31A9D4BAACC73AAF690B8ED25DF482BC5830499954C0
candidate SHA-256: 5953611E00D4087EF5BF31A9D4BAACC73AAF690B8ED25DF482BC5830499954C0
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [8, 8]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 8]
후보 중복만 있는 생략 가능 패킷: [5, 6, 7]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_881019_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_881019_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_881019_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_881019_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_881019_0008.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:881029
original SHA-256: B548D7190A60995EE8237D44BB7A31C1CBD36DE1CC23C8EB89551B3826CADEB8
candidate SHA-256: B548D7190A60995EE8237D44BB7A31C1CBD36DE1CC23C8EB89551B3826CADEB8
원문 frame 패킷: [1, 7]
최종 full_diff 패킷: [14, 14]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 14]
후보 중복만 있는 생략 가능 패킷: [8, 9, 10, 11, 12, 13]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_881029_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_881029_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_881029_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_881029_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_881029_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_881029_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_881029_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_067_counter_v1/reading_packets_v1/expanded_train_881029_0014.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

