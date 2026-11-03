# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:243315
original SHA-256: F843023DE64E6A74FA17A38E23B51AA7BE5EFBF12D01FC600291A8D7A02C25A2
candidate SHA-256: A6270EEC519D88FE67396D04D16B647E3314FA366A12F671E09FCF1EB2E3BCA0
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:243377
original SHA-256: 9B98C7B79E063365F2542B34B56D820415763E602AAD80D04DCEA43CE0DA2503
candidate SHA-256: 9B98C7B79E063365F2542B34B56D820415763E602AAD80D04DCEA43CE0DA2503
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_243377_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:243576
original SHA-256: 0D78CD3936C6BBD3741EAE404A71FEE39BD159E401A9B43A41F0770312FEF383
candidate SHA-256: 25D70BE8C21E8C83BDBB27266764013B518260811DCE9CBE01D673385247D8EA
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:243784
original SHA-256: DD05A9658DA54F65C2B6FC6863B1ED9E47441EACE2E85A386302EF88DCA19483
candidate SHA-256: 3671930569851C2BD2B06729D0A4685F6C3F3AA412C3C6FDC4D95CAD8FCF38DB
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:243975
original SHA-256: D425E31B7B5AA3CCBA265E967680160CED6C31B7E7633CE6341C25308E7865CD
candidate SHA-256: D425E31B7B5AA3CCBA265E967680160CED6C31B7E7633CE6341C25308E7865CD
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_243975_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_243975_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_243975_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_022_counter_v1/reading_packets_v1/expanded_train_243975_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

