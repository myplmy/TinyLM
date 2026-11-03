# 정확 입력 전문 판독 연결 TASK_006

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:120796
original SHA-256: 471E78591826A3212FF5DD791A4813D0B4B54780070F06DBFD763E825AE25CEC
candidate SHA-256: 55C2CF9227F962129571C8F730E7417D3BCC9D25140805BBB9802860BF989374
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:120884
original SHA-256: FA9A4CA13512265A72A37676DEBB5F1FF0C831A4B41FF5601D6194688D6D82FE
candidate SHA-256: FA9A4CA13512265A72A37676DEBB5F1FF0C831A4B41FF5601D6194688D6D82FE
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_008_counter_v1/reading_packets_v1/expanded_train_120884_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:121519
original SHA-256: 18AF0054398CA490FCCEA26AF1485250970719B28B2A32BD1D9922A4910B2802
candidate SHA-256: CCBC5EAFB298C2D42A375E3CA32625C513B390D602482932019600EE50FB4A00
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:121597
original SHA-256: 1DEF97CFC5389713616112D6D3BE72889B60497DEA9F1911310AB53CC2B807D0
candidate SHA-256: 17217F02D431ED43BE1EFAA97DBC909ED909EC965227EBFF2707D294EDE2FF87
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:121807
original SHA-256: F007DF476F22ADB15AA590B8586AF926D679B16A8C1160A2B0FA4065DBD72A45
candidate SHA-256: F007DF476F22ADB15AA590B8586AF926D679B16A8C1160A2B0FA4065DBD72A45
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_008_counter_v1/reading_packets_v1/expanded_train_121807_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

