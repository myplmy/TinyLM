# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:451895
original SHA-256: 4918B8283F90D8E3D17C23BFC81C6354CB7C9DF8BE7D9E3F6E99AA93DCEA8450
candidate SHA-256: 4B564E05DEB0377B5D64211C483CDBD7D1522E06E7D1F59512D4D1134F6E1738
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:452473
original SHA-256: B6951F003A15D5079D89AC6AD9B240E1E5F0B9AD89563674233595C11162309C
candidate SHA-256: 974C8F07AEE065538730BDAA4A2D8C3DD5A0E9FCF3912230E79415DA829C469C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:452515
original SHA-256: 481AD6C809256A6179F44ED72C00127268BFF9D000B6B85107A9797957EC7597
candidate SHA-256: 481AD6C809256A6179F44ED72C00127268BFF9D000B6B85107A9797957EC7597
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [2, 2]
원문 전문+최종diff 필수 패킷: [1, 2]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_017_counter_v1/reading_packets_v1/expanded_train_452515_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_page_017_counter_v1/reading_packets_v1/expanded_train_452515_0002.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:452536
original SHA-256: 8DA00D0C9910F78AAE01518B8F9F22606E430C43C192505760AC0ADAA06008FD
candidate SHA-256: 96C36B0B7FFDA00EDF0B3BE2B6DD07F3C0B51C32321B213F17E8B4256C13468B
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:453514
original SHA-256: 569330A1FF10DEDD97627672B4CC8827B45EBE7CA124E7049568EAF2B96D5096
candidate SHA-256: 30B87ED1F1E2EFC1418B0EE40329B66445A2241F3B63E4DB20DA6B4E57B771DC
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

