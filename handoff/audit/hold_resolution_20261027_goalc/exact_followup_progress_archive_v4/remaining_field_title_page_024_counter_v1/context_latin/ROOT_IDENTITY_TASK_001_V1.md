# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:736169
original SHA-256: 0DD28078E5663675D1695B18AF82DFFBEF72DF10F95E0A75B26CCDA4767AC0DA
candidate SHA-256: 1F76AE173BF1A3DB0BC547420E6477AC111FF952FA074931BDC627D4983E336B
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:736176
original SHA-256: DBA811946823FDF357DD2106B3D480F43E34E928C96741220DE5733CCFA65213
candidate SHA-256: FA3F8C99BE29100F55D4CDFA7629C8DEE1718FB4D0188787BD3C69DB6263326C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:736180
original SHA-256: F661E07FF6F681307CCE459B4E78A37F0C46B05D2CE4E00B9B8924197DD4D007
candidate SHA-256: B1AE24DD95165AAB1B73C1D0498929379C00B18B05D263B5B0E86D4A8758322C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:736196
original SHA-256: 45C8A85292A4D05E7108F917E356DF67737A35122EB76DFA986A3611739C68F6
candidate SHA-256: 45C8A85292A4D05E7108F917E356DF67737A35122EB76DFA986A3611739C68F6
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_024_counter_v1/reading_packets_v1/expanded_train_736196_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:736282
original SHA-256: A2076C572F49CD538B65882A08753427684903E882D6657C4579F12A2D9ED5B5
candidate SHA-256: A2076C572F49CD538B65882A08753427684903E882D6657C4579F12A2D9ED5B5
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_024_counter_v1/reading_packets_v1/expanded_train_736282_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_024_counter_v1/reading_packets_v1/expanded_train_736282_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

