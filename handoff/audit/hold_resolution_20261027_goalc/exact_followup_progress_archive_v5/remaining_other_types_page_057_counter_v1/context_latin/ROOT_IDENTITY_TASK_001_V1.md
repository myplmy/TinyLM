# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:733635
original SHA-256: 678DE85DCD9029E0ED46770D967823C648A1B7CF86B690CB4B1C7205887428D6
candidate SHA-256: 9C9CE9F89EB7569670BA5ADF9379D48067C689B03383400F0CA1ACEFE655E561
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:733641
original SHA-256: 32C699DFC8844ACD68B1FA4167BDFDBB27010674477C6F60F6219A5883ECA6ED
candidate SHA-256: 09610A949E4F6E5F7D1650E0616BA5642A86374C083C7802E39DE1657373B841
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:733768
original SHA-256: 1DA0B46EB3F7555FE68BF2B944B5F51F609A5BFC670C37FE82AB950AFC1E960A
candidate SHA-256: F17C76D4D115C04AA80130881C1722F8B0E0EDEF2333530F5DDB61968103CB6E
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:733782
original SHA-256: 569E43612B1F3CD4BFDD563E2F2B3E61C8C5BCB46F80E8FAB050D98179B838D3
candidate SHA-256: 150EAC0E8A7C4741133AFC352FB8A83190D702DF3B1DFECD541E5967C3363BAF
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:733783
original SHA-256: F1A4AEB063328691942590F8B17E24C6B92E3CD031E8A1BF6DA590BCB704CCF0
candidate SHA-256: 9333796CF5C8C850FD23E96421C8C183800352469FC9EC740F67401C427E5702
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

