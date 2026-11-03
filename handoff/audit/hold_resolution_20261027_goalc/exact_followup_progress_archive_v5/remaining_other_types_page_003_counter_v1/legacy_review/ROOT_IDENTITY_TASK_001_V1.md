# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:24073
original SHA-256: 778DC516EC706C05A14346C193C98BCFC56255354EC0A8329B81E01BE5EBB8C2
candidate SHA-256: 778DC516EC706C05A14346C193C98BCFC56255354EC0A8329B81E01BE5EBB8C2
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_003_counter_v1/reading_packets_v1/expanded_train_24073_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_003_counter_v1/reading_packets_v1/expanded_train_24073_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:24084
original SHA-256: 4049948C2A86D794ED974765F18BAC7A105225C56C66B8B174CF8CCECDB9CAAE
candidate SHA-256: A1154625864DB0B335422143228D74D473938032773EABC65187A2620B3745F6
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:24201
original SHA-256: 68FF419AC9C0E15B14B3A4691C4975CDE1A5C1FC92E97302EC5FF988003B29A4
candidate SHA-256: 68FF419AC9C0E15B14B3A4691C4975CDE1A5C1FC92E97302EC5FF988003B29A4
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_003_counter_v1/reading_packets_v1/expanded_train_24201_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:24213
original SHA-256: FD8A644CBC4897EE5322DE7EF0B29B2B1B1234C444C25655A9D37E50D614B6F5
candidate SHA-256: 05183746EDFC5F07BADF66569D7C49EB9D15091D7E8400F0AA34ED8F7D3B9B9D
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:24488
original SHA-256: 7D2703E6774C4A7DF78882F1056BFE43E6E298586A9B44B965201BB81A832288
candidate SHA-256: 983A62E1265FD4EAB5210F3A15CD9AC5782FACEEFE95940773A7776AEDFC9626
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

