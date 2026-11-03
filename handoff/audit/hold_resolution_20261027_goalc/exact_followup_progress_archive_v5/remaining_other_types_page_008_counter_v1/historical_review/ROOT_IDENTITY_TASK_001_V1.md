# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:73884
original SHA-256: 3B0DFF99C4EF7E57706A13EA5D69938832E32831AA27C555583D9709485508D3
candidate SHA-256: 3B0DFF99C4EF7E57706A13EA5D69938832E32831AA27C555583D9709485508D3
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_008_counter_v1/reading_packets_v1/expanded_train_73884_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_008_counter_v1/reading_packets_v1/expanded_train_73884_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:74158
original SHA-256: C5C6ED0EEE95F3E529220798848E7E1C1DC3158458004C855D5CE1AA8FDD9581
candidate SHA-256: 69CF26651ED4798C36ECD6A6F393D6BF4BDAF2DA7CB7EF3C1298E8273024B48E
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:74229
original SHA-256: BE37B873444F71C80AD84480153F70E3B0163C33B6E25124B95F928E6A4F7C0A
candidate SHA-256: 124C2B13FD67B37578514A0DFACEBB567AB53D36DCE5BABC27006994C536BDF7
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:74313
original SHA-256: B734700AB852BC4B796A9D41DBB05F9AAB967B7AB1159535D7C84140EF1AB8A7
candidate SHA-256: 37AD643505D51E1331F6F7A684794EB0256343214588B485B74ABFCF359FE90A
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:74367
original SHA-256: 0B4D7F9F6D853BDD76BE68B107E0166C6D00BA1C672DA3FA0644931659266B4B
candidate SHA-256: E439778F6BC4F027702F6268E2724E779A0C2792813C09D78C1080D97B692A63
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

