# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:733655
original SHA-256: 5BBDF5C681EFD53D83A2E0DBBD07F4851238F7D2F79E409B9560A446B323CE86
candidate SHA-256: 72250BB65AA089722A4DA21A65CA0D1E46AFD7321FCC8BA8F95A0259D5C488FC
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:733826
original SHA-256: 94A4B2364F4BB8A6B8AD73C92A144483E25D348740E17BD85E52E5B939D7313E
candidate SHA-256: 29EDD5AC0F839792697A4A5630545D642A59E299E00B8BF9AA8C87B572B2BFCA
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:734004
original SHA-256: ECC907AAFAF0F10DF6E5E835F275A77F1D41AC76C2E1E87AAE9C4085D4D1CC9E
candidate SHA-256: ECC907AAFAF0F10DF6E5E835F275A77F1D41AC76C2E1E87AAE9C4085D4D1CC9E
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_057_counter_v1/reading_packets_v1/expanded_train_734004_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:734076
original SHA-256: BC1FA3C443695BCF30AA7FEB1142E523A272E2EA0AD0ECFB2B3342D7A4DBA1AF
candidate SHA-256: BC1FA3C443695BCF30AA7FEB1142E523A272E2EA0AD0ECFB2B3342D7A4DBA1AF
원문 frame 패킷: [1, 1]
최종 full_diff 패킷: [1, 1]
원문 전문+최종diff 필수 패킷: [1]
후보 중복만 있는 생략 가능 패킷: []
```bash
cat /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_other_types_page_057_counter_v1/reading_packets_v1/expanded_train_734076_0001.txt
```
실제 판독 기록: 원문 전문 실제 판독 + 후보 바이트동일 연결 + 최종diff 끝 확인.

## expanded_train:734406
original SHA-256: 53C1B14D14E6B6A73FE1549D9D1ADED31C5B4D950F31508D8A493D1866A3997E
candidate SHA-256: 20215B4BEA50011FB9DA45EEE403970FAB5DBED780CFC5DDB8F48EB1E417386D
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

