# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:320193
original SHA-256: C2553BEE873E124C03EAC273CF17C93AD30F342BA7E69D37E8B88FCD226B72C4
candidate SHA-256: CAE7DF564BDD259EEDAB31E2956A0415F1D02E7BA170CF6DD650287AD3903C4D
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:320288
original SHA-256: B4D72861C8D6E05E3A5DD96DACB9D9A17B208C6959F888C3883693794A033672
candidate SHA-256: 4FFBEB1ABC04DED344C082D9CE7EFCCC4FE0B874FA2819121E7D20561A06A82B
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:320335
original SHA-256: 71CF4CA88F0127FCC2B73E7B657BE53B5F0BC881F2EE67F0CADB12741381C3F1
candidate SHA-256: 71CF4CA88F0127FCC2B73E7B657BE53B5F0BC881F2EE67F0CADB12741381C3F1
원문 frame 패킷: [1, 5]
최종 full_diff 패킷: [10, 11]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 10, 11]
후보 중복만 있는 생략 가능 패킷: [6, 7, 8, 9]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_028_counter_v1/reading_packets_v1/expanded_train_320335_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_028_counter_v1/reading_packets_v1/expanded_train_320335_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_028_counter_v1/reading_packets_v1/expanded_train_320335_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_028_counter_v1/reading_packets_v1/expanded_train_320335_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_028_counter_v1/reading_packets_v1/expanded_train_320335_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_028_counter_v1/reading_packets_v1/expanded_train_320335_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_028_counter_v1/reading_packets_v1/expanded_train_320335_0011.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:320500
original SHA-256: CFC2105FC15B42E48E54273831C26DAA47CCC7AB93E6F8ADB859F40869142DCD
candidate SHA-256: FFAD2B8AC8345B7E936009D2E37978DE865FC76E447CB182530B3A7CAB4F5581
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:320525
original SHA-256: 253DE52D123399EB59B473F1DC36B9590CD7A67E2800EC6DF1B9BEB4408E1F4B
candidate SHA-256: 253DE52D123399EB59B473F1DC36B9590CD7A67E2800EC6DF1B9BEB4408E1F4B
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_028_counter_v1/reading_packets_v1/expanded_train_320525_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

