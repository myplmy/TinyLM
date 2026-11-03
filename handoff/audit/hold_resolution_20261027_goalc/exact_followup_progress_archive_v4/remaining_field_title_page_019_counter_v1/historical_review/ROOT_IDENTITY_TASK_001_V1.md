# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:524678
original SHA-256: 4822EA6DA893CB6AD33D4353DBA046EBC458D82912D72BED7792AE5AF70C92B1
candidate SHA-256: FB17E64682F4D34373441598FD8D221B5034C979D35829B3F29F8E833297AB19
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:524900
original SHA-256: 883E72CA83AA76D54576C70D46A526D20CCDD5F1D2C1E6E816D9E05395C2FD18
candidate SHA-256: 883E72CA83AA76D54576C70D46A526D20CCDD5F1D2C1E6E816D9E05395C2FD18
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_019_counter_v1/reading_packets_v1/expanded_train_524900_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_019_counter_v1/reading_packets_v1/expanded_train_524900_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:525011
original SHA-256: B85352C62079BDB68BB4AB45BA65D62FD14AC25515C427B5AB22AB51A673C735
candidate SHA-256: B85352C62079BDB68BB4AB45BA65D62FD14AC25515C427B5AB22AB51A673C735
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_019_counter_v1/reading_packets_v1/expanded_train_525011_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:525416
original SHA-256: 211747AA224B8C47B0ABB0B8C8A72036478EF36DD27FB70C445752D8CC321EF8
candidate SHA-256: 234A80C932EA1F9AF36F4909C63942418B78CAB5A04CF2348CC1DC5F1B89CBD8
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:525794
original SHA-256: 244A4CC3ED6C0ECCC799AF012B125615BC7298311DEBB715A387FEFC35645174
candidate SHA-256: 244A4CC3ED6C0ECCC799AF012B125615BC7298311DEBB715A387FEFC35645174
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_019_counter_v1/reading_packets_v1/expanded_train_525794_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

