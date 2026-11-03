# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:112851
original SHA-256: B07F1DBE31BC448A473B844D74E1ADF34EA3A3FFCE68919B7BB6A936372F07B8
candidate SHA-256: B07F1DBE31BC448A473B844D74E1ADF34EA3A3FFCE68919B7BB6A936372F07B8
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_008_counter_v1/reading_packets_v1/expanded_train_112851_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:112898
original SHA-256: 9AED4F58A4DD90B16F227EE4FF77021BAACC9F2C2BFD834D1AB9F8AEDBBB5563
candidate SHA-256: 47E6823B117EF741FCF4651220F354453BC31EEB516B4FBFD0E238CA46553FB4
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:113374
original SHA-256: 17BC124380D9574F7F52256E499DED25992151C3F04056AB6B11900BCD1EF3AA
candidate SHA-256: 33BEDECC1A7E1D20B73D8D5E2D58206B664A7B416228F72109F823869519F9EE
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:113401
original SHA-256: 526537DC327612BCE47A92AF235A150FEEBEAE38B071D6E15E9379D8FC13AF5F
candidate SHA-256: F7D08C0159147638FD76213104DF3E222883339B13298F47529CD55C5FC24990
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:113829
original SHA-256: B27D1A72294F5F4A8C06CEBE1059E95219ADF24444A4A24177036329B3671657
candidate SHA-256: 41F1241523BC0D0A455187E6F4F49B134957854D373AD3902D1EE6EB694E6BB6
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

