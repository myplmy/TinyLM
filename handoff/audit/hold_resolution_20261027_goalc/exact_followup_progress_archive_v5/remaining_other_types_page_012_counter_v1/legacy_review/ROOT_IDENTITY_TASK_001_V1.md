# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:114169
original SHA-256: 566F50D4BB85D6C83A62E20868C4068B0C6D3C0FFE4D3C09E8F3A02AE5B5546A
candidate SHA-256: 3DE3583DF707E6DDC889FED90478A73EF2382BC915E3ADDC329284A625455405
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:114292
original SHA-256: 3EA38E7CABA3E6C3F6941C8606E5DF26E5334907793DF15609C786727B5A45E3
candidate SHA-256: 3EA38E7CABA3E6C3F6941C8606E5DF26E5334907793DF15609C786727B5A45E3
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_012_counter_v1/reading_packets_v1/expanded_train_114292_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:114295
original SHA-256: 1556580ACD212B2612507C1D903758B3095DCDF1409C676C56B818CE2328E5C7
candidate SHA-256: 1556580ACD212B2612507C1D903758B3095DCDF1409C676C56B818CE2328E5C7
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_012_counter_v1/reading_packets_v1/expanded_train_114295_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:114366
original SHA-256: 84BAE11F41B52768E0A9373A2DA535147DA96B0F46CD5FEA32A7955DCBE7DE23
candidate SHA-256: 87BBF9E27801E70049A76BC979A01636AA513FBA40A8E3A1DFAC5323418CDD27
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:114370
original SHA-256: 0E40105F2C6C0355342F3AFC4DDF09EB909E929DC55D6EC69454CCE007B7BF9E
candidate SHA-256: DD42E7F8B811F1D511ACFCA181F506F02065969E15541CA7958F480043DD5014
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

