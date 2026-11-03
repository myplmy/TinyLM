# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:927615
original SHA-256: 9A29BD09B435F7165D515BA93FA21A4FB4C27CF5AF7AE8176BED31D19E7A3E25
candidate SHA-256: 9A29BD09B435F7165D515BA93FA21A4FB4C27CF5AF7AE8176BED31D19E7A3E25
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_028_counter_v1/reading_packets_v1/expanded_train_927615_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:927905
original SHA-256: 61CFCE4789398D130A4033299EAF782FC4AE751D287E833340893F2EC921B3B3
candidate SHA-256: 7803EC227BE78B2A05FCFFA1177578886FAF1C117B7630F793FCF482BC3E7C09
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:928317
original SHA-256: 467858A4A4C0273FC4DDEF89B5A0E009B96C15CB79340CDA22C7DA210F385EF0
candidate SHA-256: C3B74068346095A41198F3596511E991FD27523329F9E5649D9877C69AC86A43
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:928762
original SHA-256: 7CB5D190A550D50FF466525465192F35FCB83651593ECD6E90F10DF7EB897421
candidate SHA-256: 70F28FF7B0092447E352C1C2C71197221BA076F4A8B3A32348A53B31B07B87E2
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:929302
original SHA-256: F1AFBB33032EC1B5B61098009FF710DB386ADE35DDFF29B761858C9198F3B448
candidate SHA-256: F1AFBB33032EC1B5B61098009FF710DB386ADE35DDFF29B761858C9198F3B448
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_028_counter_v1/reading_packets_v1/expanded_train_929302_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_028_counter_v1/reading_packets_v1/expanded_train_929302_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_028_counter_v1/reading_packets_v1/expanded_train_929302_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

