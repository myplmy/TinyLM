# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:1028609
original SHA-256: B1FAA0365C044136330B26173258743DD06CA92E87826E86497D56E9FE376125
candidate SHA-256: 6B28B0AA8E093FE8322CC84F3EB0B7683F5F19E38B971CE2A83C6D98CE595EAA
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1028617
original SHA-256: 9E28E4EA7F4D77ACE2B0E6E7A563B9981BF4C91B9E9331B85BC8DEE70A831FEE
candidate SHA-256: C2F31FF8E8250626A199AC849E788CFC228EB20348909985C6D22B96DEF3DA47
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1028626
original SHA-256: 29B6C4D7C33B723067942F0805C8482144EF91D864576D2504016379A1546819
candidate SHA-256: 96C0D3CF3BDA4EE10AEC0B17F3D041310B5A5CFBCACCF3D2831467439A5B0CE0
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1028643
original SHA-256: 3A717117E87DF6826B0F04B1C2565DC83589875BC8F9A9C4FDEB20EA6A860E49
candidate SHA-256: 631EF918374A6CCC321F18A7BFFFEA3F68EF7754794280A6E68003D550360A1F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:1029554
original SHA-256: E1B37BF11196F509DA618B9AF1032EBC4AC043C646532F5F512423F319D2AACC
candidate SHA-256: 391E97B80F3FADB5FD577B60C62490295A8D9FE462A963D23555F54F00E02BFD
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

