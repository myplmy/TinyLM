# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:873083
original SHA-256: E5103CEC368B46F19EE13DAB7AEC6C15C3ED874DE55920B9F9AA5C2131762B15
candidate SHA-256: 186E4162FD0C67165D46D8D4821524EFC5EA176E65ECACCD41EEEE1CA9A5C87F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:873544
original SHA-256: ABFD583C02F9CAE5DCFB21B7C98F2AEC313FD0D055EBD64D50B65ED0D27C46E1
candidate SHA-256: ABFD583C02F9CAE5DCFB21B7C98F2AEC313FD0D055EBD64D50B65ED0D27C46E1
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_027_counter_v1/reading_packets_v1/expanded_train_873544_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:874181
original SHA-256: 49751320156C51884CF0B330E000A1977B820225350B1E6CA9B1C698918493FB
candidate SHA-256: 0709024CE1DCEF02D393903507F4FC49964AF79226C5F79C88E015E185EEA182
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:875462
original SHA-256: 0D4D070D1F1C201A4A1869512D9CC6E60C8CE6F13FF5A468109B0C4F671CF2AF
candidate SHA-256: 921F7C595E851982C43117F139DA4799426C4FABA403AABE4A61D1F09C5117AE
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:875889
original SHA-256: A1F439187B4C4B682B5F4E22A1A6E3B55DAC7EDC82857459073B18AA43882F4D
candidate SHA-256: A1F439187B4C4B682B5F4E22A1A6E3B55DAC7EDC82857459073B18AA43882F4D
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_027_counter_v1/reading_packets_v1/expanded_train_875889_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_027_counter_v1/reading_packets_v1/expanded_train_875889_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

