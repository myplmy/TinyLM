# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:694892
original SHA-256: 7E725F7906BE4EBC9D4B2739E34B9BD518506928CA8ECC272694E5E7BACB62BA
candidate SHA-256: 7E725F7906BE4EBC9D4B2739E34B9BD518506928CA8ECC272694E5E7BACB62BA
원문 frame 패킷: [1, 4]
최종 full_diff 패킷: [7, 7]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 7]
후보 중복만 있는 생략 가능 패킷: [5, 6]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_023_counter_v1/reading_packets_v1/expanded_train_694892_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_023_counter_v1/reading_packets_v1/expanded_train_694892_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_023_counter_v1/reading_packets_v1/expanded_train_694892_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_023_counter_v1/reading_packets_v1/expanded_train_694892_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_023_counter_v1/reading_packets_v1/expanded_train_694892_0007.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:694906
original SHA-256: 83395DEA8A577E001CA56AF7B9A8223B53718C915CEED736B6B210DE5961B533
candidate SHA-256: 83395DEA8A577E001CA56AF7B9A8223B53718C915CEED736B6B210DE5961B533
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_023_counter_v1/reading_packets_v1/expanded_train_694906_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:695069
original SHA-256: 88D15B5B7730E4628E285C747DE71D54921E3A3669678E3C5A10172CD3DC3CFF
candidate SHA-256: FA5DD6719FD552714799C62D885AE9497A1509D3A3E82220F482DB155E0857A0
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:696018
original SHA-256: 0A45422D25D7A7B62A57A84B7B87F7A1FC122F4C19CABE0F7784EF774412AB52
candidate SHA-256: E0EFF6195D1E9DDA68F8D3E0C87C9CA9CE82E0247FBC18EC507936A8CEF789D5
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:696219
original SHA-256: C5D5AEB67CD60529E860C0499D099D3909E7A30B508F506C8B7EF7918E1FF83C
candidate SHA-256: C5D5AEB67CD60529E860C0499D099D3909E7A30B508F506C8B7EF7918E1FF83C
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_023_counter_v1/reading_packets_v1/expanded_train_696219_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

