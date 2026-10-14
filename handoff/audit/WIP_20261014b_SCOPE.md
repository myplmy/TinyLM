# 2026-10-14 후속 source QA 확대 영향도·권한

| 경로 | 예정 동작 | 권한 근거 | 제외 |
|---|---|---|---|
| scripts/p106b_source_course.py·diag_p106b_source_course.py·test_p106b_source_course.py | 새선별/뷰/선택본문LM/같은학생두팔 구현 | 3개우선순위 모두 알아서 판단 회신·원7의17시전실측 | 기존제품/공용checker 수정없음 |
| 새run_P106B_Stage4u*/4v* SH·experiments.tsv·P106B계획/결과101/색인/기준/방법론/COMPASS | 계획/preflight·실행/회수·정본연쇄 | 동일현재우선순위위임·원7의절차준수 | old런처/old인계/old완료원장 불변 |
| HF/sft_ready/p106b_source_course_v1_s1337·evidence/local/...·새tag의runs/ckpt | 새출력만 | 원7의한정CPU/GPU/학습·기존원형불변 | 보호TinyDataset·oldHF/CPT·download/설치 없음 |
| 현재WIP/감사·최종새인계/한국어localcommit | 운영/증거 | 원7의절차와현재후속위임 | 삭제·push/PR·17시이후모델 없음 |

| 축 | 영향 | 내용 |
|---|---|---|
| 코드 | 있음 | 기존 SOURCE_IDS/parser/20MB writer/SFT pad/component·optimizer/load/probe를재사용하고 새자료/selected-reference LM wrapper만신설 |
| 데이터 | 있음 | 기존PUBLIC와val원형SHA·group/긴본문SHA split검산;새512+64source·2view/QA+자료요청·생각은sidecar |
| 테스트 | 있음 | 학생에게보이는참조/없는자료요청의producer명시계약·labels/LM분모·split/caps/budget 회귀;실제source/모델은별도 |
| 정본문서 | 있음 | 계획·결과·목록·기준·방법론·COMPASS·후속인계에교락/부족/효과/nativeretention 비용을분리 |
| 기술부채 | 제한 | 소형seed1·teacher pseudo labels·입력근거고정시의자료요청이고모든자연QA의의도추론분류가아님 |

A 자연근거512/64+필수자료누락view를우선한다. B 같은SFT에서선택근거본문LM .1을추가하여 보존대가를별도팔로본다. C route/폭구조는기존근거로유보한다. 양팔SFT노출/부모/LR/배치는같고 B의추가LM노출/목적/계산은변경축으로보고한다. 본75M×4목표를축소하거나단일시드σ를추정하지않는다.이점검은알려진설계실수만걸러낸것이고실제로는돌려봐야한다.
