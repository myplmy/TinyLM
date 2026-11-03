# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:619217
original SHA-256: 448C112DEDEC8ED8F4258FB0B00A4C7606E3EB060074E871C3C7B1132EDBECD7
candidate SHA-256: 448C112DEDEC8ED8F4258FB0B00A4C7606E3EB060074E871C3C7B1132EDBECD7
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_619217_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_619217_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:619665
original SHA-256: CB8765D46146D0C76981B69593AAABDF33DF13A0107584788362D937362D9834
candidate SHA-256: 94559D21AEE1BE89EE31AF60B310C5204F7392CFA9AE0E4EE2C8661EB1A4A036
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:619719
original SHA-256: 60160F43529FBF1EDEF29E7CC075F2874B01F795064404B439392D93B9E4FA59
candidate SHA-256: 83A6243162C5A27CE90498C905949759CCB8069E17950FC2F66F4C6FD007B58C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:620207
original SHA-256: 8FEF4CCE72B13BBADF69667D8C3D3F914B049780E5BC9284690360F76D784539
candidate SHA-256: 385C0D2109F8FC1C92B133E358EB4D1B0B3B5C996100391F2B577501F4CEB1F7
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:620311
original SHA-256: 780685F29EA45E8C57904A1EC82D44A52574B7FD04D1E0D5ABCDCA3C6D24497D
candidate SHA-256: 780685F29EA45E8C57904A1EC82D44A52574B7FD04D1E0D5ABCDCA3C6D24497D
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_620311_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_620311_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_021_counter_v1/reading_packets_v1/expanded_train_620311_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

