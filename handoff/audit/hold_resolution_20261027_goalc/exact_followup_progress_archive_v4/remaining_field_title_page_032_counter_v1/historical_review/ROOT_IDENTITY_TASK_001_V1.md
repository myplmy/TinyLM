# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1146754
original SHA-256: 4FF83EDE69C13D5390D1FB8AB111B89F0BE6A93505859AC8AE4836C9FD8E996A
candidate SHA-256: C6567B94BA99E9BAF7A15314C7E51F404285BB84858F39AD49F27D43AC8C7747
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1146790
original SHA-256: 8D934912FFD984B82271D3CE00278671CD5E27014F5F6F754FF66773843CD3CA
candidate SHA-256: 2AF3E8435141D0936B998237EDD18E58A6137AF9D1CD78DB1DB0C0A532575DBA
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1146997
original SHA-256: A26C80639C602529BF3D54335D8CCE06A76C546A3A8D44C57238F6FDB87D5C2E
candidate SHA-256: 2151B9617BEFD3BBC56B3FC6E4B6D982C3B3E85D4AB86364BF4115E5E4813372
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1147182
original SHA-256: 912C1DD676AC75CFCCAA978C131D23A71E25BA45F9BC775D27000144AA38B83A
candidate SHA-256: 3BDCE4C1B1B831405FD4A93D55C04228F08D9569BE240953E287551710A978F3
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1147317
original SHA-256: AB19FFE5AEDC217B2A32460CD9C2176F5318BDFCBE9AA83DD2BF76327975743C
candidate SHA-256: AB19FFE5AEDC217B2A32460CD9C2176F5318BDFCBE9AA83DD2BF76327975743C
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_032_counter_v1/reading_packets_v1/expanded_train_1147317_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

