# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:50569
original SHA-256: EC0889317CFB07B7A79834B6402E76A6D142F0797B76C328270921584B380B3D
candidate SHA-256: EC0889317CFB07B7A79834B6402E76A6D142F0797B76C328270921584B380B3D
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_005_counter_v1/reading_packets_v1/expanded_train_50569_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:50573
original SHA-256: 17DD74871C43E03FE6819D1A92394B205F481A7AC758E1CAFAAF701FB5EE382A
candidate SHA-256: 9D84E0DD1FFFD537176256629B1CE12BB9340D4C3DC586CE72574B5A83491F60
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:50582
original SHA-256: 777B0B25CF08714C6979B7663CA4DC5E78D8D02B828194A956F3E622914455D0
candidate SHA-256: 777B0B25CF08714C6979B7663CA4DC5E78D8D02B828194A956F3E622914455D0
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [10, 11]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 10, 11]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8, 9]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_005_counter_v1/reading_packets_v1/expanded_train_50582_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_005_counter_v1/reading_packets_v1/expanded_train_50582_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_005_counter_v1/reading_packets_v1/expanded_train_50582_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_005_counter_v1/reading_packets_v1/expanded_train_50582_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_005_counter_v1/reading_packets_v1/expanded_train_50582_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_005_counter_v1/reading_packets_v1/expanded_train_50582_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_005_counter_v1/reading_packets_v1/expanded_train_50582_0011.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:50690
original SHA-256: 175E79DFFFB40549C136538C544643D15AD67ECAB23DA557B7CA0220B70461F4
candidate SHA-256: 93052C6B37DD072DB05946CE4A5FA05D3082B2E831F7671083F1A59AD3058F89
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:50773
original SHA-256: 37510E62D0F5DBF8DCA7C4B0AEED0AFF2C776ACE2F4EF8AB9857550BDEF5E745
candidate SHA-256: 3DA5BB2102B8797CC0735E18C7B6E511AE740EC3B5D27A13486FB3F240C81889
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

