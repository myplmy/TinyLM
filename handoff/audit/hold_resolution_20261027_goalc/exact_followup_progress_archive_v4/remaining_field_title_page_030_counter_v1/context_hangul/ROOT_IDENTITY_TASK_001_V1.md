# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1042260
original SHA-256: 565ACAC541F34799F776E789D016D10521200E3EF8C505A46E409CBDD8E32F5B
candidate SHA-256: 565ACAC541F34799F776E789D016D10521200E3EF8C505A46E409CBDD8E32F5B
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_030_counter_v1/reading_packets_v1/expanded_train_1042260_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1042362
original SHA-256: CEAB33B98E3003EF54CAE23030561D7213E46024D28CFD914EF1307F580117BE
candidate SHA-256: B3806056820C1CBD3B05683924DC6DA7AC26610A9F6C8942FEA24F872A54C744
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1042487
original SHA-256: 60ABA949E6D09DD30FEEE5D37D0AB89D2836576C460697A43DC253B75CF1DEA4
candidate SHA-256: 4AF2E564B816323137974757A7DF2FA0538D93CB6350175637BC2F00DCD62B5A
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1042556
original SHA-256: BA9DEE77A472968220076DCC525BC2CA48271D51FD2F68E5B5E02DC462D30791
candidate SHA-256: BA9DEE77A472968220076DCC525BC2CA48271D51FD2F68E5B5E02DC462D30791
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_030_counter_v1/reading_packets_v1/expanded_train_1042556_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1042564
original SHA-256: E5DB18B2AA333F838D0786C83C94B29DFBBE24B3491EDB5FD66BFEA5282EDB21
candidate SHA-256: 663DC4FA3ED842562809F28F746CA64BB57DF190EC0D492349B35143863F0247
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

