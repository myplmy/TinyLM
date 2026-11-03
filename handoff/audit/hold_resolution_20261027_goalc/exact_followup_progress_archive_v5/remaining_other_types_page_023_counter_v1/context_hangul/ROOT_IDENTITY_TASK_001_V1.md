# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:255926
original SHA-256: 989B7EDAAC10AACCFE6B5E1BED0EED969C846B69E03F2F8FA7BA999F9277CEE7
candidate SHA-256: 989B7EDAAC10AACCFE6B5E1BED0EED969C846B69E03F2F8FA7BA999F9277CEE7
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_023_counter_v1/reading_packets_v1/expanded_train_255926_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:256097
original SHA-256: 4B72F5824098AA2B0A8B5F215F38E0C4AAAEFA1C4743C31BDC30098CA47C8E77
candidate SHA-256: 4B72F5824098AA2B0A8B5F215F38E0C4AAAEFA1C4743C31BDC30098CA47C8E77
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_023_counter_v1/reading_packets_v1/expanded_train_256097_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_023_counter_v1/reading_packets_v1/expanded_train_256097_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:256130
original SHA-256: D98C72F3396A7E20F2B83C2DD0BFA51898C7355E8E688F73D0FF17742F46310E
candidate SHA-256: D98C72F3396A7E20F2B83C2DD0BFA51898C7355E8E688F73D0FF17742F46310E
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_023_counter_v1/reading_packets_v1/expanded_train_256130_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:256634
original SHA-256: 6445CDBA48EBA966B5EBAB0FCC6F3D246C6D2515E4108F3C47F70C49C73FEEA4
candidate SHA-256: EFA8C9412436E4AE14BCCBF1D7646AF7A47B803EBE1CB0B25279F44B36E29675
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:256638
original SHA-256: 6C20CB596FAE8CEEE0DF53C3C865782256C72C306403D905DE38797B1830C8BC
candidate SHA-256: DFAB30AD05C6E4FCAE9A107A9DBB5615FBB81BD5A04CEBF410D9696257E35108
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

