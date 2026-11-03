# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1028664
original SHA-256: F2CF37436424F0B7DC75371130E8A662208D01A94BD900BC05614B56CAE75BBF
candidate SHA-256: F10F40471BD99EF8D2673A60C906227A416E44DCFF6A935FEE5A5A3EFC173C79
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1028674
original SHA-256: FEE39C83ED16063C3A7264A8D221E537EFDF28E9E25621D8F449F3D9079BEE38
candidate SHA-256: 5FCAAE0CF1DC2C491995DD8914AA1E3EC3A24E43965C7F60EB608A0E6C68CA94
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1028723
original SHA-256: 248B30D23BE608BEB66BBEC85408A586C7F4670934B4D952BB08140278192E11
candidate SHA-256: CDE954A33691EBCF8DA2CAE2F0D7549307432CD06613885ED3F1DAFFC526B49F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1029046
original SHA-256: D29365438BD017B4AD726858D020797FBBC51A92F5EF070109917B10CAB68D37
candidate SHA-256: 0391C822608581F1A87A5B081B1184A8790CDEF52C1D556C83EE688F9064F1CE
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1029140
original SHA-256: FB133AB9AF6F7A0A0B11AB9A21EB1386CA573D88609F5DBBFB92A6E9A3AE7BE7
candidate SHA-256: FB133AB9AF6F7A0A0B11AB9A21EB1386CA573D88609F5DBBFB92A6E9A3AE7BE7
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [6, 6]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 6]
후보 중복만 있는 생략 가능 패킷: [4, 5]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1029140_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1029140_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1029140_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_075_counter_v1/reading_packets_v1/expanded_train_1029140_0006.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

