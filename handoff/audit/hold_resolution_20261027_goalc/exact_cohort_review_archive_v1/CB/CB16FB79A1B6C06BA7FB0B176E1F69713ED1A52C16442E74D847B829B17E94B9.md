# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:308030
original SHA-256: A6BE149EFBCC6E98FD599656475C23A36EA6A40085515080E7C82E92A51E5819
candidate SHA-256: B4DB89BB33FAB17CE9B9BC6FCD6E2BFB87A5408DE06F089D212200D9D6DF2EB4
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:308671
original SHA-256: 5DDB1DC17E3B71896F326B52D4D83446567C9F0F3892F2C630E9BD892A622958
candidate SHA-256: 5DDB1DC17E3B71896F326B52D4D83446567C9F0F3892F2C630E9BD892A622958
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_014_counter_v1/reading_packets_v1/expanded_train_308671_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_014_counter_v1/reading_packets_v1/expanded_train_308671_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_014_counter_v1/reading_packets_v1/expanded_train_308671_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_014_counter_v1/reading_packets_v1/expanded_train_308671_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:308698
original SHA-256: 71056E4E915D7B59C46F6804DF1B763C81A4D1992D11F5877E0B1F7425E8C917
candidate SHA-256: C8BCF2BF6480F198F95C4F4B6D355A2B30783885EB7421B815EFD86BDE35AA35
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:308978
original SHA-256: C3A97258EA89B04B0225D96AED9C93D369EDDA3FC951F5E230692773894D2C7A
candidate SHA-256: 17530AE7E10929B6D4D2458F50AE752F22A2F3FCA1496877901285050589063C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:309065
original SHA-256: FC36BC43827D486779ED142C4822A7AB6DCCB254734401A82A059C62B66A9814
candidate SHA-256: F5A125CA0CCE2D8C40556EE38FA2EBE649D00530440A308ACA349FEE7724BC05
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

