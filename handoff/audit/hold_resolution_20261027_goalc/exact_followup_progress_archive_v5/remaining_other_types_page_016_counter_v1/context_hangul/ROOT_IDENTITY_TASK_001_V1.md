# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:161394
original SHA-256: C1AD6E76D3D3E835BADAD350CD2EB71760B4D6326924B767FB3B5DBDF4E19655
candidate SHA-256: C1AD6E76D3D3E835BADAD350CD2EB71760B4D6326924B767FB3B5DBDF4E19655
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161394_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:161397
original SHA-256: A3F58F0C1CD5529CB8279DEC5A7A5FA5E8A9B00342113C4E1A16EE7936510B57
candidate SHA-256: A3F58F0C1CD5529CB8279DEC5A7A5FA5E8A9B00342113C4E1A16EE7936510B57
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161397_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161397_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161397_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161397_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:161408
original SHA-256: 7BA01A0F182AE1C3553362244E288FA0467D6944B79E539C34F8D7314B8E2AD1
candidate SHA-256: B366E2A555CE26E07A0A9AB499D15BC3EBBCDB0256D98068185664681028006F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:161515
original SHA-256: A61296C03E5913A8D4BCC83D970F78040EAE515EECBCFDA47C6E840EEA511085
candidate SHA-256: DE2DC5B02BCF4302BFE1088CC9BF68040B59B8BADD322CDFD789CB26AD918ED4
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:161875
original SHA-256: E0104BD7E4E03BB66B0A0AF96AD4BC7948B834F4C220C3BEF30E3E4612345DA9
candidate SHA-256: E0104BD7E4E03BB66B0A0AF96AD4BC7948B834F4C220C3BEF30E3E4612345DA9
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161875_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

