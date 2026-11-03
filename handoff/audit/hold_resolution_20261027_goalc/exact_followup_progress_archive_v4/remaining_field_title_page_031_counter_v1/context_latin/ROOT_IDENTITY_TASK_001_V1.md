# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1079430
original SHA-256: 9924ED2F8077B618B8EA13770EC61161516EE9AC929B54988FFB2DCA356EB877
candidate SHA-256: E13BF7BF044896B40E10B9CEA71C0B667E604A4F080353566D473F6597AE77AB
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1079845
original SHA-256: BE846BE38ED53D490FE520E67C6E2A23846BD0ACC74817CD2D87F0E5FF1AC2FD
candidate SHA-256: F30C822A884C12DEE38A8D4F95412B3BF6D2A54A56E198FF4373A6C35148B101
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1080599
original SHA-256: E874DE319F60BA03F46CB8445E81525661AAFA8A9FB19EE24AAD3698935F84B3
candidate SHA-256: E874DE319F60BA03F46CB8445E81525661AAFA8A9FB19EE24AAD3698935F84B3
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1080599_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1081078
original SHA-256: 9EDC9050ACABFED5E7B6C6ECC94DDAF9F3A889A85B2929DFB479EEF85CFBEC84
candidate SHA-256: 9EDC9050ACABFED5E7B6C6ECC94DDAF9F3A889A85B2929DFB479EEF85CFBEC84
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1081078_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1081276
original SHA-256: C3DAB5B2F19FA153C677D80D585DB1888F01D6F35B76A26E087CFF5ECCF1FCCB
candidate SHA-256: ECAD365FD2C592762D55BADA9264386B58358ABB29F715E21710097C4575D072
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

