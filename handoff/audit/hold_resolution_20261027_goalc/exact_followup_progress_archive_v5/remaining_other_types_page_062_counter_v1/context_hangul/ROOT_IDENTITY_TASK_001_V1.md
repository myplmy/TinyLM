# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:802295
original SHA-256: E3D02C1F07CF6CEDD6ADC0D50CD661DA36DBD3F48A8D21CDA91675B21FFFD48B
candidate SHA-256: E3D02C1F07CF6CEDD6ADC0D50CD661DA36DBD3F48A8D21CDA91675B21FFFD48B
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_062_counter_v1/reading_packets_v1/expanded_train_802295_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_062_counter_v1/reading_packets_v1/expanded_train_802295_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:802327
original SHA-256: 3F32177D27B2A6007FF9AE2F920F08ACDAA9EC0ED665C00A03377EB4F5749720
candidate SHA-256: 9CD19B4B7C7155F235C52D2B82B7C333B416DEC206A8A3B235805A3751DAE2F2
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:802515
original SHA-256: 6A80BE7BFA7775D789FCCFE8538B124DF01C011843A69415D5D8F6A874BF97C9
candidate SHA-256: 85FD63C478638CCAAD3C92DEDBF8C2ACEE06D361732F88A306DB68EBAC4C7AD6
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:802641
original SHA-256: 91BC6DC5D0FB49AEAF42EEF65809968FA9DE7C671F9A7302FC1D6608D2478CE5
candidate SHA-256: 2146CEC25E3301147411A20C8F620EE45290CC55D3838919F372C36B5CE00DDD
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:802685
original SHA-256: 313BCEE2C83510454A636F6DF045C438CD871997461BFFA2FB28C7C7AF99E907
candidate SHA-256: 12F9665E5DDAE099576D3DBFFD0EFD6C38A8D0AD66D80E6EBFAEBB7DEA04CF09
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

