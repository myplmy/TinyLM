# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:14913
original SHA-256: 7C443600879DEE66F5F33FD1EB25BB6BF7F9FCB7362CD7986B1D568177948906
candidate SHA-256: 5B3919A00AC5AF282FB2444BDDA446B3F5C2EA9E51AEDBEB77872CADDC1E65B5
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:14927
original SHA-256: 1909ECC1A377DA755F0502FD6773F9418379F8E7494218D4EDCD87F86C147501
candidate SHA-256: F9E2B3AB3E58420F0335CE53F60249D91C3A4C476D790732368F8C9F9F81A0FC
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:14937
original SHA-256: 23E97D3BAD041C32995F4FDBBD0AD49C27AD6CD04C32AC2F555A17A6EB4990CD
candidate SHA-256: 23E97D3BAD041C32995F4FDBBD0AD49C27AD6CD04C32AC2F555A17A6EB4990CD
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_003_counter_v1/reading_packets_v1/expanded_train_14937_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:14941
original SHA-256: E291AA6EA961634B2CB2CDE9DB81F3091981A51896A7AC066FCCE79726F793AD
candidate SHA-256: E291AA6EA961634B2CB2CDE9DB81F3091981A51896A7AC066FCCE79726F793AD
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_003_counter_v1/reading_packets_v1/expanded_train_14941_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:14944
original SHA-256: F7B828F6DAFFF7933BA3C22B9C2474952C066C1D2DE1AC8F4AE03A54F2563494
candidate SHA-256: 419058017BEE2C9E03263EE6053978DEA73CBCBAE34B764260882CC2D4ED3182
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

