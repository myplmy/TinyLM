# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:736157
original SHA-256: E6C88D9C6CBB5DE5D041055736219D5C0B7F35B8B017FB21E5C6C380075B06C8
candidate SHA-256: E6C88D9C6CBB5DE5D041055736219D5C0B7F35B8B017FB21E5C6C380075B06C8
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_024_counter_v1/reading_packets_v1/expanded_train_736157_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_024_counter_v1/reading_packets_v1/expanded_train_736157_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:737086
original SHA-256: 6F595B447779928A8991A740E3E68A8C524105AD612A643079470040443013FA
candidate SHA-256: 6E15139CFEB1E75772281683ABD0DF1B647309AEB610E1A5EA8E37F804E97B5B
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:737977
original SHA-256: 2E0210FFC63920536886A36377975C37BD03E08BBB1338E4C645E68272E9A5F3
candidate SHA-256: 9E876B8710780A14B3C74B7E5A9C3BFDE53F20CEF7B249ACEA785794583D14C1
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:738119
original SHA-256: EFEABC1C6DA05CEBDCC1813DA5B54787FFEC7361B8657F57D898E68D6E511B63
candidate SHA-256: EFEABC1C6DA05CEBDCC1813DA5B54787FFEC7361B8657F57D898E68D6E511B63
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_024_counter_v1/reading_packets_v1/expanded_train_738119_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:738412
original SHA-256: 0F98FEAD92C2351E9D50F3F7038481F7EEB5CB453014CDF4E3BE7D6D3BB2CC8C
candidate SHA-256: 0F98FEAD92C2351E9D50F3F7038481F7EEB5CB453014CDF4E3BE7D6D3BB2CC8C
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_024_counter_v1/reading_packets_v1/expanded_train_738412_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

