# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:736023
original SHA-256: 3DE09831057FC102B02BD775F775D6291A15B4BCAC969488B543D2D4F197C368
candidate SHA-256: A2CCE86E9613C5680129B78E35BA54432DBEA6B14BD813C0B995BDB7A2E8231F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:736639
original SHA-256: DF5297A9978DF7D4B88888F7AA488BB6EEE3CF9C49D7B060D3FAA0CBD58E801C
candidate SHA-256: 1C53885D9C5B264046ABA5E4A6A55B1DFE13AE0EC895C2F4225EBBBCE3CD1BC3
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:737435
original SHA-256: D2A8CBD9BE61D4364CC90AE8E6016DB5E8385F9A0BC565A1DC56BAF8B315F375
candidate SHA-256: D2A8CBD9BE61D4364CC90AE8E6016DB5E8385F9A0BC565A1DC56BAF8B315F375
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_024_counter_v1/reading_packets_v1/expanded_train_737435_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:739068
original SHA-256: 75EB9AA0C068930C401B65B183039842ED6F972CCE5C9886568F1E32E3B57865
candidate SHA-256: 75EB9AA0C068930C401B65B183039842ED6F972CCE5C9886568F1E32E3B57865
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_024_counter_v1/reading_packets_v1/expanded_train_739068_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_024_counter_v1/reading_packets_v1/expanded_train_739068_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_024_counter_v1/reading_packets_v1/expanded_train_739068_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:740326
original SHA-256: E547235A0DCDF879E38639B22DA0963FF26BEB77B6E706562E40F3A79329B34D
candidate SHA-256: 83440CA846B507E5F3F96C68EFF843E899E92E084F79DB115F4B521D71267E20
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

