# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:10479
original SHA-256: F656C7A1C5C47EB819F31BE468C439AE3F285B8F456E7E591860A4BF316BAC34
candidate SHA-256: F656C7A1C5C47EB819F31BE468C439AE3F285B8F456E7E591860A4BF316BAC34
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_002_counter_v1/reading_packets_v1/expanded_train_10479_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:10898
original SHA-256: 81225FE416CF91E29BE7E63ECA085E6DFC468C6A799DBF5F6624A460D0262A13
candidate SHA-256: A3DFD84D2388F019CF503889D16FF03E70268A629C19DF4B19B6128D4C2DCC13
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:10993
original SHA-256: 7636B331D4CA83092F08F81C12426FA580E49B62BE8B8B63D5A1A512DAC2ABFD
candidate SHA-256: 55A33758785FA2CCE02B7D2FD34A2B638713F1806E9F540303CE7C3E97955D65
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:11066
original SHA-256: 3161D6A8CB25EF46892976A05502C5694DA8EA2645B98F8E95781AD4FC178E58
candidate SHA-256: A0318D002EF7B2186074C370C33F902E2CCFE3972D0D2F6B0913D4CF15773E24
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:11155
original SHA-256: F194BEDC21DE9D59431213BE2707DB0491803A608588C4B3A80619DC74D9F8A2
candidate SHA-256: F194BEDC21DE9D59431213BE2707DB0491803A608588C4B3A80619DC74D9F8A2
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_002_counter_v1/reading_packets_v1/expanded_train_11155_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_002_counter_v1/reading_packets_v1/expanded_train_11155_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

