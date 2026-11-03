# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:716931
original SHA-256: 63968527C0B643FF8A0CF78C9FE12B4757A28B58BF2BAA91FB981BEE5F013793
candidate SHA-256: 63968527C0B643FF8A0CF78C9FE12B4757A28B58BF2BAA91FB981BEE5F013793
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_056_counter_v1/reading_packets_v1/expanded_train_716931_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_056_counter_v1/reading_packets_v1/expanded_train_716931_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_056_counter_v1/reading_packets_v1/expanded_train_716931_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_056_counter_v1/reading_packets_v1/expanded_train_716931_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:717111
original SHA-256: FD0E2F3CAEF1967B8FB8DF4B3DABA42F3A5B0F0EBB1A56203C301269558916AF
candidate SHA-256: F533ED196AD5D96162F4A7FFB80A0917BBA12C9F11D887A44FA75AF5531BBD41
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:717223
original SHA-256: B60F7E7BC28BE95CE20D2B444332EAB50A684189641C0C06FA0A21FE87E88475
candidate SHA-256: 6CE716E07870519E9F27A2DDE8417BF19C0D8A4A78790A8D95545FD79062F17B
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:717258
original SHA-256: 3A29162DCE652EAC75A8F0C23AB5B8F7A1655D8F78C5454D950AE8D119B85F84
candidate SHA-256: E55FCC4D829292B4B1D2A9F5B1C6D4259B0B054B7B094C270AFBF0826BFADB52
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:717259
original SHA-256: D57E9E0EF0198F38BE4F04BDC3CA3BB48F0F51D51B90C66C9FF27BB1043CACCD
candidate SHA-256: 008B996F8017C56A3AA456AEF7CBE7FE5B4AFB0F7AAE73360F4F547DC9BF4A3F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

