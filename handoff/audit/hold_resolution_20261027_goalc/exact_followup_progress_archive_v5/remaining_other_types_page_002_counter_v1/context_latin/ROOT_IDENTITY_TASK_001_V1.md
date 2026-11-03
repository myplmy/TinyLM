# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:10010
original SHA-256: 885D00ED8E10ECD7B9C387735C9ABA3A132D90190FB2C38A4FAC5BC503B3CB7C
candidate SHA-256: 136621CAF690F18D7878DFFC64A1CA23336273D5C08C67E4100E76B1F5122564
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:10022
original SHA-256: E28677D8E58D652ACB72D78D850457658D5AF103908C350906D11A50DCAD312F
candidate SHA-256: E47492377A75FEA52B3FE84F49908F57D73BE6BBCFCE9EE10B41FB8A312A6308
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:10089
original SHA-256: FF16E2FD93988FC2D89D9935D366D552E9798E2B3B4A7828E50913D91E09ABE1
candidate SHA-256: 4878B89D75A9AD2E82D50FFCDAE4F809A7954FE0286D8CEB50E362A095908B9E
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:10308
original SHA-256: A0BBEE83F0DDE332539938AC2858DB00C8401BDF20CD9EA7C1E71BF4001C84DC
candidate SHA-256: A0BBEE83F0DDE332539938AC2858DB00C8401BDF20CD9EA7C1E71BF4001C84DC
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_002_counter_v1/reading_packets_v1/expanded_train_10308_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:10329
original SHA-256: A985BA52779AAC952F6B9A67516846CA7128A094942F18D924A7C8415B05CAFC
candidate SHA-256: 144F4A91B475065813DA38BA3E71730C5B1885DE3DFA08EC764B74847F6A1D0C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

