# 정확 입력 전문 판독 연결 TASK_005

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:105386
original SHA-256: 518AD32CD58B88FC868B3CDA51E521F35C4D2F6842893733850300E51FB283A2
candidate SHA-256: B8005EF75D09D45F827DA5F0C9E855E665098B34F6B18B11EDA420A4C3BC57A4
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:105695
original SHA-256: 5261F61097A75AD4BCBC59A17061A218870AB4DC9D2AFFF72768374229FD261B
candidate SHA-256: 5261F61097A75AD4BCBC59A17061A218870AB4DC9D2AFFF72768374229FD261B
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_105695_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_105695_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_105695_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:106073
original SHA-256: 47AD37B2C179FE876995AE695EC85BAC77E64D8FABDA0AF919AE22CE1A9CE589
candidate SHA-256: 152092D058C3A632FA257253051C25D055C19B41705163C71C78103E816A29A8
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:106223
original SHA-256: E59A0A4426311C1B8C4B89F58C5E918896C4EEA0F3A7EAC5A14829E0FC2636D2
candidate SHA-256: 26A3B8F7549229240E920CCE0DD0F1FD361B392547DB1378A74B9C8BA6B6276E
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:106334
original SHA-256: 9C4B28E420B4C827E7BF537872A788A4D7CDD2CAE0E82ABEE6755111EFAC8EFE
candidate SHA-256: 9C4B28E420B4C827E7BF537872A788A4D7CDD2CAE0E82ABEE6755111EFAC8EFE
원문 frame 패킷: [1, 2]
최종 full_diff 패킷: [3, 3]
원문 전문+최종diff 필수 패킷: [1, 2, 3]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_106334_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_106334_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_007_counter_v1/reading_packets_v1/expanded_train_106334_0003.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

