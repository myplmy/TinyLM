# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:270296
original SHA-256: 1CF727BEE48DDB5C792A6260044A316E0E388481F632A39744A3359FA93B84C9
candidate SHA-256: 2BB47D7908303102638000DB7CF79F0B6D665115D9EBCF1B3B422D88564C3F77
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:270351
original SHA-256: 86CBF39AEB6D2C6BC53BA9DA013FAB7C500BBD47794AB4724D476B7AF60A648C
candidate SHA-256: 1B44DB90EC0915E8BC45ABC7E94D5CA80DC3C9E7FBEFB4881E13428C8688BF33
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:270391
original SHA-256: D4C4294A133ED1B112E74863CCA4FFB21438301512766ADAB9990C540D860A6B
candidate SHA-256: 4499A481F9EA8AF2B047BBED3584BDE4E13134F9CD1F8EF59FD9E8BB28303D08
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:270620
original SHA-256: 83802DE91E57F7C5BF09D176E729531E0A51EAC1AAF88243261E65B232C64E33
candidate SHA-256: 83802DE91E57F7C5BF09D176E729531E0A51EAC1AAF88243261E65B232C64E33
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270620_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:270634
original SHA-256: 8FC04D2BD5142AA59A6A741161A78B16BEDA98C8A1A29343D21926E271FBDBD0
candidate SHA-256: 8FC04D2BD5142AA59A6A741161A78B16BEDA98C8A1A29343D21926E271FBDBD0
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_024_counter_v1/reading_packets_v1/expanded_train_270634_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

