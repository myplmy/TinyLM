# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1079632
original SHA-256: 651887C5EB6273AA99F96F3F1DC37B9DD547125CEB48A53F8858527E3AE9B75D
candidate SHA-256: 814EDCC81F18FC7C700B50B7F65D35FB979472136C91FF9128AADD90463C27F2
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1081046
original SHA-256: 283A91D657D471A4456157A5A87C81EE3F335C419CB162CA692182C98034EEDB
candidate SHA-256: ECA1E0DAFAA9B32686E5D1947D02B391BC1CE223FA91309B5BC601520FA881CA
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1081106
original SHA-256: 768C0E768FA51942E4630B63557B90A1EEC0EF0760AB54CC15C7D807BDF3E088
candidate SHA-256: 768C0E768FA51942E4630B63557B90A1EEC0EF0760AB54CC15C7D807BDF3E088
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1081106_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1081221
original SHA-256: 48621075B9B4062FA31B02C53768D49E5CC0BC46E1EF4180BBD81E4591C945D9
candidate SHA-256: 48621075B9B4062FA31B02C53768D49E5CC0BC46E1EF4180BBD81E4591C945D9
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1081221_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1081221_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1081221_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:1081463
original SHA-256: 31434EBC89A92382D545F1DA35F2776A5D4787583987D8C3CD55F1C5E8A3B74B
candidate SHA-256: 31434EBC89A92382D545F1DA35F2776A5D4787583987D8C3CD55F1C5E8A3B74B
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_031_counter_v1/reading_packets_v1/expanded_train_1081463_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

