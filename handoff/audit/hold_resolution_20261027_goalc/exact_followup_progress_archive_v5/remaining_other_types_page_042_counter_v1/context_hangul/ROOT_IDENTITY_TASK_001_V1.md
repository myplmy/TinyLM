# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:515285
original SHA-256: 9872E2AA587AEE9144505914866B6940B72AC74A5D71599DE370E1EEAFE70244
candidate SHA-256: DEFF404E7932BBBD395C1AD493B9C0C804F8C00867F5C33B5DA0A0B3C4DF6794
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:515315
original SHA-256: A5AF0E2B0F447C51BF09FA7268CD619F59973CA977EDA55AF009B6A08D62C59E
candidate SHA-256: 9142CB1FDDBDCF6F86466C8503552DDF35713A9C63A8A788F3F1B8F52EA8578A
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:515381
original SHA-256: 68D73F8217256406BDE296B5E625C89F02288BD17BB595A33B6DC5CF807C466E
candidate SHA-256: 013981830B433FBDD33DCFC29DCAB24BF564D4BC4A8A911255FC31397A1E31C3
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:515465
original SHA-256: 3DFECE48160713B9BE20FE4213F5A45C9ED51AF327A9DB59A8947CE9604BEA49
candidate SHA-256: 249B9276CFDE5B70EFE6288341072E72190EA5E3150D020AE881895F56F73C7F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:515488
original SHA-256: B246230AD517F4EADBBF3989A951BB7B9CD7B6B30A47D16AEE23FF662DDE3FF0
candidate SHA-256: D764985C22EEB0AD8852EDB8508E9015079DF2E5D47C660C8D01D0EF9BD650EE
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

