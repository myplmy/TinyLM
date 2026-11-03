# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1116564
original SHA-256: AD8482B1E53CFE77DC585DBBA08438F94F5AE6F30999CD333F1E3F8F42EF0141
candidate SHA-256: AD8482B1E53CFE77DC585DBBA08438F94F5AE6F30999CD333F1E3F8F42EF0141
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1116564_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1116564_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1116564_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1116564_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1116576
original SHA-256: 73D34D88E5371A1CCE329B3135DAAA4D8804773003E5AB39E13D8320F829AE8D
candidate SHA-256: BD738A36FFB86E45A43C889B9705D3C941E4651B841CDE046A14CB7B2E3ED395
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1116591
original SHA-256: 9C58BF21241C72BCA2A6EF0A4F4F2662DC946FD36EA1198B5021F944AEF14977
candidate SHA-256: F1A5E7790BDB1688619E317A1DFC41BE4F32C6387EDE1558040C2FA727A9A5C3
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1116619
original SHA-256: 2E33A26B33F4C528623F8B7F0F0FCE855D10E36F9A1B19A516DB2B74749B1013
candidate SHA-256: FCB38B02FA8CB8409BEA158A1705825FFC00E44540A22BAE27500BA6AD1882BC
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1116651
original SHA-256: D39CA5003B3E18E6B00557BD62383C5C0B5000B8EE4B88DCEE58321B18669C24
candidate SHA-256: D39CA5003B3E18E6B00557BD62383C5C0B5000B8EE4B88DCEE58321B18669C24
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1116651_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1116651_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1116651_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_081_counter_v1/reading_packets_v1/expanded_train_1116651_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

