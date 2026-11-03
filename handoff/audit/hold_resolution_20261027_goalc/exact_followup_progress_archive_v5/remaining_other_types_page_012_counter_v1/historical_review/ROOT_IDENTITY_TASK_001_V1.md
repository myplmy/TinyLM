# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:114203
original SHA-256: 19E94EE3A51C16758A0A0FA6A9269A1507190F49BEF60207FE55858071AB4360
candidate SHA-256: 010258C15908CF023465F1D7152E87DBFB5A578D6E42E4BB41D41D929BB35753
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:114214
original SHA-256: 8039E0B3AE0263F0945A283D2B0173FE3BD8650929725BE7E38BB336EC48F8DF
candidate SHA-256: CBCF2A30B5F94534622EB810D52077DFD93F874DA5CDC20C159019443B2C5B56
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:114385
original SHA-256: 283063C0274E77D1C60DEFC1C329A7B729DE0F50C8C90043E3B943587509B7B6
candidate SHA-256: 85BC6B32418745B2D1F72CFFA3E70B0FD26D50B174A233B32F2E0EC4053F50AC
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:114426
original SHA-256: E2AA67167C07AA42E75BA8D161EBF11E40648699D8260D1F31D59E2250278C2D
candidate SHA-256: 99B9AC16BDECC92CFFB4B1D4E76014710ADC212132EECCBD3A64F7D26B36399D
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:114430
original SHA-256: 39B3F0CEB35B1901E2683C1FE6EC39ACA7D8143E0C0133BCDCEDDE60CC86BE89
candidate SHA-256: 036AD982D7C84A81E64BD84E521B70D9A673A171C83237C6F3AA00735A0F03FF
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

