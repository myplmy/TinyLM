# 최종본 문자 변경 판독의 고정 범위와 비용

F3: (A) 기존 줄 단위 unified diff는 긴 문단 전체를 반복 출력한다. (B) 이미 읽은 원형→후보와 저자가 적용한 패치만 합치는 방법은 최종 파일 SHA에 대한 독립 재구성 확인이 빠질 수 있다. (C) 고정 배정·guard6·원형/후보 SHA와 본인 최종 TXT의 exact SHA를 묶어 문자 범위와 앞뒤 64자만 출력한다. C를 적용한다. 원형을 이미 읽은 뒤의 최종 확인 도구이며 최초 전문 판독을 대신하지 않는다.

F4: scope6/core3를 그대로 재사용한다. role/cohort/ID 배정과 원형·후보·최종 SHA 제한은 어떤 본문을 열기 전에 확인한다. 최종 파일은 자신의 agents/role/cohort 안 exact ID의 TXT basename만 허용한다. 타 역할·페이지·ID·상위 경로·symlink·제한 SHA는 거절한다. 최종 파일 수정과 코드 실행은 없고, 원형과 최종을 실제 바이트로 검증한 뒤 고유 토큰 anchor와 작은 문자 변경 범위로 최종 UTF-8 전체를 재구성한다. 큰 비정형 변경은 숨기지 않고 전체 변경 범위를 페이지로 출력한다.

`final` 뷰는 최종본 전문, `changes` 뷰는 원형 대비 모든 변경 범위와 원문 문맥이다. 각 뷰 4KB/part·한 번에 최대 3part이며 최종 SHA에 묶인 EOF/next_part를 반환한다. 이미 출력된 part를 다시 읽어 최초 처리량으로 세지 않는다. 기존 full pair EOF 증거는 재사용하고 마지막 수정 뒤 final/changes EOF를 확인한다. 기존 완독 ID는 도구 시험 때문에 저자가 재독하지 않는다.

실제 이미 완료된 349488의 CPU 비교는 새 원문 전문 표시와 최초 판독 실적 0으로 수행했다. 원형 100834B unified diff와 같은 최종본을 정확히 재구성하는 91개 문자 변경 뷰 41541B를 얻었다. 4KB 프레임은26→11이다. 이 수치는 해당 한 문서의 출력 비교이며 전체 처리 속도나 의미 검증 완료를 뜻하지 않는다. 초회 unit fixture는 trusted_metadata 누락으로 실패했고 V1 로그를 보존했다. 보완 후8시험이 통과했다.

다섯 고정 shortcut은 tmp/hold-{c,l,h,j,g}-field-final-review-v1이다. 인자는 PAGE ID FINAL_BASENAME FINAL_SHA256 final|changes FIRST_PART COUNT1..3이며 자신의 role은 고정한다. 본문 사본·새 원형 캐시·자동 채택은 만들지 않는다. 목표 완료와 학습 승인은 false다.

저자 직접 해시 계산 금지는 유지한다. 새 `tmp/hold-{c,l,h,j,g}-field-final-identities-v1`만 본인 신규 작성 TXT의 metadata 조회로 허용한다. 인자는 PAGE ID1 FINAL_BASENAME1부터 최대5쌍이다. 전체 ID의 배정과 원형/후보 제한을 먼저 확인한 뒤 자신의 agents/role/cohort 안 exact ID TXT만 읽어 SHA·바이트수를 반환한다. 원형·후보 payload 열기0, 본문 표시0, 쓰기0이다. 생성된 TXT의 SHA를 처음 얻는 별도 identity 단계이며, 제한 SHA와 일치하면 표시하지 않고 거절한다. 그 반환 SHA를 final-review에 넘겨 이후 원형/최종 payload 검사를 고정한다. 직접 sha256sum·임의경로 해시·ROOT 개별해시 회신은 사용하지 않는다. 4개 identity 시험 통과 및 실제349488의 고정CLI SHA가 기존 CPU회귀 proof와 일치함을 확인했다. 완료ID 저자 재독이나 최초 판독 credit은 없다.

G426845처럼 전문 판독을 마친 후보로 새 최종 파일을 시작할 때는 `tmp/hold-{c,l,h,j,g}-field-prefill-v1 PAGE ID1 NEW_FINAL_BASENAME1`부터 최대5쌍만 추가 허용한다. 모든 배정·guard6·양 원형/후보 SHA·미존재 출력 경로를 선검사한 뒤 pinned candidate 바이트만 검증하여 본인 새 최종TXT를 xb로 생성한다. 원형 열기0·기존 파일 덮기0이며 별도 initial 사본은 만들지 않는다. 이는 코드의 의미 편집이 없는 초기화이며 실제 정제 편집은 해당 저자가 한다. 이미 있는 본문을 복제하는 버전 증식용으로 쓰지 않는다. 4개 전용 시험으로 경로·제한SHA·후보변경·덮기 방지를 확인했다.

L348434의 직접 sha256sum 사용이 금지 안내 직전 뒤늦게 보고됐다. 본인 출력 파일 해시였으며 이미 final/changes EOF로 확인해 재독하지 않는다. 이 권한 범위 이탈 기록은 보존하며 이후 모두 고정 identity 경로만 사용한다.

ACCEPT_CANDIDATE/KEEP_SOURCE는 새 파일 수정이 없으므로 최초 pair 전체EOF와 정확 입력SHA를 최종 근거로 재사용한다. 이 두 유형에는 prefill/identities/final-review를 추가 호출하지 않고 reader header의 정확 입력 경로를 리뷰에 연결한다. prefill은 전문 판독·판정을 마친 REVISE_TEXT ID만 묶는다. C374913은 판정전 prefill로 불필요한 TXT가 생성됐으나 미편집·미선택으로 남겼고 정확 candidate를 선택한다. 삭제나 완료본문 복제를 새로 승인하지 않는다.

짧은 REVISE_TEXT 최종본은 새 `tmp/hold-{c,l,h,j,g}-field-final-task-batch-v1 PAGE ID1 FINAL_BASENAME1 FINAL_SHA1 ...`에 최대5쌍이 아닌 **5개의 ID/이름/SHA 삼중항**을 넘긴다. identity가 돌려준 final bytes가4000 이하인 파일만 대상이다. 모든 배정·원형/후보/최종 제한SHA를 선검사하고 최종 전문+모든 문자변경을 통째로 출력한 ID만 completed_final_and_all_changes_ids에 넣는다. packet8000B/본문12000B/전체18000B 한도를 넘은 ID는 미출력으로 남기고 기존 단일 final-review를 각view part1부터 사용한다. 일부 프레임을 완료로 세지 않는다.

7개 전용 시험과 실제C의 이미완료5개에서 기존10회(5전문+5changes)와 새1회의 전체10view 바이트/양EOF가 일치했다. 실제출력14645B, CPU subprocess 범위1.93초→0.25초이며 전체작업속도배율을 주장하지 않는다. 도구시험은 원형/최종 본문을 모델에 표시하지 않고 최초판독credit·본문사본·원형변경 모두0이다. 작성자는 완료ID를 시험재독하지 않고 다음미완부터 적용한다. 바깥functions.exec max_output_tokens20000과 안쪽exec_command16000을 함께 사용하며 한블록에 본문출력 하나만 반환한다. 모델 잔여문맥 자체가 부족한 경우는 이 한도만으로 해결됐다고 주장하지 않는다.
