# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:402322
original SHA-256: 48DF22568CD7B6E65173DE7970985FC25945C7D82520D51C4B252E07A7658CCD
candidate SHA-256: 6A720D6D90805C17882360A2FF44BC1DF36630824C8E2457F06558CC483BE627
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:402333
original SHA-256: D96F74596005FE6234A2C3FBEA589ADF1B1A24D37EAFF467C3EB6002630F2E08
candidate SHA-256: 2C3FF7A5B65AF5BE3DE9EB82D9BF3505C22A5BFD3FE4B0E4EFB32E3CCF8169BB
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:402358
original SHA-256: A3358E3BB749D9D4E6118EFDF0BD1DA82F7512A9B1EDFAEDD68F3AECADB14BF9
candidate SHA-256: 9AFF8681613B4AAAA85B9827C7F405C3DDBE1756272A43B5864982D4F8B5189C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:402575
original SHA-256: E020C61858C322497F874F870BB9C6DA52EFE26D592B3300071BB54E9B23168E
candidate SHA-256: B202887CD6F3389DD4C6CEDB91F385581668E60D588AF0D3CB95F49973EB6A92
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:403010
original SHA-256: 9EFDA1CD6B0E069B3431F568FF6E0CBFB530F7256B929CC1063F2235E593660B
candidate SHA-256: 9EFDA1CD6B0E069B3431F568FF6E0CBFB530F7256B929CC1063F2235E593660B
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_403010_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_016_counter_v1/reading_packets_v1/expanded_train_403010_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

