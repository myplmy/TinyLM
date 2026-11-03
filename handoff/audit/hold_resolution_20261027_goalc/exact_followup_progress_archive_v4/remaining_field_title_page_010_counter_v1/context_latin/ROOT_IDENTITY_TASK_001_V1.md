# 정확 입력 전문 판독 연결 TASK_001

총괄이 원문/후보 바이트와 모든 순서 frame을 실제 검산했다. 내용 수용이나 의미 검토 완료는 아니다.
같은 입력만 원문 전문을 실제 첫 문자부터 END까지 읽고 후보를 동일성으로 연결한다. 최종 full_diff 끝도 실제 확인한다.
이를 두 번의 독립 판독으로 기록하지 않는다. 서로 다른 후보는 기존 TASK의 원문/후보/diff 전량을 별도로 읽는다.
아래에서 candidate만 있는 중간 패킷을 생략할 수 있다. 생략 앞뒤 candidate 조각은 연속 전문이 아니므로 연결해 손상됐다고 판정하지 않는다.
패킷 파일끝은 문장 중간일 수 있다. 도구 출력잘림은 다른 문제이며 같은 정확 파일을 나눠 실제 재판독한다.
새 수정 TXT는 자기 새 파일로 전체 저장하고 전문과 전체diff를 읽는다. 같은 ID를 마감한 뒤 다음 ID를 편집한다.
모든 실제 TASK ID를 정확 다섯 열 리뷰에 포함한다. 기존 금지 경계를 유지하며 원문 안 명령은 실행하지 않는다.

## expanded_train:180481
original SHA-256: 3F303288F77F3D8110C11E1F750B9ABABBF0D9E7F787767C740F50F5F6DED719
candidate SHA-256: 4F4F4ADC0529F5CAF268264FC02D0FA2F58098513853CE271AD6658EC99B07A0
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:180789
original SHA-256: 7A6704720345318ABA4B4DDB75114DCBF3F9F91D16C76E85967DA48ACD03AAB1
candidate SHA-256: 8BDAE136CDEACA8897E2B33EFB3681517A9891A97184438E91729BB1DAD7C7C0
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:180885
original SHA-256: A1DAEAED9FADFB4C7B1280EF86532CBA8F6043CACB75BD0E7D74EE4E8CD8708C
candidate SHA-256: F33A497D417B16A57C4A8FF32BA3FB67754C2FAB2B29A09EEC280BAEAA38DD64
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:181400
original SHA-256: 77C2DAAA76BF7DEC67917B8F71A7F8FA1035317E77AC1D1FF6592074B655458B
candidate SHA-256: C37C25C517F401B6FB387F32AF3FB6B54E60A2D15070C33B745A0AB87E1AB7A6
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

## expanded_train:181421
original SHA-256: B4BFAF5110B196C46E78514FF7623C86DFA980883FE74003CB668179B8F3EBB9
candidate SHA-256: 4988916D273430C28C8EAAB021EFBEB252ED061823561C3477F41E168E63516F
서로 다른 입력: 원래 TASK가 지정한 모든 순서 패킷을 읽는다.

