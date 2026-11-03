# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:308071
original SHA-256: 3456F8760913057598541AFEC0689A08D921816455DE89711E537DB8A916BED5
candidate SHA-256: 295EA802475DA7A88EA9A6916A5B51429F54EA788E365241D4C0BCCF9404E62F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:308248
original SHA-256: 223B21528D091F5D5404ED694BBD79736953DD51B9FC1436782FADECA301EAD2
candidate SHA-256: 188533E135F88E022BA49408180700E5D9E85213CD89204AA3557AFE1AE05BC8
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:308946
original SHA-256: 2F1DE2068B13B6F7D56E261F0761F014F070DED728515AA62E4067BDAD6AE416
candidate SHA-256: BA473282DB94777874EE2EAD6475F3472F2F02402565EF9961A60401BD07CB31
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:309328
original SHA-256: DB3474809D2AF1D644071CCE23C17A9080819EEF8A1BA63ECE92A967E0A2A183
candidate SHA-256: 24ECD6DB6002C0307EC891C75DEAA4D4B177007E047FEF5A5B85F5B8A0BC52D5
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:309642
original SHA-256: 06C81435781270B8F9DB31B69BACB667F92BF60F39C7010A196ED008077CD3C4
candidate SHA-256: 06C81435781270B8F9DB31B69BACB667F92BF60F39C7010A196ED008077CD3C4
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_014_counter_v1/reading_packets_v1/expanded_train_309642_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

