# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:161183
original SHA-256: 9A1FB95E2D36966F7DAEB92D4CBA91786264B0FED427FFB43123245CA08D93C0
candidate SHA-256: 9A1FB95E2D36966F7DAEB92D4CBA91786264B0FED427FFB43123245CA08D93C0
원문 frame 패킷: [1, 36]
최종 full_diff 패킷: [72, 72]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 72]
후보 중복만 있는 생략 가능 패킷: [37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161183_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161183_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161183_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161183_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161183_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161183_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161183_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161183_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161183_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161183_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161183_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161183_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161183_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161183_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161183_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161183_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161183_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161183_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161183_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161183_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161183_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161183_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161183_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161183_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161183_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161183_0026.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161183_0027.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161183_0028.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161183_0029.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161183_0030.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161183_0031.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161183_0032.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161183_0033.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161183_0034.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161183_0035.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161183_0036.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161183_0072.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:161279
original SHA-256: 696E89BCCCC9DA288C8ACDAF767A94476C0808E4E64B166BB8F0CB9810BBF167
candidate SHA-256: 696E89BCCCC9DA288C8ACDAF767A94476C0808E4E64B166BB8F0CB9810BBF167
원문 frame 패킷: [1, 28]
최종 full_diff 패킷: [56, 56]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 56]
후보 중복만 있는 생략 가능 패킷: [29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161279_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161279_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161279_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161279_0004.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161279_0005.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161279_0006.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161279_0007.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161279_0008.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161279_0009.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161279_0010.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161279_0011.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161279_0012.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161279_0013.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161279_0014.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161279_0015.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161279_0016.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161279_0017.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161279_0018.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161279_0019.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161279_0020.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161279_0021.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161279_0022.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161279_0023.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161279_0024.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161279_0025.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161279_0026.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161279_0027.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161279_0028.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161279_0056.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:161321
original SHA-256: 19CBADE8563BC6B575F1C0B366D868B533B2DD0A32ACCB593AF79FEB7F8D9784
candidate SHA-256: A93DEAE841F6C2E3482380ADAC6673AE281DA2B7735469F5C0E9D6A9750FC28B
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:161598
original SHA-256: 8A4B6F8590B71994FE428FD5031A57EB81918BD28D0D1F430D4E861D7DB5CF65
candidate SHA-256: 8A4B6F8590B71994FE428FD5031A57EB81918BD28D0D1F430D4E861D7DB5CF65
원문 frame 패킷: [1, 3]
최종 full_diff 패킷: [5, 5]
원문 전문+최종diff 필수 패킷: [1, 2, 3, 5]
후보 중복만 있는 생략 가능 패킷: [4]
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161598_0001.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161598_0002.txt
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161598_0003.txt /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_016_counter_v1/reading_packets_v1/expanded_train_161598_0005.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:161696
original SHA-256: EA8ED15B9564E6568F1BB5389050318DC7FD2C725E40220EC991CC26C722EE3B
candidate SHA-256: CB9A5BFF5414DDE99220FFC49236AECFF4AB6A52F703F40607288E5B42E2D710
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

