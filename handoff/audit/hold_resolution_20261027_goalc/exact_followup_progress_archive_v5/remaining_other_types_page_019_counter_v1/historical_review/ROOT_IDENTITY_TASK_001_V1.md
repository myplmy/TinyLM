# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:205211
original SHA-256: 78E420AD83FB2D67E44211A0E4C779CB5EC8B2F463C86A6433414AC09F9DEFC1
candidate SHA-256: 78E420AD83FB2D67E44211A0E4C779CB5EC8B2F463C86A6433414AC09F9DEFC1
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [4, 4]
원문 전문+최종diff 필수 패킷: [1, 2, 4]
후보 중복만 있는 생략 가능 패킷: [3]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205211_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205211_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205211_0004.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:205275
original SHA-256: 751321152A0BD81CDF8C357B38D3C5F9FDA772E5671FB37B9A3F722219447DAE
candidate SHA-256: 4F18796472A376236F1572F4716BEE8F03AFC6EAD1AFE774D24DD78C791BEC4F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:205315
original SHA-256: 98820BA5D10F445AD7D6950201C8AA8195FED53D24A4E208D540FD1E0C3672E7
candidate SHA-256: 98820BA5D10F445AD7D6950201C8AA8195FED53D24A4E208D540FD1E0C3672E7
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_019_counter_v1/reading_packets_v1/expanded_train_205315_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:205490
original SHA-256: ECF0F5ADB8D53ED50729C994C0BA2D7CF0277F1F3D91F81DED4FE185D52A3EF9
candidate SHA-256: 81EE866E3F49F301EA61414FBA02915D1AA4F6AF6BD29E51B24206EC8757937E
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:205507
original SHA-256: 63CDB4305546A3DBE57939BF3571B42A10ADDB17ACFB4FB31FFABC2DBD452074
candidate SHA-256: 94EB56D203108502636C5A79042A2B3C3E848C30DA7BC52FD729E5104950AF17
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

