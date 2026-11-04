# 정확 입력 전문 판독 연결 TASK_018

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:304548
original SHA-256: 5B198582EF8220796E9214957CEA44B7177C65408407D9CBB5F309443D5D6CE9
candidate SHA-256: 122C122587B580080C33DD8AA8E2F502DA72DD647144FABCE65DDD90CE8895B8
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:304587
original SHA-256: 64BC889CF529A25D2681875228850C79408346BD1EFA4285083BFB6A762316F9
candidate SHA-256: 64BC889CF529A25D2681875228850C79408346BD1EFA4285083BFB6A762316F9
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_013_packet_v1.py --source-id expanded_train:304587 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:304876
original SHA-256: B72655A724EFA2AC8AB82B275D5F53CAC0CEB86240E972B2907AF93BAE86A2F2
candidate SHA-256: C6998B13CE257F3AA04F01CF18F9F7FF2F417B62885EB82CE5C1CCD39FA9BF33
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:305227
original SHA-256: E0633DE58695539B475E56B1ECB8F0445785D48F7B1C1B5E2292D5794D78B429
candidate SHA-256: E0633DE58695539B475E56B1ECB8F0445785D48F7B1C1B5E2292D5794D78B429
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
/home/uranus/miniforge3/envs/tlm_torch/bin/python -I -B /home/uranus/tinyLM/handoff/audit/hold_resolution_20261027_goalc/read_context_controls_field_page_013_packet_v1.py --source-id expanded_train:305227 --packet 1 --piece 1
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:305305
original SHA-256: 0DAC59B08B7D89AC33460130A93D76019D8BB4DD76BE36E83CFA443C2CDCD93D
candidate SHA-256: 1B1C3E8ADA27E1B16371BE5A2A6E6C63AC87662B552A67E0AB9D52B7E14CD13A
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

