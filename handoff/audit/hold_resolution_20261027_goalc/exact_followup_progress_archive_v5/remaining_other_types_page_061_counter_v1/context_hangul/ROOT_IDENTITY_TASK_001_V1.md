# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:792482
original SHA-256: 62A59FE7B70D6BDB7F5D53564F830C7F34681FC09C32E17B1D0964F636683F20
candidate SHA-256: 62A59FE7B70D6BDB7F5D53564F830C7F34681FC09C32E17B1D0964F636683F20
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_792482_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:792655
original SHA-256: EDDE174F084B4D5F8258A71353EEA72DAF151F26F97C5036B2659742CF4378D0
candidate SHA-256: EDDE174F084B4D5F8258A71353EEA72DAF151F26F97C5036B2659742CF4378D0
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_061_counter_v1/reading_packets_v1/expanded_train_792655_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:792691
original SHA-256: ED5649D82E09FAA61D377159BB0FCF763DC06657ECDC3D4F955BA17D13D5FC17
candidate SHA-256: 7BE5D6B0D188845D1253CF390549EB5A1E28F300D08A089E26BFAB61F0C53499
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:792918
original SHA-256: F9C5A0922A63C6213F3992B888BDCD4334B1F3FFA58E57B41204E96C906EBA4C
candidate SHA-256: 6B36F515A8A83BC2255014C1136DF301CCDF31D0146B8880B145875B7F2EB407
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:793084
original SHA-256: B6B13761722FA813D2E53937E253748C133A6302A2669AC9DE1685571CF16D20
candidate SHA-256: 32C3304795CBFE864DAFDAA205B60BB851C18F8E03C3FDBE9E0AA5A9D89A1D93
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

