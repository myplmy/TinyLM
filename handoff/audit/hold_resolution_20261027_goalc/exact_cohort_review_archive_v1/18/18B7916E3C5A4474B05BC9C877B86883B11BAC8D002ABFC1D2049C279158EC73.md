# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:112236
original SHA-256: 3A42EEBDFDE59DF01C234AF076C0EC783035B2DB185897E10E47874CE1A3239C
candidate SHA-256: 33098B80741ADDE4EBEB238ECDA4F0470E9BB2912B62277D2B21BF37EC68A222
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:112916
original SHA-256: B239EBBDEE6C83A1D9B3D012B0840B8E28D2D6A006791CF4FFD6D78EB50D83AA
candidate SHA-256: BBF2C6954CC7B1AE15D9BB93C0CD3CFD8D6BDAA76AA3769FE161B7A0912AE813
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:113011
original SHA-256: A4DA0EFBF380B035460144B551FA349A41A6AEDF4559C6C929BCF87714EF943C
candidate SHA-256: 798CE11591C11D77E09A8F7EF586FF2BA3F8761E7FFC1ADF504CC985DD352916
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:113981
original SHA-256: 7AF5CDD2F06C21C57B2CF725D8CBF8652811188832FE9F7FCB3C5B2E2CEF77EF
candidate SHA-256: 237AB6CC07E81FE069A7C3504022945081C70525082A6DBAA86221D3AE217502
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:114164
original SHA-256: 5CFF9A2B47B6E5877E6456DEBC5525B34E51D338E4EC6FD42E9341390C18BDF7
candidate SHA-256: 6CDB3CC8ACBB07214D13AF9AAFA4E7A40F6B94AAE0FD1535340C1CB0E113893F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

