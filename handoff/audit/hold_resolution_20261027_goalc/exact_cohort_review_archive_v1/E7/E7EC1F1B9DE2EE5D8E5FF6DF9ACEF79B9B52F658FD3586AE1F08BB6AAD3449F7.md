# 정확 입력 전문 판독 연결 TASK_020

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:267542
original SHA-256: 9EC2E85953B13B37AB726E4B330B38EAD8F73A7AF53966637CEF1E12D35E9D94
candidate SHA-256: 7030CEFFE00BFF7B333879604E1BC82714E5B5E72E08FB83F469E7E1B3BEC7EC
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:268359
original SHA-256: DD6C754CBCC6E8009BFE85B58E322B935E095AAFDECC721D66ABFB3A897B02BF
candidate SHA-256: 1D3EB23118F765161C93DC35CD28ECFEE4EFD0AD0E17604C531E6632DC4125EB
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:268384
original SHA-256: 5DADF291BD62692F3327533985642F83855F1BAE6DABD41F1499615943883FC6
candidate SHA-256: CF0E7B0C46EFB4EFA2BF3EBBD23DED0728524A892526D97CE2C0204B012C377C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:268410
original SHA-256: 61A2252113AE80D826191CB1CBF54F877C4D8BDF4904E614C630C5B014327CEA
candidate SHA-256: 61A2252113AE80D826191CB1CBF54F877C4D8BDF4904E614C630C5B014327CEA
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_012_counter_v1/reading_packets_v1/expanded_train_268410_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_012_counter_v1/reading_packets_v1/expanded_train_268410_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_012_counter_v1/reading_packets_v1/expanded_train_268410_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_012_counter_v1/reading_packets_v1/expanded_train_268410_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:270450
original SHA-256: E50A8EC0528800FCB2371DD0E623EBD3E9A6DCEE0D9AA0710D6FA94893369DF2
candidate SHA-256: 34D85DE03497F4FE886527D6BF507D2A55FA0F88EA75E0A2BB543A9BA12F3A3B
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

