# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:126862
original SHA-256: 57EF41B24206FB0F4083780FB8B6BB82D33EF5CCE1AE9068F9C9768143C6E071
candidate SHA-256: 57EF41B24206FB0F4083780FB8B6BB82D33EF5CCE1AE9068F9C9768143C6E071
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_126862_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:126918
original SHA-256: 4190C641398F9DB2C656C355CE62BA0D1F407CDCDB5E09CA2815D42B6ABE68F7
candidate SHA-256: 4190C641398F9DB2C656C355CE62BA0D1F407CDCDB5E09CA2815D42B6ABE68F7
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_126918_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:127056
original SHA-256: A1744FF2433BB90C815864CC213C9A4C60D9228A4B7DE1A79219470E9679AAB7
candidate SHA-256: A1744FF2433BB90C815864CC213C9A4C60D9228A4B7DE1A79219470E9679AAB7
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_127056_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_013_counter_v1/reading_packets_v1/expanded_train_127056_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:127150
original SHA-256: 7B27C22824D64D47426181D4D12826DBC357BB4637C4EB93342595F8A779D910
candidate SHA-256: 28366E0ECC1458412CAD1B2734D3F7813F76D4BC7EF239465FC40AFC4AAD38BA
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:127185
original SHA-256: E35DFC050891D4C8CE4E45137BB9158E2239CBBF1DF7F8FA5068A877FB09BDCA
candidate SHA-256: 02037BFB460414607C6B3D0F28998C293A851FE6DD912FCDB256E123D4E07D98
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

