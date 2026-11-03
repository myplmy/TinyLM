# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:10286
original SHA-256: AF8BA11ECCF6201034682058FE14A2CA31C0F8F10E40A4A971C2D98BD2D089C9
candidate SHA-256: 4128AB1743370DE678756D8A91F781DEB7BE31DDD6A17B478FDED72EDD69FBF8
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:10300
original SHA-256: 10E1CA6AF614E8826277F3F1AD854F53752173A59921FFA246842E1DCFAA7FD2
candidate SHA-256: F0B2764F74AB11C8123FC5050792C1CCBF31DFF22204E2CCDE1AB32CBC3321F3
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:10463
original SHA-256: DA1E0C50E718F4C7D457DEF4E49DF8D95E651BEC773F925187B27B31BC408CD4
candidate SHA-256: 7004C1006A3E12BFD3BC49CF9737C84985AA346740924986EA869E36E2A7C80C
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:10494
original SHA-256: BF9050AFAA032EAA956B9DE09FB66F558D164C99250A587CEA4920551481624E
candidate SHA-256: D1243ACF6ACCD862CD440E134C752C4F2AF9B67075E60EA0B32AB4C79D5613C0
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:10627
original SHA-256: D54A8AF2EB4288A0B1A1509F009D120CBEC13EB3AEE3B250BC2A022A492E4212
candidate SHA-256: D3374FDCB1E4A6074EB738DB57C40390DC94522F8A4003592B0490621C170194
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

