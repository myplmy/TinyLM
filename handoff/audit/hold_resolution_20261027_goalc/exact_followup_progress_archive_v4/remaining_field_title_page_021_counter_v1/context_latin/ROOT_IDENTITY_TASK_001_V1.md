# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:619165
original SHA-256: 47C3F8CE3436EEB2C98810AB4DEFE950A604FCB5CFD5919B15D053B352721AD1
candidate SHA-256: B1B7B5139DC52D10A1B46C29174A11DA4CDAE2E851CFCDC441B00C276C951CDC
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:619309
original SHA-256: 6ABE942A8BE1B69C51A255122DF459565C9E98B5D134EB9B3031916FD8DDB158
candidate SHA-256: 6ABE942A8BE1B69C51A255122DF459565C9E98B5D134EB9B3031916FD8DDB158
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_619309_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:619471
original SHA-256: 334020F2F619EB4C69B5DC24668AB4C4B9E12A02DA301B3AE8DBE6352F95CF82
candidate SHA-256: 334020F2F619EB4C69B5DC24668AB4C4B9E12A02DA301B3AE8DBE6352F95CF82
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_619471_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_619471_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_619471_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:619561
original SHA-256: ACDC7D5CFB3A16D152E45E2C9AADD327AE657A4B50C217309823EC6A38BA6431
candidate SHA-256: ACDC7D5CFB3A16D152E45E2C9AADD327AE657A4B50C217309823EC6A38BA6431
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_619561_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_619561_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:619593
original SHA-256: 83ABDD0A3C1ACA306220AACF4D2E5E83978CF1A7FECA03C0706BB48166276ACE
candidate SHA-256: 4421A9CD9DB7928AF2345EFBBB95DAD374EF4F5883846445213D00FE4463FB0A
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

