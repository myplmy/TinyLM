# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:636441
original SHA-256: FC2B1ADF5A8D79F99786DF9795DF5776B92BF4CE446D67D03A9AAA0C0B186E02
candidate SHA-256: 1DF02D46C52259F66F220B7C45F44315550242A77B38330A528412013E06A302
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:636451
original SHA-256: 5CC350029C42B267DE7E21C650B608E669C31673694601157B007742BA983957
candidate SHA-256: 0807F148829D1C3B6C3A5701E4FEDB6554AA83CFBB203CAC093EB585041455C3
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:636497
original SHA-256: 0DA6DB8CB4D5EA14D4EF8EB918FB8994066EB15C001E587FF070B2B935373C6F
candidate SHA-256: 18E0C6AD8D1905D70EE371E3EAD745F7292ECCBBA244C423AF275B4469E0FC05
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:636572
original SHA-256: 119352AB6B22F9F76EBD2E5B0B43B83484277969072B5BA0E2CF8C8528C3B2AC
candidate SHA-256: 7A4C89DB86DFEEDCBD28B444F5E64F09C2D815515DC9D6D1DEF9DED7817DA1F3
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:636890
original SHA-256: 763721121F555253D707533565FE6A15A0EBDA4E393CE030121BA9B9762EF003
candidate SHA-256: D62050B66C8A583D51BE45D27B9E72EED024B41A04563BA900C38FAD5A76374A
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

