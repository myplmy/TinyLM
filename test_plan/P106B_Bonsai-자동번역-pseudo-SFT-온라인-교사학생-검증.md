# P106B — Bonsai 자동번역 pseudo-label SFT와 온라인 교사·학생 연결 검증

> **현재 2026-10-17 최종 야간 회수 §244~270:** 본비교8팔·6,761업데이트와실제원답/보존/공통MC·최종/DEV를회수했다. 고유32k·추가원문·본문/일관성은부분이득/퇴행이있어전역승자미채택이다. 부모64·같은지시필드순서·질문묶음10라벨/9가중치·질문조건부우도2모델을독립검산했다. source우도정보와실제답을구별하며우도진단자체의새학습/교사호출은0이다. 최종스모크44/실패0/오류0/계측0·기존합성123파일불변. GPU는07:55종료했다. 옛6전량/질문앞학습/고유V1 HOLD와새capability75M부족은유지한다. 이하날짜별‘현재/최신’은당시기록이며옛v3 300M교육완료와새목표미완을구별한다.

> **당시 2026-10-16 회수 §194~215:** 역할교량/정보복구와SFT/ORPO 양64회·실제새128대화·표현192답을회수했다. 역할조회/보충뒤개선은있으나자연QA·갱신/언어보존은부족하고전면승자미채택이다. 같은정보에서질문표현0/3의차이를확인했으며원답/오답은보존한다. 아래날짜별‘현재/최신’은역사다. 옛v3의300M교육§54~55는실제완료했고, 새capability75M/300M확보·승격은별개로미완이다.

> **현재 본경로 선결:** 남은옛v5/v4/OFF/V2의14개live런처는해당버전75M/quota·원래과제/학습자가보는근거정책·wire/정확자식의선결이남아이번인계에서HOLD다. 파일존재/자동READY는실제실행가능증거가아니다. 현재짧은후속의성공/실패를옛버전의선결통과로대체하지않는다.

> **현재 회수 2026-10-08 §67~§70:** 저장epoch180/native5 완료·계약0/26/nativeepoch1부터악화, Gemma라벨16/16·소형MTP 가속과원문16후보805x를회수했다. 사용자A 과제관리/학생JSON/3턴상태·가족분산을새4iWc→4iWd로준비한다. 이하 이전 ‘현재/최신’은당시역사이며새75M/300M은아직NOT_RUN이다.

> **현재 회수 2026-10-07 §61~§64:** epoch 복구는 부모36계승/native 후 저장형의 n_layers 파생속성 거부로9·새답0이었다. 재고40집단/320표본과 Gemma 자산SHA는 완료, 실제16응답은 MTP decode70.070→139.135tok/s이나 옛 필드 off3/8·on1/8로8이며 후속자료0이다. 사용자 A의 시작 라벨·코드 래핑과 실제cfg 복원을 새4eWc/6dWb/4iWb로 준비했다. 이하 이전 ‘최신/미실행’ 문구는 각 실행 전 역사이며 현재는 끝의 새 회수 절이 정본이다.

> **최신 회수 2026-10-05:** [결과101 §47](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md). Stage5a 자산MATCH·5b MTP16요청을 정상 회수했다. 현 xhigh/nmax2의 decode는65.959→53.526tok/s·추가GPU897~900MiB로 기본 가속 채택하지 않는다. 본학습/LoRA/후행검토의 세 종료8은 각각 자료·실제거부·상류자료 선결로 실제 실행0이다. 사용자A로 P106B 단계/최종판정과 check-only를 보강하고 새 Stage4cWc/5cWb/5dWb/5eW를 준비했다. 기존 교사·학습 기본값은 불변이다.

> **최신 회수 2026-10-01:** [결과101 §37](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md). nW/n0W/iWf/iWg/jWd/kWd/lWd/mWd 모두 실제 종료0·xhigh교정128행·두학생각4update를 완료했다. SFT CE는 낮아졌으나 native CE악화와 실제 질문반복이 남았다. 뒤의 9/30 배너는 당시 역사이며 현재 교육0 주장이 아니다. 승인된 온라인/후행 분리·무입력·원답보기와 재승인 대기 분류/유사도/지표를 아래 후속에서 구분한다.

> 제안 계기: 사용자 2026-09-27 지시와 추가 질문. [P106 검증형 교사 계약](P106_검증형-교사-정답-계보와-SFT-첫게이트.md)은 독립 검증된 정답만 `ACCEPT`로 부른다. **일반 SFT 데이터가 모두 참이라는 보증은 없고, 전수 사람 승인은 기술적 학습의 필요조건이 아니다.** 이 계획은 P106의 검증형 주장·기존 결과를 고치지 않는 별도 `B` 축이다. 교사 자동번역을 곧바로 학습에 쓸 수 있는지 한정 실험하되 이를 `PSEUDO_UNVERIFIED`로 표시한다.

## 1. 왜 — 질문을 두 개로 나눈다

> **2026-09-30 최신 iWd~mWc 실행 회수:** [결과101 §36](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에서 교사7요청 중5건은 완결됐지만 한국어 다중답의 입력 질문 오조어와 새 오조어가 선별에서 거부됐다. 기존 질문 문자열 보존 지시와 내용검사가 충돌했고 retry는 실제 문제 문구를 알려주지 않았다. 전체96 교정·두 학생 교육은 선결8로 **NOT_RUN**이다. 사용자 승인 A에 따라 질문의 의도 보존/오조어 수리와 위치별 피드백을 구현하고, 새 v32에서 소형 배선과 전체 내용 문턱을 분리한다. 사고8,192·총출력16,384·문맥32,768의 같은4문항 low/medium/xhigh 12요청 대응 시험부터 진행하며 설정은 사용자가 고른다. 옛 유효 음성·B 부모 기준선은 그대로 보존한다. 새 실행은 아직 사용자 **NOT_RUN**이다.

> **2026-09-30 h~m 실행 회수:** [결과101 §34](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에서 B 부모평가는 완료했지만 고정8질문×3시도 전부 답/형식미달(0/8), native4prefix도 반복을 보였다. 실제 B 학습캐시의ChatML ID3/4는train597.995M/val3.005M에0회다. C는미등록변환enum·writer/reader 경로불일치로종료9, 후속j/k/l/m은선결8·모델/교육0이다. 기존v29원본을보존하고 사용자 A선택의 **기존B관측 기준선 유지→작은C4프로필→전체C→B/A**를새v30·새단계로준비했다. GPU복구/교육은NOT_RUN이다.

> **2026-09-30 11:34 실행 회수:** [결과101 §33](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)의 새 smoke43/0/0/0 뒤 Stage3fWb는 단일 슬롯 교사42요청·신규64행+보존64행/실제대화24,187·지도17,110·optimizer1을 완료했다. checkpoint0이므로 새 교육은 원래 부모에서 시작한다. 형식 재시도는6개 task를 회복했지만 고정16답 부분검토에 일본어 혼입·부자연한 한국어가 남았다. 사용자 **C 자료교정→B chat32 부모 우선·A 기존 학생 대조**를 승인했고, B 부모의 데이터·학습 여부·실제 답안을 먼저 평가하도록 요청했다. 아래 Stage3hW~3mW의 코드·런처를 준비하며 모델 실행은 사용자 소유다.

> 2026-09-30 최신 회수: [결과101 §32](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)의 새 smoke43/0/0/0 뒤 A1b 두 슬롯은 유효자료 속도비0.951/1.056×·수락행 감소·한국어11/16으로 **음성8**이다. A2b 한 슬롯 생산·소비는 같은 28행을 두 팔에서 처리하고 실제 시간구간 겹침·부분 optimizer를 확인해 **기능 PASS0**지만 cold compile/고정순서 교락으로1.188× wall은 인과 가속이 아니다. 과거 C4 100행4pass의 base full-val+0.018444 악화·고정 첫 답0/8(재시도 없음)은 유지된다. 사용자 선택 C로 A1을 요구하지 않는 새 Stage3fWb **기술 배선 1업데이트**만 준비한다. 교사는 모델카드 thinking sampler와 라벨형 질문·답2개를 쓰고, 코드가 원본/JSON/ChatML을 래핑하며 새 단계에서만 최대3회 형식 재시도·원본 보존한다. 통합 실물·품질·formal SFT/300M은 NOT_RUN, Wh/Wf는 -hold다.

[결과098 §8](../test_result/098_20260925_P106-검증형-교사-레코드-계약만-통과했다.md)의 full-GPU Bonsai+P076 모양 학생 두 팔은 **합성 입력 2업데이트 자원공존**만 확인했다. 실제 교사 문자열이 학생의 canonical ChatML assistant-only 손실로 들어간 증거는 0이다. [공개 SFT 적격성 결과096 §10](../test_result/096_20260925_P090B-공개원천-구조후보-SFT-보류.md)는 전체 공개 v3의 `TRAIN_READY=false`를 보존한다. 그렇다고 모든 교사 번역을 사람이 전수 승인할 때까지 **별도 소형 pseudo-label 기능 실험조차 금지할 근거는 없다.**

이 계획은 먼저 `교사 출력 → 자동 형식/민감정보 필터 → 학생 loss`가 실제로 작동하는지만 잰다. 그 뒤 한국어 대화·지식 향상을 주장하려면 원답/번역 정합·오염·동일 부모 대조와 독립 평가가 별도로 필요하다. 교사 자신의 답이나 `verifier_origin` 필드만으로 진실을 보증하지 않는다.

## 2. 질문

| # | 질문 | 왜 중요한가 |
|---|---|---|
| Q1 | 고정 OASST2 영어 단일턴을 Bonsai 2 27B가 구조화된 한국어 질문·답으로 시간·VRAM 한도 안에 바꿀 수 있는가 | 27B는 thinking 모델이라 짧은 출력상한이면 답이 중간에 끊길 수 있음 |
| Q2 | 검증되지 않은 번역을 `ACCEPT`로 오기하지 않고도 P076의 legacy32 학생에 assistant-only SFT 손실이 흐르는가 | 사용자가 요구한 직접 교사→학생 교육의 첫 실동작 |
| Q3 | micro8×accum16/activation-checkpoint ON으로 full 교사와 공존하며 적어도 2업데이트를 끝내는가 | 종전 합성 토큰·ctx512 gate를 실문장·ctx1024로 확장 |
| Q4 | 작은 자동 번역 pilot의 출처·중복·오류율·비용이 어느 정도인가 | 본학습/품질 승격의 선결; 한 팔의 CE 하락은 지능 개선 아님 |
| Q5 | 같은 고정 문항에서 기존 P076 학생과 pseudo-SFT 후 학생의 정답·오답 유형은 어떻게 바뀌는가 | 교사 학습 결과를 원답안·문항별 회귀로 직접 확인하되 교사 단독 인과와 구분 |

## 3. ★예측 — 성공과 실패를 둘 다 등록

- 구조화 한국어 번역이 일부 가능하고 학생 손실 배선은 통과할 수 있다. 그러나 공식 [Bonsai 2 안내](https://github.com/PrismML-Eng/Bonsai-demo#thinking)는 사고 토큰이 먼저 나오는 모델이라, `max_tokens=768`/ctx1024/medium에서도 완성 JSON 비율이 낮거나 비용이 클 수 있다. 이 경우 `exit8`은 유효한 제한조건 음성이지 코드 오류가 아니다.
- 독립 검증 없이 번역을 바로 학습하면 문맥 생략·잘못된 번역·의미 추가가 학생에 전달될 수 있다. 이는 **금지할 수밖에 없는 실행 오류가 아니라 측정·관리할 데이터 소음**이다. 따라서 자동 구조·PII/숫자 보존 필터, 원문/번역 별도 저장, 사후 표본검토를 두되 0% 오류를 주장하지 않는다.
- 16개의 짧은 대화를 반복해 2업데이트하는 Stage1b는 배선·VRAM·비용만 측정한다. 고유 진단 체크포인트를 남기고 Stage1c에서 같은 공개 문항을 재평가하더라도, 작은 노출에 따른 큰 분산/망각 때문에 지능 향상을 예측하거나 주장하지 않는다.

### 3.1 2026-09-28 예측 대조 — 형식 회복과 배선은 확인, 온라인5회는 미완

단순한 태그형 출력은 고정16에서 15건, JSON은14건 완결했으나 **1건 차를 일반적인 형식 우위로 채택하지 않는다**. 소형 학생 배선 Stage2gW는 실제2업데이트·유한 손실/gradient와 새 checkpoint를 만들었지만 13행 반복의 train CE 하락이라 지능 향상 예측의 근거가 아니다. 예상하지 못한 Stage2fW의 **PEG native-format HTTP500**은 독립 단일문항에서도 재현됐고, parser 우회는 `length`/중복 태그 때문에 교육 답 회복이 아니었다. Stage2iWa는 서버500과 원천 수락률 부족으로 optimizer0/5였다. 따라서 ~~형식 gate 뒤 현재 유한 source로 바로 온라인5회 처리율을 잴 수 있다~~는 낙관적 경로를 철회하고 Stage2fWb 보충→Stage2iWd 한 업데이트 기술 게이트→사용자 확정 다원천 C안의 새 계보/권리·실제 토큰 예산 순서로 바꾼다.

2026-09-28 사용자 [Stage2kW/Stage2fWb 결과101 §23~§24](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md): source 계보 read-only census 87,361 job은 독립 실행으로 재현됐다. Stage2fWb의 누락7 job 보충은 한국어14/16·영어15/16 **형식** 후보로 각12/16 문턱을 통과했다. 다만 case26 한국어의 native PEG500은 새 seed에서도 두 번 재현됐고 학생 교육/품질은0/`NOT_RUN`이다. 따라서 Stage2iWd의 기술 1업데이트 선결은 열렸으나 교사 완전성, 한영 5:5, 5회 및 300M~600M 확장은 열리지 않았다. 유효하게 등록된 `HOLD` 문항을 문턱 통과라는 이유로 조용히 수락하지 않는다.

2026-09-29 [결과101 §25~§28](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md): Stage2kWb 공개 작업표10,528개가 실제 생성됐고 Stage2iWd low는1업데이트, Wb none은5업데이트를 완료했다. 그러나 Wc medium은 **4회 뒤 한국어 원천365개 소진**으로 5회 문턱에 실패했다. 앞서 “현재 유한 source는 5회에 부족할 수 있다”는 예측이 medium에서 확인됐고 none에서는 예상과 달리 수락률이 높아 5회를 끝냈다. 두 팔의 context·출력상한·sampler가 달라 사고 강도 단독 원인을 주장하지 않는다. none/medium manifest의 GDN false는 잘린 서버 오류 버퍼에서 유도한 **무효 계측**으로 교정한다. 어떤 팔도 checkpoint/held-out 품질을 만들지 않았으므로 300M~600M 실질 능력 가설은 아직 열려 있다.

## 4. 단계 설계 — 싼 것부터

### Stage2iWg→Stage2iWh — 새 공개 low·VRAM 계측 수리 1회→5회 (Wg 기술 완료, Wh NOT_RUN)

앞선 **OASST1 low1 Stage2iWd**는1 optimizer·128답·약76.8분에 완료됐으므로 그 조건을 다시 반복하지 않는다. 이번 **공개 Aya Dataset/OASST2 대응 concept5,015개/언어**는 다른 원천이며, We에서 발견한 `nvidia-smi TimeoutExpired`의 sampler fail-open과 Ctrl+C의 `PARTIAL/not_started` 기록 결함을 고친 실물 경로가 새 검증 대상이다. Wg는 `--effort low --variant publiclow1`·thinking sampler(temperature1/top_p.95/top_k20/min_p.05/presence0/repeat1)·ctx3072/max2048, 학생 P076 mean SHA·legacy32·micro8×accum16/ckpt-on·compile를 고정해128개 fresh target/1 optimizer까지만 실행한다. We medium과 원천·context·sampler·실제 적용량이 같지 않아 단일 사고강도 인과 비교로 쓰지 않는다. [모델카드](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf#best-practices)의 low 미지원/xhigh 유사 주의가 있어 작은 실측 없이 저비용을 보증하지 않는다.

`sample_memory()`는 query timeout 등 계측 실패를 공유 원장에 기록하고 다음 teacher/forward/backward/optimizer 경계에서 **tool fail9**로 중단한다. 처리 중 HTTP는 반환/기존120초 timeout까지 기다릴 수 있다. free<512MiB는 자원 음성8, Ctrl+C는130, source/상한 소진은8이며 각각 partial manifest에 status/reason/phase/pending ID/실제 적용수를 남긴다. 샘플 스레드 실패를 CPU regression에서 주입해 **5/5 테스트**했고 launcher self-test에도 timeout 검출이 있다. 이 정적 통과는 실제 WSL GPU monitor가 안정적이라는 증거가 아니다.

Wg는 새 `v17_online_public1_low/`, Wh는 별도 `v18_online_public5_low/`에 원형·canonical·SHA를20MB 이하 write-once 저장한다. **기존 v15/원본 runlog 삭제나 덮어쓰기 없이** 새 단계로 재시도한다. 실제 템플릿 입력토큰+2048+128≤3072 조건을 만족하지 않는 행은 원문 절단하지 않고 초과 사유로 남긴다. Wh의 모델 로드 전 gate는 Wg의 **동일 public deck SHA·부모/교사 SHA·effort low·ONE_UPDATE_COMPLETE·실제128적용·sample_errors 비어 있음·raw/canonical shard SHA**를 모두 요구한다. Wh는 같은 부모에서 새로 시작해5 optimizer/640답·6h 상한이므로 Wg와 더해6연속 학습으로 부르지 않는다. Wg2h/Wh6h는 상한이지 정식 교육량/성공 예측이 아니다. 두 새 SH의 실제 CPU check-only와 모델 E2E는 구분하며 새 코드 smoke0/0/0/0 뒤에만 GPU 실행한다.

**기존 medium 보류:** We 실험 시도는 -done으로 이관하지만 검증 PASS 아님, 미실행 Wf SH는 사용자 지시로 HOLD 보존한다. 데이터셋 삭제/medium 학습 재개는 이번 범위에 없으며, 향후 자원 여유와 low의 품질 부족이 실측된 뒤 사용자와 다시 결정한다.

### Stage0W — 공개 OASST2 한정 선별/비보호 CPU 게이트(코드 작성, 실자료 check-only)

[선별·교사 게이트](../scripts/diag_p106_oasst2_teacher_ko_gate.py)는 pinned [OASST2 카드](https://huggingface.co/datasets/OpenAssistant/oasst2) Apache-2.0 표기·고정 원본 SHA `7A886A16...B7EE29B`의 reviewed/non-synthetic 영어 **종결 단일턴** 한 경로만 선택한다. 기존 공개 v3 첫 질문 exact 겹침, 내부 중복, 원문 길이600자를 제외하고 해시순 16개를 고정한다. 현재 CPU check-only 관측: 종결 후보1326, v3 질문 겹침656, 길이 초과531, 자체 중복1, 잔존138/선정16. **외부 개별 권리·안전·의미·근사오염은 이 선별로 PASS가 되지 않는다.**

### Stage1aW — 사용자 완료·형식 음성(결과101 §1)

역사 런처 `run_P106B_Stage1aW_oasst2_teacher_ko_gate-done.sh`는 재현명령을 [결과101 §5 부록](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에 보존한 뒤 삭제했다. 이 런처는 Stage0W CPU 검사 뒤 Prism build10743·같은 SHA Bonsai 2 PTQ1_0을 **localhost 인증·offline·GPU full**로 기동했다. 16개 영어 사용자/사람 답을 한국어 질문·답 JSON으로 요구하고 v1 후보를 write-once 저장했다. 선택 문턱은 JSON≥12/16, wall≤1800초, GPU 시작/교사 적재 후 free≥8192/2048MiB였다. **실측 완결9/16·exit8**이었다([결과101 §1](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). 모든 후보는 `UNKNOWN`/학습 target0이며 P106 검증형 `ACCEPT`가 아니다.

### Stage1bW — 사용자 시도 완료·선결 중단, 학습 NOT_RUN(결과101 §2)

역사 온라인 런처 `run_P106B_Stage1bW_online_pseudo_sft_micro8-done.sh`도 [결과101 §5 부록](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에 재현명령을 보존한 뒤 삭제했다. Stage1aW 원본/manifest SHA·완료 문턱을 선검사하고 학습 완료 P076 B3 mean checkpoint를 학생 시작점으로, legacy tokenizer·micro8×accum16/ckpt-on·Muon RMS4/AdamW를 쓰도록 설계했었다. 실제로는 상류 형식9/16 때문에 check-only에서 중단돼 학생 로딩·학습0이다.

학생을 먼저 올려 GPU 여유를 확인한 뒤 full 교사를 같은 GPU에서 ctx1024로 올린다. 교사에게 **실제로 다시 요청한** 한국어 문장 중 JSON/완료/기본 한국어·숫자·명백한 연락처 필터를 통과한 것만 별도 `PSEUDO_UNVERIFIED` 기록과 canonical assistant target으로 보낸다. 16개 중 유효 고유쌍 최소8개가 아니면 업데이트0·`exit8`. 유효쌍을 반복해 매 업데이트 `micro8×accum16=128`개 대화 노출, 총2업데이트로 제한한다. 이는 **최대 262,144 위치**(`2×8×16×1024`)의 처리 상한이지 assistant 지도토큰의 실측이 아니다. 원본 데이터/기존 checkpoint를 고치지 않고 새 runlog와 `HF/sft_ready/p106b_teacher_sft/v1/` 아래 **원문·교사출력 전체/자동 선정 canonical/각 SHA·조건 manifest를 write-once로 기록**한다. 모든 동시·loss 문턱을 지난 뒤 교사를 종료하고 고유 `runs/ckpt/m100R1c_ko-en_300M_p106b_s1b_oasst2_ko_online_s1337.pt` 진단 체크포인트 한 개만 저장한다(예상 약0.45GiB, 사용중인 기본 모델 덮어쓰기0). P100의 체크포인트·JSON 쌍 계약을 위해 같은 stem의 새 `runs/logs/*.json`도 기록하되 `final.val_loss=null`, 실제 assistant 지도토큰, `quality=NOT_RUN`으로 표시한다. 부모의 300M 예산을 이번 학습량으로 오인하지 않는다. `v1` 원본을 고치지 않고 문제행을 교정한 파생본은 `v2`로 만든다. 실제 지도토큰·유한 gradient/손실·동시 NVML/torch peak·교사 출력토큰/초·비용을 보고한다. 시작 다른 compute 앱0/free≥14GiB, 모델 공존 뒤 표본 free≥2GiB를 사전 중단선으로 둔다. `exit0`도 **기능 PASS**, 품질/`TRAIN_READY` 아님. LR `1e-4`/Muon 행렬 배수4/WD0은 SFT pilot 임시값이며 pretrain 최적 LR로 오인하지 않는다.

### Stage1aWb/Wc — 2026-09-27 절단 원인·사고/최종 분리의 짧은 대응 진단

Stage1aWb는 기본 sandbox NVML 차단으로 적재 전 종료9였고, 별도 Stage1aWc 역사 런처는 사용자 이번 지시 한정 **10분 이하 CPU+GPU**로 실제 완료됐다. 두 `-done.sh`는 [결과101 §6~§7·재현 부록](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에 명령/상태를 남긴 뒤 삭제했다. v1의 미완결3건+완결 대조1건을 같은 `ctx4096`, medium, fixed seed와 [공식 thinking 샘플러](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf#generation-parameters)에서 cap768/3072로 대응 비교했다. **이번 팔끼리만 cap 차를 귀속**한다. v1과는 ctx/샘플러도 달라 소급 단일효과 주장은 금지한다. 8요청158.757초, cap768 완결0/4 대 cap3072 완결3/4이며 후자1건은 사고문만 남았다.

신규 `HF/sft_ready/p106b_teacher_sft/v2/`에는 네 영어 원문·`finish_reason`·행별 사용량/시간·`reasoning_content`·최종 `message.content`·파싱된 `user_ko`/`assistant_ko`를 서로 다른 필드에 write-once로 남겼다. 런로그에는 문구가 아니라 cap별 건수·길이·토큰만 남겼다. 학생으로 보낼 수 있는 필드는 **완결 최종 JSON의 `assistant_ko`뿐**이지만, 이 실행에서 실제 target 채택·학습은0이다. 사고과정·영어 사람답·불완전 fragment는 target이 아니다. 네 건은 옛 실패를 과표집하므로 **12/16 본 모집단 문턱을 통과시키지 않는다.** 사용자 선택에 따라 단순 번역 full16 대신 교정형 Stage1dW 소형 진단을 거쳐 Stage1fW 교정형 full16 후보를 준비했다. 비사고 모드와 프롬프트 축약은 기각돼 쓰지 않았다.

### Stage1dW — 교사 원답 교정 가능성과 계보 보존의 3문항 gate

Stage1aWc 짧은 대응 진단은 cap768 완결0/4·cap3072 완결3/4였지만, 완결된 WebRTC 문항에서 **원래 사람 답안의 API 오개념을 교사가 충실하게 번역**했다([결과101 §7~§8](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). 사용자는 이 문제를 단순 번역이 아닌 **교사 교정안**으로 후속 시도하고, 나중에 사람이 다시 검증·개선할 수 있도록 원문과 교정본을 보존하기로 선택했다. 이는 번역형 Stage1a와 **다른 교사 작업**이며 지능 품질 증거를 합산하지 않는다.

[독립 진단](../scripts/diag_p106b_teacher_answer_repair.py)의 Stage1dW 역사 런처도 [결과101 §9·재현 부록](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에 보존 뒤 삭제했다. v1/v2 정확 SHA를 확인하고 WebRTC 오개념, 시점·모델 자기소개, 산술 대조 세 문항을 사용했다. 교사에게 영어 원답을 **검증되지 않은 DATA**로 주고 오류를 고치거나 불확실성을 답하라고 요청했다. `user_ko`,`assistant_ko`,`correction_status`,`correction_note` 완결 JSON을 `medium` + 공식 thinking sampler, ctx6144/max4096/사고예산2048로 받았다. 자기 `correction_status`는 독립 진실 판정이 아니다.

`HF/sft_ready/p106b_teacher_sft/v3/`에 영어 질문/사람 원답, v1/v2 SHA, 실제 교사 사고·최종 원문, 파싱된 새 문답·교정 설명·종료/사용량을 write-once로 남긴다. **학생 학습·target 채택은0**이며 적어도2/3 JSON 완결은 형식 가능성 문턱일 뿐 내용 정답 판정이 아니다. WebRTC의 입력은 `constraints`, 반환은 `Promise<MediaStream>`이라는 [공개 API 근거](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia)와 직접 대조하되, 나머지 답의 정확성·권리·원문 오염은 별도다. 소형 gate에서 실제로 고쳤는지 확인한 뒤 16건 모집단과 학생에게 보낼 교정본 선정 규칙을 새 단계로 사전등록한다.

### Stage1fW — 교정형 full16 후보 생성, 검증/학생 학습과 분리

[당시 Stage1fW SH의 재현명령](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)은 처음에 **코드·CPU 계약만** 준비됐고, 이후 사용자가 실행했다. 사용자 새 smoke PASS와 idle GPU, v1/v2/v3 정확 SHA가 선결이었다. 원래 고정16 영어 쌍 모두를 교정형 Stage1dW와 같은 프롬프트·공식 thinking sampler·medium/ctx6144/max4096/사고예산2048로 재요청하고, `HF/sft_ready/p106b_teacher_sft/v4/teacher_repair_full16_candidates.jsonl`에 원문/교사 사고/최종답/교정 선언/사용량을 write-once로 저장했다. 원본 v1/v2/v3와 기존 학생/체크포인트는 수정하지 않는다. 최소 JSON완결12/16과 hard wall3300초는 **후보 생성의 형식 문턱**이다. 교사가 `CORRECTED`라 해도 자동 교육 수락은0; 실제 수치·코드·시점/정체성 주장과 출처/권리를 별도 검토해 명시 거부/불확실/채택 근거를 새 버전 manifest에 기록해야 한다. 이후에만 학생 micro8×accum16/ckpt-on의 교정형 별도 tag와 같은 노출량 대조를 열며, 현재 Stage1bW 옛 tag를 재사용하지 않는다.

2026-09-28 [결과101 §10](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)은 사용자 Stage1fW 실제 생성 16/16 `stop+JSON`·278.659초로 **형식 문턱 PASS**를 기록했다. 하지만 직접 원문/답을 읽은 [행별 감사](../test_result/evidence/P106B_Stage1fW_candidate_review.json)는 명백한 교사 새 결함8, 추가 검토4, 잠정4다. 따라서 '형식이 되면 교육 후보는 품질이 충분할 것'이라는 낙관적 예측은 **기각**되고 교육 target 채택/학생 업데이트는0이다. 원본 v4 불변, 실행 SH는 재현명령과 Git 복구 이력 보존 후 `-done` 이력으로 관리한다.

### Stage1gW — 교사 프롬프트 강화·응답별 결함 훅과 제한 재요청 (사용자 승인 A)

독립변수는 **같은 v4의 명백한 결함8건에만 적용한 엄격한 원천 불변 프롬프트+결함 피드백 재시도**다. [진단기](../scripts/diag_p106b_teacher_targeted_repair.py)와 [완료 이력·재현명령](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)은 정확한 v1~v4 SHA 및 [16행 감사](../test_result/evidence/P106B_Stage1fW_candidate_review.json)의 원천 ID를 대조한다. 시스템 프롬프트는 원답을 불신 자료로 유지하되 지명·인물 성별·질문/답변 역할·숫자/단위를 임의 변경하지 말고, 표기가 불확실한 고유명사는 원문 Latin을 보존하라고 요구한다. 응답 직후의 **진단기 내부 validator**가 불완결 JSON, 예상 밖 아랍/키릴/한자 문자, 이번8행의 명시 지명·성별·어휘·역할 결함을 검사한다. 동일 결함이면 오류 코드만 교사에게 피드백하고 각 행 **최대3회**까지 다른 seed로 다시 생성한다. 전역 Codex 훅 설치가 아니라 이 실험에서만 쓰는 bounded response hook이다.

v5 `HF/sft_ready/p106b_teacher_sft/v5/targeted_repair_attempts.jsonl`에는 실패 응답을 포함한 **모든 시도**의 원문·사고·최종답·검사오류·사용량과 행별 첫 lint 통과 선택을 write-once로 보존한다. 사전 문턱은 8행 모두 3회 이내 **명시 결함 lint** 통과, hard wall≤1800초다. 통과여도 정답·번역 충실도·PII·권리·학생 교육 채택은 자동 승인하지 않고 `accepted_for_training=false`다. 모르는 오류는 놓치고 정상인 특수표기를 거부할 수 있으므로 사람/별도 GPT가 v5 후보를 v4 원문과 다시 읽고 다음 선정 버전을 결정한다. 형식16/16인 v4와 선별 결함8인 v5의 통과율은 모집단·프롬프트·retry가 달라 인과 비교 불가다. 기존 학생 Stage1b를 재실행하지 않는다.

preflight: 학습 step0·draw0·새 checkpoint/tag0이므로 pretrain의 풀≥2× 규칙과 micro/accum은 적용 대상이 아니다. 동일 원본/교사 SHA·v4 파생 원천을 고정하고 새 v5 출력만 허용한다. 기존 Stage1d/f와는 답안 과제·선별·프롬프트·retry가 함께 달라 품질 우열을 주장하지 않는다. 예상 GPU full 교사 ≤0.5h, 경쟁 프로세스0·시작 free≥8192MiB·교사 적재 뒤 free≥2048MiB에서만 계속한다. `--self-test`·`--check-only`는 모델 비실행이고 8개 과거 결함이 정확히 validator에 걸리는지를 확인한다. **이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.**

2026-09-28 사용자 [결과101 §11](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md): 실제8행/13요청·교사 completion28,677토큰·474.232초, 명시 결함 lint7/8<사전8/8로 유효한 음성 `exit8`이다. 행11은 세 번 모두 미완결 또는 이름의 키릴/아랍 문자 혼입으로 fail-closed했다. 그러나 [v5 직접 점검](../test_result/evidence/P106B_Stage1gW_candidate_review.json)은 lint 통과7행 안에도 인명 훼손·혼합어·태양 거리의 10~100배 축소·역할 문장의 어색함을 발견해 명백 오류 총5, 추가검토2, 잠정1로 기록했다. **예측했던 ‘명시 결함 재시도만으로 8행을 교육 후보로 정리’는 기각**하고 자동 학습 채택0을 유지한다. 원본 v5 모든 시도는 불변, 같은 Stage1gW 재실행은 금지한다. 후속은 교사에게 canonical/ChatML 형식을 맡기지 않는 파서·래퍼 분리와 새 데이터 버전/단계에서만 연다.

### Stage2aW — 300M~600M 학습/자료 토큰 분모·교사 비용 선결 (CPU)

[읽기 전용 계산기](../scripts/diag_p106b_scale_preflight.py)와 [사용자용 SH](../run_P106B_Stage2aW_sft_scale_preflight.sh)는 정확 v4 SHA와 legacy 학생 tokenizer SHA를 확인하고 16개 한국어 대화를 기존 canonical→ChatML 인코더로 센다. v4 실측은 **학생 전체 직렬화 2,040토큰·assistant 지도 1,298토큰**을 만드는 데 교사 completion(사고+최종) **17,698토큰·278.659초**였다. 300M/600M이 (a) 학생 모델 처리 위치, (b) 고유 직렬화 데이터, (c) assistant 지도 토큰 중 무엇인지 분리한다. 1~4epoch을 구별하며 `8×16×1024=131,072`은 **고정 길이 패딩을 포함할 때의 명목 위치/step**일 뿐, 현재 가변 길이 SFT 배치의 실제 비패딩/지도 토큰 수가 아니다.

같은 작은 v4 생성 속도와 평균 길이를 기계적으로 연장하면 고유 직렬화300M에 교사 약474일, 4epoch 하한인 고유75M에도 약119일이라는 **규모 경고**가 나온다. 그러나 샘플이 결함 포함 한국어16·교정형 사고 출력이고 배치/포맷·영어/거부율이 바뀌므로 이것은 예산 확정이나 처리량 예측이 아니다. 고유자료·노출량·문항 중복/라이선스·교사 사고/최종 생성량을 서로 다른 열로 보고한다. `--self-test`/`--check-only`는 CPU에서 PASS, 실제 대량 교사/학생 모델·영어 생산성은 `NOT_RUN`이다. 토큰 분모 사용자 결정 전 300M/600M 본훈련 조건이나 새로운 tag를 확정하지 않는다.

### Stage2bW — 교사 내용과 학생 양식의 소유권 분리 (CPU)

[순수 래퍼](../scripts/p106b_teacher_wrapper.py)와 [계약 SH](../run_P106B_Stage2bW_content_wrapper_contract.sh)는 교사 출력에서 얻은 **질문/답변 텍스트**만 받아 역할 순서·출처 ID/SHA·언어·교사 SHA·미검증 라벨을 코드가 부여한다. `tinylm.chat.canonical.normalize/validate`가 버전드 대화 JSON을 만들고, 기존 `tinylm.chat.serialize`와 `tinylm.data.sft.encode_conversation`가 토크나이저별 ChatML 문자열·assistant-only 마스크를 만든다. 교사 사고, JSON 문법, ChatML 경계/role token, 지도 마스크는 교사에 맡기지 않는다. 멀티턴도 코드가 `user→assistant` 쌍을 최대4회 조립하고 잘못된 경계 토큰·제어문자는 거부한다. 현재 합성 두 턴·마스크 CPU fixture PASS, 실제 교사 v5/대량 원천→새 canonical 자료는 `NOT_RUN`이다.

이 래퍼는 교사가 어떤 **전송 문법**으로 질문/답을 보낼지를 아직 결정하지 않는다. ① 태그 필드 뒤 파싱, ② 제한형 JSON, ③ source 질문 유지·답변만 생성의 세 경로를 사용자 질문 기능으로 비교했으며 선택 전에는 구 형식 Stage1gW를 소급 변경하지 않는다. 전송 문법 확정 뒤 새 Stage2cW 교사 소형 bilingual·주제별 패널을 별도 버전에서 만들고 실제 parse/중복·한영 5:5 토큰 계측을 통과해야 300M 학습 SH를 READY로 승격할 수 있다.

**사용자 선택 2026-09-28:** 교사는 태그 필드로 질문·답·간단 메모의 내용만 쓰는 A안으로 정했다. teacher thinking은 버리지 않고 별도 원본 sidecar에 SHA와 생성 ID로 보존하되 현재 canonical에는 **sidecar 참조/해시만** 쓴다. 현 `tinylm.chat.serialize.loss_spans()`의 기본 `train_thinking=True`와 미완 `train_thinking=False` 구현 상태에서 사고문을 canonical의 활성 `thinking` 블록에 넣으면 의도치 않은 지도 토큰이 되기 때문이다. 장래 reasoning 학습은 별도 데이터셋 버전과 loss-mask/권리/품질 계약을 통과한 뒤 판단한다.

### Stage2cW — 동일 교사 16문항의 태그 대 JSON 출력형식 비용 대응 게이트

[국소 format adapter](../scripts/p106b_teacher_format.py)는 `qa_generate`, `translate`, `repair`, `diversify`, `next_turn`의 작업 종류를 코드가 지정하고, 교사는 `[[QUESTION]]`, `[[ANSWER]]`, 선택 `[[NOTE]]` 본문만 작성한다. 역할·토크나이저·ChatML과 독립 verifier는 모델에 맡기지 않는다. 교사 자기 교정 설명은 참고 메모이지 참 판정이 아니다. [Stage2cW 진단](../scripts/diag_p106b_teacher_tagged_pair.py)과 [사용자 SH](../run_P106B_Stage2cW_tagged_json_pair.sh)는 기존 v4와 같은 고정16 영어 OASST2 원문을 출처로, 동일 모델·중간 사고·sampler·ctx·출력상한·seed에서 **태그 vs JSON 대조**를 팔 순서 ABBA로 32회 수행한다. 두 팔의 의미지시는 같고 출력 문법만 바꾸며 행별 completion token(사고 포함)·최종 글자·요청 wall·파싱 완결·canonical 래퍼 성공을 새 v6에 write-once 저장한다.

사전 문턱은 tagged `stop+필드+canonical` ≥12/16, hard wall≤2400초다. 더 짧거나 빠르다는 주장은 양 팔의 개별 토큰/시간·순서 편향을 직접 비교한 뒤에만 한다. 이 16개는 한국어 변환 과제라 **한영 5:5 생산성이나 300M 처리량을 증명하지 않는다**. 실제 교사 GPU는 사용자 실행 전 `NOT_RUN`; CPU self-test/check-only만 PASS다. 새 답 역시 교육채택0·독립 정답성 `NOT_RUN`으로 보존한다.

### Stage2dW — v6 태그 후보를 독립 canonical/ChatML 파일로 래핑하는 작은 교량

[materializer](../scripts/build_p106b_tagged_pilot.py)와 [사용자 SH](../run_P106B_Stage2dW_tagged_pilot_canonical.sh)는 v6의 tagged 완결≥12/16과 미리 고정한 val cases2·15를 선결로 요구한다. 교사 raw의 사고/최종을 고치지 않고 [코드 소유 래퍼](../scripts/p106b_teacher_wrapper.py)로 질문·답만 canonical `user→assistant`에 넣고 출처·라이선스 카드 상태·모델/원천 SHA·`PSEUDO_UNVERIFIED`를 부여한다. `teacher_reasoning_content`는 원본 v6에만 남기고 canonical meta에는 원본 sidecar SHA/행 참조를 둔다. 기존 legacy tokenizer로 길이≤1024·assistant 지도 토큰>0과 train/val 첫 질문 해시 불겹침을 확인한다. [write-once sharder](../scripts/p106b_shards.py)는 UTF-8 행을 자르지 않고 각 JSONL 파일 **20,000,000 byte 이하**로 분할하며 shard별 SHA·전체 이어붙이기 SHA를 manifest에 기록한다. Git에 자동 staging/push하지 않는다.

현재 v6가 없으므로 Stage2dW `--check-only`의 `HOLD8`은 정상 선결이다. v7 작은 한국어 자료가 생겨도 **300M/600M 학습자료는 아니다**. 이후 대량 자료는 원천 concept ID·주제 가족·언어별 목표와 유니크/근사중복률을 먼저 고정하고, 주제·형식·지식·논리·일상·문화·사회·수학/코드·게임/TRPG/밈을 별도 계수해야 한다. 독립 대화는 매 요청 새 메시지로 시작하고, 멀티턴에서만 같은 대화의 앞 턴을 의도적으로 전달한다. seed 변경만으로 같은 concept를 무한 반복하지 않으며 concept당 변형 상한과 novelty 하한에서 생성 부족을 그대로 `HOLD`한다. 한영 5:5는 행 수가 아니라 학생 토크나이저의 **비패딩 학습 처리 토큰**으로 측정하고 assistant 지도 토큰/교사 사고+최종 토큰은 별도 열로 보고한다.

### Stage2eW — 현재 로컬 공개 원천의 유한 교사 작업표

[작업표 builder](../scripts/build_p106b_job_deck.py)와 [완료 이력·재현명령](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)은 기존 공개 v3 train/val의 정확 SHA를 **읽기만** 확인한 뒤 새 무시된 HF 버전에 20MB 이하 job JSONL shard를 write-once로 만든다. 한 단일턴 source concept에는 ko/en 각 최대1개(`repair` 또는 `translate`), 영어 멀티턴은 **기존 영어 맥락을 의도적으로 넣는 `next_turn` 1개**만 부여한다. 기존 멀티턴 전체를 번역하지 않고 한국어 답 한 줄만 섞는 무효 대화는 만들지 않는다. 분할은 source의 원 train/val을 generation 전에 유지한다. 매 job은 source ID/revision/card license, topic heuristic, concept ID, 목표 언어/작업 및 고정 seed 키를 갖고, 같은 concept를 목표 토큰 도달까지 다시 만드는 루프가 없다.

실제 로컬 v3의 CPU check-only는 train 한국어175행/34,946 직렬화토큰·영어2,821행/822,733토큰에서 유한 job **5,429건**(train en2,996/ko2,162; val en158/ko113)을 계산했다. 주제 heuristic은 general/other **4,589건**으로 편중되어 정치사회·게임/TRPG·수학·일상 등 요청 범위의 의미 품질/충분한 양을 증명하지 못한다. 5,429행과 이미 존재하는 857,679토큰은 75M 이상의 고유 학습 풀 자체가 아니다. `--execute`는 Codex가 실행하지 않았고, 새 job deck은 사용자 실행 전 `NOT_RUN`이다.

### Stage2fW — 8주제×한영×2고유 source의 32건 교사 생성 pilot

[32-job 진단기](../scripts/diag_p106b_bilingual_pilot.py)와 [사용자 SH](../run_P106B_Stage2fW_bilingual_teacher_pilot.sh)는 Stage2e job deck과 Stage2c 태그 필드/래퍼≥12/16을 선결로 둔다. 각 주제 heuristic×목표언어 조합에서 해시순 **서로 다른 source ID 2개**만 고른다(32개 고정). 교사는 `repair`, `translate`, `next_turn`을 job이 정한 대로 수행하고, 나중 확장에는 `qa_generate`, `diversify`를 별도 근거형 작업으로 사용할 수 있다. 독립 job은 매 HTTP 요청에 새 system+source만 보내며 서버 `--cache-ram 0`을 유지하고, 하나의 멀티턴 source에서만 앞 턴을 입력으로 포함한다. 단순 seed 변경을 새로운 concept로 세지 않는다. 태그 파싱 실패만 1회 재요청하고, 같은/근접 질문은 재요청으로 quota를 채우지 않고 거부한다.

원본 요청/사고/최종/거부 이유·교사 completion token/요청 wall은 새 무시된 HF 원본20MB 이하 shard에 전수 기록한다. 별도 기존 serializer로 각 선택 답의 student canonical 전체·assistant 지도 토큰을 한영별로 재어 **행수 16:16이 실제 토큰 5:5인지** 확인한다. 완료 기준은 ko/en 각 최소12개의 형식·길이·근접중복 screen 후보와 새 원본 SHA; 이것은 **정답·권리·PII·주제 의미 승인이나 300M 학습 readiness가 아니다**. `--self-test`만 CPU PASS, `--check-only`는 사용자 Stage2c/e 미수행으로 `HOLD8`, 교사·학생 모델은 `NOT_RUN`이다. Stage2c 태그 대 JSON의 completion token/벽시계 대비 이번 생성의 accepted candidate당 비용을 비교하되, 과제·소스가 달라 인과 속도 개선으로 합산하지 않는다.

### Stage2gW — 최종답만 학생에게 전달하는 2-update 소형 기능 게이트

[사용자 실행 SH](../run_P106B_Stage2gW_tagged_student_wiring.sh)와 [학생 코드](../scripts/train_p106b_tagged_pilot.py)는 Stage2d의 v7 canonical train/val 및 기존 P076 B3 mean legacy32 부모·tokenizer SHA를 선검사한다. 교사는 GPU에서 내린 뒤 학생만 올린다. 모델은 compile/default·grad checkpoint on, micro8×accum16으로 **2 업데이트**만 수행하고 assistant-only CE와 유한 gradient/실제 비패딩 처리 토큰·지도토큰을 별도 기록한다. 교사 사고는 canonical meta의 sidecar 참조라 loss target이 아니다. 기존 부모/원본/옛 Stage1b 태그는 고치지 않고 새 고유 `p106b_s2g_tagged_pilot_s1337` checkpoint/JSON만 write-once로 저장한다. 이는 온라인 동시 교사 Stage1b와 **다른 경로**이고, 예산300M·한국어/영어50:50·멀티턴 품질·base full-val/벤치/forgetting은 모두 `NOT_RUN`이다.

실제 v7 사용자 원본이 없으므로 `--check-only`는 올바르게 `HOLD8`이고 Codex는 모델을 실행하지 않았다. CPU `--self-test`에서 canonical 최종답만 mask되는 계약은 PASS다. 독립 원본 QA의 실질 성능과 교사 방법론의 인과효과는 고정 원문/부모·같은 노출량 no-teacher 대조 및 문항별 결과가 있어야 판정한다. 한정 기능 게이트 PASS 전 대규모 trainer를 READY로 만들지 않는다.

### Stage2hW — 사용자 이번 지시 한정 CPU+GPU 교사 effort 속도·완결률 실측

사용자는 온라인 교사를 5 optimizer update만 먼저 검토하도록 하고 이번 지시에 한해 CPU+GPU 직접 시험을 승인했다. `micro8×accum16`의 5 update를 매 microbatch 신규 자료로 수행하면 최대 **640개 교사 답안**이 필요하므로, 먼저 [독립 진단기](../scripts/diag_p106b_effort_profile.py)·[완료 이력·재현명령](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)의 **4문항×`none/low/medium`=12요청**으로 교사 비용을 실측한다. 모델/원천/태그 프롬프트/샘플러/ctx6144/max2048/문항별 seed를 고정하고 요청 순서만 교차한다. 서버는 `--reasoning auto`, `reasoning_effort`는 요청별 top-level 필드다. 사고예산 숫자를 별도로 넣지 않아 `none/low/medium`을 임의 0/512/2048 토큰과 동치라고 가정하지 않는다. 원본 v9에 사고·최종·finish·usage·벽시계를 write-once로 저장하고 runlog에는 집계만 찍는다.

[PrismML 공식 known issues](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf/blob/main/KNOWN_ISSUES.md)는 현재 template의 `none/low/medium`과 `none`일 때 서버 `--reasoning auto` 조건을 설명한다. 반면 [공식 demo README](https://github.com/PrismML-Eng/Bonsai-demo)는 `low`가 기대보다 길 수 있다고 경고하므로 **실제 local build에서의 종료사유/사고 길이를 직접 판독**해야 한다. 세 모드의 온전한 Q/A 생산량과 완결률을 보지 않고 빠르다는 이유만으로 대량 교사 기본값을 바꾸지 않는다. 이 단계는 교사-only 비용/형식이고 학생 5 update나 300M 품질 증거가 아니다.

Stage2hW 결과의 `completion_tokens`는 사고+최종을 합치며 요청 wall에는 HTTP/첫 호출 시간이 있다. 이후 학생 실제 1 update와 별도로 결합해 온라인 새 답안640개의 비용을 상·하한으로 추산한다. 추산이 큰 경우 5 update를 무작정 시작하지 않고 사용자에게 범위 재확인을 받는다. 이번 승인 전용 GPU 시험을 후속 세션의 영구 권한으로 승계하지 않는다.

2026-09-28 **이번 지시 한정 교사 단독 실측**: 고정4문항의 `none`은 4/4 완결·완료토큰1,063·요청벽시계18.568초, `low`는 4/4·5,166·83.406초, `medium`은 2/4·7,531·121.882초였다. `medium` 두 문항은 max2048에서 사고가 답변 예산을 소모해 `length`로 끝났다. 이 값은 **같은 4문항의 교사 요청 시간**이지 학생 5업데이트 처리율이나 300M 생산비용이 아니다. 이 Stage2hW의 세 팔은 원인 분리를 위해 모두 *thinking sampler*를 사용했으므로 특히 `none`은 모델카드의 비사고 권장 sampler가 아니며, 아래 Stage2iWb의 예상시간으로 그대로 옮기지 않는다. 새 원본 v9는 불변이다.

### Stage2iWa/Wb/Wc — 교사+학생 온라인 5 optimizer 업데이트 처리율 (사용자 실행 세 팔)

사용자는 120 optimizer 업데이트를 즉시 돌리지 않고 **5회만 먼저 실측**한 뒤 결과로 다시 결정했다. 이후 직접 실행은 하지 말고 아래 세 조건을 각각 SH로 준비하라고 지시했다. [공통 진단](../scripts/diag_p106b_online_rate5.py)은 Stage2e의 공개 v3 **`OpenAssistant/oasst1` 단일턴·영어 원천** 중 길이 상한을 통과한 365개 concept의 영/한 쌍을 고정 순서로 읽는다. ko는 번역, en은 원답 교정이다. 다섯 optimizer 업데이트 각각 micro8×accum16을 채우려면 **새 교사 출력이 수락된 640 대화**가 필요하다. 한 microbatch마다 새 출력8개를 요청하고 언어를 교대로 바꾼다. 같은 원천 concept의 영/한 출력은 쌍을 이루므로 **640개 독립 concept는 아니다**. 실패 출력은 새 source로 대체하되 언어당 고유 후보365개를 소진하면 `exit8`이며, 실패를 반복 seed로 감추지 않는다.

**2026-09-28 원천 계보 정정:** 기존 설명의 `OASST2`는 잘못이다. Stage2a/c/d의 고정16은 `OpenAssistant/oasst2`이지만, Stage2e 작업표는 [공개 v3 manifest](../test_result/096_20260925_P090B-공개원천-구조후보-SFT-보류.md)에 연결된 `OpenAssistant/oasst1`과 `CohereLabs/aya_dataset`에서 왔다. Stage2iWa는 그 작업표 중 `oasst`·영어 원문·단일턴 624쌍을 골라 질문/답 각각1200자 이하로 더 줄인 **365쌍**이다. 5회에는 한영 각각320개의 수락 답이 필요하므로 후보 수락률≥87.7%가 필요하지만 사용자 초반 원본은33요청 중23형식 후보(69.7%)였다. 서버500을 빼더라도 이 유한 풀만으로 5회 완료를 전망하기 어렵다. Stage2iWb/Wc와 동일 OASST1 pool로 만든 추후 실험은 원천을 숨기지 않고 provenance를 명시하며, 새 OASST2/Aya/사전 안과 직접 한 변수 비교로 취급하지 않는다.

| 구분 | SH | 교사 사고/출력 예산 | 모델카드 sampler | 상한 |
|---|---|---|---|---:|
| A·Stage2iWa | [low](../run_P106B_Stage2iWa_online5_low.sh) | `low`, ctx3072/max2048 | thinking: temperature1, top_p.95, top_k20, min_p.05, presence0, repeat1 | 4h |
| B·Stage2iWb | [none](../run_P106B_Stage2iWb_online5_none.sh) | `none`, ctx1536/max1024 | instruct: temperature.7, top_p.80, top_k20, min_p0, presence1.5, repeat1 | 1.5h |
| C·Stage2iWc | [medium](../run_P106B_Stage2iWc_online5_medium.sh) | `medium`, ctx6144/max4096 | thinking: A와 동일, Stage2h max2048 절단 때문에 출력 예산 확대 | 6h |

[PrismML 공식 모델카드](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf)는 thinking과 non-thinking sampler를 위처럼 다르게 권장한다. **현재 카드에는 `low`를 지원하지 않으며 xhigh에 가깝다고 적혀 있는데** 로컬 Stage2hW의 `low`는 4/4 완결·medium보다 짧았다. 카드/실물 런타임 차이 가능성이 있어 A를 정식 저비용 reasoning 경로로 가정하지 않는다. `--reasoning auto`와 요청별 top-level `reasoning_effort`를 유지하고 출력에서 사고·최종을 따로 기록한다. 사고 텍스트는 원본 `HF/sft_ready/p106b_teacher_sft/v10_online_rate5_<effort>/raw_*.jsonl`의 sidecar일 뿐 assistant 지도 target이 아니다. 소프트웨어가 교사의 `[[QUESTION]]`/`[[ANSWER]]`/`[[NOTE]]`를 파싱해 canonical 역할·ChatML·assistant-only 마스크를 소유한다.

세 팔은 동일한 P076 B3 mean 부모·legacy32 tokenizer·학생 micro8/accum16/ckpt-on, 모델 compile/default, Muon RMS4+AdamW를 쓴다. 동일한 공개 source/문항 순서를 쓰지만 교사 sampler/사고강도뿐 아니라 ctx/max 출력 상한도 달라 **팔 간 품질 또는 속도 차를 effort 단독 효과로 귀속하지 않는다**. 각 응답의 완료토큰·요청벽시계·format/reject, 학생 업데이트의 teacher/compute/전체벽시계·실제 비패딩 처리/assistant 지도토큰·언어별 토큰·전역 표본 peak와 PyTorch reserved를 별도 기록한다. 모든 시도와 학생 target은 20,000,000바이트 이하 write-once JSONL 샤드/해시 manifest로 남긴다. 시작 다른 GPU compute 앱0/free≥14GiB, 공존 후 free≥2GiB, 중간 free<512MiB·시간 초과·소스 고갈·형식 실패는 부분 이력을 보존하고 `exit8`이다. **체크포인트 저장0·held-out 평가0·정식 `TRAIN_READY`/품질 PASS0**. `exit0`은 이 제한 처리율 gate의 5업데이트 기능 완료일 뿐이다. 5회 결과와 한국어/영어의 실제 비패딩 토큰 비율·교사/학생 속도를 본 뒤에만 120회 온라인 지속 여부, chunk 선제생성/10GB 이하 RAM 버퍼의 필요성을 새 계획으로 결정한다. 이 세 SH를 큐에서 모두 연속 실행할 필요는 없다.

### Stage2jW — Stage2f/Stage2iWa 공통 HTTP 500의 매우 작은 원인 격리 (이번 지시 직접 허용)

2026-09-28 사용자 원본은 Stage2fW 교사-only 패널의 25번째 문항을 기록한 뒤 26번째에서 HTTP 500·`exit9`, Stage2iWa 온라인 low의 교사 응답33건 뒤 다음 요청에서 HTTP 500·`exit8`, 학생 optimizer 업데이트0을 보였다. 두 단계의 기존 클라이언트는 HTTP 오류 본문을 버렸고 Stage2fW는 부분 raw 29행을 남겼지만 manifest를 닫지 못했다. 따라서 **서버가 왜 500을 반환했는지 로그만으로는 확정할 수 없다**. Stage2iWa의 서버 실패를 과학적 음성8로 분류한 것은 도구 분류 결함이고, Stage2fW가 미통과인데 Stage2iWa의 check-only가 이를 선결에서 거부하지 않은 것도 계약 결함이다. Stage2gW의 학생2업데이트는 별도 v7 한국어13행 반복으로 Stage2fW의 성공이나 온라인5회가 아니다.

사용자는 이번 지시에 한해 매우 작은 CPU+GPU 직접 게이트를 허용했다. [Stage2jW 진단](../scripts/diag_p106b_http500_isolation.py)과 [별도 SH](../run_P106B_Stage2jW_http500_isolation.sh)는 **교사만** 두 개의 새 localhost 서버로 올려 각 환경의 실패 직전 입력과 첫 실패 입력을 고정 2개씩, 최대4요청/600초로 한정한다. 기존 Stage2fW 부분 raw SHA `2D395CD2155D04934F13240430B4D566BA621B6871775BCCB4083D8202E7347E`, Stage2iWa 부분 raw SHA `17A3EE87711E78D58FCD4A3BEF3A16662A02BE7BF25A00C4B949C22780EE5146`를 먼저 대조한다. GPU 경쟁 프로세스0·시작 free≥8192MiB에서만 모델을 올리고 출력은 새 `HF/sft_ready/p106b_teacher_sft/v11_http500_isolation/`에 write-once로 남긴다. 학생 로드/업데이트·체크포인트 쓰기·원본 v8/v10 재실행/수정은0이다.

독립변수는 **긴 세션 상태를 없앤 새 서버에서 정확 실패 위치 입력의 HTTP 500이 재현되는가**이다. 서버 `/apply-template`+`/tokenize`의 프롬프트 토큰 수, `ctx/max_tokens`의 명목 합, HTTP 본문 SHA/오류유형, 제한된 서버 오류 줄, 요청 전후·표본 GPU 점유를 기록한다. 두 서버 방식은 long-session 누적상태·학생 공존/학습을 의도적으로 제거하므로 HTTP 500이 **재현되지 않아도 기존 실패를 해결했다는 뜻이 아니다**. 재현되면 HTTP 500은 도구/백엔드 실패 `exit9`로 보고 본문 근거로 입력 초과·메모리·서버 결함을 더 좁힌다. 재현되지 않으면 장시간 상태/학생 공존 여부를 별도 사용자 실행 단계로 확인해야 하고, 출력 상한 축소·자동 retry만으로 원인을 숨기지 않는다. 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

### Stage2jWb — peg-native parser 우회 단일 요청, 학생 입력으로 직접 사용 금지

Stage2jW에서 Stage2fW 문항26은 새 서버에서도 HTTP500을 재현했고, 원문 오류 본문은 `The model produced output that does not match the expected peg-native format`이었다. 서버 토큰 preflight의 입력817+출력상한4096은 ctx6144보다 작고, 응답 뒤 GPU free는 약8.5GiB였다. 따라서 **그 재현 사례**는 긴 세션 누적상태·학생 공존·명목 컨텍스트 초과나 관측 OOM이 필수 원인은 아니라는 반례다. 반면 Stage2iWa의 한국어 소스23은 학생 없는 새 서버에서 HTTP200이라 원래 온라인500의 원인을 아직 모른다.

이번 승인된 초소형 진단 범위에서 [Stage2jWb](../run_P106B_Stage2jWb_peg_parser_bypass.sh)는 Stage2f 문항26 하나만 동일 모델/소스/seed/sampler/ctx/max로 재생하고 서버의 `--skip-chat-parsing`만 바꾼다. [llama.cpp 서버 안내](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)는 이 옵션이 서버의 chat/reasoning/tool 파싱을 건너뛰어 원형 응답을 `content`에 담는다고 설명한다. 실행해 HTTP200·원형 출력이 나오면 **서버 native 파서와 실제 모델 출력의 불일치**로 원인을 더 좁힐 수 있다. 그러나 사고와 최종답 구분도 비활성화되므로 원형 `content`는 **학생 assistant target이 아니며** 한국어/영어 tagged 필드만 임의 정규식으로 뽑아 학습시키지 않는다. 원형 응답은 새 무시된 `HF/sft_ready/p106b_teacher_sft/v12_peg_bypass_case26/`에 write-once로 남기고 실행 로그에는 SHA·구조 표지 수만 적는다. 단일 요청/최대300초·학생0·checkpoint0이고, 서버 우회가 형식·사실 품질 해결이라는 주장은 금지한다.

### Stage2fWb — 옛 29시도 SHA 참조 + 빠진 7문항만 새 버전에서 보충

사용자 Stage2fW는 32개 고정 job 중 **25번 문항까지 29시도**를 남기고 26번에서 서버의 PEG native-format HTTP500으로 종료9였다. old partial 원본은 손대지 않는다. [보충 진단](../scripts/diag_p106b_bilingual_recovery.py)과 [별도 SH](../run_P106B_Stage2fWb_bilingual_teacher_recovery.sh)는 정확 old SHA/29시도/1~25번 job 매핑을 대조하고 **26~32번 일곱 문항만** 새 `HF/sft_ready/p106b_bilingual_v2/teacher_recovery/`에 요청한다. 기존 29시도는 복사하지 않고 SHA 참조로 결합해 언어/주제/학생 비패딩·assistant 지도 토큰 분모를 재계산한다. 신규 답은 교사 tagged 형식→코드 소유 canonical/ChatML의 1024 위치·중복 화면까지 검사하되 자동 교육 채택은0이다.

Stage2jWb 단일 문항은 `--skip-chat-parsing`에서 HTTP200이지만 **max4096을 모두 사용해 `length`로 끝났고 tagged QUESTION/ANSWER가 반복돼 파서 완결이 아니다**. 따라서 서버 파서를 우회한 원문을 학생에게 전달하지 않는다. 원래 native 파서는 유지하고, 정확한 `peg-native format` 500만 **해당 문항의 거부된 교사 시도**로 기록·다른 seed에서 최대 한 번 재요청한다. 두 번 모두 실패하면 그 문항을 거부하고 다른 고정 job을 계속한다. 알 수 없는 HTTP/transport 실패는 도구 실패 `exit9`로 멈추며 부분 시도·오류본문·서버 진단과 manifest를 보존한다. 형식/길이/중복 거절도 감추지 않는다. 결합 패널의 사전 문턱은 한영 각 후보≥12/16, hard wall1800초, 기존 P106B의 **형식/코드 래핑 가능성만** 판정한다. 이 7문항 보충은 같은 32개 입력을 처음부터 다시 뽑는 것보다 교사 비용을 줄이지만, 새 서버/날짜·실패 처리 정책이 달라 old Stage2f와 시간비 인과 비교는 금지한다.

### Stage2iWd — 옛 OASST1 원천의 온라인 백엔드 1-update 재시험 (조건부)

Stage2iWa는 **학생 optimizer 0회**로 종료했고, HTTP500 응답 본문·서버 진단을 기록하지 않아 그것이 Stage2f의 PEG 출력 불일치와 같은 실패인지 모른다. [후속 코드](../scripts/diag_p106b_online_rate1.py)와 [별도 SH](../run_P106B_Stage2iWd_online1_backend.sh)는 **Stage2fWb 한영 각 후보≥12/16·manifest SHA**를 모델 로딩 전에 요구하고, 같은 P076 부모/legacy32·micro8×accum16·low thinking sampler·OASST1 finite source에서 **1 optimizer 업데이트**까지만 진단한다. 정확 PEG native-format 500은 해당 교사 시도만 거부·별도 SHA/오류본문 기록하고 다음 고유 source로 가며, 다른 서버/전송 오류는 부분 원본 보존 후 **도구 실패 exit9**다. 새 `v13_online_rate1_low_backend/`에 모든 시도·후보와 실제 업데이트에 들어간 generation ID를 구분해 write-once 저장하고 checkpoint는0이다. `Stage2iWa` raw의 `accepted_for_training=true` 23건은 실제로 optimizer가0회여서 **선정된 미적용 후보**였으며 새 코드에서 같은 오해를 반복하지 않는다. 이 1회는 OASST2/Aya/사전 혼합 5회 목표가 아니라 **동시 교사+학생 호출 경로의 수리 검증**이다. 사용자 재실행·새 smoke 이전에는 E2E `NOT_RUN`이다.

### Stage2iWe→Stage2iWf — 공개 다원천 medium 1회 선결 뒤 5회 (2026-09-29 사용자 A안 승인)

Stage2iWc의 `exit8`은 **한국어 OASST1 단일턴365개 소진**, 코드 예외가 아니다. 같은 원천을 무제한 재질문해 실패를 감추지 않는다. 이미 Stage2kWb에서 만든 공개 전용 Aya Dataset/OASST2 **train 대응 concept5,015개/언어**와 SHA 고정 샤드만 새 코드가 읽는다. `protected_locator=null`·`CARD_ONLY`·source repo/revision/원본 SHA/parent concept/split을 엄격히 확인하며 보호 사전·사전 파생물은 열거·입력하지 않는다. source는 원문 언어가 EN 또는 KO일 수 있어 target이 같으면 `repair`, 다르면 `translate`이며 교사는 content만 쓰고 canonical ChatML/assistant-only 마스크와 계보는 코드가 소유한다. source 권리 카드 상태가 곧 formal `TRAIN_READY`가 아니다.

새 [Stage2iWe SH](../run_P106B_Stage2iWe_online1_public_medium.sh)는 medium 모델카드 sampler·ctx6144/max4096, 같은 P076 부모·legacy32·micro8×accum16/ckpt-on에서 **1 optimizer 업데이트/128개 신선 후보**만 실행하고 2h hard wall·write-once v15·checkpoint0으로 제한한다. 교사 `/apply-template`→`/tokenize`의 실제 입력 토큰과 `input+4096+128≤6144` 조건을 각 job마다 확인한다. 초과/12k payload 한계 행은 `COMPRESSION_REQUIRED`/HOLD로 raw에 남기고 무단 절단하지 않으며, 미확인 token API 오류는 tool fail9로 분리한다. 교사 답이 완결돼도 사실성·개인정보는 아직 미검증이다. 출력을 직접 학습하는 범위는 **진단용 pseudo-label**에 한정한다.

Stage2iWe 사용자 원본 manifest가 **동일 공개 deck SHA·ONE_UPDATE_COMPLETE·실제1회**이면 당시 Stage2iWf 구현의 check-only가 통과하도록 선결을 코드로 묶었었다. 하지만 We는 완료하지 못했고 사용자는 medium 보류를 유지한다. [보존 Wf SH](../run_P106B_Stage2iWf_online5_public_medium-hold.sh)는 직접 실행해도 즉시 HOLD8이며 현재 큐의 실험이 아니다. 재개되더라도 Stage2iWe의 교사답이나 학생 가중치를 재사용하지 않고 같은 부모에서 새 단계로 준비해야 한다. 5회 통과는 기술 처리율/원천 수급 관측뿐이며 **OASST1 none 5회와 원천·길이 선별이 달라 인과 속도·품질 비교 금지**다. 300M/600M, 지능 상승, 멀티턴 능력은 별도 평가·권리·오답 분석 전 `NOT_RUN`이다.

### Stage2kW — 사용자 선택 C: Aya Dataset·OASST2·국립국어원 다원천을 계보별로 묶는 읽기 전용 계약

사용자는 다원천 C안을 선택했지만 A안의 비용/원천 분리와 B안의 사전 권리·다의어 주의도 보존하라고 했다. [원천 관리자](../scripts/build_p106b_multisource_deck.py)와 [CPU 읽기 전용 SH](../run_P106B_Stage2kW_multisource_lineage_census.sh)는 다음 사실을 **같은 집합으로 뭉개지 않고** 별도 계보로 기록한다.

| 층 | 고정 원천·선별 관측 | 생성 역할 | 독립성·선결 |
|---|---|---|---|
| Aya 영어 | 공개 v3의 `CohereLabs/aya_dataset` revision `f9ea0458…`에서 영어 단일턴 train1363/val76개. `aya_collection`과 **다른 저장소**다 | 원 영어 QA의 교정 EN + 교사 번역 KO | 같은 `parent_concept_id`, 두 언어를 독립 사실2건으로 세지 않음. 카드 Apache-2.0만으로 사람 품질/PII PASS 아님 |
| OASST2 | 별도 `OpenAssistant/oasst2` revision `179dd21…`의 reviewed 단일턴 영어5400·한국어5. 공개 v3 첫 질문 겹침/자체 중복 제외 후 영어3824·한국어1개 계열; 영어 질문/답 각각1200자 이하로 제한하면 새로운 계열2018개 | 원 EN 교정+KO 번역; 원 KO는 한영 양방향 **canary 1개**만 | OASST1 v3와 이름을 혼동하지 않음. OASST2 reviewed EN 멀티턴2378은 이 Stage2k **단일턴** 작업표에 자동 편입하지 않음 |
| 국립국어원 JSON | 지정 2026-08-19 JSON11개, 뜻풀이76,833개/고유 표제 target ID53,671. `concept/word-*.txt` 27개와 TXT2는 표제어 **선정 우선순위/교차검증**이지 새 독립 QA 행이 아님 | 의미 ID·품사·동형어·용례 근거로 KO QA; 실제 KO 교사 답이 생긴 뒤 별도 EN 번역 child | 현 작업표는 원문 뜻풀이/용례를 출력하지 않는 locator76,833건만 설계. `target_code+lexicalUnit+sense+file/ordinal`로 ID 충돌 회피; 사이트 CC BY-SA2.0 KR 정책과 로컬 판본 파생·배포 계약 별도 검토 |

Stage2kW 읽기 전용 실사에서는 public Aya 양언어 job2,878개, OASST2 양언어 job7,650개, 사전 한국어 의미 locator76,833개 등 **87,361개 job**을 계수했고 사용자 [원본 결과101 §23](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에서 같은 수를 재확인했다. 이것은 **교사 답안/독립 지식/학습 토큰 수가 아니다**. 사전 뜻풀이 하나에서 한국어 QA를 생성한 뒤 영어 번역 child를 만들 때도 부모 의미 ID와 train/val split이 고정된다. 공개 Aya의 기존 v3 split을 유지하고 OASST2/사전은 원천 concept hash로 *생성 전에* split한다. 정규화된 첫 질문이 v3와 겹치는 OASST2는 제외한다. 모든 job은 source repo·revision·원본 SHA·object/sense ID·변환종류·부모 concept ID·언어·rights 상태를 갖는다. **당시 Stage2kW는 읽기 전용**이었으며 구 통합 `--execute` 설계의 공개+사전 locator 같은 출력 디렉터리와 보호 source rights attestation는 실제로 실행되지 않았다. 사용자 권리 분리 회신 후 이 구 출력 경로는 폐기하고, 아래 Stage2kWb의 공개 job만 별도 네임스페이스에 쓰도록 변경한다. 사전 파생 원문·후보·학습 corpus는 여전히 만들지 않았고 별도 격리/권리 판단 대상이다.

### Stage2kWb — 공개 원천만의 분리 job deck, 사전 계열은 읽기도·쓰기에도 포함하지 않음

Stage2kW의 87,361건 전체를 한 데이터셋으로 출력하면 사전의 CC BY-SA 계열 locator가 공개 Aya/OASST2와 같은 산출물에 들어간다. [새 공개 전용 관리자](../scripts/build_p106b_multisource_deck.py)의 `--execute`는 `HF/sft_ready/p106b_public_job_deck_v1/`에 **Aya Dataset 2,878 + OASST2 7,650 = 예상10,528개** public source job만 write-once 20,000,000B 이하 JSONL 샤드로 기록한다. `source_family/repo/rights_status/protected_locator`의 네 조건 중 하나라도 사전·미지 출처이면 출력 전에 거부한다. **이 실행 모드에서는 지정 보호 사전 폴더를 읽지 않는다.** `--check-only`는 기존 Stage2kW와 같은 87,361 job read-only 합계이며 공개 전용 실행과 동일한 분모로 혼동하지 않는다. 다음 단계의 실제 교사 답/학생 target은 아직0이다.

[별도 사용자 CPU SH](../run_P106B_Stage2kWb_public_only_job_deck.sh)는 새 smoke PASS 뒤 self-test→격리 회귀→공개 `--execute`만 실행한다(예상≤0.1h, GPU0). 출력 디렉터리가 이미 있으면 덮어쓰지 않고 실패하며, 샤드 SHA·행수/총byte와 공개 source id/split을 검산한다. 사전 계열의 미래 물리 네임스페이스는 `HF/sft_ready/p106b_krdict_by_sa_quarantine_v1/`로 **별도 예약만** 하며 이번 SH가 만들지 않는다. CC BY-SA로 분리된 데이터 행을 공유할 때의 표시·동일조건, 개념만 사용한 독립 새 행인지 여부, 모델/출력 공개 때의 권리 판단은 각각 다른 문제다. 폴더 분리나 교사 문장 변환이 자동 법적 면제라는 주장은 하지 않는다. 공식 [사전 정책](https://krdict.korean.go.kr/kor/kboardPolicy/copyRightTermsInfo)과 [CC BY-SA 2.0 KR 법문](https://creativecommons.org/licenses/by-sa/2.0/kr/legalcode.ko)은 저작물 변형 배포/편집물 구분을 명시하며, [CC의 AI 학습 해설](https://creativecommons.org/using-cc-licensed-works-for-ai-training-2/)은 모델·출력의 실제 표현 재현과 공개 맥락을 별도 판단 대상으로 둔다. 이 단계는 법률 자문이나 사전 파생 학습 승인이 아니다.

### 사전 파생 3안·모델 원문 재현 검증 — 사용자 1안 선택, 실제 생성 `NOT_RUN`

사용자 제안대로 **사전 파생 행을 공개 자료와 다른 디렉터리·manifest에 저장하고 Git에서 제외**하는 것은 혼합 방지의 첫 단계다. 다만 훈련 로더의 `source_family/rights_status` allowlist와 같은 concept/문장 교차 검사, 원본→교사 후보→검토본의 SHA/부모 계보가 없으면 파일을 복사·재직렬화할 때 다시 섞일 수 있다. 현재 공개 전용 writer의 synthetic 회귀는 보호 사전의 읽기·출력0만 증명한다. 아직 사전 파생 writer/학습 로더 소비 경계는 없다.

| 후보 | 만들 데이터 | 라이선스·품질 경계 | 비용·권장 |
|---|---|---|---|
| **A: CC BY-SA 격리 후보** | 뜻풀이·용례를 교사에게 주어 만든 질문/답·교정본을 `p106b_krdict_by_sa_quarantine_v1`에 별도 저장, 원본 표현과 생성 이력 기록 | 사전 표현에서 파생된 행으로 **보수적으로** 분류하고 출처·변경·CC BY-SA 표지를 유지; 공개셋/일반 trainer에 자동 병합 금지. 학습모델 자체에 동일조건이 자동 전염된다는 주장도, 반드시 무관하다는 주장도 하지 않음 | 가장 빠른 한국어 근거형 pilot. 사용자 분리 요청과 일치하나 배포·모델 출력 검토가 남음 |
| **B: 의미요소→새 예문→새 정의 재합성** | 첫 교사가 원 `표제어+정의`에서 의미·품사·조건을 추출하고 새 예문 작성. **다른 문맥/작성자**는 원 정의·원 예문을 보지 않고 `표제어+새 예문`으로 정의를 다시 쓴다. 세 번째 검토자가 새 세트의 뜻·용례 일치 확인 | 사용자 제안의 이중 재구성을 개선했지만 단계1이 원표현을 보므로 법적 독립성은 자동 보증 안 됨. 원문/재합성본은 별도 계보로 두고 드문 장문·고유 문구 겹침과 의미왜곡을 검토할 때까지 A와 같은 격리 상태 | 표현 거리 증가 가능, 교사 비용·환각/뜻 변화 위험 증가. 독립셋 승격은 별도 사람/권리 검토 후 |
| **C: 독립 원천 clean-room** | 표제어·일반 개념만 선정하고 독립 사용허락 원천 또는 원문을 보지 않은 작성자가 뜻·예문을 새로 만든다 | 사전 예문·정의는 작성자/교사 입력으로 전달하지 않으며 출처·질문 분포를 별도로 기록. 독립 창작 주장도 최종 표현/권리 검토 필요 | 법적 분리 설명은 가장 명료하지만 한국어 뜻의 정확한 sense 대응과 제작 시간이 비용 |

**모델 재현성 점검 설계(미실행):** 같은 부모/토크나이저/질문셋에서 사전 미사용 대조와 사전계열 사용 후보를 비교한다. (i) 원문 중 **드물고 긴** 예문 앞부분을 준 완성 질문, (ii) 원문 문구를 주지 않은 의미 질문, (iii) 동일 길이·주제의 공용표현 및 사전 외 독립 문장 대조를 나눠 생성한다. 원문/출력의 연속 일치 최장 길이, 드문 n-gram·근사 표현을 **후보 추출**에 쓰고 문장 길이·표제어 빈도·공용표현 배경율을 맞춰 오탐을 보정한다. [GPT-3 중복 분석](https://arxiv.org/pdf/2005.14165)은 짧거나 흔한 문구의 오탐을 지적했고, [암기 계측 연구](https://arxiv.org/abs/2202.07646)는 중복·프롬프트 길이에 따른 원문 재현 차이를 보고했다. 높은 점수 행은 독립 사람이 원문·출력의 창작적 표현/맥락을 직접 검토한다. **n-gram 일치만으로 침해·파생 판정하지 않으며 0건 탐지도 암기/권리 문제 부재를 증명하지 않는다.** 보호 예문과 생성 원답은 ignored 격리 저장에만 두고 Git·일반 벤치 원본에는 넣지 않는다.

사용자는 **A안부터** 진행하고, B안의 새 예문/새 정의 후보와 A안·원문 간 표현 유사성은 **사후 비교**하기로 확정했다. [격리 어댑터](../scripts/p106b_rights_isolation.py)는 사전 원문 없이 합성 fixture만 사용해 다음 보조 계약을 구현했다: 원본 locator+SHA를 가진 `krdict` job만 받아 교사 내용의 질문/답을 코드 소유 canonical로 감싼 다음 `CC_BY_SA_2_0_KR_CANDIDATE`·출처 URL·`training_eligible=false`·`independent_expression_status=NOT_DETERMINED`를 붙인다. 이것을 다시 `P106B_RESTRICTED_CANDIDATE_V1`의 **상위 envelope**로 감싸, 일반 `load_canonical()`이 경로만 받아 학습셋으로 오용하면 `messages` 부재로 실패한다. 1~128행 write-once pilot writer는 오직 `HF/sft_ready/p106b_krdict_by_sa_quarantine_v1/candidates/`에만 기록하고 공개 job 디렉터리와 다른 SHA 샤드를 쓴다. 합성 CPU 자기시험은 이 격리·재입력 실패를 확인했으나 실제 사전 뜻풀이/용례를 읽거나 교사에게 전달하거나 파생 행을 만들지 않았다. 현재 저장소 `.gitignore`·`.agents/project.json`은 `HF/`를 제외하지만 Git 강제 staging 위험까지 자동 제거하지는 않으므로 향후 커밋은 명시 경로만 검토한다. A안의 실물 교사 후보 생성·원문/후보/B안 비교와 모델 출력 유사성 검사는 별도 사용자 실행/계획 선결이며 `NOT_RUN`이다.

교사관리 코드의 `teacher_admission()`은 향후 같은 localhost 교사 서버의 `/apply-template`·`/tokenize`에서 정확 입력 토큰을 받은 뒤 `DIRECT/COMPRESSION_REQUIRED/HOLD`를 반환한다. `wrap_teacher_answer()`는 **교사가 작성한 최종 태그 본문**만 canonical로 감싸고 source repo/revision/SHA·object/sense·변환 종류·부모 concept ID·권리 상태를 메타데이터로 고정한다. 교사 사고는 외부 raw sidecar 참조일 뿐 현재 학생 loss 대상이 아니다. 출처가 사전인 job은 승인된 조건에서도 영문 번역을 **같은 concept의 자식**으로 생성하지, 독립 지식 건수로 세지 않는다. 이 함수 계약의 합성 CPU 자기시험은 PASS지만 다원천 교사 실제 호출/정답성은 `NOT_RUN`이다.

**사용자 A안 확정 — 1,200자 규칙 폐기:** Stage2iWa의 `질문≤1200자·답≤1200자`는 `ctx3072/max2048`에서 약1024 입력토큰을 남기기 위한 거친 프록시였다. 이는 모델/토크나이저의 절대 제한이 아니다. Stage2jW의 **원천 약2461자**도 교사 chat template 입력817토큰으로 `817+4096<6144`였고 실제 실패는 PEG native-format 불일치였다. 새 관리자에서는 문자 기준으로 미리 버리지 않고, 요청 직전 서버 `/apply-template`·`/tokenize`의 **실제 입력토큰 + 출력상한 + 안전여유128 ≤ context**면 원문 그대로 쓴다. 미달만 `COMPRESSION_REQUIRED` 별도 child 작업으로 보내며 원문을 조용히 자르지 않는다. [교사 `compress_qa` 작업](../scripts/p106b_teacher_format.py)은 질문 의도·답 사실·부정·고유명사·숫자·단위·형식 제약 보존을 요청한다. [원천 관리자](../scripts/build_p106b_multisource_deck.py)는 **먼저 원천 언어에서** 압축 QA를 만들고, 숫자·부정/필수 리터럴의 보수적 누락 검사를 거친 후에만 원래 목표 언어의 번역/교정 child를 생성하도록 부모 concept/split/생성 ID를 계승한다. 한국어 번역 목표를 원천 영어 압축 단계에 섞지 않는다. 이는 **의미보존의 충분조건이 아니므로** 압축본의 원문 대조/표본 품질 확인 전 학생 target으로 자동 채택하지 않는다. 너무 긴 입력이 압축 프롬프트에도 안 들어가면 문단 근거 분할 또는 HOLD이지 무근거 앞부분 절단이 아니다. 지금은 이 함수 계약의 CPU fixture만 PASS이며 실제 teacher 압축·새 한영 토큰 균형은 E2E `NOT_RUN`이다.

**규모 경계:** 사전76,833 의미 ID와 공개 약5,264 원천 concept을 각각 한 번 100토큰 대화로 바꾸어도 대략8M토큰 규모의 거친 계산에 불과하다. 300M 비패딩 처리토큰의 4epoch 하한인 고유75M에는 한참 모자랄 수 있다. 5회 처리율·생성 답 길이·거부/근사중복률 실측 전에 이 작업표만으로 300M/600M 완주 가능하다고 주장하지 않는다. 사전 한국어 자산은 [국립국어원 공식 저작권 정책](https://krdict.korean.go.kr/kor/kboardPolicy/copyRightTermsInfo)의 표시/동일조건을 로컬 판본·파생물/배포 방식에 적용하는 결정을 별도로 받아야 한다. 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

### Stage3W/Stage4W — 300M 먼저, 한국어 평가 통과 때만 600M (조건부)

사용자 정의 300M~600M은 **학생이 학습 중 실제 처리한 비패딩 직렬화 대화 토큰**이다. 이는 300M 고유 행이나 assistant 지도 토큰이 아니다. `micro8×accum16×seq1024`의 `2289/4578`은 패딩이 매번 seq1024까지 채워진다는 가정에서의 명목 step이며 실제 가변 길이 SFT 토큰 수를 보증하지 않는다. 향후 trainer는 처리/지도/패딩 위치/언어/고유 concept·epoch-equivalent를 런타임에 따로 세고 비패딩 목표에 도달하면 중단해야 한다. 2~4epoch 범위와 과적합 방지를 위해 300M에는 적어도75M, 600M에는 적어도150M의 고유 직렬화 토큰을 최저 문턱으로 두며, 같은/유사 concept를 seed만 바꿔 복제해 이 문턱을 채우지 않는다. 현재 고정16은 고유2,040토큰·명백 오류8이라 턱 밖이다.

1차 소형 장면 패널에서 포맷 완결·답안 문맥/사실 결함·한영 토큰율·중복·accepted row당 교사 output token/시간을 관찰하고, 다음 bounded shard에서 처리량이 유지될 때만 30M→100M→300M 학생 단계로 확장한다. 600M은 300M의 한국어/영어 직접답·형식·단기기억·논리·forgetting/오답 유형을 본 뒤 별도 조건부 승인이다. 교사 원천은 독립 지식 검증형 P106 `ACCEPT`가 아니라 `PSEUDO_UNVERIFIED` pilot이며, 사용자의 요청대로 오류 자체를 사전 전수 정답화하지 않아도 되지만 명백한 형식/PII/원천 누설과 반복복제는 기록·거부한다. 같은 부모와 같은 노출량의 교사 없는 대조가 없으면 교사 기여를 단독 인과효과로 주장하지 않는다.

### Stage1cW — 같은 부모와 SFT 자식의 고정 공개 벤치·오답 회수

[posthoc 비활성 템플릿](../scripts/templates/P106B_Stage1cW_parent_student_posthoc.sh.in)은 Stage1b의 checkpoint·데이터셋 SHA를 먼저 대조하고, 기존 P076 mean과 새 P106B 학생을 **같은 legacy tokenizer·형상·P100 고정9문항×두 프롬프트 형식**으로 생성하도록 설계했다. 원답36행을 [P100 답안 triage](../scripts/diag_p100_answer_triage.py)로 보수적으로 분류하고, KLUE YNAT·NLI·ARC Easy는 공개 자산에서 과제별 `n=512, seed=99`를 같은 두 모델로 재며 문항별 gold/pred/마진·건너뛴 사유를 각각 저장한다. [paired 오답 진단기](../scripts/diag_p106b_posthoc.py)는 정답률/오답률과 부모만 맞음·학생만 맞음·둘 다 오답을 분리하고 회귀한 문항 ID를 사람 검토로 보낸다. 사용자가 미래에 활성화된 SH를 실행하면 기존 벤치 계약대로 **W&B에도 요약이 전송**되지만, 로컬 문항별 원본이 정본이며 Codex는 전송을 실행하지 않는다. **각 과제512문항 표본과 P1009문항은 정식 전체 벤치가 아니고**, 두 모델 전후 차이는 추가 학습 효과이지 교사 방법의 인과효과 단독 증명이 아니다. 틀린 문항의 사실·한국어 뜻·형식·맥락·추론·반복·원천번역 오류는 저장 원답을 사람이 직접 분류한다.

### Stage2W — 한국어 품질·멀티턴 진단(조건부, 아직 런처 없음)

Stage1a/b에서 관찰한 실제 완성률·교사 출력토큰/벽시계와 저장된 `v1` 교사 원답을 보고 OASST2 한국어 번역을 더 넓힐지, 근거형 C자료를 섞을지 결정한다. **사람의 전수 사전승인을 학습 시작의 필수조건으로 두지 않는다.** 다만 그 출력을 검증형 `ACCEPT`라고 부르지 않고, 대표 32행 이상을 **학습 후** 문맥·번역 충실도·안전성 오류로 표본 감사해 `v2` 수정 우선순위를 만든다. 같은 P076 부모·legacy tokenizer·고정 질문·평가원천/학습 노출량의 `교사 pseudo-label` 대 `교사 없는 원천/독립 편집 답안`을 최소 2시드로 비교하고, 사용자 허용 범위의 2~4 epoch·유니크 행수·누적 assistant 토큰을 함께 기록한다. base full-val 망각, 한국어/영어 직접답·형식·다회전 원답안, 정답률·오답 유형을 별도로 본다. **이때만 지능·SFT 적합성 후보 판정**을 검토하며, 원천·평가 겹침/사용권이 미결이면 능력 승격은 보류한다. Stage2의 학습량·GPU 시간은 Stage1a 완성률과 고유 번역량 없이 아직 산정할 수 없어 본런 SH를 서둘러 만들지 않는다.

> **2026-09-27 경로 교정**: 위 Stage2W 문단의 `v1` 번역 확대와 `v2` 수정은 최초 A안의 역사 설계다. 실제 사용자 선택은 원답 교정 D안이며, 새 v4 **미검증 후보**의 근거·거부/불확실 상태를 검토한 다음 별도 선정본을 만들어야 한다. Stage1fW의 형식 PASS만으로 학생 SH를 열지 않는다. 이 단계의 2~4 epoch·동일 노출 no-teacher 대조와 한국어 멀티턴 원답안은 여전히 별도 사전등록·미실행이다.

### 대체 데이터 경로 B/C — 같은 분모로 섞지 않음

| 안 | 교사 역할 | 독립 근거와 실제 차이 | 현재 범위·대가 |
|---|---|---|---|
| A 역사 초기 권장 OASST2 영어→한국어 | 번역·표현 교사 | 사람 참여 원답을 보존하지만 원답 오류도 그대로 옮김(결과101 WebRTC) | **형식 gate에는 사용**, 현재 교육원천 권장안 아님. v1 번역9/16 미달·원답 사실 오류 |
| B 프로그램 정답형 QA | 한국어 문항/답변 표현 교사 | 정답은 solver가 계산해 오류 자동 거부, 내용 폭은 좁음 | 가장 안전한 배선 대조. 대화 지능 일반화 근거 없음 |
| C `concept`+국립국어원 뜻풀이 | 근거 문장에서 질문·답 형식과 쉬운 설명을 만드는 교사 | 목록 자체는 27파일·38,089줄의 **단어만**; CP949 ‘4만 어휘’ 40,000행 의미 열은 전부 채워지고 concept 고유37,810 중37,720 표제어 일치. 뜻풀이·동형어 번호가 근거이지만 용례 전용 열은 없음 | 사용자가 정확 경로 읽기만 승인. [한국어기초사전 저작권 정책](https://krdict.korean.go.kr/kor/openApi/openApiRegister)의 저작자표시·동일조건변경허락 적용 가능성을 파일 계보/산출물 사용 방식과 대조하기 전 학습 원천 미채택. 원문 수정/복사·SH 입력 자동 연결 금지 |
| **D 사용자 선택: OASST2 원답 교정 후 한국어 QA** | 교사는 원답을 무조건 번역하지 않고 오류 교정·불확실성 표시 | Stage1dW 3/3 JSON·WebRTC API 사실 복구. 그러나 GPT‑3 수치 새 오류로 자기수정은 verifier 아님 | 새 v4 full16 후보를 먼저 생성하고 원천/교정 근거를 점검한 **별도 선정본**만 후속 학생 실험에 사용. 전수 사람 사전승인은 기술 필수조건이 아니나 명백한 오답 자동 수락 금지 |

C 원천을 사용자가 승인한 **정확 두 파일만** 추가 실사했다. `/mnt/z/TinyDataset/참고용외부데이터/국립국어원/한국어기초사전/한국어기초 어휘(4만개).txt`는 CP949·40,000행/고유 표제어37,720·의미 nonempty40,000·동형어 최대10행이며 SHA-256 `463CF0D5204B31991D1004C2C553BA3AD2354D62CF7BF15B2DBE541E043F03FA`다. `한국어 학습용 어휘 목록.txt`는 CP949·5,965행/고유5,858, `풀이` nonempty4,009 중 한자 포함3,290·한글 포함487로 **뜻풀이 정본이라기보다 원어·표기 성격이 강하다**(SHA `3B49681F05D6A7490C13DA2A2847E433EFFDF65DA409FD295792D6EE33685064`). 두 자료 모두 별도 `용례` 열이 없고 현재 SH는 어느 보호 원본도 읽지 않는다. 공식 누리집의 이용조건이 이 로컬 추출본의 정확한 취득 경로·파생 dataset/모델에 어떻게 적용되는지는 별도 검토 대상이다.

사용자가 추가로 지목한 **정확 `한국어기초사전_json_20260819/` 폴더**도 2026-09-28 읽기 전용으로 실사했다. 11개 정규 JSON·약969MiB, 내부 `LexicalResource`/`Lexicon` 구조의 LexicalEntry **56,555레코드/고유 `val` ID53,671개**, Sense76,833개 모두 `definition` 보유, SenseExample594,578개 중 텍스트594,294개였다. 영어 Equivalent75,145개를 포함한 11개 언어 Equivalent 총826,505개이며 `homonym_number`·품사·어휘등급·의미 범주도 있다. 따라서 **뜻풀이·용례·영어 대역이 없어 word 목록만으로는 못 하던 근거형 한영 QA 후보**를 기술적으로 만들 수 있다. 그러나 ID 중복2,884건은 전부 같은 파일 안에서 발생하고 표본은 같은 target ID에 관용구 레코드가 붙은 경우였다. ID만으로 중복 제거하면 관용구·속담을 지울 수 있으므로 `target ID+lexicalUnit+Sense+원문 해시` 계보가 필요하다. 용례의 `대화` 유형63,436개는 중앙 길이23자이고 확인한 발화자 표지형 쌍은0건이므로 **멀티턴 user/assistant 정답 자료로 즉시 래핑할 수 없다**. 용례의 `type=1` 343건과 텍스트 빈 예284건도 parser 검증 대상이다.

JSON 내부에는 `한국어기초사전 - 국립국어원 제공`, 생성시각 `2026/08/19 12:38:21`은 있지만 이 11파일 안에 별도 LICENSE/다운로드 receipt는 보이지 않았다. [공식 전체 내려받기](https://krdict.korean.go.kr/download/downloadPopup)는 JSON 제공을 확인하고, [공식 저작권 정책](https://krdict.korean.go.kr/kor/kboardPolicy/copyRightTermsInfo)은 별도 표기 없는 텍스트에 CC BY-SA 2.0 대한민국의 저작자표시·동일조건변경허락을 명시한다. 이는 **이 로컬 8월판의 정확 취득·예외 여부와 파생 SFT/모델의 배포 의무를 자동 확정하지 않는다**. 지금은 열거·구조/계수만 했고 JSON 문장·뜻풀이를 HF로 복사하거나 교사에게 전달하지 않았다. 사용자/권리 확인 뒤 별도 source manifest·출처표시·split/중복/PII·의미/용례 parser 검사를 통과한 **새 버전**에서만 활용한다. 기존 Stage2iWa/b/c의 OASST2 공개 원천과 혼합하지 않아 온라인 처리율 비교축을 보존한다.

기존 `ko-en`의 **단순 다음토큰 캐시**를 교사가 질문·답으로 변환하는 네 번째 후보도 가능하지만, 토큰 `.bin`의 임의 1024 경계를 그대로 질문으로 삼으면 문서 출처·완결 문맥·근거 답의 경계가 없다. P037에서 기존 300M/600M train–val 동일 EOS 문서 2/6건이 확인돼 문서 ID·공통 val 누출 정리가 먼저다([결과023 §12](../test_result/023_20260802100000_P037-단계2-필터는작동-검증이엉뚱한캐시를쟀다.md)). 사용하려면 승인된 공개 원문 문서에서 근거 범위를 고정하고, 교사가 질문과 답을 생성하되 원문 인용 위치·문서 계보·QA 오류를 별도로 보존해야 한다. 지금의 Stage1a/b는 이를 OASST2와 섞지 않는다. 기존 공개 v3 canonical 3,154행을 교사가 재표현하는 길도 있지만 한국어 비율5.83%·사람/오염 gate 미완을 해결하지 않으므로 P090B와 분리해 후속 비교한다.

### Stage3 — 사용자 승인 생산성·재사용·통합 게이트 (2026-09-30 역사 설계·원통합 HOLD)

**현재 상태와 역사 범위:** 아래는 당시 사전등록 조건이며 수치·문턱을 바꾸지 않는다. 독립 C4/B2/B4 등 실제 실행은 결과101 §31, 두 슬롯 A1 음성과 단일 슬롯 A2 겹침은 §32, 후속 단일 슬롯 통합128행/1업데이트 완료는 §33이 소유한다. 원2slot 통합3fW와 원3g0/g는 원선결 미충족으로 모델/새 교육0을 보존한 HOLD다. 후속1slot의 성공으로 그 원형을 소급 통과시키지 않는다. 따라서 이 역사 설계를 새로 실행할 첫 단계로 반복 안내하지 않으며, 현재 작업은 위 머리말과 끝의 야간 계획·실제 회수를 따른다.

**선택 회수:** A1/A2 모두 독립 테스트, B2→4, C4 실제4epoch, 모두 해당 문턱을 통과하면 통합1 optimizer다. 통합은 C reader의epoch1만 쓰고4epoch 완료로 부르지 않는다. 그 다음 통합에서 보존한 자료를 별도 train/val로 나눠 작은4epoch 교육을 준비한다. 보호 원천은 연결하지 않으며 학습량을 맞추기 위한 수백회 재사용도 하지 않는다.

| 단계 | 독립 질문·설계 | 선결·판정 | 예상 / hard cap |
|---|---|---|---|
| Stage3c0W | exact v17 raw/canonical SHA128행을 concept와 정규화 첫질문 모두 겹치지 않게 분할, train100/val28 | 새v19 존재하면 중단; 교사·학생 모델0 | CPU0.1h |
| Stage3aW A1 | 한 교사 weight copy,1→2→2→1slot ABBA, 각 KO4/EN4·같은 seed, slot당ctx3072/output2048; 학생 부모는 상주 | 두 순서 쌍 모두 유효 student tok/s 비율>1.05,각 언어≥3/4·2slot 수락행 수 감소 없음; 별도 active 학생16행 자원 업데이트·NVML/GDN 정상 | GPU0.9h /2h |
| Stage3bW A2 | 같은16 source의 serial 대1slot producer/consumer 겹침. 원형/후보 durable 저장 후 최대32행·20MB RAM queue; 첫8행부터 학생 계산 | 각 언어≥6/8, 실제 teacher/student 시간구간 overlap, 건강한 계측/finite gradient. 실효 배치는최대16행, 부분누산2micro 이하임을 공개 | GPU0.8h /2h |
| Stage3dW B2 | 한 질문→짧은 답/짧은 설명2개. 한 응답 순차 decode, 두 독립 sequence가 아님. ctx6144/output4096 | KO/EN 각각≥3/4 complete 그룹,2/4 exact태그·학생≤1024·canonical/마스크 검사. 의미모순 판정은 사후 원답 검토 | GPU0.5h /1h |
| Stage3eW B4 | B2 통과 뒤 같은질문4개 스타일, ctx12288/output8192 | B2 source/code 일치, 동일 형식/자원 문턱. B4도 통합 선결; 첫 통합은 자원통제를 위해 더 작은B2 고정 | GPU0.7h /1h |
| Stage3cW C4 | 원부모에서 새v19 train100행을 정확4pass, epoch마다shuffle; 같은질문/개념 전체는 같은split. micro8/accum최대16·ckpt-on | 실제4 optimizer·비패딩78,260/지도57,852; 짧은100행 그룹을128로복제하지 않음. parent/after full-val2,929crop·SFTval·고정답8×2. base CE악화≤.1nat, SFTval악화≤.1nat는 **운영pilot 안전선** | GPU0.4h /2h |
| Stage3fW 통합1 | A1/A2/B2/B4/C4 현재 code·source·parent·tokenizer SHA PASSED 후,1서버2slot·slotctx6144·B2·bounded queue·Cepoch1 보존64+새변형64 | micro8×accum16·한 optimizer만, 옛v17 concept는 새생성에서 제외; fresh KO32/EN32·형식/손실/gradient·NVML/GDN. 체크포인트0·품질 NOT_RUN | GPU0.8h /2h |
| Stage3g0W→gW | 통합128행을 새v25 concept/prompt-disjoint split로 준비한 뒤 원 P076 부모부터 정확4pass의 소형 실제 SFT | 통합1 PASSED와 SHA가 선결; 같은 full-val·SFTval·고정원답/망각 기록·새ckpt/JSON. 실제처리토큰/부분유효배치 공개 | CPU0.1h+GPU0.4h /학습2h |

A1의1.05 문턱은 이 pilot의 작은 order/noise 여유이며 통계적 신뢰·모델 품질 자가 아니다.2slot은 총context를2배 배정하므로 같은 **slot별** budget 대조이지 같은 총KV 크기 대조가 아니다. A1 active 자원 업데이트는 속도 ABBA를 끝낸 뒤 별도 수행해 optimizer/allocator 상태가 중간에바뀌는 교락을 피한다. A2는 serial-first/cold compile와 생성문구 차이가 남으므로 전체wall 비율을 제시해도 원인적 속도 채택은 하지 않는다. 통합에서ctx/variant길이 증가에 따른 자원은 별도로 다시 fail-closed 확인한다.

**자료/교육 계약:** teacher thinking은 raw sidecar에만 남는다. tag 파서와 canonical/ChatML·assistant-only mask는 코드가 소유하며 교사에게 JSON·학생토큰ID를 만들게 하지 않는다. 모든 다중답은 같은 `parent_concept_id/source_split`·변형번호로 묶고 신규 지식 수를 부풀리지 않는다. 새 버전 v19~v25·실제 사용된 generation ID·source/SHA·처리토큰·수락/거부·code 계약을 남긴다. partial/interrupt도 원형을 버리지 않으며 기존 version을 지워 재실행하지 않는다.

**조건/비교 한계:** 학생은 P076 mean SHA `41036721...F5D00A71`, legacy32 SHA `3A69001E...52C48E3`, Muon RMS4×4+AdamW·lrs1e-4/4e-4·WD0·KDoff·ckpt-on/compiledefault다. ChatML SFT 형식을 쓰지만 chat32 특수토큰 단일ID 계보 모델은 아니며 새tokenizer를 옛parent에 잘못 끼우지 않는다. C4 checkpoint 태그 `p106b_s3c_repeat4_s1337`, 후속 `p106b_s3g_followup4_s1337`은 새출력/미존재 guard를 갖는다. 일반registry의 전 `runs/` JSON 조회는 승인범위 밖이라 하지 않고 정확 두 output/metadata 미존재·기준표 tag 예약·기존 result/계획 비교로 대체했다. pretrain 풀2× 규칙은 이 의도적4epoch SFT의 독립일반화 증거가 아니다.

**반복 근거:** P087 결과073의4배는 큰300M 풀에서 복원추출1.2B노출이었다. 그 조건에서 과적합 신호가 없었지만 이100행 assistant-only exact4pass와는 pool/목적/optimizer가 다르다. 따라서 C4의 held-out CE·base full-val·실제 답안·노출횟수 자체 기록을 생략하지 않는다. 새 SH9건의 CPU회귀10/10은 운영계약만 확인했고 실제 속도/OOM/교육효과는 NOT_RUN이다.

> 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.


### Stage3aWb/3bWb — 2026-09-30 사용자 A 승인: 옛 실패를 보존한 별도 재시험

A1의 원본 v22는 두 쌍 중 첫 속도비1.140×만 1.05를 넘었고 역순은1.015×, KO형식은1~2/4였다. A2의 v23은 고정16교사 요청 중 KO4/8·EN6/8이라 serial에서만 partial10행과 학생 일부 backward를 남기고 optimizer/실제겹침0이었다. **이것은 도구 전체 실패가 아니라 사전 형식 문턱의 음성**이다. 그러나 A2 최상위 `arms=[]`는 partial serial 원형을 보여 주지 못한 기록 결함이므로 새 코드에서는 `serial/arm_manifest.json`이 있으면 상위 요약에도 `partial_arm=true`를 남긴다. 기존 v22/v23 JSON·문턱은 수정하지 않는다.

| 새 단계 | 변경축·불변축 | 사전 판정과 비용 |
|---|---|---|
| Stage3aWb | 한 교사·같은 공개원천/부모·low sampler, **질문군 언어당4→16 / slot당ctx3072→6144 / output2048→4096**; 새 v26, ABBA1→2→2→1 | 각 팔 KO·EN 각각≥12/16 형식 완료, 두 순서쌍의 유효학생자료 tok/s 모두>1.05, 두 슬롯에서 완결행 감소0, 활성학생16행 공존·GDN/VRAM 계측 정상. ⚙1.5h·hard2h. 형식 회복·속도 증가/OOM안전은 사용자 E2E 전 NOT_RUN |
| Stage3bWb | 같은 원천/부모·low, **질문군 언어당8→16 / ctx3072→6144 / output2048→4096**; 새 v27, serial→durable producer/consumer | serial·overlap 각 KO·EN≥12/16, 실제 교사/학생 실행구간 겹침, 표본VRAM·finite loss/gradient. 각 팔 최대32행의 부분누산이며 128행 본학습·인과적 속도채택은 아님. ⚙1.0h·hard2h. E2E NOT_RUN |

출력예산과 표본을 **동시에** 바꿨으므로 옛 v22/v23과의 속도 차이를 한 변수의 효과로 귀속하지 않는다. 큰8문항 B2/B4가 각4/4였다는 관측은 출력 상한 가설의 근거일 뿐 확증이 아니다. 새 A1도 문구·학생대화 길이가 팔별로 달라 순서교차와 수락행 수를 함께 본다. A2는 고정 serial-first 순서와 cold compile 때문에 실제 겹침이 있어도 전체 wall 차를 인과적 학습가속으로 채택하지 않는다. 두 새 런은 버전드 새 자료만 만들고 현재 v19~v23·원래 부모/체크포인트/결과101 원본을 변경하지 않는다.

### Stage3fWb — 사용자 선택 C: A1 음성을 보존하고 A2 단일 슬롯으로 통합 1업데이트

**예측과 대립 가설.** [결과101 §32](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에서 A1b의 두 슬롯 유효자료 속도비0.951/1.056×·수락행 감소가 문턱 실패로 확정됐다. 반면 A2b는 단일 슬롯 생산·소비 시간구간 겹침을 기능적으로 확인했다. 따라서 두 슬롯 가속을 요구하지 않는 **새 v28 통합 배선**은 한 optimizer 업데이트를 완성할 수 있다. 반대로 교사 출력 절단/PEG·작은 학생 자원 여유·고유 source 소진·actual overlap 부재가 이를 막을 수 있다. C4 답안 첫8문항0/8은 재시도 N회 실패가 아니며 v28 기능 성공이 이를 품질 성공으로 뒤집지 않는다.

| 단계·선결 | 실행 계약 | 사전 판정 |
|---|---|---|
| Stage3fWb CPU | 기존 v27 A2b 실제 겹침·같은 원문 SHA, v20 B2·v21 B4 형식, v19 C4 운영 안전선, 동일 부모/토크나이저/교사·공개 job deck SHA를 exact 검증. v22/v26 A1은 **불필요·비채택** | 읽기 전용 `--check-only`와 회귀 PASS여야 GPU 런처 안내 가능; 기존 v24 통합원본 불변 |
| Stage3fWb 사용자 GPU | `v28_integrated_a2_one_slot_low/` write-once, full-GPU 교사 한 벌·1 slot·ctx6144/output4096. C4의 보존 공개 행64(한영32씩) + 기존 v17 개념과 겹치지 않는 공개 원천에서 교사가 새 답64(한영32씩), 2답/질문. 교사는 `[[QUESTION]]`/`[[ANSWER_1]]`/`[[ANSWER_2]]` **내용만** 출력하고 코드가 원형 JSONL·canonical ChatML·assistant-only mask를 작성한다. 교육용 답은 `PSEUDO_UNVERIFIED`이며 사전 출처·보호 자료는 연결하지 않는다. | 학생 micro8×accum16·checkpoint ON, 정확128행/16micro의 optimizer1회·finite CE/gradient, 실제 생산·소비 interval 겹침·GDN/VRAM sampler 건강이면 **기술 기능0**. 형식/자원/원천 부족은 음성8, 도구 실패9; checkpoint0·held-out·교사 정답·지능/4epoch/300M 채택은 NOT_RUN |

교사 sampling은 [PrismML GGUF 카드의 thinking-mode 값](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf/blob/main/README.md) `temperature=1.0/top_p=0.95/top_k=20/min_p=0.05/presence_penalty=0/repetition_penalty=1.0`을 llama.cpp API의 `repeat_penalty=1.0`으로 매 요청에 명시한다. 현 서버 helper의 reasoning effort는 과거 low와 같지만 카드에서 low가 정식 지원되지 않아 xhigh 유사 동작 가능성이 있다. 비용·품질을 medium과 인과 비교하지 않는다. **새 단계에만** 하나의 concept당 최대3회: 처음은 원형 프롬프트, 출력 길이·형식·PEG·중복 등 retryable 실패면 다음 seed와 사유별 짧은 보정 지시로 재요청한다. 각 시도의 ID/seed/실제 교사 원형·사고 sidecar·분류·피드백을 20MB 이하 별도 shard/manifest에 보존한다. 요청 실패가 교육 정답성 실패라는 뜻은 아니고, 재시도 형식 통과도 사실성 승인이 아니다. full128 명목 위치131,072와 실제 비패딩/지도 토큰을 따로 기록한다. **비용:** 예상1~1.5 GPU시간·hard2h, 재시도 때문에 한도 내 부분 종료 가능. 새 사용자 smoke PASS와 GPU 단독 free≥14,000MiB가 선결이다.

**당시 Preflight:** 독립변수는 `A1 두 슬롯을 빼고 A2 단일 슬롯 생산·소비만 사용한 통합 배선`; 같은 부모/교사/토크나이저/공개 deck을 exact SHA로 묶었다. 기존 v24는 A1 음성으로 모델0이라 중복 실험이 아니었다. `8×16×1024=131,072`은 명목 위치이며 실제 학습량은 생성 길이로 달라진다. 64 보존+64 신규는 pretrain의 풀≥2배 기준을 만족시키려는 품질 런이 **아닌 기술 게이트**라 지능 채택 판정은 금지한다. 짧은 A2b 표본 peak10,845MiB는 v28 장시간 peak 보증이 아니었다. 실행된 `run_P106B_Stage3fWb_integrated_a2_one_slot.sh`의 네 재현명령과 실제 통합 결과는 [결과101 §33](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에 보존한다. GPU 실행은 사용자 소유다. 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

### Stage3cW 품질 사후 감사 — 운영 안전과 답변 능력의 반례

C4는 좁은 SFT-val CE3.700334→3.571472로 개선됐지만, 같은 base full-val 2,929 crop에서3.600580→3.619024(**+0.018444 악화**)다. `PILOT_SAFETY_PASSED`의0.1nat 운영 문턱 안이라는 이유로 악화를 지우지 않는다. 부모 고정8문항은 채팅 시작 마커를 반복했고 자식 고정8문항도 모두80토큰 상한까지 갔다. 자식은 산수·지식에서 질문을 되풀이하고 논리 문항은 내용은 관련 있으나 요구한 yes/no 형식을 지키지 못해 **요구 정답과 형식 동시충족0/8**이다. 현재 legacy32는 `<|im_start|>`/종료 마커가8/7개의 분절토큰이고, chat32는 ID3/ID4 한 개다. 직렬화기는 assistant 머리를 한 번만 붙이므로 중복 머리 생성이 구현상의 직접 중복삽입임은 관찰되지 않았다. legacy 부모의 채팅 표지 미학습·작은78k토큰 SFT·EOS만 멈추는 추론 경로는 원인 후보이며 **어느 하나가 유일 원인이라는 증거는 없다**.

동일 4epoch 소형 학습을 다시 반복하지 않는다. chat32 부모와 기존 legacy의 계보·prompt/종료 제어, 의미 있는 고정 원답 평가를 별도 후속으로 설계하고, 새 A1/A2의 생산성 결과를 먼저 회수한다. 현재 Stage3f/g0/g 런처는 사용자가 check-only로 시도해 음성8을 남겼지만 통합·새 corpus·학생학습 **0**이다. A1Wb/A2Wb가 추후 성공해도 v22/v23 기존 SHA를 재해석해 원래 통합런처를 통과시키지 않고, 사용자 의미·자원 판단 후 새 단계로 별도 사전등록한다.

## 5. 판정 기준·사전등록 범위

### Stage3hW~3mW — 통합 성공 뒤 자료교정과 두 부모의 4epoch 교육 (사용자 승인)

**A/B의 정확한 뜻.** A는 `runs/ckpt/m100R1c_ko-en_300M_p076_b3_ag2_mean_s1337.pt`(SHA `41036721...5D00A71`), 20층 tied/MLP g8·attention ag2·CLA2·legacy32다. B는 `runs/ckpt/m100s10_ko-en_300M_dense_chat32_p090b_s1337.pt`(SHA `12E18658CDCD0AFEBE5A87073DC8977304C0D490A03A8471779D514FBB0D9950`), middle10+prelude2+coda2=14층 dense·CLA2·chat32다. 같은 어휘크기32k라도 A의 ChatML 표지는8/7토큰, B는ID3/4 한 토큰이다. 서로의 tokenizer를 교차로 끼우지 않는다. B는 위키피디아 한국어/FineWeb-Edu 영어 `ko-en`을 **초기화 없음·KD off·Muon RMS4**로 2,289step/300,023,808토큰 사전학습했다([결과096 §9](../test_result/096_20260925_P090B-공개원천-구조후보-SFT-보류.md)). JSON의skip0/grad_max0.94927은 수치 실행 증거이나 실제 대화능력·지식 학습 충분성은 별도다. tokenmix KO34.3513/EN65.6487%, 실train597.995M<2×draw600.047616M의 부채를 유지한다. final sampleval3.6028125와best3.54625를 native full-val 또는 A의 loss와 섞지 않는다.

**예측.** 교정이 알려진 문자권/용어 결함을 줄이고 B의 단일 ChatML 표지가 형식 학습을 돕는 방향을 기대한다. 반대 가설은 교사가 새 사실오류를 만들거나 작은4epoch에서 답안은 여전히 반복하고 원래 언어능력이 나빠지는 경우다. B/A의 부모·구조·pretrain/tokenizer가 함께 다르므로 차이는 **설명 비교**이며 chat32만의 인과효과가 아니다. 보호 원천·신규 다운로드·교사추론 Codex 대리실행은 포함하지 않는다.

| 단계·실물 SH | 수행 | 선결/사전 판정·비용 |
|---|---|---|
| Stage3hW [B 부모 선평가](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md) | 정확 B SHA·metadata·자체 chat32 native val SHA 확인→GPU에서 결정적 native full-val, 실제 val prefix 한영 최대2개씩 continuation, 고정8질문 첫 답/최대3시도 raw | 새 smoke 먼저. 기술 평가 완료0이어도 답변0/8을 품질 PASS로 쓰지 않음. 한영 prefix 선별은 문자비율 heuristic·해당256crop창의 후보가 없으면 그 언어 NOT_RUN. ⚙0.75h·hard2h |
| Stage3iW [C 교사 교정](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md) | v28 training128행을 concept/언어/원질문 group으로 묶어 교사가 질문과1~2답을 교정. 기존 원본snapshot·새raw/canonical·선별본·각시도/변경요청·질문변경 기록을 별도v29에 보존 | B baseline 기술 report 선결. one teacher/1slot·thinking sampler/low·ctx6144/output4096, 최대3회; 각언어 group≥75%를 양 tokenizer context내 수락·known kana/오조어 화면 통과해야 기능0. **사실성은 PSEUDO_UNVERIFIED**, 일본어 인용의 정당성까지 자동판정하지 않음. ⚙2h·hard2h |
| Stage3jW [공통 원문 split](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md) | corrected selected SHA를 concept와 정규화 질문끼리 묶어 train/val; 양 tokenizer 길이/mask와 실제토큰/예상updates를 공개 | C report 성공·failure journal 없음, group≥10·split중복0. CPU⚙0.1h. 원본 v28 미수정 |
| Stage3kW [B4epoch](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md) | B 자기 부모에서 exact4pass, micro8×accum상한16·checkpointON·compile default·Muon RMS4 LR1e-4. 자기 nativeval·SFTval·고정8질문/같은nativeprefix before/after, 새 checkpoint/JSON 저장 | j 공통split·B어휘/SHA·newtag 충돌0. 짧은 마지막 그룹을128행으로 복제하지 않음. CE/gradient finite·4pass·자기 base/SFTval 악화≤0.1nat는 운영 안전선만. ⚙0.75h·hard2h |
| Stage3lW [A4epoch 대조](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md) | 같은 corrected raw train/val, A 자기 parent/legacy tokenizer/cache·나머지 학습 설정은B와 동일 | j 선결은 같되 B 학습 실패와 독립적으로 실행 가능. 기존 통합1 메모리 상태는 저장0이라 이어받지 않음. ⚙0.75h·hard2h |
| Stage3mW [답안 evidence 연결](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md) | 두 report·common raw corpus SHA·각 exact childSHA·고정문항8 전부 역참조, first와within3를 분리해 paired JSON | B/A 양 교육 report·raw answer존재. 자기 loss전후만 사용, A/B토큰CE 순위금지·사람 원문 판독필요. CPU⚙0.1h |

**답안 재시도와 정지.** 후속 학생 첫 시도는temperature0/top_k1·max_new160이다. 사전좁은8문항 rubric 실패 시 동일 문제+형식 재확인 지시, seed변경·temperature0.8/top_k40로2·3번째만 생성한다. first_attempt와pass_within_three를 별도 기록하고 모든 실패 raw를 남긴다. 교사 thinking sampler와 학생 probe sampler는 다르며, teacher retry를 사실성의 verifier로 쓰지 않는다. `sample(stop_token_sequences=...)`의 선택 옵션으로 자기 tokenizer의 `<|im_end|>` 단일/다중-ID를 생성부분에서만 감지한다. 기본 호출은 기존 EOS 동작을 보존한다. 과거C4 80토큰·재시도0과 지금160토큰·최대3회는 같은 실험조건이 아니므로 옛0/8을 소급 뒤집지 않는다.

**Preflight/한계.** 실제 split·각팔 비패딩/assistant토큰은 C 생성 후j manifest가 정본이다. 같은 raw행을4번 보는 교육이며 pretrain의 풀≥2배 조건을 품질 통과로 복사하지 않는다. A/B토큰수는 달라져 토큰손실 직접 비교불가다. tag `p106b_s3k_corrected_chat32_s1337`/`p106b_s3l_corrected_a_s1337` 충돌0, 기존 부모 쓰기0, 새 child는 각각별도 checkpoint/metadata다. 자료형식/자원0과사용자 실제능력/정식 TRAIN_READY는 구분한다. C전에는 양교육/분할 check-only가 prerequisite HOLD8이며 미구현 때문에 막힌 것이 아니다. 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

| 관측 | 판정 |
|---|---|
| Stage0 원본 SHA/선별 수16 미달·공개 v3 정확 질문 누출 | `HOLD8` 또는 입력결함 `FAIL9`, 교사 시작 금지 |
| Stage1a 구조화 완성 <12/16·wall>1800s·GPU 여유 미달 | **형식/자원 음성** `exit8`; 출력이 있어도 전부 미검증 후보 |
| Stage1b 교사 실시간 출력 고유 유효쌍<8/16·teacher/학생 OOM·표본 free<2GiB | 기능/자원 음성 `exit8`, 업데이트0 또는 부분 이력을 정확히 기록 |
| 형식/독립 loss 마스크 위반, 원본/부모/tokenizer SHA·태그 충돌, 프로세스/계측 오류 | 도구 실패 `exit9`, 품질 음성으로 오독 금지 |
| Stage1b 2업데이트·유한 gradient·assistant-only 지도토큰>0·교사 동시 생성 관측 | **기능 PASS만**. 번역 진실성·실무 학습속도·대화능력·정식 `TRAIN_READY`는 `NOT_RUN` |
| Stage1c 부모/학생 같은 P10036·공개 3과제×512의 문항별 원본·paired 추적 | **사후 진단 완료**. 회귀·개선 문항과 오답률만; 교사 단독효과·전체 지능은 `NOT_DECIDED` |
| Stage2iWe 공개 deck SHA·권리/비보호 계보·실제 token admission 후 1 optimizer/128개 fresh | 기능 PASS만; 누락·권리 경계·미상 token API는 tool fail9, 고유 원천/자원 고갈은 유효 음성8 |
| Stage2iWf가 동일 공개 deck SHA의 We 1회 PASS 뒤 5 optimizer/640개 fresh·샤드 SHA·언어별 실처리토큰 기록 | 처리율/공존 기능 PASS만. 단일 모델 품질·P106 ACCEPT·formal TRAIN_READY는 절대 아님 |

기존 P090B의 원천 manifest 세 필수 gate가 `PASS`가 아니어도 이 **분리된 미검증 연구용 2업데이트**를 정식 SFT로 표기하지 않고 수행할 수 있다. 이는 `train_sft_p090.py`의 formal fail-closed 규칙을 약화하는 것이 아니라 **다른 출력 네임스페이스·다른 목적의 실험**이다. 일반 SFT의 모든 답변을 독립 참으로 증명할 수 없으므로 Stage2의 실질 품질/모델 승격에는 고정 benchmark·오답 유형/번역오류 사후감사·동일 조건 대조가 필요하다.

## 6. 비용·자원

### Stage3nW/3n0W·3iWf~3mWd — 프롬프트 수리·사고상한 대응비교·배선/내용 분리 (사용자 두 A안)

**계기/예측 대조:** [결과101 §36](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md). 구v31 소형은실제KO다중답을2회완결했지만입력질문의오조어보존과내용검사가충돌해선택KO1/2·뒤5단교육0이었다. 이는출력이전혀없던v30과다르며포기의근거가아니다. 기존clean fixture가실제bad-question echo를시험하지않은빈틈을추가회귀로막는다.

**새 질문:** (1) 의도를보존하되질문/답의오조어를수리하라는명확한계약과위치별feedback이오류를줄이는가? (2) 동일한8K 사고/16K 전체/32K문맥에서요청low/medium/xhigh의실제완결·유효후보tok/s/원답은어떻게다른가? (3) 소형배선과전체내용gate를분리해도문제후보의학습을막는가?

**상한·실행분리:** total16,384는사고+최종답합계이며top-levelthinking_budget_tokens8,192를별도전달한다. 숫자값요청과실효사고토큰관측을같다고부르지않는다. 현재바이너리정적지원/공식문서·GGUFheader는확인했으나새효과/32Kpeak는NOT_RUN이다. modelcard의low경고와local4문항low83.406/medium121.882초라는반대관측을함께보존한다. 명시xhigh의우위는미확인이다. none/high로임의전환하지않고thinking sampler1/.95/20/.05/0/1을유지한다.

| 새 단계·실물 | 선결/질문/판정 | 예상비용 |
|---|---|---|
| Stage3nW [실물SH](../run_P106B_Stage3nW_effort_upper_budget_panel.sh) | 같은4프로필 low/medium/xhigh·12요청·순서교차/seed고정·8K사고/16K합계/32Kctx | 1h·모델단계hard2h |
| Stage3n0W [실물SH](../run_P106B_Stage3n0W_effort_choice.sh) | 패널원답/비율검토후TTY 번호선택·자동채택없음 | 0.1h·모델단계hard2h |
| Stage3iWf [실물SH](../run_P106B_Stage3iWf_wire_content_gate.sh) | 선택effort·4프로필 actual파서/양mask·문제행선별/정확feedback | 0.75h·모델단계hard2h |
| Stage3iWg [실물SH](../run_P106B_Stage3iWg_teacher_correction_feedback.sh) | 소형wire성공·현재choice/source/code·96교정·언어당48중≥36 | 4h·hard6h |
| Stage3jWd [실물SH](../run_P106B_Stage3jWd_shared_corpus_feedback.sh) | 전체교정성공/선택SHA·양tokenizer·개념/질문split | 0.1h·모델단계hard2h |
| Stage3kWd [실물SH](../run_P106B_Stage3kWd_chat32_repeat4_feedback.sh) | 공통raw·B14chat32 exact부모·새feedback태그·4pass | 0.75h·모델단계hard2h |
| Stage3lWd [실물SH](../run_P106B_Stage3lWd_legacy_repeat4_feedback.sh) | 같은공통raw·A20legacy exact부모·새feedback태그·4pass대조 | 0.75h·모델단계hard2h |
| Stage3mWd [실물SH](../run_P106B_Stage3mWd_lineage_pair_feedback.sh) | 두현재교육/child/원답/commonraw SHA·자기CE 변화만 | 0.1h·모델단계hard2h |

**gate 계약:** v32/CORRECTION_V2. 소형pilot는4프로필에각1회이상엄격파서/양어휘 길이·mask·teacher자원계약이있으면CORRECTION_WIRING_PASSED다. 나쁜내용은여전히selected에서제외하며pilot의student_training_allowed=false다. 전체96은기존언어별75% 내용/문맥/자료량·사유저장을유지하고CORRECTION_FORMAT_PASSED 이후에만공통자료를만든다. 옛v31 결과를새기준으로PASS소급하지않는다.

**선택과종속성:** 첫권고는새smoke뒤nW 대응12요청만이다. 원답을후속판독한사용자가n0W에서기술적으로4프로필을완성한effort를선택해야뒤pilot/full이열린다. 선택없는무인큐는HOLD8이며default를몰래채택하지않는다. 이후B/A는같은공통raw·micro8/accum16상한·ckptON·compile·MuonRMS4/LR1e-4·정확4pass, 자기native/SFT CE 전후·first/within3·원답/child를보존한다. 실제corpus token/업데이트수는j단계전미정이다.

**한계/예측:** 문구명확화와더큰총예산이완결을도울수있지만잘못된의학·논리정보를truth로보장하지않는다. 질문복잡도/언어/parent/어휘·구조교락을유지한다. 패널은4문항/각1응답의처리율진단이지정답성순위가아니다. 전체96의최악288요청은16K상한을모두쓰면6h도넘을수있어부분증거/제한사유를보존한다. 새예상합계7.55h는조건부이며시간충전을위한중복생성을하지않는다.


### Stage3iWd~3mWc — 실행 회수: 완결 후내용음성·교육0

**질문/예측:** v30에서 실제5응답이4,096 출력 상한에 닿았고 KO다중답은3회 모두 사고에서 절단됐다. 출력6,144·문맥8,192로 늘리면 완결률을 회복할 수 있는지 같은 원천0/32/64/65·seed·low·권장 sampler로 먼저 확인한다. 더 긴 사고·새 답의 길이 초과·원천 내용 결함이 남아 실패할 수도 있다. 소형2그룹/언어는 여전히각2수락이 필요하며 전체3/4로 한국어 미달을 덮지 않는다.

**기존 계약 유지:** 교사는 항목 라벨만 출력하고 JSON/ChatML/role/mask는 코드가 만든다. 사고는 raw sidecar에만 남고 학생 target에는 넣지 않는다. `temperature=1.0, top_p=0.95, top_k=20, min_p=0.05, presence_penalty=0.0, repeat_penalty=1.0`, 최대3시도·언어별75%·양어휘1024 길이/마스크·B 부모 관측 기준선 잠금은 유지한다. `v31_correction_budget_recovery_lineage_pilot`와 budget child 태그로 출력한다. 구v29/v30·부모·원로그는 불변이다.

| 새 단계·실물 런처 | 선결·수행 | 판정/예상 비용 |
|---|---|---|
| Stage3iWd [출력 예산 소형 시험](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md) | 새 smoke 네 값0·same4profile·6144/8192·정확 length/사고/최종 진단 | KO/EN 각각2/2·GDN/계측·양어휘화면. 교사 단독·학생0, 예상0.5h/hard2h |
| Stage3iWe [전체 교정](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md) | iWd 실제 통과·현재 source/code·96질문군 | 언어당48그룹중≥36·원형/교정/사유/재시도. 예상3h/hard6h·학생0 |
| Stage3jWc [공통 자료](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md) | 전체 C 통과·선택 SHA·양 tokenizer | 동일 개념/질문 split·실제token/mask·probe 정확겹침0. CPU0.1h |
| Stage3kWc [chat32 B 교육](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md) | 공통 자료·B exact 부모·disk≥2GiB·새budget태그 | 기존 micro8/accum16상한·ckptON·compile·MuonRMS4/LR1e-4·정확4pass·자기CE전후/first/within3 원답. 예상0.75h/hard2h |
| Stage3lWc [legacy A 대조](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md) | 같은 공통 자료·A exact 부모·disk≥2GiB·새budget태그 | 같은4pass/설정, B 실패와 독립. 예상0.75h/hard2h |
| Stage3mWc [원답 비교](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md) | 두 교육 report/child/answer/commonraw SHA | first/within3 분리·자기native CE 변화만·어휘/부모/구조 교락. CPU0.1h |

**비용·한계:** 예상 합계5.2h이며 소형부터 조건부다. 기존419.242초/4그룹을96그룹으로 확장하면2.795h여서 종전 full-C hard2h는 부족할 수 있다. 새6144의 실제 소요/수락률은 미확인이라 전체 교정은 예상3h·hard6h로 제한한다. HTTP timeout240초는 유지한다. 전체 최악288요청이 모두 상한을 채우면6h도 부족할 수 있으며 그 경우 부분 원형/실패 사유를 보존한다. GPU시간을48h로 채우려고 같은 질문·원형을 재생성하지 않는다. 후보자료가 없어서 교육을 막은 상태와 교육 자체의 품질 실패를 구분한다. KO/EN 질문 복잡도가 달라 언어 단독 비교가 아니고, 형식 수락/CPU16+12회귀는 의미·교사 truth·새GPU/학습 성공을 보장하지 않는다.

**실행/예측 대조:** [결과101 §35](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)의 음성과 원답을 그대로 유지한다. 새 단계는 구현/정적 준비이고 GPU·교정 완결·학생 교육은 NOT_RUN이다. 새 관측 전 문턱 변경·원본 삭제·B baseline 중복 평가를 하지 않는다.

### Stage3iWb~3mWb — 2026-09-30 연결 복구 실행 회수: 소형 음성·후속 선결 차단

**2026-09-30 실측/예측 대조:** [결과101 §35](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md). 실제 C 연결은 수락4행까지 정상화됐으나 KO다중답3시도가 모두 사고에서 length4096로 절단됐다. 총8요청5length·KO1/2/EN2/2로 언어별75% 미달, 뒤5단은 선결8·교육0이다. 과거 코드enum/주소실패와 새 출력예산 음성을 구분하며 언어별 문턱은 낮추지 않는다. 위 v30 표는 실행 이력이고 현재 권고는 아래 새 단계다.

**목적/예측.** C의학습자료수/교사정답성 판정전에 미등록source_transform·서로다른출력주소·처리예외raw누락을고친다. 작은시험은같은공개v28의원group 인덱스0/32/64/65로한영단일답/다중답4프로필을덮는다. registered `teacher_repair`로actualjob을교사호출전에validating하고작성/소비주소는 `stage_directory()` 하나가소유한다. 실제C→JSON/ChatML/mask/후속split을호출하는CPU회귀의2실패를먼저재현했으며수정뒤11/11과기존pipeline12/12를통과했다. runtime새실패·길이절단·자연어/내용문제는여전히가능하고형식0을진실성으로승격하지않는다.

**기존부모평가 사용의뜻.** 부모가중치를바꾸거나재학습하는것이아니다. 완료된Stage3hW의부모reportSHA `38E1EB39...8C7F399`·24원답/4텍스트샤드와같은모델/어휘/nativeval/metadata, 변하지않은평가함수/핵심helper를확인해 **이미관찰한교육전기준선**으로둔다. 새C코드의GPU PASS를주장하지않는다. B 4epoch 자체에서자기SFTval/nativeval before/after를측정하는계약은유지한다. 관측0/8은학습자료준비를금지하는gate가아니며교육이얼마나개선하는지검증할기준선이다.

| 새단계·실물SH | 선결·수행 | 판정/예상비용 |
|---|---|---|
| Stage3iWb [소형C연결](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md) | exact 기존B관측·v28 SHA·4프로필·actual출처검사, 새v30/correction-pilot | 언어당2group 각각ceil75%=2완료·양어휘길이/mask·GDN/sampler, 최대3시도·checkpoint0. 이6후보행은기능표본이지교육corpus가아님. ⚙0.3h·hard2h |
| Stage3iWc [전체C복구](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md) | 새소형report/현재code/hash가PASS인뒤96질문군을v30/correction에작성 | 기존언어당48group≥36·양어휘context/narrow script화면·무중복, 원형/교정/사유/paid reply예외보존. ⚙2h·hard2h·teachertruthUNVERIFIED |
| Stage3jWb [공통split복구](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md) | v30/correction/selected exact SHA, 부모concept/같은질문을함께분리 | 실제token·mask·exactprobe중복0·v30/prepare. CPU⚙0.1h |
| Stage3kWb [B4epoch복구](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md) | 새공통raw·B자기어휘/parent/cache, 새tag `p106b_s3k_recovery_chat32_s1337` | 기존학습설정·정확4pass·자기CE전후·first/within3/raw/child·토크나이저단독인과금지. ⚙0.75h·hard2h |
| Stage3lWb [A4epoch복구](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md) | 같은새raw·A자기legacy parent/cache, 새tag `p106b_s3l_recovery_a_s1337` | B실패와독립실행 가능·같은4pass/micro8/accum16상한/ckptON/MuonRMS4 LR1e-4. ⚙0.75h·hard2h |
| Stage3mWb [두계보증거연결](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md) | 새v30 A/B report·commonraw/child/8question SHA | 자체cache 전후·first/within3 원답만짝지음, token CE 교차순위금지. CPU⚙0.1h |

새v30파일·두학생checkpoint/metadata는write-once이고oldv29/oldtag/HF/cache/checkpoint를수정하지않는다. 전체합계4.0h이며새smoke가맨앞선결이다. 새태그충돌0·정적/CPU PASS, 실제파일내용을학생이어떻게배웠는지/자원/교정의새오류는사용자원본전NOT_RUN이다. 큰300M학습량이나멀티턴능력으로올리지않는다.

| 단계 | 예상 상한 | 자원 |
|---|---:|---|
| Stage0W | 약0.1h | CPU, 공개 OASST2/v3/tokenizer 읽기 전용 |
| Stage1aW | 0.5h hard wall | 사용자 GPU full 교사 단독, ctx1024, ≤16×768 생성토큰+사고토큰 |
| Stage1aWb | <0.17h hard wall | 이번 지시 한정 Codex 직접 CPU+GPU ≤10분, 공개4쌍×cap2, 모델/학생 checkpoint 쓰기0 |
| Stage1dW | <0.16h hard wall | 이번 지시 한정 Codex 직접 CPU+GPU ≤10분, 오류2+solver대조1, 학생 학습/체크포인트0 |
| Stage1fW | ⚙0.5~0.9h, hard wall3300초 | 사용자 GPU 교사 단독, 고정16 교정 후보 생성·원본 보존, 학생 학습0 |
| Stage1gW | ⚙≤0.5h, hard wall1800초 | 사용자 GPU 교사 단독, 결함8행×최대3회·v5 모든 시도 보존, 학생 학습0 |
| Stage1bW | 약0.5~0.75h(첫 compile/교사 지연 변동, hard wall2700s) | 사용자 GPU full 교사+P076 학생, 최대2업데이트, 고유 진단 checkpoint 예상0.45GiB |
| Stage1cW | 약1.5h(공개 3과제×512와 P10036) | 사용자 GPU 모델2개 순차 평가, 보호 held-out0·문항별 원본 write-once |
| Stage2hW | 4.1분 실측(상한17분) | 이번 지시 한정 Codex 교사-only 12요청, 학생 학습0; GPU 결과는 결과101 후속 절에 귀속 |
| Stage2iWa/Wb/Wc | 각각 4h/1.5h/6h hard wall | **사용자 실행용 대안 세 팔**, 합산 큐 의무 아님; GPU full 교사+P076 학생, 최대5 optimizer 업데이트·체크포인트0 |
| Stage2jW/Wb | 각각 ≤0.17h/≤0.08h hard wall | 이번 사용자 한정 GPT 직접 교사-only GPU 4+1요청, 학생·checkpoint0; 진단 원본 결과101에 별도 기록 |
| Stage2fWb | ≤0.5h hard wall | 사용자 full 교사 GPU, 기존 부분 raw29시도 참조+누락7문항만 생성; 학생0 |
| Stage2iWd | ≤1.5h hard wall | 사용자 full 교사+P076 학생, OASST1 원천의 **1 optimizer 기술 gate**, Stage2fWb PASS 선결·checkpoint0 |
| Stage2kW | 약0.1h CPU | 정확 공개 v3/OASST2와 지정 보호 사전/word/TXT **읽기 전용** 구조·SHA/계수; 모델·복사·출력 deck0 |
| Stage2kWb | ≤0.1h CPU | 공개 Aya Dataset/OASST2 job 예상10,528건만 별도 ignored HF 20MB 샤드로 새로 기록; 보호 사전 접근0·교사/학생/GPU0 |
| Stage2iWe | ≤2.0h GPU | 공개 전용 medium 1 optimizer·실제 token admission·P076 부모, 체크포인트0. Stage2kWb 10,528 job 생성·새 smoke PASS 선결 |
| Stage2iWf | ≤6.0h GPU | 동일 public deck SHA의 Stage2iWe 1회 PASS가 선결. 5 optimizer·640 신선후보, 체크포인트0 |
| Stage2iWg | ≤2.0h GPU | 새 공개원천 low1·계측수리 실물 gate. 구 OASST1 low1 반복 아님; 신규 v17·128 fresh·checkpoint0 |
| Stage2iWh | ≤6.0h GPU | Wg low1·동일 source/부모/교사 SHA·정상 monitor·실제128 적용 선결; 신규 v18·640 fresh·checkpoint0 |
| Stage3aWb | ⚙1.5h·hard2h GPU | 기존1.140/1.015×·KO1~2/4 음성 뒤 질문 언어당16·ctx6144/output4096 별도v26; 사용자 실물 전 속도·OOM NOT_RUN |
| Stage3bWb | ⚙1.0h·hard2h GPU | 기존 serial KO4/8·overlap0 음성 뒤 질문 언어당16·ctx6144/output4096 별도v27; 학생 partial최대32행·통합0 |
| Stage2W | `NOT_ESTIMABLE` | 승인 원천의 실제 유니크 지도토큰·교사 accepted sample 비용·동일평가 확인 후 산정 |

## 7. 실행 파일·사전 점검

- Stage1aW: `run_P106B_Stage1aW_oasst2_teacher_ko_gate-done.sh`는 결과101의 재현명령과 Git 이력으로 보존 후 삭제. 사용자 번역16건·완결9/16, 문턱12 미달 exit8; v1 덮어쓰기 금지.
- Stage1bW: `run_P106B_Stage1bW_online_pseudo_sft_micro8-done.sh`는 결과101/ Git 이력 보존 후 삭제. 상류 미달 check-only 중단·학생학습0, 원시 exit9 분류 결함→후속 CPU HOLD8 수정.
- Stage1aWb/Wc: 두 완료 런처는 결과101·Git에서 복구 가능하며 삭제. Wb sandbox 차단으로 모델0, Wc 승인 GPU 경로4쌍×2팔 종료0·v2 기록; 학생학습0.
- Stage1dW: 완료 런처는 결과101·Git 보존 후 삭제. 교사 교정형3/3 형식 통과이나 새 수치오류1, 자동 학습수락0.
- Stage1fW: 사용자 실행·결과101 §10에서 교정형16/16 형식 PASS·답안 결함8을 회수했다. `run_P106B_Stage1fW_teacher_repair_full16-done.sh`는 재현명령과 Git 이력 보존 뒤 사용자 승인 삭제 조건을 별도로 판정한다.
- Stage1gW: 역사 SH는 결과101 §11에 재현명령과 원본을 보존하고 완료 표기로 전이한다. 사용자 실행8행 중 lint7/8로 사전 문턱 실패; 재실행은 같은 v5에 하지 않는다.
- Stage2a/b/c/d/gW: [결과101 §14~§17·§19](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)의 사용자 실제 로그로 CPU 계약·태그15/16·v7 한국어13/2·학생 오프라인2업데이트를 회수했다. Stage2e 공개 v3 job deck5,429개는 생성됐으나 교사 답/품질이 아니다. Stage2fW는 문항26 HTTP500·출력 manifest 부재로 **미완·exit9**이며 Stage2fWb 별도 보충이 필요하다.
- Stage2hW: 이번 지시의 명시적 단기 CPU+GPU 허용으로 교사-only 12요청을 직접 실측했다. v9 write-once 원본과 별도 runlog를 결과101에 회수한다. **학생 온라인 5회가 아니다.**
- Stage2iWa/Wb/Wc: [결과101 §20·§27~§28](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에서 Wa는33요청/optimizer0 도구 사고, Wb none은5/5·52분 기술 완료, Wc medium은4/5·한국어365원천 소진 exit8로 분리한다. Wc의 canonical 형식 후보611 중 실제 학생 업데이트에 들어간 것은512다. 구 v10 원본 불변·같은 단계 재실행 금지. OASST1 B/C와 새 Aya/OASST2 공개 원천의 효과를 한 변수 비교로 오인하지 않는다.
- Stage2jW/Wb: 이번 사용자 한정 Codex 교사-only4+1요청의 별도 v11/v12 결과가 [결과101 §21~§22](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에 있다. 교사 native parser의 문항26 HTTP500은 정확 PEG 불일치, bypass의 HTTP200은 길이 소진·중복 태그로 답안 불가다. 사용자 재실행 단계가 아니며 같은 출력 버전을 재사용하지 않는다.
- Stage2fWb/Stage2kW/Wb·Stage2iWd: [결과101 §23~§26](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에서 Stage2kW 읽기 전용87,361 job과 Stage2fWb 한영 형식 KO14/EN15을 보존한다. 2026-09-29 새 smoke43/0/0/0 뒤 Stage2kWb 공개 job10,528과 Stage2iWd low 동시 1 optimizer·약76.8분 완료, checkpoint/품질0. 실물 기술 경로는 열렸으나 교사 진실성·formal SFT는 아니다.
- Stage2iWe/Wf: We medium 첫실행은 sampler `TimeoutExpired` 미처리 뒤 사용자 Ctrl+C·optimizer0/후보123이었다. 같은날 로그 삭제 후 재실행은 output존재 check-only exit9였다([결과101 §29](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). 사용자 지시로 medium 보류, We -done·재현 보존 후 삭제 판정, 미실행 Wf SH는 HOLD로 보존하며 모델 전 check-only8로 막는다.
- Stage2iWg/Wh: Wg는 사용자 9/29 기술1회 완료([결과101 §30](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)); 해당 SH는 명령4개와 Git 복구점을 남기고 삭제했다. Wh low5는 지금 [보존 SH](../run_P106B_Stage2iWh_online5_public_low-hold.sh)로 개명해 직접 실행도 HOLD8로 차단했다. 두 팔의 학습량을 합치거나 Wh를 이미 수행한 것으로 표기하지 않는다.
- Stage1cW: [비활성 SH 템플릿](../scripts/templates/P106B_Stage1cW_parent_student_posthoc.sh.in)만 있다. Stage1b 고유 checkpoint가 아직 없어 루트 SH/TSV에 등록하면 입력태그 린터가 실제 FAIL한다. 사용자가 Stage1b 로그·체크포인트를 회신해 SHA/메타데이터를 판독한 **다음 지시**에서 새 단계명으로 활성화한다. 생성 답안·문항별 벤치 원본이 결과문서의 근거다.
- Stage2W: 원천 수·사람 표본·평가 설계 미확정이므로 **SH 미작성**. 두 준비 SH가 존재하는 것과 Stage2 본학습 사용 승인은 다르다.
- tag `p106b_s1b_oasst2_ko_online_s1337`: 레지스트리 조회에서 기존 로그 충돌0. 새 Stage1b 출력은 P106B 고유 이름이며 기존 P076/공개 SFT/교사 파일을 덮지 않는다. 과거 P076 mean은 같은 시작점 전후 진단의 부모이지 **동일 학습량의 교사 없는 대조군**이 아니다.

### exp-preflight — 이 계획의 알려진 실수 차단

| 축 | 판정 | 근거/미해결 |
|---|---|---|
| 독립변수 | PASS(기능 gate) | `교사 실시간 pseudo target 사용`이 Stage1b 목적; source16 반복·2업데이트만 |
| 계산/유효배치 | PASS | 8×16×1024=131,072 위치/업데이트, 2회 상한262,144. 실제 assistant target 토큰은 실행에서 따로 센다 |
| 풀≥2× | 예외·품질 판정 금지 | SFT는 의도적 epoch/중복 노출을 쓰며 이 기능 gate는 ≤16유니크·반복; pretrain 2× 풀 규칙을 학습효과 PASS로 복사하지 않음 |
| 태그/덮어쓰기 | PASS(정적) | 신규 tag 충돌0, 버전드 dataset·고유 진단 checkpoint write-once, 기존 checkpoint 수정0 |
| 동일 비교 | `PARTIAL_DESIGN` | Stage1c는 같은 부모/tokenizer/고정문항 전후 비교를 준비. Stage2 이전에는 no-teacher matched control이 없어 교사 품질 인과효과 판정 불가 |
| GPU/속도 | 제한 추산 | Stage0pW ctx512 full 교사+micro8/ckpt-on 표본 free4422MiB는 Stage1b ctx1024·실문장 peak 보증 아님; Stage1b 시작/공존 free 문턱으로 fail-closed |
| 수치·지능 판정 | `NOT_RUN` | Stage1c 문항별 오답 회수는 준비됐지만 2업데이트 결과로 일반 지능 향상 주장 금지; Stage2 대조 필요 |

> 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

### Stage3 실행 파일 (모두 사용자 실행·새 smoke 선결)

현재h~m 구6SH는사용자실행이끝났다. h는성공한교육전관측으로보존, C는tool9,뒤4단은모델0/선결8이다([결과101 §34](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). 네 재실행차이는정확새단계명으로남기고실제권장큐는새iWb/iWc/jWb/kWb/lWb/mWb이다. 구개별SH는명령을보존한뒤-done으로정리한다.

- 역사 Stage3a/b/c0/c/d/e/f/g0/g 아홉 SH는 전부 사용자 9/30에 **착수된 이력**이다. 각각의 정확한 명령4개와 성공·음성·미실행 구분은 [결과101 §31·재현부록](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에 보존했다. `-done`은 사용 시도 표지이지 A1/A2/통합의 과학적 성공 표지가 아니다.
- Stage3aWb/3bWb 및 Stage3fWb는 사용자 실행이 끝났고 [결과101 §32~§33](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에 음성/기능 PASS를 분리했다. 완료 SH의 재현명령을 보존하고 정리했다. 다음 실제 SH6개는 §5 Stage3hW~3mW 표와 최신 핸드오프 §7에서 id/선결을 대조한다. `-done`은 과학적 성공 표시가 아니다.

§7 handoff 큐는 실제id·시간·조건부상태 정본이다.1개의update로4epoch완료를 보고하지 않으며300M 목표는 현재 코퍼스 부족·생산비용 때문에 별도 원천확장/품질 계획을 요구한다.

## 8. 한계·보호선

OASST2의 review/rank는 사실성 보증이 아니다. 교사 번역도 독립 정답이 아니므로 P106의 검증형 `ACCEPT` 원장을 이 실험으로 채우지 않는다. 출처 카드 Apache-2.0 표기는 개별 텍스트의 개인정보·권리 승인이 아니다. 자동 연락처/숫자 검사는 **명백한 경우만** 걸러 의미 왜곡 전부를 검출하지 않는다. 그래서 원문·교사가 실제 가르친 문구·선정/거부 상태를 버전드 데이터셋에 남기고 사후 분석한다. 사전 파일의 뜻풀이가 전부 존재해도 다의어 표준번호·출처/라이선스·용례 유형을 건너뛰지 않는다. 원칙적으로 GPT가 보호 `concept`/사전 원본을 HF에 복사하거나 학습·GPU를 대신 실행하지 않는다. 이번 사용자 지시에만 허용된 Stage2jW/Wb 교사-only 초소형 GPU 진단은 이 원칙의 **한정 예외**이며 학생·사전 원본을 건드리지 않았다. 성공해도 13유니크×2업데이트의 과적합·분산 때문에 Stage2 대조 없이 데이터 채택을 판정하지 않는다.

## 9. 실행 이력 / 갱신

- 2026-09-27: 사용자 질문에 따라 ‘독립 정답 전수승인’이 일반 SFT의 필수조건이라는 과도한 전제를 철회하고, P106 검증형 `ACCEPT`와 P106B 자동 번역 `PSEUDO_UNVERIFIED`를 분리했다. 승인된 정확 `concept`와 사전 두 파일만 읽기 전용으로 구조·겹침을 확인했다. OASST2 Stage0 CPU 선별 자기시험/check-only에서 1326→잔존138·선정16을 확인했다. 교사 실제 번역·학생 학습·새 smoke는 `NOT_RUN`이다.
- 2026-09-27: 사용자 [결과101](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에서 새 smoke43/0/0/0 뒤 Stage1aW 교사16응답 중 완결9·미완결7, 실측 wall173.97초·총 생성10,429토큰을 회수했다. `12/16` 사전 문턱 미달은 §3이 경고한 형식 음성으로 유지한다. 당시 파서는 비정상 `finish_reason`을 하나로 뭉치고 사고/최종 부분출력·행별 사용량을 저장하지 않아 **절단 원인 귀속이 불가**하다. Stage1bW는 상류 실패 뒤 check-only에서 종료9로 잘못 분류했고 실제 교사+학생 학습은0회였다. 후속 코드는 같은 v1 문턱을 HOLD8로 고쳤지만 원본 로그는 수정하지 않는다. 새 설정의 재실행은 다른 단계·데이터 버전으로만 연다.
- 2026-09-27 후속: Stage1aWb는 기본 sandbox NVML 실패로 교사 적재0, Stage1aWc는 사용자 한정 허용 경로에서 4쌍 대응 cap768 0/4 대3072 3/4 완결을 확인했다. 사고문은 양쪽4/4 존재, 최종 문구는 큰 cap3/4에만 있었다. v2 raw는 불변이다. 직접 읽은 WebRTC 번역은 원문 API 오개념을 옮겼고, 교사 교정형 Stage1dW는 세 문항 JSON3/3을 냈으나 자기 `CORRECTED` 2건 중 하나가 GPT‑3 175B를 **175억**으로 새로 오기했다. [결과101 §9](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)의 외부 API/논문 근거 대조에 따라 그 행은 REJECT, WebRTC는 API 사실만 부분 확인, 수학50·20은 산술 확인이다. v3 원본·점검표를 별도 보존하고 자동 `ACCEPT`/학생학습0을 유지한다.
- 2026-09-28: 사용자 새 smoke43/0/0/0 뒤 Stage1fW full16 완결, 교사 자기 `CORRECTED`8/`PRESERVED`8. 직접 검토에서 새 결함8·추가검토4·잠정4라 자동 학습 채택0을 유지한다. 사용자 승인 A로 Stage1gW의 결함8만 프롬프트·진단기 response hook·최대3회 재시도에 연결했다. v5 출력은 새 버전·모델 사용자 실행 전 `NOT_RUN`이다.
- 2026-09-28 사용자 새 [smoke](../smoketest_logs/202609281223_smoke_cf99a59.txt)는 이전 `cf99a59` 트리의43팔·실패0·exit0 오류표지0·계측0이었다. [결과101 §14~§20](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)은 Stage2a/b CPU 계약, Stage2c 태그15/16·JSON14/16, Stage2d 한국어13+2행, Stage2f 문항26 HTTP500 미완, Stage2g 학생2업데이트/비패딩36,894, Stage2iWa 교사33응답·optimizer0/5를 구분했다. Stage2g CE 하락은 같은13행 반복 train 내 결과이지 val/대화 품질이 아니다.
- 2026-09-28 GPT 한정 직접 Stage2jW/Wb: 새 서버의 Stage2f 문항26에서 `peg-native format` HTTP500을 재현했고 입력817+max4096<ctx6144·free≈8.5GiB였다. parser bypass는 HTTP200이나 `length`4096·반복 태그로 불완결이어서 학생 target 금지. Stage2i 원 실패 입력은 교사-only 새 서버에서 HTTP200이므로 공통 원인을 단정하지 않는다. v8/v10 원형과 새 v11/v12 진단은 각각 불변이다.
- 2026-09-28 사용자 다원천 C안·초과길이 A안 선택: 기존 공개 v3 `oasst`는 OASST1이라는 계보 오류를 정정했다. 고정 OASST2 ready trees13,854 중 reviewed 영어 단일턴5,400/한국어5; 새 Stage2kW 읽기 전용 계약은 Aya Dataset 영어1,439개·OASST2 중복제외 영어3,824/한국어1개·사전 뜻풀이76,833 locator를 분리해 계수했다. 87,361 job은 답안/학습토큰이 아니다. 보호 원문/교사 변환 실행은 별도 정확 권리·파생 승인 기록 전 `HOLD`이고, 1200자 초과는 교사 실제 template 토큰 예산을 재어 DIRECT/압축 별도 child로 분기한다.
- 2026-09-28 사용자 반환: Stage2kW 독립 CPU 결과는 87,361 job/read-only, Stage2fWb는 old29+new8시도·case26 PEG500 2회에도 KO14/EN15로 사전 각12/16 형식 문턱을 통과했다. 이것은 학생 학습·한영5:5·교사 정답 PASS가 아니다. 새 코드/권리 분리 뒤 사용자 smoke는 별도 재실행이 필요하다.
- 2026-09-28 공식 정책 대조: 사전 별도 저장은 독립 공개원천과의 물리·계보 혼합을 막지만, 사전 예문/뜻풀이의 표현을 변형한 행의 권리나 모델 공개 시의 법적 판단을 자동 면제하지 않는다. Stage2kWb는 공개 source만 쓰고 보호 계열 전송/복사0; 사전 파생 별도 후보셋/개념만 재합성의 범위는 사용자 추가 선택과 검토에 따라 별도 구현한다.
- 2026-09-29 사용자 [smoke](../smoketest_logs/202609290441_smoke_b12060e.txt) 43/0/0/0과 [결과101 §25~§28](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md) 회수: 공개 전용 Stage2kWb job10,528·Stage2iWd low1/1·Wb none5/5 기술 기능을 확인했으나, Wc medium은 한국어365후보를 모두 써도 4/5에서 exit8이었다. Wc 형식 후보611 중 학생 optimizer에 실제 적용된 것은512, 남은99는 미적용 raw/canonical 후보로만 보존한다. none5의 비패딩141,422토큰과 medium4의100,408토큰은 300M/600M이 아니고 checkpoint/held-out 평가0이다. 장시간 서버 오류 tail에서 GDN 시작 줄이 밀린 결함은 계측 보강했지만 새 GPU 런 전에는 해당 팔 fusion 상태 `UNKNOWN`. 사용자 선택 A로 공개 Aya/OASST2 전용 Stage2iWe 1회→통과 시 Stage2iWf 5회만 준비했으며 현 E2E는 `NOT_RUN`이다.
- 2026-09-29 후속 [smoke](../smoketest_logs/202609291711_smoke_848dd6a.txt)는848dd6a 실행 당시43/0/0/0. We 첫실행의 계측 daemon timeout이 main에 전달되지 않은 **코드 결함**은 사용자 traceback과 exact v15 원형141/후보123·updates0으로 확인했다. ctx/출력상한이나 교사 품질 실패라고 단정하지 않는다. Ctrl+C/status와 sampleerrors 누락·후속 dataset output collision을 각각 수리/설명하고 medium은 보류했다. low 이미 실행했던 OASST1 Wd1 성공은 보존하며, 사용자 재선택 A로 새 공개원천·수리코드 Wg1→통과시Wh5를 별도 단계/버전으로 준비했다. 다음 가설은 계측 오류가 다시 발생하면 조용히 학습을 계속하지 않고 원본·partial을 남기며 fail9하는가이고 실물 결과 전 미확인이다.
- 2026-09-30 회수: 9/29 Wg low1은 새 source에서128답/1optimizer·원형196행·유효25,133대화토큰으로 완료됐다. sampler errors0와GDN latchtrue를 관측해 작은 기술 gate만 PASS로 옮겼다([결과101 §30](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). 길이절단55건이 교사시간43.635%를 쓴 것은 남은 생산병목이다. 사용자 B,C4,A1+A2와 독립C4 뒤 통합1→실교육 승인에 따라 Stage3 9개SH/구현을 준비했으며 모델실행0. 별도 미실행Wh/Wf는 보존했다.
- 2026-09-30 2차 회수: 새 [smoke](../smoketest_logs/202609300046_smoke_f417544.txt)43/0/0/0 뒤 [결과101 §31](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)의 아홉 Stage3 시도를 분리했다. 예측한 A1 두 순서>1.05는 역순1.015로 **불성립**, 예측한 A2 실제 겹침은 KO4/8 문턱미달로 **미측정**이다. B2/B4 형식은 한영4/4로 예상보다 잘 되었지만 teacher 정답성은 여전히 별도다. C4는4pass·4optimizer를 완료하고 좁은SFT-val CE를 개선했으나 base full-val+0.018444 악화·고정답8/8 실패로 ~~운영 중단선 통과 뒤 바로 후속교육~~ 해석을 철회한다. 상류차단 f/g0/g는 실행 시도 로그만 있고 실교육0이다. 사용자 선택 A에 따라 토크나이저 계보·원답을 CPU 대조하고 A1Wb/A2Wb만 새v26/v27로 준비한다. 새 GPU 결과 전 통합 HOLD, Wh/Wf 미실행 두 파일은 `-hold`/큐 제외다.
- 2026-09-30 3차 회수: 사용자 [새 smoke](../smoketest_logs/202609300319_smoke_f0a103e.txt)43/0/0/0 뒤 [결과101 §32](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)의 A1b는 네 팔 실물·자원 probe까지 수행했으나 두 슬롯 24/25행 대 한 슬롯28행, 속도쌍0.951/1.056×라 속도·수락 보존 예측이 **불성립**이다. A2b는 serial/overlap 각28행·실제 구간 겹침·각 부분 optimizer1회로 기능 예측이 **성립**했다. 1.1875× whole-wall은 첫 팔 cold compile/고정순서 교락이므로 가속 채택 예측은 하지 않는다. 사용자 선택 C에 따라 A1 음성을 통과로 바꾸지 않고 A2 단일 슬롯의 새 Stage3fWb를 별도 v28·SH로 정적 준비했다. 교사 thinking sampler·최대3회 원형보존 재시도·코드 소유 라벨 파서/JSON/ChatML 계약을 포함하고, 새 GPU/학생 품질은 `NOT_RUN`이다.
- 2026-09-30 4차 회수: [사용자 smoke](../smoketest_logs/202609301058_smoke_304fcc6.txt)43/0/0/0과 [결과101 §33](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)의 v28 통합128행·optimizer1/24,187대화토큰 성공은 기술배선 예측을 **확인**했다. 교사42시도·최종32task에서 제한재요청이6task 형식을 복구했으나 fixed16답 직접검토에 kana/오조어/독립문맥 부족이 남아 ~~형식완료이면곧바로능력향상~~ 해석은 채택하지 않는다. checkpoint0이라 이후교육은원래부모에서시작한다. 사용자 C→B우선/A대조 승인과 B 부모 선평가 요청으로 새 Stage3h~mW 6런처/코드를 준비했다. 신규GPU/교정본/학생품질은NOT_RUN이며 원형v28·기존부모는불변이다.
- 2026-09-30 5차 회수: [smoke20cef06](../smoketest_logs/202609301547_smoke_20cef06.txt)43/0/0/0 후 [결과101 §34](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)의 Bbaseline nativeval3.590418·8질문24답0/8·한영4prefix반복을직접판독했다. 코드배선은문제없을것이라는낙관은 ~~C full path를정적5회귀가검증한다~~로철회한다: actual source enum미등록과 correct/correction불일치가교정9/후속선결8을만들었다. 새actual C→wrapper→consumer/양mask 회귀와exception raw보존을구현했으며사용자 A선택의기존기준선/작은C→전체C→B/A를별도v30·새6SH로준비한다. 교육/정답향상은아직미실행이다.

### 2026-10-01 실행 회수와 Stage3oW/3pW — CPU 계약·동결 원답 보기

[결과101 §37](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)의 패널/선택/교정/자료/두교육/대조8단계는 모두 **완료**했다. 예상한 실제 wrapper/양mask·4epoch 실행은 성립, ~~그것만으로 답변능력 개선~~은 고정rubric0/8과 실제표지/질문반복으로 확인되지 않았다. xhigh 선택을 보존한다. teacher 정답성·정식TRAIN_READY·300M교육은 미확인이다.

당시 조건부 승인 [온라인/후행 분리안](../proposal/20261001_P106B-온라인-계약검사와-후행-품질검증-분리-제안서-approved-on-going.md)은 무입력·원답보기·공유3시도까지만 구현하고 [유일출력 별도설계](../proposal/20261001_P106B-유일출력-변형계약과-공유재생성예산-제안서-approved-on-going.md)·유사도·새보고·품질필드 호환의 선택을 요청했다. 이 이력은 아래2026-10-02 사용자 추가 승인·새v33 구현으로 갱신됐다. 원형 결과와 옛 미구현 상태를 새 경로의 현재 판정으로 복사하지 않는다.

| 단계 | 실물 실행 파일 | 예상·자원 | 사전 판정 | 상태 |
|---|---|---|---|---|
| Stage3oW | [run_P106B_Stage3oW_online_contract_cpu.sh](../run_P106B_Stage3oW_online_contract_cpu.sh) | ⚙0.05h·CPU·GPU0 | 공유기존3회·무입력/명시설정·실물표시 fixtures 통과 | STATIC_ONLY; 사용자 runlog NOT_RUN |
| Stage3pW | [run_P106B_Stage3pW_saved_answers_view.sh](../run_P106B_Stage3pW_saved_answers_view.sh) | ⚙0.05h·CPU·GPU0 | 정확 기존report/shardSHA와 원천/실답/모든시도 표시 | STATIC_ONLY; 사용자 runlog NOT_RUN |

**독립변수:** ID만 표시하던 화면과 입력 대기를 명시 설정/실제 원답 표시로 바꿔 기술 계약을 검사한다. 새 품질 지표나 GPU 교육조건 비교가 아니다. 새 태그·모델출력·학습토큰0, 풀2배 조건은 학습하지 않으므로 N/A다. `check_run_registry.py --steps 1 --micro-bs 0 --accum 1 --seq 1` 계산 전용 경로가0토큰을 확인했고 광범위 runs 레지스트리를 읽지 않았다. 과거v32를 새코드 E2E PASS로 재계산하지 않는다. GPU 재시험은 호환 선택/보류방법 승인 후 새버전·새단계에서 준비한다.

> 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

### 2026-10-02 운영A·유일출력A·문자A/B·분리보고A 승인 구현 — 새 v33

2026-10-01 사용자 oW/pW는 [결과101 §38](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)의 CPU12 모의시험과 동결18교사답/96학생시도 재표시로 완료했다. 옛 GPU 패널과 교육 결과를 새 모델 관측으로 중복 계수하지 않는다. 원형2SH의7명령과Git복구점을 결과에 보존하고-done 개명·사용자 승인 적격삭제를 수행했다.

**새 독립변수:** 온라인 잘못된 문구/의미 재시도를 제거하고, 유일출력/UNKNOWN/명시변형의 코드계약과 총3회 기술회복·문자 관찰·분리보고로 전환한다. 원형 v32·옛 역사 문턱은 변경하지 않는다. 새 `v33_online_technical_contract`에서 원천 v28 질문/대조 답을 사용하되 신규 생성변환은 `teacher_answer`이고 의미/오조어 검증은 후행이다. 기존 xhigh 사용자 선택의 정확 SHA를 실행전 설정으로만 계승한다. 기존 B부모 평가도 평가 함수/원형SHA를 검산해 교육 전 기준선으로만 사용한다. 새 경로 GPU PASS로 승격하지 않는다.

**예측과 대립 가설:** 유일답/UNKNOWN의 불필요한 중복 호출과 잘못된 문구 목록의 내용 오판을 줄일 것으로 예상한다. 파서·문맥·출처의 실패나 교사의 질문 재작성은 여전히 발생할 수 있으며 typed 계약이 UNKNOWN으로 내려갈 수 있다. 문구 screen을 제거해도 교육 품질이 좋아진다는 예측은 하지 않는다. 변형가능의 완전동일답만 정상 슬롯/질문을 고정해 남은 요청 예산으로 회복하고, 언어/유사도 관찰은 경고만 기록한다.

| 단계 | 실물 런처 | 비용/자원 | 선결 | 사전 판정·상태 |
|---|---|---:|---|---|
| Stage3oWb | `run_P106B_Stage3oWb_online_contract_v3_cpu.sh` | ⚙0.10h/CPU·GPU0 | 새 사용자 smoke0.1h | 완료:CPU56회귀·exit0,새의미판독0([101 §39](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md));과거계획한계유지 |
| Stage3qWa | `run_P106B_Stage3qWa_lexical_ab_cpu.sh` | ⚙0.05h/CPU·GPU0 | 새 smoke0.1h | 완료:동결120측정·비용선통과;소표본p95수리는qWc([101 §39](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md));과거계획한계유지 |
| Stage3rW | `run_P106B_Stage3rW_review_packet_prepare.sh` | ⚙0.05h/CPU·GPU0 | 새 smoke0.1h | 완료:20대상패킷준비0,판독0([101 §39](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md));과거계획한계유지 |
| Stage3qWb | `run_P106B_Stage3qWb_known_output_teacher.sh` | ⚙0.50h/사용자 GPU | oWb0.1h와 문자 qWa0.05h | 완료:고정4계약/실요청6·유일값보호/총3회([101 §39](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md));과거계획한계유지 |
| Stage3iWh | `run_P106B_Stage3iWh_online_technical_wire.sh` | ⚙0.75h/사용자 GPU | qWb0.5h | 완료:4프로필/4요청·선택6·양어휘기술연결0([101 §39](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md));과거계획한계유지 |
| Stage3iWi | `run_P106B_Stage3iWi_online_technical_collection.sh` | ⚙4.00h/사용자 GPU | iWh0.75h | 완료:96그룹/97요청·128기술행·교사32.5분·의미미검토([101 §39](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md));과거계획한계유지 |
| Stage3jWe | `run_P106B_Stage3jWe_shared_corpus_contract.sh` | ⚙0.10h/CPU·GPU0 | iWi4h | 완료:train94/val34·source48/12concept·mask/겹침0([101 §39](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md));과거계획한계유지 |
| Stage3kWe | `run_P106B_Stage3kWe_chat32_repeat4_contract.sh` | ⚙0.75h/사용자 GPU | jWe0.1h | 완료:B4update/57,276x-token·SFT감소/native악화·문항0/8([101 §39](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md));과거계획한계유지 |
| Stage3lWe | `run_P106B_Stage3lWe_legacy_repeat4_contract.sh` | ⚙0.75h/사용자 GPU | jWe0.1h | 완료:A4update/67,048x-token·SFT감소/native악화·문항0/8([101 §39](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md));과거계획한계유지 |
| Stage3mWe | `run_P106B_Stage3mWe_lineage_pair_contract.sh` | ⚙0.10h/CPU·GPU0 | kWe/lWe 각0.75h | 완료:child/raw/source SHA연결·DESCRIPTIVE_ONLY([101 §39](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md));과거계획한계유지 |

**판정 분리:** qWb는 코드고정4계약과재시도/슬롯의 기술 PASS, iWh는4프로필/양mask 연결 PASS, iWi는언어별75% **기술 자료량** PASS다. 옛 quality3필드는null이며 통과 status는COLLECTION_TECHNICAL_READY다. 이 값은 정답률이나자료권리 적격이 아니다. B/A 교육은 각자 부모·각자토크나이저/기존 native crop로 전후를 비교하고 같은8질문 첫답/최대3시도를 보존한다. 기존0/8의 rubic과 의미 전체 정답성을 동일하게 취급하지 않는다.

**문자 A/B:** 현재 기본A는같은요청; B는최근32답/256KiB큐·상한64·후보표시상위3을추가하며모드로되돌릴수있다. 같은12요청10반복 CPU비용은 결과§38.3에관측했고 비용선(p95≤200ms·peak≤32MiB)은통과했다. 실제 교사/학생whole-wall·오탐은미측정이라B기본채택하지않는다. 유사도는자동재생성/격리/수락/손실에영향0이다. 임베딩/NLI는 후속 별도 데이터셋 검증 계약으로만남기며이번구현0이다.

**preflight:** 교사입력/샘플링xhigh·8K사고/16K전체/32Kctx는동일설정, 기존실험을반복하지않도록새출력경로/태그/단계명을사용한다. 태그는 `p106b_s3k_contract_chat32_s1337`와 `p106b_s3l_contract_a_s1337`로 별도예약하며 원형을덮지않는다. 풀2배·300M표준은 이소형의4pass배선진단에충족되지않는**의도된 예외**다. 실제토큰=각자tokenizer로직렬화한비패딩대화합×4이고지도토큰/패딩계산상한은별도표시한다. 업데이트수는4×ceil(train행/128), micro8×accum16·seq≤1024·checkpoint-on이다. 동일자료라도어휘가달라토큰분모/부모/구조가달라 **tokenizer단독인과·교차CE순위·300M효과**는금지다. Codex사전조회는허용된정확아티팩트/계산전용레지스트리경로만사용하고전체runs를열지않는다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.



### 2026-10-03 Stage4 복구 회수 (문서 갱신2026-10-04)

[결과101 §46](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에4aWb/4bWb/4c0Wb 세로그와정본4를대조했다. 세단계는**실행완료**다. 예측한전체hash/sourcecap과교사plain field·실제소비계측은성립했다: 큰원천의목표25%cap, literal표지0/48, wire256실제노출/16KO+16EN val. ~~이수리로충분한영어량과학생답변개선~~은확인되지않았다: 영어1.851M/35.649M부족,wire2update/0문항개선.

교사4개묶음은유효token비1.912×이나같은8슬롯의답이50.95%길어졌고wall단축은약1.27×다. 원답의언어혼입/어법·내용문제는남아온라인문구목록판정없이후행검토한다. 공개C 전체주제균형·정식TRAIN_READY·300M교육은미완이다. 미실행4cW/4cWb는취소하지않고부족량선결로HOLD한다. 후속모델진단은새P106C 결과와승인A→B를따르되일반batch/목표는변경하지않는다.

### 2026-10-02 Stage4 회수·순서독립 선별/평문 교사/균형 평가 복구

[결과101 §45](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)의 qWc/4a/4b/4c0는 모두 완료됐다. 예측한 CPU p95계산·교사4개묶음 생산성·학생2업데이트는 작동했다. 그러나 ~~공개C가 충분하고 고르게 구성될 것~~은 EN1.847M·KO의 두 위키 작업83.64%로 불성립, ~~교사 plain content가 깨끗할 것~~은48행 중44행의 literal placeholder로 불성립했다. 학생 실답 전후0/8이라 기술 성공을 교육 성공으로 올리지 않는다.

사용자 A 승인으로 새 공개v2는 전체 prompt hash 정렬/내용 SHA 중복선택/언어별 목표25% source-family cap을 쓴다. 부분 코퍼스는 실제 점유율과 부족량을 따로 보고하며 cap완화/복제/새 다운로드를 하지 않는다. 교사v2는 예시 placeholder 제거·질문/답 목표언어·실제 messages보존·경고 전용 scaffold 관측을 추가한다. 새 wire는 소비한256행과전체준비행을 분리하고 val은 KO16/EN16의 고정hash로 선정한다. 과거 val/속도 원형은 그대로 둔다.

| 단계 | 사용자 실행 파일 | 예상 | 선결/판정 | 현재 |
|---|---|---:|---|---|
| Stage4aWb | `run_P106B_Stage4aWb_balanced_public_corpus.sh` | CPU0.75h | 전체색인·고정SHA·20MB·분포/실제 x부족량, no model | 완료·결과101 §46 |
| Stage4bWb | `run_P106B_Stage4bWb_concept_batch_plain_fields.sh` | GPU1.5h 상한 추정 | 같은8슬롯/양순서·생산성/실제답·경고. 정답성 PASS 아님 | 완료·결과101 §46 |
| Stage4c0Wb | `run_P106B_Stage4c0Wb_balanced_student_wire.sh` | GPU0.5h | v2 exacttrain/val·2update·256실제노출·balanced32val | 완료·결과101 §46 |
| Stage4cWb | [run_P106B_Stage4cWb_balanced_chat32_repeat4.sh](../run_P106B_Stage4cWb_balanced_chat32_repeat4.sh) | GPU12h 잠정 | 같은v2 wire통과·각언어37.5M실제고유량·micro8/accum16/ckptON·4pass | 조건부 HOLD |

이전 Stage4cW는 미실행 원형으로 보존하며 취소/삭제하지 않는다. 현 v1의 영어 부족으로 실행 전 차단된다. full v2도 부족하면 실행하지 않고 부족량을 다음 자료확보/교사생성 계획의 입력으로 삼는다. 분포 변경 때문에 v1/v2 CE 차이를 단일 소스 효과로 해석하지 않는다. 새 모델 태그는 `p106b_s4_mixed300m_balanced_chat32_s1337`; 정확 새 경로 write-once와 학습 전 부모/자료SHA를 검사한다.

별도 사용자 B 승인 연구는 [P106C](P106C_실제-업데이트-선택기와-답변학습-비용게이트.md)가 소유한다. micro8×accum4의 반복 암기/선택 진단 예외를 본 P106B에 전파하지 않는다. 기존 공개75M×4/300M, 사전 파생 격리·교사원형 보존·후행판독 정책은 유지한다.

> 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

**원본 보존·한계:** 이전v32의실제품질/비용·선택값을새 코드 결과로재계산하지않는다. 신규교사/학생/GPU·스모크는사용자실행이고현재NOT_RUN이다. 교사raw/사고·canonical·선택/미선택·교정의계보는20MB이하write-once샤드로남는다. 후행 패킷20개 준비는판독이아니며지금GPT가내용을새로평가하지않는다. 제안서종료는승인범위새사용자실행/결과회수후판정하고 사용자실행대기만으로현재GPT WIP를미완료로유지하지않는다.

### 2026-10-02 후속 — CPU p95 수리와 한정 생성 경로 진단 (Stage3qWc·Stage3sWa)

사용자 회수10로그는 모두 본체 종료0이다. 원형 v33의 교사/양 교육·원답은 보존하며 같은 학습을 다시 실행하지 않는다. 코드 점검에서 소표본 p95의 내림순위 결함과 학생 runs JSON의 시간/분리보고 저장시점 누락을 확인했다. 후자는 원형을 고치지 않고 새 실행의 작성 시점만 수리한다.

| 단계 | 구현·실물 런처 | 독립변수·측정 | 비용·선결 | 판정·한계 |
|---|---|---|---|---|
| Stage3qWc | `run_P106B_Stage3qWc_lexical_ab_percentile.sh` | 같은 동결12질문×10반복 문자 A/B; nearest-rank p95를 명시하고 2/3/120건 CPU 집계 회귀 | CPU0.05h·새 smoke 먼저; 코퍼스/교사/학생 새 생성0 | p95≥median·기존120건 순위 동일·기존 p95≤200ms/peak≤32MiB 유지. 실시간 GPU slowdown·오탐/정답성 미검토; B 자동 채택 없음 |
| Stage3sWa | `run_P106B_Stage3sWa_generation_path_audit.sh` | 정확 A/B 부모·v33 학생4를 순차 로딩. 같은8질문·QA/ChatML·greedy·cache on/off·최대160토큰; 원시 token ID·최종답·기존 prefix 추출·종료 사유; CPU 부모/학생 상태 변화량 | GPU0.25h·전체실행 hard900초. 최신 사용자 smoke43/0/0/0; 이번 사용자 추가회신만 Codex CPU/GPU 직접진단 허가 | 128case와64cache쌍을 빠짐없이 저장. 학습0·교사0·기존 원형 변경0. BF16 greedy 차이는 관측이지 곧바로 cache 논리결함 확정이 아님. 좁은8문항은 광범위 지능 평가 아님 |

**예측:** 업데이트는4회뿐이지만 부모/학생 가중치 변화와 SFT 손실 감소는 관측될 수 있다. 질문 형식 차이·160토큰 끝까지 이어 쓰기·정지 신호 미학습 가능성을 분리한다. 대립 가설은 생성/cache 또는 prefix 추출 결함이며, 같은 checkpoint·같은 question·동일 greedy 안에서 비교한다. 어떤 형식에서도 답변이 부족하면 ChatML만의 문제나 학습 불가능을 단정하지 않는다.

**preflight:** sWa는 재학습이 없어 steps/accum/LR 변경0이고 새 checkpoint 태그를 만들지 않는다. 고정 부모 SHA와 새 v33 child SHA·두 tokenizer SHA를 검사하고 정확 파일만 읽는다. 출력은 `test_result/evidence/101_P106B_Stage3sWa_generation_path_audit.json` write-once와 새 단계 runlog다. 기존 HF/runs/cache/checkpoint는 읽기 전용이며 보호 TinyDataset·교사 모델·외부 전송은0이다. 4×8×2×2=128개 진단, 생성 상한160·greedy0/top-k1·단일모델만 상주. 주어진 표준 micro8×accum16을 accum2로 변경하지 않는다.

**accum 해석:** train94에서는 현재 상한128개보다 작아 epoch당 ceil(94/128)=1·4epoch=4update가 정상이다. micro8×accum2이면 ceil(94/16)=6·4epoch=24update가 되지만 유효배치·gradient 잡음·optimizer 노출횟수가 함께 바뀌므로 단순 오류수리가 아닌 별도 대조다. 기존조건을 유지하면서 update를 늘리려면 고유 train행을 늘리되 반복≤4epoch·자료계보/검증분할을 지켜야 한다. 예: train1024행이면 동일 micro8×accum16·4epoch에서32update이며 실제 대화토큰은 패딩 상한과 별도로 계산한다. A 결과 이후 개선안은 사용자에게 다시 제안한다.

#### Stage3sWb — A의 관측된6쌍만 FP32 수치 대조 (동일 일회 A 진단 범위)

Stage3sWa 128건/64쌍을 실행한 뒤 BF16 greedy token이 다른6쌍을 관측했다. 새 `run_P106B_Stage3sWb_fp32_cache_recheck.sh`는 이6쌍만 같은 체크포인트/입력/160상한으로 FP32 forward·quantized shadow FP32·TF32 off에서 캐시 on/off를 비교한다. 출력은 별도 `test_result/evidence/101_P106B_Stage3sWb_fp32_cache_recheck.json`, 최대12생성·hard300초·GPU0.10h이며 모델/교사/학습 추가0이다. 관측6쌍이 아니면 거부한다. 여섯 쌍이 모두 일치하면 그 BF16 차이가 정밀도 경로와 관련 있음을 확인할 뿐 모든 캐시의 논리정확성을 일반화하지 않는다. 원형 A/로그/체크포인트는 변경하지 않는다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

### 2026-10-02 실행 이력·예측 대조 — Stage3 완료와 Stage4 혼합75M/300M

[결과101 §39~§44](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)가 지정10단계·일회 A/FP32 두단계의 원형/정본/실답/재현을 소유한다. Stage3sWa는128생성/64cache쌍에서prefix/mask오류0이고, Stage3sWb에서BF16 QA차이6쌍은FP32모두동일했다. 이 진단에만 허용된 GPU 권한은 종료됐다. sWa/sWb SH와 지정10 SH는 완료12본의 역사로 옮긴다. 새 대량자료/학습·종합smoke는NOT_RUN이다.

**예측 대조:** v33 기술자료/양mask·각4update는작동했지만지능향상은확인되지않았다. 실제SFT손실감소/native악화·반복/요구형식실패0/8을유지한다. A는이번표본에서추출결함을지지하지않았고QA형식변경만으로회복하지못했다. p95/최종저장시점은기록결함이지교육0/8을고친것이아니다.

**Stage4 질문/예측:** 공개 C로교사전면생성의100일규모비용을줄일수있는가? 서로다른concept2~4개를한요청에서생성하면유효학생tok/s가늘어나는가? 75M고유train의4pass에서지시/종료/QA가개선되는가? 양이커도원천분포/오답/부모한계로실답이좋아지지않을수있다.

| 단계 | 정확 SH | 비용·자원 | 선결·판정·상태 |
|---|---|---:|---|
| Stage3qWc | [run_P106B_Stage3qWc_lexical_ab_percentile.sh](../run_P106B_Stage3qWc_lexical_ab_percentile.sh) | CPU0.05h | 새smoke 뒤 nearest-rank 수리의동결문자비용 재시험;실물NOT_RUN |
| Stage4aW | [run_P106B_Stage4aW_mixed_public_corpus.sh](../run_P106B_Stage4aW_mixed_public_corpus.sh) | CPU0.75h·모델0 | sourceSHA/첫질문split·1024mask·37.5M/언어quota·20MB선택샤드/부족분. 기술exit0과token_target_ready/품질은별도;전량NOT_RUN |
| Stage4bW | [run_P106B_Stage4bW_distinct_concept_batch.sh](../run_P106B_Stage4bW_distinct_concept_batch.sh) | 사용자GPU1.5h/hard3h | 같은한영각4concept·xhigh·1서버·28논리/최대84completion·1→2→4→4→2→1·8192사고/16384총/32768ctx.8slot완결과두순서쌍속도비>1.05 분리;정답성NOT_RUN |
| Stage4cW HOLD | [run_P106B_Stage4cW_mixed_chat32_repeat4-hold.sh](../run_P106B_Stage4cW_mixed_chat32_repeat4-hold.sh) | 사용자GPU12h 역사추정 | 옛v1 영어부족/별도quota는미충족. 사용자2026-10-06 A로취소없이보존. 해제는선결및새결정후만, held 직접실행8 |
| Stage4c0W | [run_P106B_Stage4c0W_mixed_student_wire.sh](../run_P106B_Stage4c0W_mixed_student_wire.sh) | 사용자GPU0.5h | 부분C언어당128train/전체8val에서원batch/optimizer/stream/저장경로2update·새wire출력·teacher다운. 대량4c 앞선결·300M과품질PASS가아님;실물NOT_RUN |

**preflight/자원:** 원래batch 유지·새태그 p106b_s4_mixed300m_chat32_s1337. SFT변동길이의실제x-token을합하고패딩상한131072/step과분리한다.75M고유train/≤4epoch/300M은승인반복SFT축이고복원추출pretrain2배풀과동일비교가아니다. 마지막그룹은실제assistant targets로정규화한다. Collector는현재영어부족을적고같은문항재생성/무한반복으로채우지않는다. 판정자는기술선결·사전기존문항/자기native손실이고범용sigma를복사하지않는다. 8GiB디스크 초기선·현재32K교사와full학생의자원을단순합산해공존안전이라고하지않는다.

**원천/한계:** Collection 잠재390M은4000행표본의길이외삽이며적격량아님. 알려진평가source와혼합하위평가우려family를metadata로제외한다. 공감형/Carrot는기본C에서자동채택하지않는다. 영어확대UltraChat200k train_sft의고정revision/SHA·사용자선언 어댑터만준비했고취득0이다. teacher/B속도/대량학습·전체오염/사용조건·후행GPT/임베딩NLI는NOT_RUN. 형식기술성공을지능으로올리지않는다. 추가원문재가공/고유100M은이학습의효과를보고새단계/버전으로검토한다. 보호사전/word 접근0.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 2026-10-05 추가 계획 — Stage5 MTP Bonsai2 교사·선택적 LoRA

### 왜·질문·승인 범위

사용자가 내려받아 CLI 구동을 확인한 MTP 포함 GGUF를 교사 생산성 후보로 추가한다. Q1은 같은 파일에서 MTP를 켰을 때 decode·전체 요청 시간이 좋아지는가, Q2는 LoRA 배율1.0의 속도·메모리 대가와 실제 거부 응답이 어떻게 달라지는가다. 학생의 P101A MTP 보조손실과 다른 **외부 교사 추론** 기능이다. 기존 교사를 새 파일로 교체하거나 학생을 학습시키는 범위는 아니다.

세 안을 비교해 사용자 **C: 실제 거부 확인 후 LoRA 실행**을 선택했다. A는 요청 배율1.0의32응답을 바로 대조해 구현 변화가 작다. B는0.5/1.0을 함께 대조해 답변 변화의 절충을 보지만48응답으로 비용이 늘고 adapter 로드 크기는 줄지 않는다. C는 MTP16응답부터 수집하고 허용되는 교육 질문의 실제 거부를 확인했을 때만 이미 준비한 LoRA32응답을 연다. **C를 구현**하며 B의 배율0.5는 이번에 추가하지 않는다.

### 자산·구현·영향 범위

| 자산 | 정확 파일·관측 | 지위 |
|---|---|---|
| MTP model | `HF/models--ayshinko--Ternary-Bonsai-2-27B-PTQ1_0-MTP-gguf/Bonsai-2-27B-PTQ1_0-MTP-Q8_0.gguf` ·6,397,969,728bytes·SHA`4C21BFCFA7E643D32179DB409751941C5D1F7FCF188901C286E37D3913809CD1` | header `qwen35`·65blocks·MTP 예측층1·메타데이터 확인 |
| LoRA | 같은 폴더 `adapters/bonsai-abliterate-lora.gguf` ·9,682,464bytes·SHA`F1669534803D340A496015F5C45125F3437B4D13EC764F40E34488CE83967F42` |258텐서/129쌍·qwen35·배율1.0·런타임효과미측정|
| Runtime | `/home/uranus/llama-prism-bin-ubuntu-x64-cuda133/llama-prism-b10743-adfffbe/llama-server` ·SHA`F0321669B20397593E3AC09972BF6F4B7A0684954906565353B7CA84B4B0320F` |실제help에draft-mtp/nmax/LoRA-scaled 지원;코어/공통/CUDA 6라이브러리도SHA 고정|

메타데이터의 예측층 수1과 `--spec-draft-n-max 2`는 다른 설정이다. head 존재는 실행 활성화·수락률의 증거가 아니다. 모델과 LoRA 원본은 읽기 전용이며 별도 다운로드·원본 변환은 없다. 129쌍의 대상/차원을 확인했고 embedding의 LoRA-A는 일반 Linear와 축 배치가 달라 별도로 검사했다. [upstream adapter 검사](https://github.com/ggml-org/llama.cpp/blob/master/src/llama-adapter.cpp)는 `token_embd.weight`를 분기한다. 이 구조 호환은 실제 ternary CUDA LoRA 성능까지 보장하지 않는다.

[프로파일/순수 계약](../scripts/p106b_mtp_teacher.py)·[진단기](../scripts/diag_p106b_mtp_teacher.py)·[CPU 회귀](../scripts/test_p106b_mtp_teacher.py)를 신설한다. 기존 TeacherSession·모델 기본경로·student optimizer·토크나이저·기존 원본 보고는 수정하지 않는다. 데이터 쓰기는 사용자 실행 후 새 `HF/sft_ready/p106b_mtp_teacher_v1/<mode>/`에만 하며 20,000,000byte 이하 샤드/SHA로 원답과 사고를 보존한다. 코드·테스트·계획/레지스트리/나침반 영향만 이번 승인에 포함된다.

### 예측 — 더 빠르다고 가정하지 않는다

MTP가 여러 후보를 싸게 제안하고 target 검증에서 충분히 수락되면 decode가 빨라질 수 있다. 반대로 수락률이 낮거나 검증·GDN 융합·추가 상태 비용이 크면 느려질 수 있다. LoRA 파일은 약9.23MiB지만 실제 GPU/RSS·workspace 대가가 그 크기와 같다는 보장은 없다. 배율1.0이 거부를 줄이더라도 질문 충실성이나 사실성이 나빠질 수 있다. 현재 실제 개선/거부율은 **NOT_RUN**이다.

### 단계·런처·자원

| 단계 | 정확 런처 | 내용·비용 | 상태·선결 |
|---|---|---|---|
| Stage5aW | `run_P106B_Stage5aW_mtp_asset_contract-done.sh` | CPU 회귀·모델/adapter/runtime SHA·GGUF header와layout·약0.05h |사용자 CPU 완료;[101 §47.2](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md);모델0|
| Stage5bW | `run_P106B_Stage5bW_mtp_speed_pair-done.sh` |교사 단독 base→mtp→mtp→base,총16요청·실제phase184.962초 |사용자 완료·가속음성;[101 §47.3](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)|
| Stage5cW | `run_P106B_Stage5cW_mtp_lora_factorial-done.sh` |설정32요청이나 실제교사0 |시도회수HOLD8·거부증거없음;[101 §47.4](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)|
| Stage5dW | `run_P106B_Stage5dW_lora_refusal_postreview-done.sh` |설정후행CPU;실제검토0 |시도회수HOLD8·상류없음;[101 §47.5](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)|

하나의 요청 팔이 backend 오류를 내면 원본을 보존하고 독립 팔을 수집한다. 전체 wall 상한은 내부 예외처리에서 삼키지 않는다. sampler/nvidia-smi 오류는 메모리 측정을 무효로 기록하며, free<512MiB는 자원 음성이다. 교사 로딩 뒤 여유2GiB를 요구한다. 총 카드메모리 약16GiB에서 **교사 단독**이며 기존 학생과 동시 상주 안전성을 단순 합산으로 보장하지 않는다. 모델 로딩·GPU·새 smoke는 사용자 소유다.

### 고정 조건과 비교의 분모

동일 MTP GGUF·동일 바이너리/라이브러리·한 slot·full GPU·fit off·no-op-offload·32,768 context를 사용한다. 기존 선택 xhigh와 모델카드 thinking sampler를 유지한다: temperature1.0/top_p0.95/top_k20/min_p0.05/presence0/repeat_penalty1.0. 사고8,192·합계출력16,384를 구분하고 서버의별도사고예산옵션도 명시한다. 저문맥·비사고 mode를 섞어 MTP 효과로 주장하지 않는다. 공식 추천 근거는 [Bonsai2 모델카드](https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf)다. 사용자 파일과 이름이 다른 최신 Swift/Katana 파일의 설정을 조용히 적용하지 않는다.

서버의 실제 chat template와 tokenizer로 입력을 센 뒤 input+max_output+128≤context를 확인한다. 같은질문/round의 적용prompt SHA·입력token·seed를 네조건에서 대조한다. 매 요청은 새 system/user 메시지이며 cache_prompt=false를요청한다. 실제 cache_n과 prompt_n은별도기록하므로캐시가항상0이었다고추정하지않는다. 한영 단답/다중답 4개 코드 작성 교육문항을 고정하며 현재교사생산자료의복사·보호데이터접근은없다.

보고는 (1) backend decode token/time (2) 전체RPC completion token/time (3) 최종문구/사고길이·형식완결·technical candidate수 (4) 첫요청/후속요청 (5) 모델startup (6) baseline 대비 GPU 표본 peak/RSS·free를 분리한다. `whole_wall_sec`는첫startup부터마지막팔까지이며 자산SHA검증·마지막보고/패킷저장은범위밖이다. 자산검증시간은별도기록한다. [llama.cpp server timing 안내](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)는 predicted_n/predicted_ms와usage를 제공한다. fork가draft 수락 카운터를 응답하지않으면그값은null로남기고키워드에서가짜수락률을만들지않는다.

### 판정·거부 검토·C 실행조건

끝나면 stdout에 실제질문/최종답을직접보여주고 `review_packet.md`에서같은질문의조건별답을모아본다. 사고는raw sidecar에따로저장하며학생학습은0이다. 두실행순서의MTP speed ratio와LoRA on/off speed·GPU/RSS delta를보고한다. 두순서가반대면일괄가속채택하지않는다. 형식완결·시간·draft수락이정답성이나거부감소를뜻하지않고, 이번계열sigma는미측정이다. exit0은완결비교이며비채택음성도유효하게보존한다.

거부는 **허용되는 교육 질문을 명시적으로 거절해 실질 답을 제공하지 않은 경우**로 후행판독한다. 인용된거부문구·불확실성·출력절단·형식오류를문자열로자동거부판정하지않는다. label은 ANSWER/REFUSAL/PARTIAL/INVALID/UNSURE와근거·reviewer다. base가전부답했다면LoRA의거부감소이득은이표본에서입증불가다. 전체후행label이없으면거부율은null이며0으로위장하지않는다.

C선택을코드로검사한다. `HF/sft_ready/p106b_mtp_teacher_v1/lora_trigger.json`은실제교사원본의정확JSONL·SHA·행·질문/최종답fieldpath·텍스트SHA·판독자를가리켜야한다. 기존공식Bonsai2 또는이번MTP파일에서관측한거부만대상으로하며확정적으로관측된허용교육거부라는후행기록이필수다. 지정source는비보호 `HF/sft_ready/`의20MB이하JSONL로한정한다. 보호사전/다른데이터경로를연결하지않는다. 이파일이없으면5c execute는모델시작전에HOLD8로끝나며stdin을읽지않는다. 예시schema:

```json
{
  "schema": "P106B_LORA_OBSERVED_REFUSAL_V1",
  "source": "HF/sft_ready/p106b_mtp_teacher_v1/mtp/raw_000000.jsonl",
  "source_sha256": "검산한 정확64자리SHA",
  "line_number": 1,
  "source_model_sha256": "4C21BFCFA7E643D32179DB409751941C5D1F7FCF188901C286E37D3913809CD1",
  "question_path": ["question"],
  "answer_path": ["metrics", "final_text"],
  "question_sha256": "해당질문SHA",
  "final_sha256": "해당최종답SHA",
  "allowed_educational_request": true,
  "observed_refusal": true,
  "reviewer": "실제판독자",
  "reason": "질문과답을함께읽고판정한근거"
}
```

이예시는실제증거가아니다. 첫줄이metadata인raw에서는실제response행번호를검산해야한다. 원본돌연변경·중복label·미판독은검사에서거부한다. 데이터셋전체품질검증·교사기본LoRA채택·교사MTP의학생동시교육효과는후속실물결과로별도판단한다.

### preflight·한계·2026-10-05 준비 이력

- 학습0·새checkpoint0으로steps/2배학습풀은해당없다. 기존학생배치/optimizer/LR/tokenizer는변경하지않았다.
- 새로운phase명·출력namespace를확인해기존원본/정본충돌을피한다. 새출력이나중단로그가있으면조용히지우지않고새suffix/버전으로재시험한다.
- metadata 검사와CPU/mock orchestration이통과해도CUDA·MTP활성·LoRA속도/거부율PASS로올리지않는다. 사용자의단독CLI확인은참고관측이며우리대응벤치수치가아니다.
- 동일seed에서도확률샘플링·speculation의난수소비차로문구가달라질수있다. 저장/상주/표본peak를구분하며짧은4문항거부율을전체생성률로외삽하지않는다.
- 구모델GGUF와새MTPGGUF의차이에는변환/추가head가포함되므로기존60tok/s와직접MTP인과비교하지않는다. **같은새파일off/on**이주대조다.

현재자산header/129LoRA쌍/정확SHA·실제serverhelp옵션을읽기전용으로확인했다. 사용자지시에따라런처4개를작성했고 C의거부관측선결을구현했다. GPU·교사generation·LoRA거부/속도수치는NOT_RUN이며HF기존원본·기본교사를변경하지않았다.

> 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 2026-10-05 실행 회수·후속 — 하위 성공과 전체 판정을 분리

기존 Stage5 준비절은 당시 설계 이력이며 현재 수치/상태는 [결과101 §47](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)이 소유한다. 자산/같은파일 MTP가 실제 작동한다는 기능 예측은 맞았지만 **가속 예측은 현 조건에서 틀렸다**. draft수락52.7071%·GDN융합활성에서도 두 순서 decode비0.8224/0.7986이고 추가GPU 약900MiB다. 생성량/사고/문구가 달라 전체요청 시간비를 동일답 시간비로 쓰지 않는다. MTP를 자동 켜거나 한국어 향상이라고 쓰지 않는다.

Stage4cWb는 영어35,649,183토큰부족으로execute 미호출이다. Stage5c는 사용자C의 실제거부 증거가 없어교사0,5d는그상류가없어검토0이다. 실행시도가끝났다는-done과 모델/정답 검증이끝났다는판정을구분했다. 원형/재현15child는같은결과§47.8에보존한다.

회귀17PASS의화면987B는중간상태였고최종5d는35행2446B다. 로그 유실은없지만 review check-only의 무검사0과 LoRA check-only의 C검사생략은 준비판정을혼동시켰다. 사용자A의 [재발방지 제안](../proposal/done/20261005_P106B-단계완료와-전체실험판정-혼동-재발방지-제안서-approved.md)에따라 P106B caller만수리했다. 공용runlog/queue/전역훅·스킬·검사기/기본교사/원배치변경0이며학생·모델재실행은사용자소유다. 승인 구현·CPU29조건 검증을 완료해 제안은 done으로 종결하되 사용자 새smoke와 실제모델효과는 별도 미실행이다.

| 단계 | 정확 SH | 비용·독립변수 | 선결·판정 |
|---|---|---|---|
| Stage5eW 완료 | `run_P106B_Stage5eW_stage_receipt_contract-done.sh` |CPU0.05h, COMPLETE/HOLD/ERROR fixture3·모델0 |[101 §48](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md): 사용자 CPU12/FINAL3phase PASS; 재현 원형 Git 보존|
| Stage4cWc HOLD | [run_P106B_Stage4cWc_balanced_final_verdict-hold.sh](../run_P106B_Stage4cWc_balanced_final_verdict-hold.sh) |조건부12h·옛v2불변 |옛v2 영어35.649M부족. 새v3완료와다른자료. 사용자A로보존·활성큐제외·직접8|
| Stage5cWb HOLD | [run_P106B_Stage5cWb_lora_conditioned_final_verdict-hold.sh](../run_P106B_Stage5cWb_lora_conditioned_final_verdict-hold.sh) |조건부2h·원LoRA1.0/32요청 |실제허용교육거부원형/SHA없음. 사용자A로보존·직접8·선결과새결정후해제|
| Stage5dWb HOLD | [run_P106B_Stage5dWb_review_conditioned_final_verdict-hold.sh](../run_P106B_Stage5dWb_review_conditioned_final_verdict-hold.sh) |CPU0.05h·상류32원답/주석 |실제LoRA32답+후행32label 부재. 사용자A로보존·직접8·허위거부율 작성금지|

**preflight:** teacher-only/CPU 진단의 학습steps0은 실제 학습량이 아니다. 미승인 zero-step registry의 broad조회를 하지 않고 정확 source/태그/원배치·출력namespace를 직접대조한다. 새callback의phase명/SH/name을함께변경했고oldHF/runs/cache를재생성하지않는다. 같은벤치MTP의음성을새코드실행으로덮지않는다. 조건부 모델3SH는선결전실행순서에자동포함하지않는다.

**한계:** 회귀와CPU receipt는원본/GPU/장기학생교육/한국어/정답성PASS가아니다. caller수리로 영어자료량이나 실제거부가생기지않는다. 다음 queue는새smoke→CPU5e 이후이며나머지는선결HOLD를유지한다.48h를채우기위해완료된MTP를반복하거나부족자료로학습하지않는다.

## Stage6aW — Qwen 후보 교사의 실제 역할과 chat32 학생 공존 (2026-10-05 사전등록)

### 1. 왜 / 2. 질문

사용자가 지정한 IQ2_XS-mtp GGUF와 llama-b11396을 별도 후보로 고정한다.
기존 Bonsai 한국어 우려와 영어 자료 부족은 같은 문제가 아니다. 우선 이 후보가
교육용 최종답을 내고 **실제 목표 학생과 함께 GPU에 들어가는지** 확인한다.
교사만 로드되거나 작은 legacy 학생만 들어간 것으로 chat32 dense 공존을 주장하지 않는다.

### 3. 예측

8.77GB 파일에 MTP·context·작업 버퍼가 추가되므로 16GB에서 학생 학습 peak와
합산하면 OOM 또는 여유 부족이 가능하다. 한국어 출력 가능성은 공식 다국어 모델과
사용자 다운로드에 근거하지만, 양자화된 해당 파일의 정답성은 이 4문항으로 일반화할 수 없다.

### 4. 단계 / 5. 판정

1. CPU: 모델/런타임/학생/tokenizer SHA, GGUF MTP header, 옵션·6회귀.
2. GPU: idle/free≥14000MiB일 때만 localhost 교사 한 벌. full offload,
   fit off/no-op-offload, MTP draft2, 한 슬롯/context8192, low, 사고1024/총3072.
3. 교사-only: 한국어 설명·영어 산술·한국어 문맥조회·번역 4요청.
   `reasoning_content`와 final 원형을 분리 보존하고 기존 태그 파서를 사용한다.
   문구 blacklist/온라인 의미합격 판정은 하지 않는다.
4. 같은 서버가 살아 있는 상태에서 P090B chat32 dense14 부모를 strict 로드.
   micro8×accum16·checkpoint ON·compile default·길이1024의 합성 assistant-mask
   1회 업데이트와 추가 교사 1요청을 겹친다. 시간·전역200ms peak/free·Torch peak를 기록한다.
   길이1024 패딩은 자원 상한 측정을 위한 것이며 실제 고유 대화량과 구분한다.
5. OOM은 실제 예외, 여유512MiB 미만은 안전음성, backend/계측 오류는 tool failure로 구분.
   원형 JSON/최종상태를 새 경로에 남긴다. 체크포인트 저장·정식 SFT·기본교사 교체 없음.

### 6. 비용 / 7. 실행

최대20분·GPU16GB, 교사 최대5요청 및 학생1합성 업데이트.
`run_P106B_Stage6aW_qwen_chat32_coload_role-done.sh` (완료 원형은 Git archive로 보존).
이번 사용자 추가 지시에 한해 Codex 직접 CPU+GPU 실행을 허가받았다. 이 권한은 대량
코퍼스 생성·후속 학습·smoke/queue 실행으로 확대하지 않는다.

### 8. 한계 / preflight

새 Qwen 파일/런타임/샘플러·low는 기존 Bonsai/xhigh와 다르므로 속도·한국어 품질의
단독 인과 비교가 아니다. 공식 Qwen 사고 sampler의 min_p=0을 사용한다.
1×8×16×1024=131072 **패딩 슬롯**이며 고유 train 75M 또는300M 교육이 아니다.
2배 풀 규칙은 이번 반복 합성 자원 게이트에 해당하지 않는다. 부모/원본/캐시 불변,
새 Stage6aW와 evidence 경로가 비어 있음을 확인하고 broad runs registry는 열지 않는다.

> 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

### 9. 실행 이력

2026-10-05 실제 실행을 [결과101 §49](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에 회수했다.
자원 성공 예측은 맞았지만 빈 NOTE 파서 때문에 첫 역할 wire3/4로 전체8이다.
실제 학생 업데이트1·OOM0·전역peak15023/최소여유1039MiB이다. 언어 전반·대량 교육은 미검증이다.

## Stage6bW·Stage4aWc/Wd·4c0Wc/4cWd — 래핑 복구와 영어 부족의 실행 경로

### 1. 왜 / 2. 질문

기존 공급 함수는 Aya Collection의 한국어2파일만 연결했다. 영어 추가 adapter가
존재하는 것과 실제 원천·manifest가 확보된 것은 달랐고, 이를 선결HOLD 보고로
반복한 것이 준비상의 미완이었다. 현 v2는 한국어37,500,482/영어1,850,817 train
비패딩 토큰이며 부족 영어35,649,183이다. 기존자료와 영어 train7파일을 함께
해시 순서로 새 버전에 선별하면 어느 출처에서 얼마를 얻는지 확인한다.

### 3. 예측

같은 Collection의 영어7파일은6,321,198,481B이며 여러 실제 원천 가족을 포함한다.
한국어보다 원문이 많은 만큼 부족분을 줄일 가능성이 있지만 1024 context·중복·평가
가족 제외·각 가족9.375M 상한을 적용한 뒤75M이 확보될지는 미측정이다.
빈 NOTE 선택필드 정규화는 질문/답 내용을 바꾸지 않아 배선 복구가 예상된다.

### 4. 단계 / 5. 판정 / 6. 비용 / 7. 실행

| 단계 | 사용자 SH | 예상 비용 | 판정·선결 |
|---|---|---|---|
| Stage6bW 완료 | `run_P106B_Stage6bW_qwen_wrapper_role-done.sh` |실제13.191초 teacher-only |[101 §50](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md): 원답 불변·빈 선택 NOTE wrapper 제거·4/4 첫 시도 완결, 학생 재학습0|
| Stage4aWc 완료 | `run_P106B_Stage4aWc_english_collection_fetch-done.sh` |실제9.9분 |[101 §51](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md):7train SHA검산·6.32GB 확보·모델0|
| Stage4aWd 완료 | `run_P106B_Stage4aWd_english_refill_corpus-done.sh` |실제103.3분 |[101 §52](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md): 고유75,000,817 x/24,129,790지도·부족0·과제/권리품질은별도|
| Stage4c0Wc 완료 | `run_P106B_Stage4c0Wc_refill_student_wire-done.sh` |실제4.8분 |[101 §53](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md):2update/256행·38,050x·원답0/8·4pass아님|
| Stage4cWd 완료 | `run_P106B_Stage4cWd_refill_chat32_repeat4-done.sh` |실제runlog5.615h |[101 §54](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md):300003268x/96519160지도·15752updates·SFT감소/native+1.485747·원배치불변|

출력은 `HF/sft_sources/p106b_aya_collection_en_a3af2fde` 및
`HF/sft_ready/p106b_mixed_public_v3_en_refill`/학생v3뿐이다. 원형v1/v2와 기존
추가 원천 manifest를 덮어쓰지 않는다. 영어집합은 train만 사용하고 최종 split은
현재 계약인 첫질문 hash modulo20을 유지한다. 출처 계보/원천 품질과 번역 문항의
cross-language 의미 누설까지 자동 해결됐다고 주장하지 않는다.

Stage4cWc는 원v2만 읽으므로 임의 활성화하지 않는다. 새v3의300M 실험은 별도
4cWd로 구분하고 기존 목록·원형은 보존한다. Stage5dWb의 결손은 SFT 영어가 아니라
실제 LoRA32답과 후행label이다. 사용자C의 거부관측 선결을 가짜 자료로 채우지 않는다.

### 8. 한계 / preflight

75M×4는 반복 없는 고유75M 및 실제 노출300M 목표다. 원자료를 단순 반복해서
75M이라고 쓰지 않는다. 이 SFT 반복 설계는 사용자 별도 승인이고 사전학습2배풀
규칙을 기계적으로 적용하지 않는다. 적정 권리/정답성/학생 능력은 각각 후행 평가다.
Collection 카드 Apache 표시는 모든 파생 출처의 일괄 권리 판정이 아니다.
fetch 중 `.partial` 실패는 보존하고 완성 파일은 SHA가 같을 때만 재사용한다.
신규 fetch/CPU선별/본학습은 Codex 직접 미실행이며 Qwen 제한게이트 허가로 확대하지 않는다.

### 9. 실행 이력

Stage6bW는 실제4/4로 배선 복구 예측이 맞았다. 그때 미실행이었던 영어 공급은
2026-10-05 §51~§53에서7train/75M/학생2update로 실제 회수됐다. 부족분 회복 예측은
맞았지만 sourcecap이 QA/논리/명시적 멀티턴 균형을 보장한 것은 아니다. 본교육300M은
아직 NOT_RUN이고 4cWd 선결 CPU는 같은v3/wire SHA로 통과했다.

## Stage4dW — 기존 A 교육 뒤 B 다축 평가 (2026-10-05 승인)

### 1. 왜

기존8문항에서 부모와2회 학생 모두0/8이었다. 비밀 단어 한 프롬프트의 복사는 실제
멀티턴 기억 시험이 아니며 SFT/native 손실과 실제 답안도 다른 지표다.
사용자는 **B=A+후속 다축평가**라면 승인한다고 확정했다. 이미 준비된 같은4pass
교육·자료·배치·LR·기존8평가는 그대로 유지하고 완성 학생과 부모의 추가 원답을 모은다.

### 2. 질문

지식QA/문맥조회/논리·산술/정확형식/코딩/한국어·영어와3턴 기억·수정이 각각 어느
정도인가? 일반 언어 손실 감소만으로 놓친 답변 반복과 형식/내용 이탈은 무엇인가?

### 3. 예측

75M×4 교육이 실제로 수행되면2회 wire보다 형식/종료를 배울 여지가 있다.
반면 자료의 문장변형·문단후속·요약 비중, 모델의 작은 용량, 실제3턴 학습 비율과
기존 위키 반복 때문에 일부 능력은 실패할 수 있다. 정답이 나와도 작은 후행 패널을
광범위 지능/한국어 전반/40MiB 배포 성공으로 확대하지 않는다.

### 4. 단계 설계

1. CPU:새패널24단일턴+4개3턴 대화(모델당36첫답)·72계획콜·출처/파일SHA를 고정한다.
   선택코퍼스 SQLite를 읽기전용으로36개 첫질문해시만 조회한다. 현재 exact overlap0은
   의미/사전학습 오염 없음의 증거가 아니다. 실제 benchmark가 아니라 후행진단이다.
2. 본교육 기존4cWd:micro8/accum16/ckptON·LR1e-4/Muon4e-4·같은v3·4pass 유지.
3. 새4dW:완료된4pass child와자기chat32 부모만 순차로 GPU에 로드한다. two-update
   wire child를 대신 쓰지 않는다. 정확 교육 sidecar·4완료epoch/300,003,268x·체크포인트
   내부sft/step·같은tokenizer/architecture를 대조한다. 이전응답을 다음user문맥에 실제로
   넣고 각 episode마다 초기화한다. 추가 학습·교사·체크포인트 저장0.
4. 각응답은160토큰·입력800토큰·같은greedy/seed·첫답만, 재시도0. 역할경계 표지만
   이력에서 문자로 escape하고 raw는 보존한다. 의미내용을 교정하지 않는다.
5. 응답마다 저장/flush한 뒤 다음질문을 요청한다. 중단/오류/누락을 부분manifest로
   보존하고 기존출력/로그를 덮지 않는다. 각 원형질문·실제prompt·답·종료/시간·grade를
   stdout와JSONL에 보존하며 마지막 실제호출수/72계획/미검토품질을 함께 보고한다.

### 5. 판정

도구 완료는 두모델의36+36 원답 수집이며 지능PASS가 아니다. 명확한literal/JSON/산술
**출력계약**은 코드로 확인한다. JSON의정수5와float5.0/booltrue를 혼동하지 않는다.
자유QA/번역/코드 의미는 후행판독 대상이고 생성코드는 실행하지 않는다.
정답 문구가 다양할 수 있는 행을 word blacklist로 자동REJECT하지 않는다.
전제파일 부재8, 스키마/SHA/추출 불일치9, 사용자중단130으로 분리한다.

### 6. 비용 / 7. 실행

GPU 예상0.25h·상한0.5h, 실제답 길이/초기화에 따라 달라진다. corpus재생성/추가교육0.
완료원형 `run_P106B_Stage4dW_refill_multiaxis_eval-done.sh`, 재현은 [101 §55](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md).
모델/GPU 실행은 사용자 소유다. 지금 완성4pass checkpoint가 없어 check-only는
패널CPU 확인 후 상류HOLD8이며 GPT 구현 완료와 사용자의 본교육 대기를 구분한다.

### 8. 한계 / preflight

새 같은구조/어휘 두endpoint 비교, 추가train0·2배풀은평가에서 해당없다.
본교육 조건 변경 없음. 새4dW·새ignored HF 출력만 사용하고 원본로그/weights/cache는
불변이다. 일부역할 표지는 안전한이력문자로 escape될 수 있으며 변형을기록한다.
자유답의정답성은자동보증하지않고 학습노출/언어분모·loss·내용·형식을분리한다.
기존8문항 최대3시도와 새36첫답의 점수를 같은지표로 합산하지 않는다.

### 9. 실행 이력

2026-10-06 사용자완료:정확부모/완성학생72첫답·자기history3턴과원답/종료/SHA를회수했다.
명시계약양0/26·학생EOT28/36·parentMAX_NEW35/36이다. 구현된수집/종료경로는동작했으나
예측한교육효과는미확인이다. 형식만어긴맞는색상/논리결론도별도로기록했다([101 §54~§55](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)).
본교육도실제300M완료로상태변경하며, 저장epoch 대조와QA/형식/명시적멀티턴 새자료준비를 병행한다.

## Stage4eW / Stage4fW / Stage4g0W / Stage4gW — 저장epoch 대조와 과제정렬 자료·새300M (2026-10-06 승인)

### 1. 왜

[결과101 §54~§55](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)는
실제300M교육 완료와 native+1.485747/명시계약0/26을 함께 관측했다. 더많은같은자료 반복으로
노출부족을 설명할 수 없다. 사용자는 A저장epoch대조+B자료·새300M준비 병행을 승인했다.
GPU/모델은사용자 실행이고 GPT는코드·CPU검증·SH까지 준비한다.

### 2. 질문

어느epoch부터 답변변화/언어손실이 나타났는가? 공개 원천의 QA후보를 선별하고 명확한
JSON 출력·명시적 대화턴을 추가하면 목표과제 학습과 언어보존이 개선되는가?
자료량 준비·출처후보·마스크·실제역량·정식적격성을 분리한다.

### 3. 예측

epoch2가 SFT-val 최저였어도 native/답안 최적이란 보장은 없다.
명시적 출력/기억 대화는 현재자료보다 목표와 가깝지만 작은부모·고정LR·원천의 미검증내용으로
여전히 실패할 수 있다. 새자료75M을 확보할 수 있는지도 미계측이며 부족은그대로보고한다.

### 4. 단계 설계

- **Stage4eW**: 같은 parent와저장epoch1/2/3, 최종4pass endpoint를 비교한다.
  부모/최종의기존72답은SHA잠금재사용하고 중간3모델108첫답만새생성한다.
  총180답/5모델의같은패널이고 native는현재같은 val.bin SHA에서5모델 모두재측정한다.
  원본checkpoint는읽기전용, teacher/train/newcheckpoint0, 기존EOT160/입력800/greedy를유지한다.
- **Stage4fW**: 현재핀된12공개원천만두번순회한다. source-task metadata로QA후보를 고른다.
  Aya/OASST1+2와Flan-Coqa/NQ-Open/MLQA/SQuAD/TyDiQA 등선언된가족 후보만단일턴으로사용하고 다른미분류는제외계수한다.
  현재각parquet 첫16행의metadata표본에서Flan-Coqa(T)/NQ-Open(T)를직접확인해alias를반영했다.
  이표본은전체QA가용토큰/전체자료품질census가아니다. Flan-Coqa의문자열대화도곧바로역할다회전으로세지않는다.
  실제4메시지이상 원천대화는내용/역할을유지한다. source명은오답문구목록/내용정답검사가아니다.
  단일원천첫질문해시당하나만50/25/25 hash배정(일반QA/JSON형식후속/기억후속)한다.
  JSON후속은코드가정수와result/count/value/number 키를프롬프트에명시하고정답JSON을감싼다.
  형식정수범위는train2~79/val80~98로분리하고UNIQUE_JSON 계약을기록한다. 유한형식의반복노출은
  별도제어훈련이며새고유지식/새로운정답정보라고세지않는다. source첫질문분리와의일치를CPU로검증한다.
  기억후속은원답→준비/READY→첫답JSON복원으로실제3user턴을구성한다.
  이는 **코드작성형식/기억훈련이며 자연스러운사람대화·새지식이아니다**.
  원천다회전/코드형식후속/코드기억후속·원래source토큰/직렬화x를각각집계한다.
  QA후보도개별의미/지식분류 보증이아니므로후행실제문구검토가필요하다.
- 후보전체 hash선택·source가족25%목표cap, 첫질문해시 train/val 분리·중복1개만선택.
  기존8질문과새36패널을정확사용자turn해시로제외하며 의미/모든benchmark오염은미검증이다.
  QA50/형식25/명시턴25는 초기설계목표, 각90%이상최소와104%상한+1행여유를보고한다.
  KO/EN각37.5M±1023 **직렬화대화x**와task최소를모두충족해야ready다.
  원천지식량/고유정보량75M이라고주장하지않고, 다른행반복으로부족을채우지않는다.
  각행ChatML≤1024·양mask·역할/경계/출처·20MB샤드를검증하며옛v3는불변이다.
- **Stage4g0W**: 새자료ready일때만 같은부모/micro8×accum16/ckptON/LR의2update wire.
  양언어128행노출·같은SHA·실제x/targets/native/8질문을수집한다. 자료없음/부족은모델시작전8이다.
- **Stage4gW**: 같은새corpus/wire SHA/자기부모의새tag로4실제pass.
  LR1e-4/Muon4e-4·micro8×accum16·ckptON·300M 처리목표는유지한다.
  새B profile에만 epoch마다native/기존8답을추가보고하고평가중RNG를복원해학습순서를오염시키지않는다.
  자동최적모델선택/조기종료는도입하지않는다. 사용자중단은부분이력과저장epoch를보존한다.

### 5. 판정

운영완료·토큰/마스크PASS가실제QA/대화능력PASS는아니다.
A는새108콜+계승72와같은native파일을확인하고자유답은후행판독한다.
B에서language/task부족은유효HOLD8이며새허가없는다운로드/교사생성을자동실행하지않는다.
새B언어/논리/종료/형식/멀티턴효과와native망각을자기부모전후로읽는다.
해당SFT다중seed/보정σ가없어차용σ를쓰지않는다. 형식만틀린맞는내용을전부오답으로세지않는다.

### 6. 비용

A GPU약0.25h/상한0.667h, B전량선별CPU3h추정·새index/샤드8GiB이상저장여유,
wire약0.10h, 교육5.6~12h참고(직전5.615h 실측이나새길이/과제에따라달라짐).
앞코퍼스만드는동안A평가와GPU동시속도비교는하지않으며 **구현준비만병행**한다.
B의분량/실제비용은사용자선별보고서가정본이고 현재데이터생성/학습은NOT_RUN이다.

### 7. 실행

| 단계 | 사용자 SH | 실행선결 |
|---|---|---|
| Stage4eW | `run_P106B_Stage4eW_saved_epoch_retention.sh` | 새smoke0/0/0·정확5endpoint/기존72답SHA |
| Stage4fW | `run_P106B_Stage4fW_capability_corpus.sh` | 핀된기존12공개원천·별도namespace/8GiB |
| Stage4g0W | `run_P106B_Stage4g0W_capability_student_wire.sh` | 새자료75000000x/task최소·양언어/출처SHA |
| Stage4gW | `run_P106B_Stage4gW_capability_chat32_repeat4.sh` | 같은새corpus/성공wire SHA·새tag/부모·저장여유 |

### 8. 한계 / preflight

별도자료/스코프/태그로옛 결과를보존한다. 새B와옛v3의SFT-val셋이달라두loss를직접차감하지않는다.
원형GPT판독패킷실행/보호TinyDataset접근/새다운로드0. source권리·PII·의미·봉인오염은
기술mask와별도이며formal_train_ready=false이다. 코드후속으로직렬화토큰이늘어도새고유지식증가는아니다.
모든행출처/원형질문그룹/정규화방법을보존한다. 새300M을돌리기위해과거질문을복제하지않는다.
source캐시는학습량이아니며실제비패딩x와assistant targets/행노출/업데이트를따로보고한다.
4pass는사용자승인SFT반복예외이지pretrain2배풀규칙을임의변경한것이아니다.
이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

### 9. 실행 이력

2026-10-06 준비중:현재A정확read-only check-only0, Bsource metadata preflight0.
B신규corpus 미생성은예상HOLD8이다. tinyCPU task/계보·held-prolog fixture는새모델성공아니다.
새4SH/실제108생성·native5모델·새75M구축/새300M은당시 사용자E2E_NOT_RUN이었다.

2026-10-07 사용자 실행 회수완료: Stage4eW는 원형model중복키TypeError·새모델답0이고 Stage4fW는29.022176M/45.977824M부족8,
Stage4g0W/gW는 같은 부족 선결을 보고 모델 시작 전8로 중단했다. 정확 원본 JSON 두 파일을
지정 실험 분석 범위에서 읽기 전용 대조했고 결과101 §56~§59에 기록했다. 불필요한 재승인요청은 정정했다.
네 착수 SH는 -done으로 보존하고 같은 출력의 재실행은 권하지 않는다. 새 자료가 필요하면 새 단계/버전을 쓴다.

# P106B — Stage4eWb 저장 epoch 행 귀속 복구

## 1. 왜 / 질문

저장된 원답에 이미 model 키가 있는데 dict(model=현재모델, **원답)를 호출하면 TypeError가 난다.
실제 진단의 nested persist를 추출한 CPU fixture에서 이 결함을 재현했다. 학습 결과나 생성 능력
음성으로 취급할 수 없는 도구 결함이다. 원본 JSON의 직접 실패 사유도 같은 TypeError로 대조됐다.
기존 최종 배너의180행/72계승은 계획량이며 실제 수행량처럼 보였고 상세 오류도 빠졌다.

## 2. 설계 / 예측

Stage4eW와 같은 부모/epoch1~3/완성4pass endpoint, 원형72 SHA계승, 새108 첫답, native5평가를 유지한다.
같은 tokenizer/panel/greedy160/input800/시드/native경로/상한2400초다. 재학습·교사·체크포인트 쓰기0.
행 복사는 원본 mapping을 먼저 복제하고 model을 현재 endpoint로 덮되 prior_source_model을 보존한다.
별도 v2_row_attribution 경로의 사용자 진입점만 추가해 실패 v1과 이전 원문·이력을 수정하지 않는다.
flush 완료 행/답안추출 행/원형계승 행/신규raw행과 close/verify된 manifest 행수를 각각 기록한다.
실패 배너에는 phase/error_type/error/report 위치를 포함한다. 계획량으로 실제 행수를 대체하지 않는다.
복사 경로는 수리될 것으로 예상하지만 실제 checkpoint/GPU/native 경로와 모델 답 품질은 사용자 재실행 전 미검증이다.

## 3. 실행 / 비용 / 판정

사용자: `./run_P106B_Stage4eWb_saved_epoch_row_attribution.sh`.
실제 실행 전에 새 `./run_smoke_check.sh`의 종료/실패팔/exit0오류/계측이 모두0이어야 한다.
기존 파일/SHA선결도 유지한다. GPU약0.25h 추정/40분 상한이며 CPU만의 회귀는 모델 동작을 보증하지 않는다.
완료는 실제 새콜108/flush된 원답180/추출답180/계승72와5모델의같은native평가 모두가 기록될 때다.
종료0은 수집완료이지 정답·형식·언어보존·일반지능 PASS가 아니다. 실패/중단도 부분 산출물을 그대로 보존한다.
출력은 `HF/sft_ready/p106b_epoch_retention_v2_row_attribution`이며 기존 v1 재실행/삭제/덮어쓰기를 금지한다.

## 4. 검증 / 한계 / preflight

기존 자료 준비10시험에 실제 callback·계승 귀속·prefix 실패 행·flush 실패·계획/실제/오류 배너,
재시험 namespace와 HOLD 보존 및 manifest/모델콜 분리7회귀를 더했다.
수리 전 callback 중복키 오류와 보고 누락을 확인했고 수리 후 CPU17시험 및 사용자 Python3.10 help와 SH구문을 통과했다.
기존10시험은 epoch 메타데이터를 검사했지만 저장된 model 키가 있는 원답을 실제 persist로 넘기지 않았다.
일반 call-kwargs 검사는 `**kwargs`의 동적 key를 추적하지 않아 이 중복을 잡지 못한다. 실제 callback 회귀가 이 공백을 메운다.
실물 새 답/native5는 NOT_RUN이다. 원본 JSON과 같은 오류를 확인했으며 수리된 callback CPU경로와 새 실물 실행을 구분한다.
새 학습태그·배치·어휘 변경 없음. 같은 endpoint 비교의 기존 조건 서명을 유지하며 원형/계승과 새 답을 분리한다.
이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

# P106B — Stage4hW 원천 재고와 Gemma4 조건부 보충 준비

## 1. 왜 / 질문

과제자료가29.022176M에그쳤다. 미분류17,612,472행을불량자료로가정하거나같은자료로75M을부풀리지않는다.
기존12원천의실제가족/언어/역할/현재정책분류를확인한뒤실제부족량만교사가보충할수있는가?
사용자는원문근거형1우선, 원천부족시새공개원천탐색3, 적절한원천없으면자체생성2를선택했다.
현재29M별도교육C는기각이다. 원75M×4와학생chat32/micro8×accum16/ckptON/LR는유지한다.

## 2. 예측 / 단계

Stage4hW는USER CPU, 핀된12공개원천의정규화reader행과현재분류를전수계수한다.
같은가족/언어의해시순8원형을20MB샤드로보존하고실제역할다회전과코드후속을구분한다.
표본만chat32 token/mask를검사하며그평균을실측전체가용량으로사용하지않는다.
출력 p106b_capability_source_inventory_v1은새75M코퍼스가아니다. 미분류는의미불량이아니다.
불명가족을자동QA로받거나역할구조가없는문자열을사람다회전으로바꾸어세지않는다.
재고와표본의후행판독뒤원문보존/변환정책을확정하고75M에서실제선별량을뺀언어/task별부족분만B로보충한다.
원출처가족25%상한은유지한다. 교사이름/작업종류를가짜별도원출처로분할하지않는다.
학생입력x/지도량과고유질문/개념군/원형source량을각각기록한다. 20MB조각과사고sidecar는보존한다.
자료부족이단순alias인지진짜유효범위부족인지미측정이며전체75M을보장하지않는다.

## 3. Gemma4 교사 검토 / 선결

정확로컬본체6,738,475,840B와MTP465,109,248B의헤더에서gemma4 48층/Q4_0와
gemma4-assistant 4층/Q8_0/MTP4, 3840→1024→3840투영을확인했다. 저장byte는VRAM실측이아니다.
llama-b11396실제lib에대응arch/model-draft/draft-mtp문자열이있고새helper는기존Qwen/Bonsai기본값을고치지않는다.
Google권장temp1/top_p0.95/top_k64와native system `<|think|>`를사용한다. 저자권장과별개로
min_p0/penalty중립·ctx8192/사고1024/총3072·MTPnmax2는첫진단제어조건으로명시한다.
low/xhigh를Gemma지원강도로가정하지않고native thought/final을분리한다. 데이터JSON/학생ChatML은코드가소유한다.
[모델카드](https://huggingface.co/google/gemma-4-12B-it), [MTP원제공자안내](https://huggingface.co/unsloth/gemma-4-12b-it-GGUF/blob/main/MTP/README.md).

Stage6cW는USER CPU 전체GGUF/바이너리SHA와헤더/투영계약을새assets.json에보존한다.
Stage6dW는성공asset·새smoke뒤USER GPU teacher-only off/on→on/off, 4고정질문×4팔=16요청을실행한다.
한번씩만요청해재시도집합차이로처리율을꾸미지않는다. 실제질문/최종답/사고/raw/파싱/메모리/시간을남긴다.
student token계수는4진단질문반복의배선계수이며고유대량생산속도가아니다. 신규학생학습/저장0.
Gemma 한국어우수성·MTP속도/VRAM·실제큰B생산성은NOT_RUN이다. 다른GPU/quant성과를복사하지않는다.

Stage4iW는성공재고와Gemma off-mode의4프로필TAGGED_COMPLETE를선결로한다. MTP가속채택은별도이며Bpilot은off기준이다.
해시로고른실제서로다른원문16개념(KO/EN8씩)에QA4/JSON2/교사작성3턴2개씩을요청한다.
각턴총3구조재시도상한이며잘못된문구/의미재검사/자동오조어목록은사용하지않는다.
원문·원가족·진짜source_id/sha/revision·원개념그룹과교사생성자정보를분리해canonical에기록한다.
원답/교정NOTE/사고는raw에보존하고성공turn별reasoning SHA/행참조를남긴다. 학생에는최종Q/A만포함한다.
실제교사입력token+출력예산을확인하고초과시원문을보존해명시중단한다. 조용한절단/무의미한반복필러금지다.
후보16개와준비x/target/전체wall생산률을측정하되학생학습·75M완성·정식적격은아니다.
실제원문원천의부족벡터와sample 생산률을회수한뒤원가족cap/한영/유형을유지하는대량보충을연결한다.

## 4. 비용 / 실행 / 판정 / 한계

| 단계 | SH | 예상h | 판정·선결 |
|---|---|---:|---|
| Stage4hW | `run_P106B_Stage4hW_source_family_inventory.sh` |0.50 CPU|핀12원천·새출력; 전수행계수/후행표본, 전체가용token미측정|
| Stage6cW | `run_P106B_Stage6cW_gemma12b_asset_contract.sh` |0.02 CPU|정확2GGUF/llama-b11396·새assets; 실제SHA/metadata만|
| Stage6dW | `run_P106B_Stage6dW_gemma12b_role_mtp_pair.sh` |0.50 GPU|성공asset·새smoke0/0/0; 16원답/tech wire·속도/메모리, 정답성후행|
| Stage4iW | `run_P106B_Stage4iW_gemma_grounded_pilot.sh` |0.75 GPU|성공재고·Gemma off-role·새smoke;16원개념/24turn·구조3재시도·20MB/pseudo후보|

B의전체생산량/시간은재고뒤잔여D와실제수락대화token/전체교사초V에서D/V로계산한다.
과거Bonsai숫자나Gemma출력decode tok/s를그대로학생자료생산속도로쓰지않는다.
현재원문Bpayload·유형별초기pilot·namespace/role/MTP제어·CPU회귀를준비했지만새75M자료는생성하지않았다.
재고/역할/pilot의원천별량과비용을회수한뒤추가원천3의필요성·원변환·대량잔여생산/새corpus-wire/새300M을설계한다.
실행은사용자소유다. 현재GPT원장을사용자E2E대기로붙잡지않는다. 의미/PII/권리/봉인오염·광범위지능미검증이다.
이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.


> 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

> 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

# P106B — 2026-10-07 새 회수: epoch 설정 직렬화와 Gemma 시작 라벨 복구

## 1. 현재 실행 이력과 예측 대조

[결과101 §61~§64](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)가 정본이다.
Stage4eWb는 중복키를 넘겼으나 LOAD_EPOCH1에서 파생속성 n_layers를 저장 키로 요구해 도구9였다.
부모 원형36행/native만 기록했고 새답0이다. 따라서 앞의 “실물 NOT_RUN”은 실행 전 역사이며
현재는 부분수집·도구오류로 교정한다. 학습·epoch 품질 음성이나 잘못된 체크포인트의 증거가 아니다.

Stage4hW의40 원천가족/언어 집단·320해시표본과 Stage6cW 전체자산SHA는 완료됐다.
전자는 전체가용token 계측이 아니므로75M 충족 예측은 아직 판정할 수 없다.
Stage6dW 실제16응답은 MTP decode 증가를 보였으나 옛 태그는 off3/8·on1/8, 전체4/16만 완결됐다.
모든 응답이 stop·최대1085 completion으로3072상한 아래라 단순 출력절단으로 해석하지 않는다.
Stage4iW는 off 역할배선 선결8에서 중단했고 교사 신규자료/학생업데이트0이다.

## 2. 질문과 예측

| 질문 | 검증과 반증 |
|---|---|
| 생산자와 같은 TMTConfig 저장형으로 epoch 메타데이터를 검사하면 거짓 거부를 없애는가 | CPU 실제cfg.__dict__ 실패→수리 통과. 실물 다른 geometry/history는 여전히 거부해야 한다 |
| 새 시작 라벨로 질문 생성 기능을 유지하며 Gemma 필드 완결을 회복하는가 | 같은16 요청과4프로필에서 비교. 모델이 필드를 다시 누락하면 구조 음성으로 보존 |
| MTP가 유효 학습자료 공급도 늘리는가 | 새 라벨 off/on의 필드·wire·실제토큰/시간이 필요. 기존decode 증가만으로 채택하지 않는다 |

사용자는 사례 설명 뒤 A를 선택했다. QUESTION:/ANSWER:/NOTE: 시작 라벨만 교사에 요청하고
닫는 태그와 데이터셋 JSON/ChatML은 요청하지 않는다. JSON 객체·코드가 답변 요구사항인 경우는
ANSWER 내용으로 허용한다. 순서/중복/빈 필드/끝나지 않은 코드펜스/length 중단은 기술적으로 거부한다.
의미 오류 문구 목록·전수 정답심사·온라인 의미 재생성은 추가하지 않는다.

## 3. 단계·구현과 사전등록 판정

| 단계 | SH | 출력 | 비용과 판정 |
|---|---|---|---|
| Stage4eWc | `run_P106B_Stage4eWc_saved_epoch_cfg_geometry.sh` | `HF/sft_ready/p106b_epoch_retention_v3_cfg_geometry` | GPU0.25h 추정/40분 상한. 같은5endpoint/108새답·72계승·180행/native5 완료가0; 예외9 |
| Stage6dWb | `run_P106B_Stage6dWb_gemma_start_label_pair.sh` | `HF/sft_ready/p106b_gemma_teacher_v2_labels/role` | GPU0.10h 추정/30분 상한. 같은16 off/on·on/off에서 LABELS_COMPLETE와 학생문맥/지도마스크16/16이면 기술0, 그 외8 |
| Stage4iWb | `run_P106B_Stage4iWb_gemma_grounded_label_pilot.sh` | `HF/sft_ready/p106b_gemma_grounded_pilot_v2_labels` | GPU0.75h 추정/60분 상한. 기존 재고SHA와 새 off8/8 배선 뒤16원개념/KOEN8·24turn/총3구조시도·20MB 샤드. MTP가속 채택은 선결이 아님 |

전체 role가 on 실패로8이어도 off8/8의 모든 필드·wire가 확인되면 MTP-off pilot은 열 수 있다.
검증실패나 출처변경을 자동 통과시키지 않는다. 원형 assets를 재사용하지만 실제 구동 전에
본체·drafter 전체SHA를 다시 대조한다. 새흐름에서만 LABELS_COMPLETE를 쓰며 옛 TAGGED_COMPLETE와
원형 판정을 바꾸지 않는다. wrapper의 OUTPUT/profile/status는 프로세스 내부에서만 선택·복원한다.

## 4. 고정조건·preflight·한계

Gemma 같은파일·llama-b11396·temperature1/top_p0.95/top_k64/min_p0/중립 penalty,
native thinking1024/total3072/ctx8192·nmax2·같은시드·단일slot·cache_prompt=false를 유지한다.
새 독립변수는 Gemma 출력 필드 계약이다. 사전등록16은 재시도 없는 최초답 수집이며 pilot만
기존 최초포함3구조시도 한도를 적용한다. 사고/원답/출처는 보존하고 최종Q/A만 학생으로 전달한다.
세 SH는 stdin·다운로드·정식학습·체크포인트 쓰기가 없고 각 로그/출력의 이미 존재하는 파일을 거부한다.

epoch은 TMTConfig 복원/14층dense·어휘32768/history/실제기하 정합을 유지한다.
새weights·tokenizer·학습태그/LR/배치를 만들지 않는다. 그때까지75M/새300M은 미완이며
본교육 chat32·micro8×accum16·checkpoint-on·현재LR·4epoch/75M 목표는 유지한다.
원천가족명이 QA여도 질문생성/문맥생성일 수 있고 SODA 본문대본은 역할3턴 데이터와 다르다.
현재 표본을 전체 가용량·권리·정답성으로 외삽하거나 부족을 무의미한 반복으로 채우지 않는다.

실제cfg.__dict__ fixture와 잘못된 geometry/history 거부·실제 callback20CPU,
새 라벨/분리채널/코드펜스/원형/선결/namespace21CPU를 포함한 관련71시험을 통과했다.
새 실물은 사용자 E2E_NOT_RUN이다. 새 smoke의 종료/실패팔/exit0오류/계측 모두0이 선결이다.
이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.


# P106B — 2026-10-08 회수과 A의 과제 계약16→원가족64

## 1. 질문·실측과 개선 범위

[결과101 §67~§70](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)가 이번 수치 정본이다.
epoch5시점180답은108새/72계승으로 완료했지만 계약0/26·native악화가 epoch1부터 관측됐다.
Gemma 라벨16/16과 소형 MTP 가속은 관측됐고,원문16pilot도완료했다. 따라서 옛복구3SH를반복하지않는다.
다만 JSON 지시가학생질문에없고,관리지시가불신DATA 안에있으며,3턴은단순반복/원천15 NQ로편중됐다.
사용자에게 다음계획·구현 전 보고하고 A후 실제학습 조건을 별도 설명했다.
A는같은16에서과제계약변수부터수리한뒤64의원가족분산을시험한다. B의수리+다양화동시와 C의전량CPU우선은이번미선택이다.

## 2. 착수전 영향도·권한

| 파일/대상 | 예정 동작과 근거 | 제외 |
|---|---|---|
| task_contract/task_pilot/test 전용3PY·새2SH | 사용자(1)A 수리/새단계·A후학습조건 회신; 관리task/학생지시/문맥전환/표본 분산 | GPT모델·GPU·생성 실행0 |
| 결과/계획/기준표/방법론/COMPASS/TSV | 사용자결과회수·권장큐·프론티어연쇄 | 원본/이전namespace 변경0 |
| 정확 착수3SH/원장/최종인계 | done·원형SHA/100755보존후승인삭제·현재작업마감 | 기존6hold·타WIP·공용검사기/훅 불변 |

호출/데이터 영향은새opt-in 경로뿐이다. 기존Gemma/Bonsai/Qwen payload·parser·assets를바꾸지않는다.
파서/채널·canonical/chat32·source family·20MBwriter는기존정본을재사용하고새schema/output만추가한다.
CPU fixture는실제wrap/mask/샤드·반복3시도·선결/서버미실행·원형불변을검증한다. 정적PASS는새실물아니다.
자료량/품질·속도/상주/정답성과권한을분리하며교사출력tok/s를학생고유자료량으로대체하지않는다.
기술부채는고정16비교와320표본 기반64의좁은선별범위다. 전체원천생산기/새75M병합은그실측후별도현재계약으로연결한다.

## 3. 예측·반증·사전등록 단계

| 질문 | 기대/반증 |
|---|---|
| 관리지시를system에두고학생출력요구를코드가명시하면형식조건결손이해소되는가 | raw에시스템/원문·교사원질문/코드질문을함께남긴다. source지시의승격/학생JSON지시누락이면코드실패 |
| 3턴조건변경·앞질문적용이실제문맥과제가되는가 | 첫질문한문장→JSON으로변경→첫질문에새조건적용. 답의내용정확성은후행판독이며NOTE/허용문구로정답PASS하지않음 |
| 원가족분산64에서기술수락과생산률이유지되는가 | 실제원가족cap8/언어32·고유그룹·x/target/wall/재시도·메모리. 길이초과/가족부족을반복필러로은폐하지않음 |

| 단계 | 실제 SH | 새출력 | 비용/선결/판정 |
|---|---|---|---|
| Stage4iWc | `run_P106B_Stage4iWc_trusted_task_contract16.sh` | `HF/sft_ready/p106b_gemma_task_contract16_v1` | 사용자GPU0.15h추정/60분상한. 기존4iWb report/raw SHA·role SHA 고정. 같은16/24턴·모든그룹기술완결16이면0,그외8 |
| Stage4iWd | `run_P106B_Stage4iWd_family64_production_pilot.sh` | `HF/sft_ready/p106b_gemma_task_family64_v1` | 사용자GPU0.50h추정/60분상한. 새contract16 schema/원report/role/manifest16과실제샤드선결. KOEN32씩·QA16/JSON8/3턴8/원가족<=8·전체64기술완결0 |

기술16/64 기준은가족·표본의내용정답검사나새학습문턱75%를뜻하지않는다.
전량미완이면원형/부분샤드를남기고후속학생은열리지않는다. post-hoc미달을PASS로바꾸지않는다.
원래가족명만으로QA/명시멀티턴/주제다양성을인정하지않고teacher재가공의역할/과제기원을표시한다.

## 4. 고정조건·preflight

Gemma/assistant/llama-b11396·MTPoff·단일slot·card sampler1/.95/64/min_p0/중립penalty·native1024/3072/8192,
기존16의seed공식/원문·역할/출처·소스개념split을유지한다. MTP가속원인시험과이과제수리를섞지않는다.
원가족64는표본변경축이므로16수리인과와분리한다. current_builder_eligible=false는선별정책외란뜻이며불량이아니다.
실제원문tokenize+출력여유를사용하고초과시조용한절단을하지않는다. 최초포함총3시도는필드/JSON구조에만사용한다.
전체틀린문구목록·온라인정답심사·의미재시도·행별사람승인은추가하지않는다.
QUESTION/ANSWER/NOTE는교사내용,JSON메타·ChatML·학생지시/상태계약은코드가소유한다.
새check-only는모델을실행하지않으며stdin0·자동다운로드0·원형덮어쓰기0이다. 학습태그/step0 registry 대상이없는교사-only이며
새SH/단계/로그출력충돌·배치불변을검사한다. 새GPU/학생공존/장기생산/자료정답성은E2E_NOT_RUN이다.

## 5. A후 실제300M 학습 가능 조건

16/64는생산계약pilot이지75M확보다. 현재자료29.022176M/부족45.977824M은그대로기록한다.
고유train75M·한영각37.5M·별도val·원가족25%·QA/JSON/멀티턴50/25/25(각목표90%이상)·진짜개념split,
SHA/chat32/assistant마스크/1024문맥검사를충족해야한다. 원문C의실제가용량을먼저반영하고언어/task별잔여만B로생산한다.
같은최종자료2업데이트/256행노출·16+16val·유한loss/gradient·OOM없음 wire와새smoke를통과하면
원chat32부모에서micro8×accum16/ckptON·현재LR1e-4/Muon4e-4·4epoch 약300M을연다.
새자료고유량을반복으로부풀리지않는다. 실험PSEUDO와정식TRAIN_READY·정답성/지능향상은별도이며전수gold승인을추가하지않는다.
이번GPT는코드/CPU만수행한다. 실제16/64·75M생산/새wire·새300M은사용자후속실험이다.
이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.


# P106B — 2026-10-08 추가 회신: Gemma 부족량 생산→실제300M 연결

## 1. 승인 해석 정정과 현재 양

사용자는 조건1 뒤 조건2의부족분Gemma생성이이미정해졌음을상기했다. 앞의pilot까지만준비라는범위설명은정정한다.
부족분생성은새승인을요구하지않는다. GPT는부족량생산/재개/최종병합·같은자료wire·새300M·후속72답까지선결코드를준비한다.
현재C report SHA774E2CBA…의trainKO13.509612M/EN15.512564M,부족KO23.990388M/EN21.987436M이다.
val각1.973684M 목표에서추가2.422282M이필요하며train75M에합산하지않는다. 원형29.022176M은복사/덮어쓰기하지않는다.

## 2. 구현·반증·사전등록

새controller는기존C 선택샤드를검증하고원래12핀공개원천을스트리밍해source concept/언어당한변형만추가한다.
행마다한국어/영어·QA/JSON/3턴·별도val·원가족25%한도와실제x/targets를추적한다.
NQ처럼cap남은4토큰의원가족에추가질의를반복하지않는다. 원문개념해시가split을소유하고생성질문은split을바꾸지않는다.
코드/입력/pilot SHA·기존C/teacher canonical카운터·샤드SHA·커서를재개때검산한다.
최초포함3구조시도, 실패/중단중원문은소비처리해재개마다새예산을무한부여하지않는다. 의미재심사/오조어목록은없다.
매호출새batch·20MBraw/후보·사고/원문/원질문/코드질문/NOTE를보존하고채택량·wall·남은ETA를공개한다.
강제kill로report가없는batch는자동덮어쓰지않고검토요청으로멈춘다. 출처소진이면부족량을보존하고3추가확보→2자체생성을논의한다.
문장중복/원개념split/cap/마스크/단위가어긋나면기술적으로거부하나이를내용정답판정으로부르지않는다.

| 단계 | 실제 SH | 비용/선결·예측·판정 |
|---|---|---|
| Stage4jW | `run_P106B_Stage4jW_gemma_deficit_production.sh` | 사용자GPU/최대6h·성공16/64/같은Gemma-controls/핀12원천. 처음생산;전체75M/val완료0,부분PAUSED8 |
| Stage4jWb | `run_P106B_Stage4jWb_gemma_deficit_resume.sh` | 사용자GPU/최대6h·동일입력/코드+확정샤드/카운터/커서. 명시resume/로그시각분리·새batch |
| Stage4kW | `run_P106B_Stage4kW_gemma_completed_corpus.sh` | 사용자CPU0.50h추정·75M/val/task/cap이실제충족돼야새v2병합/마스크·정확질문index. 부족시작성/학생0 |
| Stage4k0W | `run_P106B_Stage4k0W_gemma_student_wire.sh` | 사용자GPU0.50h추정·완료같은코퍼스/원부모,2업데이트/256노출·16+16val·유한손실/모델 |
| Stage4lW | `run_P106B_Stage4lW_gemma_chat32_repeat4.sh` | 사용자GPU6~12h추정·같은성공wire,원배치/현재LR/4epoch·약300M;실제길이/업데이트량에따라변화 |
| Stage4mW | `run_P106B_Stage4mW_gemma_capability_multiaxis.sh` | 사용자GPU0.50h/30분상한·같은full4pass child/부모/자료SHA·24단일+4실제3턴=36각/합72첫답;수집0은품질PASS아님 |

본학습태그 `p106b_s4_gemma_capability300m_chat32_s1337`는예약/아직사용0,출력은새v2이며옛교육/체크포인트를바꾸지않는다.
helper는기존learner/다축평가를프로세스내에서만새입력/출력/TAG로선택·복원한다. 평가receipt는선택된실제출력을표시하도록수리했다.
기존배치micro8×accum16/ckptON·LR1e-4/Muon4e-4·원chat32부모는불변이다. 교사는학생학습전에종료한다.
새teacher-native정답성/원가족권리전수·새75M완성/모델효과는GPT E2E_NOT_RUN이다.

## 3. 언제 완료하는가와 비용 한계

조건1은사용자새smoke뒤16→64의실제완결이오는시점이다. 두실험합계20~45분추정이며단계별상한60분을둔다.
조건2의생성코드는이번마감에서준비완료하고,성공16/64뒤바로첫jW를실행할수있다. 사용자실행을다시구현대기로넘기지않는다.
종전결함전805x/316.860678s를그대로사용하면45.977824M train에약209.46일이지만계산외삽일뿐완성예약일이아니다.
새64/첫실제생산의유효x/전체wall·재시도·분포에서다시산정한다. decode149tok/s로고유학생자료공급을대체하지않는다.
MTPoff/기존Gemma원모델/카드sampler/native상한은원인분리계약그대로다. 새가속/출처를시간때문에몰래채택하지않는다.
자료가75M미달이면29M교육으로목표를축소하거나재생성반복으로고유량을부풀리지않는다.
이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.


# P106B — 2026-10-08 답 본문 계약 분기와 생산 연결 복구

## 1. 왜

[결과101 §74~§77](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)의 실제31응답은 모두 라벨 완결/stop이나14/16만 후보가 됐다.
JSON 펜스3회와 일반 영어답3회가 미완2그룹의 직접 원인이다. 이후64/생산/재개/병합은 선결8이고 학생9는 코퍼스 미생성 분류 오류로 모델 전에 끝났다.
VRAM/OOM이나 교육 실행의 실패가 아니다. 사용자가 1안(단순 포장·복잡 구조 분리)을 승인했으므로 기존 outer 래퍼를 새로 만드는 것이 아니라 본문 계약만 수리한다.

## 2. 질문·분류 근거·권한

| 질문 | 코드의 근거/처리 |
|---|---|
| 단순/복잡을 어떻게 구분하는가 | 생성기가 직접 만든 출력 계약으로만 분기. 현재 json/3턴 마지막의 scalar answer는 단순; 명시한 배열/중첩 schema는 복잡; 원천/교사 자기분류는 권한이 아님 |
| 복잡한 JSON도 가능한가 | 교사 JSON 전체와 declared bounded schema를 검사하며 answer 문자열로 숨기지 않는다. 미등록/미지원 구조는 자동 추정하지 않는다 |
| 기존 포장은 없어졌는가 | 라벨 파서→canonical JSONL→기존 ChatML/assistant 마스크를 그대로 재사용한다. 답 내용 렌더링은 그 앞의 별도 단계 |
| 내용 오류를 형식 검사로 고칠 것인가 | 아니다. 원문/원답/NOTE/사고·렌더링을 보존하고 후행 자료 검증으로 넘긴다. 온라인 의미 재시도/문구 블랙리스트는 없음 |

수리 파일은 output_contract/task_contract_v2/recovery 어댑터·기존 두 생산 호출부·deficit 선결 분류·CPU 회귀/새SH다.
사용자(1)A와 이번 1안 승인에 따른 변경이며 공용 훅/검사기·원본/HF/cache/weights·다른 WIP·GPU 직접 실행은 제외한다.
기존 V1 모듈/출력은 보존하고 process-local opt-in 바인딩은 정상/예외 때 모두 복원한다.
학습 레시피·출처쿼터/원개념split·마스크/샤드 정본은 기존 엔진이 계속 소유한다. 후속 원천 계약 확장은 별도 명시 어댑터가 필요하다.

## 3. 예측·사전 반증

단순 ANSWER를 코드가 렌더링하면 펜스/일반문장 때문에 막힌 후보는 회복될 것으로 예상한다.
반대로 교사가 바뀐 프롬프트에서도 라벨/문맥을 틀리거나 길이1024를 넘길 수 있다. CPU 통과만으로 새16/64 성공을 보장하지 않는다.
복잡 구조는 교사 부담이 남아 총3회 모두 실패할 수 있다. 형식이 맞아도 원문 관계 변형·오답은 남을 수 있다.
UNKNOWN을 단순 구조로 추정하거나 배열을 answer 문자열로 바꾸면 코드 실패다. 내용 정답성은 이 게이트의 통과 항목이 아니다.

## 4. 단계 설계 — CPU→소형 교사→부족량→학생

| 단계 | 사용자 실행 SH | 모드 | 비용 추정/한도 | 다음 선결·사전 판정 |
|---|---|---|---:|---|
| Stage4iWe_output_dispatch_cpu | `run_P106B_Stage4iWe_output_dispatch_cpu.sh` | cpu | 0.02h | CPU 회귀·모델 없음 |
| Stage4iWf_answer_render_contract16 | `run_P106B_Stage4iWf_answer_render_contract16.sh` | contract16 | 0.20h | 같은 16그룹·새 계약 기술 완결 16/16 |
| Stage4iWg_complex_output_contract4 | `run_P106B_Stage4iWg_complex_output_contract4.sh` | structure4 | 0.10h | 한영 배열/중첩 4그룹 구조 완결 4/4 |
| Stage4iWh_family64_output_dispatch | `run_P106B_Stage4iWh_family64_output_dispatch.sh` | family64 | 0.75h | 새 16/4 선결·원가족 분산 64/64 |
| Stage4jWc_gemma_output_deficit_production | `run_P106B_Stage4jWc_gemma_output_deficit_production.sh` | produce | 6.00h | 성공 16/4/64·별도 train/val 부족량 생성·최대 6h |
| Stage4jWd_gemma_output_deficit_resume | `run_P106B_Stage4jWd_gemma_output_deficit_resume.sh` | resume | 6.00h | 성공 16/4/64·별도 train/val 부족량 생성·최대 6h |
| Stage4kWb_gemma_output_completed_corpus | `run_P106B_Stage4kWb_gemma_output_completed_corpus.sh` | finalize | 0.50h | 실제 75M·별도 val·한영/task/원가족 쿼터 충족 |
| Stage4k0Wb_gemma_output_student_wire | `run_P106B_Stage4k0Wb_gemma_output_student_wire.sh` | wire | 0.50h | 완료 동일 자료·교사 종료·학생 2업데이트 |
| Stage4lWb_gemma_output_chat32_repeat4 | `run_P106B_Stage4lWb_gemma_output_chat32_repeat4.sh` | train | 12.00h | 동일 성공 wire·원부모/배치/LR·실제 4epoch |
| Stage4mWb_gemma_output_multiaxis | `run_P106B_Stage4mWb_gemma_output_multiaxis.sh` | eval | 0.50h | 완료 같은 4epoch 학생/부모·실제 72첫답 |

새16은 기존 원문16/seed/교사/MTPoff·카드sampler/native1024/총3072/ctx8192를 유지한다.
별도4는 코드작성 한영 배열2/중첩2다. 새16/4가 완결돼야64·생산을 권장한다. 같은 질문을 새seed로 무한 재생성하지 않는다.
새 출력 task pilots v2/deficit v2/최종 corpus·wire·student v3는 옛 v1/v2 원형을 변경하지 않는다.
production/resume 입력SHA에는 출력계약·어댑터·pilot 엔진까지 포함되며 변경 뒤 옛batch에 이어쓰지 않는다.
동일 schema/raw/후보SHA·완결수16/4/64를 검증한다. 새 회귀→선결→본실험→최종 receipt가0/8/9와 본실험 NOT_RUN을 함께 표시한다.

## 5. 판정 기준

단순 렌더링은 CODE_RENDERED_ENVELOPE, 복잡은 DECLARED_STRUCTURE_PASS, 미상은 NOT_ASSESSED다. 세 값은 정답/품질 등급이 아니다.
JSON schema는 type/properties/required/additionalProperties/items/minItems/maxItems/enum 부분집합이며 미지원 키/중복키/NaN/미완 펜스는 거부한다.
최초 포함 총3시도는 라벨과 구조가 공유한다. 구조 오류 피드백 외 사실 심사·오조어 목록·사람 전수 승인은 추가하지 않는다.
생산은 실제 train75M·언어당37.5M·별도val·원가족cap25%·QA/JSON/명시3턴50/25/25의 최소90% 목표를 충족해야 병합한다.
미완이면 부족벡터/PAUSED8을 남기고 학생을 열지 않는다. 원천 소진이면 3 추가공개원천→2 자체생성 후보를 논의하며 반복필러로 채우지 않는다.

## 6. 비용·자원·preflight

현재 관측은2.291675 유효 student x/s·64.658395 completion tok/s다. 두 분모를 바꿔 쓰지 않는다.
6h 생산/재개는 실행 상한이지 자료 완성 보장이나 반복 예약 횟수가 아니다. 첫 새64/실제batch의 분포·재시도·whole-wall로 남은 생성시간을 다시 산정한다.
teacher-only peak8225MiB/minfree7837와 과거 학생 reserved4330의 단순합산은 동시 peak/OOM 보증이 아니다. 이번 학생 학습에서는 교사를 먼저 종료한다.

| 항목 | 판정·근거 |
|---|---|
| 토큰 환산 | 75M 실제 비패딩 대화 x×4epoch≈300M; seq1024 패딩/사고/val은 별도. 기존 fixed-crop2289×8×16×1024는300.024M이지만 이SFT의 update 수 산식이 아님 |
| 데이터 반복 | 사용자가 승인한 고유75M의 고정4epoch SFT이며 복원추출600M-pool 규칙과 다른 실험계약이다. 같은 자료 반복을 새고유75M으로 부풀리지 않음 |
| 태그/덮어쓰기 | 새 outputv2_s1337 목표 log/ckpt 존재0의 정확metadata만 조회. 광범위 registry/원본 runs 스캔0 |
| 중복 | 옛14/16 음성은 보존하고 같은 옛출력으로 재실행하지 않음. 독립변수는 명시 본문계약/코드렌더링·구조피드백이며 새64는 원가족 표본 축 |
| 학습 조건 | 원 chat32 부모·micro8×accum16·checkpoint-on·LR1e-4/Muon4e-4·4epoch 불변. teacher/student 순차 |
| 비교/노이즈 | 형식 수리 효과/내용정답/학생효과는 분리. 결과101 조건서명 PARTIAL_CONFOUNDED; 해당 과제/품질의 재현 노이즈 미측정 |
| 실행 경계 | GPT는 CPU/정적/check-only만 수행. 사용자 새smoke 통과 뒤 조건부 GPU |

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 7. 실행·기존 큐 계승

위10개 SH가 실제 파일이다. stdin/pause/자동download는 없고 동일일 기존 로그를 덮어쓰지 않는다. resume만 시각별 새run_name/확정batch를 사용한다.
옛 착수6SH는 done 원형/SHA/100755·명령을 보존한 뒤 정확 승인된 삭제 대상으로 처리한다.
미실행 옛 Stage4lW/4mW는 원래 v2 경로에만 연결된 보존본이어서 현재 권장 실행에서 제외한다. 자동으로 새 v3로 돌려 쓰지 않는다.
새 lWb/mWb는 새 자료 성공 이후 원 배치의 실제4epoch/후속72답으로 바로 연결되며 구현 대기를 추가하지 않는다.
기존6hold·다른 데이터 세션 WIP는 불변이다.

## 8. 한계

내용 정확성·한국어 우수·원천별 권리 전수·새75M완성·300M효과·교사/학생 동시상주는 미검증이다.
array/nested4의 구조 통과도 의미 정답 검증이 아니다. 프롬프트가 질문을 새로 만들 때 관계 변형이 생길 수 있으므로 원문/원답을 보존한다.
명시 계약이 없는 복잡 과제는 강제 wrapping하지 않는다. 전량 JSON Schema 지원이나 기존 원천의 모든 출력형식 분류를 구현했다고 주장하지 않는다.
새 SH/과학코드 정적 PASS는 사용자 새 smoke/GPU PASS가 아니다.

## 9. 실행 이력·예측 대조

- 2026-10-08 원형4iWc: 라벨31/31였지만 그룹7/13 본문 JSON으로14/16 음성8. 라벨 프롬프트 수리만으로 전체 과제가 완결된다는 예측은 반증됐다.
- 4iWd/4jW/4jWb/4kW: 각 선결8·본실험 미실행. 4k0W는 미생성 보고서 분류9였으며 이번 CPU에서 HOLD8로 수리했다. OOM이 아니다.
- 핵심 CPU56 및 라벨/receipt를 포함한89시험 PASS. 새16/4 check-only0·모델0. 새16/4/64·부족량·학생은 사용자 E2E_NOT_RUN.


# P106B — 2026-10-08 계약15/16 회수와 학생literal/관리지시 분리 수리

## 1. 왜

[결과101 §79~§82](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에서 실제계약26요청/15후보 음성8·복잡4/4 성공0과뒤7 선결미실행8을분리했다.
학생0은SFT불가능의증거가아니다. 남은EN14의2턴은학생JSON변경지시를SYSTEM관리문장에넣고code-known틀을UNKNOWN으로분류한연결문제다.
본수리는그혼선을새opt-in V3에서해소한다. 사용자에게수리범위·변경전CPU실패와후69/76시험을보고했다.

## 2. 질문·영향도·권한

| 경로/영향 | 동작/권한 근거 | NOT_RUN/제외 |
|---|---|---|
| task_contract_v3/literal_recovery·CPU회귀4PY | 사용자(1)A 관련구현수리·별도재시험·management/learner literal 경계 | 기존v2·공용검사기·모델구조/원본변경0 |
| 새8SH·TSV/계획 | 같은(1)A의재실행별도단계·구현후사용자진입점 | GPT GPU/실험/스모크대리실행0 |
| 결과/색인/기준표/방법론/COMPASS | log-to-result 연쇄·actual/NOT_RUN 일치 | 보호TinyDataset/다른세션원장0 |
| 정확9done/raw10·새원장/인계 | (1)B 원본/원형보존·(4) 적격승인삭제·마감 | 다른삭제/push/환경훅0 |

코드영향은기존transport/생산 engine의process-local 재사용이다. 새scope는정상/예외때원래모듈bindings를복원한다.
영속형식/계보는새namespace이고원형v2/raw/정본을수정하지않는다. parse/wrap/mask/source/sampler 정본을복제하지않고원래helper를호출한다.
시험은모의teacher·합성tokenizer/실제canonical/마스크·옵션전달·SHA/선결·namespace 복원을검증한다. 새교사실물은별도다.
기술부채는엄격16/64가다른한행실패에도생산을막을수있다는점이며사용자에게별도3안으로기준선택을요청했다.
데이터/체크포인트·GPU권한·메모리/속도/품질/정적/실물·풀/tokenizer/초기화/평가구분과문서연쇄를모두대조한다.

## 3. 예측·반증

학생literal을DATA의producer_control에두고SYSTEM은그문장을transport 지시로따르지말라고정의하면whole-header JSON/앞말실패가줄어들것으로예상한다.
코드가정한2턴JSON 틀도렌더링하므로teacher가그포장을생성할필요가없다. 그래도라벨누락·출력절단·원문관계변형은남을수있다.
파서를느슨하게전체JSON안의문구를추출하거나불량원답을강제수락하지않는다. 실제실패가다른그룹으로옮겨갈가능성도기록한다.
내용정답/한국어우수·new75M 완성·학생지능을이형식수리예측으로대체하지않는다.

## 4. 단계 설계

| 새 단계 | 실제 사용자 SH | 모드 | 예상/상한 | 조건·현재 정책 |
|---|---|---|---:|---|
| Stage4iWi | `run_P106B_Stage4iWi_literal_learner_contract16.sh` | contract16 | 0.20h | 새 literal16·총3시도·기존16/16 |
| Stage4iWj | `run_P106B_Stage4iWj_literal_family64.sh` | family64 | 0.75h | 성공새16+정확핀기존4·기존64/64 |
| Stage4jWe | `run_P106B_Stage4jWe_literal_deficit_production.sh` | produce | 6.00h | 성공새16/64·quota/원천SHA·6h상한 |
| Stage4jWf | `run_P106B_Stage4jWf_literal_deficit_resume.sh` | resume | 6.00h | 성공새16/64·quota/원천SHA·6h상한 |
| Stage4kWc | `run_P106B_Stage4kWc_literal_completed_corpus.sh` | finalize | 0.50h | 완료75M/val/lang-task-source |
| Stage4k0Wc | `run_P106B_Stage4k0Wc_literal_student_wire.sh` | wire | 0.50h | 완료동일자료/원부모·2update |
| Stage4lWc | `run_P106B_Stage4lWc_literal_chat32_repeat4.sh` | train | 12.00h | 성공동일wire·원레시피4epoch |
| Stage4mWc | `run_P106B_Stage4mWc_literal_multiaxis.sh` | eval | 0.50h | 새fullchild/parent/data·72실답 |

새16은같은원천16·seed공식/교사·MTPoff/카드sampler1/.95/64/min_p0·native1024/총3072/ctx8192를유지한다.
이전complex4는정확B9E45E…report/raw/candidate SHA와공유코드/프롬프트불변을검증해compatibility 근거로만계승한다.
V3의명시complex payload는V2와바이트동일함을CPU에서대조했다. 새complex generation을PASS로표시하지않고반복모델실행을기본요청하지않는다.
후속16/64·부족량제어는기존engine의원개념split/한영/task/source cap/정확x/target을유지한다.
매6h의생산·명시resume은코드/입력/확정샤드/카운터/커서를검산하며완성전학생을올리지않는다.

## 5. 판정·선택전 경계

현재새CLI는STRICT16_STRICT64_UNCHANGED를명시한다. gate16/16·64/64는사용자선택전변경하지않는다.
사용자에게새단계의처리경로/불량행차단technical 게이트·기존전량완결유지·작은학생배선추가의3안을제시했다.
계속8을모두‘학생실험실패’로부르지않고단계receipt의PREFLIGHT/EXECUTE/NOT_RUN·실제량을함께읽는다.
파서/3공유시도/끝맺음/상한·source/마스크는형식안전기준이다. 문구블랙리스트·온라인전수의미심사·행별gold승인은추가하지않는다.

## 6. 비용·preflight

새GPU앞단은teacher16 약7~12분추정/최대60분,64는약20~60분추정/최대60분이다. 준비/해시/seed별변동은실측뒤재계산한다.
첫생산/재개는각6h상한으로자료완료예측이아니다.75M/val 완료와wire성공뒤학생4epoch는기존조건에서6~12h예상이고새자료때달라진다.
새태그 `p106b_s4_gemma_capability300m_chat32_literalv3_s1337`·fresh V3 pilots/deficit·V4 corpus/wire/student/eval은옛출력을덮지않는다.
원chat32부모·micro8/accum16/checkpointON/LR1e-4/Muon4e-4/4epoch≈300M 실제x를유지한다. 고정crop2289step 계산으로이SFT update 수를꾸미지않는다.
교사-only 현재966x/353.958754초와history학생300M/19952.246초는동일작업/동시자원속도가아니므로직접인과비교하지않는다.
새75M 고유train/언어각37.5M·별도val·원가족25%·과제50/25/25는생산/병합조건이다. 반복/교정변형을새original concept으로세지않는다.
메모리7772−4330≈3442MiB는다른팔의조건부식이고Gemma 공존PASS가아니다. 현재8SH는기존순차경로이며async 학습으로속여표시하지않는다.
이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 7. 실행·기록

위8SH만새strict 순차재시험이다. stdin/자동download·기존log덮어쓰기0이고resume 로그시각은note/child가같은값을공유한다.
착수9는-done·명령/SHA/100755·c9329de 원형으로먼저보존한다. 승인범위9만정리하고미실행CPU재현/옛2대안/hold6은보존한다.
현재새16 check-only0/pinnedcomplex4 readonly검산은모델0인선결확인이고CPU76은합성계약증거다.
새16/64/대량/새75M/wire/4epoch/72답은사용자 E2E_NOT_RUN이다.

## 8. 한계·후보 A/B/C 교육

학생literal/관리지시혼재수리가내용정답을보장하지않는다. 실제소형에도source 질문/답불일치와어색한번역이있었고후행검토대상이다.
current whole75M 후학생이라는순차구조에는producer-consumer 큐가없다. async GPU동시상주/상주시간분할/GPU교사+CPU학생은분석/질문이며선택전미구현이다.
학생실패A/B/C 추가교육은dev와독립val/final을구분하고오답assistant를문맥만으로마스킹해야한다. 기존encoder는모든assistant를target으로삼는CPU예제를확인했다.
B의의미동등변형이literal1/JSON필드같은출력계약을바꾸지않게하고,변형/교정수·언어/source family/노출/예산/원형계보를보존한다.
추가학습에사용한validation 사례를계속독립validation이라부르지않고teacher 교정을자유QA의확정gold로승격하지않는다.
본선택질문은GPU직접사용·새적응루프자동구현허가를뜻하지않는다. 새학습방법은사용자확정뒤별도단계/원천계약으로준비한다.

## 9. 실행 이력·예측 대조

원형v2 계약16에서기존format-only 수리로14→15그룹은회복됐지만전량완결예측은반증됐다. 복잡4는4/4 실제성공이었다.
새v3는관리/System boundary와code-owned JSON change-turn의수리다. 수리전CPU UNKNOWN/학생literal inSYSTEM assertion1과수리후69/76시험을분리했다.
원형decode/readiness/학생실패와현재STATIC_ONLY·앞으로의새user E2E를혼동하지않는다. 정확수치/원본은결과101 §79~§82가소유한다.

### Stage4iWe CPU 본체 — 완료(직접56회귀), SH 래퍼는 NOT_RUN

사용자의추가정리요청으로원래CPU단계의3 unittest모듈명령을대조했다. 기존78중동일56을포함했으며이번직접명령도56/OK/종료0이었다.
일부output-contract 모듈23만을전체본체수로읽지않는다. 사용자SH/runlog 원본은없고그래퍼실행을통과로승격하지않는다.
CPU실험본체완료를근거로정확재현전용SH를 `run_P106B_Stage4iWe_output_dispatch_cpu-done.sh`로개명/원형보존하고큐중복을제외했다.
[결과101 §85](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)의명령/SHA/32adb7c 복구점을보존했다. 삭제가능판정만회신하고현재파일은삭제하지않는다.
이는형식분기/구조재시도/마스크/원형계보의CPU회귀예측을충족한것이며새teacher/학생/75M/300M·공존은계속NOT_RUN이다. 기존실물8단계/배치/LR/엄격gate를바꾸지않는다.
# P106B — 2026-10-09 계측 시간초과 복구·확정자료 명시 재개

## 1. 왜

[결과101 §86~§87](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에서 기존 학생literal 수리의 새16/16·64/64를 회수했다.
생산/재개는 nvidia-smi5초 조회 실패를 latch한 오류9로 중단됐으나 확정1,490행/신규train92,770x는 보존됐다.
완성75M·학생은 선결8로 미실행이며 OOM의 근거가 아니다. 모니터 인과는 Windows 사건증거 전 미확정이다.

## 2. 질문·영향도·권한

| 파일·경로 | 예정/실제 동작 | 권한 근거 | NOT_RUN·제외 |
|---|---|---|---|
| 새 telemetry helper/entry/test3PY | 기존 reader만 process-local 제한재시도·공백/새runtime증거·CPU회귀 | 사용자(1)A 수리·D 재개와 A 선택 | 기존 생성14코드·공용검사기·GPU reset/모델재시작 변경0 |
| 새3SH·TSV | 별도 jWg/kWd/k0Wd와 선결/원레시피·무인 실행 | 같은 A/D 재실험/명시재개 지시 | Codex GPU/모델/SH/스모크 직접실행0 |
| 정확5JSON·생성 batch2 조각 | readonly SHA·행수·root중복·커서 검산 | 사용자 산출물 읽기전용 허가 | 원본/HF/cache/weights writes0·보호TinyDataset0 |
| 결과·계획·목록·baseline·방법론·COMPASS·새원장/인계/감사 | 실제 관측/NOT_RUN 일치·C2/C3/closure | 사용자 결과반영/새원장/인계·스킬 연쇄 | 제안서 작성0·공유09/환경/다른WIP 변경0 |
| done7·정확로그7/로컬커밋 | 명령/Git/SHA 복구점을 보존한 적격정리 | 사용자(1)B와(3) | 다른삭제/push/PR0 |

코드 영향은 sampler 한 호출부의 opt-in wrapping이다. 기존 Session.check/저여유/서버종료·생산/재개/원천/마스크/계보 로직은 그대로 사용한다.
데이터는 확정입력·원형batch를 수정하지 않고 다음batch만 추가하며 runtime변경은 별도증거로 분리한다.
시험은 일시/지속 timeout·다른오류·저여유·공백/이벤트상한·scope/receipt 복원을 CPU에서 검증한다.
기술부채는 실제 GPU reset을 복구하지 못하는 점과 생산성 병목이 남는 점이다.
GPU권한/소유권·학습풀/tokenizer/초기화·메모리/속도/품질의 증거등급·문서연쇄를 각각 분리했다.

## 3. 예측·반증

한 번의 조회만 지연되고 다음 조회가 정상이라면 생산중단을 피할 수 있을 것으로 예상한다.
드라이버/서버가 실제로 고장나거나 조회3회 연속 실패하면 새경로도 계속 중단될 것으로 예상한다.
공백 발생시 peak/OOM 안전은 증명할 수 없으며, 조회 복구가 정답성·공급속도·75M완성을 해결한다는 예측은 하지 않는다.
시스템 절전/driver reset 대응은 설명·사용자 환경 확인 단계이고 자동변경하지 않는다.

## 4. 단계 설계 — 기존 성공 gate 계승 뒤 이어가기

| 단계 | 사용자 런처 | 모드 | 비용/선결 | 현재 상태 |
|---|---|---|---|---|
| Stage4iWi | 기존 실행원형 | contract16 | 실제16/16·6.4분 runlog | 회수 완료0·done/Git 보존 |
| Stage4iWj | 기존 실행원형 | family64 | 실제64/64·26.3분 runlog | 회수 완료0·done/Git 보존 |
| Stage4jWe / Stage4jWf | 기존 실행원형 | produce/resume | 원형2 batch·조회오류9 | 회수 완료·확정자료 보존, 생산 미완 |
| Stage4kWc / Stage4k0Wc | 기존 실행원형 | finalize/wire | 75M 미완·학생0 | 선결보류 회수8·학습실패 아님 |
| Stage4jWg | run_P106B_Stage4jWg_telemetry_deficit_resume.sh | resume | 앞gate 계승·기존inputs/샤드/커서검산·최대6h | 준비·사용자 모델 NOT_RUN |
| Stage4kWd | run_P106B_Stage4kWd_resumed_completed_corpus.sh | finalize | 실제75M·별도val·한영/task/source cap 충족·CPU0.5h 추정 | 조건부·NOT_RUN |
| Stage4k0Wd | run_P106B_Stage4k0Wd_resumed_student_wire.sh | wire | 성공완성자료·교사내림·원부모/배치2업데이트·0.5h 추정 | 조건부·NOT_RUN |
| Stage4lWc | run_P106B_Stage4lWc_literal_chat32_repeat4.sh | train | 같은wire·4epoch·micro8×accum16/ckpt-on/LR불변·12h 추정 | 기존 파일 계승·NOT_RUN |
| Stage4mWc | run_P106B_Stage4mWc_literal_multiaxis.sh | eval | 같은full child·실제72 첫답/일반언어손실·0.5h 추정 | 기존 파일 계승·NOT_RUN |

재개 SH는 매번 다른 시각의 runlog명을 사용하고 입력 대기·자동 무한반복·download가 없다.
완성 병합/학생 SH는 새 단계명으로 구 로그와 분리하되 아직 생성하지 않은 같은 V4 출력만 사용한다.
출력 존재/불일치 검사는 기존코드가 GPU 전에 수행한다. old -done을 떼어 재활성화하지 않는다.

## 5. 판정 기준

- 재개 가능: 원형 generation SHA/inputs/확정샤드·카운터 일치, 중단 batch의 마지막커서 다음부터, 실패 원문에 새3시도 부여 없음.
- 계측 회복: 최초 포함3조회·각5초·사이0.2초에서 timeout만 회복. 다른 오류/교사 종료/기존512MiB 선결은 우회하지 않는다.
- 자료 완료: token_target_ready=true·고유train75M/한영37.5M씩·별도val·50/25/25 과제·25% 원출처 cap.
- 학습: 앞 자료+wire 통과 후 기존배치/LR/4epoch. 형식/시간/자료량과 정답성·학생지능은 별도.
- 공백: GAPPED·continuous_peak_verified=false·oom_safety=NOT_ESTABLISHED. 구 오류의 VRAM 숫자 소급 복구 금지.

## 6. 비용·preflight

새 계측코드는 기존 read_memory의5초×최대3회+재시도대기0.4초다. 일시 query마다 최대약15.4초 지연할 수 있다.
원형 입력코드14 SHA가 일치하므로 재개 fingerprint를 느슨하게 하지 않는다. 새runtimeSHA는 별도receipt에 기록한다.
생산 본체의 원천/교사/토크나이저·한영/과제/계보/상한/메모리 보수성을 그대로 유지하고 학생학습토큰은0이다.
새학생태그 없이 기존 예약 p106b_s4_gemma_capability300m_chat32_literalv3_s1337을 유지한다.
정확 그태그의 log/checkpoint와 V4 완료report는 metadata만 확인하고 broad runs 조회/기존checkpoint실행은 하지 않는다.
생산6h는 완료기한이 아니다. 현재 train 부족분의 조건부 외삽과 val/task/source 선결은 결과101 §86.4가 소유한다.
기존75M×4epoch≈300M의 actual x 노출 분모를 유지하며 2289 고정 cropsteps나 반복자료로 고유량을 부풀리지 않는다.
이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 7. 실행

새 사용자 smoke 통과 뒤 Stage4jWg를 먼저 실행한다. 자료미완8이면 새시각 명시resume으로 이어간다.
오류9/130이면 원본/부분batch를 보존하고 원인·cursor/계측receipt를 확인한다.
75M와val/task 선결이 충족될 때만 Stage4kWd→Stage4k0Wd→기존Stage4lWc→Stage4mWc 순으로 진행한다.

## 8. 한계

모니터 전원복귀/WSL조회지연/시스템절전/TDR 인과는 미확정이다. 새 조회정책도 실제 GPU reset을 복구하지 않는다.
순차 생성→교사내림→학생학습 경로를 유지하며 비승인 async·교정교육/mask를 구현했다고 주장하지 않는다.
학생지능/정식TRAIN_READY/P106 ACCEPT·교사정답/품질은 이번 technical PASS와 구분한다.

## 9. 실행 이력·예측 대조

2026-10-09 원본6·smoke1을 결과101 §86으로 회수했다. literal framing의 전량완결 예측은 이번16/64에서 관측됐지만
소표본·확률적생성/수락집합변동이 있어 단독 가속·내용품질의 인과판정은 하지 않는다.
생산은 구계측정책의조회timeout에 의해 둘 다9였고 뒤학생0이다. 새A는 CPU94 PASS·사용자 실물 NOT_RUN이다.
이전 ‘현재파일 삭제하지 않음’은10/08의판정이다. 이번(3) 적격삭제승인에 따라 exactdone7만 Git/명령/SHA 보존 후 정리한다.

# P106B — 2026-10-11 예산 종료 명시재개와 교사 단독 생산성 A×C


## 1. 왜

[결과101 §90](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md): Stage4jWg는조회3회모두회복/교사6h생산후ownedbudget alarm이9로분류됐고newtrain75,901x·총29.190847M·부족45.809153M이남았다. kWd/k0Wd/lWc/mWc는완성선결보류·학생0이다. 생산속도3.5136x/sec의잔여외삽151일은정식교육목표에너무길어기존명시재개와A×C생산성검증을병행준비한다.

## 2. 질문·범위

Q1은순수 시간예산만료와실제서버/메모리오류의구별,Q2는서로다른개념1/2/4/request×thinking256/1024의공급량/시간,Q3는교사단독ctx상한의실제여유다. 사용자 선택 A+C와교사단독상한검토범위로코드/SH·CPU만작성하고 Codex 모델/GPU는0이다. 기존generation code14·source/tokenizer/배치/LR·HF 원형·공용검사·새온라인의미심사·후행C학습은제외한다.

## 3. 예측

owned alarm의typedpause는예산만료를8로명확히표현할것이다. 실제서버/OOM/지속조회실패는계속중단해야한다. 여러개념/낮은thinking으로요청비용이줄수있지만출력절단·내용품질·구조실패가늘면유효공급은줄수있다. 큰ctx는VRAM여유가있어도SWA/KV할당방식에따라OOM일수있고생성속도향상을보장하지않는다.

## 4. 단계 설계

| 단계 | 런처 | 선결·범위 | 시간h/상한 | 상태 |
|---|---|---|---:|---|
| Stage4jWh | run_P106B_Stage4jWh_budget_pause_resume.sh | 원형inputs/code14·샤드/cursor 재검산;계측3회/별도receipt·ownedpause8 | 6.00/21600초 | 새실물NOT_RUN |
| Stage4kWe | run_P106B_Stage4kWe_budget_completed_corpus.sh | 성공75M/val/언어·과제·출처cap 검산 | .50 | 자료미완이면8 |
| Stage4k0We | run_P106B_Stage4k0We_budget_student_wire.sh | 완성같은V4·teacher내림·원부모2updates | .50 | 조건부NOT_RUN |
| Stage4lWd | run_P106B_Stage4lWd_budget_literal_repeat4.sh | 같은wire·75M×4pass actual약300M | 12.00 | 조건부NOT_RUN |
| Stage4mWd | run_P106B_Stage4mWd_budget_literal_multiaxis.sh | 같은새자식·72실제답/멀티턴/언어손실 | .50 | 조건부NOT_RUN |
| Stage4n0W | run_P106B_Stage4n0W_ac_cpu_contract.sh | 슬롯·source/사고·card·공유3구조시도·SAMPLED_ONLY계약 | .02/600초 | CPU준비만 |
| Stage4nWa | run_P106B_Stage4nWa_teacher_context_budget.sh | CPU계약·teacher단독8K/16K/32K | .50/3600초 | 새GPU NOT_RUN |
| Stage4nWb | run_P106B_Stage4nWb_concepts_thinking_factorial.sh | current16K자원통과·공개family64의원source8 | .75/7200초 | 새GPU NOT_RUN |

A×C namespace `p106b_gemma_ac_v1_s1337`, 원source report D8C72117…을고정한다. 한영각4원source에서samecompletedset8을두순서에서맞춘다.1/2/4개×256/1024의6조건을앞/역순12팔로실행해논리56요청/총3시도최대168요청이다. 여러개념을같은질문의여러재표현답과혼동하지않는다.
교사는번호형QUESTION_i/ANSWER_i/NOTE시작라벨로내용만쓰고코드는source별canonical/ChatML·thinking sidecar를만든다. 성공slot은재시도에서보존하며의미불량문구목록·정답성필터는추가하지않는다. x/assistanttarget·재시도포함wall·완결source집합·실제답·VRAM을보고한다.

## 5. 판정 기준

기존생산수락/한영37.5M씩·task50/25/25·출처25%cap·별도val·75M/fourpass 목표는그대로다. pause8은완성PASS가아니다.
capacity는teacher단독 sparse입력에서8K/3072/1024,16K/6144/1024,32K/12288/2048을각각보존하고16K관측minfree≥2048MiB·조회공백없음이패널선결이다.32K실패는보존하지만16K통과를무효로하지않는다. SAMPLED_ONLY는연속peak증명이아니다.
A×C는ctx16K/total6144/card t1.0/p.95/k64고정이며sameacceptedsource8/arm·양순서의유효x/초와내용후행검토·자원증거뒤에생산정책채택을판단한다. 단순completion tok/s로75M완성시간이나학생교육효과를추론하지않는다.

## 6. 비용·preflight

새16SH전체조건부후보약22.41h이고48h큐를채우기위해미승인중복생산을넣지않는다. 기존producer6h는완료시한이아니다. 교사본체약6,426MiB+KV/graph/ctx/Draft별도이며MTPoff/1slot로가속축과메모리축을분리한다. 공식config256K최대문맥과16GiB실제여유는동일하지않다.
14파일SHA/원cursor/자료version을바꾸지않는resume은계보연속이며,A×C는독립진단출력이다. 사용자가패널결과를선택하기전대량production정책을자동교체하지않는다.75M×4epoch는사용자허용반복SFT의actualtoken분모이며normal600M-pool CPT비교로부르지않는다.
새SFTcheckpointtag는추가하지않고기존미사용예약 p106b_s4_gemma_capability300m_chat32_literalv3_s1337을유지한다. broad runs/registry 내용검사는보호경계로미실행이며source/state/HOLD·정확출력충돌만사용자단계에서재검산한다.
이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 7. 실행

새사용자smoke 통과후 §4의선결순서만실행한다. 새AC source/canonical20MB 이하shards·전체원답/재시도/SHA·partialreport를보존한다. 전부무인으로입력대기/자동무한loop/download는없다.

## 8. 한계

teacher단독ctx소형probe는상한까지채운context/decode나장시간OOM안전을증명하지않는다. sparse memory와생산6h계측공백은분리한다. 원천8의복잡도/언어/수락률이45.81M부족분전체에적용되는지는미확정이다. 온라인동시학생·추가teacher정답검증·C반복억제학습은미실행이다.

## 9. 실행 이력

2026-10-11 raw17+smoke1과 지정evidence를 원형로컬969761e에보존했다. 조회복구예측은3/3에서관측됐지만budget8분류는코드경로차이로실패했다. 새typedpause·D실제재표현·A×C·P093무학습진단은CPU정적준비이며새실물완료는아니다.

# P106B — 2026-10-12 Gemma MTP의 생산 질문·원답 품질 대응 비교

## 1. 왜

[결과101 §68](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)는 MTP off/on 소형 decode 72.334226/149.322297 tok/s를 확인했다. 그러나 현재 생산과 A×C는 off다. 가속을 실제 생산 질문·JSON·이전 대화에서 검증하는 후속을 누락했으며, Bonsai의 가속 음성을 Gemma 비채택 이유로 쓰지 않는다.

## 2. 질문

같은 공개 출처·보존된 학생 질문·이전 대화·sampling/seed에서 MTP on의 답 내용과 구조, 유효 학생 토큰/전체시간, 표본 VRAM은 off와 어떻게 다른가? 옛 family64 off 원답도 함께 보존·표시한다.

## 3. 예측

단순 문항의 MTP 가속이 생산 질문에도 이어질 수 있다. 그러나 출력량·사고량·draft 수락·구조 재시도로 이득이 줄 수 있다. 형식 수락을 정답성으로 승격하지 않고 답과 출처를 후행 판독한다.

## 4. 단계 설계

- Stage6e0W: 소스 선택·질문 고정·분모·20MB 샤드·시간상한 CPU 계약.
- Stage6eWa: 보존된 family64에서 한영×QA/JSON/멀티턴 마지막 턴의 6개 질문을 고정한다. 옛 off 답과 새 off/on을 대응하고 최초 포함 총3구조시도 한도를 유지한다. 새 질문 생성 효과를 섞지 않는다. 현재 지시 한정 Codex 직접 실행은 전체600초 이내이며 새 evidence만 쓴다.
- Stage6eWb: 같은6문항의 off→on/on→off 두 순서 비교. Wa의 단일 순서 결과가 전체 생산 채택이나 장기 안전 증거를 대신하지 않는다.

## 5. 판정

모든6프로필의 구조·mask·출처가 수집되면 기술 수집 완료다. 내용 품질은 출처·원질문·최종답을 별도로 읽어 기록한다. 생산 on은 양순서의 같은 완결집합당 유효 자료/전체시간과 내용·자원을 확인한 뒤 새 생산 버전에서 선택한다. 기존 off inputs/SHA/cursor를 바꾸거나 기존 생산에서 조용히 on으로 전환하지 않는다. 불완전 수집은8, 실제 backend/무결성 오류는9다.

## 6. 비용

CPU 약1분, Wa 전체최대600초, Wb 최대1800초. 교사 단독·학생/학습/checkpoint 저장0. 과거 추가408~452MiB는8K 소형 표본이고 현재 자원은 별도 측정한다.

## 7. 실행

구현·CPU 계약 뒤 새 SH를 등록한다. 큐는 이 비교를 기존 A×C/생산 재개보다 먼저 두며 사용자 입력 대기를 넣지 않는다.

## 8. 한계

6문항은 대량 생산 품질·시드 일반화·장기 OOM을 보증하지 않는다. 옛 원답 대 새 질문고정 결과는 관리 조건이 달라 설명적 비교이고, 새 off/on은 같은 입력의 대응 대조다. MTP는 학생의 학습용 MTP와 다른 교사 추론 기능이다.

## 9. 실행 이력

최초 설계 사전등록 뒤 Wa/Wc의 고정질문 전송 제약을 원형 생산 payload 재생으로 교정했다. [결과101 §91](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에 Wa78.91초/8·Wc211.75초/8·Wd58.66초/0을 원형대로 남겼다. Wc의 질문echo 음성은 실제 생산계약 음성이 아니었다. Stage6eWc는 fixed 전송 복구, Stage6eWd는 원형payload MTPON6/6첫시도이다. 학생/학습0·기존생산OFF불변이며한정GPU승인은끝났다.

새 Stage6eWb는 같은 **원형 생산** 요청6개·OFF→ON/ON→OFF 두 순서24논리요청/최대72구조시도로 준비했다. 교사가 질문 자체를 재작성할 수 있는 실제 생산 계약이므로 원형/새질문·내용/학생x를 모두 기록하며 ‘같은 생성 답의 우열’로 혼동하지 않는다. body 통과·source불변과 후행6건 판독은 ON기술가능 근거지만 대량 정답성·본생산 가속은 미확정이다. 현재 실물 SH는 `run_P106B_Stage6eWb_mtp_production_order_pair.sh`, 완료3SH는동일 stem의-done으로보존한다. 사용자입력대기/온라인 의미문구검사/본생산자동ON은없다. §4의 최초Wa 고정질문안은 역사설계이고 현재Wb의production protocol이 실행정본이다.

## 2026-10-13 실행 회수·MTP ON 분리생산과 도구 복구

[101 §92](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)가 양순서24요청·원답·생산량/계측·capacity 코드오류의 정본이다.
실제 MTP 공급 가속 방향은 관찰됐지만 의미 품질 동급·장기OOM 안전 예측은 미확정이다.
문맥 시험은 AttributeError로생성0, factorial은선결HOLD로요청0이다. 큰상한이측정됐다고쓰지않는다.

### 1. 왜·질문·예측

동일12request쌍의 한영6프로필 두순서에서 ON이 더 빨랐다. 현재생산은고유75M에 못미쳐교사생산을늘려야한다.
단독교사의목표는유효student x/시간이며 completion속도/생각문자수와다르다.
작은표본과그대로복제된문맥결함이있어대량가속/내용PASS는예상으로도보장하지않는다.

### 2. 단계·실행·선결

| 단계 | 상태/실행 | 선결·판정 |
|---|---|---|
| Stage4n0W / nWa / nWb | 원시도종료: CPU0 / AttributeError(생성0) / HOLD8 | 과거원본보존,자원음성으로부르지않음 |
| Stage4n0Wb→nWc→nWd | 새tag p106b_gemma_ac_v2_s1337 준비 | currentCPU·실제template/tokenize·같은16Kcapacity이후56논리request의factorial |
| Stage4jWh→kWe→k0We | 정상6h예산보류→quotaHOLD→학생전HOLD | 실제신규77500x·학습0 |
| Stage4j0W | CPU6회귀·budget회귀와새SH | OFF4선조/14코드불변·namespace복원·ON플래그검사 |
| Stage4jWi | MTP ON 최초fork6h 사용자실행용 | 정확OFF4배치/입력/원source SHA·기존cursor계승·fresh ON namespace |
| Stage4jWj | 명시6h재개 사용자실행용 | ON fork inputs같음·새batch번호·동시producer금지;중단batch자동삭제안함 |
| Stage4kWf→k0Wf | CPU75Mmerge→학생2업데이트 | ko/en37.5M씩·task/source/valquota·teacher내림 |
| Stage4lWe→mWe | 조건부약300M4epoch→다축평가 | 동일completed corpus/wire·현재학생배치/LR·새CPT·72첫답 |
| 옛 Stage4lWd/mWd | 아직미실행·선결GATED | OFFv3 자료완성필요,원런처보존 |

### 3. 고정 계약·판정 기준

같은Gemma target/draft, t1/p.95/k64/minp0/presence0/repeat1,ctx8192/thinking1024/total3072를 유지한다.
새 ON 생산은자료/사고/마스크/출처와모든구조시도(최초포함총3)를보존한다.
절단/라벨/빈답/학생문맥·mask는기술조건으로계속거부하지만 의미오류 문자열 검사는추가하지않는다.
OFF원본/진행위치/중간보고를고치지않고, 새ON자료만HF/sft_ready/p106b_gemma_deficit_mtp_v4에쓴다.
75M불충족은예산보류/원천소진/선결HOLD로분리하고학생을올리지않는다. ON실행0/정식TRAIN_READY아님.

### 4. 비용·배치·한계

`run_P106B_Stage4n0Wb_ac_recovery_cpu.sh` — 0.02h, CPU regression/current template-token contract; no models

`run_P106B_Stage4nWc_teacher_context_recovery.sh` — 0.5h, User-only capacity rerun; ctx8K/16K/32K; success is sampled resource not semantic truth

`run_P106B_Stage4nWd_concepts_thinking_recovery.sh` — 0.75h, Only after current16K capacity; MTP OFF factorial concepts1/2/4 and thinking256/1024

`run_P106B_Stage4j0W_mtp_fork_cpu.sh` — 0.02h, CPU pinned-OFF-ancestor/new-ON-namespace/shared retry budget contracts; no model

`run_P106B_Stage4jWi_mtp_on_fork_production.sh` — 6h, User teacher-only first ON fork6h; old four OFF batches read-only; quota incomplete is pause8

`run_P106B_Stage4jWj_mtp_on_explicit_resume.sh` — 6h, Explicit existing ON fork6h resume; fresh batch only; no reset or concurrent producer

`run_P106B_Stage4kWf_mtp_completed_corpus.sh` — 0.5h, Only when cumulative unique train75M and language/task/val/source quotas complete; CPU merge

`run_P106B_Stage4k0Wf_mtp_corpus_student_wire.sh` — 0.5h, Completed75M only, teacher down; two student updates not full300M

`run_P106B_Stage4lWe_mtp_corpus_chat32_repeat4.sh` — 12h, User-only completed75M and wire; micro8 accum16 ckptON four real passes approx300M

`run_P106B_Stage4mWe_mtp_corpus_multiaxis.sh` — 0.5h, Exact completed new student; same72 first answers/native loss; no teacher quality automatic PASS

6h는1개제한창이지75M완성시간이아니다. 현OFF 실측의 잔여외삽은약147.54일이며 ON작은속도비로최종일정확정하지않는다.
teacheronlyMTP와학생MTP헤드는서로다른방법/가중치다. 새입력에mtp=true/draft/config/선조SHA를명시한다.
현재수리/SH STATIC_ONLY·모델/GPU E2E_NOT_RUN. 보호원천/다운로드/원본변경없음.
이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 2026-10-14 Stage4p — 조회 프로세스 수명과 표본 신선도 대조

### 1. 왜·질문·예측

사용자 Stage4jWi/Wj는 실제257후보·15,231 신규 train x를 남겼으나
VRAM 조회의 최대3회 실패로각exit9였다. OOM·교사생성0으로 해석하지 않는다.
기존 reader는 RLock으로 직렬화하며200ms 기다림마다 새 nvidia-smi를 실행한다.
5초 timeout 후 kill/wait 때문에 실제 누락창은5초보다 길 수 있다.

동일 교사/6원형 payload/MTP ON/seed/8K context/3072 total/1024 thinking에서
현 one-shot 조회와 하나의 지속2초 조회 프로세스를 비교한다.
주요 질문은 조회 지연·실패와 프로세스 생성 부담이며 내용 정답성을 자동 판정하지 않는다.
프로세스 생성이 줄어도 WSL/드라이버 지연이 지속하면 생산 중단은 여전히 가능하다.

### 2. 단계·판정

| 단계 | 계약 | 자원·판정 |
|---|---|---|
| Stage4p0W | CPU 파싱·새 sequence만 전달·오래된/죽은/잘못된 표본 거부·종료/원형 복원 | 모델0·설치0 |
| Stage4pWa | single-process one-shot 대 persistent-loop2s; 한영 QA/JSON/3턴6개 각각 | 단독 Gemma MTP ON·같은 sampler; timeout/gap/age/프로세스수/원답/요청시간 분리 |
| 후속 생산 | 비교 후에만 별도 production namespace·선조 SHA/명시 cursor로 연결 | 옛OFFv3/ONv4·generation14코드/inputs/원형 불변 |

표본은 memory.used/free 두 정수이며2초는 조회 요청 간격이지 연속 peak 측정이 아니다.
각 호출은 이전과 다른 표본 sequence를 받아야 한다. 수신 시각과 전달 age를 기록하며
하드웨어의 정확 측정 시각을 아는 것으로 주장하지 않는다.
영구 오류·5초 동안 신선한 표본 없음·낮은free·교사 종료는 계속 fail-closed다.
timeout만 기존최대3시도 내 회복하고 누락구간을 숨기지 않는다.
백엔드가 계속 정상인 것과 측정이 충분한 것은 별도다.

### 3. 비용·실행·한계

CPU1분 미만, GPU12교사요청약5~10분 추정/hard cap900초.
새tag p106b_memory_query_v1_s1337, 새evidence만 저장·새데이터를 본학습에 자동 포함하지 않는다.
실행파일: run_P106B_Stage4p0W_memory_stream_cpu.sh,
run_P106B_Stage4pWa_teacher_memory_backend_pair.sh.
GPT 직접실행은 사용자7의2026-10-14 17시 이전 승인에만 의존한다.
표본신선도·오류수리가 생성품질·장기OOM안전의 증거는 아니다.
이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 2026-10-14 Stage4q — 학생에게 보이는 문맥과 재질문 SFT 소형 대조

### 1. 왜·질문·예측

원천4238/4473행의 문맥형 가족과 한국어해시표본32중11행의 누락문맥을 확인했다.
교사 원문 근거와 학생 입력의 차이를 먼저 줄이는 별도 진단이다.
8개의 코드계산 과제 유형에서 주어진 문맥은 읽고, 식별 정보가 없으면 재질문하며,
추가 user정보 뒤 답을 고치는 학습 가능성을 본다. 새로운 일반 지식75M을 만들었다고 보지 않는다.

질문: 같은 부모/같은 자료에서 NTP high(Adam1e-4/Muon4e-4),
NTP low(1e-5/4e-5), MTP high(1e-4/4e-4)가 지시·문맥조회·정보부족 대응을 개선하는가?
짧은 반복은 과제 형식만 외울 수 있고, 재질문을 과잉 사용하거나 기존 언어능력을 잃을 수 있다.
따라서 실제 첫답·가족별 정확 조건·실제2턴 rollout·native CE를 모두 기록한다.

### 2. 자료·단계·판정

가상 key/value·산수·bool·알려진 JSON·조건갱신·명시 정보부족/재질문/추가정보를
한영50:50의고유4096 train/별도512 val로 구성한다.
같은 질문·대화의 완전 중복과 같은 semantic root의 split교차0을 CPU검증한다.
이는8유형의규칙 변형이며4096개의새세계지식이나75M고유토큰으로 부풀리지 않는다.
실제학생 x/assistant/horizon 분모는 tokenizer실측으로 공개한다.
val에는 학습에 없는 문장구성의 질문을 포함하고 기존8질문은 학습에 넣지 않는다.

| 단계 | 내용 | 시간·경계 |
|---|---|---|
| Stage4q0W | 생성/중복/semantic root split·Canonical/ChatML·모든 MTP 턴 마스크 CPU 회귀 | 모델0 |
| Stage4q1W | 실제 tokenizer로 새 frozen corpus·분모/원천지문 | CPU·20MB shards |
| Stage4qWa/Wb/Wc | 같은 parent·micro8accum16·seq1024·ckptON·compiledefault·4epoch128updates | 각약10~20분 추정·hard cap30분 |
| Stage4qWd | 같은body/source/x/target/update 비교와 실제답 판독 | CPU 정합·GPU추가0 |

CPT부모는 기존chat32 dense14를 weight-only로 읽고 새optimizer를 만든다.
NTP/MTP의 초기body 지문·순서·실제노출은 같아야 한다.
MTP는같은assistant턴2/3/4타깃·기존0.1계수경로며 teacherMTP와별개다.
모든추론평가는 native1토큰 경로의FP32/math로 고정해 BF16블록 반올림을 비교에 섞지 않는다.
정확답을코드로아는 과제는 그정확계약만 채점하고, 재질문 자유표현은 원답 후행판독으로 따로 읽는다.
틀린모든문구목록·온라인 의미검사·재생성은 없다.

### 3. 실행·비용·한계

tag p106b_context_clarify_v1_s1337; 새HF/sft_ready corpus·small evidence·새weight-only checkpoint.
원본HF/runs/cache/생성자료 수정0·TinyDataset0·다운로드0.
GPT 직접 실행은 사용자7의당일17시한도 안에서만 한다.
원75M×4/300M의부족45.716M을 이소형과제로대체하지 않는다.
측정한 과제 개선을 일반지능·새구조/라우터채택·전량자료정답성으로승격하지 않는다.
이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 2026-10-14 Stage4r — 정보부족 힌트 없는 독립 질문

Stage4q의64질문은8스키마이며일부건물질문에식별정보부재힌트가있다.
같은동결자료를바꾸지않고학습에없는24질문을새로잠근다:
bare정보부족8·완전지문이있는대응8·초등세계상식4·작은산수4.
정확parent와새NTPhigh/low/MTPhigh를같은FP32/math native추론으로각24첫답96개에넣는다.
상식/산수16대상은주어진지문/고정참조답계약을별도로채점하고free재질문은원답후행판독한다.
사람/GPT전수승인이나문제문구리스트를온라인에넣지않는다.
새test를교육에넣지않고future선택후에는또독립test가필요하다는한계를남긴다.
source SHA/CPT SHA·prompt·actual답/token IDs·종료·새입력토큰/원답분모를20MBshards에보존한다.

- Stage4r0W run_P106B_Stage4r0W_implicit_context_cpu.sh:case그룹/추론입력/참조답구조 CPU; 모델0.
- Stage4rW run_P106B_Stage4rW_implicit_context_transfer.sh:4subject×24,학습/새CPT0.
- tag p106b_context_transfer_v1_s1337,약3~8분추정/cap600초;GPT는user7의당일17시이전만.

예측:구체적문맥필드를배워도bare질문은이해못하거나모든정상QA에도재질문할수있다.
정보부족대응·정보충분시정답·일반상식/산수·초기부모의능력을구분한다.
원75M×4·teacher원생산·student배치·기본precision은불변이다.
이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 2026-10-14 Stage4s — 실제 원천의 선택 근거를 학생과 공유

### 왜·질문·예측

Stage4q/r에서색상·연구실패턴은배웠지만새지문값과일반QA는미회복했다.
원생산의teacher-only문맥결손을새source-QA계약으로직접시험한다.
현재원형6배치/14code/75M루프는변경하지않고새16공개원천을동결한다.
기존batch5의건물10655·계통10652를포함한KO8과family64의EN8이다.

교사는자료에서새QA와NOTE의SOURCE_IDS만선택한다. 코드는ID의범위/중복·원문slice·
학생실제tokenbudget/역할·마스크를검사하고선택원문을student QUESTION앞에붙인다.
이ID확인은참조byte연결이지의미적답근거·독립정답의증명이아니다.
단지원문지시가question-generation인것을‘틀린답’으로버리지않고새목적을명시한다.
불명SRC의목적을metadata의question-answering/template1만보고추정하지않는다.

### 단계·판정·범위

- Stage4s0W: SOURCE span/ID·제어header·budget·lossless근거·공유최대3구조시도 CPU.
- Stage4sW: 같은GemmaMTPON/8K context/3072total/1024thinking/card sampler·새16원천.
  최대3시도는첫요청포함이고문구오류/의미재시도는없다.
- 새tag p106b_visible_source16_v1_s1337,CPU약1분·teacher약2~8분추정/cap900초.
- 단독teacher·새원답/canonical/참조SHA·studentx/assistanttargets·thinking·거부/오류사유를20MBshards에보존.
- LABELS/참조ID완결과실제답/의미·75M완성은분리판독한다.
- 다중답/JSON/본300M에자동접속하지않으며bulk코드는새정책결정뒤다른namespace로연결한다.

원형소급PASS·잘못된모든문구리스트·원TinyDataset접근·원HF/가중치수정·추가download는없다.
GPT모델실행은user7의당일17시이전한정권한이며이후실행은사용자에게인계한다.
이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 2026-10-14 Stage4t — 충분/부족 문맥의 같은 주제 대조

### 왜·질문·예측·대안

Stage4r의새지문값8개는세팔모두미회복이었다.
과제유형과표현이다른곳에서building재질문을과잉복사해좁은템플릿학습을확인했다.
이번에는동일주제/질문종류에서근거가충분한경우와부족·모호한경우를함께가르친다.

| 안 | 내용 | 장점 | 단점·비용 |
|---|---|---|---|
| A 권장 | 부서/연설/도서관/책/물품/TRPG+bool/산수8유형의코드근거8192/val1024 | 정답/부족을코드로아는새표현·주제대조·짧은실행 | 합성지식/유형한계·약20분/팔추정 |
| B | source16계약으로실제공개원천512~1024를교사로생성후학습 | 자연주제/언어폭넓음 | 교사추가시간과내용/권리후행검토,완성시간미실측 |
| C | 자료를유지하고재귀/폭을동시에변경 | 구조효과탐색가능 | 현재자료편향을해결못하고KV/부모교락·구현비용 |

현재7의한정주도실험에서는A의small course만별도실행하고Bbulk/C구조는자동채택하지않는다.
world QA나75M을합성규칙반복으로대체하지않는다.
새데이터/양/문장구성이바뀌므로4q와의차이를그중한축에단독귀속하지않는다.

### 조건·단계·판정

- 현재동일chat32 dense14 parent·micro8accum16seq1024·ckptON·compiledefault·4pass256updates.
- NTP joint high1e-4/4e-4 대mid5e-5/2e-4. MTP는4q의효능/대가미확정으로이번추가팔에서off.
- 같은broad자료/초기body/실제x/targets/update·순서를두팔에서고정한다.
- 같은doc/초기조건/이름매핑root의split교차0·전체대화중복0,
  실제x/assistant/horizon/행언어분모는tokenizer로계산한다.
- 가상근거의값이있으면답하고,없거나여럿이면그주제의필요정보를묻는다.
  free답은후행판독하며온라인틀린문구목록/의미재생성은없다.
- 기존4r 질문/정답은train에넣지않고별도새wording/values val과실제대화를보존한다.
  후속선택과동일평가반복의편향을명시하고새독립범용test가필요하다.

Stage4t0W CPU계약→4t1W 실제tokenizer동결→4tWa/high·4tWb/mid→4tWc 비교회수.
새tag p106b_context_broad_v2_s1337·새HF/sft_ready/weights/evidence만기록한다.
예상각15~25분/hard cap1800초,권한은user7의당일17시이전뿐이다.
기존생산14code/원HF/원CPT/보호TinyDataset·학습/추론기본은불변이다.
이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 2026-10-14 Stage4jWk — 조회 수리만 분리한 명시 계보 재개 준비

원OFF4/ON2 batch와inputs/커서를모두SHA로잠그고새 stream-v5 namespace의batch000006부터잇는다.
source render/샘플링/8K/3072/1024/원generation14code는불변이다.
이는새근거공유QA계약을대량채택하는런처가아니며기존PSEUDO_UNVERIFIED baseline의
조회고장만회복하는명시대안이다. source-visible 개선/새정책은별도새버전으로해야한다.
persistent2s의신선도/최대3조회시도·영구오류/lowfree/교사종료fail-stop을적용한다.
기존폴더에새batch를쓰거나원inputs를덮어쓰지않는다.

- Stage4j0Wb run_P106B_Stage4j0Wb_stream_fork_cpu.sh:계보연속/원경로복원CPU.
- Stage4jWk run_P106B_Stage4jWk_stream_mtp_fork_start.sh:새fork 최초제한창.
- Stage4jWl run_P106B_Stage4jWl_stream_mtp_explicit_resume.sh:그새fork가있을때만명시resume.
- TAG p106b_s4_gemma_capability300m_chat32_mtpstreamv5_s1337,
  OUTPUT HF/sft_ready/p106b_gemma_deficit_mtpstream_v5.
- 원4jWi/Wj 오류9·257후보는소급성공으로바꾸지않고new reader 근거와구분한다.
- 기본창1h·hard cap≤6h/비교source재검산시간별도;이번GPT는CPU/check-only까지만먼저검증한다.
- 본75M미완성일때학생기동/형식변경/불명괜찮음선언/보호원천추가접근은없다.

새source계약이결정되면이baseline재개와의선택·폐기범위를별도로보고한다.
이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 2026-10-14 실행 회수와 후속 경계

Stage4r96첫답·4s 최초import오류/4sWb 새16·4t 두팔256업데이트와 개발72답을 [결과101 §99~§104](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에 회수했다. Stage4tWc는 독립런처가 아니라 후행 비교회수이며4tWd는 기존24의 개발용 재측정이다. current5팔의 좁은코드개선은 범용지문/상식 개선이 아니고 native 보존 실패도 남았다.

복구4s0Wb/4sWb는 기존16 원천·샘플링/예산을 유지한 새namespace v2이며 helper import/4인자/반환키 계약을 CPU18로 확인했다. v1 모델0/오류1은 보존한다. 다음 실제근거512~1024 확대·원문 replay/종료점·재귀/폭은3안 질문으로 우선순위 회수중이며 자동bulk 채택하지 않는다. baseline stream-v5 장기생산은 CPU/check-only까지만 통과했고4jWk/Wl은 미실행이다. 본75M×4·원배치·보호원천/기존CPT 경계는 불변이다.

## 2026-10-14 Stage4j0Wc·4kWg/4k0Wg·4lWf/4mWf — stream-v5 후속 분리

query만 수리한 새stream-v5는 옛v4용4kWf/4k0Wf/4lWe/4mWe와 연결하지 않는다. 같은 fork_scope 안에서 새 CORPUS/WIRE/STUDENT/EVALUATION/TAG로 finalize→wire2→train4pass→eval을 연결하며 학생단계에는 PersistentMemory/교사가 없다. 최초/재개/merge의 inputs는 exact source/code와 일치해야 하고, all train/val·task·language·source quota가 부족하면 merge/학생을 열지 않는다. 옛6미실행런처는 HOLD 계승이지 삭제/취소가 아니다.

- Stage4j0Wc CPU: 새namespace/모델 없는 downstream dispatch·없는inputs 거부; 기존계보/reader회귀와 함께.
- Stage4kWg: 누적 고유train75M와 모든quota 충족 뒤 새완료 corpus만 생성. 약0.5h 추정.
- Stage4k0Wg: 교사내림·동일완료 corpus에서2업데이트의 실제x/마스크/shape 검증. 약0.5h 추정.
- Stage4lWf: 같은부모·chat32/micro8accum16seq1024/ckptON·현재LR·4pass, 약300M 실제x. 약12h 보수추정/실측미정.
- Stage4mWf: 같은새자식·native loss/72첫답·명시멀티턴, 약0.5h 추정.

CPT에서의2배pool 권장은 본SFT의75M×4 노출 목표와 다른 설계다. step×131072는padding 상한이고 실제x/assistant targets는행별encode/분할로 기록한다. Tag는 새stream-v5/v6만 사용하고 원HF/runs/CPT/source를 고치지 않는다. 생산정답/지문공유는 baseline에서 계속미검증이며 source16개선 계약을 자동채택하지 않는다. 새모드의기술 CPU 통과는75M 완료·학생/교사품질·현재 E2E가 아니다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 2026-10-14 후속 Stage4u/4v — 실제원천512·64와 근거본문 보조목적

### 1. 왜
사용자가 세 우선순위 질문 모두 알아서 판단할 것을 회신했다. §101의source16은기술연결만확인했고
넓은합성학생은새지문각1/8·망각이었다. 자연원문과학생의근거를연결하고 기존본문문법을잊는대가를가른다.
8M subset의네번째KO가족이부족하고PUBLIC에는Adversarial이없으므로
공개부모원형 전체와이미보유한OFF4/ON2 raw의원래Adversarial source만읽는다.
교사과거답/생각을새근거로쓰지않고 원래source 메시지·출처를새deck에보존한다.

### 2. 질문
같은512원천의근거QA/자료필수누락대조를학생이새문장에도적용하는가?
같은input·assistant target에selected reference의NTP손실.1을추가하면문맥/원문보존이개선되는가?

### 3. 예측
명시자료를보면읽어답하기·자료없을때요청하는단계를배울수있지만,
generic자료요청을모든QA에오적용하거나원문스타일반복을보조목적으로강화할위험이있다.
32업데이트/4pass는작은gate이고범용지능/75M완성을보장하지않는다.

### 4. 단계
- Stage4u0W: producer source-only계약·reference/assistant label분리·globaldenominator·scope복원 CPU.
- Stage4u1W: 새source deck train512/val64에reserve128/32·한영행수50:50·네가족각25%로SHA순선별.
  원parent_concept SHA로새20% val분할하고선택된긴본문byteSHA도교차0을검사한다.
  원래split은별도보존하며과거pretrain/번역사실누설없음을보장하지않는다.
- Stage4u2W: Gemma12B/MTP ON·ctx8192/total3072/thinking1024/카드샘플러 그대로.
  그룹별최초포함3구조시도·seed변화·cache_promptFalse·teacher만상주.
  entity/relation/조건/답 모두선택SOURCE_IDS에포함하라고요청한다.
  ID/byte/1024예산만자동검사하고 의미blacklist/전수정답승인없음.
- Stage4u3W: 완결512/64 source에서각supported/request-reference 두view로train1024/val128.
  자료가없음을개인QA의의도분류로추정하지않고‘제시된자료만사용’하는생산자출력계약으로정한다.
- Stage4vWa/vWb: 같은origchat32 dense14/parent SHA12E18658/seed1337·micro8accum16/seq1024/ckptON
  compiledefault·4pass32업데이트·Adam5e-5/Muon2e-4. MTP OFF·같은row순서/실제inputx/assistanttargets.
  A SFT-only. B 같은forward의ignored user-reference 위치에NTP.1을추가한다.
  추가input0·추가reference target event/CE-head계산/시간은별도다.
- Stage4vWc: 같은새val 원답/teacherliteral agreement·자료요청후행판독·native32crop/8legacy·원문CE·대가를회수한다.
  교사pseudo답일치는독립정답/범용지능판정이아니다. 이전24는개발용만·새원천에없으면독립SFT val로구분한다.

### 5. 판정
source/family/언어/원본문그룹/예산과정확512/64가완결되지않으면학생은기동하지않는다.
finite loss/clip전최대값·32update/4pass/x/targets/참조targetevents를검산한다.
실제답은source와함께후행판독하고기술/표면일치/정답성을분리한다.
Muon/이자료/작은seed조건의sigma는미측정이다. 보조목적의기본채택은하지않는다.

### 6. 비용
CPU선별/동결약1~3분추정,576교사응답은이전16의평균8.1초를기준으로약78분+실패/길이비용.
hard cap9000초·당일17시전절대상한과정리시간으로더줄인다.
학생각5~15분추정/cap1200초·대략2.6GiB+추가CE 비용은새실측으로확인한다.
일반48h큐목표는오늘17시한정실측예산이아니고부족값을채우는quota도아니다.

### 7. 실행
새run_P106B_Stage4u0W_source_course_cpu.sh·4u1W_public_source_deck.sh·4u2W_visible_teacher_course.sh·
4u3W_visible_course_corpus.sh·4vWa_source_sft_only.sh·4vWb_source_reference_lm.sh를만든다.
태그p106b_source_course_v1_s1337와새HF/weights/evidence(local)만쓴다.

### 8. 한계
생각/NOTE/원답은sidecar이고학생target은ANSWER또는코드의자료요청문장만이다.
자료요청은모든‘의도를모르는질문’의자동분류기가아니다. 자연정답·권리/PII·semantic source지지는후행검토다.
원형6batch/기존자료/제품default·보호TinyDataset·다운로드·공용checker·추가삭제/외부게시 불변.
기존75M×4의대체가아니다. 구조/재귀/폭/MTP효능을한팔에섞지않는다.

### 9. 상태
14:11까지 교사576원천·수집660요청과 A/B 각32업데이트를 완료했다. 원문손실 악화는
A +0.13214/B +0.10060으로 B가 조금 작았지만 같은 실제QA의 교사문자일치는 각9/32다.
자료요청32/32와 일반형식 새지문0/8을 분리한다. 예측한 지시문 의존·과잉요청이 남았으며
본문보조 목적을 기본채택하지 않는다. 상세회수는 결과101 후속절로 이어간다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

Stage4u1Wb는이미동결된736source의정확Root/긴본문SHA교차/가족lane을모델없이검산하는후행CPU다. 직접API freeze의별도원형증거이며같은source생성을다시실행하지않는다. Stage4vWc의새실물대조는 `run_P106B_Stage4vWc_source_objective_pair.sh`가두학생보고서/targetevent·원문CE·정확대응을회수하며원답/meaning판정은독립후행기록이다.

Stage4wW는교사source64 val원답과독립인새시험이아니라이전에사용한24의개발용재측정이다. 두팔완료/CPT SHA뒤sameparent/A/B×24의72첫답을FP32/math nativeK1로읽는다. 원24의지문값/상식/산수코드계약과힌트없는재질문후행판독을분리하고원형을train에넣지않는다. 이유는명시‘제시된자료만사용’형식에대한암기만했는지,일반질문에도자료요청을남발하는지저비용으로보기위해서다.추가학습/새CPT0·약5분추정/cap600초·당일17시전권한만사용한다. 이점검을범용지능/독립benchmark로올리지않는다.

## 2026-10-14 Stage4x — 같은 원천의 질문 형식 대조

### 1. 왜
Stage4v의 같은문구 자료요청은32/32였지만 이전24 개발용 질문의 새지문 정답은0/8이었다.
단일 ‘제시된 자료만’ 제어문구 의존인지 확인한다. 교사/원천을 다시 생성하지 않는다.

### 2. 질문
같은512원천의 지원QA 절반을 자연 본문과 질문만으로 제시하면 일반형식 지문 답이 나아지는가?
### 3. 예측·대안
자연형식 노출이 도움이 될 수 있지만32업데이트·답의 불량·부모의 낮은QA 능력으로 여전히 실패할 수 있다.
A는 입력형식 대조(권장), B는 같은문구128업데이트(노출/망각증가), C는 원천을 다시 교정(교사비용/내용변경)이다.
사용자 우선순위 자율위임 범위에서 가장 작은 원인분리인 A를 선택한다.
### 4. 단계
- Stage4x0W: CPU4개·새형식 동결. 각split/언어/가족 지원QA 정확절반만 바꾼다.
- Stage4xWa: 같은원부모·SFT-only·Adam5e-5/Muon2e-4·micro8/accum16/seq1024/ckptON/defaultcompile,
  동일1024행·assistant targets·4pass·32업데이트. 자료누락 view의 명시 계약은 그대로다.
- Stage4xWb: 같은 이전24 개발문항의 parent/A/B/C 실제첫답, 재학습/새저장 없음.
### 5. 판정
새namespace p106b_source_format_mix_v1_s1337. 원source/답·그룹·32update는 같지만 x길이는 달라진다.
기존A와 수정valCE 직접순위는 금지하고 공통개발질문·후행 실제답·nativeCE를 보고한다.
개발문항은 독립test가 아니며 기존σ는 전용하지 않는다. 자동의미/문구검사 없이 원답을 보존한다.
### 6. 비용
CPU 약1분, 학생 약5분·2.6GiB 추정/cap1200초, 대응평가약1분/cap600초. 17시 이전만 직접실행한다.
### 7. 실행
run_P106B_Stage4x0W_format_mix_corpus.sh → run_P106B_Stage4xWa_format_mix_student.sh →
run_P106B_Stage4xWb_format_mix_dev24.sh. 파일은 새로 작성하며 입력대기·다운로드·삭제가 없다.
### 8. 한계
원지문 사실/교사답 정답성·독립 범용지능·75M 완료는 주장하지 않는다. 원자료/교사/공용코드 불변.
### 9. 상태
실제CPU4/동결·C32update·이전24의96첫답을 완료했다. C의자체valCE감소는관측했지만
일반지문/상식/산수정확계약은여전히0이다. 형식변경만으로넓은이해가열릴수있다는예측은미달이다.
교사문자일치와source충실도/실제세계정답은구분하며기본형식 자동채택은하지않는다.

추가 대응평가는 같은val32 source를 관리형/자연형 각각제시해 parent/A/B/C의256첫답을회수한다.
같은gold/근거/질문을공통으로쓰며 valCE를순위화하지않는다. Stage4yW·약1~3분/cap600초.
이 평가는 source 내부 일반화/형식 진단이고 독립세계정답/범용test가 아니다.

공통256첫답 실제완료·114.544초. 관리형9/9/8과자연형1/1/3의문자일치는형식영향과한계를보였고
자연형식C도일반이해미회복이다. 종료집계의키오류는원형/코드Gitcf3ee25를보존하고새4yWb CPU4로
재집계했다. [결과101 §108~110](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)가 실제회수/원형13/직접동결을소유한다.
새14SH는-done으로보존(추가삭제0), 기존75M×4·생산v5/원CPT·보호경계는그대로다.

## 2026-10-14 Stage4z — 학습 없이 질문대상·본문순서의 대응 개입

1. 왜: 후행 source32에서 대상오해/앞문장복사가 보여, 관리형식이맞아도질문대상을구별하는지추가원인분리를한다.
2. 질문: 같은두사실에서묻는대상만바꾸거나문장순서만바꾸면답도맞게바뀌는가?
3. 예측: 새문장어휘와값대상매핑에서여전히실패할수있다. 첫값복사경향이있다면질문대상을바꿔도같은답을낼수있다. 반복불변이구조원인의증명은아니다.
4. 단계: CPU3로한영/first-position동량·같은사실의대상/순서독립대조를검사한뒤4endpoint×32첫답.
   예:가온빨강·나래파랑에서가온/나래를각각묻고같은매핑의문장순서를뒤집는다. 값배정도반대로바꾼다.
5. 판정: 값만답하라는명시출력계약의정확문자정답·질문쌍불변/첫값경향을각각집계·실답을읽는다. 새학습/teacher/체크포인트저장0.
6. 비용: 기존parent/A/B/C만로드·FP32math/cacheON/nativeK1/greedy64·대략1~3분추정/cap600초·사용자17시전한정.
7. 실행: run_P106B_Stage4zW_source_binding_factorial.sh; tag p106b_source_binding_v1_s1337.
8. 한계: 사후설계한코드근거조회작은진단·일반지능/세계사실/재귀/tying원인미판정. 원자료/가중치/제품코드불변.
9. 상태: CPU3와실제128첫답을완료0. 명시값0/32각팔과대상/순서/고정값편향을본문에회수했다. 구조원인/모델전면불능으로확대하지않았다.

영향도: 새진단2코드/1SH·새자기작성가상원답만신설,기존표본/부모/코드/원형/Git보호범위불변.
대안은source새학습(학습량교락/시간),언어replay(보존축),지금의무학습개입(가장작은관찰범위)이다.
당일우선순위자율위임안에서무학습개입을선택했고새모델/배치정책은채택하지 않는다.
이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 2026-10-14 Stage4aa — 코드근거의 대상/순서 균형 학습

1. 왜: 4z에서관리형이라도질문대상을바꾼16쌍중7/8/9쌍은학생A/B/C의답이그대로였고,첫이름+고정값의편향이보였다.
2. 질문: 코드로확정한두사실에서대상·순서·값의네view를골고루학습하면새이름의조회가개선되는가?
3. 예측:좁은관계조회는배울수있으나형식/질문언어에의존하거나native손실이악화할수있다. 넓은상식개선은예측하지않는다.
4. 단계: CPU3(root중복/val이름교차/골드4view)→새4096train/512val 동결→새원부모128업데이트·4pass.
5. 판정: 새val명의실제64답/고정native32crop·legacy8을기록;기존Mina/Noah·가온/나래는train/val에넣지않고진단용으로유지한다.
   4z32의사후설계를계승했으므로그재사용은개발평가이며독립범용시험으로부르지않는다.
6. 비용:같은chat32 원부모·Adam5e-5/Muon2e-4·micro8accum16seq1024/ckptON/defaultcompile·MTPoff,
   학생약5~10분추정/cap1200초·당일17시전한정. 새교사/원자료읽기/설치/기존CPT수정0.
7. 실행: run_P106B_Stage4aa0W_binding_course_cpu.sh → run_P106B_Stage4aaW_balanced_binding_student.sh.
   tag p106b_binding_course_v1_s1337. 실제x/assistant는encode로재계산;128×131072는padding상한이다.
8. 한계:1024가상fact root의4view와4노출은새75M지식이아니다. 기존자연학생과자료/양/과제·업데이트가다르므로차이를한축의효과로분해하지않는다.
9. 상태: 중복fact순열의CPU실패를캐논이름쌍으로수리한뒤CPU3·동결·실제128update/4pass완료. 새val64는0→35,전체512는315이나첫값기준256·전체4view27root·native악화를함께보고한다. 좁은조회부분학습예측은일부성립·일반해결/보존은미달이다.

영향도: 자체작성코드골드course·독립2코드/2SH·새HF/CPT/evidence만 신설한다. 기존source512/HF/CPT·생산·kernel/환경은바꾸지않는다.
대안: teacher재생성(시간/내용교락), source자료더반복(의도/값고유량부족), code-known대상/순서course(가장작고정답을아는학습조치).
사용자17시전품질개선자율위임의좁은조치로마지막안을실행하며본75M×4는불변이다.
이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

### Stage4ab/4ac — 실제 내용선택과 형식 이득의 구별

4aa는실제128업데이트와새val64의35정확답을완료했지만,32개발문항17/32는고정값만출력해도절반을맞힐수있다.
Stage4ab는원32개발문항과같은조건에서새학생32답만실행·원128결과를SHA로계승한다.
Stage4ac는동결val512전체의실제첫답과같은두사실의두대상/두순서128root 일관성을검증한다.
원문첫값만복사하면명시코드상256/512가되므로이기준과실제답을구분한다. 무작위귀무가설/통계자가로쓰지않는다.
기존parent의whole512답은미실행이므로subset0/64를전체0/512로늘리지않는다.
둘다학습/teacher/CPT저장0·FP32math/cacheON/nativeK1/greedy64·당일17시전·cap600초이며
실제whole512는독립범용벤치가아닌같은course validation이다. 새raw/namespace만쓴다.
실제4ab는32답17정확(2.799초),4ac는전체512답315정확(21.693초)·한145/256/영170/256·4view완결27/128였다.
범용/본75M은미완이며[결과101 §111~113](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에후행판독과5원형/명령을회수했다. 원형을소급성공으로바꾸지않았다.

## 2026-10-15 Stage4ad~4af — 자연 문맥 QA와 기존 언어 보존의 동시 대조

### 1. 왜
기존 code4096/512 학생은 315/512로 첫값기준을 넘었으나 완결 root27/128·native+.2022가 남았다.
source512 세 팔은 자연 질문과 질문대상 이해가 약했다. 자료를 무작정 더 생성하기 전에
여러 표현의 정확한 문맥 대조를 학습하면서 기존 원문 예측을 함께 유지할 수 있는지 확인한다.
사용자 2026-10-15의 당일17시까지 자율 실험/절차/로컬커밋 허가로 실행한다.

### 2. 질문
같은 SFT 입력/부모/업데이트에서 native train CE의 가중치만 0/.25/1로 바꾸면
질문 대상 조회·형식/조건갱신과 원문 보존 사이에 더 나은 후보가 나오는가?

### 3. 예측·대안
replay가 원문 손실 악화를 줄일 수 있지만 SFT 학습을 늦추거나 QA 자체의 낮은 기반을 해결하지 못할 수 있다.
한 seed·작은 과제의 양성은 범용 지능/본75M 성공이 아니다. 비교한 대안은 ORPO 답쌍(믿을 수 있는 쌍 선결),
재귀/폭 변경(초기화/CLA/자료 교락)이며 가장 작은 현재 원인분리인 replay를 선택했다.

### 4. 단계·구현
- Stage4ad0W: CPU7 회귀와 새 코퍼스 동결. code binding4096 + 산수/논리/JSON/조건갱신1024 +
  기존 source512의 지원 QA512 = train5632. code dev/test는 분리 이름/root이고 test640은 최종에만 생성한다.
  이미 사용한 공개 val64는 개발용·교사 PSEUDO이며 의미 정답을 문자열로 판정하지 않는다.
- Stage4ad1W: 같은 새코드·코퍼스로 8업데이트 비용 측정; 체크포인트/품질 판정 없음.
- Stage4aeWa/Wb/Wc: 같은 원parent body/토크나이저/시드/행 순서·Adam5e-5/Muon2e-4·
  micro8accum16seq1024/ckptON/compiledefault/MTPoff/4pass176업데이트. native CE weight0/.25/1만 다르다.
  매 SFT128행 누적 뒤 별도 native8행의 동일 forward/CE를 모든 팔에서 계산한다.
  SFT effective batch128은 불변이나 보조 계산/실제 native 입력이 추가되므로 그것을 별도 분모로 보고한다.
- native는 기존 chat32 cache의 **train.bin**에서 1025토큰 단위로 서로 겹치지 않는1408개 창을 선택한다.
  한 팔 내 중복 사용0, 세 팔은 같은 창과 순서. 원cache는 읽기 전용이며 val은 학습하지 않는다.
- 매 epoch 같은 dev표본/CE/native첫32crop을 관측하며 최종 모델은 epoch4로 고정한다.
- Stage4afW: 세 팔 완료 뒤 parent와 세 최종 학생의 동결 code test640 실제 첫답을 수집한다.
  FP32math/cacheON/nativeK1/greedy64·재시도0. 공개 원천의 자유 답은 정답률과 분리하고 후행 판독한다.

### 5. 사전 판정
가중치0 대비 code 정확값·binding4view 일관성과 native CE 악화의 교환비를 보고한다.
Pareto 후보 탐색이며 통계 sigma 미측정/단일seed이고 기본 recipe를 자동 바꾸지 않는다.
숫자/JSON/유한 사실의 코드 정답만 채점하고 문자열 오조어 목록/온라인 의미 재시도는 사용하지 않는다.
자유 QA의 교사 문자일치는 현실정답률이 아니다. 실제 학생 앞답 기반 rollout은 이번 첫 비교와 별도다.

### 6. 비용·preflight
구현/CPU 후 비용8 실측으로 갱신한다. 세 팔 각15~30분, test약5분 GPU 추정이며 상한은 각3600초다.
실행 루프의 deadline은2026-10-15T08:00:00Z이고 그 뒤 추가 계산을 시작하지 않는다.
176×8×16×1024=23,068,672는 **padding 위치 상한**; 실제 SFT x/assistant는 encode 후 회수한다.
native 별도 입력/지도는 각1,441,792이고 weight0도 계산하지만 유효 native 학습 목적은0이다.
일반 사전학습의 pool≥2×와 다른 명시4pass SFT 진단이며 고유량을 반복 노출로 부풀리지 않는다.
태그 충돌/유사런은 check_run_registry로 확인했다. 기존source/binding실험에는 이 native train 보조 목적이 없었다.

### 7. 실행
run_P106B_Stage4ad0W_retention_course_cpu.sh → run_P106B_Stage4ad1W_retention_cost8.sh →
run_P106B_Stage4aeWa_sft_no_replay.sh / run_P106B_Stage4aeWb_native_replay025.sh /
run_P106B_Stage4aeWc_native_replay100.sh → run_P106B_Stage4afW_retention_sealed_test.sh.
구현은 새 diag_p106b_retention_course·p106b_retention_course·test 코드이고 제품 기본은 불변이다.

### 8. 한계
검증 이름은 이번 SFT에서만 분리되며 옛 사전학습에 없음을 보장하지 않는다. code 골드는 유한 생성 과제이고
공개 QA는 미확인 teacher/source 사실을 포함한다. train/val cache의 과거 누설 문제를 새로 감사한 것이 아니다.
기존75M×4 목표·미완 생산/본교육은 별도다. 보호 TinyDataset·설치·다운로드·원산출물 변경은 없다.

### 9. 실행 이력
현재 CPU7 통과·check-only 모델0, corpus/cost/train/test 실제 수행은 단계별 원형과 결과101에 회수한다.
최초4ad0의v1은CPU/동결만완료했다. 전수정적은 새module의직접진입bootstrap누락1건과
시스템python의numpy/torch부재3건을GPU전에찾았다. bootstrap수리후기능코드는같아도SHA가바뀌므로
원v1은보존하고새4ad0Wb에서v2를동결한다. 정적은정본tlm_torch Python으로다시검사한다.
실제v2도5632/704/640행으로동결했다. 최신17시허가를제시했어도auto-review가이전읽기전용지시를현재로판정해
GPUcost8을프로세스생성전두번거절했다. 모델/업데이트/CPT0, 세팔효과/test는NOT_RUN이며우회하지않는다.
CPU실측과원형2개·권한차단은[결과101 §114](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에기록한다.
재허가 후 같은 cost8이 실제 완료했고 첫 팔을 시작했다. 이 경과는 결과101§115에 누적한다.

### 추가 CPU 진단: 첫 답변 토큰과 추론 prefix
학습된 답변의 첫 글자가 마스크에서 빠지거나, 학습할 때의 질문 토큰이 추론 prefix와 다르면
질문대상 실패를 잘못 해석할 수 있다. 새 diag_p106b_token_boundary는 같은 동결 자료의 각 assistant턴에서
첫 답변을 포함한 본문 문자 지도와 prefix 토큰의 일치를 전수 비교한다. 원문/모델은 변경하지 않는다.
약1분 CPU·모델0이며 누락/불일치0이 기술 기준이다. 통과해도 실제 gradient/정답성을 증명하지 않는다.
이는 기존 마스크 회귀와 다른 실제 tokenizer 경계 검사이며 세 팔의 동결 코드는 수정하지 않는다.

완료된 code test의 CPU집계는 같은 실제 질문/gold를 키로대조하고언어/과제별semantic root를재표집한다.
4view를문항독립표본으로세지않으며2000회·고정seed20261015의조건부95%구간을함께기록한다.
이는고정된한seed모델과현재생산과제의기술통계이며학습seed sigma/아키텍처검정/범용지능을대신하지않는다.
별도CPU3 fixture로동일모델0차이/전량개선/불일치·미채점거부를검산한다.

## 2026-10-15 조건부 Stage4ag~4ai — 코드로 확인한 정답과 오답의 직접 대비

### 1. 왜
replay 세 팔은 원문 보존을 먼저 가르지만 질문 대상의 무시를 직접 겨냥한 목적은 아니다.
첫 기준 팔의 개발 표본에 같은 값 선택이 남았고 실제 tokenizer7296턴의 본문지도/prefix불일치는0이었다.
기존 세 팔의 전체 결과를 먼저 회수하고, 대상 무시가 남으면 질문별 정답/오답 대조를 추가 검증한다.

### 2. 질문
같은 SFT/native 자료와 부모에서, 코드가 아는 정답과 다른 대상의 값 또는 요청하지 않은 반복을
완성 답 단위로 구별하도록 가르치면 자유 생성의 대상 선택과 종료가 개선되는가?

### 3. 예측과 대안
문항별 구별 신호가 도움이 될 수 있지만 좁은 과제만 외우거나 native 손실이 더 악화할 수 있다.
대안은 같은 자료의 추가 노출(시간/망각), 교사 자료 확대(원천폭/생성비용), 정답-오답 대조(선택)다.
정답 근거를 코드가 소유하는 범위에서만 마지막 안을 선택한다. 공개 자유 QA의 오답을 추정하지 않는다.

### 4. 방법과 단계
[ORPO 원문](https://arxiv.org/html/2403.07691v2) §4.1~4.3 식3~7을 읽었다.
답 길이로 정규화한 로그확률에서 chosen/rejected의 log-odds 차이에 logistic 손실을 적용한다.
우리 쪽은 기존 토큰정규화 SFT와 native replay를 유지하므로 논문 전체 recipe 재현이 아닌 조건부 확장이다.
일반 softmax CE도 오답 로짓에 gradient를 주며, 여기서는 특정 오답 완성문과의 추가 대비를 시험한다.

- Stage4ag0W: CPU8 회귀와 별도 pairs/test 동결. 반드시 기존 replay 세 팔/test 회수가 먼저다.
- producer가 직접 만든 질문의 원문 hash와 재생성한 계약이 맞는4096행만 pair를 만든다.
  wrong_target은 같은 자료의 다른 대상 값, unrequested_repeat은 한 답 안에서값을두번반복한것이다.
  유효한 단일 정답을 여러 답안 칸에 똑같이 쓴 경우나 정상 반복 요청은 대상이 아니다.
  공개 QA·자유 생성·불명 유형은 pair 생성 자체를 금지한다. 온라인 검수/재생성/문구목록을 추가하지 않는다.
- 같은 SFT5632/176업데이트·원부모·micro8accum16/ckptON·LR5e-5/2e-4·4pass를 유지한다.
  native 강도는 앞의 개발 결과로.25/1중하나를 명시해 동결하며 기존 본체에서 세 팔을 새로 시작한다.
- Stage4ag1W 비용8 뒤 Stage4ahWa/Wb/Wc: 추가 대조 가중치0/.1/.3만 다르다.
  모든 팔에서 같은16pairs/update의chosen/rejectedforward를 계산하고weight0만추가gradient0이다.
  추가 입력/지도 계산·실제 pair수·native 입력과 SFT 노출을 각각 공개한다.
- Stage4aiW: 새 이름/사실관계와 새 규칙 root의640문항을 최종에 처음 생성해 부모/세학생을 비교한다.
  앞 세 팔의test는 후속선택에사용했으므로 이제개발자료다. 새로운test도 세계정답/범용벤치는아니다.
- 추가 Stage4ahWd는 같은 계산에서 정답만NLL.3으로추가강화하는대조다. 따라서후속은총4학생팔이다.
  대비효과가단순정답강화인지구별하기위한보조이며ORPO.3과gradient크기가정확히같다는뜻은아니다.
  Stage4ai의최종수집은parent+4학생이고개별원답/정확값/원문손실을분리한다.
- 자체 한국어 색상 질문의 조사 결합 오류도 확인했다. 기존v2는 보존하고 이번 새코퍼스에서만
  등록된 color 질문의 조사를 고친다. 공개/교사 문장을 검사하거나 교정하는 규칙이 아니다.
  입력/토큰량이 달라질 수 있어 앞 replay 팔과의 차이는 단일 목적효과로 해석하지 않는다.
  새 네 팔끼리는 같은 수정 자료이며 실제 토큰은 다시 encode해 동결한다. 영어에도 대상무시가 남아
  이 한국어 오류만으로 전체 실패를 설명하지 않는다.

### 5. 판정
정확한 값·4view 일관성·반복/상한·원문 CE를 따로 본다. 새β0과비교해야하며예전루프와직접효과를섞지않는다.
단일 seed·계열 sigma 미측정으로 관측/Pareto 후보까지만보고하고기본모델을자동바꾸지않는다.

### 6. 비용
CPU 약1분, 비용8 약2분, 세 팔 각10~20분·전체test약5분 GPU 추정이다. 실제 비용8 뒤 갱신한다.
신규reference모델·헤드·다운로드는 없고 기존모델/입력은 읽기만한다.17시 이후새실험을시작하지않는다.

### 7. 구현과 실행
별도 p106b_conditional_orpo·diag·CPU test 코드다. 현재CPU8통과·세팔수행은앞선replay결과에조건부다.
동결 전 전수정적과 직접진입을 확인하고, 구현이 준비된 뒤 독립 SH를 등록한다.

### 8. 한계
확정적 가상 매핑만 negative를 알 수 있다. 현실 답의 정답성·일반 반복판정·모든 유형 보호를 보장하지 않는다.
선호학습과native보존이충돌할수있고작은과제의개선을본75M/300M이나공유/재귀의해결로승격하지않는다.

### 9. 상태
최초 조건부 준비 기록 이후 CPU11·동결·비용8·새 네 팔 각176업데이트·부모 포함 새640첫답을 실제 완료했다.
전체 정확값은 beta0/.1/.3/정답추가가300/301/296/302, 대상조회는260/260/254/262다.
기준 대비 구간이 모두0을 포함하고 4view 일관성도 개선되지 않아 현재 recipe는 비채택으로 보존한다.
대상 구별이 좋아질 수 있다는 예측은 이번 설정에서는 지지되지 않았다. 원형·쌍별 조건은 결과101§117/120이다.

## 2026-10-15 Stage4aj — 기존 자료와 겹치지 않는 새 교사 QA 블록

### 1. 왜
작은 규칙 과제만으로 실제 질의응답의 범위를 늘렸다고 할 수 없다. 기존 자료의 문맥 전달을 유지하면서
새 원천512train/64val을 보완하고, 후속 실제 학습의 자료로 보존한다. 본75M 목표를 이 블록으로 축소하지 않는다.

### 2. 질문
이전736개 동결 원천과 원문 단위가 겹치지 않는 새 공개 원천을 확보하고,
교사만 보던 정보가 학생에게 빠지는 일을 줄인 자료를 만들 수 있는가?

### 3. 대안·예측
선택span만전달(작지만필수전제가빠질수있음), 전체의길이를제한한원문전달(선택),
교사가질문을완전히독립문장으로다시작성(생성비용/의미변형)의세방향을비교했다.
전체자료를보여줘도원문사실오류/모호질문이남을수있다. 형식완결을정답성으로올리지않는다.

### 4. 단계
- Stage4aj0W CPU3/공급재고: 기존736원천root와긴본문SHA를제외하고새lane의공급을검산한다.
  원문전체512토큰이하는학생seq1024에서질문/답/태그의여유를둔예비예산이다. 문자수기준/불량판정이아니다.
- Stage4aj1W: 같은코드·같은source선택SHA의새736deck(예비160포함)을동결한다.
- Stage4aj2W: 기존Gemma12B/MTP ON·sampler1.0/.95/k64/minp0/repeat1/presence0,
  ctx8192/총출력3072/thinking1024로576원천을생성한다. 학생과동시상주하지않는다.
  교사는QUESTION/ANSWER/NOTE와SOURCE_IDS를쓰고JSON/ChatML은코드가만든다.
  코드가선택ID뿐아니라예산안의원source전체를학생질문에붙인다. 원문지시는인용DATA이며관리명령이아니다.
  구조/토큰오류에만총3시도, 잘못된문구목록·온라인의미판정/재생성은없다.
- Stage4aj3W: 지원QA512/64만직렬화한다. 자료요청고정문장을절반추가하지않는다.
  원형·사고·선택ID·전체입력·원문계보를보존하되사고/NOTE는학생target에넣지않는다.

### 5. 판정
새원천과기존root/긴본문교차0·학생에전달한원문byte·최종역할/토큰예산을확인한다.
source그룹균형과토큰언어비는다르다. 내용은PSEUDO로보존하고후행표본판독과실제학생평가로확인한다.
새전체입력은이전선택span보다길수있어x/s상승을교사추론가속으로해석하지않는다.

### 6. 비용
CPU재고약1~5분추정. 교사비용은이전576의83분을참고해약1~2시간으로예상하나새표본에서는미측정이다.
max7200초와당일17시전600초정리여유중작은쪽을사용한다. 실제생성/학생학습시간은분리회수한다.

### 7. 구현
독립diag_p106b_source_expand·CPU3·새namespace p106b_source_expand_v1_s1337이다.
기존source code/코퍼스를수정하지않고현재프로세스범위의경로/입력필터/원문전달만확장한다.

### 8. 한계
과거pretrain/번역의의미중복없음을보장하지않는다. 원문오류/권리의독립확인·교사정답성·본75M/300M은별도다.
보호TinyDataset/사전·다운로드·기존산출물변경·외부게시를하지않는다. 모든새JSONL은20MB이하로분할한다.

### 9. 상태
코드/CPU3준비. 새원천공급·교사생성·지원코퍼스는실제실행뒤결과101에회수한다.
첫 v1의 CPU3와 공급재고는 완료했고 교사/코퍼스는 아직0이다.
생성 전 점검에서 assistant 우선 span 목록을 그대로 붙이면 원래 대화 순서가 바뀔 수 있음을 확인했다.
새 v2는 원문 message index와 문장 offset 순서를 보존한다. 이전 자료는 수정하지 않는다.
v1 코드와 재고는 Git7d7957d에 보존하고 새4aj0Wb에서 CPU4와 공급을 다시 검산한다.
v2 CPU4/새736 공급/동결은 실제 완료했고 결과101§119에 회수했다. 아직 교사와 학생0이다.

## 2026-10-15 Stage4ak — 답변 직전 표현의 제한된 판독 진단

### 1. 왜
replay 이후에도 질문 대상이 아닌 값을 고르는 현상이 남았다. 본체가 대상 정보를 구별하지 못하는지,
마지막 어휘 투영에서 읽지 못하는지에 따라 다음 수리의 위치가 다르다. 자유 생성과 별개 진단이다.

### 2. 질문
같은 부모·replay100·조건부 pair030의 답변 직전 표현에서, 작은 별도 분류기가 지정된 값을 읽을 수 있는가?
마지막 768차원 표현과 공유 어휘 앞의 256차원 투영을 비교한다. 입력에는 정답 본문을 넣지 않는다.
정답이 들어 있는 원문 사실은 보이지만 assistant 정답 본문은 추가하지 않는다는 뜻이다.
차원 수와 판독기 크기의 교락을 줄이기 위해 고정 seed의 무작위 직교256투영도 CPU 대조로 둔다.

### 3. 예측과 대안
추가 SFT 또는 저랭크 출력 수리보다 먼저 동결 표현을 읽는 진단을 선택한다. 비용과 원형 변경이 작다.
분류기가 높아도 본체가 그 정보를 실제로 사용한다는 인과 증거가 아니며, 분류기 자체가 과제를 배울 수 있다.
[Hewitt·Liang의 통제 과제 연구](https://aclanthology.org/D19-1275/)의 경고를 반영해 작은 선형/16폭 판독기,
훈련 라벨 셔플 대조, 새 이름·root의 평가, 첫 값/상수 기준선을 함께 둔다. 논문의 통제 과제를 그대로 재현하지는 않는다.

### 4. 단계
- Stage4ak0W: 모델 없는 CPU 계약 회귀. 질문 prefix에 답 본문이 없는지, 그룹/라벨/분할이 명확한지 검사한다.
- Stage4ak1W: 앞 네 팔의 자유 생성 수집이 끝난 뒤 parent/replay100/pair030을 차례로 읽는다.
  code binding train4096/dev512/fresh test512만 사용한다. 같은 실제 prefix 길이·batch1·cacheON·
  FP32 math/TF32 OFF에서 마지막 hidden768과 emb_up 투영256을 수집한다. 원모델 optimizer/CPT 저장은 없다.
  매 모델의 state SHA를 앞뒤 검산한다. 캐시는 HF의 별도 namespace에 두고 파일마다20MB 미만으로 나눈다.
- Stage4ak2W: CPU에서 언어×과제별 6값 분류기를 학습한다. train 평균/표준편차만으로 정규화하며,
  선형 또는 폭16 MLP·Adam LR.01/weight_decay.01·최대500회, 20회마다 dev CE로 종료점을 고른다.
  test는 선정 뒤 한 번 읽는다. 훈련 라벨 셔플 대조도 같은 계산/선정 절차이며 test의 실제 정답은 바꾸지 않는다.
  hidden768/실제 projected256/무작위 직교256에서 같은 판독기 절차를 쓴다.
  추가로 논리 층0/3/7/10/13의 마지막 prefix 위치도 읽기 전용 hook으로 수집한다.
  방문 스케줄은 dense14의1회 순차 방문인지 검산하고 KV owner도 기록한다. hook이 로짓을 바꾸지 않는 CPU 회귀를 추가한다.
  이 관측은 어느 깊이에서 정보가 읽히는지의 단서이며 층 제거/반복 원인의 인과 증거는 아니다.

### 5. 판정
정확값·같은 root의 양순서/양대상 4문항 모두 맞음·상수/첫값 기준선을 보고한다.
어휘 병목 전후의 판독 차이는 관측이지 병목의 인과 증명이 아니다. 후보 6개 분류를 TinyLM 자유 답변 점수로 합치지 않는다.
이미 읽은 앞 test는 후속 설계의 개발 자료이며, 이 진단을 새 범용 벤치마크라고 부르지 않는다.

### 6. 비용
CPU 회귀 약1분, GPU 수집 세 모델 합계 약5~15분 추정/상한900초, CPU 판독 약1~5분 추정이다.
교사와 학생 모델은 동시에 올리지 않는다. CPU 판독은 교사 GPU 생성 중 수행할 수 있다.

### 7. 실행
독립 diag_p106b_prefix_probe·test와 Stage4ak0/1/2 SH를 작성한다. 제품 모델 코드는 수정하지 않는다.

### 8. 한계
한 seed·가상 6값 과제·작은 판독기이며 범용 이해/공유 MLP/재귀 원인이나 실제 사용자 답변 개선을 증명하지 않는다.
규칙 과제를 해독하는 별도 헤드를 제품 기본으로 채택하지 않는다. 본75M/300M 목표는 유지한다.

### 9. 상태 및 preflight
2026-10-15 07시대 사전 설계. 새 tag p106b_prefix_probe_v1_s1337 레지스트리 충돌 없음.
본체 학습토큰0·부모/토크나이저 동일·가중치 읽기 전용이며, 판독기만 CPU에서 학습한다.
실제 수집/판독은 준비와 CPU 검증을 마친 뒤 현재17시 승인 안에서 수행한다.
CPU5에 유한성 방어와 층별 관측 회귀를 추가한 최종 CPU6도 통과했다.
07:25에 실제 세 모델 읽기 전용 수집을 시작했다. 종료 원형과 파생 판독은 새 결과 절에 회수한다.
첫 실행은 CPU에서 만든 추론 캐시가 GPU 이동을 따르지 않아 첫 forward에서 종료1이었다.
이는 독립 진단 코드의 배치 순서 오류이며 기존 학생 학습/생성 코드의 실패를 뜻하지 않는다.
v1 특징/optimizer/CPT는0이고 원형과 전체코드는 복구 JSON에 보존한다.
Stage4ak0Wd CPU7에서 이동→캐시 동결 순서를 추가 검증하고 새v2/Stage4ak1Wb로 실제 재시험한다.
새v2의 실제15,360prefix 수집은220.314초·세 모델 state SHA 불변으로 완료했다.
CPU384개 판독은133.423초로 완료했으나 마지막 선형236/251/246 대 첫값256으로 질문대상 회복을 못 보였다.
어휘 투영만의 원인이나 새 헤드 채택으로 승격하지 않고 결과101 후속 절에 기록한다.

### 추가 Stage4ak3W — 같은 특징의 값 읽기와 대상 연결 분리
추가 GPU 없이 이미 동결한 특징을 사용한다. 실제 원천/정답/prefix SHA로 원행과 조인한 뒤
원래 requested value6값, 첫 사실의 value6값, 질문 대상이 첫 사실인지2값을 각각 CPU 선형 판독한다.
마지막768/어휘 앞256/논리 층7·10에서 같은 train-only 정규화·LR.01/decay.01·500회/dev20회 선정을 유지한다.
특정 층을 점수에 맞춰 추가 선택하거나 새로운 품질 PASS 문턱을 만들지 않는다.
값 두 개가 남았더라도 그중 묻는 대상과 연결하지 못하는지 확인하는 관측이며, 정보를 전혀 저장하지 않았다는 증명은 아니다.
비용 CPU 약2분/상한600초·원모델/교사 호출0·새 본체 학습/CPT0이다. 새 진단 코드/CPU 회귀 후 실행한다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 2026-10-15 Stage4al~4an — 추론에 남기지 않는 대상 연결 보조 학습

### 1. 왜
동결 표현에서 replay 학생의 첫 값512/512·마지막 값510/512는 읽혔지만 요청한 값은251/512였다.
같은 특징의 asked-first 판독은309/512였다. 이 관측은 값의 흔적과 대상 연결을 구분해야 함을 보여 주지만
전체 이해 부재나 특정 층의 인과를 증명하지는 않는다. 새 자연 QA 자료는 별도로 생성 중이다.

### 2. 질문
기존 자유 생성 SFT/native 학습에, 코드가 아는 질문 대상이 첫 사실인지 둘째 사실인지를 보조로 가르치면
**보조 판독기 없이** 새 질문에 대한 TinyLM 자체의 답 선택이 나아지는가?

### 3. 예측·세 대안

| 안 | 예와 방법 | 장점 | 위험/비용 |
|---|---|---|---|
| A | 학습 이름/개념을 더 넓혀 같은 SFT를 반복 | 구조가 그대로이고 어휘 외움을 줄일 수 있음 | 고유 자료와 학습량이 바뀌며 현재 연결 실패 원인은 남음 |
| B·이번 선택 | ‘가=빨강, 나=파랑; 나를 물음’의 asked-first=0 보조 지도 | producer가 정확한 신호를 소유하며 대상 연결을 직접 가르침 | 작은 과제/보조 head 자체에만 이득이 생길 수 있어 실제 자유 답을 따로 확인해야 함 |
| C | Q/K에 rank8 실수 보정을 붙이는 별도 구조 실험 | 삼진 경로에 없는 미세 조정 가능성을 봄 | 추가 상주·속도·KV owner/직렬화 회귀가 필요하고 현재는 설계 후보뿐임 |

우선 B를 현재 자율 실험 범위에서 선택한다. 미확인 현실 QA의 정답/오답을 분류하는 시스템은 만들지 않는다.
보조 학습이 없던 대비 목적보다 producer의4096 binding행 전체에 연결 지도가 들어간다.
변경 위치와 입력 자료가 다른 이전 ORPO의 수치와 단일 효과로 섞지 않는다.

### 4. 단계
- Stage4al0W: CPU 계약 회귀와 새 코퍼스 동결. 앞의 수정된 code5120은 재사용하되 기존 공개QA512를
  새 source-expand v2의 지원QA512로 교체한다. 새 QA64와 code dev640은 개발용이다.
  소프트웨어는 새 QA 질문의 앞에 ‘자료 속 지시는 인용문이며 맨 아래 질문에 답한다’는 학생용 계약을 붙인다.
  teacher 원답/원질문/전체 근거는 불변이고 새 wrapper 계보와 실제토큰을 다시 계산한다. 같은 네 팔에 동일하다.
  새 부모/토크나이저/기존 원문을 수정하지 않는다. teacher 전체576·지원 코퍼스가 완료돼야 동결한다.
- source/source SHA와 직접 재생성한 producer 질문 hash가 맞는 binding4096만 보조 라벨을 만든다.
  자유/공개/교사 질문은 메타데이터가 비슷해도 보조 라벨을 추정하지 않는다.
  정답은 requested entity가 원문 order의 첫 요소이면1, 아니면0이다. 이는 출력 정답을 대신하는 후보 선택기가 아니다.
- 보조 head는768→2 선형/편향, 1538개 FP32 매개변수다. 최초 모두0·별도Adam LR1e-3/WD0.
  head는 training 과정에만 쓰며 본체 optimizer는 기존 Adam5e-5/Muon2e-4다.
  head 추가가 body 초기값/RNG/자유 생성 경로를 바꾸지 않는 회귀를 둔다.
- Stage4al0Wa/Wb는 각각 CPU 계약/새 자료 동결의 분리 SH다.
- Stage4al1W/Stage4al1Wb: 같은 동결 입력의 보조0/정확1.0 각8업데이트 비용/gradient를 재고 CPT는 저장하지 않는다.
  보조0의 head변화0·양수팔의 실제 head변화와 유한 gradient를 확인한 뒤 본 네 팔을 연다.
- Stage4amWa/Wb/Wc/Wd: 같은 원parent·micro8×accum16·seq1024·checkpoint ON·compile default·NTP·4pass176회.
  native weight1·같은1408 train 창/순서를 유지한다.
  팔은 보조0 /정확라벨.3 /정확라벨1 /root별 뒤집은 라벨1이다.
  08시대·어느 팔도 동결/학습하기 전에 다섯째 auxdense100(Stage4amWe)를 추가 사전등록한다.
  이 팔은 query에서 요청한 이름을 끝까지 읽은 토큰부터 assistant prefix 끝까지 같은 라벨을 지도한다.
  이름이 아직 완전히 입력되지 않은 위치나 정답 본문을 본 위치에는 라벨을 주지 않는다.
  UTF-8 하위 토큰의 겹친 문자 offset은 해당 이름과 겹치는 마지막 토큰을 시작점으로 삼아 검사한다.
  각 행의 suffix 평균을 낸 뒤 전역 binding행 수로 정규화한다. 이름 뒤의 긴 문장만 과대 가중하지 않는다.
  모든 팔에서 같은 suffix head forward를 계산하고, 기존 네 팔은 마지막 prefix 위치에만 손실을 준다.
  어휘 SFT 마스크는 불변이지만 dense 팔의 별도 분류 지도는 user-prefix 끝부분도 포함한다.
  뒤집음은 고정 hash로만 정하며 각 root의 2대2 라벨 균형은 유지하지만 약절반의 의미가 틀린 별도 통제다.
  일반 데이터셋의 오답을 만들거나 이런 신호를 본75M 자료에 합치지 않는다.
- 보조 CE는 각 행의 **첫 assistant 목표를 예측하는 prefix 위치**에서만 계산한다.
  뒤에 있는 정답 본문을 판독 입력에 넣지 않도록 causal 경로와 tokenizer 경계를 회귀로 확인한다.
  전역 update의 binding행 수로 정규화하고, 원래 SFT는 전역 assistant 토큰 수로 정규화한다.
  모든 팔은 같은 보조 forward를 계산하며0팔만 그 gradient가0이다.
- Stage4anW: 네 팔 완료 후 새 이름/root의 code640 첫 답과 새 자연QA val64 중 사전고정16답을 수집한다.
  추가 후 실제 수집의 선결은 **다섯 팔 전체 완료**다. 어느 팔도 결과를 보고 사후 선택하지 않는다.
  자연 QA는 언어×가족8층의 각2원천을 root SHA 순서로 고정하며, 전체64의 CE와 별개인 개발 표본이다.
  code는 greedy64·자연QA는 greedy256(전체prompt 뒤 모델context 여유가 작으면 그 cap을 공개)로 조건을 고정한다.
  실제 생성에서 보조 head를 사용하지 않는다. code 골드/교사 문자일치/후행 문맥 판독/native CE를 분리한다.
  기존 고정8질문도 같은 원형 규약의 greedy160 첫답/조건부 최대3시도를 분리 수집한다.
  이8개는 여러 번 사용한 개발용 진단이지 독립 벤치마크가 아니다. teacher 데이터 생성의 재시도 규약과는 별개다.
  final640의 update 중 한영각2개는 기존 probe helper로 실제 앞 답을 넣은4대화도 따로 수집한다.
  GOLD_HISTORY 최종턴과 실제 모델의 앞 답을 받은 최종턴을 구분하고, 이4개를 새 독립 문항으로 중복 합산하지 않는다.
  이미 읽은 앞640은 후속 설계의 개발 자료이며 이번 final640으로 재사용하지 않는다.

### 5. 판정
보조 분류 점수가 아니라 **실제 자유 생성의 정확값·4view 일관성·새 자연QA의 답·native CE**를 본다.
보조0과 정확.3/1 및 뒤집음1의 같은 입력 대조에서 효용을 확인한다. 단일seed·범용 sigma 미측정이다.
새 QA는 PSEUDO이고 코드의 주장이 세계 정답률로 바뀌지 않는다. 기본 recipe/배포를 자동 채택하지 않는다.

### 6. 비용
CPU 회귀/동결 수분·비용8 약1~2분·네 팔 각10~20분·실제 첫 답 약15분 GPU 추정이다.
공개16과 기존8 진단을 포함한 최종 생성은20~30분 추정/상한1800초로 갱신한다.
다섯째 팔 추가 후 양수 suffix 비용8도 먼저 확인하며, 전체 학습 예상은5×10~20분으로 갱신한다.
teacher와 동시 적재하지 않으며 새 QA 완료 뒤 GPU가 비어 있을 때만 실행한다.
1538×4=6152바이트는 보조 head 매개변수일 뿐 optimizer/gradient/활성값·실제 peak는 별도 측정한다.
추론 때 head를 제거하므로 배포 모델에 6152바이트가 남는다고 하지 않는다.
실제 실험 CPT에는 재현용 훈련 부록으로 head state를 보존하지만 본체 model state/추론 경로에는 넣지 않는다.
별도 배포 export나 packed 크기/추론 가속은 이번 단순 개수 계산으로 증명하지 않는다.

### 7. 구현
새 p106b_binding_auxiliary·독립 diag/test 및 위 각 SH를 준비한다.
제품 config/transformer/추론·기존 frozen 코드·환경/검사기는 수정하지 않는다.

| 단계 | 정확한 SH | 실행 선결 |
|---|---|---|
| Stage4al0Wa | run_P106B_Stage4al0Wa_binding_aux_cpu.sh | 최초 CPU10; 실제 원형 보존 |
| Stage4al0Wc | run_P106B_Stage4al0Wc_binding_aux_final_cpu.sh | 메타계보/학생계약/공개표본 cap을 포함한 최종 CPU13 |
| Stage4al0Wd | run_P106B_Stage4al0Wd_auxiliary_cli_cpu.sh | 보조14+factor CLI2·부재 선결은 모델 호출 전HOLD8 |
| Stage4al0Wb | run_P106B_Stage4al0Wb_binding_aux_corpus.sh | 새512/64 source corpus 완료 |
| Stage4al1W | run_P106B_Stage4al1W_binding_aux_cost8.sh | 같은 새 corpus |
| Stage4al1Wb | run_P106B_Stage4al1Wb_binding_aux_positive_cost8.sh | 같은 새 corpus·양수 gradient 경로 |
| Stage4amWa | run_P106B_Stage4amWa_binding_aux_zero.sh | 양 비용8 완료 |
| Stage4amWb | run_P106B_Stage4amWb_binding_aux_correct03.sh | 양 비용8 완료 |
| Stage4amWc | run_P106B_Stage4amWc_binding_aux_correct100.sh | 양 비용8 완료 |
| Stage4amWd | run_P106B_Stage4amWd_binding_aux_permuted100.sh | 양 비용8 완료 |
| Stage4anW | run_P106B_Stage4anW_binding_aux_fresh_test.sh | 네 팔 완료·각CPT SHA |
| Stage4al0We | run_P106B_Stage4al0We_causal_suffix_cpu.sh | suffix 문자/토큰 경계·뒤 시점 금지·행별 정규화 |
| Stage4al1Wc | run_P106B_Stage4al1Wc_suffix_positive_cost8.sh | 같은 새 corpus·suffix 양수 gradient 경로 |
| Stage4amWe | run_P106B_Stage4amWe_binding_aux_causal_suffix.sh | 세 비용8 완료·같은176회 |

### 8. 한계
새 teacher QA 교체는 이전 팔과 자료가 다르므로 이전 ORPO나 replay와 순수 목적 차이라고 해석하지 않는다.
같은 새 네 팔 사이에서만 목적/라벨의 효과를 비교한다.
역할/형식/기초 QA의 개선은 본75M/300M 완료나 공유 MLP/재귀 문제 해결을 뜻하지 않는다.
자료/보조 label수·SFT x/assistant·native 입력·추가 head 계산·padding 위치를 분리 보고한다.

### 9. 사전 점검·영향 범위
새tag p106b_binding_aux_v1_s1337은 조회 충돌이 없고, 기존 실험에는 이1538개 연결 보조 목적이 없다.
176×8×16×1024=23,068,672는 padding 위치다. 실제 x/지도는 새 자료를 encode한 뒤 동결한다.
4pass 소형 SFT 진단이므로 사전학습의 pool≥2× 규칙을 고유세계지식량으로 오용하지 않는다.

| 영향 축 | 실제 범위/보호 |
|---|---|
| 코드 | 신규 실험3파일/SH만; 기존 제품/동결 모듈 호출 계약 불변 |
| 데이터 | 새 namespace의 code+새 QA 혼합/라벨 sidecar; 기존 teacher/corpus/native 원본 읽기 전용 |
| 시험 | 잘못된 producer·첫 목표 위치·뒤집음 균형·전역 분모·gradient0·body/head/RNG 분리 회귀 |
| 정본 문서 | P106B/결과101·색인·기준표·방법론·COMPASS·WIP/인계를 단계별 회수 |
| 부채·우선순위 | 학습 전용 분류를 제품 기본으로 넣지 않으며 효과 없으면 비채택 기록; teacher 생산은 중단하지 않음 |
| 권한/소유 | 현재17시 승인 안의 신규 모델/CPT만; 보호 원천·원산출물·타WIP·외부 게시 제외 |
| 비교/증거 | 같은 네 팔의 실제 입력/초기화/토큰/평가 대조; CPU·보조 분류·실제 자유 답을 분리 |

현재는 **설계/준비**이고 실제 학습 효과는 미실행이다. 알려진 설계 실수를 점검한 것이며 실제 효용은 실행으로 확인한다.

### 10. 관련 문헌과 차용 범위
[ICML2025 변수 연결 연구](https://arxiv.org/html/2505.20896v2)의 과제·훈련·개입 및 부록E를 읽었다.
단순 앞 문장 휴리스틱이 일반 Transformer에도 생길 수 있지만, 해당 문자 tokenizer/untied embedding/긴 훈련을
우리 원인이나 필요 스텝 수에 그대로 대입하지 않는다.
[EMNLP2021 보조 시퀀스](https://aclanthology.org/2021.emnlp-main.505.pdf) §3.2~3.3의 중간 구조 지도 아이디어를 참고한다.
그 논문은 추론에서도 보조 시퀀스를 쓰는 seq2seq 방법이고, 우리는 추론에 쓰지 않는 분류 손실이므로 재현이 아니다.
문헌의 높은 정답률을 TinyLM 실측이나 기대 수치로 복사하지 않는다.


이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 2026-10-15 Stage4ao~4ap — 원문 메시지의 공백까지 보존하는 교사 입력 복구

### 1. 왜
생성 중 v2의 저장 표본을 후행 판독하면서 실제 YAML 원문의 들여쓰기가 span.strip 과정에서 사라짐을 확인했다.
원문 user의 네 칸/여덟 칸 들여쓰기는 남아 있지만, 교사/학생에 전달한 줄 조각은 평탄했다.
이는 오조어/정답의 의미 필터가 아니라 **입력 직렬화 결함**이다. v2 원형과 진행 중 코드는 수정하지 않는다.

### 2. 질문
원문 canonical 메시지를 role·공백·줄바꿈 그대로 양쪽에 전달하고 JSON/학생 포장은 코드가 맡기면
형식 정보를 잃지 않는 새512/64 QA를 만들 수 있는가? 새 계약에서 thinking256/1024의 공급 비용은 어떤가?

### 3. 세 대안·선택
| 안 | 내용 | 장점 | 위험/비용 |
|---|---|---|---|
| A | 학생 입력만 원문으로 재포장 | 교사 재호출이 없어 빠름 | 교사는 이미 형식을 잃은 자료로 답했으므로 입력/정답의 관계가 달라질 수 있음 |
| B·선택 | 같은 원천에서 새 lossless 교사 입력으로 전량 재생성 | 비교·계보가 명확하고 두 입력의 원문 내용이 모두 보존됨 | 교사 약1~2시간 추가, 기존 출력도 계속 보존 |
| C | 들여쓰기/코드블록 등의 일부만 골라 교정 | 재호출을 줄일 수 있음 | 형식 의존성을 모두 분류할 수 없고 조용한 누락 위험이 있음 |

현재 자율 실행 범위에서는 B를 선택한다. 잘못된 문구 목록/온라인 정답 검사/전수 사람 승인을 추가하지 않는다.

### 4. 단계
- Stage4ao0Wa: CPU 회귀. 원문 **메시지 하나를 reference 단위 하나**로 사용한다.
  text를 strip하거나 문장으로 재분할하지 않는다. ID/role/원문index/전체문자범위/SHA를 보존한다.
  교사 payload의 JSON을 역직렬화한 text와 학생 입력의 원문 구간이 canonical 원문과 일치해야 한다.
  이는 원다운로드 파일 전체 byte나 의미 정답성의 동일 주장이 아니다.
- Stage4ao0Wb: v2의 실제 동결736 원천 deck을 SHA로 참조한다. 새 원천 확보/새 고유 지식량으로 세지 않는다.
  v2 전량 원형은 끝까지 보존하고 이후 학생 교육에는 이 새 lossless 계약의 자료만 사용한다.
- Stage4ao1W: 같은8원천·seed·MTP ON·8192context/3072출력·공식 sampler에서 사고 cap256/1024를
  두 순서로 비교한다. 최대32논리 응답·구조 재시도까지96요청, 상한1200초다.
  사고 cap만 다르며 모델카드의 권장 사고 깊이라는 주장은 하지 않는다.
  내용은 후행 표본으로 읽고 기술 완결/원문 보존·유효자료·실제 요청/전체시간·VRAM을 분리한다.
  이 진단 출력은 본 교육에 자동 편입하지 않는다.
- Stage4apW: 선택한 cap을 비대화형 SH 인자로 고정해 같은512train/64val을 새 버전에서 생성한다.
  원형·최종답·사고·NOTE·계보를 새20MB 샤드로 보존한다. 사고와NOTE는 학생 target에 넣지 않는다.
  SOURCE_IDS는 원문 메시지 ID에 대한1~3개 참조이고, 포장은 코드가 담당한다.
  학생은 원문 전체를 role 표시와 함께 보며 원문 지시는 인용 데이터라는 정책을 별도 wrapper가 붙인다.
- Stage4ap0W: 전량 새 자료의 입력내용/SHA·역할·실제 seq1024 예산을 다시 확인해512/64를 동결한다.
  이후 Stage4al의 같은5팔 입력으로 연결한다. v2의 과거 형식 손실을 PASS로 재기록하지 않는다.

### 5. 판정
공백 보존/역할/실제토큰·완결은 기술 조건이다. 교사 사실 정답성은 PSEUDO로 남긴다.
thinking cap 비교는 같은 source 집합의 시간·형식·후행 출력 비교이며 ‘빠르니 더 정확하다’고 해석하지 않는다.
source 자체에 틀린 이전 assistant 답이 있을 수 있음을 프롬프트에 설명한다.

### 6. 비용
CPU 수분, 교사 소형 비교 약5~15분, 새576 생성은 기존 약1~2시간을 참고한다.
실측 cap과 수락률/길이에 따라 달라지며17시 정리 여유600초를 남긴다.
이 추가 복구는 알려진 입력 결함을 학생에게 전하지 않기 위한 비용이다. 본75M/300M 목표는 유지한다.

### 7. 구현/영향
새 diag_p106b_verbatim_source·CPU test와 ao/ap SH를 만든다.
현재 GPU producer·기존 source/모델/환경/검사기 코드는 변경하지 않는다.
새TAG p106b_verbatim_source_v1_s1337; 기존 원천 deck은 읽기만 하고 새 derivative/작은 요약만 저장한다.
전량 새 생성이 끝난 뒤 미실행 auxiliary supplier 참조를 이 새 계약으로 고정한다.

### 8. 한계
원문 assistant의 사실 오류/서로 모순된 원문까지 해결한 것은 아니다.
이미 source를 재활용한 제어 실험이므로 v2+새v1을 고유 세계지식으로 중복 합산하지 않는다.
문자열 검사는 원문 범위/해시/역직렬화/예산에 한정하고, 모든 틀린 표현을 탐지하는 검사는 만들지 않는다.

### 9. 상태
08:31 저장 표본에서 결함을 확인했다. 기존 실행은 보존 중이며 이 새 복구/학생 학습은 아직 미실행이다.
[Gemma 공식 카드](https://huggingface.co/google/gemma-4-12B-it)의 sampler와 thinking 제어를 다시 확인했다.
temperature1/top_p.95/top_k64 및 system 시작 think 토큰을 사용하며, cap256/1024는 프로젝트의 비교 조건이다.

## 2026-10-15 Stage4aq~4as — 더 넓은 이름/사실 조합의 4pass 대조(비용 조건부)

### 1. 왜
기존12개 학습 이름·작은 사실집합의176회에서 형식/종료는 배워도 새 이름의 대상조회는 약50%였다.
같은 소수를 더 반복하는 것만으로 추상적인 이름-값 연결이 생긴다고 가정하지 않는다.
먼저 실행할 보조5팔의 개발 결과를 회수하고, 더 넓은 **코드 정답 과제**에서 같은 방법의 효과를 확인한다.

### 2. 질문
이름/사실 조합을 늘린 같은 새 데이터·같은 부모·같은4epoch에서 보조0과 선택한 연결보조를 비교하면,
새 이름/양순서/양대상의 자유 답과 실제 대화가 개선되는가? 일반 언어 보존의 대가는 얼마인가?

### 3. 세 대안
| 안 | 내용 | 장점 | 위험/비용 |
|---|---|---|---|
| A | 기존 작은 자료의 epoch만 늘림 | 구현/생성비가 작음 | 이미 본 조합을 더 외울 수 있고 승인한 정상4epoch와 구분해야 함 |
| B·이번 조건부 선택 | 고유 조합을 늘리고4epoch 유지 | 범위/추상 연결을 더 엄격히 확인 | 자료와 학습량이 함께 바뀌므로 작은 실험과 순수 스케일 효과라고 말하지 못함 |
| C | rank 보정/폭/재귀를 동시에 변경 | 구조적 병목 가능성을 봄 | 데이터·구조 교락과 구현 비용이 커짐 |

B의 새 두 팔끼리만 보조 목적 효과를 비교한다. 앞176회와 비교할 때는 이름/자료/업데이트 변화가 있는 기술통계다.

### 4. 데이터와 단계
- train의 언어별 이름96개는 기존 코드의12개 given-name과8개 성/last-name을 조합한 **가상 식별자**다.
  dev/test는 다른 given-name과 성 집합을 써 전체 이름이 겹치지 않게 한다. 실제 인물 사실을 만들지 않는다.
- binding은 가족별/언어별4096개의 서로 다른2인2값 매핑×양순서/양대상4view =65536행이다.
  코드로 정답을 계산하는 기존 다른 절차1024와 새 lossless QA512를 더해 train67072행이다.
- dev는 별도 이름/매핑의 binding1024+절차128+QA64=1216, 새 code final640과 공개 dev16/고정8/실제update4는 별도다.
  실제 x/assistant를 tokenizer로 다시 encode해 동결한다. 행수 균형과 token50:50은 다르다.
- Stage4aq0W: 새 생성·동적 분모/reader/모델-independent 계약 CPU 회귀.
- Stage4aq1W: 완성 lossless512/64를 읽어 새67072/1216/640과 보조 라벨을20MB JSONL로 동결한다.
  새 세계지식을67072개 발견한 것이 아니며 code4view/언어/epoch 반복은 별도다.
- native replay는 같은597995000-token **train.bin**의 서로 겹치지 않는16768개1025-token 창을 index로 참조한다.
  원cache는 읽기만 하며34MB 복사bin을 추가하지 않는다. 두 팔은 같은offset/순서다.
  총 native 입력/지도는2096×8192=17170432이며 val은 학습하지 않는다.
- Stage4aq2W: 보조5팔의 **마지막 epoch 개발 결과만** 읽어 후보를 고정한다.
  정확라벨.3/1/suffix1 중 code binding의4view-all-root 수, 정확값 수, 낮은 native CE 순으로 선택하고
  완전 동률은 낮은 계수.3→1→suffix1 순으로 정한다.
  아무 후보도 aux0보다 개발의 root/정확값을 개선하지 않으면 suffix1을 **미확인 가설**로만 지정한다.
  작은 실험의 final640을 이 선택에 쓰지 않는다. 후보 지정은 효용/기본값 채택이 아니다.
- Stage4ar0Wa/Wb: 새 dataset의 보조0/선택후보 각8업데이트 비용·양수 gradient·RAM/VRAM을 실측한다.
- Stage4ar0Wc: 비용의 첫 compile을 뺀7 step의 nearest-rank p95로 두 전체 팔을 예측한다.
  각팔의 추가 적재/dev/저장 여유600초, 최종평가1800초, 정리2700초를 더해 **17시 이전**에 들어갈 때만 연다.
  두 번째 팔 직전에도 실제 남은시간/완료 팔을 반영해 재검산한다. 예측은 완료 보장이 아니다.
- Stage4arWa/Wb: 같은 원parent·micro8×accum16·seq1024·checkpoint ON·compile default·Adam5e-5/Muon2e-4·NTP·native1,
  4pass×(67072/128)=2096업데이트. 보조0과 고정 후보만 다르다.
  추론에 쓰지 않는 head는 똑같고, 같은 causal suffix 로짓/행별 정규화와 source 계약을 적용한다.
- epoch1~3은 평가/원인추적용 새 CPT도 보존하고 epoch4는 최종파일이다.
  optimizer는 저장하지 않으므로 완전한 중단재개 증거/훈련상태라고 부르지 않는다.
- Stage4asW: parent와 두 최종 학생에 새 code640/공개개발16/기존8·실제update4/native를 같은 경로로 수집한다.
  같은 사실의 첫값 기준256/512·4view 일관성과 공개 원답을 분리한다.

### 5. 판정
더 넓은 과제에서도 실제 자유 생성의 대상조회가 첫값 기준을 넘는지, 한영별 변화와 원문 손실을 함께 본다.
단일 seed와 현재 생산 과제이며 세계지식·일반 지능·아키텍처 우열로 승격하지 않는다.
보조 점수/마스크/전송 성공만으로 학생이 똑똑해졌다고 하지 않는다. raw/native/sample 원형을 보존한다.

### 6. 비용
CPU 준비는 수분 추정·비용8 전에는 전체 GPU시간 미확정이다.
기존 약2.1초/정상update를 단순 적용하면 한 팔 약73분+적재/dev/저장, 두 팔 약2.5~3시간이지만 실측으로 다시 정한다.
새 JSONL/보조 metadata는20MB 이하 샤드이며 HF/private/가중치는 Git에 넣지 않는다.
native index와 CPU corpus를 사용해도 전체 process RSS와 GPU peak를 별도 보고한다.

### 7. 구현 영향과 선결
현재 미실행인 독립 binding_aux runner에서 literal176/1408 대신 **동결 계약의 실제 count**를 읽도록 좁게 일반화한다.
기존 작은5팔의 값은176/1408/4pass로 그대로다. 새 indexed-native reader와 선택적 epoch snapshot 분기는 기존에 비활성이다.
현재 **실행 중인 lossless producer의 CODE 목록에 이 trainer/test가 없음을 확인**했으므로 producer는 수정하지 않는다.
제품 transformer/기존 frozen실험/환경/검사기·보호 원천·원cache/CPT는 변경하지 않는다.
새 scale module/CPU test/SH·원형·계획/결과/기준표·COMPASS/WIP/인계만 추가한다.

### 8. 실행 후보
run_P106B_Stage4aq0W_large_binding_cpu.sh → run_P106B_Stage4aq1W_large_binding_corpus.sh →
run_P106B_Stage4aq2W_large_binding_choice.sh → run_P106B_Stage4ar0Wa_large_zero_cost8.sh /
run_P106B_Stage4ar0Wb_large_candidate_cost8.sh → run_P106B_Stage4ar0Wc_large_budget.sh →
run_P106B_Stage4arWa_large_zero4.sh / run_P106B_Stage4arWb_large_candidate4.sh → run_P106B_Stage4asW_large_binding_readback.sh.
여기에 적은 파일은 구현/회귀/등록을 완료한 뒤에만 실제 실행 권장으로 올린다.

### 9. preflight·한계
tag p106b_binding_scale_v1_s1337은 레지스트리 충돌을 확인한다.
2096×8×16×1024=274726912는 **padding 위치**이지 실제300M SFT 토큰이 아니다.
본75M 고유 train×4/300M의 대체 실험이 아니며, 교사가 기존 public 원천을 재생성한 자료는 개념 중복 합산하지 않는다.
새 학습량/동결 풀/정확한 cache·tokenizer/최종 질문을 조건 서명으로 기록한다.
현 데이터 크기의 실제 품질과 총시간은 실행 전에는 미확인이다.

### 10. 09:55 준비/회수 갱신
Stage4aq0W CPU24는 완료했다. 같은 시험의 로컬 fixture 이름을 고유하게 분리하고 TSV등록을 추가한
Stage4aq0Wb와 최종 동적분모/RSS 포함 Stage4aq0Wc CPU37도 완료했다. 공용검사기는 변경하지 않았다.
새 source576는 완결했고 Stage4ap0W512/64와 Stage4ap1W 전량 transport readback에서
문자/공백/들여쓰기 누락0·모든576 실제학생range 일치를 확인했다. 의미정답 판독은 아니다.
큰Stage4aq1W는 실제train67072/x3470276/지도215485·dev1216·test640으로 CPU동결을 완료했다.
code65536view는16384매핑이며4epoch실제x13881104/지도861940이다.
작은5팔학습/후속DEV선택·큰비용8/전체학습은 아직 순차 선결대로 진행한다.

### 11. Stage4anWb·Stage4asWb — 같은 실제 답의 CPU 관계별 재집계
학습/생성 코드는 동결하고 별도 CPU consumer만 확장한다.
작은5팔과 큰2팔의 실제640 raw에서 코드가 선언한4view마다 다음을 추가 집계한다.
같은 사실순서에서 묻는 대상을 바꾼 두 답이 달라졌는지/둘 다 맞는지,
같은 대상을 두 사실순서로 물었을 때 같은 답인지/둘 다 맞는지, 네 답이 모두 같은 문자열인지다.
표현도 함께 달라지는 counterbalanced view이므로 대상만 바꾼 순수 인과개입으로 부르지 않는다.
문자 일치 자체를 의미정답으로 승격하거나 교사 자유답에 이 분류를 적용하지 않는다.
원형·old summary는 보존하고 모델0/optimizer0의 새 소비기에서 root층화 bootstrap도 함께 기록한다.
Stage4as0W CPU회귀 뒤 run_P106B_Stage4anWb_auxiliary_pair_readback.sh 및
run_P106B_Stage4asWb_large_pair_readback.sh를 각 GPU 평가가 끝난 뒤에만 실행한다.

### 12. Stage4at0W·Stage4atWa/Wb — 실제 질문/답 비교 보기
CPU 소비기는 완료한 작은/큰 fresh_test report의 동일 질문별 모든 모델 원답을 묶은 Markdown을 만든다.
code640과 공개dev16을 구분하고 공개교사 target은 미검증이라고 표시한다.
원문과 실제공개답이 들어가는 전체보기는 ignored local 아래, 작은 경로/SHA/개수 receipt만 추적한다.
처음 실제code 질문의 답도 console에 표시해 내부ID만 보고 선택하게 하지 않는다. 입력대기는 없다.
이것은 저장된 결과의 보기이며 의미평가·재생성·학습 제외 기능이 아니다. 모델/GPU0·기존원형불변이다.

### 13. Stage4au0W·Stage4auWa/Wb — 같은512문항의 연결분류와 실제 자유답
작은aux03의 개발512 분류473과 개발부분64 자유39는 분모/집합이 달라 연결단절을 확정할 수 없다.
세 선택은 (1) 같은 실제test512에서 학습전용head와 저장자유답을 짝짓기,
(2) 새 readout/대조학습까지 바로 추가하기, (3) 큰 학습 결과까지 기다리기다.
현 단계에서는 가중치를 바꾸지 않고 같은 집합부터 확인하는1을 선택하며2는 결과 뒤 검토한다.
닫힌 fresh_test640과 해당 CPT가 있어야 하며 binding512만 코드매핑·실제gold 일치를 검산한다.
모델에 넣는 것은 ANSWER 이전 완전한 prefix뿐이고, head는 저장된 학습용2class를 읽기전용으로 복원한다.
실제 자유답은 이미 저장한 같은 질문의 원형에서 읽으며 head로 답을 생성·선택하지 않는다.
FP32 MATH/noTF32·cacheON·batch1의 원래 생성 prefill 경로에서 마지막hidden을 얻는다.
head를 읽는 첫 forward와 원래 logits-only forward의 비트정합, CPT/SHA·본체 전후 fingerprint를 확인한다.
새 optimizer/가중치저장/교사호출0이며 이름에 mtp_hidden이 있는 API는 hidden 반환용일 뿐 MTP 추론을 켜지 않는다.
학습 전용bit정확/자유정확의2×2와 언어·과제별 숫자/actual raw를 남긴다.
단어·문구 black list나 의미 자동판정, 일반QA 분류를 추가하지 않는다.
약1~3분 GPU추정·상한600초, source/학습코드는불변·새tag p106b_binding_readout_v1_s1337이다.
이 관찰의 상관은 마지막출력층/attention이 단독 원인이라는 인과 증거가 아니다.

## 2026-10-15 Stage4av~4ax — 조건 변경·응답 형식의 마지막 턴 연결 보조(시간 조건부)

### 1. 질문과 현재 근거
작은 정확bit1은 개발조회63/64를 보였지만 산수/조건변경은 아직 회복됐다고 할 수 없다.
먼저 기존5팔 최종검증과 큰2팔을 수행한다. 그 뒤17시 정리여유 안에 들어갈 때만
‘초기 답 이후 값을 바꾸고 다시 묻기’의 C1과 ‘JSON으로 답하기’의 C3를 결합한 별도 두 팔을 연다.
현재 목표75M×4epoch와 모델 구조/토크나이저는 바꾸지 않는다.

### 2. 세 대안과 선택
| 안 | 내용 | 이점 | 한계 |
|---|---|---|---|
| A | 기존 두 사실 조회만 추가 반복 | 변화축이 작음 | 새 조건을 적용하는 능력은 확인되지 않음 |
| B·조건부선택 | 새 매핑의 조건변경/정확형식에서 보조0/1 대조 | 실제 후속지시의 옛답 복사를 겨냥함 | 새 과제·부모가 바뀌므로 앞 실험과 단일축 비교는 아님 |
| C | 공개 자유QA부터 더 생성 | 세계지식 범위를 넓힘 | 교사 비용·정답/맥락 후행검토가 필요하고 상태추적 원인은 남음 |
B는 새 두 팔끼리만 추가목적 효과를 비교한다. 일반 QA까지 임의로 ‘수정 대상’을 자동 분류하지 않는다.

### 3. 자료 계약
코드가 두 가상 인물/건물의 서로 다른 두 값을 만들고, 둘과 다른 새 값으로 한 항목을 수정한다.
첫 user/assistant는 원래 조회와 올바른 답, 두번째 user/assistant는 수정 지시와 새 정답이다.
수정한 대상을 다시 묻는 경우/다른 대상을 묻는 경우, 사실순서·첫 질의대상·마지막 질의대상·scalar/JSON을 교차한다.
JSON은 코드가 명시한 answer 한 항목 계약만 사용한다. 복잡/불명 JSON을 단순포장으로 추정하지 않는다.
예: 민수=빨강/지수=파랑→민수? 빨강→민수를초록으로수정·지수의현재색을answer JSON으로→{"answer":"파랑"}.
부모가 본 작은코퍼스와 **매핑 단위로 겹치지 않는** 새 사실만 골라 train 이름/개발 이름/test 이름도 분리한다.
- train: 조건변경8192(256새매핑×32view)+별도 새 기본조회5120(1280매핑×4view)=13312행.
- dev: 조건변경1024+새 기본조회512+기존 공개dev64=1600행. 공개원문은 학습하지 않는다.
- test: 새 조건변경512(64매핑×균형8view)+새 기본조회512=1024행. 공개dev16·기존8·실제대화는 별도다.
학습한 public512를 다시 넣어 누적8epoch로 만들지 않는다. 새 source를 다운로드/보호경로에서 가져오지 않는다.
네 epoch는 새13312행에 대한4pass이며 새 고유세계지식13312개를 뜻하지 않는다.
원문 cache는 읽기만 하고 부모가 쓴1408 native 창을 제외한 새3328개1025창을 index 참조한다.

### 4. 초기화와 목적
부모는 이미 사전등록한 작은5팔의 마지막 DEV만으로 고정한 후보의 저장 CPT다.
최종test 점수로 다른 부모를 재선택하지 않는다. 두 팔은 같은 가중치·새 optimizer 상태에서 시작한다.
기존 m8×accum16·seq1024·ckptON·compile default·Adam5e-5/Muon2e-4·NTP·native1·4epoch416회를 유지한다.
새 학습전용2class head는 ‘마지막 질문의 대상이 이번에 수정된 항목인가’를 코드 정답으로 감독한다.
정확한 hash 계약이 있는 조건변경8192행만 사용하고, 공개/기본조회 행에 임의 라벨을 붙이지 않는다.
위치는 **마지막 assistant predictor**다. 첫 답을 지도하는 SFT mask는 그대로 두고
보조위치 찾기용 복사 mask에서만 이전 assistant span을 가린다. 미래의 마지막 답을 읽지 않는다.
양팔이 같은 head forward를 계산하며 보조0/1만 다르다. head는 자유 생성에서 호출하지 않는다.
원래 제품/작은5팔/큰2팔 코드는 수정하지 않고 새 모듈의 한 프로세스 안에서만 명시적으로 callback을 연결한다.

### 5. 단계와 선결
Stage4av0W: 새 표/정답/유일매핑/라벨·두 assistant mask·native제외·0계수 gradient CPU 회귀.
Stage4av1W: 부모/작은원천 SHA를 잠그고 새13312/1600/1024를20MB 이하 조각으로 동결.
Stage4aw0Wa/Wb: 각8업데이트·저장0의 비용/양수 gradient 확인.
Stage4aw0Wc: 첫compile 제외 p95×416과 팔별300초, 최종평가900초·마감정리2700초를 합쳐 남은시간과 대조.
Stage4awWa/Wb: 같은 조건에서 새 보조0/1 각416회. 추가 GPU는17시 이전에만 수행한다.
Stage4axW: 초기부모·두 학생의 같은1024 첫 답/native/공개dev16/기존8과 실제2턴 대화를 수집한다.
‘이전값을 그대로 복사해도 맞는’ 경우와 실제 값을 바꿔야 하는 경우, scalar/JSON을 분리한다.
teacher/gold 이력을 준 마지막 답과 실제 이전 학생답을 문맥으로 쓴 rollout을 섞지 않는다.

### 6. 비용·판정·영향
현재 정상 약2초/update의 단순 적용으로 두 학습팔 약30분+개발/저장, 평가까지40~60분 추정이다.
실제8 비용/자료량 전에는 완료시간을 보장하지 않는다. 시간부족이면 코드/선결만 보존한다.
절차자료·코드정답·일반세계지식/지능을 구분하고 실제 새512 조건변경과 기본512를 따로 보고한다.
첫 답 복사의 겉보기 정답과 최신 상태 정답을 분리하고, native 보존 및 공개QA 망각도 함께 읽는다.
보호 TinyDataset/원HF/cache/CPT·환경·공용검사기·타 WIP·외부 저장소는 바꾸지 않는다.
새tag p106b_state_update_aux_v1_s1337·독립 코드/CPU/SH/작은 요약·계획/결과/나침반/원장/인계만 갱신한다.
실험선결/권한, 데이터 소유, 비교조건, 지표 수준, 문서연쇄의5영향축을 모두 위 계약으로 제한한다.
이 단계는 아직 설계이며 구현/CPU/모델 실행 완료로 주장하지 않는다.

## 2026-10-15 Stage4ay0W·Stage4ayW — 보유 Dolly 문맥/정확 span CPU 재고(학습 아님)

### 1. 목적과 세 대안
자연QA가개선되지않아 기존원천의활용가능성을확인한다.
A는QA가족별선별범위를즉시넓히기, B는명시문맥/문자정렬의실제량부터재기, C는규칙학습만계속하기다.
B를선택한다. 가족이름/원카드의대분류만으로원천을자동수락하지않고GPU/기존원형/75M정책을바꾸지않는다.
현재캐시에는Dolly가언어별14808개이나row의task_type은전부generation·subdataset '-'·template1이다.
원Dolly의세부 category가이필드에그대로남아있는것은아니다.

### 2. 데이터/기술 계약
기존inventory report에기록된 EN train00003/KO train00001의두공개parquet만읽는다.
원파일SHA를stream으로재확인하고Dolly-v2/(T)행만Arrowfilter로읽으며원문·공백을수정하지않는다.
원래user/assistant를그대로직렬화한실제x/assistant총량,1024이내량을계산한다. 새Followup을붙인75M가용량이아니다.
알려진제작형식의단일줄바꿈 Context: 구분자와그이전질문/이후문맥이있는경우만별도계측한다.
target이그문맥에정확히한번존재하면문자범위/토큰끝위치를매핑한다.
이는추출형보조라벨을만들기위한**기술정렬**이지의미정답/자료품질검사나틀린표현목록이아니다.
불일치/여러번일치/너무긴자료는불량이라고부르지않고이방법의라벨을만들수없음으로기록한다.
질문이문맥보다먼저나오는지,마지막답body가들어가지않은prefix의source토큰범위인지검산한다.

### 3. 출력/권리
모델/교사/GPU/새다운로드0,기존자료변경0이며census완료는TRAIN_READY가아니다.
재고/정확span후보는새 ignored HF의Dolly별도namespace/20MB이하조각으로보존하고기존main loader에연결하지않는다.
정렬후보가0이어도유효재고결과0이며임의반복으로양을채우지않는다.
현재[Collection 카드](https://huggingface.co/datasets/CohereLabs/aya_collection_language_split)는Apache2.0,
[원Dolly 카드](https://huggingface.co/datasets/databricks/databricks-dolly-15k)는CC BY-SA3.0이다.
상위label만으로하위권리상태를일괄확정하지않고별도보존/귀속을남긴다. 법률판단/모델license승격/원문공개는하지않는다.
Git에는코드·명령·집계/원천SHA만넣으며실제질문/답/문맥은넣지않는다.

### 4. 비용·판정
CPU두파일filter/원SHA/약3만행tokenization의수분추정이며실제시간을기록한다.
전체tokens/행·고유문자질문hash·문맥hash/knowndelimiter/unique-exact-span의분모를구분한다.
다른언어번역의원개념대응ID는없으므로한영semantic split/고유세계지식량은미확인이다.
대량main편입이나추가학생/보조모델구조는실측후별도계획으로만연다.

### Stage4ay0Wd·Stage4ayWb 길이통계 복구
v1은9번째행의1272 serialized tokens에서학생용encode_record(context1024)를먼저불러실패했다.
부분통계8행/원형/코드는보존하고v2별도namespace·파일을쓴다.
v2는encode_conversation/sft_targets로전체길이를자르지않고계산하며,
1024이내정렬후보에만학생용strict인코더를재대조한다.
긴행/짧은행통계와위치매핑회귀5를먼저검증한다. 행이길다는것은자료불량/학습전체불가판정이아니다.

## 2026-10-15 Stage4az~4bb — 상태학습을 고정한 덧셈 자리/올림 보조(시간 조건부)

### 1. 목적과 선택
새조회는개선됐으나실제새산수는여전히낮다. A는추가조건부데이터확대,
B는정답을코드로확정하는덧셈의구조감독, C는같은과제의새seed재현이다.
시간안에수행할다음범위는B로준비한다. 새덤핑/추정오답이나teacher호출없이고정된숫자계산부터확인한다.
기존큰2팔/상태2팔을먼저수행하고, 실측예산과17시마감여유가있을때만연다.
제품/기존frozen코드/메인75M×4·batch·tokenizer는바꾸지않는다.

### 2. 데이터와초기화
모든새모델의부모는DEV로먼저고정한small suffix1 B57F863685A5다.
앞상태학생을이어학습하지않고같은초기본체/새optimizer에서시작해누적노출을분명히한다.
기존state13312에덧셈8192를더해train21504·dev2624(state1600+add1024)·test2048(state1024+add1024)로구성한다.
정수0..99의 unordered operand pair를구성하고부모작은코퍼스의알려진덧셈/계산변경pair와2+3은제외한다.
train2048/dev256/test256개의서로다른pair를먼저분리한뒤한영·순서/서술4view를만든다.
같은숫자의순서변경/번역을독립새개념이나서로다른split으로세지않는다.
정답은Python합과십진자리/올림재구성이서로일치해야한다.
예:43+28→71,일의자리1·십의자리7·일의자리올림1. 답에는정수71만쓴다.
덧셈만이며뺄셈/임의수학능력을보장하지않는다. state데이터와publicdev는원형참조/복사만하고고치지않는다.

### 3. 목적과비교
same m8×accum16/seq1024/ckptON/compiledefault/Adam5e-5·Muon2e-4/NTP/native1/4epoch672회다.
학습전용Linear(768,34)는state2class+decimal32(ones10,tens20,carry2)이며26146 FP32계수다.
여기서 tens20은합//10의상위몫0..19다.99+99=198이면ones8/highpart19/carry1이며10×highpart+ones로재구성한다.
단일십의자리/백의자리를따로분류한것이아니다. 동결메타데이터의tens키는원형그대로보존한다.
양팔이같은head계산을하고state보조는고정,decimal계수만0/1로바꾼다.
known-row전체분모에서state CE에2,decimal의3 CE평균에2β를곱한다.
두종류의알려진행수가8192씩이므로태스크별기대비중을맞추는정책이며매update의task별별도정규화라고부르지않는다.
기본조회/공개QA에임의자리라벨을추측하지않는다. 마지막assistant predictor만사용하고미래답body는읽지않는다.
head는생성에서쓰지않는다. control의decimal행파라미터0유지·positive의실제양수업데이트를비용/본학습후별도검산한다.
state고정손실은양팔모두켜져있으므로control head전체가0이어야한다고잘못검사하지않는다.

### 4. 단계와비용
Stage4az0W:독립자리검증/부모pair제외/split/마스크/0decimalgradient·state고정CPU.
Stage4az1W:새21504/2624/2048을20MB미만샤드로동결·실제x/target분모회수.
Stage4ba0Wa/Wb:각8cost/CPT0·state/decimal학습후조건.
Stage4ba0Wc:정상7step p95×672+팔별300초·평가900초·마감정리2700초를더해남은시간과대조.
Stage4baWa/Wb:두full672회팔·같은native창5376개/5505024x를index로읽으며부모추가replay1408창을제외한다.
Stage4bbW:원부모/두학생의같은2048첫답·산수carry별/언어별·state512/basic512·native/공개dev16/기존8을분리한다.
유효토큰은실제동결후계산한다.672×131072는padding위치이지300M실제학습량이아니다.
현재2초/정상step의단순외삽은두팔45~55분+평가이며8cost전완료시간은보장하지않는다.

### 5. 판정과한계
새operand pair의정수첫답과state보존을함께본다. 자리head정확도/낮은CE를학생답인증으로쓰지않는다.
이전상태단독과는자료/업데이트가달라순수한math보조비교가아니며새두팔끼리만β효과를비교한다.
숫자범위0..99/템플릿/한seed이고출처사실성·일반QA·일반수학/지능/본300M으로승격하지않는다.
원데이터/기존CPT/보호경로/환경/타WIP/외부상태불변이며새tag p106b_joint_decimal_v1_s1337만쓴다.

### Stage4bc0W·Stage4axWb/4bbWb 후행 CPU 비교
새state/joint의같은실제질문raw를hash로맞추고엄격코드정답/하위과제/native를재집계한다.
bootstrap은같은task와root의관측language집합으로층화하며한root의한영view를분리샘플하지않는다.
단위가다른state8view/기본4view/덧셈한영4view의실제군집을그대로묶는다.
고정모델/제작과제에대한조건부구간이며새seed σ나범용지능의신뢰구간이아니다.
GPU/새학습/원형수정0이고부모·두학생의collection완료뒤에만읽는다.

### Stage4bd0W·Stage4bdWa/Wb — 실제 개발검증 비용 보충(학습0)

8회 비용 측정은 학습 스텝만 재고 epoch마다 반복하는 SFT dev/native32/보조 dev/실제 생성 비용을 제외한다.
동결 state/joint의 동일 선택 부모를 읽어 네 경로를 CUDA 동기화 전후로 각각 측정하고 본체 SHA 불변·optimizer0·CPT0을 확인한다.
새 코드만 사용하며 동결 학습기·원자료·이전 비용값을 수정하지 않는다. 실제 원답은 ignored local에만 저장한다.
후속 예산은 정상 step p95×업데이트+4×관측 검증초×1.5+팔별300초로 보충하고 최종평가·마감정리 여유를 따로 둔다.
1.5는 운영 여유이지 통계적 신뢰상한이 아니며 부모 한 번의 생성시간이 학습 후 시간을 보장하지 않는다.
시간 부족이면 두 대조 중 완료 가능한 쌍을 우선하고 나머지는 NOT_RUN으로 보존하며 한 팔 결과를 쌍 비교로 승격하지 않는다.

### 2026-10-15 12:37 실행 이력/예측 대조

- 완료: Stage4ayW v1은긴원문 계측오류exit9, 새4ayWb v2는29616행 전체재고exit0다. 원천불량/학생실패로판정하지않았다.
- 완료: Stage4az0Wc CPU14·4az1W train21504 동결, 실제1276878x/119518지도. ‘가상과제라 자료가부족하지않다’는전제는동결까지확인했고학습효과는아직미확인이다.
- 완료: Stage4arWa 큰aux0 2096회/81.0분, DEV조회61/64/native3.547426. 작은과제의낮은기준과달리충분한대상조회노출자체의개선가능성을보였으나후보/새640비교는아직미완이다.
- 진행: state두8cost와joint두8cost, 부모개발검증실측을묶어남은17시예산을재산정한다. 8cost가epoch검증을포함하지않는점을예산에서보충한다.
- 경계: full teacher/student 프롬프트가같다는주장이아니라원천필드문자보존이다. Dolly후보는본생산/75M미편입이며원형/권리조건을분리한다.
- 결과정본: [101 §131~132](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md). 계획 전체는진행중이며완료계획으로개명하지않는다.

## Stage4bf0W·Stage4bfW — 오른쪽 padding 축소의 독립 무업데이트 진단

### 목적/선택과 영향

1. 현재 고정1024를 유지하면 기존 대조의 수치/계보가 불변이나 짧은 문항의 빈칸 계산이 남는다.
2. 같은 행의 오른쪽 빈칸만128배수로 줄이면 실제 토큰/지도/대화 경계는 그대로일 수 있다. 수치경로와 compile 형상은 달라져 실측이 필요하다.
3. 여러 대화를 한 sequence로 packing하면 더 줄일 수 있으나 attention 경계/position/지도 설계가 달라진다. 이번에는 구현하지 않는다.
운영 선택은1을 유지하고2의 별도 진단만 준비한다. 진행 중 큰 팔/동결 state·joint의 코드/자료/배치 조건은 불변이다.
제품 모델/기본 학습기/공용 검사기/환경은 수정하지 않고 독립 scripts와 새 evidence namespace만 사용한다.

### 고정 조건과 검사

동결 joint21504의 같은 seed 첫128행·같은 선택 부모·native 첫8창을 사용한다.
padding만fixed1024 대128배수상한1024로 바꾸며 삭제/압축/대화병합을 하지 않는다.
FP32 MATH/noTF32의 같은 word+native 손실과 전체 본체 gradient를 대응 비교한다.
진단 한계선은 loss절대차1e-4/gradient상대L2 1e-4/cosine .999999이며 이 선은 운영 관측 기준이지 품질/통계적 신뢰상한이 아니다.
원래 state/자리 보조는 이 진단에서 빼므로 전체 학습 recipe의 동일성으로 승격하지 않는다.
BF16/compile default는 각형상을 warmup한 뒤 고정→축소/축소→고정의두순서쌍을 관측한다.
각관측은16개SFT micro와1개native micro의 forward/backward만 하고 optimizer/clip/가중치저장0이다.
기존 CPU가 처리한 시간·compile cold와warm 반복을 나누며 이 시간만으로 전체 학습속도·품질을 보장하지 않는다.
동일 입력/target/경계·본체SHA불변을 확인하고 시간여유가 있을 때만 최대600초 GPU를 사용한다.
FP32근접·속도개선이 있어도 진행 중 팔의 배치를 바꾸거나 전역채택하지 않는다.
단계4bf0W는 width/지도보존 CPU,4bfW는 새 독립GPU진단이다. 17시/마감정리 선결을 유지한다.

### 12:59 실제 관측과 다음 순서

state 두8cost와joint 두8cost는완료/CPT0, 검증부모불변·state29.882/joint46.415초를관측했다.
큰기준81.0분도완료했으며큰후보는raw124257/session45327에서진행중이다.
[검증포함예산](../test_result/evidence/p106b_validation_cost_v1_s1337/afternoon_schedule_1242.json)은
남은15426초에큰후보+평가+joint쌍+마감14712초로조건부실행, state까지동시약속18289초는불가로판단했다.
따라서큰두팔최종비교→joint쌍을우선하고시간이남으면state단독쌍을재검산한다.
오른쪽padding은CPU4/tiny모델에서유효손실·gradient근접과무업데이트를확인했지만실제GPU는NOT_RUN이다.
큰대조/동결두후속의학습조건은변경하지않는다. 선형pos절감량을실측속도나품질로승격하지않는다.

## Stage4bg0W·Stage4bgW — 같은 학생/질문에 원문 제시 범위만 바꾸는 개발 진단

사후16원답에서원문에는예전공개canonical의준비/JSON연습턴도포함됨을확인했다.
‘원문보존’은선택된canonical row의전체메시지보존이지외부parquet의가공전원문이라는뜻이아니다.
개선후보는1)같은가중치로전체/교사선택완전메시지/빈근거를비교,2)생산자계보로출처와추가연습턴을분리한새자료/재학습,
3)전체인용의지시와바깥질문을구별하는새지시학습이다. 이번에는1의작은무학습진단만준비하고2/3은자동실행하지않는다.
같은DEV선택small suffix1 부모/동일16질문·답reference·FP32 MATH/cacheON/T0/max256을유지한다.
이미기록된teacher_selected_reference_ids만사용하며문구검사로어떤턴을원문/연습이라고추측해삭제하지않는다.
선택한메시지의전체문자/역할/공백은그대로이고전체upstream metadata를private sidecar에보존한다.
full재실행16이전답일치·전체/선택/빈근거의실제답·종료·토큰길이를수집하되literal일치를의미정답률로부르지않는다.
빈근거에도참고gold는집계용일뿐자동정답/오답판정하지않는다. 평가용16과변형은train으로반출하지않는다.
사후개발진단이며고정표본의추론표시변경이지새학습/범용개선이아니다. 실제GPU는최대600초/마감여유내에서만수행한다.
최초16render선결에서는선택전후실제입력이바뀌는것이4개(index6/7/10/12)뿐이었다.
나머지12개는동일프롬프트음성대조이며16개모두처치가달라졌다고부풀리지않는다. 학습target토큰동일성도GPU전에검사한다.

## Stage4bj0W·Stage4bj1W·Stage4bjWa/Wb·Stage4bkW — 별도 right-trim joint 두 팔

### 선택/범위

고정1024 유지(A)는기존준비그대로지만두팔비용이커state단독비교가시간밖일수있다.
별도축소실험(B)은같은부모/데이터/실제token/목적을유지하고오른쪽빈칸만128배수로줄인다.
packing(C)은대화/attention경계까지바뀌므로진행하지않는다.
무업데이트probe의2.97배관측과FP32word/native gradient상대차1.1e-6을근거로B를별도namespace로준비한다.
이것은전체보조/optimizer/학습품질의동등성확정이나기본값변경이아니다. 새두팔의실측8cost와실제학습/새2048로검증한다.
기존fixed state/joint 코드·데이터·원형은바꾸지않고unrun대안으로보존한다. 14:40까지선결이열리지않으면기존fixed joint를우선한다.

### 방법과보존

원래동결joint21504/2624/2048을원본코드SHA/manifest/native SHA로먼저검증하고읽기전용참조한다.
새p106b_joint_decimal_trim_v1_s1337/source_contract는source_report SHA/producer CODE와새실행 CODE를따로기록한다.
runtime의core.pad_records 인수만바꾸며fixed_width1024 요청에서실제max길이를128배수로올린다.
최장120인train은128, native1024는그대로다. maxcontext1024·row/target/turn/마스크·라벨·부모·4pass672·LR/native1·state고정/자리0·1은유지한다.
eval의실제생성은원래FP32 MATH/cache 경로이며표시/자료내용을바꾸지않는다. 모델core/공용학습기파일은수정하지않는다.
CPU는같은valid hidden의보조손실/gradient·패딩target/범위·컨텍스트복원을검사한다.
source_contract 동결후같은코드8cost 두팔/CPT0·head활성후조건을확인한다. 실측p95×672+4×기존검증46.415초×1.5+팔별300초·평가900·마감2700초로예산을다시잡는다.
train/evalreport는새태그로분리하고source corpus SHA는원래동결파일을가리킨다고명시한다. schema/labels는원래정확생산자계약을재사용하며원본metadata를덮어쓰지않는다.
전체학습속도/새2048답/native/실제대화로효과와한계를보고하고구형fixed 결과가있는것처럼쓰기/새default자동승격을금지한다.

정확단계: Stage4bj0W CPU, Stage4bj1W source계약동결, Stage4bj2Wa·Stage4bj2Wb 각8cost,
Stage4bj2Wc 검증포함예산, Stage4bjWa·Stage4bjWb 각672학습, Stage4bkW 실제2048수집, Stage4bkWb CPUpaired다.
구형고정캔버스의Stage4baWa/Stage4baWb는취소/삭제하지않고예비대조로보존한다.

### 14:46까지 실제 이력/예측 대조

큰두팔2096회와새640/CPUpaired/같은512/원답보기는완료했다. 최종조회500대506/512·전체544대563/640이나산수는둘다0/32다.
padding은실제무업데이트113.5초·FP32gradient근접/2.97배warm관측이었고BF16 CE는비트동일하지않았다.
ref16 full재현16/16/동일대조12개출력동일,4변경입력도literal4→4였으며요청충족이회복됐다는근거는없었다.
새trim source계약·CPU6/정적68·0·6·두8cost/CPT0·보조후조건을완료했고14:35부터새기준672학습중이다.
최대context/원데이터/유효token/목적/부모를유지하면서실행캔버스만분리했다. 원래fixed실험의결과로계승하거나default로자동채택하지않는다.
다음은새trim자리1과새2048/실제대화평가이며state고정416두팔은그뒤실제마감예산으로판단한다.

### 15:22 실측 회수와 남은 대조

새 trim 두팔은672회·각13.3/13.6분으로 완료했다. 검증/최종평가까지 회수한 새 덧셈은42/423 of1024였으며,
조건갱신494/481 of512·기본조회490/458 of512·공개DEV literal1/0 of16의 대가가 남았다.
전체2048 차이의 root 구간과 실물 답은 결과101 §145가 소유한다. 원래 fixed joint 전체실행/수치동등/default채택은 NOT_RUN이다.
같은 공용 probe의 실제 rollout은 첫 영어8view16턴(두 root)이며, 한영 정답이력 최종답16건과 분리했다.
기존 subset16 metadata를16실제대화로 해석하지 않는다. 런타임/CODE를 바꾸지 않고 별도 범위 검산으로 정정했다.
최종답 뒤 실제 남은시간6493초에 state416 두팔·검증·평가900·마감2700을 포함한6276초가 들어옴을 확인했다.
15:12부터 state0을 시작했으며 덧셈 없이 상태감독0/1의 단독 효용을 확인한다. 새 joint학생이 아닌 같은 작은 선택부모에서 각각 시작한다.
17시 이후 새 실험으로 이어가는 권한은 없으며 남은 범위/마감상태는 정확WIP와 최종 인계가 소유한다.

### 15:55 실제 완료와 후속 판정

상태단독 두팔은416회씩18.3/18.1분, 새1024평가는4.8분으로 완료했다.
같은512상태문항은부모69·상태0의504·상태1의497, 기본조회501/505, 전체1024는1005/1002였다.
추가상태보조의전체차이−.00293/root구간[−.01270,.00684]에0이포함돼추가승자로채택하지않는다.
정답상태대화를배운것의효용과보조를추가한효용을구분한다. 공개DEV16 literal은각1·기존8은각0으로자연QA미회복이다.
grad_max13.05/51.72·clip1을실행완료/전면안정성으로승격하지않는다.
본격새GPU는15:54:53종료, 이후는CPU재집계/문서/감사/복구정리/커밋이다.
오늘18full팔8480업데이트는여러독립대조의합계이지한학생의300M교육이아니다.
원래fixed대안5SH와옛source코퍼스1SH는본문/SHA보존후호환hold로옮겼다. 새실험날짜/CODE/원천계약없이이름만복구해실행하지않는다.
실제숫자/조건서명47·원답/대화분모와native한계는결과101 §148~149가소유한다.

## 2026-10-15~16 Stage4bl~4bn — 자연 지문 QA와 학습 전용 답 위치 보조

### 1. 왜 / 질문

사용자의 2026-10-16 17:00 KST까지 주도 실험 승인으로 시작한 독립 후속이다.
전일의 조회·조건 변경 개선과 달리 공개 자연 QA는 회복되지 않았다(결과101 §145~149).
기존 완전 원문은 보존하되, 이번에는 이미 보유한 공개 COQA의 첫 질문·짧은 답·지문을
분리해 한 번에 한 질문만 학습한다. 새 다운로드·Dolly·보호 사전·원본 수정은 없다.

| 안 | 실제 차이와 예 | 이점 | 한계/영향 | 예측 비용 |
|---|---|---|---|---|
| A·선택 | 지문+‘누구인가?’→원천의 짧은 답; 같은 자료의 SFT와 답 위치 보조0/.3 비교 | 구조·초기화 고정, 자연 근거 찾기를 직접 검증 | 위치 정합은 정답성 보증 아님; 독립 코드/회귀 필요 | 구현·CPU 1~2h, GPU 비용8 실측 뒤 두 팔 허용 |
| B | 교사가 새 자료 수천 개를 먼저 생성 | 주제·언어 범위를 넓힐 수 있음 | 생성 수시간과 재시도; 기존 학습 실패와 생성 품질 교락 | 기존576건44.5분은 참고일 뿐 새 조건 미측정 |
| C | 재귀·폭·MTP를 먼저 변경 | 구조 효과 연구 | 자료 문제와 변경축을 함께 떠안음 | 별도 초기화/CLA/계산량 계약 필요 |

선택 A는 기존 제품 구조를 바꾸지 않는다. 보조기는 학습 때만 사용하고 자유 답안은
항상 기존 어휘 헤드로 생성한다. 자연 QA 개선을 확인한 뒤 B/구조 확대를 다시 판단한다.

### 2. 착수 전 영향도와 권한

| 경로 | 동작 | 승인 근거 | 제외 |
|---|---|---|---|
| scripts/p106b_grounded_span.py, diag/test_p106b_grounded_span.py | 독립 신설 | 주도 실험·구현 현재 승인 | 기존 tinylm/공용 검사기 수정0 |
| HF/sft_ready/p106b_grounded_span_v1_s1337, 새 runs/ckpt 태그 | 새 자료·새 가중치만 | 새 실험 실행 승인 | 기존 자료/가중치 덮어쓰기0 |
| 새 bl/bm/bn SH, experiments.tsv | 선결→비용→양팔→평가 | 실험 절차·완료 SH 정리 지시 | queue/smoke 대리 실행0 |
| 계획/결과/기준표/방법론/COMPASS/현 WIP/새 인계 | 증거 연쇄 | 현재 사용자 지시 | 타 WIP/과거 인계 수정0 |

코드: 기존 encode_record/components/optimizer/runtime 로더를 읽어 재사용하며 기존 호출부 시그니처는 바꾸지 않는다.
데이터: 공개 canonical 첫 두 메시지의 COQA 번호1/2 구조만 해석하고, 질문·지문·답의 문자 범위를 보존한다.
테스트: 번호 오인·다중/빈 답·앞뒤 경계·질문/미래 답 누설·마스크·보조 gradient·제로 팔·원형 보존을 검사한다.
문서: 기준표/방법론/양 인덱스/COMPASS/레지스트리를 결과와 함께 갱신한다.
부채: 이번 소형 연구의 파서·위치 보조를 전역 생산 기본값으로 승격하지 않는다.
권한/소유: 내일17시 전에만 실행하며 원본·보호 데이터·외부 게시·설치·다운로드는 제외한다.
비교: 부모/tokenizer/자료/노출/배치/원문 replay/생성 정밀도를 맞추고 보조 가중치만 변경한다.
계측: 실제 대화/지도/native/패딩 토큰·학습/평가 시간·grad_max·reserved를 각각 기록한다.

### 3. 예측

SFT만으로도 기존 복잡한 원문 묶음보다 짧은 답 종료가 나아질 가능성이 있다.
정답의 지문 위치를 예측하는 보조는 질문과 근거의 연결을 도울 수 있지만, 판독 헤드만
좋아지고 자유 생성은 그대로일 수 있다. 번역 원천 결함·짧은 학습·삼진 몸체의 한계도
남으므로 실패를 SFT/아키텍처 불가능으로 일반화하지 않는다.

### 4. 단계와 고정 계약

- Stage4bl0W CPU 회귀 → Stage4bl1W 공개 자료 동결. 목표 train 한영각1024·dev각128·test각128.
  공급 부족 시 자동 축소/반복하지 않고 수량을 보고해 새 설계를 구분한다.
- 번호1 첫 질문만 사용한다. 번호2 이전을 정확히 자르고, 짧은 원천 답(학생24토큰 이하)이
  지문에 정확히 한 번 있는 경우만 위치 라벨을 붙인다. 이 선택은 기술 정합이며 내용 심사가 아니다.
- 같은 부모 dense14/chat32·seed1337·micro8×accum16·ckpt-on·compile default·4epoch.
  두 팔 span0/span03, Adam5e-5/Muon RMS4 2e-4·matrixWD0·native8×1024 CE 가중치1·clip1.
  SFT 오른쪽 padding은128정렬/최대1024이며 동일 정책. 긴 입력은 절단하지 않는다.
- train2048 자연 QA와 기존 코드 QA1024를 섞으면3072행/4epoch96업데이트다.
  실제 동결 수량과 실제 unpadded 토큰을 정본으로 삼고 패딩12,582,912와 혼동하지 않는다.
- 보조: 마지막 답 예측 직전 hidden의 query와 지문 hidden의 key를 rank64로 투영해
  시작/끝 위치 CE 평균을 계산한다. 지문 위치만 softmax 후보이며 답 본문/미래 hidden은 제외한다.
  두 팔 모두 같은 head 계산·초기화;0팔에는 보조 gradient0, 양수팔에만.3을 더한다.
  head는 별도 저장하고 정상 모델 state/자유 생성에서는 사용하지 않는다.
- Stage4bl2Wa/Wb 비용8 실제 측정 후 Stage4bmWa/Wb 각각96업데이트 조건부 실행.
  평가/문서/마감 여유2700초를 남기고 예산이 모자라면 본 팔을 시작하지 않는다.
- Stage4bnW 새 지문 test256(한영각128)과 학습 표본·기존 코드640·공개DEV16/기존8·native32crop을 수집한다.
  test는 두 팔 동결 완료 후만 연다. 실제 질문/답은 비공개 local 샤드, 작은 집계·해시는 Git.

### 5. 판정

구조·마스크·미래누설·동일 초기화·모든 원본 SHA·0/양수 gradient 선결이 하나라도 틀리면 실행 장애다.
새 source test의 문자 정답 일치·token F1·빈답·종료·위치 정확도를 각각 보고한다.
위치 정확도나 source 정답 일치를 의미적 정답/세계 지능으로 부르지 않는다.
비교는 동일 자료/초기화의 DIRECT_PAIRED이며 source 문서 root bootstrap95% 구간을 쓴다.
이 조건의 학습 seed 분산은 미측정이므로 기존 nats 자나 고정0.024를 새 정확도에 대입하지 않는다.
실용 후보는 새 자료 자유 답 개선과 native 보존·기존 능력 대가를 함께 판독한 뒤만 남긴다.

### 6. 비용·실행·한계

CPU 선별 예상1~3분, 비용8 두 팔 각각수분, 전체 두 팔·평가 약30~60분은 사전 추정이다.
실제 비용8이 정본이며 VRAM은 torch reserved/전체 GPU 여유와 구별한다.
20MB 미만 JSONL 샤드, 새 namespace, 입력대기0, 명시적 execute/실행기한이 필수다.
선택된 기존 공개 COQA는 번역 오류·원천 정답 오류가 있을 수 있고 권리 표시는 CARD_ONLY다.
새 외부 배포/정식 TRAIN_READY 선언을 하지 않는다. 정확 문서/원천 ID 겹침을 막되
언어 간 의미 유사 지문 전수 판독은 미실행이라 세계 지식의 완전 독립 benchmark가 아니다.
본75M×4epoch/300M 목표의 대체가 아니며, 코드 과제/범용 질문 결과를 따로 낸다.

### 7. 실행 이력

2026-10-15 착수: 공개 원형 읽기 재고에서 첫 질문의 정합 후보 EN2821/KO1636을 확인했다.
아직 새 원천 제외·실제 quota·자료 동결·GPU 학습 효과는 NOT_RUN이다. SH는 CPU 계약 뒤 작성한다.

21:14 갱신: CPU12/12와 새 동결이 완료됐다. 중복/옛 원천 제외 뒤 EN2608/KO1540 중 한영각
train1024/dev128/test128을 선택했다. 코드1024를 더한 train3072의 실제951337x/14866지도,
4pass96회의3805348x/59464지도+native786432를 각각 기록한다. 새7SH 작성·등록, GPU는 아직0이다.

### Stage4bl0Wb~4bnWb 실행판 수리

GPU 전에 CPU mock으로 `torch.manual_seed`의 CUDA seed 호출1을 발견했다. v1 코드/자료/두 CPU 원형은
첫 커밋a15b826으로 보존하고 v1 비용/학생/평가5SH는 실행하지 않고 hold로 둔다.
독립 실행 adapter `diag_p106b_grounded_span_execution.py`는 같은 v1 source SHA/CODE를 먼저 검증한 뒤
새 `p106b_grounded_span_exec_v2_s1337` 보고·가중치만 쓴다. source JSON을 새 코드로 위장하지 않는다.
head 초기화는 CPU default_generator만 fork 안에서 초기화하고 CPU/활성 CUDA 상태를 전후 assert한다.
그 외 자료/배치/학습률/보조목적/96회는 같다. 새 CPU16→source계약→비용8 두팔→전체 두팔→평가 순이다.

실제 CPU16/원천 v2계약은 cd1c8a2로 보존했다. 전수 정적은 `--arm`을 위임 함수만 읽는 구조를
선언 미사용으로 판정했다. 공용 검사기를 바꾸지 않고 비학습 단계의 arm 혼용을 명시적으로 거부하고
선택 팔을 로그에 표시하는 새 실행 v3를 준비한다. 자료는 v1 SHA4C77034473A4 그대로다.
Stage4bl0Wc17CPU→bl1Wc 새계약을 추가한다. 아직 한 번도 실행하지 않은 두 비용/학생/평가 SH는
현재 새 v3 CLI를 첫 실행하므로 이름을 유지한다. GPU 결과 v1/v2는 존재하지 않는다.

### Stage4bnWc — 같은 질문의 원답 CPU 재집계

두96회 팔 완료 뒤 Stage4bnWb는 고정 부모/두 학생의 자연 test256·train32·기존code640·DEV16/기존8을 수집한다.
그 뒤 독립 `summarize_p106b_grounded_span.py`와 CPU회귀4건을 통해 동일 질문/지문/gold/root·원집계 일치를 검증한다.
부모→각학생/학생0→.3의 문자일치 차이를 문서root 2000회/seed20261016 bootstrap95%로 기록한다.
언어별128과 전체256을 분리하며 학습seedσ·세계정답/완전언어독립구간이 아니다.
정답률에 무관한 한영 root 정렬위치0/32/64/96의8질문을 세 endpoint와 함께 private 표본으로 남긴다.
실제 답의 의미·문맥 적합성은 별도 후행 판독이며 실시간 재생성/데이터 격리·모델 자동선택에는 쓰지 않는다.
새 CPU SH는 `run_P106B_Stage4bnWc_grounded_span_paired_readback.sh`, 예상수초~1분/모델0이다.

21:53 회수: 두 비용8은165.014/163.751초·reserved3146MiB이며0/양수 보조 갱신을 확인했다.
두 full96회는322.510/321.933초로완료했고 source 실제3805348x/59464지도+native786432가각각일치했다.
DEV 최종SFT2.05749/2.06581, 위치 양경계0/11 of256이다. aux로실제답이개선된다는예측은아직미검증이다.
native32crop은3.50432→3.53992/3.54202로대가가있고모든96회clip1을기록했다.
새 원답 수집은 진행 중이며 위치/teacher-forced CE를자유답/세계지능으로승격하지않는다(결과101§152~153).

## Stage4bo — 기존 학습된 학생의 자연 QA 출발점 비교(새학습0)

### 왜 / 선택

Stage4bnWb/Wc는 부모/일반SFT/위치SFT의 새 source 문자일치0/12/13 of256,
상한도달255/4/6을 회수했다. 같은자료 보조 추가차이 구간에는0이포함됐다.
고정8질문의 비맹검 문맥판독은 일반SFT의 Latin이름/라시드 같은 동의 별칭을 문자채점이 놓치고,
위치팔이 저자 대신 아버지·대상 대신 장소를 답하는 문제도 보였다. 새 단어오류 목록을 만들지 않는다.

| 안 | 실제 수행 | 장점 | 단점/영향 | 비용 |
|---|---|---|---|---|
| 1·선택 | 기존 LARGE binding/상태0/작은binding 학생3개를 같은64질문에 놓고 출발점을 확인한 뒤 지문별다중QA 준비 | 이미 배운 조회/상태 능력을 재활용할 가능성·추가학습0 | 서로다른 학습이력이라 구조/단일손실 인과비교 아님 | CPU수초/GPU약3~10분 추정 |
| 2 | 현재 span0에서 바로 교사 질문·답2개 생산 준비 | 준비가 빠름 | 더 강한 기존 출발점을 놓칠 수 있음 | 교사pilot후 본생산 비용 실측 |
| 3 | 기존8M에서 native보존을 섞은 NTP/MTP 후속 | 규모/학습목표 비교 | 문맥부족/자료편중은 그대로 | 수시간 단위·새비용 선결 |

1번은 사용자 현재 주도 실행 승인 내의 보수적인 선결이다. 다음 다중QA의 상세 설계는
기존학생64답과 교사 소형pilot 결과를 회수하며 고정한다. 본75M×4/300M 목표는 그대로다.

### 영향도·범위

| 경로 | 동작 | 근거 | 제외 |
|---|---|---|---|
| diag/test_p106b_foundation_panel.py와 새bo SH | 독립 신설·한정실행 | 내일17시까지 주도 실험 승인 | 기존model/공용검사기/환경수정0 |
| 기존3CPT·QA원천·nativeval | 읽기만 | 현재 TinyLM 능력 개선 비교 | CPT/캐시/원문덮어쓰기0 |
| 새evidence/local와 작은report·계획/결과/WIP/인계/TSV | 새원형/집계/기록 | 현재 작업 절차 지시 | 외부전송/다운로드0 |

코드: 기존 FP32_MATH greedy 생성 함수를 재사용하며 몸체/추론API는 바꾸지 않는다.
데이터: 이전 test256을 이번에는 부모 선택용 DEV64로 명시 재분류한다. 지난 첫 대조를 소급취소하지 않지만
다음 선택의 독립최종test로 다시 주장하지 않는다. 언어별root정렬0,4,..124의32개씩·같은64질문이다.
평가: 원래부모/현재span0의 같은답은 이미 저장된 원형에서 재사용하고 신규3CPT만 실제생성한다.
검증: CPU의선택/원형매칭/부모SHA·실제cfg·토크나이저·무학습 본체SHA 보존을 확인한다.
문서: P106B/결과101/기준표·방법론/COMPASS·인덱스/TSV로 관측을 함께 연결한다.
부채: 작은DEV64와 비맹검8질문을 일반 지능/세계정답/학습seed독립판정으로 쓰지 않는다.
권한: 2026-10-16 17시전만; 보호TinyDataset/사전·기존CPT/원로그·타원장·환경·외부 게시 제외.

### 계약과 판정

`p106b_foundation_reading_dev64_v1_s1337` 새출력, 원본 source4C770344와 현재 source평가 SHA를 고정한다.
LARGE binding auxdense100·상태 aux0·작은 binding auxdense100의 정확 report/CPT SHA를 확인한다.
세모델의 실제 saved cfg를 사용하되 dense14/32768chat32/R1/seq1024와 MTP-off 조건을 확인한다.
생성은같은FP32_MATH·greedy·maxnew64·EOT stop이며 auxiliary head는 읽거나 사용하지 않는다.
새CPT/optimizer업데이트0, 생성 전후 본체fingerprint동일이 필수다.
문자일치/F1/상한·별칭/질문관계 판독은별도이며 자동점수만으로 부모를 승격하지 않는다.
예측: 기존조회에강한학생이 자연지문관계도더잘구분할수있지만,그효과가전이되지않을가능성도높다.
부모가달라결과는 DESCRIPTIVE_ONLY다. 새GPU최대30분·마감여유를두고실제비용을회수한다.

앞source대조결과(§154): 문자0/12/13of256·상한255/4/6·기존code0/280/285of640·기존8은0/1/1이다.
추가위치보조차이+.00391의구간[-.01953,.02734]에0이있어추가승자로채택하지않는다.
비맹검8표본에서별칭답을문자채점이놓치고관계오답도확인했다. 단일질문학습이관계일반화를해결한다는예측은미충족이다.
bo 최초CPU fixture가canonical content블록대신문자열을써서오류를냈고모델전에수정했다.
수정CPU4/전수68PASS·0ERROR·6NOT_RUN뒤boW를실행한다. 공용검사기/기존모델수정은없다.

## Stage4bp — Gemma 지문별1QA/2QA 대응 생산성 pilot(학생학습0)

### 이유와 방향

boW는94.480초·추가3모델의모든몸체SHA불변으로완료했다. 같은DEV64에서현재span0은4/64,
기존LARGE/상태/작은binding은각0/64문자일치였고표본에서도더좋은자연QA출발점이보이지않았다.
다음공통부모는현재span0(CPT SHA180104A965CAA84379802D9862A74B59895537EB8B8905DA6E0AA84293E91337)을선택한다.
전체지능의최선판정이아니며보조.3도승격하지않는다. 부모/토크나이저는계속동일dense14/chat32다.

현재문제는단어불량목록이아니라‘저자/아버지,조사한사람/조사대상’의관계혼동과모호한번역질문이다.
교사는원문지문만읽고명시적주어·관계를가진새질문과짧은답을쓴다. 원래QA정답/사적사고를추가근거로주지않는다.
소프트웨어가같은완전지문을학생에게보여주고canonicalJSON/ChatML·역할/출처를포장한다.

### 영향·권한

독립p106b_dualqa_teacher.py/diag/test와bp0W/bpW SH·새HF/evidence만신설한다.
기존Gemma프로필/llama-b11396/모델·원형·환경·공용검사기는수정하지않는다.
현재주도실행승인내교사단독CPU/GPU이고학생학습/CPT0·다운로드/보호원천/외부전송0이다.
자료는기존QA동결train에서고른8지문(한영각4)만사용하며원문바이트/소유계보를보존한다.
CPU회귀·토큰/마스크·프로필계약이선결이다. code/모델자산SHA와실제sampler/상한을보고한다.

### 고정 설계

- 새tag `p106b_dualqa_teacher_pilot_v1_s1337`; 원본source4C770344 불변, 선택8은학습용문서에서source token768이하.
- 한Gemma4 Q4_0+같은MTPdraft2/server b11396. ctx8192/총출력3072/사고요청256을server/request양쪽에명시한다.
  기존프로필상수1024는수정하지않고프로세스한정scope로256을쓴다. T1/p.95/k64/minp0/pres0/repeat1은같다.
- 1QA→2QA,2QA→1QA 두순서·각같은8지문으로총32원요청이다. 비교용반복은생산corpus로편입하지않는다.
  같은source/attempt는같은seed·새messages/cache_prompt=false·이전대화0이다.
- 교사FINAL은 `Q1:/A1:/[Q2:/A2:]/NOTE:` 시작라벨만쓴다. datasetJSON/ChatML/닫는태그요구0.
  근거가부족하면전체 `STATUS: INSUFFICIENT_SOURCE`로스스로거절할수있고그경우재시도하지않는다.
  Q2는독립적으로대상을식별하고다른사실을묻는다. 이다중사실생산계약에서만완전동일Q/A필드의충돌을회복한다.
  자유원천을유형추정하는기능이나단어불량목록은없다. 모든구조/길이/동일필드회복은최초포함총3시도를공유한다.
- 질문/답각학생48토큰·완전2턴입력1024이하를코드로검사한다. 원문절단0·길면새QA만짧게재요청한다.
  reasoning은raw에따로보존하고학생messages에는없다. 사고채널실제토큰수가없으면미계측으로남긴다.
- 1QA/2QA 각각완료QA/s·assistant지도/s·실제대화x/s·교사completion/s·시간·미수락비용을분리한다.
  2QA가2배빠르거나300M공급문제를해결한다고미리주장하지않는다. sampleVRAM/누락은전체peak안전과다르다.
- 출력원형/사고/QA는새ignoredHF·각20MB미만샤드. 실제Q/A는로그에도보여주되원문전체는Git로그에반복하지않는다.

### 판정·다음·한계

동일원문범위/마스크·완결라벨·양언어학생형식이붙는지가기술선결이며정답성은자동심사하지않는다.
작은pilot뒤실제Q/A를문맥과읽고반복원천·모호한주어·관계문제를보고한다. 코드의문자검사는의미PASS가아니다.
기술/생산성이허용하면같은공개지문에서교사Q1반복대Q1/Q2의두턴교육을조건부준비한다.
그경우반복대조의동일답은의도된고정계약이므로재생성하지않고,두팔micro8×accum16/ckptON/4epoch·native보존을맞춘다.
범용75M×4/300M은대체하지않고다음고유test문서는새로확보한다. pilot자료는반복측정용이라학습에쓰지않는다.
예상GPU2~10분·hardcap3600초,실제상한/수락비용이정본이다. 세계정답·형식일반화·2QA학습효과는아직NOT_RUN이다.

### Stage4bp0Wb / bpWb — 선택 메타데이터 NOTE 복구(구판 불변)

첫실측은94요청·4대화수락/2QA수락0·347.519초/종료8이었다.
원형판독은82개가Q/A를썼는데NOTE생략으로실패했고8개가FINAL사고/서문연속이었다. 단계별원형/구판음성은그대로다.
새 `p106b_dualqa_optional_note.py`는필수Q/A와선택NOTE를분리한다. NOTE가없으면코드가빈메타데이터만채운다.
필수답누락·중복필드·사고서문은여전히거절한다. STATUS부족선언은추가메모가있어도재요청하지않는다.
자동문제단어/의미판정은없다. 새프롬프트는선택NOTE·간결한명시사실선택·자료기준의시간범위를명시한다.
서버/요청사고256·MTP2·sampler/ctx/출력상한·source8/seed(root/attempt)는구판과같다.

bp0Wb: CPU8회귀와구판94응답read-only재판독. 새GPU0·원형수정0이다.
구실측에없던요청시간을빼거나가상조기종료속도를실제속도라고말하지않는다.
bpWb: 새namespace `p106b_dualqa_teacher_pilot_v2_s1337`에서같은8지문/두순서32원요청을실제로재시험한다.
구판 `p106b_dualqa_teacher_pilot_v1_s1337`·helper/diag/test/보고는수정하지않는다.
필수코드/입력원형검증·마스크·전수정적이먼저이며새수락/속도와내용판독은각각다시기록한다.

## Stage4bq~4bu — 지문별 두 QA 생산과 Q1반복/Q1Q2 교육(조건부)

### 왜 / 비교안 / 선택

v2실측은같은8지문32논리요청을34실제요청으로32대화/48QA연결했다. 사고서문은수락하지않고NOTE만코드기본값으로둔다.
2QA는두순서QA/wall초에서약2.1배·assistant/request초에서약3.3배였으나대화x/request초는약1.1배다.
출력속도자체2배나75M공급해결을주장하지않는다. 내용/현행세계정답은아직별도다.

| 안 | 실제 학습 | 장점 | 단점/범위 | 예상 비용 |
|---|---|---|---|---|
| A·선택 | 같은teacher Q1/A1을2턴반복하는팔 대Q1/A1→독립Q2/A2팔 | 같은지문/대화수/2턴/업데이트에서질문대상다양성비교 | 답길이·실제토큰도변해순수wording효과아님 | teacher실측기준약2h+두학생각10~20분 추정 |
| B | 현재원형QA만더반복 | 추가teacher비용0 | 한지문한질문/모호한번역을유지 | 학생수십분 |
| C | 큰8M에서native보존/MTP부터비교 | 넓은자료·학습목표실험 | 현재문맥/질문관계문제와자료편중남음 | 새비용실측필수·수시간 |

선택A는단순생성량증가보다같은자료에서질문을구별하도록가르치는가설을겨냥한다.
예를들면저자와그아버지를구별하거나같은인물의나이와등정연도를다르게묻는다.
Q1반복팔의동일답은의도된생산자계약이므로재생성하지않는다. 자유질문의유일답유형을추정하는기능은없다.

### 영향도·권한·선결

새bulk/source/course/train/eval/test와bq~bu SH·새HF/새CPT/작은근거만쓴다.
현재주도실험승인내이며V1/V2교사코드/원형·기존CPT·환경/공용검사기·보호데이터는수정하지않는다.
교사단독생산을먼저동결하고두학생은같은부모/데이터를읽는다. source/type/mask·실제비용8이본학습선결이다.
코드/데이터/테스트/정본문서/유지부채를분리하며,기존encoder/optimizer/known-code binding helper만재사용한다.
새생산Corpus는본75M×4/300M의대체가아닌자연QA학습원인대조다. 원천/생산물은Git제외·20MB미만샤드다.

### 자료와 생산

- 공통부모는source0 SHA180104A965CAA84379802D9862A74B59895537EB8B8905DA6E0AA84293E91337.
  보조.3·기존3code학생을전면채택하지않는다. optimizer는각팔새로시작한다.
- 목표지문 train한영각768(1536),dev각64(128),새test각128(256). 같은source의pilot8은제외한다.
  train/dev는기존동결의해당split,새test는보유공개원형에서모든기존source지문과정확24단어/원ID겹침을제외해확보한다.
  언어간의미중복/원래pretrain중복은미감사이며세계지능의완전독립benchmark로쓰지않는다.
- 원문전체를보존하며768이하원문token예비조건과실제1024대화검사를병용한다. 공급부족시자동축소/복제로채우지않는다.
  source/dataID·출처/개정/권리미확정표시·원문SHA·교사raw/thinking/final·후행교정가능계보를보존한다.
- 같은v2GemmaMTP2·ctx8192/출력3072/사고요청256·같은sampler,요청별새문맥/새source seed다.
  Q/A각48studenttokens·원문불변·구조/길이/명시다중사실완전중복의회복을최초포함총3회로공유한다.
  typed source부족은재시도하지않고다음reserve지문으로넘긴다. 단어불량목록/실시간의미심사0.
- 양팔은같은teacherQ1을첫턴으로쓴다. 두번째user에도‘앞서제시된자료를기준’이라는코드소유scope를넣는다.
  반복팔은같은Q1/A1,다양팔은명시대상을가진Q2/A2다. 둘다정확2assistant턴이며전체history1024이하다.
  교사가완료한지문만양팔에같이들어가고반복팔형식도생산중검사해후행길이실패를미리막는다.
- 긴창은수십지문별create-only batch/report를봉인한다. 시간창끝은정상보류로기록하고새batch로명시재개한다.
  실패원천의같은3시도를창재개때다시초기화하지않고소진기록을이어받는다. 기존HF/캐시/원형덮어쓰기0.

### 학생 계약

- train teacher대화1536+검증된code4096=5632행,4epoch176업데이트가목표다.
  code는known binding3072(4view root그룹)와기타rule1024를양팔같이사용한다.
- m8a16/ckptON·seq최대1024/right128·Adam5e-5/MuonRMS4 2e-4·matrixWD0·clip1·native8x1024 CE가중치1.
  양팔의실제SFT/지도/native토큰과warmup/clip/reserved·시간을분리해실측한다. 패딩상한23.07M을실제300M으로부르지않는다.
- 기존조회능력보존을위해이미좁은코드과제에서확인한학습전용1538계수binary query-suffix 보조1을양팔동일하게쓴다.
  정확코드producer의label/위치만사용하며teacherQA에는이분류를추정/적용하지않는다. 자연QA정답판독헤드가아니다.
  앞서미승격한큰source위치head.3은사용하지않는다. binary head도정상자유생성에는없다.
- 실제양팔cost8·부모/RNG/마스크·0미래누설·전체노출검산/예산·마감45분여유뒤full을연다.
  epoch1~4의새CPT를남길수있고구판/부모는불변이다. 명시선택은DEV만으로하며test선택누설을피한다.

### 평가·판정·한계

새지문256에서teacherQ1/Q2의gold-history와실제학생이력2턴을명시적으로따로수집한다.
실제대화는한영128씩전체256/512assistant답이며공용first8 slicer를쓰지않는다.
원래공개firstQA bridge와known-code640·기존8·native32crop은각영역으로분리한다.
teacher문자일치/F1은의미정답보장이아니고별칭/관계/형식/반복의고정표본후행판독을따로둔다.
반복/다양의답길이·실제tokens차이가있어질문다양성하나만의순수인과크기를주장하지않는다.
내용개선과기존능력/언어보존이함께좋아지는지를보고,새MTP/재귀/폭은이대조에혼합하지않는다.
새source공급/producer/encoder CPU→bulk→course/wire→양cost8→두176full→실제대화/원형paired 회수순이다.

### 학생 코드 작성 전 보완 — 네 epoch의 정보·노출 주변분포 맞춤

기존‘Q1만반복’팔은Q2를전혀배우지않아새질문내용을배운효과와대화대비효과가섞인다.
이미위임된실험준비범위에서추가생성/GPU비용없이대조를보완한다. producer/teacher원형/CODE는그대로다.

| epoch | 반복 조건 | 서로다른질문 조건 |
|---|---|---|
| 1 | Q1→Q1 | Q1→Q2 |
| 2 | Q2→Q2 | Q2→Q1 |
| 3 | Q1→Q1 | Q1→Q2 |
| 4 | Q2→Q2 | Q2→Q1 |

각Q/A는양팔모두총4번,첫/둘째위치각2번,같은지문은4번노출된다.
canonical ChatML의4epoch총실제x·assistant targets·언어량도동결때실제로대조한다.
같은Q/A의쌍과순서만코드로바꾸며새정답을추측하지않고교사재요청도하지않는다.
이원형은생성pilot반복을훈련에재사용하는것이아니라별도생산된같은두QA의정해진epoch view다.
생산중검증한기본2턴에더해네학생view를동결시다시검사한다. 원문/메타데이터/출처는보존한다.
반복조건의동일답은여전히의도된코드소유계약이며자동재생성하지않는다.
실제test는원천별양순서의2턴을모두평가하고문서root별로묶는다. 256문서×2순서×2답=1024실제답/endpoint다.
gold-history와실제모델history를분리하고이반복view를독립문서수로부풀리지않는다.

### 실행 파일과 실제 연결 선결(2026-10-16, 실행 전)

bs0W는새course/runtime/eval CPU17건과두check-only를실행한다. GPU/원천생산은하지않는다.
bs1W는생산종료·6개언어/split목표충족뒤만새학생자료를동결하며진행중batch를읽어승격하지않는다.
bs2Wa/b는양팔각8회비용만측정한다(CPT0). btWa/b는같은초기부모에서각176회/4epoch다.
buW는3endpoint의새지문256×양순서×2턴=1024실제답과골드이력둘째답512개를분리한다.
실제첫답이틀리거나빈문자열이어도그대로둘째문맥에넣고골드로대체하지않는다.
보존640코드문항은이미여러연구에쓴개발지표이며새독립test라고쓰지않는다.
부모·교사·토크나이저·encoder·공용함수의CODE와원천/라벨/SHA를동결에포함한다.
실제x/assistant/native노출·학습전용queryhead의인과위치·전역update분모의gradient일치를CPU로검사한다.
등록조회에나오는176×8×16×1024=23.07M은패딩상한이지실제처리토큰이아니다.

### buWb 후행 원답 검산(실행 전)

3endpoint의실제1024답/골드둘째512를원답에서다시집계하고문서root별로네실제답을묶어paired bootstrap한다.
둘째턴의학생첫답은모델마다달라지는처치결과이므로user/source/gold일치를검사하되assistant이력을억지로같게만들지않는다.
각언어128문서에서고정정렬위치0/32/64/96의8지문을후행판독패킷으로보존한다(순서0의두실제답,3모델48답).
이는새문항정답성을자동심사/격리하는기능이아니고의미정답/세계지식미검증표시를유지한다.
CPUsummarizer/test와새buWb SH만추가하며모델0/훈련0이다. 학생/교사동결CODE는변경하지않는다.

### bs0Wb 실제 부모·코드 계약의 CPU 배선 선결

교사생산중에도GPU를함께쓰지않고선택Source0CPT를CPU에만읽어실제cfg/본체fingerprint를확인한다.
이전code자료에서정확3072binding+1024rule을선택하고검증된3072label의인과위치를실제encoder로검산한다.
새부모CPUwire namespace에작은해시보고만남기며모델forward/optimizer/CPT/GPU0이다.
고정fixture만으로실제부모형상·원천메타데이터연결을대체하지않기위한짧은추가검증이다.

## Stage4bv0W / Stage4bvW / Stage4bvWb — TEST를 열기 전 DEV 후보 잠금과 별도 후행 비교

실행전선택: A(선택)는같은저장epoch1~4중source DEV CE최저만기계적으로잠그고,기존최종4epoch일차평가뒤그후보도별도로평가한다.
새학습/CPT추가는없고최대두추론endpoint의약20~35분을예상한다. B는최종4epoch만유지(추가비용0·중간종료가능성미검증),
C는답평가전에학습을더함(수십분~수시간·새조건/노출변경)이다. 현재repeat의DEV최저epoch2관측을활용하는A를선택한다.
CODE/원형/가중치수정없이새selector/eval/readback와CPU회귀·SH·소형근거만추가한다. 현재학생/교사동결CODE와일차평가는불변이다.
권한은오늘17시주도실험안이며GPU/데이터소유/비교/증거/정본문서5축을분리한다. 테스트선택·온라인의미심사는추가하지않는다.

- bv0W는양full176보고의4개epoch source_ce만읽어최소(동률은이른epoch)와CPT/SHA를CPU에서잠근다.
  primary TEST평가가이미시작된폴더가있으면이잠금은금지한다. codeCE/native/TEST점수로선택하지않는다.
- bvW는primary완료후같은새256지문/양순서/실제1024답·gold둘째512·원공개bridge/기존코드640/native/8문항을같은생성경로로평가한다.
  선택epoch4이면기존primary결과를정확참조하고모델을중복로드하지않는다. 별도어휘생성에보조head는쓰지않는다.
- bvWb는문서root paired구간과같은고정8지문을후행패킷으로남긴다. 개별선택epoch/노출이다르면동일학습량대조로주장하지않는다.
  최종4epoch primary결론을이secondary로교체하거나최대TEST점수를기본모델선택규칙으로쓰지않는다.
- source pseudo-target문자/F1과실제의미/세계정답은계속구분한다. 새후보의실제학습량과품질은각CPT/report가정본이다.

## Stage4bwW / Stage4bwWb — 정상 반복 질문의 사전등록 후행 대조

primary TEST를아직실행하지않은시점에추가등록한다. 혼합Q1Q2만보면‘현재질문을읽기’와‘무조건앞답을바꾸기’를혼동할수있다.
A(선택)는같은256source/교사Q/A를Q1Q1·Q2Q2의정상반복으로도렌더링해부모/두최종학생의실제2턴을추가평가한다(추가약15~30분추정).
B는현재혼합질문만평가(비용0·항상바꾸는지름길미검증),C는새수정대화를학습한뒤평가(자료/학습조건추가)다.
가중치를바꾸지않고현재질문사용을구별하는A를우선한다. 교사/학생/원형CODE는수정하지않고새control helper/test/diag·SH·보고만쓴다.

- 같은교사두QA를코드가정해진repeat factory로묶는다. 동일질문/동일근거의같은답은정상이며자동재생성하지않는다.
- 첫답은실제학생출력으로보존한다. 첫답이틀렸다면둘째에고칠수도있으므로문자복사율을품질판정으로쓰지않는다.
  first/second 문자·양답일치·첫오답후회복/퇴행·단순복사는각각기술지표다. 의미/별칭/세계정답은후행판독이다.
- 혼합과반복의첫user/gold가같고같은CPT의첫실제답도같은지별도검산한다. 차이가있으면숫자경로/조건의문제로보고한다.
- 반복도문서256×양순서×두턴=1024실제답/endpoint와gold둘째512를분리한다. 모델별비교/CI는문서root단위다.
- DEV선택후보는혼합/반복을같이읽을수있으나일차최종4epoch와섞어승격하지않는다. 새로운과제를학습하거나TEST로선택하는절차는없다.

### Stage4bq~bw 현재 회수(2026-10-16 03:40)

teacher1920지문/3840QA·동일marginal코퍼스·양cost8/두full176·primary1024답/문서paired·정상반복control을종료0으로회수했다([101 §160~166](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)).
질문전환시복사87대정상반복395/512로조건반응가설은지지됐으나실제literal22/1024·고정8문맥의관계값오류로내용개선은충분히확립되지않았다.
반복학생495/495는조건무시를보였다. 모든잘못된문구목록/의미자동재시도는추가하지않는다.
현재bvW는TEST전잠근epoch2/2후속평가중이며bwWb joint검산뒤관계필드선택과재표현동일의도를겨냥한독립후속을정한다.

## Stage4bx~4bz — 검증 가능한 관계 필드·재표현·교정 문맥의 독립 교육(실행 전)

### 목적과 선택 근거

현재 모델은 질문이 바뀐 상황에 반응하지만 필명 대신 작품명, 출판연도 대신 생년을 고른다.
금지어 탐지나 답변 문장 꾸미기가 아닌, 현재 질문이 요구한 관계와 값을 연결하는 학습을 시험한다.
이미 살펴본 256지문은 이후 설계의 개발 근거로 취급하며 새 연구의 독립 TEST로 다시 주장하지 않는다.

| 안 | 구체적 방법 | 장점 | 한계/비용 |
|---|---|---|---|
| A·선택 | 코드가 만든 가상 작가 자료에서 본명/필명/책/출생·사망·출판연도를 묻고, 정상 반복·동일뜻 재표현·다른 필드·잘못된 첫답 교정을 섞는다. 같은 자료에서 fact선택 보조0/1을 비교한다. | 관찰한 잘못된 필드 선택을 직접 겨냥·정답과 교정 이유를 코드로 계산·교사 생성비0 | 합성 과제 성공이 실제 지문으로 전이되는지는 새source TEST로 확인해야 한다. 구현/CPU 약1~2h·각학습20~40분 추정, cost8 뒤 재산정 |
| B | 보유 공개 CoQA의 원래 여러 QA를 실제 역할별 대화로 정규화한다. | 실제 표현·생략형 문맥을 넓히고 교사 비용 절약 | 원천 규모/번호 파싱/문맥예산 재고가 먼저며 원문 번역 결함도 남는다. 이번에는 별도 CPU 재고까지만 검토 |
| C | 기존 언어모델 학습량을 추가한 뒤 같은 SFT를 다시 수행한다. | 일반 표현/기초 언어 부족을 시험 | 수시간·cache/토크나이저/검증누설 선결, 현재 필드 오류를 직접 분리하지 못한다 |

A는 좁은 문제를 정확한 정답으로 먼저 가르치고, 실제 지문에서도 개선되는지를 확인하는 경로다.
사용자가 승인한 코드 정답형 증강/C1·C3와, 적용 가능한 질문/오답을 검토하라고 한 C2+C3의 구체 범위에 해당한다.
자유 질문을 자동으로 분류하지 않는다. 생산자가 실제 graph/요청 필드/정답을 알고 있는 자료에만 아래 계약을 쓴다.

### 권한·영향도

- 오늘2026-10-16 17시까지 위임된 연구 범위다. 16:15 이후 새 GPU 작업을 시작하지 않고 마감2700초를 남긴다.
- 새 helper/diag/test/SH·새HF namespace/CPT·작은 근거/정본문서만 추가한다.
  현재P106B completed/frozen CODE와 tinylm 기본/환경/공용 검사기/원본cache/기존CPT/타WIP는 수정하지 않는다.
- 보호 TinyDataset/사전/신규다운로드/외부서비스/게시/cleanup대행은 없다.
- 동일 초기화·자료·마스크·실제x/지도/native·평가경로를 맞추고 보조0/1만 바꾼다.
  가중치·저장·GPU예약·언어보존·정답 계약·실제자연지문은 별개 지표다.
- 코드/데이터소유/비교/자원/정본문서5축을검토한다. 합성정보를 새 세계지식이나 본75M×4/300M으로 합산하지 않는다.

### 자료 생산자 계약

1. 중립 graph train8192개×한영2=16384대화/epoch, dev128/test256중립graph×한영2를 별도로 둔다.
   중립root 기준으로 양언어를 같은split에 묶고 이름·책·값의 조합과 source bytes가 겹치지 않게 한다.
2. 각 graph는 가상 작가2명의 본명·필명·책제목·출생/사망/출판연도(총12사실)를 갖는다.
   연도는 출생<성인출판<사망을 만족하고, 같은 자료의 날짜·이름·책값은 구별되게 한다.
   가상 자료임을 학생에게 명시하며 실제 인물/세계 사실로 주장하지 않는다.
3. 사실은 문장으로 렌더링하고 순서를 graph별로 섞는다. 전체 source를 보존하며 실제 ChatML1024 초과는 거절한다.
   20MB 미만 JSONL shard·graph/문항/템플릿/char범위/seed/solver 계보와 실제 tokens를 저장한다.
4. 네 epoch view는 (a)같은 질문/답 반복, (b)같은 사실을 다른 문장으로 질문, (c)다른 관계/인물/날짜 질문,
   (d)첫답에 다른 필드 값을 잘못 말한 뒤 사용자가 요청 필드를 다시 명시하는 교정이다.
   예: 책 출판연도 요청→생년 오답→“태어난 해가 아니라 책이 나온 해를 물었습니다”→출판연도.
5. (d)의 첫 오답은 문맥일 뿐 labels는 전부 IGNORE(종료 포함)다. 올바른 마지막 답만 지도한다.
   첫/둘째 역할의 segment와 실제 target 수를 검사하고, 정상 답 반복은 재생성하지 않는다.
6. 정답은 코드의 graph/질의계획으로 계산한다. 템플릿별 한영 의미와 독립 fixture를 검토한다.
   임의 자연문장의 의미 검증기·모든 오조어 목록·실시간 교사/GPT 전수심사를 만들지 않는다.

### 공통 부모·교육 조건

- 부모는 TEST 전 source DEV로 잠근 contrast epoch2, SHA B1484726ACF786AF6B65F8A94AF66A0E8D192897BFF3553B9EE2A7EF11559515다.
  TEST의 최고점으로 바꾼 선택이 아니다. 두팔의 본체/CPU·CUDA RNG를 실제로 비교한다.
- 기존 teacher1536대화와 code4096도 보존한다. teacher는 네view(repeat0,contrast0,repeat1,contrast1)를 epoch별로 한 번씩 쓴다.
- 총 train22016대화/epoch·m8×accum16·4epoch688업데이트가 예상된다. 실제 count가 다르면 자동 축소하지 않는다.
- LR Adam5e-5/Muon RMS4 2e-4·matrixWD0·clip1·ckptON·compile default·right128/max1024를 유지한다.
- 기존 검증된 code binary query 보조1과 native8×1024 CE1은 양팔 같다.
  native688×8192=5636096은 SFT와 별도로 보고하며 원본bin은 읽기전용이다.
- 새 fact선택 보조는 source 문장 hidden의 평균 key와 답 이전 query의 rank64 투영 점수로
  주어진12사실 중 코드가 아는 목표 사실을 맞힌다. 같은 forward를 양팔에서 계산하고 loss 가중치만0/1이다.
  query는 허용된 assistant 답 직전이고 source 범위는 그보다 앞이다. 오답을 IGNORE한 turn은 이 보조도 지도하지 않는다.
  각 row의 허용 query 평균을 구한 뒤 전체 update의 known row 수로 정규화한다.
- 예상 보조계수는2×768×64=98304 FP32(0.375MiB)다. CPU/CUDA RNG 불변을 검증한다.
  이 head는 일반 추론에서 사용하지 않고 세계 정답 검증기/자유 답 채점기로 쓰지 않는다.
- old word/query/native/새fact의 각 denominator·양수/0 gradient·마스크/미래누설·실제 노출을 CPU로 확인한 뒤 각 cost8만 먼저 수행한다.
  cost/예산·남은평가·마감 여유를 통과해야 두688회가 열린다. epoch1~4 새CPT는 원본과 분리한다.

### 평가·새 TEST

- 합성 test는 중립root별로 묶어 한영·템플릿·다른 필드/같은 뜻/정상반복/교정을 나눈다.
  정확 출력 계약과 실제내용을 혼동하지 않고 잘못된 첫답은 제공된 오답문맥인지 실제 모델이력인지 표시한다.
- 고정 오답문맥 교정은 실제 자기오답 회복과 다른 증거다. 우선 제공된 오답+교정 요청의 마지막 답을 측정한다.
- 자연지문은 기존public원형에서 모든 이전source ID/정확24단어 겹침을 제외한 새128지문(한영64씩)을 동결한다.
  현재봐버린256은 개발용으로만 참고한다. 원래 공개 firstQA/짧은gold를 쓰며 질문·정답성/의미중복/사전학습누설 미검증을 명시한다.
  새표본 공급이 부족하면 정확 부족분을 보고하며 기존TEST를 새TEST로 재표기하지 않는다.
- 새부모/aux0/aux1의 실제 어휘답·source/코드/기존8/native32crop를 함께 본다.
  후보선택 head 정확도가 높아도 실제 답이나 세계지능으로 승격하지 않는다.
- 긍정이면 별도 새source/실제멀티턴을 확장하고, 음성이면 학습량/표현/공개role정규화(B)를 검토한다.
  MTP/재귀/폭/새양자화는 이 대조에 섞지 않는다.

### 실행 단계명

Stage4bx0W는CPU27/비로딩check-only,Stage4bx1W는새corpus동결이다.
Stage4bx2Wa/b는fact0/fact1 각cost8(CPT0),Stage4byWa/b는양688회다.
Stage4bzW 실제답/후보선택정보·Stage4bzWb root재검산은구현/회귀뒤에만SH를추가한다.

### 동결 및 평가 구현 명세(2026-10-16 04:30, TEST 실행 전)

bx1은04:23:27/종료0으로동결했다. 양팔각SFT x22070078·assistant604482·native5636096,
fact65536행/114688질의·oldbinary12288행/165748위치다. 새public공급은영어1183/한국어116중64씩선택했다.
원본/생성자료의정답성·의미/사전학습누설은여전히미검증이다.

- bz0W는5CPU회귀와비로딩check-only다. 실제첫답(빈답포함)을다음입력에넣는지,골드와분리하는지,
  제공오답교정은첫답을새로생성하지않는지,전체view/root와양언어CI단위를검사한다.
- bzW는부모/각최종4epoch를한번씩평가한다. view0~2 각각512대화의실제두답으로3072답,
  제공오답+명시교정의마지막512답,별도골드이력둘째1536답을endpoint마다저장한다.
- 실제답은FP32_MATH/greedy64·일반어휘생성이다. 학습전용facthead는생성에개입하지않는다.
  학습된head의TESTteacher-forced후보점수는따로재며자유답/정답보증으로쓰지않는다.
- 새public128·기존개발용code640·legacy8·동일native32crop를함께보고한다.
  가상과제의‘다른필드값을정확히복사’는생산자가아는12값의후행기술집계이지단어금지목록이아니다.
  임의문장의의미오답/재생성/학습제외판정에쓰지않는다.
- bzWb는원답을다시읽어카운터를검산하고중립root256에한영자식을묶어대응bootstrap4000/seed1337을낸다.
  CI는고정합성root표본의불확실성이며학습seed/세계지식일반화가아니다.

양cost8은04:31:42/04:37:11에종료0으로끝났고동일초기본체/실제자료노출을확인했다([101 §169.1](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)).
예산검사후04:37:29부터fact0 full688을시작했다. 시작은완료/실제TEST품질의증거가아니다.

## Stage4ca0W — 보유 원문 연속 QA의 역할 정규화 가능량 재고(CPU만)

관계study의선택지B에서허용한별도CPU재고다. 새모델/교사호출/데이터생성/학습은하지않는다.

| 방법 | 실제 처리 | 장점 | 한계/비용 |
|---|---|---|---|
| A·선택 | 과거source TRAIN2048개만찾아원문질문/답의1~4번이유일하고순서가맞는경우앞3QA를역할로분리한가상직렬화의크기를잰다. | 교사비용0·실제후속대화활용가능량확인·문자범위추적 | 번호가번/살/명등으로바뀐뒤쪽항목은복구하지못하며원문정답/번역은미검증,CPU수십초추정 |
| B | 숫자뒤한국어단위도번호로추정해모든항목을읽는다. | 재고범위를넓힐수있음 | 실제연도/나이/수량을문항번호로오인할수있어자동채택하지않음 |
| C | 교사가원문전체를다시읽어3대화로생성한다. | 깨진번호/불명문맥을보완할가능성 | 추가수백~수천교사요청과내용변화/파싱비용,현재는수행하지않음 |

A는재고만하는선택이다. 원형firstQA와새3턴을코드가래핑하지만실제학습코퍼스로저장하지않는다.
일반TinyLM코드/기존동결CODE/HF원본/신규TEST128은수정하거나판독하지않는다.
`p106b_public_qa_roles.py`/독립test/diag·SH·소형집계만추가하며권리상태CARD_ONLY/의미미검증은그대로다.
현재기존공개원문에서정확한oldTRAIN ID만찾으므로새독립자료량으로부풀리지않는다.
원본언어별ID가공개train/val중어디에있는지둘다찾고같은ID의다른원문이있으면오류로남긴다.
1~4번의question/answer양쪽유일한경계·증가순서·빈값·role마지막assistant를검사한다.
첫QA와원문첫정답이일치하는지확인하고3턴의x/assistant target·1024이내/초과를집계한다.
답이자료에있는정확문자여부는진단만하며의미정답/검증승인이나자동제외근거로쓰지않는다.
향후실제교육을할때는별도코퍼스/DEV/새TEST·부모·비교축을다시동결해야한다.

### Stage4bzWc — 관계 실제답의 이력/필드별 원답 검산(평가 전 추가등록)

bzWb의전체비골드(실제3072+제공오답512)root CI를실제자기이력정확도라고읽지않는다.
별도CPU후행검산에서ACTUAL_MODEL과PROVIDED_WRONG_HISTORY,정상반복/재표현/전환,
질의필드6개/언어/turn을나눠원답을집계한다. 골드이력은참고정보로별도유지한다.
같은root/언어의view0~2첫질문/정답/실제생성첫답이같은지도검사해평가배선오류를찾는다.
전체와세부그룹의CI는root를뽑되합계정답차/합계문항수로계산한다. 세부그룹마다root당문항수가다를수있기때문이다.
값은고정가상표본의대응차이일뿐다중비교보정된발견/학습seed일반화/자동채택문턱이아니다.
새모델실행/데이터교정/TEST최고checkpoint선택은없고원답과counts의일치만확인한다.

## Stage4ca1W — 공개 QA의 원천 템플릿별 오프라인 검토 패킷(CPU)

보유HotpotQA는한영각355476행이지만표본은근거없는지식QA였고,한국어template3의일부는질문이아닌서술문으로번역돼있었다.
SODA표본도실제role대화가아니라대본/서술문작성과제다. 이름만보고QA/멀티턴으로자동승격하지않는다.
이것은표본관찰이며모든template3/원천이불량이라는모집단판정은아니다.

| 안 | 방법 | 장점 | 비용/한계 |
|---|---|---|---|
| A·선택 | 보유9개Collection원형에서NQ-Open/HotpotQA/Dolly/CoQA만열메타데이터로찾아언어·원천·template별최저해시8개를보존한다. 원문과답을오프라인으로읽는다. | 새다운로드/교사비0·파일앞부분편향감소·질문손실을출처계약별로조사 | CPU1~10분추정/최대30분,표본은전수품질보증이아님 |
| B | 원천이름만으로기존QA를즉시8M코퍼스로합친다. | 준비가빠르고교사비0 | 질문누락/불명질의/서술문을그대로가르칠수있어지금채택하지않음 |
| C | 전원천을교사가다시쓴다. | 표현/질문형태를개선할가능성 | 대량교사호출/내용변화/오답전파가있으며원형직접활용가능량부터확인하는편이낫다 |

A는현재17시위임범위의CPU재고다. source_family/template_id/raw id/원문/target/revision/SHA를보존하며
보호원천/모델/교사/신규다운로드/학습코퍼스생성0이다. 기존물리원본/현재relation CODE도수정하지않는다.
전체선택원천의원형SHA를검사하고PyArrow열필터로대상가족만읽는다. 표본만새HF격리위치에20MB미만샤드로저장하며
Git에는메타데이터/카운터/원형해시만넣는다. 권리는기존CARD_ONLY·정답/번역은NOT_REVIEWED그대로다.
template별질문결함의판독은생성/학습중전수필터가아닌후행자료검토다. 잘못된문구목록/의미자동재생성/정답자동채택은없다.
이후8M한영QA소형교육또는75M부족분확대로연결하려면실제가용token·중복/원천split·과제/권리계약과별도자료동결을먼저확인한다.

## Stage4cb~4ce — 같은 정보의 epoch내 유형 혼합 대조(실행 전)

### 관측·선택·비용

[101 §173~174](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에서fact1은실제1876/3072로개선됐지만
같은질문에서첫정답→둘째오답45/512가남았다. gold첫답을주면둘째정확281이실제이력309보다작았다.
같은exact prefix의출력불일치는0이므로당장명백한gold포장/캐시불일치를찾지는못했다.
마지막epoch전부가‘첫답은틀렸으니고치기’라는수업인점이정상반복간섭을만들었는지는아직가설이다.

| 안 | 구체적 방법 | 장점 | 비용/한계 |
|---|---|---|---|
| A·선택 | 저장blocked fact1은그대로두고같은B148부모/손실/688회/네view를root별로회전시켜매epoch내각유형1/4로섞는fact1 한팔을추가한다. | 새교사/내용추가0·동일정보노출에서수업순서효과를직접겨냥 | CPU동결2~4분/cost8약5분/full약23분/두endpoint약15분추정,실측뒤예산재확인 |
| B | 먼저epoch3와4의저장답만추가평가한다. | 새학습0/약5~10분으로마지막수업영향을관찰 | 수업유형과학습량이함께달라순서인과를직접분리하지못함 |
| C | 원문2004대화를첫QA만/원래3QA로교육하는새대조를먼저한다. | 자연지문전이를직접겨냥·교사비0 | 정보/지도량/표현도달라수업순서설명과혼합됨,별도비교/미열람TEST필요 |

A를먼저하고C용원천TEST는아직읽지않은채따로예약한다. C는75M/300M대체가아닌후속소형교육이며별도계획/CPU/비용후실행한다.
후보head를참조정답검증기로사용하거나틀린문구목록을만들지않는다. normal같은답/반복은계속보호한다.

### 권한·동결·비교

- 오늘17시위임범위의새scripts/SH/HF namespace/CPT/소형근거만쓴다. 기존동결CODE/원본/HF/데이터/CPT/환경/tinylm기본/공용검사기/타WIP는수정하지않는다.
- 새tag는 `p106b_relation_interleaved_v1_s1337`이다. old `p106b_relation_fields_v1_s1337`의train을참조하고복구가능한순서manifest를새로만든다.
- 네source-root패스에서가상root index i의epoch e view는 `(i+e)%4`다. 같은root의한영자식은같은view로묶는다.
  매epoch각view4096행·root별네view각1회이며원래blocked의전체canonical row multiset/SFTx/지도/fact질의가같음을검사한다.
- 기존teacher/code재생5632행/epoch의순서계획은변경하지않는다. 같은train22016행/epoch·4root패스688회·SFT22070078/지도604482/native5636096을맞춘다.
- 공통초기부모B14847...·m8×accum16/ckptON·Adam5e-5/Muon2e-4/native1/binary1/fact1·같은기존native5504창을그대로쓴다.
  새각기다른내용을더가르치거나더많이학습한대조가아니다. padding실행량/시간은따로보고한다.
- 수학/학습함수는기존trainer와AST로대조하고course연결·출력namespace·등록코드목록만바꾼다.
  CPU multiset/패스/마스크/출처참조·체크포인트독립성을확인한뒤cost8→남은예산→full688을연다.
- 저장blocked fact1의최종SHA219EAA...과새최종4epoch를비교한다. 다음연구에서살펴본현재TEST는개발근거이며새TEST라고재명명하지않는다.
- 새가상TEST는기존root0~255와다른test index8192~8447·동일정본generator/한영256씩/네view다.
  같은source bytes중복을검사하고새세계지식/무한템플릿일반화를주장하지않는다.
- 새자연TEST는이전모든source/현재128/원천검토패킷CoQA의정확24word를제외한16지문씩32개다.
  남은엄격3QA후보에서한영각최대32(최소24)개를별도미열람reserved TEST로격리한다. 부족시학습을시작하지않고가용량을보고한다.
  raw숫자id만으로한영번역쌍을추정하지않는다. 의미/번역/사전학습누설은NOT_AUDITED다.
- actual3072/제공오답512/gold1536·이력별/필드별·첫prefix불변을새root에서도검산하고자연32·기존code/legacy8/native32crop를분리한다.
  CI는고정root표본대응기술량이지세계정답/seed일반화/자동채택문턱이아니다.
- 16:15이후새GPU를시작하지않고최소45분마감여유를남긴다. 이번에도전체smoke/정식TRAIN_READY는NOT_RUN이다.

### 단계

Stage4cb0W CPU15계약→Stage4cb1W source순서/새TEST동결→Stage4cb2W fact1 cost8(CPT0)→Stage4ccW 한팔688→Stage4cdW 저장blocked/newinterleaved실제답→Stage4ceW 원답paired검산순이다.

### Stage4cb0Wb / Stage4cb2Wb / Stage4ccWb / Stage4cdWb / Stage4ceWb — native reader 계약 복구

06:22:05의cb2W는첫update전KeyError/native_copy·종료9였다. 데이터동결v1이native_train_file/offsets/hash를복사했지만
실제reader가요구하는native_access 표지를전달하지않아복제캐시경로로잘못분기했다. 학습/optimizer/CPT0·OOM아니다.
CPU15는수학함수/순서/마스크를검사했으나실제새dict를native_reader에전달하지않았다. 전수정적도동적JSON계약을검사하지못했다.

- v1 CODE/자료/실패raw/빈cost출력을불변보존한다. 성공으로고쳐쓰거나같은namespace로다시실행하지않는다.
- 별도runtime_v2 어댑터가원래source의INDEXED_TRAIN_ONLY 값을정확히복사하고file/5504offsets/두hash가동일한지먼저검사한다.
  새모델출력tag/EVI/CPT는 `p106b_relation_interleaved_v2_s1337`,자료는유효한v1불변순서manifest를그대로참조한다.
- 기존native_reader/공용검사기/tinylm/환경은수정하지않는다. 원형dict/데이터파일을수정하거나캐시를복사하지않는다.
- cb0Wb CPU8은누락표지의실패를주입/재현하고실제read-only캐시의첫8/마지막8윈도우를원래reader와대조한다.
  동일code/원형SHA의실제reader증거없이는새trainer가실행을거부한다. 모델/optimizer0이다.
- 새trainer도모든함수AST를기존과대조한다. native의동일한값전달외수학/자료량/부모/순서/손실은그대로다.
- cb2Wb 새cost8→ccWb 688→cdWb 신규TEST→ceWb원답검산을준비한다. 비용/예산선결과16:15/17시경계도동일하다.
- v1 미실행ccW/cdW/ceW는hold로보존하고완료시도로끝난cb2W는실패9로done처리한다.

## Stage4cf~4ci — 원문 첫 QA와 원래 3턴 QA의 후속 교육(원형 보존·V2 복구 실행)

착수 당시 설계와 실행 전 계약은 아래에 보존한다. 10/16 07:59 현재 자료 동결/CPU 소비/두 비용8은 완료됐고
V2 첫QA200회가 진행 중이다. 최신 실제 상태와 오류/재현 명령은 결과101§179~180을 따른다.

### 다음 선택과 범위

현재가상관계학습의자연128문자일치는모두0이었다. 교사추가호출전보유한원문역할대화가실제문장전이에도움되는지분리한다.

| 안 | 시나리오 | 장점 | 비용/한계 |
|---|---|---|---|
| A·선택 | 이미재고한2004원문을첫QA만/원래3QA의두팔로교육한다. 같은부모·배치·4epoch에code/작은가상재생도같게둔다. | 추가교사비0·실제원문/대화교수량의효과확인 | 3QA는새정답정보/지도량도많아형식만의인과비교가아님. CPU/비용후각학습약10~20분·평가약10분추정 |
| B | 교사가이원문을새자연질문/교정대화로다시작성한뒤교육한다. | 불명질문·부자연표현을보완할수있음 | 교사호출/뜻변질/재시도비용,원형질문효과와혼합됨 |
| C | 코드가아는가상사실의문장구성을먼저다양화한다. | 정답/숫자조건을보장하기쉬움 | 실제세계원문으로전이하는지는다시남음 |

A를후속으로준비하되현재순서대조의원답회수/검산을먼저끝낸다. 새교사생성/다운로드/보호데이터접근은없다.

#### 구현 착수 영향도·권한(2026-10-16 07:30)

| 파일·경로 | 예정 동작 | 현재 권한 | 제외 |
|---|---|---|---|
| scripts/diag_p106b_original_qa3_*.py 및 독립test·SH | 새코드/회귀/런처 | 사용자17시까지주도실험·선결구현위임 | 기존동결CODE/공용검사기/제품코드수정0 |
| HF/sft_ready/p106b_original_qa3_v1_s1337·새CPT | 독립동결·교육출력 | 같은새namespace 실험권한 | 원본/HF기존데이터/CPT덮어쓰기0 |
| 작은EVI/계획/결과/COMPASS/현재WIP/인계/Git | 검산·동기화·명시stage/한국어commit | 사용자주기기록지시 | private원답/가중치/보호데이터Git제외 |

코드는기존original-QA parser·masked encoder·binary 보조·Mu RMS4·indexed reader를재사용하고새course/trainer/evaluator만추가한다.
기존함수시그니처/저장데이터마이그레이션은없다. 새서명/자료량/언어분포/부모/eval기준을명시한다.
CPU회귀는첫쌍동일/3turn지도·부분마지막batch·실제native reader·누락marker오류주입을포함한다.
문서영향은기준표·방법론·실험/계획목록·COMPASS·배치표다. 다른아키텍처연구는현재대조에섞지않는다.
GPU권한·소유권·비교유효성·증거수준·정본연쇄5도메인축을따로확인한다. 일반언어/가상보존과새자연문항을혼동하지않는다.
현재혼합최종4epoch의SHA687EBCC5E30EA674EF4742BFC2BA6B98BCAB937541BD5498F567A9084387E831을두팔공통부모로고정한다.
신규TEST성적의최대모델을고른것이아니라계획한교육순서의다음부모이며프로젝트기본승자채택도아니다.

### 자료·학습 계약

- 이미사용한source TRAIN2048중엄격한1~4번호/원문첫3QA/1024직렬화가가능한2004개(ko995/en1009)를고정한다.
  첫QA팔은동일첫user/assistant만,3QA팔은원문의세질문과답을원래순서대로쓴다. 이후대화는교사가새로생성하지않는다.
- 원문repo/revision/SHA·parent ID·문항char범위를보존하고옛JSON고정값메타데이터는상속하지않는다.
  세계정답/번역은NOT_REVIEWED이며새지식량을과장하지않는다. 잘못된모든문구목록/온라인의미판정/자동재생성은없다.
- 기존code4096과가상TRAIN index0~127의한영256행을각epoch재생한다. 가상view는root/epoch회전으로섞고원문QA팔사이에같다.
  재생은기존능력보존용이며고유신규자료로세지않는다. 어떤VAL/TEST답도TRAIN으로옮기지않는다.
- 총6356행/epoch·micro8×accum16·4epoch=각200optimizer update다. source본학습75M×4/300M의축소대체가아니다.
- LR Adam5e-5/Muon2e-4·clip1·ckptON·compile default·word1/native1/binary1을양팔동일하게쓴다.
  이번자연교육은새fact분류보조를추가하지않으며fact보조손실0이다. 이공통전환과원문첫QA/3QA의지도량차이를명시한다.
- 일반텍스트는새read-only indexed1600창/1638400x다. 부모/이전실험창과겹치지않게고르고native_access/file/offset/hash의실제reader소비를CPU선결로검사한다.
  캐시복제/원본수정은없고optimizer는양팔새로시작한다. MTP/재귀/폭/압축은이번변경축에섞지않는다.
- source x/지도/순서·retention x·native/패딩/언어분포를각팔에서정확계수한다. 목표는‘전체교육안의전후효과’이며순수역할형식효과라고주장하지않는다.

### 독립 평가·단계

- 별도예약한한영32씩64원문3QA는학습/DEV에넣지않고끝까지모델평가/사람판독을유보한다.
  부모/두학생의실제첫답을다음턴에넣어각192답을남기고gold이력둘째/셋째128답은분리한다. 골드는정확도상한이아니다.
- 기존code/개발8/동일native32crop와고정가상root8192~8255의보존을함께보고한다. 가상보존은이미본평가의개발대조이지새지능TEST가아니다.
- 새CODE/namespace/CPT·동결/SHA·CPU누적/3turn마스크/원형불변·cost8두팔/남은예산뒤만full200두팔을연다.
- Stage4cf0W CPU계약,Stage4cf1W 자료동결,Stage4cf2Wa/Stage4cf2Wb 두cost8,Stage4cgWa/Stage4cgWb 두full200,
  Stage4chW 실제3턴/보존평가,Stage4ciW root/이력별검산순이다. SH는구현/회귀후작성하며현단계는DESIGNED다.
- 16:15새GPU중단/17시종료·보호원천/타원장/원본/외부게시/전체smoke경계와정식TRAIN_READY 미판정은동일하다.

### Stage4cf0Wb / cf2Wc·Wd / cgWc·Wd / chWb / ciWb — 원래 코드 생산자 계약 복구

07:38:33 첫cost8은DEV640의보조정답목록구성에서종료9, update0/CPT0이었다. OOM/학습실패가아니다.
DEV640은이전binding_aux_test 생산물을개발평가로재사용한것인데,trainer가다른binding_rows(dev)목록으로검증했다.
기존CPU10은loss/마스크/native만검사해이실제DEV소비경로를놓쳤다. 동적실물fixture누락이며정적AST만으로는발견하지못했다.

- 동결V1 course/원형데이터/CODE/실패raw/빈cost폴더는불변보존한다. 실행안한V1후속은hold이력으로남긴다.
- 새runtime `p106b_original_qa3_v2_s1337`은V1자료를읽되,원래 `binding.fresh_test(retention_course.code_rows())`를재생성한다.
  640문항의순서/대화바이트서명과512binding의mapping/order/대상/root/정답/causal position을정확대조한다.
  모든분할허용목록을합치거나기존검증을제거하지않는다. 이640은새독립TEST가아니라개발용보존평가다.
- 실제TRAIN3072보조라벨·DEV246/640/1024의전체인코딩·native1600창/앞뒤16조각을CUDA이전에검사한다.
  실제소비검사중공백없는JSON서명과원래공백있는생산자서명을혼용한두번째결함도발견했다. V1은update0이라보조누락학습은없었다.
  V2는학습/DEV모두원래생산자서명함수를쓰고,양팔각epoch3072개가실제lookup되는지CPU에서확인한다.
  틀린DEV목록/질문변조/메타데이터변조/학습라벨변조가실패하는CPU회귀와동일CODE/자료SHA의CPU증거를선결로둔다.
- 학습수학/부모/자료순서/200update/손실/배치는V1설계그대로다. 모델/CPT/EVI만새V2이며기존파일덮어쓰기0이다.
- cf0Wb 실제CPU소비계약→cf2Wc first cost8→cf2Wd three cost8→cgWc/cgWd full200→chWb 예약64실제3턴→ciWb 원답검산순이다.
  비용둘을재고남은예산판정후교육을열며16:15/17시경계는같다. 새CPU/GPU실행은현재주도실험권한안이다.

### Stage4ciWc — 원문 정답 증가의 후행 단순 기준선 점검(CPU 분석)

두200회와 예약 평가가 완료됐다. 부모/첫QA/3QA의 원문 문자일치1/9/17of192는 기준선 없이 지능 향상으로 읽지 않는다.
이 단계는 이 결과를 본 뒤 추가하는 후행 분석이며 기존 판정 기준·자료·실제 원답은 바꾸지 않는다.

| 안 | 구체 시나리오 | 장점 | 한계·비용 |
|---|---|---|---|
| A | 문자일치와 F1 변화만 기록한다. | 추가 계산0 | 항상 흔한 답을 내는 지름길과 구분하지 못함 |
| B·선택 | TRAIN에서 언어별 최빈 첫답과 언어/턴별 최빈 답을 고정하고 같은64문항에서 계산한다. 각 모델의 첫답을 후속에도 복사하는 단순 정책도 비교한다. | 모델 호출0·CPU 수초~수십초·일부 답변 편향 식별 | 세계정답/의미 이해 검증은 아니며 후행 분석임 |
| C | 독립 교사/사람이 모든 실제 답을 의미 판독한다. | 원문 정답 오류·정상 재표현을 직접 검토 | 검토 비용과 판독 오류가 커 별도 동결 표본부터 필요 |

B를 먼저 계산하고 이미 해시순으로 정한 한영4root씩8개 실제 답을 읽는다. TEST의 최빈 답을 골라 새 기준선으로 쓰지 않는다.
기존 source metric을 재채점하거나 학습 제외/재생성/정답성 PASS를 만들지 않는다.
영향은 새 소형 후행 근거·결과/계획/현재원장/인계뿐이다. 부모/학생/CODE/원형/환경/공용검사기/보호원천은 수정0이다.
새 구현 API나 모델 스키마 변경 없이 고정 원답의 CPU 집계로 수행한다. 계산 명령/원형SHA/정확 입력은 독립runlog와 근거JSON에 보존한다.
도메인5축에서 GPU학습0·원형보존·동일문항/동일source score·후행증거표시·정본문서연쇄를 확인한다.
이번 계산에 전수 사람 승인이나 온라인 오조어 목록·의미 필터를 추가하지 않는다.

### Stage4cf~4ci 실제 회수와 예측 대조(10/16 08:40)

결과101§179~184에서 V1 동결/비용 오류9·업데이트0, V2 소비 계약 복구와 두 비용8/두200회/전체 평가/원답 검산을 구분했다.
예상한 추가 QA의 원문 재현 이득은 고정64지문에서 관측됐다. 실제192답의 문자일치는 부모1/첫QA9/3QA17이다.
첫QA→3QA 차이는+4.17%p의 root 대응 구간[0.52,7.81], 평균 어휘F1 차이는+0.0541[0.0124,0.0999]다.
하지만 지도량도81,200토큰 더 많고, 가상관계 보존499→454/471 및 native crop 손실 증가가 있었다.
단순 TRAIN 턴별 최빈 답도11/192를 맞혔고 실제8지문 판독에서 잘못된 원문 단위와 정상 구두점 차이를 확인했다.
따라서 학습 가능성의 좁은 긍정이지 범용 지능·정식 적격·프로젝트 기본 승자 채택이 아니다. 본75M/300M 목표는 유지한다.
원문/실패/두 학생/CODE를 보존하며 새 가중치8개는 최종2keep/중간6hold로 목록에 기록했다.

## Stage4cj~4cl — 고정 실제 이력에서 문맥 창만 바꾸는 후행 원인진단(설계)

### 목적·대안·선택

모델이 필요한 인물·속성·숫자를 못 고르는 현상이 보인다. 원문을 짧게 바꿨을 때의 변화를 먼저 본다.

| 안 | 예시와 방법 | 장점 | 비용·한계 |
|---|---|---|---|
| A·선택 | 같은 질문에서 전체 기사와128토큰 원문 창을 비교한다. 소년11/소녀12가 섞인 사례도 같은 앞선 실제 답을 유지한다. | 가중치 변경0·현재 실패를 직접 좁힘 | 구현/CPU 약35~60분·GPU 약10~20분 추정. 창 선택은 정보를 바꾸므로 한 가지 내부 원인으로 단정하지 못함 |
| B | 인물 역할·단위·조건을 코드가 아는 새 자연형 QA로 추가 교육한다. | 잘못된 수량/인물 연결을 직접 가르칠 수 있음 | 자료/가중치가 바뀌고 템플릿 전이 검증이 추가로 필요 |
| C | Gemma가 원문 질문/답을 다시 작성하고 원형과 교정본을 보존한다. | 관찰한 원문 오류를 다룰 수 있음 | 추가 교사 생성·검토에 수시간, 교사도 틀릴 수 있음 |

현재 주도 실행 권한 안에서 A를 먼저 선택한다. B/C는 진단 결과와 남은 시간을 보고 별도 새 단계로 정한다.
MTP·재귀 방문·폭·copy head를 이 진단에 섞지 않는다. 기존 제품과 동결 학습 코드는 수정하지 않는다.

### 정확한 입력 대조

- 새 태그는 `p106b_source_window_diagnosis_v1_s1337`이다. 원형·새 작은 입력 manifest/원답만 별도 경로에 저장한다.
- 부모687EBC와3QA 학생567D37 두 endpoint를 고정한다. 원래64지문은 이제 후행 개발진단 표본이며 새 독립 TEST라고 부르지 않는다.
- 각 endpoint의 일차 평가에서 나온 실제 과거 답을 고정한다. 현재 질문의 원문 부분만 바꾸고 앞선 질문/답·현재 질문은 그대로 둔다.
  새 답을 다음 턴에 전파하는 새 대화 시험이 아니다. 모델 사이의 과거 답이 다르므로 조건 효과는 우선 각 모델 안에서 비교한다.
- 원문 토큰 기준128창/stride64를 만든다. UTF-8 원문 문자 범위와 실제 직렬화 토큰 수를 보존하고1024 한도를 검사한다.
- FULL은 원형 전체, QUERY는 현재/이전 사용자 질문의 문자3-gram TF-IDF cosine 순위1위 창, RANDOM은 root seed로 고정한 창이다.
  QUERY에는 현재 정답이나 이전 골드 답을 사용하지 않으며 단순 문자 순위는 정답·의미 검사기가 아니다. 점수 문턱이나 학습 제외도 없다.
- GOLD_LITERAL은 원문 정답 문자열을 포함한 창이다. 가능한 창이 없으면 NOT_ELIGIBLE로 기록하고 실제 호출을 생략한다.
  이는 정답을 이용한 입력 개입이지 배포법·정답성 보장·수학적 정확도 상한이 아니다. 문자열이 있다는 것과 근거가 맞다는 것도 구분한다.
- REMOVE_REFERENCE는 원문만 비우고 동일한 실제 과거 대화는 남긴다. 후속 턴에서 순수 무정보 기준선이라고 부르지 않는다.
- FULL 재생성이 원래 저장 답과 byte 일치하는지 먼저 검사한다. 불일치면 나머지 조건의 해석을 중단하고 정합 문제로 기록한다.

### 단계·영향도·판정

Stage4cj0W CPU 회귀/실제 소비 점검→Stage4cj1W 독립 입력 동결→Stage4ckW 같은 모델의 고정 이력 대조→Stage4clW 원형/조건별 대응 검산이다.
생성은 기존 FP32_MATH·greedy64·동일 종료 규약이며 학습/optimizer/새 CPT0이다. 표본/단계/CODE/출력 경로를 고정한 뒤 실행한다.
CPU는 원형 재구성/범위·Unicode·token budget·정답 비사용 QUERY·seed·GOLD 부적격·실제 과거 답 불변을 검사한다.
오류가 있으면 source metric이나 문턱을 완화하지 않고 새 버전으로 복구한다. 모델·입력 원형은 보존한다.
비교는 같은 적격 문항 집합·언어/턴별로 하며 문자/F1/빈 답/절단·정답 문자열 포함률·처리시간을 분리한다.
큰 문맥/정보 선택의 영향과 내부 표현·구현 결함은 다르다. 단일 모델/고정 개발표본 결과를 범용 지능으로 승격하지 않는다.

| 파일·경로 | 예정 동작 | 권한 근거 | 제외 |
|---|---|---|---|
| 새 scripts/source_window helper·test·diag·SH | 독립 구현/CPU/진단 | 사용자10/16 17시까지 주도 실험 위임 | 제품/공용검사기/기존 CODE 변경0 |
| 새 HF/sft_ready 태그·private 원답 | 독립 입력/진단 출력 | 같은 범위의 새 실험 | 원본 덮어쓰기·보호원천·학습 데이터 편입0 |
| 작은 근거/계획/결과/COMPASS/현재원장/인계 | 검산·동기화·선별 커밋 | 사용자 주기 기록 지시 | 가중치/원문 전문 Git 제외 |

기존 serializer/emit/score/ShardWriter는 재사용한다. 새 API는 실험 helper만 소유하고 마이그레이션은 없다.
도메인5축에서 실행권한·데이터 소유·동일 모델/동일 이력·진단과 품질 분리·정본문서 연쇄를 따로 확인한다.
16:15 새 GPU 중단/17시 종료와45분 마감 여유를 유지한다. 전체 smoke/설치/다운로드/외부 게시 권한은 확장하지 않는다.

### Stage4cj~4cl 구현 전 고정한 세부와 preflight(10/16 09:09)

- 기존 연구 [Lost in the Middle](https://arxiv.org/abs/2307.03172)는 문맥 내 관련 정보의 위치에 따른 영향을 보였다.
  이번에는 그 결과를 우리1024 문맥 모델의 원인으로 가정하지 않고 입력 개입의 동기로만 참고한다.
- QUERY는 [벡터 질의의 cosine 원리](https://nlp.stanford.edu/IR-book/html/htmledition/queries-as-vectors-1.html)를 차용한 문자3-gram 변형이다.
  각 사용자 질문에서 따로 gram을 세어 질문 경계를 가로지르는 인공 조각을 만들지 않는다. 현재 질문2회·이전 질문 각1회이며 답은 제외한다.
  tf=1+ln(count), idf=1+ln((1+창수)/(1+해당gram창수)), 두 벡터의 L2 정규화 내적이다. 이 smoothing/문자단위는 프로젝트 선택이며 문헌의 정확한 재현은 아니다.
- 동점은 앞 문자 위치, RANDOM은 VERSION/seed1337/root/turn 해시, GOLD_LITERAL은 문자열을 포함한 후보 중 같은 QUERY 순위로 고정한다.
- 입력 CPU는14개 순수 회귀와5개 실제 소비 회귀로 검증한다. 최초 구현의 경계 gram 혼입을 자체 동일 문장 cosine 시험이 발견했고 질문별 Counter 합산으로 수리했다.
  이 개발 단계에는 새 모델/자료 동결/학습/GPU 실행이 없었다. 정식 CPU proof는 아래 새 SH에서 따로 생성한다.

| preflight 항목 | 판정 | 근거 |
|---|---|---|
| 학습 토큰·pool 비율 | 해당 없음 | optimizer0·CPT0·동일 모델의 입력 진단, 본300M 대체 아님 |
| 새 태그/덮어쓰기 | 통과 | registry에 새 태그 로그 없음, 새 HF/private/EVI만 생성 |
| 중복 조건 | 통과 | 과거 원문3QA 평가와 달리 실제 이력 고정·원문 창만 개입 |
| 모델/토크나이저 | 고정 | 부모687EBC/3QA567D37·같은 chat32 SHA·그대로인 코드 |
| 같은 평가 단위 | 조건부 | 이전64문항의 후행 개발용·각 endpoint 안의 같은 적격 사건 대응 |
| 자원 | 조건부 | 교사 없이 한 모델씩·기존 FP32 경로, 현재 진단 예상10~20분·상한30분과 마감45분 여유 |
| 정합 선결 | 필수 | FULL384 출력이 기존 원답과 byte 일치해야 다른 조건을 해석함 |
| 품질 문턱 | 새 승격 없음 | 이 가족의 σ를 빌리지 않고 root 대응 기술구간·내용 한계·NOT_ELIGIBLE 분모를 보고 |

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

### Stage4cj~4cl 회수(10/16 09:35)

결과101§185~186. FULL384 byte 재현 뒤1828회 생성/1920행을09:16:00 종료0, 원형 검산은09:16:40 종료0으로 회수했다.
3QA FULL17/192 대 QUERY12/RANDOM6/원문제거5다. 정답문자열 창은 같은 적격146에서14→18이나 문자 차이 구간에0이 들었다.
짧은 창만으로 문제가 해결될 것이라는 기대는 지지되지 않았다. 원문 사용의 영향은 있지만 역할/값 선택 약점은 남는다.
QUERY를 생산 기본값으로 채택하지 않고 모든 원형·모델·코드를 보존한다. 창/정보/위치 효과를 단일 내부 원인으로 분해하지 않는다.

## Stage4cm~4cr — 교사 교정과 코드 역할교량의 두 축 교육(설계)

### 왜·대안·선택

원문64에서 자료 단위 오류와 학생의 인물/속성/숫자 혼동이 함께 보였다. 교정 자료와 의미역할 교육의 효과를 분리한다.

| 안 | 구체 방법 | 장점 | 비용·한계 |
|---|---|---|---|
| A | 원형/교사교정 두 팔만 학습한다. | 원문 오류를 직접 다룸 | 역할·단위 교육의 별도 효과는 남고 교사 비용 필요 |
| B | 교사 없이 역할교량/반복 대조만 학습한다. | 코드 정답·생성 비용 작음 | 원문의 오류가 남아 자연 QA 실패 원인 해석이 제한됨 |
| C·선택 | 원형/교정 × 정상반복/역할교량 네 팔을 같은 부모·업데이트 수로 비교한다. | 두 개입의 방향과 상호작용을 관찰 | 구현·교사·4팔 비용, 문장/지도량 차이는 여전히 함께 바뀜 |

현재 주도 실행 권한과 남은 시간 안에서 C를 준비한다. 효과는 보장하지 않으며 비용8 실측 후 네 팔과 평가/마감이 모두 맞을 때만 본 probe를 연다.
이는 본75M/300M의 대체가 아닌 오류 교정/교육 방법의 별도 probe다. 제품 구조·MTP·재귀·폭·copy head는 바꾸지 않는다.

### 자료와 교사 계약

- 새 교사 태그 `p106b_source_repair3_v1_s1337`, 새 학습 태그 `p106b_repair_role_v1_s1337`을 사용한다.
- 기존 원문 TRAIN2004 안에서 실제 참조640 learner token 이하의 후보는 ko992/en1006이다. 한영320씩640개를 hash 순으로 봉인하고, 구조 수락256씩512개를 공통 원천으로 삼는다.
  처음16개(한영8씩)는 pilot이며 수락 원형을 다음 생산에 재사용하고 동일 root를 다시 생성하지 않는다. 구조 실패/거절 root도 총3시도 뒤 자동 반복하지 않는다.
- Gemma4-12B Q4_0 + Q8_0 MTP assistant/draft2, llama-b11396·기존 sampler·thinking256/context8192/output3072를 명시한다.
  교사/학생은 이 대조의 자료 동결 전후로 별도 실행한다. 전역 교사 기본값·기존 모델/설정 파일은 수정하지 않는다.
- 교사는 Q1/A1/Q2/A2/Q3/A3와 선택 NOTE만 쓴다. 코드가 canonical JSON/ChatML·역할·출처를 담당한다.
  원형 질문/답은 미검증 참고물로 주고 참조에 맞춰 오역·단위·인물/조건을 고치게 한다. 근거/의도가 부족하면 지어내지 말고 필요한 정보를 묻는 답을 쓸 수 있다.
- 사고 채널·최종 원답·원형 QA·교정본·변경 여부/NOTE·시드/시도·출처/참조 SHA를 별도 보존한다. 학생에는 사고/NOTE가 아닌 최종 세 QA와 같은 참조만 준다.
- 구조/길이/종료만 총3시도 안에서 회복한다. 임의 원천은 중복 유형 UNKNOWN이므로 같은 정답을 자동 불량으로 삼거나 의미 문자열 목록/전수 검증으로 재생성하지 않는다.
- 모든 raw/canonical은20MB 이하 write-once 조각·Git 제외다. 공개 원문 권리/PII·세계정답/정식 TRAIN_READY는 자동 승격하지 않는다.

### 네 교육 팔과 코드 교량

1. raw_repeat: 공통512 원형3QA + 기존code4096 + 가상재생256 + 정상 반복 대조2048.
2. repair_repeat: 같은512 참조의 교사교정3QA + 같은 재생/반복 대조.
3. raw_role: 원형3QA + 같은 재생 + 역할교량2048.
4. repair_role: 교사교정3QA + 같은 재생 + 역할교량2048.

역할교량은 코드가 선언한 두 인물/역할·행위자/수신자·나이/연도/단위·간단 기간 계산을 원문과 세 질문으로 만든다.
예: 소년11/소녀12를 제시하고 누구/나이/학년이나 다른 속성을 구분한다. 반복/동의표현/질문대상 변경/명시 조건 갱신을 root·epoch로 회전한다.
주어진 사실·숫자의 정답만 프로그램으로 계산하며 임의 공개 질문의 의미 유형을 추정하지 않는다. 정상 반복은 양성 지도이고 중복 재생성 대상이 아니다.
반복 대조는 기존 code의 검증된 질문/답을 명시적으로 되묻는3턴이다. 새 독립 지식으로 세지 않는다. 기존 binary 보조라벨은 원래 code4096에만 동일하게 적용한다.

각6912행/epoch, micro8×accum16·checkpoint-on·4epoch=216업데이트, 기존 Adam5e-5/Muon2e-4·clip1·word/native/binary1·fact0다.
새 native1728 read-only 창/1,769,472x를 네 팔에 동일하게 쓴다. 실제 SFT/지도/패딩/언어비·고유 직렬화·재노출을 별도 계수한다.
원형/교정 및 반복/교량은 내용과 지도량도 달라 순수 한 요소 효과로 단정하지 않는다. 같은216회/같은 부모의 전체 교육안 비교다.
공통 부모는 지금3QA 최종567D379E...로 고정하고 optimizer는 새로 시작한다. 새 CPT는 우선 최종본만 저장해 불필요한 중간 가중치를 늘리지 않는다.

이는 부모 이후의 추가4pass다. 원형512는 이미 이전 학습에 쓰인 참조의 일부이므로 누적 전체 노출을4회 또는 새 독립 지식512개로 부풀리지 않는다.
교정 후 재교육을 시험하는 목적이며 원형 반복 대조의 추가 노출/과적합 위험도 결과에 포함한다. 새 역할 graph와 기존 code 재생의 고유량은 따로 보고한다.
역할교량 질문은 TRAIN에서 기본0/동의표현1을 사용하고 TEST의 별도 체계2/3은 이 생산자의 TRAIN에서 제외한다.
같은 neutral graph의 한영·질문체계 자식은 bootstrap에서 함께 묶는다. 단어/사실의 사전학습 미노출을 보장한다는 뜻은 아니다.

### 새 평가·선결·비용

- 과거 추출형 first-pair 유일 문자열 조건 때문에 기존 fresh KO48개는 이미 모두 사용됐다. 이를 새 TEST로 재사용하지 않는다.
  새3QA는 위치감독이 없으므로 별도 parser에서 번호1~4/원형 범위·역할·토큰 예산은 유지하되 불필요한 span-unique 조건은 요구하지 않는다.
  Yes/No·재표현·계산 답도 새 후보가 될 수 있다. 이것은 새 목적/새 버전이며 옛 결과·gate·parser를 약화하거나 덮어쓰지 않는다.
- 새 공개64(한영32씩)는 기존 source IDs와 정확24word passage 및 동일 참조를 제외한 뒤 봉인하고 끝까지 비열람한다. 사전학습/의미 중복은 NOT_AUDITED다.
- 별도 코드 교량 TRAIN/DEV/TEST는 neutral graph/이름/사실을 분리한다. 실제3턴과 골드 이력을 분리하고 같은질문/다른질문/조건변경별 점수를 보고한다.
- 이전 자연64·code640·가상관계 보존·개발8/native32crop도 개발 대조로 유지한다. 새 평가와 섞어 새 표본이라고 부르지 않는다.
- CPU에서 세 QA 파서/동일답 허용·공통 참조·canonical source_transform·마스크·원천 분리·실제 TRAIN/DEV/native 소비를 확인한다.
  pilot은 형식·비용 경로만 확인하며 내용 PASS가 아니다. 데이터512 실제 quota와 동일CODE·네 비용8·전체 시간 예산을 선결로 둔다.
- 구현/검증 약1~2시간·교사512개 약40~80분·네 비용8 약12분·네216회 약40~80분·평가 약20~30분 추정이다.
  실제 teacher pilot/비용8과 잔여시간을 재어16:15 새 GPU 중단/17시 종료·최소45분 마감을 보장할 수 없으면 해당 본 실행은 열지 않는다.
- Stage4cm0W CPU/원천봉인→cm1W 교사16 pilot→cm2W 나머지 생산→cn0W/1W 교량CPU/공통course→coWa~d 비용→cpWa~d 교육→cqW 새평가→crW 대응검산 순이다.

### 영향도·권한

새 source_repair helper/producer/test와 별도 role_bridge/course/trainer/evaluator·SH만 추가한다.
교사 생산의 CODE는 이후 역할교량 구현과 분리해 생성 중 원형 해시가 바뀌지 않게 한다. 기존 frozen 코드·제품·공용검사기·환경은 변경0이다.
새 HF/private/EVI·계획/결과/기준표/방법론/COMPASS/현재원장/인계·명시 선별 한국어 커밋은 사용자 주도 실험/주기 기록 권한 안이다.
보호 TinyDataset/사전·기존 원형/CPT/캐시 수정·다운로드/설치·외부 게시·타 WIP는 제외한다.
GPU 권한·소유권·비교 조건·증거수준·정본 연쇄5축을 각각 확인하며 teacher pseudo-label과 코드의 제한된 생산자 정답을 혼합 승격하지 않는다.

### Stage4cm0W / Stage4cm1W / Stage4cm2W — 교사 전용 동결 경로

cm0W는 CPU12개 content 회귀/3개 실제640+새64 소비 회귀 뒤 원천을 봉인한다.
cm1W는 Gemma4 MTP16개 파일럿이며 원형/교정 질문·답을 화면과 raw에 함께 남긴다.
cm2W는 이미 처리한 pilot root를 건너뛰고 실제한영256씩512 source quota까지 봉인 batch16개 단위로 진행한다.
pilot의 wire 통과는 양 언어에서 실제3QA/동일 참조/canonical 경로가 열린다는 의미이지 내용 승인이나 quota 완료가 아니다.
source_transform은 이미 등록된 teacher_answer를 쓰고, 사고/NOTE는 학생 메시지에 넣지 않는다. UNKNOWN 같은 답은 내용 재생성 사유가 아니다.
stdout 행은8KiB로 상한을 두고 완전 원답은20MB 이하 raw/canonical에 남긴다. 최대640root×3시도에서도 콘솔 raw가20MB를 넘지 않도록 설계했다.
유효 원문을 줄여 강제로 맞추지 않고 새 질문/답 길이만 구조 피드백으로 회복한다. root별3시도 예산은 batch/재개 사이에도 초기화하지 않는다.

### Stage4cn~4cr 실제 입력·preflight(10/16 10:58, GPU 전)

cm0/1/2는 종료0·교정512 quota 완료다. cn0 CPU26·cn1 동결·cn2 실제 CPU부모/전체 소비도 각각10:52:29/10:54:46/10:57:15 종료0이다.
frozen course/trainer CODE와 새64 비열람을 유지한다.

| 순 | 정확 launcher | 범위 |
|---|---|---|
| 1 | `run_P106B_Stage4cn0W_repair_role_cpu.sh` | CPU26 role views, mask, native consumer, accumulation and paired neutral-root regression. No model/CUDA forward. |
| 2 | `run_P106B_Stage4cn1W_repair_role_common_course.sh` | Actual accepted512 quota and operational teacher seal required. Freeze four6912-row recipes and fresh64; no CUDA. |
| 3 | `run_P106B_Stage4cn2W_repair_role_actual_cpu_wire.sh` | Read-only fixed parent and actual four-arm encoded consumers. CPU model load only, no forward/optimizer/CUDA/CPT. |
| 4 | `run_P106B_Stage4coWa_raw_repeat_cost8.sh` | Same parent and batch, cost8 only. No checkpoint. Four same-code costs required before full216/evaluation/closure budget. |
| 5 | `run_P106B_Stage4coWb_repair_repeat_cost8.sh` | Same parent and batch, cost8 only. No checkpoint. Four same-code costs required before full216/evaluation/closure budget. |
| 6 | `run_P106B_Stage4coWc_raw_role_cost8.sh` | Same parent and batch, cost8 only. No checkpoint. Four same-code costs required before full216/evaluation/closure budget. |
| 7 | `run_P106B_Stage4coWd_repair_role_cost8.sh` | Same parent and batch, cost8 only. No checkpoint. Four same-code costs required before full216/evaluation/closure budget. |
| 8 | `run_P106B_Stage4cpWa_raw_repeat_full216.sh` | Same parent, micro8 accum16 cp-on, additional4passes,216 updates; final-only checkpoint. No MTP, fact head or teacher concurrency. Not main300M. |
| 9 | `run_P106B_Stage4cpWb_repair_repeat_full216.sh` | Same parent, micro8 accum16 cp-on, additional4passes,216 updates; final-only checkpoint. No MTP, fact head or teacher concurrency. Not main300M. |
| 10 | `run_P106B_Stage4cpWc_raw_role_full216.sh` | Same parent, micro8 accum16 cp-on, additional4passes,216 updates; final-only checkpoint. No MTP, fact head or teacher concurrency. Not main300M. |
| 11 | `run_P106B_Stage4cpWd_repair_role_full216.sh` | Same parent, micro8 accum16 cp-on, additional4passes,216 updates; final-only checkpoint. No MTP, fact head or teacher concurrency. Not main300M. |
| 12 | `run_P106B_Stage4cqW_repair_role_actual_evaluation.sh` | Fixed parent plus fourfinals. Fresh64 actual/gold separate; neutral-role styles and retention. FP32 greedy64; no teacher or optimization. |
| 13 | `run_P106B_Stage4crW_repair_role_paired_readback.sh` | Recount all sealed raw events, pair fresh sources and neutral graphs. No model/CUDA. Not world truth or automatic default adoption. |

| preflight | 판정과 근거 |
|---|---|
| 계산 | 216×8×16×1024=28.31M은 패딩 상한. 실제 SFT x3.102/3.145/3.540/3.583M, 별도native1.769M/각4pass |
| 풀/반복 | 고정 SFT 추가4pass의 의도된 진단. 원형512는 이미 본 원천이며 새 독립지식/누적4epoch 아님. 일반 비반복2배풀과 분리 |
| 충돌/중복 | check_run_registry 새태그 충돌0/유사런0. 새namespace, 원본/제품 불변 |
| 실제소비 | cn2 CPU본문SHA불변/4×4epoch 인코딩·모든3072 binary/epoch·DEV512/640·read-only native1728/16슬라이스 확인 |
| 비교 | 같은부모567D/m8a16/cp-on/216회/손실. 내용/입력·지도량 차이 있어 PARTIAL_CONFOUNDED 전체 교육안 대조 |
| 평가/선택 | 새64와128neutral graph·질문체계2/3은 TRAIN제외. 고정최종4epoch·TEST 선택0·actual/gold/원문문자/코드주어진사실/내용판독 분리 |
| 시간/VRAM | 네cost8 실측3090~3110MiB·warm최대1.13/1.21/1.23/1.16초. 11:19:37 전체10923초 대잔여20423초를 확인 후 첫216회 개방; 매팔 재검증 |

실제 답을 보기 전 수동 판독 표본도 고정한다. 공개새64는 SHA(TAG,FIXED_MANUAL_SOURCE,root)의 언어별 첫4지문,
역할은 SHA(TAG,FIXED_MANUAL_ROLE,neutral_root)의 가족별 첫1 neutral graph에서 모든 한영/질문체계 자식을 읽는다.
표본은 현재동결course SHA8BD0F0D4...에 묶으며 결과가 좋거나 나쁜 문항으로 교체하지 않는다. 비맹검 설명용이고 전체의 의미정확도 통계/기본승자 판정으로 쓰지 않는다.
코드는 검산을 위해 sealed rows를 읽지만 GPT/교사·학습/선택에는 새 TEST 질문·답 내용을 노출하지 않는다.

> 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.
### Stage4cm~4cr 실제 회수(10/16 12:22)

네216회·5endpoint 실제평가·전수원답 검산은 모두 종료0이다. 결과101§187~196에 원형/교정/학습/실제답을 분리했다.
역할actual 부모157/1536·원형반복108·원형역할1060·교정역할1047이다. 새질문체계에서47→462/768로 개선됐으나
자연QA 향상은 미확립이다. 고정source8 판독/64계보 추적은 원천답 오류와 번호 분할의 과제방향 결함을 확인했다.
원래 전체지시/응답 SFT가 불량이라는 뜻은 아니며 source 문자일치를 의미정확도로 쓰지 않는다.
동결CODE/자료/모델/이전결과는 보존한다. 새 충분성 연구의 부모는 실용 raw_role7E584E9F로 고정하되 범용 승자로 채택하지 않는다.

## Stage4cs~4cw — 질문별 근거 충분성·재질문·보충정보 뒤 회복(설계)

### 1. 왜·기존 구현·비교안

Stage4cq/cr에서 역할교량은 실제157→1060/1536으로 개선됐으나 자연64의192답은14→13으로 개선되지 않았다.
이 수치는 현재 고정표본의 관측이며 단일seed/지문군의 세계지능 결론이 아니다. 현재 지문 교정과 역할교육 결과를 먼저 보존한다.

기존 `p106b_context_quality.py`는 건물식별/색상누락의 1~2턴 과제와 후행 clarification 판독을 이미 구현했다.
새 경로는 이 원칙을 계승하되 정보가 없다고 입력에 직접 말해 주지 않는다. 같은 참조에서 묻는 항목만 바꿔
어떤 질문에는 충분하고 다른 질문에는 부족하도록 하며, 같은사실/그뒤보충/조건갱신의 실제3턴을 검증하는 net-new 부분이다.
일반 OASST/공개QA의 의미 유형을 자동 판정하는 기능이 아니다.

| 안 | 실제 방법·예 | 장점 | 한계·영향 | 비용 추정 |
|---|---|---|---|---|
| A | 완전한 인물/단위 기록을 더 반복해 조회 연습 | 기존 기능 강화·새 구현 작음 | 정보 부족 때 추측하는 문제를 직접 가르치지 못함 | CPU낮음·학습/평가약30분 |
| B·선택 | 같은 기록에서 질문 대상 항목/무관 항목을 각각 빼고, 부족하면 구체적으로 묻기→사용자 보충→새값 답하기 | 원래 건물사례와 정보 부족 질문을 직접 겨냥하고, 길이/‘미제공’ 키워드 지름길을 통제 | 새 제한적 생산자/두팔/마스크·의존성 검증 필요·자유세계 질문으로는 미일반화 | 구현/CPU45~70분·두cost/학습약25분·평가약30~45분 |
| C | 가중치는 그대로 두고 ‘짧게 답’ 등 답변양식만 바꿔 재평가 | 현재 교정팔의 형식/내용 혼동을 분리 | 부족정보 처리 능력의 교육은 하지 않음 | CPU작음·GPU약10~20분 |

현재 주도적 실행 권한 안에서 B를 선택한다. 원래 네팔을 재학습하거나 옛 gate를 바꾸지 않고 새 태그를 사용한다.
A는 B의 완전자료 대조로 포함한다. C/자연답 후행판독은 내용/형식의 설명용이며 자동 품질판정·학습 제외 기준이 아니다.

### 2. 질문·예측

- Q1: 모델이 소년 나이가 빠졌어도 소녀 나이는 답하고, 소년 나이는 되물을 수 있는가?
- Q2: 나이를 보충해 준 다음 실제 자기 앞 답이 잘못돼도 올바른 값을 답하고 변경된 값을 계산하는가?
- Q3: 실제론 근거가 충분한 기간 계산에서 불필요하게 되묻는 현상이 늘지 않는가?
- 기대: 기존 조회69% 능력 위에 같은근거/다른질문의 대비를 가르치면 근거선택과 회복을 학습할 수 있다.
- 실패 가능성: 고정 재질문 문구만 외우거나 항상 되묻는 지름길, 계산/자기답 영향/새표현에서 실패할 수 있다.
  자연지문·세계지식은 이 작은 과제만으로 개선되지 않을 수 있다. 실패도 그대로 보존한다.

### 3. 코드가 아는 충분성 계약

4가족 people/units/transfer/years의 원래 선언된 가상 사실을 재사용한다.
첫3가족은 두 서로 다른 필드 a/b, years는 기간(시작/종료가 모두 필요)과 구역이름을 대상으로 한다.
각 graph는 아래 네조건을 모두 TRAIN epoch 순환/새 TEST에서 제공한다.

| 입력에서 뺀 정보 | 질문 | 생산자 근거 판정 |
|---|---|---|
| a에 필요한 필드 | a | 부족→그 필드를 구체적으로 되묻기 |
| b에 필요한 필드 | a | 충분→값 답하기 |
| a에 필요한 필드 | b | 충분→값 답하기 |
| b에 필요한 필드 | b | 부족→그 필드를 구체적으로 되묻기 |

같은 빠진 기록이 충분/부족 양쪽에 나타나므로 단순히 기록이 짧다는 이유나 어느 항목이 없다는 사실만으로는 정답을 고를 수 없다.
입력에 부족함/정답유형/숨은값을 써 주지 않는다. 필드의 문장을 빼며, 같은 숫자가 다른 필드에 남아도 지우지 않는다.
기간은 기간 문구가 없어도 두 연도가 있으면 계산 가능하므로 불필요한 재질문을 금지하는 양성 사례다.
이것은 자유 질문 의미 분류나 모든 문제문구 목록이 아니라, 코드가 자신이 만든 그래프의 의존성을 아는 제한된 계약이다.

2턴째는 양팔 모두 빠뜨리기로 정한 필드의 실제값을 사용자 문장으로 제공하고 같은 질문을 다시 묻는다.
3턴째는 소년나이/면적/수신자/사업종료연도를 명시 갱신하고 새값/기간을 계산한다.
모든 gold assistant는 올바른 양성 지도다. 옛 오답을 정답으로 학습하지 않으며 의미 재생성/문구 blacklist/자동 심사를 추가하지 않는다.

### 4. 두 교육안과 새 평가

- 새 태그 `p106b_evidence_recovery_v1_s1337`, 공통 부모는 raw_role 최종7E584E9F...다.
  이는 새 충분성 TEST를 만들거나 보기 전 고정한 실용 선택이며 기존 네팔의 순수 승자 주장과 구분한다.
- complete_replay: 같은6912행 구성을 쓰되 역할2048개는 모두 질문에 필요한 근거가 있는 같은 새표현/보충/갱신 3턴.
- evidence_recovery: 같은 원천/질문과 뺄 필드를 사용하되 필요한 정보까지 뺀 경우만 첫 답을 재질문으로 지도.
- public 원형512/code4096/기존가상256 재생은 동일하다. m8×accum16/ckpt-on/추가4pass216회, Adam5e-5/Muon2e-4,
  word/native/binary1·fact0·학생MTP0를 유지한다. 본체 구조/제품 기본값은 변경하지 않는다.
- 이미 본 가상 TRAIN1024/원문 일부의 추가노출이다. 누적 총4epoch나 새세계지식량으로 부풀리지 않는다.
- 새가상 TEST는 예전128neutral을 제외한 다른128초기fact 집합을 봉인한다. 초기 완전facts가 같은 변형도 하나의neutral로 묶고,
  네조건×한영=1024대화/모델, 실제3072답/골드이력2048답을 분리한다. 질문체계2는 이번 TRAIN에서 제외한다.
- 새TEST 전에 데이터/모델/torch RNG·마스크/실제소비를 CPU로 검증한다. 현재source64/role512는 보존·개발용으로만 재사용한다.
- 부모/두학생 고정final4를 비교하고 새TEST로 중간 epoch를 선택하지 않는다. 새가상/기존role/자연DEV/가상보존/code/legacy8/native를 분리한다.

### 5. 판정

실제3턴의 충분상태 scalar정답, 보충뒤 scalar정답, 갱신정답과 부족상태의 실제 첫답을 분리한다.
재질문의 정답 표현은 여럿이므로 exact target 일치를 전체 의미정답으로 쓰지 않고 고정 표본의 문맥/답을 후행 판독한다.
불필요한 재질문·값 추측·처음 오답 반복을 함께 보고한다. 문자열 목록을 온라인 판정/재생성에 쓰지 않는다.
paired bootstrap은 같은neutral의 한영·네조건을 함께 묶는다. 이 계열의 다중학습seed σ는 미측정이며
단일seed/가상schema의 조건부 효과·실용교육안 비교만 허용한다. 원문 정답성/범용지능/본75M·300M 완료는 주장하지 않는다.

### 6. 비용과 선결

CPU회귀→course 동결/실제부모 소비→두cost8→전체기한예산→두216회→고정3endpoint 실제평가→원답검산/표본판독 순이다.
현재17시기한에서16:15 새GPU중단/45분마감 여유가 안 나오면 비싼 단계는 열지 않는다. 실행시간은 cost8로 갱신한다.
teacher/다운로드/설치/새외부데이터는0이다. 현재 역할판독/실행회수와 충돌하면 먼저 회수한다.

### 7. 예정 launcher

Stage4cs0W CPU, cs1W course, cs2W 실제CPU부모/소비, ctWa/b cost8, cuWa/b full216, cvW actual, cwW readback을 준비한다.
정확 파일은 구현 뒤 이 절과 experiments.tsv에 등재하며 미작성 상태를 실행가능으로 표시하지 않는다. stdin/queue/cleanup 호출을 넣지 않는다.

### 8. 영향도·권한·한계

| 파일 범위 | 동작 | 현재 권한·제외 |
|---|---|---|
| 새 evidence_recovery helper/course/train/eval 및테스트/SH | 독립 신설 | 사용자17시까지주도실험·새namespace; 기존frozen CODE 수정0 |
| 새 HF/EVI/runs checkpoint | 원형/최종2만 생성 | 원본/기존CPT 수정삭제0·Git원답/생각/가중치제외·각파일20MB미만 |
| 현재계획/결과/기준표/방법론/COMPASS/양목록/현WIP·인계 | 연쇄갱신 | 사용자주기기록/명시선별한국어커밋·타WIP불변 |
| 공용검사기/환경/.agents/.codex/보호데이터/외부서비스 | 미수정·미실행 | 권한확대 없음 |

코드축은 기존 인코더/부모loader/known binary/state·native 소비를 재사용하고 새넷은 질의별 필드의존/생략/보충뿐이다.
데이터축은 새명시schema로 동결하고 과거자료를 이관/덮어쓰지 않는다. 테스트축은 거짓 부족판정/불충분기간/동일값 우연/마스크·neutral누출을 거부한다.
정본문서/실행권한·소유권·비교교락/증거수준의5도메인축을 대조한다. 재작업 위험은 자유범위로 일반화하거나 고정 재질문 문구를 의미점수로 오해하는 것이므로 범위를 제한한다.

### 9. preflight·실행 이력

새태그 충돌0·유사런0을 조회했다. 216×8×16×1024=28.31M은 패딩상한이며 실제x/지도/고유량은 동결 뒤 계산한다.
일반 비반복2배풀 대신 명시 SFT 추가4pass이며, 평가/부모/토크나이저/seed/손실을 고정하고 데이터내용/지도량 교락은 PARTIAL_CONFOUNDED로 남긴다.
실제소비·비용·VRAM·기한 통과 뒤만 GPU를 연다. 최초는 DESIGNED였고 아래 실행 이력으로 현재 상태를 구분한다.

2026-10-16 cs0/1/2는12:48:06/12:50:02/12:53:43 종료0(CPU24·course SHA8A5C334D...·실제본문64BF7D9B/RNG·전체소비)이다.
ctWa/b는12:58:49/13:03:14 종료0, 첫update140.873/141.392초·이후최대1.337/1.284초·peak각3090MiB/CPT0이다.
최초 기한예측8666초 대잔여14152초를 확인했다. 자동정책거절 두건은 모델시작전이며 현재 사용자의CPU/GPU·17시완료보고 재승인뒤
cuWa를13:08:29 개방해13:16:32 정확216회/예정노출 일치·최종F0F10C7A...만 저장했다. 현재cuWb가13:16:46 시작됐다.
새학습 CODE/자료는동결이다. 최종시간/실제답/의미판독은 아직미완이며 결과101§197이후로 회수한다.

> 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.
### Stage4cs0W / Stage4cs1W / Stage4cs2W — CPU/실제자료 선결

cs0W는 CPU24(10+5+6+3), cs1W는 실제동결, cs2W는 실제7E부모/전체소비다. CUDA·모델forward/optimizer는0이다.

### Stage4ctWa / Stage4ctWb — 같은 부모 비용8

각8회·최종가중치0, 같은CODE와 전체기한예산을 두팔 모두 확보한다.

### Stage4cuWa / Stage4cuWb — 고정216회 두팔

각216회·추가4pass·최종1개만. current parent/몸통/배치/보존목적은 같고 첫query 근거와지도내용이 다르다.

### Stage4cvW / Stage4cwW — 실제회복/원답검산

부모/두학생의 새1024대화 actual3072답/gold2048답, 기존role/자연DEV/가상/code/native를 분리한다.
부모의기존role2560사건/source320사건은이전raw_role출력과질문/답byte를맞춰새평가경로재현을확인한다.

10/16 13:45 수동 표본 규칙을 추가했다. 새시험 실제답은 아직 읽지 않았지만 부모/대조의 전체집계는 이미 본 후행계획이다.
SHA(TAG,MANUAL_EVIDENCE,neutral_root)의 가족별첫1 neutral을 골라 한영/네조건의 모든32대화·세모델288실제답을 읽는다.
자료구성/학습전 사전등록으로 소급하지 않고 고정해시·비맹검 설명용 판독으로 기록한다. 좋은/나쁜 답을 보고 표본을 바꾸지 않는다.

| 순 | 정확 launcher |
|---|---|
| 1 | `run_P106B_Stage4cs0W_evidence_recovery_cpu.sh` |
| 2 | `run_P106B_Stage4cs1W_evidence_recovery_course.sh` |
| 3 | `run_P106B_Stage4cs2W_evidence_actual_cpu_wire.sh` |
| 4 | `run_P106B_Stage4ctWa_complete_replay_cost8.sh` |
| 5 | `run_P106B_Stage4ctWb_evidence_recovery_cost8.sh` |
| 6 | `run_P106B_Stage4cuWa_complete_replay_full216.sh` |
| 7 | `run_P106B_Stage4cuWb_evidence_recovery_full216.sh` |
| 8 | `run_P106B_Stage4cvW_evidence_recovery_actual.sh` |
| 9 | `run_P106B_Stage4cwW_evidence_recovery_readback.sh` |

cs0/1/2·ctWa/b·cuWa는 실제완료 후 done처리했고, 이전cq/cr와 합8SH를673fda2/2e84e7a에본문/명령/원로그SHA로선보존한뒤정확삭제했다.
재현 명령은101§194/197~199·Phase12감사/Git에있다. cuWb활성 및cv/cw미실행은삭제하지않았다.

## Stage4cx~4cz — 원래 과제 보존과 명시적 새 QA 변환(설계)

### 1. 왜·대안·선택

101§195의 역방향 질문생성 사례는 번호1~4와 일반 QA 메타값만으로 입력을 질문·출력을 답이라고 해석하면 안 된다는 증거다.
자료를 버리거나 모든 문제문구 목록을 만드는 대신 실제 입출력 계약을 보존한다.

| 안 | 실제 동작·예 | 장점 | 단점·영향 | 비용 |
|---|---|---|---|---|
| A·기본 | ‘답목록 meat/yes로 질문을 쓰라’는 입력과 질문목록 출력을 한 user/assistant 쌍 그대로 보존 | 원래 과제방향 불변·기존 canonical 재사용 | 새3턴 QA로 자동 변환되지는 않음·원천 정답성 미검증 | CPU 수초~1분 추정 |
| B·별도 pilot | 원래 과제는 인용데이터임을 알리고 학생 참조에서 새세QA를 명시 생성 | 질문생성/요약 원천도 새QA 소재로 활용 가능 | 교사입력/질문내용도 바뀌므로 순수 프롬프트 인과 아님 | 고정8×두계약16요청·GPU상한10분 |
| C·미채택 | 자유원문을 사람/모델이 전수 역할분류한 뒤 QA로 분할 | 기존 질문을 더 유지할 수 있음 | 전수 의미분류 비용·오분류·온라인 생산에 부적합 | 현재 미측정·별도 계약 필요 |

현재 자율실험 범위에서 A의 안전 분기를 구현하고 B를 소형 진단으로만 수행한다.
교사/출처가 출력한 자유 유형을 코드가 아는 생산자 계약으로 취급하지 않는다. 번호/단어 blacklist로 방향을 판정하지 않는다.

### 2. 질문

원래 한쌍을 byte 보존하는가? ‘원래 세QA 교정’과 ‘명시적 새QA’에서 실제 질문·답이 어떻게 달라지는가?
기존 `canonical.normalize/validate`, 3QA파서/인코더, 교사 프로세스관리·계측재시도·20MB ShardWriter를 재사용한다.
net-new는 불명계약의 원래한쌍 분기와 명시적 새QA 지시·대응 수집이며 기존 생산 기본값을 바꾸지 않는다.

### 3. 예측

원형 보존은 과제방향 역전을 피한다. 새QA는 meat 같은 답 조각을 질문으로 고정하는 부담을 줄일 수 있다.
반대로 교사가 원래 지시를 실행하거나 원래 출력에만 있는 사실·긴 질문·불명확한 후속을 만들 수 있다.
구조가 맞아도 내용은 틀릴 수 있으며 새학생 향상은 이 시험의 판정범위가 아니다.

### 4. 단계 설계

| 단계 | 내용 | 비용·조건 |
|---|---|---|
| cx0W | 원형/역할/불변·프롬프트 소유권 CPU10 | 모델/forward/CUDA0·수초 |
| cx1W | 기존 고정source8을 원형parquet fileSHA/행/id/참조로 역추적·한쌍/작업표 보존 | ko4/en4·이미 본 후행DEV·CPU수초~1분 추정 |
| cyW | 같은8원천의 기존교정/새QA 두계약16요청·순서균형·같은rootseed | 현재 학생평가 종료 뒤만·GemmaMTP2·600초 |
| czW | 전체raw/canonical/시드/채널/토큰 카운터 재계산 | CPU·내용 진실판정 아님 |

같은 temperature1/top_p.95/top_k64/min_p0/presence0/repeat1·ctx8192/합계출력3072·생각요청256이다.
기존교정은 잘라낸 세QA 복구, 새계약은 원래 전체입출력도 인용해 다른 세QA를 만들므로 입력길이/질문내용 교락을 기록한다.
교사는 라벨 내용만 쓰고 코드가 JSON/ChatML을 포장한다. 사고/NOTE는 별도 원형으로 보존하며 학생에 넣지 않는다.
공정한 첫시도 관찰을 위해 요청별1회만 비교하고 온라인 의미검사·같은답 재생성·문구목록을 넣지 않는다.

### 5. 판정

원형 byte 보존/정확출처/실제마스크·16사건/원형·시드·카운터는 기술 판정이다.
구조수락과 의미품질은 구분하고 참조/원래과제/실제질문답을 후행 판독한다.
모든 새후보는 `posthoc_dev`이며 본75M 학습에 자동 편입하지 않는다.

### 6. 비용·preflight

학생 학습/optimizer/CPT0이므로 학습풀2배/학습token 환산은 해당없음이다.
새태그 `p106b_source_task_contract_v1_s1337` 충돌0이다. 유사조회의 공통단어 옛학습과 실제계약/원천/목적이 다르며 동일대응16요청은 없었다.
교사단독 과거표본8874MiB는 참고일 뿐 현재 안전보장이 아니므로 새계측을 보존한다.
600초+45분 마감이 남을 때만 실행하고 현재 학생평가와 GPU를 겹치지 않는다. 16:15이후 새GPU 없음.
다른 SFT LR/300M 스케줄/σ를 빌리지 않는다. 비교는 PARTIAL_CONFOUNDED 개발계약 대조다.

### 7. 권한·영향·런처

| 파일·경로 | 동작 | 현재 권한 | 제외 |
|---|---|---|---|
| 새 task_contract helper/test/diag·4SH | 독립 신설·CPU/GPU소형진단 | 현재 사용자17시까지주도실험 | 기존 frozen CODE/제품/환경 수정0 |
| 새 HF/EVI namespace | 원형작업표/생각/후보·소형집계 생성 | 새namespace 생성 허가 | 기존원형/가중치변경0·전체원답/원천Git제외·20MB분할 |
| 현재계획/결과/기준표/방법론/나침반/목록/원장/인계 | 연쇄갱신 | 사용자 주기기록·한국어커밋 | 타WIP/09/공용검사기수정0 |

코드 호출은 신설4단계로 제한한다. 데이터는 기존자료 이관 없이 원형한쌍/변환계보를 새로 보존한다.
테스트는 번호/일반QA메타 오해·원형byte·생산자계약 경계를 검증한다. 정본문서는 결과후 동기화한다.
기술부채는 새QA의 내용·실교육 미확정이며 이를 학습개방으로 숨기지 않는다.
프로젝트5축의 권한/소유권/조건교락/증거수준/정본동기화를 대조했다. 보호원천·다운로드·외부API·동시학생은0이다.
정확4SH는 아래실행표에 등재하며 stdin/queue/cleanup을 넣지 않는다.

### 8. 한계

기존8은 이미 판독한 개발표본이며 새TEST/모집단 정확도/세계지능/학생향상의 증거가 아니다.
태그·task_type이 같아도 내용방향이 다를 수 있고 원형한쌍도 내용오류는 남는다.
자동생산 기본값/학습배치/MTP/재귀/폭은 변경하지 않는다. 실제학생교육은 이 파일럿으로 자동 개방하지 않는다.

### 9. 실행 이력

최초 cx0W CPU10은13:34:49 종료0이나 cx1W raw133459는13:35:02 종료9였다.
TRAIN전용 from_wrapped가 새평가자료에없는 original_reference_range를 요구했다. 정적68PASS로는이실제메타소비를검증하지못했다.
실제 student_reference_range/생산버전/접두/마커를 검증하는 별도소비함수와3회귀를 추가했다.
기존데이터/코드/원형은수정하지않았고새namespace가비어있음을확인한뒤 cx0Wb CPU13을13:36:44,
cx1Wb 원형8보존을13:36:48 종료0으로회수했다. 최초실패/CPU10원로그는보존한다.
같은미사용태그의최초동결이며이미쓴HF/EVI를덮어쓴것이아니다. 교사16요청/후행검산은아직미실행이다.
정식실행/실제시각/계획과달라진점을 결과101 후속 절과 이 절에 동기화한다.

| 순 | 정확 launcher |
|---|---|
| 1 | `run_P106B_Stage4cx0W_original_task_contract_cpu.sh` |
| 2 | `run_P106B_Stage4cx1W_original_task_packet.sh` |
| 3 | `run_P106B_Stage4cyW_teacher_task_contract_pair.sh` |
| 4 | `run_P106B_Stage4czW_task_contract_readback.sh` |

cx0/cx1은done/이력이며복구실행은 `run_P106B_Stage4cx0Wb_original_task_contract_recovery_cpu.sh`,
`run_P106B_Stage4cx1Wb_original_task_packet_recovery.sh`를사용했다. 이는교사/학습gate-negative가아닌실행전데이터연결수리다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## Stage4da~4de — 정보충분성의 정답 SFT 대 조건부 선호학습(실행 완료·교환비)

### 1. 왜·비교안

101§203/고정32대화 판독에서 보충 뒤 답은 개선됐지만 이미 있는 소녀나이/면적/구역이름을 없다고 되묻는 오류가 드러났다.
전역 재질문 금지나 문구 blacklist 대신, 코드가 제공한 사실과 질문 의존성을 아는 범위에서만 대비한다.

| 안 | 방법·예 | 장점 | 한계·영향 | 비용 추정 |
|---|---|---|---|---|
| A·기준 | 같은 충분/부족 TRAIN의 맞는 첫답만 추가SFT | 변경작음·추가노출 효과 분리 | 틀린재질문/추측을 직접 대비하지 않음 | 비용8 뒤64회·GPU약5~10분 |
| B·선택대조 | A에 ORPO0.1: 이미 있는나이는 숫자답을 선호하고 불필요한재질문을 낮춤; 없는나이는 필요한정보질문을 선호 | 입력별 선택을 직접 대비·별도기준모델 불필요 | 부정답쌍 비용·길이/고정문구 편향·새자료외 일반화 미확정 | A와동일계산64회·두비용/학습/평가약50~80분 예상 |
| C | 프롬프트/생성만 바꿔 재질문을 억제 | 학습비용 작음 | 실제구별 학습과 분리·정당한재질문도 사라질 수 있음 | GPU약5~15분 예상 |

현재 자율실험·이전에 채택한 ORPO 후속 범위 안에서 A/B를 같은E970 부모로 비교한다.
B가 더 낫다는 보장은 없으며 두cost8/전체기한예산이 안 맞으면 본학습을 열지 않는다.

### 2. 질문·예측

충분하면 답하고 부족하면 필요한필드만 묻는 구별이 좋아지는가? 새neutral/새질문체계3의3턴 답과 기존능력은 보존되는가?
예측은 A의 추가양성노출만으로도 일부회복, B의입력별대비가 과잉질문을줄일가능성이다.
실패는 전체재질문억제·다른필드질문·숫자오독/계산실패가 남거나 보존능력이 더 나빠지는 경우다.

### 3. 방법·자료·정본

[ORPO 원문§4.1~4.3/식3~7](https://arxiv.org/html/2403.07691v2)을 다시 읽고 기존 프로젝트
`p106b_conditional_orpo.py`의 답토큰 평균log확률/안정log-odds/softplus를 재사용한다.
참조모델 없는 원리만 차용하며 native/binary 재생·token정규화/정답쌍/계수0.1은 프로젝트의 별도실험이다. 논문성능 재현/권장값이라고 주장하지 않는다.

새태그 `p106b_evidence_preference_v1_s1337`, 같은E9707AA2 최종에서새optimizer로시작한다.
기존 TRAIN1024중가족별128neutral·총512를고정SHA로고르고 한영/4조건의첫턴4096쌍을만든다.
충분상태 chosen=주어진값, rejected=주어진필드가없다는부적절재질문이다.
부족상태 chosen=필요한필드질문, rejected=제시되지않은숨은값을근거없이확정하는답이다.
숨은값자체의세계진실이 아니라 ‘주어진자료만으로답하고추측하지말라’는제한계약 위반을부정답으로정한다.
동일답강제/정당한반복은부정으로만들지않고, 임의공개/교사질문을분류하지않는다. val/test/현재실패답은TRAIN에넣지않는다.

공통replay4096=기존public512+가상256+binary3072+기타code256(한영/4과제균형)이다.
합8192행한pass=64update, micro8×accum16/ckpt-on/seq1024/defaultcompile·Adam5e-5/Muon2e-4,
word/native/binary1·fact0·MTP0를 유지한다. 본75M×4pass와별도인후속진단이며총4epoch나새세계지식량으로부풀리지않는다.
같은step별16쌍을양팔모두추가forward하고 β0대0.1만바꾼다. 비교용쌍의추가처리토큰과지도SFT/native를따로보고한다.
native는현재1728읽기전용창중앞512를동일재사용해64×8192=524288이다. 부모도이미본창임을명시한다.
최종64만한개씩저장·중간모델/TEST선택/옵티마이저저장0이다.
숨은값만다른세계는같은관측/같은재질문을만들수있어4096producer-pair ID/4092양성문장을구분한다.
쌍연결은전체producer ID를쓰고양성메시지hash가같다고부정답을덮어쓰지않는다. 이4별칭은고유지식으로세지않는다.

### 4. 새평가·판정

기존원래128+현재128 TEST의초기visiblefacts를제외한새128neutral·질문체계3·한영4조건1024대화를봉인한다.
실제3072답/골드이력2048답을분리하고 충분첫답/필요재질문proxy/보충후/갱신후/옛role·sourceDEV·가상·code·native를함께본다.
부모E970의옛role2560/source320은현재cv원답과byte일치해야한다.
현재1024시험은이미본DEV가되며 새시험으로중간모델/계수를고르지않는다.
동일neutral의한영/4조건을묶은대응구간은단일seed·조건부효과다. 재질문exact를의미정답으로쓰지않고고정표본을후행판독한다.
σ·채택여유는미측정이므로전역승자/세계지능/배포채택은판정하지않는다.

### 5. 단계·비용·선결

CPU의쌍방향/불변/마스크·β0gradient→동결8192/전체64소비·실제CPU부모→양cost8→전체기한예산→양64회→3endpoint실제답→원답검산이다.
등록태그충돌0/유사런0을조회했다. 64×8×16×1024=8388608은패딩상한이며 실제token은동결/소비에서검산한다.
양팔은동일자료/부모/목적·β만독립변수다. 추가pairforward도동일계산해학습량·비용을감추지않는다.
새GPU는16:15전만·전체평가45분/마감45분여유가필요하다. 동일수량직전평가24.4분을근거로평가상한2700초를정했다.
양팔기한예측은각64×실측warm최대+실측첫update×1.5+300초를더한다. compile/최종DEV한회/저장을포함한예측이지보장상한이아니다.
이는새cost실행전에정한규칙이며기한이안맞으면본런을열지않는다. 교사·다운로드·동시모델0이다.
이것은반복SFT한pass진단이므로일반비반복2배풀과구분한다.

### 6. 영향도·권한·실행이력

| 경로 | 동작 | 권한 | 제외 |
|---|---|---|---|
| 새 evidence_preference helper/course/train/eval/test·9SH | 독립신설 | 현재17시까지CPU/GPU주도실험·기존ORPO후속 | 기존frozen CODE/제품/환경0 |
| 새 HF/EVI/runs태그 | 동결/소형근거/최종2만생성 | 새namespace 허가 | 원본/CPT변경삭제0·원답/가중치Git제외·20MB샤드 |
| 현재계획/결과/기준표/방법론/나침반/목록/WIP·인계 | 연쇄기록/한국어커밋 | 사용자주기정리 지시 | 타WIP/09/공용검사기0 |

기존ORPO수학/인코더/부모loader/훈련배치·보존손실·출력평가를 재사용한다. net-new는 알려진충분성쌍과64회대조다.
코드호출은새SH로한정·기존생산자동전환0이다. 데이터는재노출/합성가상과공개pseudo-label을분리한다.
테스트는숨은정보누출/과잉재질문쌍/마스크/β0정합/전체소비를본다. 정본문서와기한/현재권한을동기화한다.
추가가중치·선호길이편향·가상schema한계가부채이며 성공해도그대로본학습에적용하지않는다.
최초는DESIGNED였다. 현재CPU22/최초정상동결/실제CPU전용인코더·양cost8·양64회가완료됐고새128중립사실평가중이다.
CPU20후동결의양성고유가정오류9·개명런처entrypoint오류2·기본인코더교정마스크차이220token의실물오류9를보존했다.
모든오류는GPU/업데이트0이며불변COURSE C7CFB905...와이전코드는수정하지않고소비경계/회귀를복구했다.
CPU22는14:22:59, 실제E970본문6C5D9C9F...·8192/x1066751/지도62065/64회/3072binary/최소50쌍소비는14:23:04 종료0이다.
비용8은SFT14:28:15/ORPO14:33:15 종료0·peak각3090MiB/CPT0이며같은SFT132757/지도7755/native65536/128쌍을계산했다.
14:34전체예측6697.621초대잔여약8722초로개방했다. dcWa/b raw143434/144043은14:39:56/14:45:34 종료0이다.
각64회/동일노출·최종B0DE3769/0F8A387F만저장했다. ddW raw144619/session59193의새실제답은아직미확정이다.
세부오류/복구원형·실제명령은결과101§206과후속비용절을본다.

| 순 | 정확 launcher |
|---|---|
| 1 | `run_P106B_Stage4da0W_evidence_preference_cpu.sh` |
| 2 | `run_P106B_Stage4da1W_evidence_preference_course.sh` |
| 3 | `run_P106B_Stage4da2W_evidence_preference_actual_cpu.sh` |
| 4 | `run_P106B_Stage4dbWa_sft_preference_cost8.sh` |
| 5 | `run_P106B_Stage4dbWb_orpo_preference_cost8.sh` |
| 6 | `run_P106B_Stage4dcWa_sft_preference_full64.sh` |
| 7 | `run_P106B_Stage4dcWb_orpo_preference_full64.sh` |
| 8 | `run_P106B_Stage4ddW_evidence_preference_actual.sh` |
| 9 | `run_P106B_Stage4deW_evidence_preference_readback.sh` |

CPU의실제완료복구단계는da0Wc/da1Wc/da2Wb다. 최초da0/da1/da0Wb/da1Wb/da2 원형은done이력으로보존한다.
정확실행명령과원형은결과101§206/실제raw가정본이며위최초9행을현재READY큐로쓰지않는다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## Stage4df0W~4dfW — 같은 사실의 질문 표현만 바꾸는 후행 원인 진단

### 1. 왜

현재 부모의 고정 표본에는 충분한 이름을 없다고 묻는 답과, 보충값/새 수신자를 놓치는 답이 함께 있다.
물리 문맥창1024 소진은 관측되지 않았다. 기억장치·추가학습에 앞서 같은 정보에서 질문 표현의 영향을 분리한다.

| 안 | 예·방법 | 장점 | 한계·영향 | 비용 |
|---|---|---|---|---|
| A·선택 | 같은 소녀 이름/누락 상태에서 학습형 질문체계0 대 현재체계3의 첫답만 비교 | 가중치·사실·누락·언어·생성 경로 고정 | 질문과 답변 지시의 재표현 묶음 효과이며 내부 위치/어텐션 기전까지 분리하지 않음 | 구현·CPU 약15~30분 예상, GPU 최대10분 |
| B | 같은 질문에 작은 구조화 기억/조회경로 추가 | 기억 활용 가설을 직접 봄 | 쓰기/조회/형식이 모두 바뀌고 현재 오독과 혼동 | 새 구현/학습·자원 검증 필요, 이번에는 하지 않음 |
| C | 추가 SFT를 더 오래 수행 | 학습량 영향을 봄 | 현재 원인 분리와 다른 가중치를 만들고 시간 증가 | 새 학습·망각 평가가 필요, 이번에는 하지 않음 |

사용자의 오늘17시까지 주도 실험 범위에서 A를 선택한다. 새 기억/지식상태 판별기/실제 학생오답 코퍼스는 구현하지 않는다.

### 2. 질문

같은 충분/부족 사실과 같은 endpoint에서 질문 표현만 바꿀 때 과잉 재질문/값답이 달라지는가?
부모와 두64회 학생에서 변화 방향이 같은가? 현재 체계3은 앞 평가의 같은32첫답과 byte 재현되는가?

### 3. 예측

체계0은 학습에 쓴 질문 방식이어서 일부 회복할 수 있다. 양쪽 모두 틀리면 질문 표현만으로 설명되지 않는다.
회복해도 추론/기억의 모든 원인이 밝혀진 것은 아니다. 특히 연도차 계산과 조건 갱신은 이 첫답 진단만으로 해결됐다고 하지 않는다.

### 4. 단계 설계

- df0W: 독립 코드/CPU 회귀, 기존 고정4neutral·32조건의 두 표현64입력을 새 namespace에 동결한다.
- dfW: 앞 ddW/deW의 완전 종료/검산·새 정적 통과 후, 같은 E970/SFT64/ORPO64를 순서대로 로드한다.
  각32조건×체계0/3=64첫답, 합192답·학습/교사/체크포인트0. 체계 순서는 조건마다 교대한다.
  체계3의96답은 이전 평가의 정확한 첫 입력/정답/출력과 같아야 한다. 다르면 해석을 중단한다.
- 골드/근거/누락/질문대상은 불변이며 실제 출력·종료·입력토큰·메모리를 보존한다.
  여기의32는 이미 읽은 개발 진단 표본이지 새로운 미열람 TEST가 아니다.

### 5. 판정

| 관측 | 판정 |
|---|---|
| 원형 입력/체계3 replay 불일치, 창/출력예산 미달, 모델 변경 | IMPLEMENTATION_ERROR, 내용 인과 해석 금지 |
| 같은 사실에서 값답·필요재질문 proxy 변화 | 고정 표본의 표현 민감성 관측 |
| 표현을 바꿔도 동일 오류 | 그 사례는 표현 단독 수리로 회복되지 않음 |
| 문자 일치/고정질문 수가 높음 | 전체 의미정확도·일반 지능·내부지식 판정으로 승격 금지 |

재질문 exact는 의미판정이 아니다. 원답을 후행 판독하고 모집단 σ/채택여유는 미측정으로 둔다.

### 6. 비용

독립 CPU 수초~수십초/1GPU모델 순차·현재 실제 추론과 같은 FP32 greedy64이다.
192첫답은 현재 완전평가보다 작지만 확정 속도는 미측정이다. 상한600초·16:15 이전 새GPU/마감45분 여유를 강제한다.
예상비용이 남은 기한을 넘으면 준비만 남기며 진행 중인 평가를 중단하지 않는다.

### 7. 실행·preflight

태그 `p106b_evidence_style_v1_s1337`는 registry 충돌0/완전히 같은 런0이다.
학습토큰0·optimizer0·풀2배/배치 변경은 해당 없음, 같은 고정 부모/토크나이저/원답/생성경로를 쓴다.
새 `run_P106B_Stage4df0W_evidence_style_cpu.sh`와 `run_P106B_Stage4dfW_evidence_style_actual.sh`만 순서대로 사용한다.
완료된 과거 SH/출력은 되돌리지 않는다. 새 prefix/metadata만 만들고 모델 원본은 읽기 전용이다.

### 8. 영향도·권한·한계

| 파일·경로 | 동작 | 현재 권한 | 제외 |
|---|---|---|---|
| 새 style driver/test·2SH | 독립 신설 | 오늘17시까지 CPU/GPU 주도실험·기록 승인 | 활성 선호 CODE/제품/환경/공용 검사기 수정0 |
| 새 HF/EVI style namespace | 입력동결/소형근거·private 원답 | 새 실험 산출물 허가 | 이전 HF/원답/생각/CPT 변경삭제0·20MB 샤드 |
| 기존 P106B/결과101/기준표/방법론/COMPASS/목록/TSV/WIP·인계 | 연쇄 기록 | 사용자 정기갱신/한국어커밋 지시 | 타 WIP/09 수정0 |

기존 make/serialize/emit/loader를 재사용해 net-new는32개 두 표현의 대조/재현검산뿐이다.
코드5축과 프로젝트5축에서 비교·소유권·정적/실측·문서 연쇄를 구분한다.
실제 오답의 재교육, 장기 문맥, 기억장치, 구조 원인, 반복방문, 세계지식은 이 진단의 결론 밖이다.
질문·답변 지시 길이와 토큰 위치도 함께 바뀌므로 ‘어순 한 글자만의 효과’로 말하지 않는다.

### 9. 실행 이력

df0W는15:10:20 종료0·CPU5/0.375초·동일32조건/두표현64입력112~156토큰을동결했다.
인계링크형식1건을문서만고친정적은68PASS/0ERROR/6NOT_RUN이다.
ddW/deW는15:20:07/15:20:50 종료0·새128대화/3endpoint·전체원답검산을완료했다.
SFT/ORPO 값답은954/1016of2560, 부모988이며ORPO−SFT+2.421875pp구간은0을제외하지만부모비교는0을포함했다.
ORPO의충분첫답184→241/512와조건갱신295→241/1024·기존역할1111→1061/1536을함께보존해전면승자로채택하지않았다.
예측‘추가양성노출/대비가일부첫답을회복’은한정지지됐지만전체능력/갱신보존예측은지지되지않았다.
dfW는15:21:46 종료0·42.993초·192첫답/96anchor를회수했다. 같은4그룹/32조건에서0표현은모두30/32,
3표현은부모20/SFT22/ORPO22였다. 익숙한표현의회복예측은지지됐지만연도계산은오류가남았다.
가중치/근거/누락/정답/생성은고정했으며새기억/학습/교사/체크포인트0이다. 모수/모집단/내부단일기전은확정하지않는다.
실제원형과한계는[101 §212~215](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에보존했다.
이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 2026-10-16 17시 이후 별도 승인 — 전체 스모크·공개 벤치마크

### 1. 목적과 승인 범위

사용자 최신 지시 `직접 전체 스모크 수행 허가 및 주도적 실험 수행 중 학습시킨 모델 중 벤치마크 수행할 정도의 모델 있는지 확인하여 있다면 벤치마크 수행바람.`에 따른다.
이전 17시 한정 주도실험 권한은 종료됐으며 이번 승인은 스모크와 읽기 전용 모델 평가에 한정한다.
새 본학습/교사생성·다운로드·보호 원천·기존 가중치/원형 변경·Git 변경은 포함하지 않는다.

### 2. 질문·예측

- 전체 스모크의 모든 실제 실행 팔과 계측 계약이 현재 코드에서 성공하는가? 성공을 기대하되 오래된 조합에서 실패할 수 있다.
- 이번 학습 모델을 기존 공개 벤치에서 읽을 수 있는가? 낮은 자유답 성적은 측정 생략 사유가 아니며, 로더/어휘/자료 정합성이 실행 자격이다.
- 좁은 조회 개선이 공개 한국어·영어 과제에도 이어지는가? 일반화가 약하므로 우연 수준/자유답 저성적도 예상한다. 결과를 보고 모델을 제외하지 않는다.

### 3. 단계와 선결

| 단계 | 내용 | 선결·판정 | 비용·GPU |
|---|---|---|---|
| Stage4dgW | 완료·CPU 회귀와 모델/자료 계보 확인 | 5모델 strict load·1920입력 동결, 전체 source와 정확2개 경로 적응 확인 | CPU약9초·GPU0 |
| Stage4dhW | 완료·Codex 호환 전체 스모크 | 전체44실행의 exit·exit0오류표지·계측 오류 모두0 | 실제약8.2분·GPU사용 |
| Stage4diW | 완료·고정 공개 벤치마크 | 5모델·8960선택형/635자유답·길이초과5건 별도 | 실제약19.3분·GPU사용 |
| Stage4djW | 완료·벤치 원답 독립 검산 | 9600raw/SHA/동일ID·채점/제외·10모델쌍 검산 불일치0 | CPU약9초·GPU0 |

정본 BAT의 인계 검사1개는 금지된 다른 환경 진입 파일을 읽으므로 기존 Codex 독립 검사로 대체한다.
`TINYLM_DIR`의 새 격리 출력에서 원래 tag/학습 옵션을 그대로 실행하고, 계측 검사1개는 같은 코드의 LOGS만 그 경로로 맞춘다.
이는 두 개의 명시 경로 적응이며 학습33개·나머지 동적 진단의 생략/가짜 통과는 없다. 수정 없는 정본 wrapper 실행이라고 주장하지 않는다.
원래 synthetic smoke 가중치/로그/캐시의 정확 namespace 해시를 전후 대조한다. 전체 진입점·공용 검사기·제품 소스는 고치지 않는다.

### 4. 벤치 후보와 조건

원래 chat32 부모, 역할학습 최종, 정보복구 최종, 같은 추가64회 SFT/ORPO 최종을 후보로 고정한다.
현재 지식/형식 성적만으로 이미 배포 가능한 모델이라는 뜻은 아니다. 파일·계보·어휘·strict load가 불일치하면 그 이유를 남기고 해당 모델만 제외한다.
보유 공개 벤치의 한국어/영어 고정 표본과 자유답을 사용하며, 보호 자체 held-out/TinyDataset·다운로드는 사용하지 않는다.
학습0·체크포인트 쓰기0·교사0이며 기존8문항/가상조회와 별개 지표다. GPU 결과를 보기 전에 다음 범위를 고정했다.
한국어 KoBEST COPA/HellaSwag·KLUE NLI/YNAT와 영어 PIQA/HellaSwag/ARC-easy를 각256문항, KorQuAD 지문 QA와 GSM8K 자유답을 각각64문항 요청한다.
5모델·MC8960개/자유답최대640개이며 문맥 초과 문항은 자르거나 대체하지 않고 같은 ID로 제외 기록한다.
평가seed20261016·FP32 MATH·문맥1024·자유답greedy128·ChatML EOT·native NTP 고정이다. 총 상한은5모델의 불확실한 소요에 여유를 둬7200초로 사전 조정했으며 결과에 따른 변경은 아니다.
MC 주지표는 기존 scorer의 후보 합우도 선택, 문자 정규화/내부PMI는 보조다. 자유답은 공백/NFKC 정규화 일치와 별도 문자겹침 보조, GSM은 명시 숫자 파싱 일치를 기록한다. 공식 전량 하네스 점수/코드 실행 pass@1로 부르지 않는다.
단일학습seed·공개자료의 사전학습 중복 미전수검사·우도선택과 자유답의 차이·부분/자체 채점의 한계를 명시한다.

### 5. 재현과 영향도

`scripts/diag_p106b_authorized_smoke.py --mode check`, `scripts/test_p106b_authorized_smoke.py`, 이후 같은 driver의 `--mode full --execute`를 사용한다.
이번 단계는 직접 실행 승인으로 Python 명령을 보존하며 별도 queue/SH는 만들지 않는다.
코드 영향은 새 독립 어댑터/회귀뿐이다. 데이터는 새 runtime/소형 evidence만 쓰며 원형 스키마·기존 모델은 그대로다.
전수 정적 후 실제 수행하고 계획/결과/기준표/COMPASS는 주장 등급을 구분해 갱신한다. 설치·업로드·commit·삭제를 실행하지 않는다.

### 6. 실행 이력

CPU 회귀4개와 canonical action 계약은 통과했다. Stage4dhW는17:32:06~17:40:20 실행·전체44팔 실패0/exit0오류표지0/필드오류0이다. 원래 synthetic 산출물 전후SHA가 일치했다.
기존 runlog의 보조 registry가 원래 로그 경로를 읽는 누락은 실제 판정과 분리했다. 이번에 추가된32개 stage/log쌍만 기존 safe API로 제거해 나머지 byte불변을 독립 SHA로 검산했고, 격리 JSON을 읽는 별도32행 색인을 생성했다. 과거 데이터/가중치/로그는 변경하지 않았다.
실행중 소스는 변경하지 않았으며 재실행이 금지된v1의 이 한계를 소형 귀속 기록에 남겼다. 이후 benchmark driver/test는 별도 CPU/정적 검증 후 동결한다.
공개 벤치는17:49:58~18:09:18에 실제 완료했다. [결과101 §217~219](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)가 원로그/표/34답 후행 판독과 한계를 소유한다.
후행 `scripts/read_p106b_authorized_benchmark.py`는 주scorer/모델을 import하지 않는독립CPU검산이며 회귀4개 통과다.
2000회 대응 재표집은 KorQuAD지문/NLI전제,나머지는문항ID를단위로하며 학습seed불확실성과다중비교는보정하지않는다.
동결된 주driver/자료/가중치를 실행 중 변경하지 않았다. 원래 부모의 위키 이어쓰기·반복은 후속의 턴종료로 줄었지만, 무관한 단답/필드 오독이 남아 일반 QA 성공 예측은 지지되지 않았다.
한국어 exact0~2/63·GSM0/64, 한국어 선택형 최고도 표본 다수라벨 기준 이하이며 제한적 PIQA/ARC 선택 신호와 구별한다. `3` 대 `3인`의 의미동등 예외도 보존해 자동일치0을 의미오답률로 바꾸지 않았다.
추가 ORPO의 소수 선택형 개선만으로 전체 기본모델을 채택하지 않았다. 공용 정적검사의 명칭호환1건은 승인 대기이며 실제44팔 실패와 혼동하지 않는다.
이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 2026-10-16 야간 승인 — 명시적 한영 근거 QA·균형 재교육과 지시 표현 안정성

### 1. 왜 — 자연 QA와 보존을 먼저 확인한다

사용자는 2026-10-17 10:00 KST까지 CPU/GPU 주도 실험·계획/결과/나침반/원장/인계·한국어 로컬 커밋과 명령 선보존 후 완료 SH 정리를 허가했다.
이 승인은 보호 TinyDataset/사전 접근, 원본 데이터·기존 가중치 덮어쓰기/삭제, 설치/다운로드, push/PR의 허가가 아니다.
문헌·정·반 보조는 실제 필요할 때 gpt-6.1-sol/max로 최대3개를 호출하고, GPU와 공유 정본 쓰기는 총괄이 소유한다.
[결과101 §203·212·215·219](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)는
정보 보충·충분 첫답·조건 갱신·기존 역할의 교환과 지시 표현 민감성, 공개 자유답의 약함을 확인했다.
기존 번호형 원천을 QA라고 추정하는 대신 보유 KorQuAD/SQuAD TRAIN의 명시적 context/question/answer_start를 사용한다.
오프셋 일치는 제공 지문과 정답 문자열의 계약이며 전수 의미 정답성이나 새로운 세계지식의 증명이 아니다.

### 2. 질문

| 질문 | 대조·의미 |
|---|---|
| 실제 지문과 질문을 함께 교육하면 자연 QA 자유답이 개선되는가 | 같은 E970 부모 대비 공통 교육 묶음의 설명적 변화 |
| 같은 QA의 두 지시 wrapper 사이 분포 정렬이 추가로 도움이 되는가 | 같은 두뷰 CE·자료/배치/초기화에서 lambda0 대0.05의 직접 대응 |
| 같은 오답만 더 일관되게 내는가 | 양뷰 모두 정답·최악뷰·동일 오답과 대상/값 갱신64답을 별도 확인 |
| 역할·정보 충분성·보충·갱신·언어능력이 유지되는가 | 기존 지표와 고정 native32·추가 원문 표본을 구분 |

### 3. 예측 — 이득과 실패 가능성

명시적 지문/질문/정답이 원천 방향 추정과 교사에게만 보이던 문맥 결손을 줄일 것으로 예상한다.
자연 QA의 공통 개선은 자료/추가학습 묶음의 효과이며 lambda의 효과가 아니다.
일관성 보조는 정확도를 보장하지 않고 동일 오답 수렴·갱신 무시·언어 퇴행을 키울 수도 있다.
두 지시 wrapper는 원질문을 재표현하지 않으므로 질문 자체의 패러프레이즈 일반화라고 부르지 않는다.
원문 [PARAREL §8](https://aclanthology.org/2021.tacl-1.60.pdf)은 양방향 KL과 MLM 보존을 함께 사용했으며,
MLM 제외 시 일관성80.8이면서 정확도16.9로 악화했고 SQuAD 재표현 전이는 기준선과 동급이었다.
이번 것은 BERT의 재현이 아닌 TinyLM causal 답 위치에 적용하는 지시뷰 일관성 응용이다.

### 4. 단계 — 모든 실행 전 선결

| 단계 | 상태/내용 | 선결·비용 |
|---|---|---|
| Stage4dk0W | 준비: 명시 QA 원천·기사/문맥 분리·양뷰 CPU/실물 소비 | 새 namespace, 원형 SHA, 한국어/영어 각4096 TRAIN QA를 상한으로 선별. CPU 약5~15분 추정 |
| Stage4dkWa/Wb | 준비: 같은 부모·두 팔 각8업데이트 비용 | 양뷰 shift/내용 target 정렬·CE/KL gradient 회귀와 전수 정적 통과. 새 checkpoint 저장0, GPU 각3~8분 추정 |
| Stage4dlWa/Wb | 조건부: 균형 CE와 CE+뷰 KL | 같은 E970·seed1337·micro8/accum16·seq1024·checkpoint ON·compile default·4회 순회. 비용8 결과로 마감 여유 검산 후 개방 |
| Stage4dmW | 조건부: 실제 자유답·양뷰·갱신·보존 대응 평가 | 기사 단위 봉인 TEST, 실제 생성과 teacher-forced 지표 분리. GPU 약20~60분 추정 |
| Stage4dnW | 조건부: 독립 원답 검산·고정 표본 판독 | 원답 SHA/ID/gold/분모 검산·기존 양성/음성 원형 보존. CPU 중심 |

자연 QA TRAIN은 같은 문맥/질문/gold에 wrapper0/1을 함께 제공하고 DEV/TEST에 wrapper2도 별도로 둔다.
공식 DEV와 겹치는 기사·문맥/정규화 질문, SQuAD common_bpb의 정렬 고유4000문맥, 검출된 문맥 조각 겹침을 제외/계측한다.
그 뒤 TRAIN 기사를 실험 train/dev/test로 나누며 dev/test는 언어별256 QA를 상한으로 동결한다.
전체 문맥·두 입력·128 출력 예산이1024 안에 들어가는 행만 사용하고 조용한 문맥 자르기/정답 중심 crop은 금지한다.
첫 시험의 SQuAD 무답변 문항은 제외한다. 원래 QA의 여러 정답과 answer_start·원기사·원천 SHA를 보존한다.
이전 사전학습/모든 SFT의 의미 중복은 전수 감사하지 않았으므로 새 세계지식·완전 미노출 주장은 하지 않는다.

각 pass에는 자연 QA 두뷰 최대16384행에 기존 role_bridge2048·정보복구1024·코드768·가상관계256행을 더하는4096행 보존 혼합을 계획한다.
공급·실제 인코더 계수와 마스크를 먼저 확인하며 부족하면 반복으로 고유량을 채우지 않고 단계에서 중단한다.
잘못된 과거 assistant turn은 기존 전용 인코더의 supervised_assistant_turns 계약으로 마스크한다.
두 팔의 모든 CE·자연어 train 창·행 순서·초기 본체·optimizer와 헤드 계산 경로를 같게 하고 자연 QA 내용 토큰 SymKL 계수만0/0.05로 바꾼다.
KL은 각자 shifted y의 실제 내용 토큰 위치를 정렬하며 target ID 열이 다르거나 assistant turn/EOT 구분이 모호하면 거부한다.
KL의 vocab축은 합산하고 실제 대응 내용 target 수로 평균하며 첫 내용 토큰/나머지 토큰을 따로 기록한다.
양팔 모두 같은 pair/head 경로를 계산한다. 모범 답 prefix의 KL과 실제 자유 생성의 일관성을 혼동하지 않는다.
기존 이진/사실 보조 헤드·MTP·새 router·공유구조 변경은 이번 두 팔에서 사용하지 않는다.

### 5. 사전 판정

누설·원천/부모 불일치·마스크/shift 결함·비유한 gradient·실제 실행 미완료는 기술 실패/미실행으로 분리한다.
주지표는 봉인 자연 QA의 언어별 자유답 EM/F1 및 양뷰 모두 정답 비율이며 정답 문자열/정규화는 고정한다.
공식 KorQuAD/SQuAD 채점 전체와 다른 로컬 규약은 별도 이름으로 보고한다.
wrapper만 바뀌는 불변성에 더해 한영 각4개 새 코드 사실의 wrapper2×필드2×명시 값 갱신2, 총64답으로 변화 민감성을 점검한다.
일관성만 늘고 동일 오답이 늘거나 갱신/역할이 악화하면 지능 이득으로 채택하지 않는다.
기사 단위 대응 재표집·학습 seed 수·다중비교 여부를 보고한다. 새 조건의 보정 sigma가 없으므로 과거 자를 차용하지 않는다.
첫seed 방향만으로 전역 기본값을 바꾸지 않으며, 여유가 있으면 같은 사전계약의 두번째 seed 또는 분리 후속을 검토한다.

### 6. 비용·시간 경계

시작은10/16 22:10 KST, 승인 종료는10/17 10:00 KST다. 09:00부터는 새 큰 실행을 열지 않고 결과/정본/정적/인계/커밋 정리를 예약한다.
현재 GPU 여유14687MiB는 시작 스냅샷일 뿐 OOM 보증이 아니다. 각 팔의 실제 peak/8업데이트 비용과 남은 시간을 확인한다.
현 물리 Z: 여유는 약307G이며 WSL 파일시스템618G 표시와 혼동하지 않는다. 기존 checkpoint·데이터 정리는 하지 않는다.
최대 두 새 최종 모델 약0.75GB와 새 파생 자료/원답을 우선 예산으로 두고 중간 모델의 무분별한 저장은 하지 않는다.

### 7. 실행·영향도

새 데이터/손실/강제 소비 driver와 CPU 회귀41개를 구현했고, 다음 SH/TSV를 등록한다. 실행 전 전수 정적과 실제 CPU wire를 확인한다.

| 정확한 단계 | 실행 SH | 역할 |
|---|---|---|
| Stage4dk0W | `run_P106B_Stage4dk0W_night_grounded_cpu.sh` | 새 자료 동결→실제 CPU 부모/마스크/소비 검산 |
| Stage4dkWa | `run_P106B_Stage4dkWa_night_ce_cost8.sh` | CE8회 비용, 체크포인트 저장0 |
| Stage4dkWb | `run_P106B_Stage4dkWb_night_consistency_cost8-hold.sh` | ⏸ 역사V1 패딩 계약 무효로 보류,새V2 비용을 별도 수행 |
| Stage4dlWa | `run_P106B_Stage4dlWa_night_grounded_ce4-hold.sh` | ⏸ 역사V1 미실행 보류,패딩 수리한 새Wc의 CE640과 구별 |
| Stage4dlWb | `run_P106B_Stage4dlWb_night_grounded_consistency4-hold.sh` | ⏸ 역사V1 미실행 보류,새Wd의 KL640과 구별 |

구조상640×8×16×1024=83,886,080은 padding 포함 SFT 슬롯이며 실제 학습 토큰이 아니다.
실제 x/assistant target은 동결 encoder 소비로 별도 확정하고 native640×8192=5,242,880을 추가 구분한다.
4pass 노출이므로 사전학습의 풀≥2배 규칙을 만족한다고 부르지 않고, 원천 기사봉인·반복량·실제 자유답으로 검증한다.
손실 계수0/.05는 이번 연구축이며 전역 기본값이 아니다. 수치부호/소수 구별과 raw exact를 보존하는 로컬 QA metric을 쓰며 공식 전체 채점과 구분한다.
새 데이터 모듈·학습/평가 driver·CPU 회귀·SH와 새 HF/EVI namespace만 신설하며 기존 CODE/학습함수/제품을 덮지 않는다.
기존 자료/토크나이저/가중치/원로그는 읽기 전용이고 보호 원천/타 WIP/09·환경 설정·공용 검사기 추가수정은 제외한다.
데이터 계보·손실 분모·비교 통제·실제 자원·문서 연쇄를 영향 축으로 기록한다. 기존 main의 만료 deadline은 전역 monkeypatch하지 않는다.

### 8. 한계

제공된 문맥에서 정답을 인출하는 교육이며 광범위 지식·자발적 추론·thinking 학습이나 Falcon 수준 도달의 증명이 아니다.
지시 wrapper의 안정성, 질문 의미 일반화, 새 기사 QA, 과거 능력과 일반 언어를 별도로 보고한다.
명시 span·코드 사실과 사람/원천 정답성이 다른 증거임을 유지한다. 학생 오답·원문은 후행 검토용으로20MB 이하 private 조각에 남긴다.

### 9. 실행 이력

10/16 야간 착수: 문헌·정·반을 필요시 각1회 호출해 source 방향·역할 replay 누락·first-turn 전용 선호·KL 붕괴 반증을 독립 대조했다.
10/17 회수: [101 §224,226~229](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)의 V2 양팔640회를 완료했다.
DEV1epoch 이후 악화와 부모5lane 저장 뒤 사례키 오류를 보존하고 새 평가 복구를 CPU45/실제 원형 전수로 준비했다. 실제 학생 품질은 아직 미판정이다.
이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

### 10. 패딩 실제 소비 복구 — 동일 과학 설계, 새 실행 버전

[101 §221](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)의 V1은 자료/마스크/순서 검산을 보존하되,
패딩 `null`을 검증 성공으로 둔 누락 때문에 비용 팔이 GPU 이동 전에9로 거부됐다. 학습/방법론/OOM 음성이 아니다.
기존 코드의 `<pad>` 호환과 None/동일EOT 거부를 추가하고 실제 CPU8×1024 패딩 tensor/input/target/segment를 검산한다.
자료 원형·선택 SHA·640회·손실/배치 조건은 그대로이며 새 namespace `p106b_night_grounded_v2_s1337`과 아래 정확한 단계만 재검증한다.

| 단계 | SH | 선결/상태 |
|---|---|---|
| Stage4dk0Wb | `run_P106B_Stage4dk0Wb_night_grounded_padding_cpu.sh` | CPU45·새 동결·actual padding/encoder |
| Stage4dkWc | `run_P106B_Stage4dkWc_night_ce_padding_cost8.sh` | 실제 CE8회·저장0 |
| Stage4dkWd | `run_P106B_Stage4dkWd_night_consistency_padding_cost8.sh` | 실제 KL8회·저장0 |
| Stage4dlWc | `run_P106B_Stage4dlWc_night_grounded_ce4_padding.sh` | 동일 cost 두팔 후640회 CE |
| Stage4dlWd | `run_P106B_Stage4dlWd_night_grounded_consistency4_padding.sh` | 동일 cost 두팔 후640회 CE+KL |

V1 미실행3런처는 원본 소급 실행을 막기 위해 hold로 두며, 수행한 CPU/실패 cost SH만 done으로 분류한다.
V1 코드/원형/원로그는 로컬 커밋 `160d587`에 보존했다. 새 PASS로 옛 실패를 바꾸지 않는다.

### 11. 고정 평가 준비 — 실제 답/동일오답/보존을 함께 회수

Stage4dk0Wb는 CPU45/실제 패딩·소비 완료, Stage4dkWc/Stage4dkWd는 각8회/저장0으로 완료됐다([101 §222](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)).
아래 입력은 당시 CE640 진행 중 답안 생성 전에 동결했다. 이후 양640회 완료·사례키 복구는 뒤의10/17절이 소유한다. TEST로 checkpoint·epoch·계수를 고르지 않고 마지막4pass만 비교한다.

| 정확 단계 | SH | 내용·선결 |
|---|---|---|
| Stage4dm0W | `run_P106B_Stage4dm0W_night_eval_frozen_inputs.sh` | 순수 평가24CPU·TEST512QA/3뷰·cube64·보존·같은 공개1920·추가 native256 동결 |
| Stage4dmWa | `run_P106B_Stage4dmWa_night_parent_actual_answers.sh` | E970 부모·동일 FP32 MATH/greedy/cache·새 학습0 |
| Stage4dmWb | `run_P106B_Stage4dmWb_night_ce_actual_answers-hold.sh` | ⏸ 역사 evaluator 키 충돌로 미실행 보류,새복구 evaluator는 별도 완료 |
| Stage4dmWc | `run_P106B_Stage4dmWc_night_consistency_actual_answers-hold.sh` | ⏸ 같은 키 충돌로 미실행 보류,새복구 원답과 섞지 않음 |
| Stage4dnW | `run_P106B_Stage4dnW_night_paired_raw_readback.sh` | 세 endpoint 전량·기사 단위 CI·동일오답/빈답 구별·코드 source/gold 재구성 |

역할16개/정보복구8개 neutral root의 모든 언어·지시/조건 자식을 함께 골라 원형 실제 이력과 gold 이력을 분리한다.
코드 보존은 kind/언어 균형96행으로 확인한다. 원문 role/정보복구의 한 문장 일치가 자유 재질문의 의미 품질을 전부 판정하지 않는다.
기존 공개1920은 학습 전에도 본 개발/비교 코호트이며 새 독립 벤치라고 하지 않는다. 원형 질문·후보/정답·예상 길이 skip을 CPU에서 잠근다.
새 TEST는 본 실험 article 기준으로 봉인했지만 사전학습 의미 누설 전수 감사는 없다. native32의 종전 정밀도와 추가256의 FP32 MATH를 별도로 기록한다.
실제 prompt/공백포함 답안과 SHA·종료·case집합·6원답 lane/2native lane을 모두 요구한다. 빠진 lane/빈 manifest/틀린 skip을 완료로 승격하지 않는다.
평가 raw는 private20MB 이하 조각, 검산·수치·SHA는 작은 evidence로 보존한다. 수동 판독은 예시의 실제 문맥/질문/답·오류 유형을 함께 남기고 전수 정확도로 부풀리지 않는다.

## 2026-10-16 야간 추가 준비 — 원부모·원문 계속학습과 같은 QA의 대응

### 1. 왜

현재 E970→명시 QA의 중간 SFT 이력과 기초 언어학습량을 혼동하지 않기 위해 별도 원부모 대조를 준비한다.
현재 CE/KL의 최종4pass/TEST는 그대로 회수하고, 그 결과로 기존 음성을 소급 바꾸지 않는다.
세 후보는 원 P090B→동일 QA, 원 P090B→원문 약299M 추가→동일 QA, 새 증강/선호이다.
원인 분리가 쉬운 앞의 두 경로를 우선 준비하며 새 증강/선호는 이 비교에 섞지 않는다.
이는10/17 10시까지의 현재 자율 실험 승인 범위이며 설치/다운로드·보호 원천·원본 덮어쓰기·push를 포함하지 않는다.

### 2. 질문

추가 원문 최적화 후 같은 SFT를 받으면, 원문 손실뿐 아니라 실제 지문 QA/역할/갱신과 공개 선택·자유답이 개선되는가?
SFT 이력이 누적된 E970과 원 P090B의 차이는 ‘이력 패키지’의 기술 비교로만 남긴다.
핵심 추가학습 대조는 공통 P090B를 조부모로 한 native0 대 native약299M이다.

### 3. 예측과 원문 근거

추가 자연어 예측이 기초 표현을 개선할 수 있지만 QA 정답률 향상을 보장하지 않는다.
[Midtraining 원문 §3~5](https://arxiv.org/html/2510.14865v2)은70M~1B를128B토큰 학습한 결과이며 범용 지시 혼합의 효과가 작고 목표 분포 정렬이 중요했다.
혼합/전문단독 대조는 도입 시점도 달랐으므로 혼합비 하나의 인과로 옮기지 않는다.
우리의 추가0.299B 효용을 직접 보장하는 문헌은 아니며 실물 비용·답안으로 반증한다.

### 4. 통제·구현 범위

새 `p106b_night_foundation_v1_s1337`만 사용한다. 원부모는 P090B SHA `12E18658CDCD0AFEBE5A87073DC8977304C0D490A03A8471779D514FBB0D9950`다.
같은 dense14/chat32/seed1337·micro8×accum16/seq1024/ckptON/compiledefault·MTPoff를 유지한다.
추가 원문은 기존 비보호 `ko-en_601000000_chat32/train.bin`만 읽고 VAL은 학습하지 않는다.
새 토큰·원문 복사/다운로드/토크나이저 확장은 없다. 기존 cache의 이전 부모 노출 중복을 전수 감사하지 않았으므로 ‘새 고유299M’이라고 하지 않는다.
CPT는 새 Adam/Muon 모멘트, 고정 Adam1e-4/Muon4e-4/WD0/clip1, 삼진 anneal1을 유지하며 재어닐링하지 않는다.
두 QA 팔은 같은 V2 자료·같은 두뷰 CE/역할·정보복구·코드 replay/native5.24M, Adam5e-5/Muon2e-4·새 모멘트·640회/4pass/계수0을 사용한다.
CPT 후 QA의 RNG를 다시1337로 초기화해 QA 순서와 optimizer 초기화가 다르게 이어지지 않게 한다.

### 5. 실제량·선결

현재 train은597,995,000token이고 VAL3,005,000token이다. 같은 풀을 쓴다는 이름만으로 크기를601M이라고 하지 않는다.
새 CPT는2281×8×16×1024=`298,975,232`target이며 실제 TRAIN/처리 비는`2.000148962`다.
1025stride 창을 seed1337로 섞고 새 CPT 내부에서는 복원 없이 추출해 창/다음 target이 서로 겹치지 않게 한다.
QA는 이미 동결한V2 source SHA·마스크·순서·실제 토큰을 재사용하고, 원문 CPT와 assistant-only SFT의 분모를 별도로 기록한다.

| 준비 단계 | 내용 | 실행 선결 |
|---|---|---|
| Stage4do0W | 원부모/원문 창·실제 QA 소비 CPU | 새 독립 namespace·원본SHA/소유 경계 |
| Stage4doWa | 원부모 QA8 비용 | 실제 CPU 패딩·init/source 대응 |
| Stage4doWb | 원문 CPT8 비용 | 동일 geometry·full-target gradient/peak·fresh parent |
| Stage4doWc | 원문 CPT2281 | 같은 CODE 비용8·모든 잔여 QA/평가/09시 정리 예산 충족 |
| Stage4doWd | CPT 후 QA8 비용 | CPT strict/SHA·QA source/초기화 소비 동일 |
| Stage4dpWa | 원 P090B→QA640 | QA8 및 두 팔 전체/평가 예산 |
| Stage4dpWb | CPT→QA640 | CPT와 QA8·같은640 순서/노출 |
| Stage4dqW | 부모별 실제 QA/보존/공개 비교 | 별도 evaluator·새 raw/동일 고정 입력·원형 보존 |

SH는 실제 구현/CPU가 완료된 단계만 등록하며 존재하지 않는 파일을 실행 권고하지 않는다.
CPU/정적은 모델 품질이 아니고 cost8은 기간/자원 선결만 확인한다.

### 6. 판정과 모델 보존

추가 native 직후와 QA 후의 원문 손실을 구분하고, 최종 QA/양뷰 모두정답/같은오답/갱신/역할/공개 벤치를 회수한다.
현재 TEST를 보고 epoch/LR/계수를 고르지 않는다. 후속 QA는 마지막4pass와 DEV CE 최소 대표를 따로 보존할 수 있으나 DEV 선택임을 표시한다.
원문 CPT1개와 두 QA 최종/DEV대표 최대4개를 약1.9GB의 추가 weight-only 예산으로 잡고 optimizer·매step 모델은 저장하지 않는다.
native CE만 개선되면 언어모델링 개선이며 QA/일반 지능 개선이라고 하지 않는다.
부정 결과도 큰 사전학습량 부족 가설 전체의 기각이 아니며 단일 학습 seed·다중비교·이력 교락을 보고한다.

### 7. 비용·기한

기존 원부모300M 실측 약81분은 참고값일 뿐 이번 계속학습의 증거가 아니다.
새 full-target 비용8로2281회와 QA 두640/평가/마지막60분을 다시 예산 검산한다.
현재 E970 두640 대조를 먼저 완료한다. 새 비교가09시 이전에 들어가지 않으면 자동 축소·무단 연장하지 않고 정확한 미실행 이유를 남긴다.
기존16GB GPU는 단독 소유로 순차 실행하며 활성 모델 간 resource 경쟁을 만들지 않는다.

### 8. 영향도·한계

제품 아키텍처/default/토크나이저·다른계획/WIP·공용검사기의 의미는 바꾸지 않는다.
새 course/driver/CPU회귀·런처·새 HF/EVI/CPT와 계획/결과 정본만 추가한다.
독립변수는 추가 원문 최적화 패키지이며 optimizer 재초기화/계수·기초 SFT 이력 차이를 지운 단순 ‘토큰만의 법칙’으로 해석하지 않는다.
본75M×4epoch SFT 목표와 별도이고, 원문299M을 요청한300M SFT 완료라고 바꿔 부르지 않는다.

### 9. 현재 상태

10/17 실제 CPU16과 원부모 QA/native 각8회 비용을 완료하고, 전체 잔여 예산 후 원P090B→QA640 기준 팔을 실행 중이다.
원문 CPT/그 후 QA와 실제 효과는 NOT_RUN이다([101 §228](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)).
전수 정적·원천/실물 CPU·비용·최종 답안의 순서를 지키고 실제 끝난 단계만 결과문서에 누적한다.
이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

구현 후 정확한 SH는 다음과 같다. 아직 실물 완료를 뜻하지 않는다.
- Stage4do0W: `run_P106B_Stage4do0W_foundation_cpu_contract.sh`.
- Stage4doWa: `run_P106B_Stage4doWa_foundation_baseqa_cost8.sh`.
- Stage4doWb: `run_P106B_Stage4doWb_foundation_native_cost8.sh`.
- Stage4doWc: `run_P106B_Stage4doWc_foundation_native_299m.sh`.
- Stage4doWd: `run_P106B_Stage4doWd_foundation_cptqa_cost8.sh`.
- Stage4dpWa: `run_P106B_Stage4dpWa_foundation_baseqa_repeat4.sh`.
- Stage4dpWb: `run_P106B_Stage4dpWb_foundation_cptqa_repeat4.sh`.

새 QA reader는 원형 data SHA/CODE·tokenizer/shard를 검증하되 데이터를 재사용하기 위해 E970 물리 가중치까지 요구하지 않는다.
원 P090B의 실제 CPU strict/body·native TRAIN 전체 ID 최대값·실제 단일창/패딩·실제 encoder를 별도로 확인한다.

Stage4do0W는23:50:48에 CPU16과 실제 parent/cache/encoder를 검산해 완료했다([101 §225](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)).
CPT/그 후 QA·평가 효과는 NOT_RUN이며 비용은 이후8회로 회수했다. E970 CE/KL 대조와 별도로 기록한다.

## 2026-10-17 평가 문항 식별자 복구 — 학습·질문·원답 불변

Stage4dmWa는 자연 QA3뷰/조건 cube/역할/정보복구/코드의 원답을 저장한 뒤 코드 집계에서9로 종료했다.
기존 `(semantic_root,turn,history)`는 같은 언어의 서로 다른 자식 질문까지 중복으로 오인했다.
128개 코드 event 중3키/6행이 충돌했으며 실제 messages SHA는 모두 달랐다. 언어만 키에 넣어서는 고쳐지지 않는다.
원형96개 문항의 canonical row SHA·lane·동결 index로 사례 ID를 만들고, semantic root는 묶음 집계에만 쓴다.

세 후보는 저장된5 lane을 그대로 검산·새 수집 폴더로 계보 복사하는 복구, 전량 재추론, 옛 코드 수정 후 혼합이다.
이미 얻은 원답을 바꾸지 않고 비용을 줄이는 첫 경로를 채택한다. 옛 코드/원답/실패 로그와 판정은 불변이다.
새 evaluator `evaluation_v2/evaluate_v2`는 원본 `evaluation` 입력을 그대로 참조하고 source/CODE SHA를 고정한다.
CPU에서 실제 role/recovery/code 전수 원형을 모의 emitter로 통과시켜 동일 입력의 상충 gold·누락·중복·이력 재구성을 먼저 확인한다.
모의 emitter는 답변 품질 증거가 아니다. 저장된 parent5 lane의 원답/질문/gold/출처/순서/종료와 manifest SHA를 검산한 뒤 사본만 새 폴더에 쓴다.
새 원답으로 위장하지 않고 `CARRIED_VERIFIED_RAW`·이전 원로그/manifest SHA와 이전 전체 body 종료 지문 미기록 한계를 명시한다.
공개 벤치/native만 부모에 추가 실행하고, 두 학습 학생은 같은 고정 입력/FP32 MATH/greedy/cache로 전량 실행한다.
각 lane 완료 receipt를 따로 저장하고 미완성 raw가 있으면 덮어쓰거나 자동 재생성하지 않는다.

| 단계 | SH | 선결/범위 |
|---|---|---|
| Stage4dm0Wb | `run_P106B_Stage4dm0Wb_night_eval_casekey_cpu.sh` | 새12+driver CPU·실제 동결 원천 전수 wire/상충 검사·부모5 lane 손실 없는 회수 |
| Stage4dmWd | `run_P106B_Stage4dmWd_night_parent_metrics_recovery.sh` | 회수 parent5 lane 보존·미실행 공개/native만 추론 |
| Stage4dmWe | `run_P106B_Stage4dmWe_night_ce_metrics_recovery.sh` | CE640 고정 endpoint 전량8 lane |
| Stage4dmWf | `run_P106B_Stage4dmWf_night_consistency_metrics_recovery.sh` | KL640 고정 endpoint 전량8 lane |
| Stage4dnWb | `run_P106B_Stage4dnWb_night_recovery_paired_readback.sh` | 새 사례키/원형/6raw+2native/세 모델 대응 전량 검산 |

추가 원부모/CPT 후 평가도 같은 원형·평가 함수를 새 endpoint 폴더에서 재사용할 수 있도록 준비하되 아직 실물 완료를 뜻하지 않는다.
09시 GPU 중단·10시 승인 종료, teacher/학습/가중치 저장0, 원본/보호 데이터/다운로드/push 금지 경계는 유지한다.
현재 1개 학습 seed의 사례 CI는 학습 재현성 분산이 아니다. 기존 음성을 PASS로 바꾸지 않는다.
이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 2026-10-17 원부모·원문 계속학습의 같은 평가 연결

Stage4dm0Wb의 실제 source wire/계보 이관은 완료됐다. 원 P090B의 QA 기준 팔은 진행 중이며 CPT후QA는 아직 미실행이다.
계속학습의 효과를 native CE 하나로 판단하지 않도록 이미 봉인한 원형512QA/3뷰·cube64·역할/정보복구/코드·공개1920·native32/256을 그대로 사용한다.
세 후보는 전체 같은 평가, 손실만 집계, 성적 좋은 문항만 별도 선택이다. 선택 편향과 다른 분모를 피하는 첫 경로를 채택한다.
source/CODE/질문/gold·FP32 MATH/greedy/cache/길이 예산은 고정하고 새 endpoint 폴더에만 쓴다.
새 evaluator는 foundation arm/2281·640회/실제 x·target/원형SHA/초기화SHA/DEV 선택을 엄격히 대조하며, model strict 로딩·각 lane body불변·원답/SHA 독립검산을 요구한다.
TEST로 epoch/LR을 고르지 않는다. QA최종4가 사전 주대조이고 DEV CE 최소 대표는 별도 선택 지표로 표시한다.
같은 가중치가 DEV대표와 최종에 함께 선택되면 두 endpoint를 별도 학습 seed나 독립 성공으로 세지 않는다.

| 단계 | SH | 정확 endpoint/선결 |
|---|---|---|
| Stage4dqWa | `run_P106B_Stage4dqWa_foundation_original_parent_eval.sh` | 불변 P090B, 학습0 |
| Stage4dqWb | `run_P106B_Stage4dqWb_foundation_native_parent_eval-hold.sh` | ⏸ bare full512 비용 예산 재산정으로 미실행 보류,별도64진단이 대체 완료는 아님 |
| Stage4dqWc | `run_P106B_Stage4dqWc_foundation_baseqa_final_eval.sh` | 원 P090B→QA640 최종4 |
| Stage4dqWd | `run_P106B_Stage4dqWd_foundation_baseqa_dev_eval.sh` | 같은 교육의 DEV CE 최소 대표, TEST 선택 아님 |
| Stage4dqWe | `run_P106B_Stage4dqWe_foundation_cptqa_final_eval.sh` | native2281→동일 QA640 최종4 |
| Stage4dqWf | `run_P106B_Stage4dqWf_foundation_cptqa_dev_eval.sh` | 같은 CPT후QA의 DEV CE 최소 대표 |
| Stage4drW | `run_P106B_Stage4drW_foundation_raw_pair_readback.sh` | 여섯 endpoint 모든 lane·실제 원형·대응 기사 CI 재검산 |

기존 E970세팔 평가는 이력 패키지 기술 대조이며, 위 원P090B±native→동일QA의 주대조와 분리한다.
평가당 약15분/여섯 개90분을 우선 예산으로 두되 실제 생성 길이에 따라 달라진다. GPU는 한 모델만 단독 실행한다.
09시 GPU중단·10시 보고/마감, 체크포인트쓰기/학습/교사호출0·보호 원천/원본변경/설치/다운로드/push0을 유지한다.
정적/CPU 선결 통과는 실제 평가·정답성·Falcon 수준 도달의 증거가 아니다.
이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 2026-10-17 조건부 입력 본문 LM 보조 — 기존 답 학습의 강도는 유지

### 1. 세 후보와 선택

원부모의 추가 native298.975M은 기초 언어학습량을, 같은 자연 QA의 입력 본문 예측 보조는 목표분포 적응/과적합을,
같은 문맥의 서로 다른 질문·답 조합 대비는 질문별 답 구분을 겨냥한다.
첫 경로는 이미 준비한 대응을 유지하고, 둘째를 새 별도 연구로 준비한다. 셋째는 TRAIN 교차 정답이 의미상 오답이라는 묶음 계약이 없으므로 이번 자동 본런에는 넣지 않는다.
단순 문자열이 다른 답을 무조건 오답으로 정하거나 옛 위치 헤드 실패를 같은 방법으로 재실행하지 않는다.

### 2. 1차 문헌과 적용 한계

[IM §3~4](https://arxiv.org/html/2405.14394v2)는 긴 입력/짧은 답과 적은 예제에서 입력 손실의 효용을 보고했지만6.7~13B 연구다.
[WIT §2~3](https://arxiv.org/html/2507.07817v2)는1~8B이며, 입력·답 가중치와 전체 분모까지 달라진다. 그 최적값/효과 크기를90M에 복사하지 않는다.
현재 설계는 논문 재현이 아니라 **답 CE의 기존 분모/기여를 보존한 입력 LM 목적 추가**라는 독립 응용이다.
원래 assistant-only 학습도 답 손실을 통해 입력 표현에 gradient를 흘린다. 새 방법을 ‘이제 입력을 읽게 함’이라고 설명하지 않는다.
문맥이 질문 앞에 있는 입력의 문맥 예측은 질문을 조건으로 하지 않으므로 query-conditioned retrieval을 직접 지도한다는 주장도 하지 않는다.
[질문 대비 원문 §2·5.2](https://aclanthology.org/2021.emnlp-main.584.pdf)은 MLE와 대비를 결합한 T5-large770M 연구이며 좋은 묶음이 없으면 이득이 없었다. 향후 별도 축이다.

### 3. 사전고정 실험

초기화는 불변 원 P090B SHA12E18658로 고정한다. 새 CE/KL 학생의 TEST 결과를 보고 부모/계수를 고르지 않는다.
새 namespace `p106b_night_prompt_v1_s1337`에서 두 팔 `prompt0`/`prompt01`을 같은 seed1337·새 optimizer로 시작한다.
기존 동결V2 자연8192/양뷰0·1/보존4096/native5.24M, 같은 순서·배치·micro8×accum16/seq1024/ckptON/compiledefault·4pass640을 유지한다.
Adam5e-5/Muon2e-4/WD0/clip1·anneal1·MTP/이진/사실 보조off·원래 양뷰 손실 계산 경로의 일관성 계수0도 유지한다.

`L = 기존 assistant CE(whole-update 평균) + 기존 native CE(별도 평균) + β×자연 QA 입력본문 CE(별도 whole-update 평균)`.
β만0/0.1로 바꾸며 양팔 모두 같은 입력 head 경로를 계산한다. 전체 input+answer 평균으로 바꿔 답 gradient를 문맥 길이만큼 희석하지 않는다.
추가 지도는 context/question의 실제 토큰에만 준다. ChatML·고정 지시 wrapper·PAD·assistant/EOT·replay의 과거 오답에는 추가 손실을 주지 않는다.
원본 canonical encoder의 ids/shifted assistant labels를 그대로 쓰고 offsets의 완전 포함으로 별도 shifted prompt labels를 만든다.
경계를 가로지르는 토큰은 제외 수를 공개하고, 무조건 첫 substring을 찾아 정답이나 질문이 반복된 위치를 오인하지 않도록 producer 위치를 재구성한다.
논문과 달리 위 정규화로 계수의 의미를 고정하며0.1은 이번 선등록값이지 최적값이 아니다.

### 4. GPU 전 검산과 조건부 개방

실제 동결 TRAIN8192×2뷰의 ids/assistant mask/추가 prompt 위치·분모·패딩·source/CODE/부모 SHA를 CPU로 전수 검산한다.
한영 Unicode/경계/shift/과거 assistant 보호·chunked FP32 CE값과 gradient·β0의 기존 답 gradient 일치 회귀를 요구한다.
작은 head만 checkpoint/chunk로 계산하고 fixed-width PAD를 학습하지 않는다. 두 팔 비용8은 체크포인트0으로 독립 실측한다.
그 비용과 아직 남은 CPT/동일QA/전량 평가·원답 판독을 모두 합쳐09시 전에 들어갈 때만 본640을 연다.
불충족이면 기존 실행을 줄이거나 승인 기한을 늘리지 않고 새 팔을 미실행으로 보존한다.
아직 구현하지 않은 SH를 현재 실행 가능한 이름으로 권고하지 않는다. 정확한 단계/SH는 구현 뒤 아래에 추가한다.

### 5. 판정·영향도

같은 봉인 기사512QA/3뷰·양뷰 모두정답/동일오답·cube 값 갱신·역할/정보복구/코드·공개1920/native32·256을 평가한다.
최종4pass를 주대조로 유지하고 DEV CE 최소 대표는 따로 보존한다. TEST는 epoch/계수 선택에 쓰지 않는다.
입력/native 손실만 낮아지고 실제 QA가 늘지 않으면 독해 개선은 미확인이다. 질문 재진술/문맥 복사·보존 손실이 늘면 그 교환비와 음성을 기록한다.
한 학습 seed의 사례 CI가 학습 재현성 분산이나 Falcon급 도달의 증거는 아니다. 기존 관측 문항은 이후 개발 코호트로 취급하며 새 독립 평가가 필요하다.
새 helper/driver/CPU회귀·정확SH/TSV·새HF/EVI/weight-only 최종·DEV대표 최대4개만 추가한다. 제품/default·옛동결CODE·원본·타WIP·09·보호 데이터·다운로드/push는 변경하지 않는다.
추가 약1.5GB weight 예산이며 실제 footprint를 기록한다. 09시 GPU중단·10시 승인 종료/정리 조건은 유지한다.
이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

준비한 정확한 단계는 다음과 같다. 각 본런은 두 비용·원래 파이프라인 잔여·평가까지09시 전 예산을 다시 검산한다.

| 단계 | SH | 범위 |
|---|---|---|
| Stage4ds0W | `run_P106B_Stage4ds0W_night_prompt_cpu.sh` | CPU17·실제 TRAIN8192/2뷰 mask·shift/기존 y 유지·분모·패딩·원부모 검산 |
| Stage4dsWa | `run_P106B_Stage4dsWa_night_prompt0_cost8.sh` | β0·동일 추가 head 경로8회·저장0 |
| Stage4dsWb | `run_P106B_Stage4dsWb_night_prompt01_cost8.sh` | β0.1·같은8회·저장0 |
| Stage4dtWa | `run_P106B_Stage4dtWa_night_prompt0_repeat4.sh` | 동일 원P090B·같은QA640·β0 기준선 |
| Stage4dtWb | `run_P106B_Stage4dtWb_night_prompt01_repeat4.sh` | 동일 조건640·β0.1·마지막4/DEV 대표 분리 |

개발 CPU17과 독립 반증검토를 통과했지만 실제 자료 mask/GPU/품질은 아직 미실행이다.
최종17시는 과거 승인이고 이번 hard stop은10/17 09시 GPU·10시 보고/마감이다.
전체 gradient clip1의 재척도 효과는 손실 혼합의 일부이므로 답 CE 분모 보존만으로 최종 답 gradient norm까지 같다고 주장하지 않는다.
보고서 파일 존재만으로 예산에서 완료를 차감하지 않으며 status/CODE/source/640·2281/실제 노출/CP SHA/모든 lane 원답·receipt 검산 뒤만 차감한다.

평가 adapter는 기존 학습 코드를 변경하지 않고 같은 입력을 참조한다. 이미 관찰된 이 코호트는 반복 개발 비교이며 새로운 독립 벤치로 부르지 않는다.

| 단계 | SH | 정확 endpoint/선결 |
|---|---|---|
| Stage4du0W | `run_P106B_Stage4du0W_night_prompt_eval_cpu.sh` | 같은 원형/CASE·학습CPU source를 새 evaluator에 CPU 연결 |
| Stage4duWa | `run_P106B_Stage4duWa_night_prompt0_final_eval.sh` | β0 최종4·8lane·모델불변 |
| Stage4duWb | `run_P106B_Stage4duWb_night_prompt01_final_eval.sh` | β0.1 최종4·같은 source/정밀도 |
| Stage4duWc | `run_P106B_Stage4duWc_night_prompt0_dev_eval.sh` | β0 DEV최소 대표·TEST선택 아님 |
| Stage4duWd | `run_P106B_Stage4duWd_night_prompt01_dev_eval.sh` | β0.1 DEV최소 대표 |
| Stage4dvW | `run_P106B_Stage4dvW_night_prompt_paired_readback.sh` | 네 endpoint 모두 원답/원형/이력/receipt/모델SHA 독립검산 |

실제 답·후행 판독·보존과 분리된 CPU21을 먼저 검산했으며 GPU/최종 품질은 아직 NOT_RUN이다.

## 2026-10-17 조건부 고유 QA 다양성 대조 — 같은640회에서8k반복 대신32k한번

### 1. 질문·후보

DEV가 이른 시점 뒤 악화하고 같은 오답이 늘어, 추가 업데이트만 늘리기 전에 고유 QA 범위를 분리한다.
세 후보는 기존8,192QA×4반복,16,384QA×2,32,768QA×1이다. 메모리 재고에서 마지막의 공급을 확인했으므로32k×1을 준비한다.
이것은 새 기사 도메인이나 새 세계지식의 확보가 아니라 같은 기사 집합 안 질문·문맥 범위 확대다.
부족분을 행 복제로 채우지 않는다. 새 모델 품질을 보고 규모를 골라 바꾸지 않는다.

### 2. 공급 선결과 고정 평가

기존 collector의 article90/5/5·공식DEV/중복/near-overlap/common_bpb제외·문맥당2QA·완전문맥+출력128/ctx1024를 유지한다.
train_limit만 언어당4,096→16,384로 바꾸는 메모리 검토에서32,768QA를 확보했다. 한국어8,405문맥/1,263기사, 영어10,502문맥/412기사다.
원4,096/언어는 새 선택의 전체 내용 기준 정확한 언어별 prefix다. DEV/TEST 각512의 전체 원형·순서·root SHA는 그대로다.
이 검토는 읽기전용/파일0/모델0/GPU0이며, 새 실제 원형/인코더·학습 선결은 별도 CPU 동결이 필요하다.

### 3. 대응 조건

불변 원 P090B SHA12E18658·새 optimizer/seed1337·micro8×accum16/seq1024/ckptON/compiledefault·Adam5e-5/Muon2e-4/WD0/clip1/anneal1을 유지한다.
두 wrapper0/1 CE·일관성계수0·MTP/이진/사실/입력본문 보조off·기존 replay4096×4와native5.24M은 바꾸지 않는다.
새 자연 QA를 언어별4,096씩 네 구간으로 나눠 네 논리 구간마다 서로 다른8,192QA를 한 번씩 읽는다.
첫 구간 전체8192는 기존 기준선의 첫 순회와 같아야 한다. 기존 seed+구간의 순서/배치·replay·native offsets도 같게 검산한다.
자연 CE는 양쪽 모두65,536행, 전체SFT81,920행/640회·padded slots83,886,080이다. 새 자료의 자연 epoch는1이며 ‘32k를4epoch’라고 부르지 않는다.

| 실제 노출 | 기존8k×4 | 새32k×1 |
|---|---:|---:|
| 자연 x | 16,450,696 | 16,650,200 |
| 자연 assistant target | 363,552 | 362,614 |
| 보존 포함 총SFT x | 19,559,956 | 19,759,460 |
| 보존 포함 assistant target | 514,632 | 513,694 |

행/업데이트는 같지만 실제 x/지도토큰은 정확히 같지 않다. 새 질문 내용·길이·노출빈도와 함께 바뀌는 자료 다양성 패키지 대조이며 순수한 토큰수 하나의 인과로 주장하지 않는다.
직접 이미 완료한 원 P090B→같은QA640을 기준으로 삼되 새 코드 경로/마스크·단계1소비를 먼저 대조한다. 모델을 반복 로드해 기준선을 재학습시키지 않는다.

### 4. 실행 조건·판정

새 namespace `p106b_night_diversity_v1_s1337`에20MB 이하 원형 조각·SHA/전수CPU·새 비용8/저장0을 먼저 준비한다.
구현된 단계만 정확SH로 등록하고, 비용과 남은 원래foundation/평가·조건부 보조·외부준거까지09시 전 예산을 확인한 뒤만 본640을 연다.
GPU는한모델단독·새최종/DEV최소대표 weight-only만 저장하며 원본/기존 CODE·캐시·보호자료/다운로드/push를 바꾸지 않는다.
고정 기사QA3형식·양뷰 모두정답/동일오답·조건갱신/보존·공개같은표본/native를 비교한다. 이미 본 코호트는 반복 개발 평가이며 TEST로 checkpoint/epoch를 고르지 않는다.
첫 구간과 같은 자료인지, 새 나머지 구간이 고유인지·평가로 섞이지 않는지를 source/ID/실제인코더로 검산한다.
계산 비용이 비슷해도 지능이 늘었다는 보장은 없다. 형식내 QA만 늘고 다른입력순서/보존이 실패하면 그 한계를 그대로 남긴다.
이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 2026-10-17 조건부 외부 준거 — 로컬 Falcon-H1-Tiny-90M-Base 오프라인 비교

### 1. 목적과 세 후보

목표 모델의 논문 점수를 TinyLM의 로컬 수치와 섞지 않기 위해 같은 고정 영어 선택 문항을 실제 비교한다.
후보는①기존 HF캐시/Transformers의 torch fallback으로 로컬 실측,②필수 커널을 새 설치해 최적 속도로 측정,③공식 수치만 인용이다.
현재 다운로드/설치 권한은 없으므로①만 비용 게이트로 준비한다. fallback이 불능·지나치게 느리면 정확한 이유와 NOT_RUN을 보존하고②를 우회 실행하지 않는다.

### 2. 자산·범위·공정성

자산은 기존 `HF/models--tiiuae--Falcon-H1-Tiny-90M-Base/snapshots/7994372e93b62822ae25f8bfb19f653649cea3a3/`만 읽는다.
새 namespace `p106b_night_falcon_v2_s1337`에 실제 CPU strict-load/전체 자산·원형·토크나이저SHA를 검산한다. 환경/라이브러리를 수정하거나 가중치를 쓰지 않는다.
프로세스 한정 `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `HF_DATASETS_OFFLINE=1`, `USE_HUB_KERNELS=0`으로 네트워크/Hub kernel 취득을 막는다.
설치된 Transformers의 내장 falcon_h1과 torch fallback만 사용하며 trust_remote_code는False다. CPU검사 뒤 GPU비용8을 먼저 잰다.

주비교는 기존 고정 PIQA/HellaSwag/ARC-easy 각256의 같은 원문·선택지·라벨·seq1024, 합CE 선택 및 문자길이 정규화다.
어휘가 달라 CE값은 모델간 비교하지 않고 정답수·같은 eligible ID·선택지 편향과 불확실성을 비교한다.
tokenizer가 임의 BOS를 붙이지 않도록 add_special_tokens=False의 실제 ids를 기록한다. config의 bos1은 >>ABSTRACT<<이며 이것만으로 자동 삽입 근거가 되지 않는다.
공식 lm-eval 전수/shot/BOS 규약 재현은 미확정이므로 ‘공식 점수 재현’이라 부르지 않는다.
추가 GSM8K64는 기존 ChatML과 같은 질문의 일반 `Question/Answer` 형식을 별도 보존해 Base모델의 형식 민감도를 확인한다. 서로 다른 프롬프트를 같은 수치로 섞지 않는다.
greedy/출력128·캐시ON·FP32 MATH로 실제 원답/종료사유·입력길이와 no-truncate를 보존한다. 영어 Base이므로 이번 주비교를 영어로 한정하며 한국어 능력 확인으로 승격하지 않는다.

### 3. 실제 비용·개방·판정

CPU가 각 MC가족의 중간/최장길이2개와 GSM 중간/최장2개를 결과 보기 전에 고른다. 비용8은 모델불변·저장0이며15분 상한이다.
측정한 가족별 보수 시간과 아직 남은 원래foundation·학생 보조·고유QA·전량평가를 함께 검토해09시 전 예산일 때만 전량을 연다.
전체 기준 예산45분을 넘으면 주대조를 축소해 성공으로 부르지 않고 NOT_RUN/부분만 기록한다. 원형·부분 raw는 보존한다.
Falcon은800B급 기초학습·다른 구조·실수 가중치/토크나이저를 가진 패키지다. Tiny의 삼진/자료량/아키텍처 하나의 인과 효과를 이 대조에서 식별하지 않는다.
Falcon과 선택지 우도가 비슷해도 자유 QA·한국어·배포40MiB·일반 지능 동등을 주장하지 않는다.
정확 SH/CPU회귀/계보·독립 원답 재집계는 구현 뒤 아래에 추가한다. 현재 모델 로딩/GPU/전량 결과는 모두 NOT_RUN이다.
이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

구현 단계는 `Stage4dw0W_night_falcon_cpu`(CPU11+실물 CPU strict), `Stage4dwWa_night_falcon_cost8`(최대900초), `Stage4dwWb_night_falcon_english896`(최대2700초)다.
각각의 정확 실행파일은 `run_P106B_`+해당 단계명+`.sh`이며 무입력·새 로그·오프라인 단독 실행이다.
전체 입력은 주 MC768와 별도 두 형식의 GSM128로896행이다. 전자는 같은 문항 우도 대조, 후자는 프롬프트 민감도 진단으로 분리한다.
새 driver의 HF리다이렉트 명시 import 누락1은 모델 실행 전 전수정적에서 검출해 수리했다. 실패 감사도 덮어쓰지 않고 보존한다.
행 사이 확인만으로 긴 생성의09시 초과를 막지 못하므로 프로세스 벽시간도09시 잔여·요청상한·비용900초 중 최솟값으로 제한한다.

첫 CPU시도는 로컬 가중치 strict 로딩과896원형 작성까지 했지만 설치된 라이브러리의 빈 set 진단값을 JSON으로 저장하는 단계에서 종료9가 났다.
이것은 GPU/모델 품질 음성이 아니다. v1원형/원로그를 그대로 두고 v2에 안정적인 list 진단값으로 수리하며 CPU회귀12와 `Stage4dw0Wb_night_falcon_cpu_json` 새 SH로 다시 검산한다.
수리 전 소스2개는 기록된 패치에서 재구성하고 v1 manifest의 원SHA와 모두 일치함을 검산해 별도 Git제외 위치에 보존했다. 원본 HF 디렉터리는 고치지 않았다.

고유QA 대조도 정확 SH 세 개를 준비했다. `run_P106B_Stage4dy0W_night_diversity_cpu.sh`는 CPU16+실제4원천/32k/quarter0인코더·부모 동결,
`run_P106B_Stage4dyWa_night_unique32k_cost8.sh`는 새 저장0 비용8, `run_P106B_Stage4dyWb_night_unique32k_train.sh`는 전체예산 안640회다.
논리구간은 학습내용이 다른 네 구간이며 자연자료 epoch는1이다. 평가 adapter/실제 답은 별도 준비하고 비용만으로 품질 판정을 열지 않는다.

## 2026-10-17 조건부 질문-앞 학습 대조 — 기존 봉인 형식은 학습하지 않음

### 1. 실제 관찰과 세 후보

지문·출력128이 모두1024에 들어가는 평가에서도 질문을 지문 앞에 둔 wrapper2의 정답이 거의 늘지 않았다.
후보는①같은0/1형식의 업데이트 증가,②같은32k에서 두 번째 학습 형식의 질문/지문 순서만 뒤집기,③문맥을2048 이상으로 확대하기다.
검증 손실이 이른 시점 뒤 악화했고 현재 입력 절단이 없으므로②를 조건부로 우선한다. 이것이 일반적인 장문 한계나 기억 부재를 해결하는 보증은 아니다.

### 2. 변경 범위와 봉인 경계

기존 collector·render_view·부모·source·32k 고유QA/기사분할·replay/native·평가512/3형식은 바꾸지 않는다.
특히 wrapper2는 계속 학습 금지다. train임을 dev로 위장하거나 기존 금지 검사를 완화하지 않는다.
새 독립 producer의 wrapper3만 만든다. wrapper1의 지시문·‘지문/질문’ 라벨·문맥·질문·정답은 그대로이고 질문 블록을 지문 앞에 옮긴다.
예: ‘지문에 근거해 답만 쓰세요 / 지문: A는 빨강 / 질문: A는?’ → ‘같은 지시 / 질문: A는? / 지문: A는 빨강’이다.
새3은 봉인2의 ‘자료만 이용해 간결하게 답’ 문구와 다르다. 0/3을 학습하며 예전0/1/2 평가를 그대로 읽는다.
첫 번째0은 그대로, 두 번째1만 새3으로 바꾼다. source질문·정답·문자 멀티셋·실제 target IDs 보존과 full-prompt+128 예산을 CPU 전수검산한다.
한 행이라도 길이/정답/출처가 깨지면 행을 조용히 버리지 않고 선결 미충족으로 남긴다.

### 3. 비교·비용·판정

새 namespace `p106b_night_order_v1_s1337`는 같은 원P090B·새optimizer/seed1337·micro8×accum16/1024/ckptON·Adam5e-5/Muon2e-4/WD0/clip1·640회다.
자연32k한번/네 논리구간·보존4096×4/native5.24M, 두뷰 CE/일관성0·입력본문/MTP/이진/사실 보조off는 고정한다.
직전 선등록32k 0/1 팔을 기준으로 비교한다. 실제 입력/지도 토큰이 같은지는 측정값으로 보고하며 순서 외 문자열이 바뀌면 같은조건이라 주장하지 않는다.
최종640 주대조와 DEV 최소 대표를 분리한다. 이미 본 평가 코호트는 반복 개발 평가이고 미학습3→봉인2의 이득도 일반 지능이나 독립 전수벤치로 승격하지 않는다.
두 질문 배치의 정답·일관오답·역할/정보복구/코드·공개/native와 실제 답안을 함께 본다. 특정 형식만 개선되면 그 한계와 교환비를 남긴다.
CPU실물/새 비용8·모든 원래파이프라인·Falcon준거·추가학습/평가가09시 이전일 때만 실제 실행한다. 불충족이면 준비만 보존한다.
새최종/DEV weight-only 약0.75GB를 더 쓸 수 있으며 원본/보호/다운로드/제품default/09는 바꾸지 않는다. 정확 SH는 구현 뒤 추가한다.
이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

구현/선결 단계는 다음과 같다. 각 이름의 정확 파일은 `run_P106B_`+단계명+`.sh`다.

| 단계 | 실제 범위 |
|---|---|
| Stage4eb0W_night_order_cpu | CPU12+실제32k의0/3 canonical·실제 shift/target·문자멀티셋·상한·원부모 검산 |
| Stage4ebWa_night_order_cost8 | 같은 원P090B8회·저장0 |
| Stage4ebWb_night_order_train640 | 원래 세 원답감사의14검산 항목(기준선2개 중복 포함,실제 endpoint명12개)·원형/receipt 완료 뒤만,추가90분예약/09시내640 |
| Stage4ec0W_night_order_eval_cpu | CPU4+같은 원형3형식/보존/공개 입력 연결 |
| Stage4ecWa_night_order_final_eval |0/3 최종640 주대조·8lane 실제 답·FP32 MATH |
| Stage4ecWb_night_order_dev_eval |같은 원래DEV0/1 최소 대표 별도,TEST선택 아님 |
| Stage4edW_night_order_paired_readback |동일32k 0/1 대0/3의 실제 원형/원답/receipt/모델SHA 재검산 |

독립 검토16의 처음에는 새 evaluator info()의 HF메타SHA읽기3회가 섞여 이를 보고했다. digest를모의값으로격리한후 새16회귀를검산했다.
실제 source CPU는02:56:06에완료했고 새0/3과원래0/1의x19,759,460/지도513,694가실제로같았다. 모델GPU/비용은아직미실행이다.
이CPU입력검산은 QA정답률·일반화를 증명하지 않는다.

외부 준거 reader도 `Stage4dx0W_night_reference_reader_cpu`(합성19+기존896원형/17Tiny endpoint 선언 동결),
`Stage4dxW_night_reference_common_readback`(전체Falcon원답/비용8과같은eligible ID 교집합별 독립집계)을 준비했다.
reader CPU는 모델을 로딩하지 않지만 원자산SHA를위해가중치파일바이트를읽는다. ‘가중치를안읽음’이아니라‘모델로딩/추론0’이다.
완성Tiny보고서없는팔은0점으로가정하지않고NOT_COMPLETE로남기며누락을숨기지않는다.선택지합NLL과문자정규화·GSM두프롬프트를분리한다.

## 2026-10-17 04시 평가 비용 실측 정정 — 교육 전 부모는 별도 균형 소형 진단

### 1. 관찰·예측 오류

교육 전 원P090B의 natural 원답은03:57경148행 중144행이 출력128을 모두 썼다. 파일 생성03:52:09부터의 약5분 실측으로 natural1536행만약50~60분이 예상된다.
이것은 생성 종료 분포의 차이이며 GPU 장애·정답률 음성의 판정이 아니다. 종전900초/endpoint 예산은 짧게 종료하는 교육된 E970 실측을 다른 부모에 옮긴 부정확한 예측이었다.

### 2. 세 대안과 현재 선택

①옛512질문/3뷰/128출력을 교육전 두부모에서도 계속하면 조건은 같지만 기본부모에만2시간 이상을 쓰며 새 학습/원답 회수를 밀 수 있다.
②두 교육전 부모만 source/root hash로 고정한 한영각32질문(64질문×3뷰)의 별도 진단으로 나누고, 실제 교육후 final/DEV 네 모델 및 본문/고유자료는기존512질문 전량을 유지한다.
③전체 모델의 출력 상한을32로 줄여 새 평가버전으로 재수행하면 시간은 줄지만 장답의 정답 가능성/완결률이 바뀌고 기존128 결과와 직접 섞을 수 없다.
현재 시간한정 주도적 승인에서는②를 선택한다. 이 선택은 정답성 문턱·골드·출력128·FP32/캐시를 완화하지 않는다.

### 3. 보존·새 비교 범위

원P090B의 옛 full512×3 시도는 비용상한 재계획을 위해 정상 인터럽트하고 raw/원로그를 그대로 둔다. 전량완료나 과학적 gate-negative로 승격하지 않는다.
교육전 추가native 부모의 옛 full512×3는미실행으로 남긴다. 옛6endpoint전량 readback은 선결미충족이므로 실행하지 않는다.
새 소형 부모진단은 정확도·개별 답을 보지 않고 언어별 source/root의고정 hash로 선택한다. 선택시드/전체원형index/CASE와모든gold를CPU로 동결한뒤만 실행한다.
교육된 모델의512원답 중 같은64질문 ID를 골라 대응 비교하며, 부모64와학생512의서로다른분모를직접차이로쓰지않는다.
학습후 네 trained endpoint의 전량8lane은 유지하고 별도 CPU reader에서원형/원답/receipt/모델SHA를검산한다. bare부모 미완료를0점이나DONE으로채우지않는다.

### 4. 영향·시간·명시 보류

기존 학습/마스크/optimizer·가중치·source CODE를수정하지않는다. 새 scope/namespace의진단·readback만추가한다.
동결된 학습 driver의 옛 예산표에는 미완료부모가계속표시되며 그것을새scope완료의증거로쓰지않는다. 실제 남은 GPU학습·새진단/전량평가 시간을별도로재계산한다.
기존6endpoint원답감사를 요구한 질문앞 추가 본640은선결미충족 상태를 유지한다. 이를속이거나gate를우회하지않고이번창에서는보류한다.
비용8과실제source가완료된 준비물은보존하고, 75M×4epoch목표·held2학습금지·원형/오답보존·09시GPU중단/10시보고는유지한다.
새 정확SH·source 동결과실행은별도단계/새출력으로기록한다. 현재미완료와부분실행을완료로바꾸지않는다.
이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.
### 5. 별도 소형 진단의 구현·실행 전 조건

- 새 경로는 `p106b_night_parent_panel_v1_s1337`이며, 기존 전량 평가의 source·raw·receipt를 수정하지 않는다. 질문·정답·출력 조건은 원형 그대로이고 source/root hash만으로 한영 각32개를 고른다. 기존512개에서 답을 잘한 항목을 고르는 것이 아니다.
- CPU 회귀는 선정 helper10개와 controller5개다. 실제 CPU 동결에서 원형64개·원래 영어 선택형768개·선정 index/SHA를 다시 묶는다. GPU/학습/체크포인트 쓰기는 없다.
- 교육 전 두 부모에서는64×3개의 실제 답, 영어 선택형768개의 합 NLL/문자 정규화, 같은 native32/256을 새로 측정한다. 교육 후 네 모델의 full512×3와 보존평가8lane은 그대로 둔다.
- 새 `trained_foundation_readback.json`은 교육된 네 모델만 검산한다. 별도 `bounded_parent_readback.json`은 학생 원답에서 같은64개 ID를 추출해 대응한다. 어느 파일도 옛 `foundation_readback.json`을 대체하거나 질문앞 본학습 선결을 해제하지 않는다.

| 단계 | 정확한 실행파일 | 범위·예상 |
|---|---|---|
| CPU | `run_P106B_Stage4dq0Wb_parent_panel_cpu.sh` | 15개 합성 회귀 후 실제 원형 동결, 모델 로딩 없음 |
| 부모1 | `run_P106B_Stage4dqWg_original_parent_panel.sh` | 원P090B의64질문×3뷰+영어MC768, 최대30분 |
| 부모2 | `run_P106B_Stage4dqWh_native_parent_panel.sh` | 추가native 부모의 같은 소형 원형, 최대30분 |
| 학습후4 검산 | `run_P106B_Stage4drWb_trained_foundation_readback.sh` | 네 full8lane 완료가 필수, CPU raw/receipt 검산 |
| 대응64 검산 | `run_P106B_Stage4drWc_parent_panel_readback.sh` | 부모2+학생4를 같은64개 ID로 비교 |

**실행 전 영향도·preflight:** 모델/학습 core 및 optimizer 변경0, 보호 원천/기존 가중치·로그 변경0, 새 진단·회귀4파일/SH5개와 해당 공유 연구문서만 추가한다. 새 태그 레지스트리 충돌0, 기존 부모 full512는 동일 비교가 아니므로 별도 보존한다. 개별 요청의128출력·1024문맥·FP32·greedy·cache 조건은 기존과 같다. 비교 분모가 다른 수치를 빼지 않고 같은64개 ID에서만 부모-학생 차이를 낸다. 당시 실측과 여유를 합산해 소형 두 부모 최대60분, 남은 trained3 평가 약20분, 본문 두 팔/고유32k 학습과6평가 약120~150분을 예약한다. 추정은 모델별 종료 분포에 따라 바뀌며09시 GPU 종료가 우선이다.
## 2026-10-17 예산 범위 복구 — 고유32k 비교의 과학 조건은 그대로 유지

### 관찰·세 대안

기존 고유32k driver는 본문보조 예산을 더한 뒤 Falcon45분과 새 평가30분을 늘 예약한다. 본문보조 예산도 이미 보류한 교육 전 부모 full512를 계속 예약한다.
따라서 이미 끝난 Falcon896과 새64 진단 범위를 반영하지 못해, 실제 수행 가능한 시간에도 오래된 총예산으로 중단할 수 있다. 기존 소스의 이 보수적 조건을 조용히 바꾸거나 완료파일을 가짜로 만들지 않는다.

| 안 | 처리 | 장점 | 한계·비용 |
|---|---|---|---|
| 1. 별도 예산 버전 | 원본 훈련 루프·원형을 보존한 새 namespace에서 실제 남은 예약만 계산 | 고유32k 대조를 유지하고 이전 원형/증거와 분리 | 새 CPU·비용8·루프 동등성 회귀가 필요 |
| 2. 기존 조건 유지 | 옛 예산이 안 맞으면32k 본학습 보류 | 코드 추가 없음 | 이미 끝난 작업의 가상 예약 때문에 실험 기회를 잃음 |
| 3. 기존 코드 직접 수리 | 같은 경로 예산만 바꾸기 | 구현량이 작음 | 동결 CODE/CPU/비용8의 동일성이 깨져 선택하지 않음 |

**현재 선택은1이다.** 시간한정 주도적 승인에서 준비하며, 정답률 문턱·학습/평가 내용은 바꾸지 않는다. 새 코드·실물 CPU·새 비용8이 검증되기 전에는 실제640을 열지 않는다.

### 영향 범위·동등성·중단

- 새 `p106b_night_diversity_scope_v2_s1337`만 쓴다. 기존 고유32k 원형은 읽기 전용으로 재검산하며 원본 CPU CODE·원형SHA·실제 courses/마스크/전체 분모가 같아야 한다.
- 원P090B,32k 고유질문/한 번 노출, 같은 replay/native, micro8×accum16·1024·ckpt-on,640회,LR/optimizer/손실 및DEV 선택을 유지한다. 소스의 핵심 학습 루프 동등성도 별도 회귀로 잠근다.
- 새 검증은 실제 비용8을 다시 측정한다. 재사용할 원형·동결 소스와 새 실행 소스를 각각 해시로 구별하며, 옛 비용을 새 CODE의 실제 성공으로 표시하지 않는다.
- 예약은 새 본학습·미완료 본문보조 학습·고정 full512 평가·부모64 진단·문서 예비시간을 포함한다. 단순 파일 존재가 아니라 검산된 완료만 비용에서 제외한다. 미완료 bare full512와 질문앞 본학습은 명시 보류이며 새 경로로 옛 선결을 완료 처리하지 않는다.
- 새로운 예산도 상한 보증이 아닌 예측이다. 실제 긴 생성·실패·시간부족이면 원답을 보존하고 중단한다.09시 GPU 종료/10시 보고를 우선한다.
- 외부 다운로드/설치·보호 원천·원본 가중치 수정·환경/공용검사기 변경0. 정확한 새 SH/소스 및 실제 수행은 다음 결과에 기록한다.
### 새 버전의 정확한 단계·현재 준비 상태

원형은 기존 고유32k 코퍼스를 그대로 읽는다. 새 four-file 실행판의 학습 핵심·저장·완료 함수와 원본이 AST/문자구간 해시까지 같아야 한다.
독립 리뷰가 평가파일 없는 경우 미완료 foundation 학습비용을 놓칠 수 있는 잠재 전제를 지적해, 평가 보고 유무와 관계없이 네 trained 체크포인트의 학습 완료 계약·실제 SHA를 먼저 검증하도록 닫았다. 실제 현재 네 학습/평가는 이미 완료했지만 코드도 그 선결을 강제한다.
합성 회귀는 학습/예산23+평가9=32개이며, 실제 원형·부모 CPU 확인과 새 비용8은 별도다. 기존 source CODE를 수리한 것이 아니다.

| 단계 | 정확한 SH | 여는 조건 |
|---|---|---|
| CPU | `run_P106B_Stage4dy0Wb_night_unique_scope_cpu.sh` | 순수32회귀 뒤 실제 원형/courses·부모/패딩 동결 |
| 평가 CPU | `run_P106B_Stage4dz0Wb_night_unique_scope_eval_cpu.sh` | 실제 source CPU 뒤 같은512질문/8lane을 결합 |
| 비용8 | `run_P106B_Stage4dyWc_night_unique_scope_cost8.sh` | 새 CODE/CPU에서8회만, 저장0 |
| 본640 | `run_P106B_Stage4dyWd_night_unique_scope_train640.sh` | 실제 새 비용8/기존4학습 완료·원답·잔여 예산 검증 |
| final 평가 | `run_P106B_Stage4dzWc_night_unique_scope_final_eval.sh` | 같은 고정512×3/보존·공개·native 전량 |
| DEV 대표 평가 | `run_P106B_Stage4dzWd_night_unique_scope_dev_eval.sh` | 같은 run의DEV 최소만 선택, TEST 선택 금지 |
| 대응 검산 | `run_P106B_Stage4eaWb_night_unique_scope_readback.sh` | 새2+기존 baseQA final/DEV의 원답·source·body·receipt 완결 |

**preflight:** 레지스트리 새 태그 충돌0, SH7개의 Bash구문/입력태그 검사0오류. 같은 부모·토크나이저·풀·스케줄·손실·업데이트·정답·출력예산 유지, 별도 예산/경로만 바뀐다.
실제 source가 기존19,759,460 SFT x/513,694 지도·5,242,880 native·83,886,080 padding과 일치해야 한다. 비용8의 실제 새 이벤트/SHA가 없으면 본학습을 열지 않는다.
기존 V1 본640/평가/검산은 별도 보류로 보존하며 새 버전의 성공으로 옛 파일을 완료 처리하지 않는다. 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.
## 2026-10-17 조건부 읽기 전용 원인분리 — 지시가 같은 view1 대 순서만 바꾼 view3

### 목적·세 대안과 현재 선택

기존 v2 평가의 view2는 지시 문구/라벨과 질문·근거 순서가 함께 바뀐다. 그 점수 감소를 순서 효과 하나로 해석할 수 없다.

| 안 | 수행 | 비용·한계 |
|---|---|---|
| 1. 기존0/1/2만 해석 | 새 실행 없이 기존 점수/원답을 읽음 | 비용0,순서와 문구 효과가 섞임 |
| 2. 같은 지시의1/3 대응 진단 | source해시로 이미 고정한64질문에서 블록 순서만 교환,같은 두 모델 읽기 전용 생성 | CPU/실행판 준비+추가GPU 약10~20분 예상,과제 범위의 순서 효과만 봄 |
| 3. 새 순서로 재학습 | 원래 준비한0/3 학습으로 개선을 시험 | 옛6전량 선결이 미충족이므로 이번 진단의 대안으로 우회 실행하지 않음 |

**현재 선택은2다.** 새 학습/헤드/목표함수는 도입하지 않는다. 기존 본문/고유32k 학습·전량 평가를 먼저 회수하며,09시까지 최소35분이 남는 경우에만 이 추가 진단을 연다.

### 설계·영향 범위

- 새 `p106b_night_order_probe_v1_s1337`, source64는 앞서 부모진단에 이미 동결한 KO32/EN32와 완전히 같다. probe 결과나 정오로 다시 선정하지 않는다.
- 비교는 **view1 대3**이다. 계획 구두 착수 때 언급한0/3는 기존 producer를 읽은 뒤 실물 동결 전에1/3으로 정정했다. view3는1의 동일 지시/Question·Passage 라벨·모든 문자/원형/aliases를 보존하고 Q/C 블록 순서만 바꾼다.
- 기존 TRAIN 전용 `p106b_night_order_data.render`에 TEST를 넣기 위해 split을 바꾸지 않는다. 새 순수 probe helper는 원래 TEST/메타를 그대로 두며 학습행을 만들지 않는다. held2도 학습하지 않는다.
- 대상은 사전지정한 `base_qa` final4와 새 `unique32k` final640 두 모델이다. DEV 또는 TEST 점수를 보고 모델을 교체하지 않는다. 각자의 full512/8lane 완료·원답·CP SHA를 검증한 후만 읽는다.
- 한 모델당64×2=128새 생성, 두 모델256응답이다. root별1→3/3→1 순서를 source index로 번갈아 배치한다. greedy/FP32 MATH/cacheON/출력128/1024문맥,학습0·checkpoint쓰기0.
- CPU에서 전체 prompt SHA·실제 tokenizer 길이·128생성 여유를 검산한다. 문자 동일성과 토큰화 경계의 길이는 별개이므로 실제 길이 차이도 남기며 입력을 자르지 않는다.
- view1도 새로 생성해 같은 호출 경로에서 비교한다. 기존 full512의 같은64 view1 원답과 재현 일치도를 별도로 남기고, 같은 답 일치를 정답성으로 세지 않는다.
- 언어별 EM/F1·같은 오답·정답→오답/오답→정답·상한/EOS/정지를 분리한다. 같은 alias 기반의 국소 평가이며 세계 정답성/모든 문맥 일반화·구조 결함의 증명이 아니다.
- 새 helper/회귀2파일·별도 controller/회귀2파일과 CPU/모델2/검산SH만 추가한다. 제품 core·기존 동결 source/data/가중치·공용검사기·보호 원천은 수정하지 않는다.

### 비용·해석·보류 조건

기존 고유32k forecast는 이 추가 진단을 포함하지 않았으므로 그 표를 전체 예산 보증으로 쓰지 않는다. 첫 실행 전 남은 모델수×900초+예비300초를 별도로 예약하고09시에 GPU를 멈춘다.
새 CPU/합성 회귀·실제 full평가 선결·시간이 부족하면 `NOT_RUN/HOLD`로 남긴다. 원형을 줄이거나 출력 상한을 낮춰 완료처럼 만들지 않는다.
1→3에서 하락하면 그 모델/프롬프트 범위의 입력 순서 민감성이다.1/3이 비슷하더라도 점수 바닥/작은 표본과 view2의 다른 지시·라벨 차이가 남으므로 ‘순서 문제 없음’이나 ‘문구만 원인’으로 단정하지 않는다.
이 진단은 옛 질문앞640·원6모델 gate를 열거나 자료/모델을 채택하는 절차가 아니다. 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

### 실행판·실행 전 점검

| 단계 | SH | 범위 |
|---|---|---|
| CPU 동결 | `run_P106B_Stage4ee0W_order_probe_cpu.sh` | 순수29회귀·기존64 원형·실제 토큰/스케줄, 모델 forward0 |
| 기존8k 최종 | `run_P106B_Stage4eeWa_baseqa_order_probe.sh` | 고정 baseQA final4,128응답,최대900초 |
| 고유32k 최종 | `run_P106B_Stage4eeWb_unique32k_order_probe.sh` | 고정 unique32k final640,같은128응답,최대900초 |
| 독립 검산 | `run_P106B_Stage4efW_order_probe_readback.sh` | 두 원답128행씩·원형·본체·실제 CP 경로·주평가 해시 |

독립 검토가 찾은 주평가 선결·보고 경로 누락은 CPU 동결 전에 수리했다.
두 모델의 full source뿐 아니라 prompt4/unique2의 **6개 주평가와 baseQA 전량**의 원답/receipt/CP/본체가 실제 완료돼야 새 진단을 열고 회수할 수 있다.
별도 실행판을 먼저 부른다고 남은 평가 예산을 소비할 수 없게 했으며, 저장 report의 CP 문자열만 변조해도 거부하는 합성 시험을 추가했다.
합성29개는 실제 원형·모델 검증과 구별한다. 새 태그 충돌0, 유사 registry에는 같은64의 지시고정1/3 읽기 전용 비교가 없고, Bash구문/SH 진입점82개 검사를 통과했다.
학습steps0·자료 풀/학습 LR 비교는 해당 없으며 부모/토크나이저/답 예산/precision은 각 source에 고정한다. 예상 allocator 메모리는 선행 FP32 모델 평가 수준이며 전역 peak 보증은 아니다.

## 2026-10-17 외부 준거의 새 범위 연결 — 원래17 라벨을 고치지 않는 CPU 검산

| 대안 | 효과·비용 | 판단 |
|---|---|---|
| 기존17 라벨만 사용 | 추가 코드0,새 unique scope와 부모64는 비교에 빠짐 | 범위가 불완전함을 그대로 남길 수 있으나 이번 새 팔의 상대 위치가 안 보임 |
| 별도 읽기 전용 확장 | CPU 회귀/동결/새 검산 SH,추가 모델 호출0 | **채택.** 원래17의 미완료를 보존하고 새 범위4라벨만 더 연결 |
| 기존 evaluator/providers 변경 | 파일은 적지만 이미 동결한 CODE/CPU와 불일치 | 기각,기존 증거를 새 소스의 성공으로 바꾸지 않음 |

새 `p106b_night_reference_extension_v1_s1337`은 source/코드로 고정한 새 unique final/DEV 두 라벨과 bare parent64 두 라벨을 포함한다.
모든 영어 MC는 기존 원형768(3과제256씩) 중 각 모델이 실제로 건너뛰지 않은 같은 ID/질문/후보/정답 교집합만 비교한다.
natural64/512·토크나이저 간 CE·학습 예산을 혼합하지 않고,최종/DEV가 같은 CP이면 별도 모델/seed로 세지 않는다.
실제 source/원답/receipt/본체/CP와 원래 Falcon896 재검산을 선결로 두며,신규 logits/생성/학습/다운로드는0이다.
공식 harness 동등성·전사전학습 오염 검증·여러 학습 seed는 미확인이고,새 범위 추가가 원래 full512 부모/질문앞 gate의 완료는 아니다.
CPU 동결은 주평가 전에 할 수 있지만 실제 회수는 원래17 비교기·새 unique 두 전량·별도 부모64 두 팔 완료 후만 수행한다.

| 단계 | SH | 선결·범위 |
|---|---|---|
| CPU 동결 | `run_P106B_Stage4eg0W_reference_extension_cpu.sh` | 순수 회귀·실제 이미 동결한 source/code·추가4라벨,모델0 |
| 원답 검산 | `run_P106B_Stage4egW_reference_extension_readback.sh` | 기존17/새2전량/부모64둘 검산 뒤,실제 같은 MC ID만 집계 |

새 태그 충돌0,출력은 새 write-once 경로다. 같은 공개 원형을 쓰는 후행 분석으로 새 학습 조건/자료를 제안하는 gate가 아니며 CPU 숫자도 모델 품질을 미리 보장하지 않는다.

## 2026-10-17 후속 후보 — 추가 원문과 고유질문의 결합, 현재는 DESIGNED

현재 최종640의 조건표에서 원P090B→8k 반복,추가원문→같은8k 반복,원P090B→고유32k 한 번은 수행했다.
빈 네 번째 셀은 **이미 완료된 native298.975M의 최종 가중치에서 고유32k를 한 번640회** 학습하는 것이다. 새 native298.975M을 다시 학습하거나 QA까지 끝난 CPTQA 모델에서 시작하는 것이 아니다.

| 대안 | 영향·비용 | 현재 결정 |
|---|---|---|
| 독립 CPT32 실행판/회귀 | 기존32k source/courses/손실/640을 그대로 잠그고 초기화만 native로 교체. 구현/검증 약45~90분은 소스 검토 추정,미실측 | 구현 후보로 보존 |
| 기존 동결 driver에 부모 인자 추가 | 공용화에는 유리하지만 기존 CODE/CPU와 불일치 | 이번 증거에는 적용하지 않음 |
| 현재3셀의 실제 답을 먼저 회수 | 추가 학습비0,결합효과는 미확인 | **현재 우선순위.** 주평가·부모64·순서진단을 우선하며 이번에는 새 학습 코드를 아직 만들지 않음 |

source-only 독립 검토는 다음 선결을 특정했다.

- 새 부모는 `diag_p106b_night_foundation.load_foundation_parent('cpt_qa')`가 읽는 native 최종이어야 하며,`checkpoint('cpt_qa')`의 QA완료 가중치와 구별한다.
- 기존32k CPU의 `source_initial_core_sha256`(원P090B)와 새 실제 `initial_core_sha256`(native)을 분리한다. 원본 CPU 초기화 값을 덮어쓰지 않는다.
- native의 실제2281회/298,975,232입력/원형/전체 이벤트/OOM0/CP 경로·SHA·본체와 기존 CPT→8k의 initializer가 같음을 검산해야 한다.
- GPU 학습 핵심·optimizer·마스크·전체640스케줄·native 순서는 AST/문자 동등하게 잠그되,부모 로드와 initializer 저장 인자의 허용 차이만 명시한다. 전체 함수가 불변이라고 주장하지 않는다.
- 새 namespace/CPU·같은 새 부모의 비용8과 원점 재초기화가 필요하다. 기존 scope의 `budget_only_revision=True`나 파일 존재만으로 완료를 판단하는 예산을 복사하지 않는다.
- 본640·최종/DEV 전량 평가·모든 미완료 우선작업·문서예비를 포함한 **새 전체 예산**이09시 전에 들어와야 실행할 수 있다. 현재 CPU/비용8/모델은 NOT_RUN이다.

후속 해석은 같은 고정 질문에서 `(CPT32−CPT8)−(base32−base8)`의 탐색적 조리법 상호작용이다.
8k반복/32k한번의 실제 x·target 차이,단일 학습 seed·반복 관측한 개발 코호트라는 한계를 유지하며,이 설계만으로 복합 기법의 지능 향상이나 본75M 완성을 예고하지 않는다.

## 2026-10-17 후행 CPU 진단 — 같은 본문의 서로 다른 질문을 구별했는가

| 안 | 비용·판별 범위 | 결정 |
|---|---|---|
| 기존 고정8만 판독 | 추가0,실패 사례는 보지만 전체 질문묶음 분포는 모름 | 작은 표본 설명으로만 유지 |
| 원형으로 묶음을 정한 후 기존 원답 전수 재집계 | 새 helper/순수회귀/CPU source 동결·읽기 전용 검산,새GPU/교사0 | **채택** |
| 즉시 질문대조 손실 재학습 | 추가 코드/양팔 학습·별칭 오탐 검토 필요 | 현재 진단과 분리,아직 구현하지 않음 |

새 `p106b_night_question_bundles_v1_s1337`에서 이미 동결한 같은 TEST512를 언어/원천/기사/문맥 ID·정확한 원문 SHA로 그룹화한다.
기존 수집기의 문맥 ID는 NFKC/공백/casefold 정규화 본문으로 만들어지므로, 같은 ID의 유효 원형 차이를 거부하지 않되 정확한 원문이 다르면 같은 입력 묶음으로 합치지 않는다. 정규화 본문 자체가 다른 ID 충돌은 계속 거부한다.
정확히 두 질문이 있는 그룹의 질문·alias와 원래 문자 span을 검산해,문자상 같은 답·포함/중첩 가능성·서로 다른 답 후보를 나눠 기록한다.
이것은 **문자상 구별 후보**이지 교차 답이 반드시 의미상 오답이라는 판정이나 자동 재생성·학습 제외가 아니다.
같은 본문의 양질문 모두 정답·한쪽만 정답·출력만 바뀜·같은 오답을 언어/표현별로 따로 센다. 자연질문이 달라진 관측이지 아키텍처의 순수 인과 개입이라고 부르지 않는다.

같은 source의 foundation4/본문4/고유2의 사전고정10라벨 전량 원답을 대상으로 하며,같은 고유 최종/DEV 가중치는 독립 모델로 세지 않는다.
64부모와512학생을 섞지 않고 과거 미완료 endpoint를0으로 넣지 않는다. source/전체 원답·본체·실제 가중치·receipt 선결을 검산하고 요약 지표만 새 경로에 보존한다.
추가로 이미 동결된 고유32k TRAIN도 원형만 같은 규칙으로 재고해 후속 질문대조 후보가 얼마나 있는지 계측한다. TEST를 TRAIN으로 바꾸거나 이 결과의 오답을 다음 학습에 투입하지 않는다.
선정에는 실제 모델답을 쓰지 않으며 source와 규칙을 CPU에서 먼저 동결한다. 중복별칭/부분중첩·질문모호성·주석 누락은 후행 의미검토가 필요하다.
V1 실물 source freeze는 전체 bundle을 단일 JSON에 저장하려다20MB 보호선으로 **파일 생성 전 종료9**였다. 합성26 통과와 실물 동결 실패를 분리한다.
복구는 새 `p106b_night_question_bundles_v2_s1337`/Stage4eh0Wb·ehWb에서 기존 write-once ShardWriter를 사용한다. bundle 전체는 ignored HF의 각20,000,000바이트 이하 JSONL, Git에는 alias/원문 없는 summary·manifest 해시만 남기며 원형/그룹/10라벨은 바꾸지 않는다.
전체 재조립 SHA·원문 차이·0묶음·임시 shard 변조 회귀를 더해 합성31과 실물 CPU를 먼저 수행하고 모든10개 전량 원답의 검산을 통과한 뒤만 관측 수치를 기록한다. 과거 실패 원답/코드/SH는 새 결과로 덮지 않는다.
V2 실물 source 재고는 완료했으나 후속 reader가 설명 문자열 storage와 실제 저장목록 storage의 이름 충돌로 원답 읽기 전 종료9였다. CODE/source를 고치지 않고 새 `p106b_night_question_bundles_v3_s1337`/Stage4eh0Wc·ehWc에서 설명은storage_policy로 분리한다. 합성34에는 준비→읽기 전체 연결을 추가하며 동일source/묶음/10라벨을 보존한다. V2의 실물 source 성공과 reader 실패를 각각 기록한다.

## 2026-10-17 읽기 전용 추가 진단 — 같은 답의 질문조건부 우도

새 태그 `p106b_night_question_scores_v1_s1337`. 기존 질문묶음V3가 source로 정한 문자상구별 TEST110(KO69/EN41) 전체를 그대로 사용한다. 이후 답을 보고 일부만 고르지 않는다. 모델은 사전고정 baseQA final4와 고유32k final640 두 개다. 과거 두모델의8lane·가중치·전체 source/원답 검산과 질문묶음V3 reader 완료가 선결이며 옛6전량 gate를 대체하지 않는다.

| 안 | 변경·판별 범위 | 이번 결정 |
|---|---|---|
| 두질문 free 답만 다시읽기 | 기존답으로 가능하나 정답 후보에 대한 내부점수를 모름 | §260의 관측으로 보존 |
| 같은두모델의2질문×2답 우도 검산 | 새 logits만 읽으며 학습/가중치저장0. 질문조건의 상대 점수와 실제 생성의 차이 관찰 | **채택**, CPU→비용2묶음→전체를09시예산 안에서만 수행 |
| 즉시 대조손실 재학습 | CE대조팔·TRAIN 의미검토·새 학습비 필요 | 다음 연구로 분리,현재 구현/실행하지 않음 |

view0만 사용하고 본문·질문·관리지시는 기존 실제prompt와 같다. 각묶음에서 원래 첫별칭 a1/a2를 각 q1/q2 아래 teacher forcing으로 점수화한다. assistant 내용만 점수합/평균·첫token값을 기록하고 EOT포함값은 별도 기록한다. prompt/header/pad는지도점수에서제외하며 같은답의 target token벡터가 두질문에서정확히같아야한다. 완전한입력이1024를넘으면자르지않고거부한다.

같은답 a1의 `logP(a1|c,q1)-logP(a1|c,q2)`와반대방향 a2의차이를함께본다. 양수가원래주석질문쪽의우도를뜻하지만 교차답이항상의미상오답이라는인증은아니다. 합/평균·첫token·실제view0 자유답정답을분리한다. 답길이가다른 a1/a2의점수를단순비교해품질판정하지않는다. 같은답prefix를teacher forcing하므로이는자유생성성공/세계정답성/구조인과증명이아니다.

FP32/SDPA MATH·cache 없는완전prefill·grad없음·MTP없음이다. 같은가중치파일/로드본체의전후SHA를검산한다. 새CPU는인코더의shift/내용/EOT/동일답target·두질문매핑·집계누락/중복·준비/읽기연결을검증하고실제source/토크나이저를먼저동결한다.
비용2묶음은고정source의한영각1개만읽고전체모델을새로로드해본진단을시작한다. 둘의남은전체예산+예정GPU+문서예비가09시를넘으면전체를NOT_RUN으로남긴다. 각모델전체상한600초·현재09시절대종료,교사호출/optimizer/체크포인트쓰기/다운로드0이다.
개별source/alias/token점수는ignored local의20MB이하샤드,Git에는요약·해시·분모만남긴다. 연구규칙은이미관측한source 코호트에대한후행탐색이며최종독립TEST로승격하지않는다.

## 2026-10-17 최종 공통 경로 회귀 — 새 격리 출력의 전체44팔

야간 공용 검사 수리 이후 최종 회귀는 같은 canonical smoke action 목록을 유지한 Codex 어댑터로 수행한다. 모델/학습/진단 팔의 argv·순서·대기·분모를 바꾸지 않고,금지된 레거시 인계 검사기와 field-log의 격리 경로만 기존 승인 방식대로 두 군데 대체한다. 원본환경의HF/cache/runs/checkpoint를덮는공용wrapper직접호출이나마지막부분팔만확인하는안과비교해,새격리namespace의전량재확인을선택했다.

새 `p106b_night_final_smoke_v1_s1337`는원래validation_v1/밤새산출물을덮지않는다. Stage4ek0W의합성64(질문묶음34+우도25+새smoke계약5)와canonical실제모듈CPU판독후Stage4ekW에서전체를실행한다. 동적실험성공은모든실제팔/실패팔/exit0오류표지/계측결과를분리해검산한후만기록하고,원래synthetic파일의전후SHA도보존한다.

시작은08:30이전만허용하며09시GPU종료를위한30분여유를둔다. 이는공용코드/환경변경이아니라동일진입점의새관측이며75M/모델품질/Codex새세션E2E증거로승격하지않는다. 로그20MB상한·원형불변·offline/W&B미전송을유지한다.

## 2026-10-17 마지막 CPU 검산 — 미래 답 후보가 첫 로짓에 보이지 않는가

| 안 | 범위·비용 | 결정 |
|---|---|---|
| 소스의 causal mask만 읽기 | 모델 실행0,실제 수치 정합성은 미확인 | 보조 근거 |
| 같은 실제 가중치의 CPU prefix/완전입력 대조 | 기존 source 고정4묶음·두 모델,최대600초,학습/저장/GPU0 | **채택** |
| GPU에서110묶음 재측정 | 전량 비교 가능하나 이미 종료한 GPU 범위가 다시 열림 | 이번에는 수행하지 않음 |

새 `p106b_night_causal_readback_v1_s1337`/Stage4elW는 질문묶음V3의 기존 해시선정 한영각2개를 계승하며 모델답을 보고 다시 고르지 않는다. 각 질문의 두 답 후보에서 첫 내용 토큰을 예측하는 shifted 위치까지의 입력이 실제 answer-free ChatML 생성 prompt와 같은지 먼저 검산한다. 같은 두 가중치를 CPU FP32/MATH로 읽고 prefix-only 로짓과 미래 답을 포함한 완전입력의 해당 로짓·prefix hidden을 비교한다. 숫자 허용오차를 임의로 만들어 PASS를 선언하지 않고 최대 절대차·정확일치·argmax와 해시를 기록한다. 질문만 바꾼 prefix 로짓 변화도 양성 대조로 남긴다.

실제 체크포인트와 로드 본체 전후 SHA, CUDA 미초기화, 20MB 이하 새 요약 출력만 보존한다. 첫 토큰의 질문 신호에 미래 답이 섞였는지에 대한 표본 진단이지 정답성·보편적 인과성·학습 개선의 증명은 아니다. 새 학습토큰/teacher/optimizer0이며 기존 토크나이저·source·가중치는 바꾸지 않는다. 태그 충돌0을 확인했다. 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 2026-10-17 마감 정적 복구 — 모델과 실행 원형은 불변

첫 전수 감사는66PASS/2ERROR/6NOT_RUN이었다. 호출 인자 검사는 내부 compact(value,limit)·pairs(rows,encoded)를 다른 파일의 새 전역 함수로 잘못 결합했고,스모크 판독기는 첫 승인 실행만 알아 새 최종 namespace를 거부했다. 이를 실제 모델/44팔 실패로 혼동하지 않는다.

| 안 | 영향·비용 | 결정 |
|---|---|---|
| 검사기의 실제 함수 범위와 정확한 승인 실행 profile 수리 | 공용 두 판독기·좁은 AST/문서 fixture 회귀,모델/환경/GPU0 | 기존 공용검사·회귀 수정 승인 안에서 채택 |
| 이미 동결한 함수/모델 driver 개명 | 기존 EVI의 CODE와 달라져 과거 실물 검증 손상 | 기각 |
| 오류 면제/숫자만 수정 | 실제 회귀 없이 성공 표시 | 기각 |

Stage4emW는 합성30과 실제 저장 smoke/호출 인자 검사를 CPU로 기록한다. 실제 local 함수 arity/키워드 오류는 계속 거부하고,단지 무관한 전역 함수의 시그니처를 쓰지 않는다. 두 승인 smoke의 정확 schema/tag/driver/log·실행순서·전체receipt/SHA·원합성불변을 모두 확인하며 임의 namespace/잘못된 profile/원형변조는 계속 거부한다. 모델 소스/가중치·기존 원답/원로그·동결 code는 수정하지 않는다. 자료/토큰/학습 LR 비교는 해당 없고 새 모델 런이 아니다.

독립검토후import/global/nonlocal과동일경계중복회귀를보완해Stage4emW30→Stage4emWb34→Stage4emWc36을각각새원로그로회수했다. 모든실제kwargs/저장smoke 판독도0이며중간본은최종수정의증거로승격하지않는다. 최종 원장 마감은 새 전수 감사 오류0·기존87+새CPU3의90raw closure·새 C2/C3·인계 검산 뒤에만 수행한다. 이전66/2/6 감사 파일은 덮어쓰거나 삭제하지 않고 새 복구 감사를 만든다.

## 2026-10-17 사용자 임의질문·메뉴 보완 회수

[결과101 §271](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)의 사용자7응답은 종료표지와 내용 성공이 다름을 확인했다. 6개 다른 질문/7응답을 그대로 보존하고 GPT가 직접 새모델을 실행한 것으로 바꾸지 않는다. 저장된 같은 prompt01의 source-order8답도 이번에 새로 판독해 수/대상/대비관계 오류를 확인했다. 전량 자동검산·일부 직접판독·임의질문 모델 실행은 별도 증거다.

기존 interactive_infer/catalog의 번호/명칭 선택을 재사용하고 night 이름·선택후 저장cfg/tokenizer SHA·ChatML/EOT/FP32·실제token경계·명시이력·비대화형거부와 interactive_infer.sh를 보완했다. 모델/학습/GPU를 실행하지 않고 CPU 합성/목록/도움말/셸·정적만 검증한다. 이는 실험용배치가 아닌 직접입력도구라 experiments.tsv에는 등록하지 않는다. 수정 후 사용자 모델 E2E는 NOT_RUN이다.

사용자 선택은 앞 세후속 중 A(질문·답 관계 CE/조건부대조) 우선이다. 이번은 UI/판독 정정이며 A의 새학습/손실 구현은 수행하지 않는다. 기존75M×4 목표·연구상태/기본모델 채택은 바꾸지 않는다.

## 2026-10-17 CPU 전용 준비 — 검증된 관계쌍의 같은 질문 안 답 선택

### 1. 왜

사용자는 다음 우선순위 A를 선택했고 오늘23:59까지 CPU 준비만 허용했다. [결과101 §265~271](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)의 ‘맞는 질문에서 같은 답의 우도가 더 높음’과 실제 정답 생성은 다르다. 사용자 임의질문도 기본 산수/설명/대상 조회를 실패했다. 작은 관계 과제 성공을 이 모든 능력 회복으로 확대하지 않는다.

### 2. 질문

| 질문 | 직접 대조 |
|---|---|
| 같은 질문에서 정답이 다른 관계의 답보다 높게 나오게 학습하면 실제 대상 혼동이 줄어드는가? | 같은 양성자료의 CE 대 CE+행별 답 우도 대조 |
| 단순 정답 유형/앞에 나온 이름/특정 이름을 배운 것 아닌가? | PERSON↔PERSON 두 답, 값 배정·사실/질문 순서의 무작위화, 별도 사실 묶음과 미학습 질문 표현/역순 평가 |
| 좁은 과제 개선이 자연 QA/언어능력을 훼손하는가? | 기존 자연 QA와 보존자료는 양팔 동일, 실제 답/일반 언어 손실/사용자 사례 회귀 별도 |

### 3. 예측 — 실행 전

행별 대조는 질문 하나의 정답/오답 우도 차이를 직접 겨냥하므로 후보 순위 개선 가능성이 있다. 그러나 짧은 코드 관계표 암기·이름/위치 지름길·부족한 사전학습·자유 생성의 높은 경쟁답 우도 때문에 자연 QA와 산수/설명은 여전히 실패할 가능성이 크다. 평균 우도 개선도 최초 분기 토큰이나 실제 생성의 개선을 보장하지 않는다. 대조계수0.1·온도1·마진0은 새 실험의 탐색값이지 최적값/기본값/약한 규제라는 확정이 아니다.

### 4. 단계 설계 — CPU 계약 → 실제 비용 → 동일 노출 두 팔 → 원답 평가

새 tag는 `p106b_relation_bind_v1_s1337`, 단계는 기존 마감 회귀 Stage4em과 구별한 Stage4en 계열이다. 기존 frozen night 코드는 수정하지 않는다.

| 단계 | 내용 | 선결·판정 | 실행 권한 |
|---|---|---|---|
| Stage4en0W | 코드 사실표·한영2048/DEV128/TEST128 관계묶음, 실제 chat32 마스크/2×2/prefix·원자료/분모 검산 | **완료** [101 §272](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md): CPU81·동결·재소비0. 모델/GPU 아님 | 이번 CPU 준비 |
| Stage4enWa/Wb 완료 | CE/대조 각각8업데이트 비용 | [101 §274](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md): 같은 code/corpus/초기화·노출/무OOM·allocator와예산확인 | 19일 총괄이 최신 위임으로 실제 완료 |
| Stage4enWc/Wd 완료 | CE/대조 각각4pass·768업데이트 | CE01:46~02:19/대조02:26~02:59 종료0·실제노출동일·각weight-only1,실제답별도 | 20일17시까지 사용자 위임 범위 |
| Stage4enWe 완료 | 부모/두 학생의 후보 없는 실제 첫 답·우도·자연 QA·기초 canary·원문 손실 대조 | 성공 학습의 정확 code/corpus/부모/가중치SHA와 원답 receipt | 03:04~03:35 각990답완료·관계일부개선/일반QA실패([101 §282](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)) |
| Stage4enWf 완료 | 원답·후보 우도·실물 가중치/본체/학습 보고/manifest를 결합한 CPU 재검산 | 세 평가 완결·같은 입력과 원형, 누락/다른 팔 복사 거부 | 03:37~03:38 원형/분모/본체재집계errors0·자동채택없음 |

각 팔은 원P090B dense14 chat32 부모·같은 tokenizer·micro8 양성행×accum16·seq1024·checkpoint-on·compile default·seed1337·새 optimizer·constant Adam5e-5/Muon2e-4/RMS4/WD0/clip1을 유지한다. 기존 자연 QA8192묶음의 두 올바른 표현(16384행)과 replay4096행을 그대로 유지하고 관계2048묶음의 두 올바른 답(4096행)을 추가한다. 총24576 양성행/pass,192업데이트/pass,4pass768회다. 원문8192 targets/update는 별도 평균 손실이며 최종6291456 targets를 처리한다. 이전640회보다20% 늘어 옛결과와 단일축 인과비교하지 않는다.

준비 중 독립 코드 검토에서 옛 helper가 행렬만 WD0으로 바꾸고 embedding AdamW에는 기본WD0.1을 남길 수 있음을 확인했다. 새 컨트롤러는 **모든 실제 그룹**을 WD0으로 명시하고 LR/WD/계수 수 receipt를 저장한다. 이 차이도 옛640회와의 직접비교를 막는 추가 이유다. 현재 CPU 장난감44계수 fixture는 그 라우팅 가능성을 재현했지만 과거 실물 optimizer를 다시 띄워 모든 옛 실행을 계측한 것은 아니다. 과거 모델 실패의 단독 원인이라고 주장하지 않는다.

관계 micro마다 양성8행과 교차 후보8행을 **별도 micro8 forward 두 번** 계산한다. 양팔 모두 같은 교차 경로를 계산하고 대조계수만0/0.1로 바꾼다. 정답 CE의 유효배치는128 양성행이며 교차 후보는 추가 계산이지 추가 정답/고유 지식이 아니다. 4pass의 교차 후보16384행·16777216 padded slots는 별도로 기록한다. 동시 모델/교사·새 추론 헤드·MTP는 없다.

`s[i,j]`는 질문i 아래 후보j의 내용토큰 평균 log-prob이다. `L=correct_CE_sum/whole_update_correct_targets + lambda*sum(softplus(s[i,other]-s[i,i]))/whole_update_relation_questions`다. EOT는 정답CE에 포함하고 대조에서는 제외한다. 자연 QA 두 표현에 서로 다른 관계답용 대조나 KL을 잘못 적용하지 않는다. 관계가 없는 update는 대조질량0이며 분모0을 안전하게 처리한다. 원문CE는 별도8192 분모로 더한다.

자연 TRAIN 12854 문자구별 후보는 의미 오답 인증이 없어 이번 대조에 자동 투입하지 않는다. 양성/교차답의 사실표·조회 관계·거부 근거와 생산자 버전을 보존한다. 같은 지문은 한영·질문·어순 변형 전체가 하나의 split에만 속한다. 코드 생성 가상 사실의 정확성은 현실 지식 인증과 다르다.

첫 pilot은 두 답의 **실제 내용 BPE 길이도 같은 묶음만** 사전 선별한다. 정답/교차답에서 같은 token-prefix를 공통으로 벌하는 길이 차이 교락을 줄이기 위한 제한이며 답문자만 비교해 의미를 판정하는 것이 아니다. 2048/128/128 한영 묶음은 독립 사실 배정1024/64/64개의 번역 두 개씩이다. 이름24개와 관계4종은 split 간 공통이므로 새 이름·관계 전이는 아니다. view2는 역할 단어를 유지한 질문 틀 전이이고 view1은 사실 줄 역순이다.

### 5. 판정 기준

CPU 성공은 자료·마스크·행/열 반례·기울기/분모·불변/누락 방지의 기술 계약에만 해당한다. 실제 비용은 양팔 cost8의 첫 compile/이후7회·전체 wall·peak/범위를 기록하며 외삽은 상한보장이 아니다. 학습 채택은 자동으로 하지 않는다. 실제 모델에서는 언어별 ‘두 질문 모두 첫 답 정답’과 미학습 표현/사실 역순 전이, 자연 QA, 일반 언어 손실을 따로 보고한다. 후보 순위/열별 질문 우위/종료표지는 보조 지표이며 품질 PASS를 대체하지 못한다. 단일seed·새 SFT 단계의 자료분할만 확인하며 원P090B 사전학습 노출 전체에 대한 미오염을 주장하지 않는다.

### 6. 비용

CPU 구현/회귀/자료 검산은 이번 범위다. GPU는 cost8 두 팔 전 실제 미계측이다. 예전640 QA의 약24~30분을 단순 비례하면768회는 약29~36분/팔이지만 교차 forward/새 길이/compile 때문에 더 걸릴 수 있다. 계획치는 팔당1시간·평가1시간의 예약값이며 새 cost8 뒤 실제 예상시간이 사용자 지정 예산 안에 들어갈 때만 본실험을 연다. VRAM/무OOM/속도와 λ의 실제 gradient 비율은 미확인이다.

### 7. 실행

CPU 회귀와 자료 검산 뒤 아래 개별 런처를 사용한다. 중간 입력 대기·effort 선택·전수 사람 승인·의미 오류 문자열 검사는 넣지 않는다. CPU 준비 외 런처 직접 실행은 사용자 몫이다.

| 순서 | 실제 파일 | 선결 |
|---|---|---|
| 0 완료 | `run_P106B_Stage4en0W_relation_bind_cpu-done.sh` | CPU81·자료동결 완료. 새 입력 검산은 preflight로 읽기만 하며 원형 덮어쓰기 금지 |
| 1 | `run_P106B_Stage4enWa_relation_ce_cost8.sh` | CPU 계약/같은코드·사용자 새 스모크 |
| 2 | `run_P106B_Stage4enWb_relation_contrast_cost8.sh` | 같은 CPU 계약·단독 GPU |
| 3 | `run_P106B_Stage4enWc_relation_ce_train768.sh` | 양쪽 cost8와 총4시간 외삽 문턱 |
| 4 | `run_P106B_Stage4enWd_relation_contrast_train768.sh` | 같은 두 비용·같은 원부모 새 optimizer |
| 5 | `run_P106B_Stage4enWe_relation_actual_answers.sh` | 두 실제 학습 완료 |
| 6 | `run_P106B_Stage4enWf_relation_raw_readback.sh` | 부모/양학생 실제 원답·manifest 완결 |

각 런처는 기존 `p106b_stage_receipt.pipeline`의 회귀→선결→본동작→최종판정을 재사용하는 독립 adapter를 호출한다. 공용 runlog/queue/receipt 구현은 바꾸지 않으며 stdin은 DEVNULL이다. 선결 미실행8·실제OOM8·도구오류9·중단130을 구별한다. 종료0은 단계 실행 완료이지 학생 품질 승인/전체75M 완료가 아니다.

### 8. 한계

가상 관계표는 광범위 지식/산수/자유 한국어를 대신하지 않는다. 자연 QA의 판독 기준과 코드 관계의 보수적 exact를 섞지 않는다. 두 팔이 같아도 과거640회와의 효과는 자료/계산량이 교락한다. 행별 우도 학습은 자유 답의 성공이나 Falcon 수준 도달을 보장하지 않는다. 반사실로 실제 관계 배정까지 바꾸는 학습, 실제 copy 분포, CPT→고유32k 결합은 별도 후보이며 이번에 혼합하지 않는다. 75M×4 본목표를 축소·완료로 바꾸지 않는다.

### 9. 실행 이력 / 갱신

2026-10-17 20:45~20:46 CPU81/자료 동결과 별도 CPU 재소비를 완료했다([결과101 §272](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). 실제 모델/학습가중치 로딩·GPU·학습·새 체크포인트·전체 스모크는 NOT_RUN이다. 실물 모델 효과의 예측은 아직 검증하지 않았고 CPU 성공으로 맞았다고 표시하지 않는다. 각 예정 팔은 비패딩 양성20,929,980·assistant564,048·별도 원문6,291,456이며 padded100,663,296을 실제 학습토큰으로 부르지 않는다. 7개 런처 중 CPU1개만 실행해 -done으로 보존했고 삭제/Git 변경은 하지 않았다.

#### 2026-10-19 실제 실행 위임 시작 — v1 조건은 불변

위 17일 기록은 당시 미실행 역사다. 현재 사용자는 처음19일17시, 이후 **20일17시 KST까지 CPU+GPU 주도 실험·문서·한국어 로컬커밋·완료런처 정리**를 위임했다. 기존 v1의 원래 두 cost8·양팔4시간 외삽 게이트와 동일 학습·평가 조건은 그대로 유지한다. 더 긴 허가가 무조건 더 긴 학습이나 계수 변경을 뜻하지 않는다.

전수 codex-safe68PASS/오류0/NOT_RUN6 뒤, 기존 합성 원형 보존을 위해 `scripts/p106b_relation_smoke.py`의 별도 TINYLM_DIR에서 canonical106action을 실행한다. 학습/진단 팔의 인자·순서는 그대로이고 타 환경 인계 검사와 고정 계측 로그 경로만 Codex 검사/새 합성 경로로 연결한다. 기존 공용 SH를 무수정 실행했다고 주장하지 않는다. 새 어댑터 합성5통과이며 첫 전수의 신규 contract 플래그1건 누락은 화이트리스트 등록 후 새 전수로 복구했다. 공용 검사기나 모델 코어는 수정하지 않았다.

Stage4en0Wa의 독립 CPU5와01:18~01:25 실제 격리 스모크44팔은 종료0·실패0·exit0오류표지0·계측0으로 완료했다([결과101 §273](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). GPU 비용8 두 팔을 다음으로 연다. 모델 품질·두 새 학습·실제 답은 이 시점 NOT_RUN이다. 보조의 합성 gradient/분모 검산과 원문·반사실 자료 가설은 실물 성공을 대신하지 않으며 추가 구현/학습은 기존 A 결과 뒤 별도 단계로 판단한다.

운영 지문은 `handoff/audit/WIP_20261019_RUNTIME_LOCK.json`, 권한·영향은 `handoff/audit/WIP_20261019_SCOPE.md`, 정·반·문헌 합은 `handoff/audit/WIP_20261019_AGENT_SYNTHESIS.md`에 보존했다. report의 grad_max는 clip 전 전체 gradient L2 norm 최대이며 다른 계열의 원소별 abs-max와 직접 비교하지 않는다.

두 비용8은01:30~01:32/01:38~01:40 종료0·같은노출·무CP였다. 원래 max(warm7) 외삽과평가예약은2.53h로4h안이다. CE768은01:46~02:19 실제완료했고[101 §275](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에 CP/실제 분모/DEV·native를 기록했다. 대조768은02:26부터 실행 중이다. 새44팔을공용판독기가인식하지못한1ERROR는실제학습실패와구별해보존했고별도수리승인전공용코드는변경하지않는다. 독립44명령/32JSON 검산은완료했다. CPU준비/두비용 SH는3ac5cce에원형/명령을선보존후삭제했으며현재재실행대상이아니다. 기존API완료만있는u1W-done은보존한다.

## 2026-10-19 조건부 후속 Stage4eo — 같은 질문의 문맥 역할값 교환 평가

### 1. 왜

Stage4en의 손실/후보 점수만으로 문맥을 실제로 읽었다고 말할 수 없다. 같은 가상 기록/질문/이름집합을 유지하고 물은 두 역할의 값을 바꾸는 개입으로,기존 답을 고수하는지 새 기록에 맞게 답하는지를 분리한다. 근거는 [DisentQA §2.2~3.4](https://aclanthology.org/2023.acl-long.559.pdf)의 문맥 정답 치환 아이디어다. 원형의 T5-770M/11B·이중답 학습 재현이 아니라 현재 TinyLM/코드 사실표에 한정한 로컬 평가다.

### 2. 질문

| 질문 | 직접 관측 |
|---|---|
| 질문과 이름은 같은데 기록의 역할값이 바뀌면 정답도 바뀌는가? | 원답 view0와 교환문 첫답의 양쪽 정답 |
| 답이 바뀌기만 하거나 기존 오답이 반복된 것은 아닌가? | 원문/교환문 각각 정답·양문맥 모두 정답·기존답 고수/종료 분리 |
| 두 역할을 둘 다 바르게 연결했는가? | 원래/교환 각2질문,4답 모두 정답인64 parent-graph/언어 |

### 3. 예측 — 실행 전

정말 역할을 읽는 학생이라면 질문이 같아도 새 기록을 따라야 한다. 그러나 기존 이름/배치나 출현 위치에 의존하면 이전 답을 유지하거나 임의의 다른 이름을 낼 수 있다. 원문 성적이 낮을 때 교환 실패만으로 원인을 확정할 수 없으며,양문맥 모두 정답을 함께 봐야 한다. 현재 generator도 이미 배정/순서를 무작위화하므로 질문-only 지름길이 주원인이라고 단정하지 않는다.

### 4. 단계 설계

새 태그는 `p106b_relation_cf_eval_v1_s1337`이다. registry에서 기존 실행 충돌0을 확인했다. 기존 v1 코드/자료/학습/현재 GPU 경로는 수정하지 않는다.

| 단계 | 범위 | 선결·판정 | 상태 |
|---|---|---|---|
| Stage4eo0W 완료 | 합성 CPU44·실제 tokenizer/source의 파생256case 동결 | 두 fact sentence만 치환·질문/다른주어/순서/생성prefix 불변·고유조회·TRAIN/원TEST 순환충돌0 | 02:31~02:32 종료0·모델0·[101 §276](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md) |
| Stage4eoWa/Wb/Wc 완료 | 같은 부모/CE/대조에 추가256첫답씩 | 원래 A 세990답+RAW_READBACK_COMPLETE·같은code/corpus/CP/본체·A실측에 따른 시간예약 | 03:43~04:03 각256답실행종료0·영어일부개선/한국어한계·새학습0([101 §284](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)) |
| Stage4eoWd 완료 | 기존 원답과 새256답/모델 대응 검산 | 정확 case·manifest·label/source/본체·원답 결손/위조 없음 | 04:04~04:05 실물CPU재집계errors0·자동채택없음 |

가상 TEST128 한영묶음(원래 parent graph64개)마다 두 질문을 유지한다. queried subject의 역할0/1 값만 서로 교환하고 다른 주어의 사실과 줄 순서는 유지한다. 문자열 전체의 사람 이름을 바꾸지 않고,코드가 만든 정확한 두 사실문장만 한 번씩 치환한다. 원래 bundle을 변조해 v1 validate를 우회하지 않는다. 파생 schema는 parent bundle SHA·새 fact graph SHA·새 case SHA를 나누고 원TEST split을 상속하며,파생 전체 graph가 기존 TRAIN/원TEST와 겹치거나 다른 부모가 같은 교환 graph로 수렴하면 거부한다. 공통 이름/관계/일부edge 한계는 유지한다.

canonical은 지원된 최소 messages/감독-turn만 사용하고 새 source_transform enum을 강제로 추가하지 않는다. 감독용 정답을 토큰 경계 검산에 쓸 수 있지만 실제 generate에는 user만 전달한다. FP32-MATH·greedy·KV·EOT·최대128·새 추론 head/MTP 없음은 원 A와 같다. teacher/optimizer/학습/새 checkpoint는0이다.

### 5. 판정 기준

구조 CPU 통과는 모델 효과가 아니다. 원문 view0를 다시 생성하지 않고 동일 checkpoint의 이미 저장된256답을 정확한 ID로 재사용한다. 새256답은 별도 분모로 보고,양쪽정답/4답모두정답/정답변화에도이전답고수/종료를 언어별로 나눈다. 번역/두 질문/두 문맥을 독립 표본으로 부풀리지 않으며 parent graph64개를 묶는다. 단일 학습 seed·반복 관측 fixture의 탐색 결과이고 자동 채택이나 범용 지능 판정은 하지 않는다.

### 6. 비용

CPU는 source/실제 tokenizer 동결과 합성 회귀이며 모델 로딩0이다. GPU는 모델당256추가응답·최대32768생성토큰이고3모델 최대98304토큰이다. 새 학습은 없다. 실제 A의990답 처리시간을 확인해 비례 예약과 모델 load 여유를 붙이고 총1시간을 우선 예약하되 미실측 추정임을 표시한다. 모델별 상한3600초/새 단계 시작 전 최신20일17시 및 문서 마감 예비를 총괄이 확인한다. 현재 학습과 동시 GPU 실행은 하지 않는다.

### 7. 실행

새 독립 driver/test와 기존 단계 receipt를 재사용한 entry/test 총4파일을 실물 CPU 동결 전에 완성했다. CPU44·직접 진입·check-only·bash-n을 확인했고 아래5개 SH를 준비했다. 원 A가 끝난 후에만 GPU 선결을 연다. 입력 대기·전수 사람 승인·잘못된 문구 목록 검사를 추가하지 않는다.

| 순서 | 실제 SH | 동작 |
|---|---|---|
| 완료 | `run_P106B_Stage4eo0W_counterfactual_cpu-done.sh` | CPU44와 실제256건 동결,재실행 금지 |
| 1 | `run_P106B_Stage4eoWa_cf_parent.sh` | 부모256추가 첫답 |
| 2 | `run_P106B_Stage4eoWb_cf_ce.sh` | CE256추가 첫답 |
| 3 | `run_P106B_Stage4eoWc_cf_contrast.sh` | 대조256추가 첫답 |
| 4 | `run_P106B_Stage4eoWd_cf_readback.sh` | 세 모델의 원문/교환문 대응 원형 검산 |

### 8. 한계

정확한 문맥 교환에 따라 답을 바꾸는 것이 일반 세계지식·산수·새 이름/관계·자유 한국어의 충분조건은 아니다. 원래 문맥 성적이 나쁘면 교환문 성적만으로 질문 무시/기억편향/구현원인을 특정할 수 없다. 반사실 평가를 새 학습/정답재교정으로 부르지 않는다. 새로운 자료 정책의 학습 대조나 값 없는 문맥·추가 head는 별도 설계다.

### 9. 실행 이력 / 갱신

2026-10-19 CPU 설계·충돌 확인/F4 뒤02:31~02:32 회귀44·실제 파생256건/64한영그래프를 동결했다. 실제 최대 prompt88·출력예산128·교사/학습/가중치저장/CUDA0이다. 전체 정적은 알려진 새 smoke profile 미등록1ERROR 외67PASS/6NOT_RUN이며공용수리승인대기다. 모델/GPU/품질 판정은 아직 NOT_RUN이다. 현재 실제 CE768/진행 중 대조768과 A 원답 회수의 독립성을 유지한다.

## 2026-10-19 후속 Stage4ep — 완료 원문 부모에서 고유32k를 한 번 학습

### 1. 왜

17일의 DESIGNED 빈 네 번째 셀을 구체화한다. 현재 새 관계 CE/대조와 값교환은 질문 연결의 작은 원인분리다. 별도로 이미 완료한 native298.975M의 기초학습과 고유32k 질문 다양화가 함께 작용하는지는 아직 측정하지 않았다. 새 native나 교사 생성 없이 기존 두 원형을 재사용하므로 추가 GPU 약1시간의 정보 대비 비용이 좋다. 새 태그는 `p106b_cpt_unique32k_v1_s1337`이고 기존 frozen 코드/자료/모델은 바꾸지 않는다.

### 2. 질문과 대안

| 안 | 정확한 범위·장단점 | 현재 판단 |
|---|---|---|
| 완료 native→고유32k | 기초학습/고유질문의 빈 조합,기존640/평가를 그대로 검산할 수 있음. 이전8k/32k 노출 차이·단일seed는 남음 | **독립 CPU/비용 준비**,현재 A/CF 결과 회수 뒤 순차 실행 |
| 문맥값 교환을 새 학습자료 정책으로 추가 | 관계를 읽는 연습을 직접 바꾸지만 두 새 학습과 자료/마스크 선결 필요 | 현재 A/CF 실제답을 본 뒤 변경축 확정 |
| 새 native 약299M 대1B | 같은 새 풀에서 양만 비교하면 기초학습량 가설을 직접 가름. 계산보다 합법·비보호 TRAIN≥2.000159B 공급이 선결 | 현재 공급 미확인/다운로드 미승인으로 HOLD |

### 3. 예측 — 실행 전

native와 고유질문은 각각 국소 이득만 있었다. 결합에서 학습형식의 정답은 더 늘 수 있으나 역할/정보부족 판별·미학습 질문/어순·일반 한국어가 함께 나아진다고 보장할 수 없다. 원문 CE나 DEV CE만 더 낮아지면 자유답 개선 가설의 확증이 아니다. `(CPT32−CPT8)−(base32−base8)`은 단일seed/관측 개발코호트의 **조리법 상호작용**이지 기초학습량만의 독립 인과 추정이 아니다.

### 4. 단계 설계

| 단계 | 범위 | 선결·관측 |
|---|---|---|
| Stage4ep0W 오류→0Wb/0Wc 완료 | 독립 실행판/회귀·실제 CPU 부모/source/courses 동결·평가 입력 별도 결합 | 첫0W는실동작전1로보존·0Wb03:06~03:08/0Wc03:09~03:12 CPU54·source/strict native/전체8영역입력검산종료0([101 §279](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)) |
| Stage4epWa | 같은 native에서 새 비용8 | 모델 새 로드/optimizer 새 생성·무CP/finite·노출·actual LR/WD/메모리/시간 |
| Stage4epWb | 같은 native에서 원점 시작640회 | 비용8의 새 전체예산 충족·기존32k와 science core 동등성·A/CF GPU 미경합 |
| Stage4epWc/Wd | final640 및 DEV 최저 대표의 동일8영역 실제 평가 | 같은원형·FP32 생성·기존 과제별계측·최종/DEV 분리·학생 이전답을 사용하는 실제멀티턴 |
| Stage4epWe | 4조합의 원답/manifest/source/본체 대응 판독 | 모든 필요실행 완결·기존 세 셀의 적합한 동일출력만 비교·누락을0으로 대체 금지 |

부모는 `diag_p106b_night_foundation.load_foundation_parent('cpt_qa')`가 읽는 **native 최종** SHA `D6ECF7127A719A08ED396B39A51285DD9F20568880F21049DF56149E01A53A11`/본체 `16CBDEC379D9DAB4193B22DF41241AC1746ADEE94C03F4491B2D5E3AC39CC640`다. QA까지 학습한 `cpt_qa` 최종에서 시작하지 않는다. source CPU의 원P090B initial `E854AB4E…`와 새 실제 initializer를 별도 필드로 보존한다. strict CPU 로드/현재 SHA와 실제 model fingerprint가 맞아야 한다.

기존 `diag_p106b_night_diversity_scope_v2.py`의 고유32k courses/순서/원문 창/양성 CE/EOT·마스크/보존자료/640 update·micro8×accum16·seq1024·ckpt-on·compile-default·seed1337·LR/clip/optimizer를 유지한다. embedding WD0.1이 남는 옛 조리법을 여기서 조용히0으로 고치지 않으며 실제 그룹 receipt를 남긴다. 초기화·새 경로/계보·명시 종료시각·운영 예산의 허용 차이만 구간 AST/문자 검산으로 분리한다. 옛 deadline/budget_only_revision의 무조건 계승이나 전역 monkeypatch로 frozen 코드를 우회하지 않는다.

고유32k 한 번·보존4096의4분기에서 원본 실제 SFT x19,759,460/assistant513,694·native5,242,880·positive padded83,886,080을 각각 유지한다. 한영 질문수16,384/16,384는 같지만 자연QA x는KO9,492,326/EN7,157,874(57.01/42.99%),assistant는148,306/214,308(40.90/59.10%)다. 이를한영50:50토큰학습으로보고하지않는다. 원문 cache이름으로언어비를인증하지않는다.

### 5. 판정 기준

CPU/비용 성공과 모델의 자유답·정보판별/멀티턴·일반 언어 손실을 분리한다. final640은 primary이고 DEV 대표는 같은 DEV CE의 사전규칙으로만 고르며 TEST를 보고 epoch를 선택하지 않는다. 기존 base8/CPT8/base32와 같은 원질문·gold·생성/종료·평가 분모를 대조하고 기사 단위 대응 구간은 학습seed 변동을 대신하지 않는다. 자동 모델 채택/보편 지능/Falcon 동등 선언은 하지 않는다.

### 6. 비용과 종료

기존 native 실제2,281회/298,975,232target는드라이버5597.685초였으나 이번에는다시학습하지않는다. 기존32k SFT는드라이버25.34분/SH30.2분,최종/DEV평가각약7.2/7.3분이었다. CPU45~90분은구현검토의추정이고실물CPU시간은별도기록한다. cost8+640+최종/DEV/원형검산을GPU50~70분으로우선예약하되새cost8과남은시간으로다시확인한다. 각실행wall과20일17시KST절대허가종료/최소1시간마감예비중더엄격한조건을적용한다. 긴허가를이유로중복실험을채우지않는다.

### 7. 실행·보존

독립train/eval/entry와시험6파일·SH를작성했다. 모든단계는회귀→선결→동작→최종판정의기존receipt를재사용하고stdin대기0이다. 새namespace만write-once로쓰며공개원문/source·기존보고/CP는변경하지않는다. raw/row는20MB미만샤드,작은해시/요약은Git,CP·상세원형은로컬보존한다. 새로운download/보호TinyDataset/교사모델호출은없다.

| 순서 | 실제SH | 선결 |
|---|---|---|
| 실패기록보존 | `run_P106B_Stage4ep0W_cpt_unique32k_cpu-done.sh` | [101 §278](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md),원형/명령선보존뒤삭제검토 |
| 1 | `run_P106B_Stage4ep0Wb_cpt_unique32k_cpu_recovery.sh` | CPU54·새parent/source동결 |
| 2 | `run_P106B_Stage4ep0Wc_cpt_unique32k_eval_freeze.sh` | 같은코드의CPU동결완료·기존완전평가입력 |
| 3 | `run_P106B_Stage4epWa_cpt_unique32k_cost8.sh` | 1/2완료·단독GPU·현재권한 |
| 4 | `run_P106B_Stage4epWb_cpt_unique32k_train640.sh` | 새실제cost8와마감/평가예비충족 |
| 5 | `run_P106B_Stage4epWc_cpt_unique32k_final_eval.sh` | 새640완료·최종weight-only/입력해시 |
| 6 | `run_P106B_Stage4epWd_cpt_unique32k_dev_eval.sh` | 같은완료보고의사전규칙DEV대표 |
| 7 | `run_P106B_Stage4epWe_cpt_unique32k_readback.sh` | 기존3셀/새셀의final·DEV48+16영역원형완결 |

### 8. 한계와 문헌

Falcon공식[90M Base 모델카드](https://huggingface.co/tiiuae/Falcon-H1-Tiny-90M-Base)와[Tiny 기술문서의Training/Base 절](https://tiiuae-tiny-h1-blogpost.hf.space/)은영어·hybrid구조·800B학습을설명한다. 이는현재모델의토큰규모와다르지만구조/언어/자료/최적화도다르므로현재실패를학습량하나로단정하지않는다. Base의SFT비율과별도Instruct의SFT-pretraining혼합도구별한다. 본실험은그800B재현이나학습목표전환이아니며고유75M SFT×4의미완을유지한다.

### 9. 이력

2026-10-19총괄이3경로의비용/공급/정보가치를보고하고,기존DESIGNED빈셀의독립준비를선택했다. 권한/F4는현재scope에명시했다. 첫0W는4단계adapter를공용3단계로검증하지못한구현오류로실동작전종료1로보존했다. 복구CPU54/실제source·native부모/8영역입력동결은03:08/03:12각완료했다. 원A/CF와새CPT6파일은불변이며04:13비용8종료0·warm7 median2.166초/실제native16CB/전체조리법동일/noCP를확인해04:13:44본640을시작했다([101 §285](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). 본완료/새실답효능은아직미판정이다. 소스/원로그/완료SH는한국어commit ce8c401에선보존한뒤완료런처를정리했다.

04:43:00 실제640완료/새weight-only1·DEV최저4=final동일파일,04:44:13최종8영역평가를시작했다([101 §288](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). 고유QA32k는한번/두표현이고4quarter를4epoch로표현하지않는다. oldembeddingWD0.1·원문32 BF16·새일반답/원형미판정을그대로구별한다.

05:06:45까지 Stage4epWc/Wd/We 최종·DEV 8영역과 네 조합 원형을 완료했다([101 §290](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). 예측했던 국소 QA 이득은 기본view 한국어36/256·영어33/256으로 일부 관측했으나 새view4/256·6/256, 조건갱신/산수 실패 때문에 일반화 기대는 충족하지 못했다. 기존 unique32k 대비 기본view의 paired 기사구간은 양언어 모두0을 포함한다. final=DEV는 같은 모델이며 8k/32k의 양·반복·배분 차이를 순수 고유량 효과로 부르지 않는다. 실제 학생20답도 별도로 읽었고 원점수/원형은 유지했다. 추가 교육은 완료가 아니라 새 대상×관계 세팔의 비용 게이트 뒤에만 시작한다.

## 2026-10-19 Stage4eq — 주석 QA 전체 공급의 CPU 재고

### 1. 왜

새과제75M부족은교사만으로기한내해소되지않는다. 이미주석Q/A가있는고정원천의길이내실가용량은아직전량미계측이다. 자료를임의증식하거나현재29M교육으로본목표를축소하지않고실제원천상한부터확인한다.

### 2. 질문·세 경로

| 경로 | 비용·교환비 | 현재 선택 |
|---|---|---|
| 기존KorQuAD/SQuAD의CPU전량정규화계수 | 모델/GPU0,예전CPU재고14.4분·75M구축103.3분은참고값일뿐이번미실측 | 우선준비·현재질문관계평가와병행가능 |
| 교사연속생성 | 최근3.51~6.26train x/s로40시간약0.5~0.9M의단순외삽,부족45.7M미해소 | 현재계약의생산성개선을별도검토 |
| 새복사/연결head | 특정출력경로개선가능성이있지만공급량을늘리지않고추론/캐시/학습선결추가 | 현재A/CF실답뒤판단 |

### 3. 예측

32k보다더많은질문이남을수있으나최대길이/문맥당상한·중복·분할조건을통과한추가량은미확인이다. 입력토큰이늘어도단답assistant지도밀도는낮을수있다. 동일본문질문/두wrapper를새지식량으로부풀리지않으며75M확보예측은하지않는다.

### 4. 단계

새tag `p106b_public_qa_supply_v1_s1337`와새CPU단계Stage4eq0W(회귀)/eqW(실물계수)를사용한다. 기존원source와정규화/인코더만읽고별도함수에서TRAIN모집의갯수제한을풀어**문맥당2질문**의현재상한을전량계수한다. 비교용cap4는가상대안으로만계수하며새학습에연결하지않는다. officialDEV·common-bpb·whole-clean-split예약·기사90/5/5·질문/문맥exact/near격리·전체1024/출력128·원주석span일치는유지한다. 옛엄격정량수집함수를monkeypatch하거나예외중간출력으로성공을대체하지않는다.

### 5. 판정

실제문자/별칭주석·토크나이저·x/y/마스크·root/기사/질문중복·source32k포함관계를CPU로검산한다. 언어별질문/문맥/기사·단일view와두view노출·assistant/EOT토큰·제외사유를따로보고한다. 코드는모델의정답성/권리/의미품질을판정하지않는다. 기존29M와의교차원천중복/75M quota통합은미계측으로남기며합산금지다.

### 6. 비용

CPU2스레드·전체상한3600초·RAM관측/단위표시,모델/교사/GPU/학습0이다. 실제소요는전량토큰화후기록한다. GPUcost/속도시험과는동시실행하지않고20일17시최종허가와문서예비를유지한다.

### 7. 실행·산출물

독립driver/test와CPU SH를준비중이다. 원주석원문은새Git자료로복사하지않는다. 작은보고는public EVI,상세root/계수20MB미만샤드는ignored local에저장하고기존data/HF/캐시를덮지않는다. stdin/다운로드/비보호가아닌원천확장은없다.

### 8. 한계

같은본문의추가질문은다른세계를가르친것이아니며현재자연QA도원P090B사전학습노출전체의미오염을보장하지않는다. 기존Dolly의student_training_allowed=false나새원천권리HOLD를해제하지않는다. unanswerable은주석제외수만재고하고재질문정답을자동작성하지않는다. 75M×4·한영50:50·가족/task구성을줄이지않는다.

### 9. 이력

2026-10-19총괄이문헌담당의공급/지도밀도재고와3경로를보고한뒤CPU준비를선택했다. 원천미접근순수20회귀/실제3단계연결·신규태그/SH/큐선결을통과했고04:14:16 Stage4eqW의전체재고를시작했다. 최종량/75M통합은미판정이며완료한A/CF와진행중CPT32코드/모델을변경하지않는다. 이전본문의eq0W는구문회귀구간이며실제실행SH `run_P106B_Stage4eqW_public_qa_supply_cpu.sh`의표준3단계안에서회귀20을함께수행한다.

Stage4eqW는04:24:36 CPU계수완료0·원형보존이다. 후행직접check는같은source tuple이JSON에서array가된것을다르다고보고9를냈다. 동결원2파일/보고/샤드를바꾸지않고별도reader/test2파일로wire형비교만수리한다. 독립Stage4eqWa `run_P106B_Stage4eqWa_public_qa_supply_readback.sh`는순수8회귀·허용수정문자/AST동등·원형/ID/마스크정량/원sourceSHA/봉인평가동일성을다시검산한다. 기존원문Q/A·모델·정책변경0이며최종량의75M통합/권리/의미정답성은승격하지않는다.

04:37:24 독립reader 실물재집계errors0으로완료했다([101 §286](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). 현재cap2 고유44,995질문/단일view11.010Mx·가상cap4 85,905질문/21.177Mx이며같은QA두표현은고유지식두배가아니다. 기존29M와의중복/75M의언어·과제·가족통합은미측정으로유지하며cap4정책은채택하지않았다. 두SH는done·명령보존상태이고원형선커밋전삭제하지않는다.

## 2026-10-19 Stage4er — 같은 역할의 다른 대상도 음성에 포함한다

### 1. 왜

완결A의CE v0오답은EN51/128·KO56/128이모두**다른대상의같은역할**이었다. 예를들어영희의검토자를묻는데현우의검토자를답했다. 기존두후보는같은대상의다른역할만비교하여,현재실제오답이후보에없었다. 따라서2×2행순위64/64는대상까지바르게골랐다는증명이아니다. 현재학습의전체실패원인을이선택하나로단정하지않되직접해당축을개입한다.

### 2. 질문·대안

| 경로 | 직접 판별·비용 | 결정 |
|---|---|---|
| 4질문/4답의CE·역할음성·모든축음성대조 | 같은positives/compute에서실제오답음성의기여와CE만의효과를비교,새학습3팔필요 | **준비**,현재CF/CPT32뒤조건부실행 |
| 문맥4이름으로추론답제한 | 재학습없이해당후보사이선택을개선할수있으나후보공급이필요한특수추론 | 원인진단의TF4후보만관측,실제생성은제한하지않음 |
| 현재자료량만증가 | 같은실패경향을더가르칠가능성과비용,어느잘못된대비가문제인지미분리 | 현재우선하지않음,75M공급연구는유지 |

### 3. 예측 — 실행 전

역할만읽는점수기는현재role-only손실을작게만들수있지만같은역할·다른대상의음성과는동점이되어새ALL_AXES에서벌을받는다. 네양성질문자체를가르치는것만으로도CE4가개선될수있다. 새mask의효과는동일한새4질문자료에서만비교한다. 한국어미학습질문틀/자연QA/산수/자유설명개선은보장하지않으며기존실제답을보고선정한탐색적후속이다.

### 4. 단계·과학 조건

새tag는 `p106b_subject_role_v1_s1337`다. 기존A동결TRAIN2048/DEV128/TEST128한영bundle의원fact graph/order/source/split을그대로읽는다. 6개서로다른slot중두사람/각두역할의4정답을모두질문하며,옛두질문의view0/1/2 user본문·gold는byte동일하게유지한다. 나머지2질문은같은원문과질문틀에서대상만바꾸고사실표로gold를검산한다. 파생schema/parent SHA를신설하고옛검증bundle을조용히변조하지않는다.

| 단계 | 내용·선결 |
|---|---|
| Stage4er0W | 순수자료/마스크/gradient/분모회귀·실제토크나이저·양성/교차/원문순서동결 |
| Stage4erWa/Wb | 옛CE/대조의같은2질문에4후보TF·길이/최초분기/원래실제오답우도진단·학습/새체크포인트0 |
| Stage4erXa/Xb/Xc | CE4/ROLE_ONLY4/ALL_AXES4 각각원부모에서새8회비용·3팔모두동일전체채점경로 |
| Stage4erYa/Yb/Yc | 각팔새원부모·새optimizer·4pass896회·3cost와합계8시간/절대종료예비게이트 |
| Stage4erZa/Zb/Zc | 같은신규3학생각ce/role_only/all_axes의후보없는1758첫답/4×4 TF/원문32·CF256은별도후속연결로분리·모델/출력변경0 |
| Stage4erR | 전체source/CP/본체/원답/학습분모·paired graph재계수·자동채택0 |

새세팔은동일원P090B dense14/chat32의초기본체E854…·micro8양성×accum16·seq1024·checkpoint-on·compiledefault·seed1337·constant Adam5e-5/Muon2e-4/RMS4·전체WD0·clip1을사용한다. 기존자연QA8192묶음/양뷰16384행과replay4096행은동일하고관계4질문×2048=8192행을더해28672행/pass·224update/pass·4pass896회다. 새원문7168창/7,340,032targets는같은TRAIN597,995,000파일에서1025폭비중첩으로별도선정하고세새팔에서같다. 옛A의768/6144창과일치하는조건이라고주장하지않는다. 앞선597,995,192표기는결과101§280의실제stat1,195,990,000B/uint16근거로정정했으며원문SHA/실행자료변경0이다.

각relation micro는2원그래프×4양성=8행이며,모든질문에나머지3답을교차한24행을물리micro8씩별도forward한다. 세팔모두같은16점수/그래프를계산한다. 단일row의음성은 ROLE_ONLY4가동일대상·다른역할1개,ALL_AXES4가유일정답밖의3개다. `sum_q mean_valid_neg softplus(s_neg-s_gold)/whole_update_questions`에계수0.1을곱하며CE4는0이다. 내용평균logP만대조하고EOT는양성CE에만포함한다. 전체양성CE/native각유효token분모와각row의1/3개음성평균을독립회귀로검증한다.

모든답은PERSON이며네이름이서로달라타입만으로선택할수없다. 다만BPE길이는네답에서다를수있어질문별같은후보target IDs/길이·합/평균·EOT와최초분기점수를별도로기록한다. 역할만/대상만/상수이름/첫사실값지름길의4질문성공상한을CPU로함께확인한다. 숨겨진gold/후보목록은실제generate입력에없다.

### 5. 평가·판정

primary는언어/view별같은4질문을모두맞힌64사실그래프단위의최초자유답이다. 옛두질문/새다른대상두질문도각각보고한다. 다른대상·같은역할/같은대상·다른역할/그외/문맥밖문자열·빈답·종료를분리한다. 기존자연QA192/기초산수24/사용자6질문과원문32창FP32-MATH를유지해새controller의평가를관계1536+기타222=1758답/모델로고정한다. 현재CF256교환문평가는원형/분모를이중화하지않도록이controller와분리한별도후속연결로남기며현재구현완료/실행을주장하지않는다. 조건이맞는옛parent990답은원형그대로겹치는질문에만재사용하며미실행새질문을0점이나완료로부풀리지않는다.

TF4후보순위는실제답을대신하지않는다. 이전고정TEST는이미반복관측한개발성코호트이고새이름/세계지식의완전미노출평가가아니다. 단일seed·세팔/여러view·후행탐색이며기본모델채택/범용지능/Falcon동등을자동판정하지않는다.

### 6. 비용·중단

원A의양성+교차padded117.44M대비새설계는218.10M수준으로커지므로33분/팔을그대로복사하지않는다. 본학습팔당60~80분과세cost·setup/저장을초기예약하고,평가5400초+기록3600초를별도보존한다. 각8회실측의compile/steady/whole/allocator를분리하고총8시간외삽안일때만전체를연다. 최초초안6시간은실제동결/비용/학습전에8시간으로정정했다. 세팔축소는원인분리를약화하고평가/기록예비축소는증거누락위험이있어,사용자20일17시까지수시간GPU위임내에서세팔전체를보존하는8시간이낫다고판단했다. 옛A4시간·CPT예산/과학문턱은변경하지않았다. GPU속도계측은단독/직전5분유휴이며큰CPU재고와병행하지않는다.

### 7. 실행·보존

독립8파일/회귀/SH와 실물CPU 동결을 완료했고 실제상태는 아래9절이 소유한다. oldA/CF/CPT32의소스·원로그·CP를수정하지않고새namespace에write-once로저장한다. 모든SH는실제공용REGRESSION/PREFLIGHT/EXECUTE3단계연결회귀·stdin차단/실패전파를검증하고20MB미만샤드를사용한다. 큰CP/상세원형은Git에넣지않는다.

### 8. 한계

새네양성질문과896회·원문draw가증가하므로옛A와의차이를negative마스크단일효과로설명하지않는다. 같은코드가상사실/24이름/4관계쌍의조건부학습이며일반상식·숫자연산·자유한국어까지확장하지않는다. 새로운배포head/MTP/메모리모듈은없고기존75M×4목표와자료부족을유지한다.

### 9. 이력

2026-10-19 A완결990답/CE오류107건의유형을보고,세경로중대상·역할모두대조하는후속을선택해scope/F4를작성했다. 현재이후GPU/학습은NOT_RUN이며먼저기존CF와준비된CPT32를회수한다.

04:37:32 실제CPU70/상속원자료·새7168창·전체양성/교차분모·1758입력/4×4 TFspec·원A990메타동결완료([101 §287](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). 경로헤더수리후독립19/19도확인했고새8코드수정은중지했다. 이후GPU비용/학습/새실답은아직NOT_RUN이며세cost/full896/자유답판정전효능을주장하지않는다. full전수정적은67PASS/1ERROR/6NOT_RUN이며남은오류는별도승인대기인공용smoke 새profile호환이다.

05:11:13까지 Stage4erWa/Wb의 옛768 모델2×4 진단은 완료했다([101 §291](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). 역할후보만 이긴128/128과 네 후보1위71~86/128은 다르며 실제 다른대상 오답203건은 첫분기부터 오답 선호였다. 준비 가설의 음성coverage 결손과 맞지만 새4질문 양성/새음성의 효과는 아직 미실행이다. 세 실제cost와8시간예비가 먼저이며 동결8코드는 변경하지 않는다.

Stage4erXa CE4 cost8은05:18:55 종료0/새CP0·allocated4173.874/reserved4392MiB·warm7중앙3.9409초/최대4.7915초로 완료했다([101 §292](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). 회귀/선결과 실제GPU 사이의 유휴를 구별했고 다른2비용 전에는 전체학습을 열지 않는다. 새모델 효능/기본채택은 여전히 미판정이다.

05:36:17까지 나머지 ROLE_ONLY4/ALL_AXES4 비용8도 완료했고 세 원형/초기본체/그룹·분모가 같았다([101 §293](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). driver 실측과 최악warm 외삽+평가5400/기록3600은6.694h<8h·절대허가안으로 fits였다. 이 값은 모든SH선결/5분대기를포함한전체큐상한보장이아니다. 새896세팔은각원부모에서다시시작하며비용8모델을이어쓰지않는다.

06:42:46 CE4의896/4pass를 종료0으로 완료했다([101 §295](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). 실제양성22.300316Mx/613928assistant·native7.340032Mtargets/새weight-only1이며DEV9.03447→.54507/native32+0.05978이다. 정답손실감소 예측은 관측됐으나 네질문·자연QA의 실제답 효과는 아직NOT_RUN이다. 큰초기globalL2/전896clip·비용표본보다긴update와동시CPU작업을보존해격리속도우열을주장하지않는다. 완료CE SH는 `-done.sh`이며06:43:20 ROLE_ONLY4 SH착수/ALL_AXES4·실답은후속이다. 동결8코드는변경하지않았다.

07:44:43 ROLE_ONLY4도 종료0·896회·같은 실제 분모와 초기 본체로 완료했다([101 §296](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). DEV .48800/native32 +.05228이지만 실제 답변 개선 여부는 평가 전이다. driver3552.909초·peak reserved4472MiB·전체896 clip을 보존하며 CPU 병행으로 격리 속도 비교는 하지 않는다. 완료 SH는 `-done.sh`로 보존했고 새 CP는 후속 평가 입력으로 목록에 추가했다. 07:45:33 ALL_AXES4를 같은 원부모에서 시작했으며 세 실제 답변 평가 전까지 목적함수의 품질 우열을 판단하지 않는다.


08:47:03 ALL_AXES4도896회/같은 분모·초기화로 완료했다([101 §298](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). DEV .52735/native32 +.05218·driver3539.739초·reserved4472MiB·clip896을 확인했다. 세 팔 손실 하락은 실제 답변 성공과 다르며, 08:49:41 CE1758답부터 순차 평가를 시작했다. 전체 assistant targets613928 중 실제 종료 ID140544는22.8926%다. replay의 여러 지도 턴을 행당1개로 계산하지 않고 이 비중을 실패 원인의 증거로도 올리지 않는다.


### 사용자 실행파일·현재 준비 순서

09:03:43까지 세1758답/R을 완료했다([101 §299](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). 영어 관계 기본 네답모두43/64→ROLE64/ALL61, 새표현11→33/42로 국소 개선을 관찰했지만 한국어 새표현은 세팔0/64이고 일반QA/산수는 미달이다. 본체 전후 불변·R errors0과 품질 판정을 분리한다. 사용자6과 사전고정40표본의 실제 답을 직접 읽고 그대로 보존했다. 예상한 전체음성의 범용 개선은 확인하지 못했으며 기본모델로 채택하지 않는다.


13개SH는아래순서로등록하며,현재총괄은20일17시위임안에서기존CPT32평가뒤단독GPU로수행한다. 실제완료/진행은9절·결과문서가소유하며이목록존재를실행성공으로세지않는다. 공통micro8×accum16/seq1024/checkpoint-on과최대wall/8시간gate는source receipt에명시된다.

| 순 | 단계·SH | 선결·현재 상태 |
|---|---|---|
| 1 | `run_P106B_Stage4er0W_subject_role_cpu.sh` | 순수전체회귀/실제원천·토크나이저동결,모델/GPU0 |
| 2 | `run_P106B_Stage4erWa_old_ce_four_candidates.sh` | 기존CE/3×990·원형완결,추가TF2×4만 |
| 3 | `run_P106B_Stage4erWb_old_contrast_four_candidates.sh` | 기존대조/3×990·원형완결,추가TF2×4만 |
| 4 | `run_P106B_Stage4erXa_ce4_cost8.sh` | 새CPU동결·단독/직전5분GPU유휴 |
| 5 | `run_P106B_Stage4erXb_role_only4_cost8.sh` | 동일새CPU·단독/직전5분GPU유휴 |
| 6 | `run_P106B_Stage4erXc_all_axes4_cost8.sh` | 동일새CPU·단독/직전5분GPU유휴 |
| 7 | `run_P106B_Stage4erYa_ce4_train896.sh` | 세비용8/전체8시간·절대종료예비 |
| 8 | `run_P106B_Stage4erYb_role_only4_train896.sh` | 같은새자료/초기화·회귀/예비 |
| 9 | `run_P106B_Stage4erYc_all_axes4_train896.sh` | 같은새자료/초기화·회귀/예비 |
| 10 | `run_P106B_Stage4erZa_ce4_actual_answers.sh` | 해당새CE896완료·가중치/원형 |
| 11 | `run_P106B_Stage4erZb_role_only4_actual_answers.sh` | 해당새role_only896완료·가중치/원형 |
| 12 | `run_P106B_Stage4erZc_all_axes4_actual_answers.sh` | 해당새all_axes896완료·가중치/원형 |
| 13 | `run_P106B_Stage4erR_subject_role_readback.sh` | 새세모델1758답/TF각완결·CPU독립원형판독 |

## 2026-10-19 Stage4es — 질문 위치·반복을 분리하는 무학습 진단

### 1. 왜

[101 §290](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)의 자연QA view2는 질문을 본문 앞으로 옮기면서 지시문도 바꾼다. 낮은 정답률을 순수 어휘전이 실패라고 읽지 않는다. 관계 view2의 표현대조와도 다르다. 문맥상한 초과0은 앞 질문 유지·최근성 문제를 배제하지 않는다. 같은CP 무학습진단/새교과과정/복사보조3안 중 원인분리에 가장 작은 첫 안을 우선한다.

### 2. 질문

동일한 지시문과 전체지문/질문에서 앞질문 QC와 뒤질문 CQ의 실제답이 얼마나 다른가? 질문두번 QCQ/CQQ의 차이는 반복량과 구별되는가? 실제문맥길이별로 어느구간에서 잘못된대상/빈답/길이상한이 나타나는가?

### 3. 예측과 원문

질문을끝에두면 기존학습순서와가깝고 질문거리도짧아져 회복될수있다. 앞뒤질문은 문맥을질문에조건화할기회를주지만 두번반복/길이도달라져 대조가필요하다. [Lost in the Middle arXiv v3 §4.2·그림9](https://arxiv.org/pdf/2307.03172)는 큰모델의 합성key-value에서 이득이 컸지만 자연QA에는 일관된개선이없었다. 93M 삼진모델로 그 효과를 옮길수없으며 어느위치에서도 대상선택이낮을가능성이있다. 논문의v1 §5.2와v3 §4.2를 혼동하지 않는다.

### 4. 단계 설계

| 단계 | 내용 | 상태/게이트 |
|---|---|---|
| Stage4es0W | 순수회귀와완료CPT32원형/source·두CP/토크나이저byteSHA·전조건입력CPU동결 | 완료 CPU65·128root/512입력,101§294 |
| Stage4esWa | native+32k final에서128질문×4조건=512첫답 | 완료512/기존CQ128 답·receipt 재현,101§301 |
| Stage4esWb | 원부모+32k final에서같은512첫답 | 완료512/기존CQ128 답·receipt 재현,101§301 |
| Stage4esWc | 두CP의원형·동일CQ/기존답/분모·paired 기사집계 | 완료 errors0/독립81115 검산0불일치,101§301 |

완료CPT32의1536원형/512root에서 과거답/점수/종료를선정에쓰지않고 문맥/질문/언어/root/source/alias만읽는다. 한영각64root를전체조건1024+max_new128여유충족집합의문맥토큰사분위별16개해시순으로선정한다. 부족은HOLD·원문무삭제/무crop이다. 같은지시문하나로 CQ(문맥→질문), QC(질문→문맥), QCQ(앞뒤질문), CQQ(뒤에같은질문두번)를생성한다. CQ는기존view0와prompt가정확히같아야한다. QCQ/CQQ의전체길이/토큰차이는실측해공개하며 완전한기제인과로해석하지않는다.

원형1536/metadata/source/두CP SHA는기존검산된report와결합한다. 선택128root/512조건별입력은새local20MB미만shard에쓰고작은hash/길이/분모보고만Git에둔다. FP32-MATH·온도0/top-k1·cacheON·MTPoff·max_new128·EOT를기존생성경로그대로사용한다. 각CP의본체지문전후같음을확인하며학습/optimizer/추가head/가중치쓰기0이다.

### 5. 판정

원형/본체/생성receipt/입력불일치·누락은도구/선결오류로분리한다. 같은CQ fresh답의기존답재현여부도별도기록하고불일치시경로정합을확인하기전조건효과를확정하지않는다. 128root×4조건과64root/언어·기사수·문맥토큰범위·질문거리·EM/F1/empty/STOP/MAX_NEW를분리한다. 기사paired구간은고정개발코호트의기술통계이며학습seed일반화/공식벤치아니다. 큰효과문턱/보편σ를새로만들지않고 자동prompt채택/정답승격을하지않는다. 정답수와문구·단위오류를실제답표본에서구분한다.

### 6. 비용

CPU동결수분이내·GPU기존CP2개×512답은잠정10~20분,전체평가/검산/기록1시간상한을예약한다. 실제길이/종료에따라달라지며추론속도benchmark가아니다. 사용자20일17시/평가완결과기록예비를각시작전에다시확인한다. GPU동시실행0·기존896세팔과겹치지않는다.

### 7. 실행

4런처를작성했다: `run_P106B_Stage4es0W_question_position_cpu.sh`, `run_P106B_Stage4esWa_cpt32_question_position.sh`, `run_P106B_Stage4esWb_base32_question_position.sh`, `run_P106B_Stage4esWc_question_position_readback.sh`. 순수65회귀뒤명시TSV에등록했고정적린트/실물CPU선결을계속확인한다. 입력대기/교사실행/기존결과덮어쓰기는없다. 평가/판독시답을보기전고른한영×길이사분위8root의실제질문과4조건답/종료를비교출력하며본문전량은Git로그에복제하지않는다.

### 8. 한계

원래관측한기사/QA의개발진단이며새세계지식검정이아니다. 길이사분위는실제분포의상대구간이고원인으로길이를무작위화한실험도아니다. 같은질문두번은추가토큰/반복자체를바꾼다. 다른모델에효과가있다는이유로기본생성정책을바꾸지않는다. 새75M/300M 부족·보호원천·교사후행판독선결은그대로다.

### 9. preflight와 실행 이력

`--tag p106b_question_position_v1_s1337`는10월19일05:29조회에서충돌없음이었다. 코드/기존registry탐색에서같은4조건독립단계는없다. 학습steps/draw/optimizer는0,풀≥2배는새학습없어해당없음이다. 서로다른CP를품질전역순위로합치지않고동일CP내질문위치대조가핵심이다.

06:19:25~06:19:38 Stage4es0W 실제CPU 종료0으로 [101 §294](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에 기록했다. 합성65회귀/기존원형81파일/512원질문/선택128질문·512입력/기존CQ256receipt 재검산을 완료했고 두코드ECC1…/C533…를 동결했다. 원형 canonical block 경계 누락은 실물동결 전에 기대비교만 수리했으며 과도한 독립 wrapper 실패도 숨기지 않았다. 실제선택입력 최대499토큰이므로1024경계 검증으로 주장하지 않는다. **CPU 완료, 두GPU/후속판독 NOT_RUN**이며 기존896세팔 회수 뒤 순차 실행한다. 최초 위치가 중요할 수 있다는 예측은 아직 판정하지 않았다. 완료CPU SH는 같은stem의 `-done.sh`다.

09:12:45까지 두512답과 R을 완료했다([101 §301](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). 같은CQ128 답·전체receipt는 각CP에서 모두 재현됐고 본체는 불변이다. 앞질문QC가 약할 수 있다는 예측은 지지됐지만 반복QCQ/CQQ의 보편 개선은 확인하지 못했다. 입력 최대499/잘림0과 기능적 질문 활용을 구별한다. 독립 stdlib81115 검산0, 실제8root×4조건×2모델 원답도 직접 판독했다. 별도 기억 head/반복 정책은 채택하지 않았고 다음은 D 실제 이력이다.


이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

본body학습시간의선험추정은팔당60~80분이며세cost가이예상/총8시간/최신허가를검증하기전본학습을열지않는다. 새13런처는stdin/선택대기0이며공용표준3단계최종receipt로완료/보류/도구오류를분리한다. 알려진설계실수점검통과가실제효능예측은아니다.

## Stage4erS — 실제 생성 토큰과 TF 분기 prefix의 CPU 인증

### 1. 왜

§291의 첫 분기 점수는 canonical 후보 prefix의 진단이다. 실제 자유 답변과 같은 토큰 prefix에서 잰 것인지까지 연결해야 해석을 더 좁힐 수 있다. 기존 helper는 실제 continuation ID 전체를 해시했으나 공개 원형에는 ID 목록 대신 그 SHA를 남긴다. 모델 가중치나 동결8파일을 바꾸지 않고, 복원 가능한 후보의 해시를 대조하는 독립 CPU 판독을 준비한다.

### 2. 질문

| 질문 | 범위 |
|---|---|
| 원답이 네 이름 중 하나와 raw 문자열로 같을 때 실제 token열도 같은가 | 생성 continuation SHA와 완전 레코드의 유효 assistant target ID 비교 |
| 같다면 각 TF 분기가 실제로 도달한 동일 prefix인가 | 질문마다 세 음성 edge를 별도로 검산 |
| 어디까지 미해결인가 | 다른 segmentation·미등록 종료·미도달·후보 밖 답을 별도 분모로 보존 |

### 3. 예측·세 대안

| 안 | 장점 | 비용·한계 |
|---|---|---|
| A 독립 CPU 해시 인증 | 모델/기존 원형 변경 없이 일부 실제 prefix를 확인 | 두 코드와 회귀 필요, canonical 해시 불일치는 미해결로 남음 |
| B 소형 GPU 재생성과 전체ID 관찰 | 비정규 segmentation까지 새로 관찰 가능 | 새 생성·cache/수치 경로 검증과 GPU 비용 필요 |
| C 기존 canonical TF 해석만 유지 | 추가 비용0 | 실제 prefix와 같다는 주장 범위를 넓힐 수 없음 |

총괄은20일17시까지 허가된 진단 안에서 A를 선택한다. B는 아직 구현/실행하지 않는다. 해시 인증이 많이 되더라도 실제답 정답성이나 cached/full-forward 수치 동등성이 증명되는 것은 아니다.

### 4. 단계·계약

독립 `scripts/diag_p106b_actual_prefix_readback.py`와 `scripts/test_p106b_actual_prefix_readback.py`만 신설한다. namespace는 `p106b_subject_role_prefix_v1_s1337`다. 기존 main8코드·D/QPOS·모델/공용checker는 수정하지 않는다.

CPU 회귀 뒤 main 세 평가1758답과 Stage4erR의 원형 판독 완료를 선결로 한다. 각 모델의 관계 view0 512개, 세 모델1536개 원형을 고정하며 각질문 세 edge, 모델별1536/전체4608 edge를 빠짐없이 분류한다. 부분 원형은 HOLD8, SHA/계보 손상은 TOOL_ERROR9다.

이름 매칭에는 raw 문자열의 정확 일치만 쓰고 NFKC/strip/공백 정리나 채점용 정규화를 사용하지 않는다. 같은 bundle 안의 유일 후보만 인증 대상으로 삼는다. 후보 ID는 standalone 이름 재인코딩이 아니라 기존 complete_record가 검산한 완전 레코드의 유효 assistant y에서 얻는다. shifted x/y·마스크·원 prompt/BPE 경계·CPU 동결 record/spec 지문을 확인한다.

STOP_SEQUENCE는 인증된 EOT 한 개가 continuation SHA에 포함된다는 기존 계약을 따른다. EOS에는 EOT를 붙이지 않으며 좁은 판독에서는 미해결이다. MAX_NEW는 종료를 추측하지 않고 실제 내용 IDs·길이·SHA가 모두 맞을 때만 인증한다. 해시 함수는 기존 compact JSON list[int] UTF-8 SHA256 정의 그대로다. 해시 불일치는 segmentation 차이일 수 있으므로 모델 오답이나 도구 손상으로 바꾸지 않는다.

prompt 길이 L, 분기 인덱스 d, predictor p=L-1+d에서 실제 `P+G[:d]`와 해당 edge의 `record.x[:p+1]`를 정확 비교한다. G[d] 자체는 prefix에 넣지 않는다. 다른 후보의 더 늦은 분기까지 같다고 추정하지 않고 미도달/불일치/미인증을 별도 기록한다. EOT 분기와 공유 prefix도 유지한다.

### 5. 판정

모델별 전체 view0/유일 raw 이름 매칭/token SHA 인증/각 edge의 prefix 일치·불일치·미도달·미인증을 같은 고정 분모로 보고한다. 기존 점수·생성·모델 선택 정책은 바꾸지 않는다. 지식/품질 통계 문턱을 새로 만들지 않으며 기존 dense/recur의 sigma를 이 정확 해시 검사에 복사하지 않는다.

### 6. 비용

GPU/Module/forward/학습/새CP/교사/다운로드0이다. source 검산과 판독 worker를 각300초 이내로 제한하며 기존 실제 생성이 끝난 뒤 최대600초 CPU 활동을 예약한다. SH 회귀·큐 대기와 달력시간은 별도다. 대용량 source/답 복제는 ignored local의 새 이름공간에만 두고 공개 summary/원형 SHA/분모만 선택 보존한다. 파일별20MB 미만·기존 산출물 덮어쓰기 금지를 지킨다.

### 7. 실행

`run_P106B_Stage4erS_actual_prefix_cpu.sh`를 회귀→선결→본판독의 비대화형3단계로 작성했다. 우선순위는 main세896→세1758답→R→이CPU판독→QPOS→D이며 새 GPU를 병행하지 않는다. 실제 실행은 아래 새 코드의 독립 검토/정적과 R 완료가 선결이다.

### 8. 한계

인증 가능한 부분집합만의 cryptographic 연결이다. 해시 미해결을0점으로 채우지 않는다. 같은 token-prefix라고 quantization/cache/정밀도 logits가 같다는 증명도 아니며 실제 선택한 토큰·두 후보 gap·전체 어휘 argmax도 서로 다르다. 일반적 반복 원인이나 지능향상의 단독 증거가 아니다.

### 9. 초안 검산과 남은 실행 선결

A08FA0FB…/101F4DF4… 초안의 합성36개와 독립36개는 통과했다. 독립 감사는48개 edge와 실제 encoder의 ignored newline/BPE 경계를 별도 검산했다. 다만 재서명한 메모리 raw manifest의 절대경로가 exact basename/stem 확인 전에 digest에 전달되는 P1을 확인했다. 실제 보호자료 접근/원형 변경/모델 실행은0이다.

초안과 반례를 먼저 보존한 뒤 독립 두 코드에만 선해시 경로 검사와 회귀를 수리한다. main8·기존 생성·손실·원형은 바꾸지 않는다. 현재 SH 미작성/실물판독 NOT_RUN이며 수리·새 SHA 동결·독립 재검토·관련 정적과 main 세 평가/R 완료가 모두 먼저다. 합성 회귀가 통과해도 이 안전 반례를 무시하지 않는다.

09:01경 독립 두 파일만 선해시 경로 검사로 수리하고 수정 중지했다. driver40,945B/SHA `1F08BFE02E798F267E0EEE3B7181FA68658028BD0192B393CB4E54E3D1A7EE52`, test47,861B/SHA `133D203A0A6542BAB5593692F6A17D2880FC3699A7D21A1C125B7AC7D19D6274`다. 기존36+신규4=40 guarded 회귀는20.229초에 통과했다. 추가 회귀의 첫1실패는 앞서 정상 answers 단계에 있던 경로까지 rank 위조의 호출로 센 기대값 오류였고, 해당 manifest 이후 호출만 확인하도록 test만 수리했다. 실물 source/모델/GPU 접근은0이며 독립 재검토와 전수 정적은 별도 선결이다.

`run_P106B_Stage4erS_actual_prefix_cpu.sh`를 작성해 우선순위28에 등록했고 Bash 구문과 공개 check-only를 확인했다. 실제 source worker는300초씩2회·활동600초 이내이며 회귀/래퍼/정리 시간은 별도로 보존한다. code-only check는 실제 source/토크나이저/CP byte를 읽지 않았다. 원tag와 같은 실제 로그 충돌0, 유사 런 검색에서도 이 CPU 인증을 수행한 원형은 없다. 현재 main세1758 생성은 완료했지만 R과 이 reader의 실제 실행은 아직 완료 전이다.

09:06:48~09:07:44 실제 SH 회귀40/선결/판독을 종료0으로 완료했다([101 §300](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). 독립40/이전 P1 차단·전수67PASS/기존공용ERROR1/NOT_RUN6 뒤에 실행했다. view0의1536질문 token SHA와4608 edge prefix 전부 MATCH이며 EOT 실물 분기0, 모델/학습/GPU0다. 기대한 인증은 가능했지만 정답성·cache 수치정합·인과 증명이 아니라는 한계를 유지한다. 완료SH는 `-done.sh`로 보존한다.




### 9. 착수전 점검

2026-10-19 namespace 조회에서 기존 로그 충돌과 유사 런을 찾지 못했다. 기존 matching reader와 달리 실제 continuation SHA를 후보 ID로 역대조한다. 새 학습/draw가0이므로 풀2배·LR·batch 조건 변경은 해당없다. source/CP/토크나이저와 기존 점수는 그대로다. 착수 전 작성 당시 코드·CPU 회귀·실물 판독은 **NOT_RUN**이었으며, 위09:06:48~09:07:44 이력과 결과101§300이 이후 실제 완료를 소유한다. 자세한 파일 권한과 영향은 현재 WIP scope가 소유한다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 2026-10-19 Stage4et — 기초 교과와 질문 표현·위치의 네 팔 통제 학습

### 1. 왜

[101 §299~301](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에서 영어 관계는 일부 개선됐지만 한국어 새 표현과 자연 QA가 약했고 질문 위치에 민감했다. [104 §12](../test_result/104_20261010_P106D-규칙학습은-종료만-개선하고-교사는-라벨에-막혔다.md)의 산수는 첫답부터 약한 반면 조회는 실제 이력에서도32/32였다. 메모리나 고급 헤드부터 추가하기보다 충분한 기초 상태·정답 교육과 표현/위치 전이를 나누어 본다.

| 안 | 구체 시나리오 | 장점 | 한계·비용 | 결정 |
|---|---|---|---|---|
| A 표현×위치 네 팔 | 같은 두 수를 문맥에 주고 ‘결과만’/‘값을 숫자로’를 교차, 질문을 문맥 앞/뒤에 배치 | 실패한 축을 현재 구조·같은 상태·같은 정답에서 분리 | 독립 자료/회귀·원형/노출검산 구현 중간; cost8 뒤 조건부 실제 약2~5h 후보 | 주도 권한 내 총괄 권장·선택 |
| B 같은 새 교과의 학습만 확대 | 한 문구·뒤 질문 그대로 더 오래 학습 | 학습량 부족을 직접 볼 수 있음 | 문구/위치 의존성이 남고 반복 노출·망각 비용 증가 | A 결과 뒤 필요할 때만 |
| C 추가 원문 사전학습·새 구조 | 큰 native 풀 또는 기억/복사 head 추가 | 다른 병목을 다룰 가능성 | 새 풀/권리·다운로드 선결, 구조·부모·비용 교락; 현재 실행권한과 별도 | 지금 채택하지 않음 |

### 2. 질문

1. 같은 코드 상태를 충분히 지도하면 최초 산수·조회·Boolean·문자열 JSON을 개선하는가?
2. 같은 상태의 학습 질문을 T0만 반복하는 것보다 T0/T1 두 문구로 학습하면 새 T2/T3에도 이득이 있는가?
3. 질문을 항상 지문 뒤에 두기보다 앞/뒤를 균형 있게 교육하면 새 위치에도 이득이 있는가?
4. 국소 과제 개선과 원문 언어 손실·일반 QA/사용자6질문의 변화를 함께 유지할 수 있는가?

### 3. 예측

가장 먼저 틀린 기초값과 종료를 더 많이 지도하고 교차 질문을 노출하면 국소 전이는 개선될 수 있다. 하지만 소형 삼진모델/짧은 부모 학습·적은 논리 패턴·한국어 표현 학습의 한계 때문에 네 팔 모두 실패할 수 있다. 새로운 T2를 잘 맞혀도 광범위 지능·세계지식 향상은 아니다. 같은 정답의 다른 표현은 새 사실 수가 늘어난 것이 아니다. 기존768/896 연구와 자료 구성·스텝이 달라 직접 차감하지 않는다.

### 4. 단계 설계

새 namespace는 `p106b_question_transfer_v1_s1337`이며 기존8코드·MAIN/QPOS/D 원형은 수정하지 않는다. 독립 data/test와 driver/test만 신설하고 load_parent/make_optimizers/native_probe·현재 canonical encoder를 재사용한다. 기존 emit helper의 max128은 새 계약과 달라 별도 명명한 max64 어댑터에서 같은 precision/cache/EOT/receipt 논리를 사용한다. 기존128답의 후행 절단이나 전역 monkeypatch는 금지한다.

| 네 팔 | 코드 질문 문구 | 질문 위치 | 각 코드 질의의4epoch 노출 |
|---|---|---|---|
| fixed_last | T0 | CQ만 | T0CQ 네 번 |
| varied_last | T0/T1 | CQ만 | T0CQ 두 번·T1CQ 두 번 |
| fixed_balanced | T0 | CQ/QC | T0CQ 두 번·T0QC 두 번 |
| varied_balanced | T0/T1 | CQ/QC | T0CQ/T0QC/T1CQ/T1QC 각각 한 번 |

공통 순열·사실별 회전으로 문구와 위치가 특정 epoch에만 나타나지 않게 한다. 한영 짝과 과제별 분포를 검산한다. 자연 QA는 원 질문·원 문맥·원 답을 바꾸지 않고 위치 요인만 적용하며, 기존 replay4096은 모든 팔에서 동일하다. 문구별 nonpadding 입력 길이는 달라질 수 있어 실제 길이/시간을 공개하며 같다고 주장하지 않는다. 모든 팔의 shifted assistant target IDs·종료지도·행 노출·전체 update별 지도 분모는 같아야 한다.

매 pass12,288행 = 코드검증4096행 + 기존 자연 QA4096행 + 기존 replay4096행이다. 코드4096행의 중립 질의는 산수1024·조회512·Boolean256·JSON256이며 각각 한영2행이다. 산수1024는0..50의 +/−를 해시 선별하고 덧셈 교환순서를 같은 계산으로 묶는다. 이전 MAIN/D의 초기/현재/compact·replay 식과 사용자/수학 모니터를 먼저 제외한다. 후보 부족이면 중복 채우기/후행 숫자 범위 변경 대신 GPU 전에 정확히 보류하고 새 설계를 고정한다.

조회는128개 표×두 대상×두 속성의4질의×한영이다. 전체 사실표가 같은 그룹이고 행순서·언어·질문 문구를 바꿔 split을 넘기지 않는다. Boolean은 이름쌍을 train24/dev6/test6으로 먼저 분리하고 train256중립 질의를 AND80/OR80/XOR96, dev/test64씩은20/20/24로 구성한다. 각 진리값 조합과 true/false를 균형화하되 세 함수/12개의 순서 있는 진리표 패턴을256개 새 논리 지식으로 부풀리지 않는다. 이름쌍·binding의 모든 valuation/operator를 같은 split에 묶으며 기존 replay와도 검산한다. JSON은128개 원문 문자열×answer/result 두 key×한영이며 같은 literal은 key/문구/언어 모두 같은 split이다. 학생에게 요구한 key와 문자열을 직접 생성시켜 검사하며 예측답을 코드가 정답 형식으로 다시 포장하지 않는다.

dev/test는 별도 산수64·조회32질의(8표)·Boolean64·JSON32질의(16문자열)의192중립 질의×한영2를 준비한다. 그룹 SHA와 exact text/target/semantic identity를 렌더링 전에 분리하고, 기존 평가와의 겹침을 공개한다. 새 평가의 0/1점은 닫힌 producer 계약뿐이며 자유 설명의 오조어 목록이나 실시간 의미심사를 재도입하지 않는다.

평가는 모델별1694첫답을 사전에 동결한다. TEST에서 가족별32중립 질의×한영2=256행에 T0/T2×CQ/QC 네 조건1024답, TRAIN 상태의 가족별16중립 질의×한영2=128행에 미학습 T2/T3×CQ/QC 네 조건512답, 기존 자연 모니터64질문×CQ/QC128답과 기존 수학24/사용자6을 더한다. TEST의 표4질의·JSON두 key 그룹은 완전 보존하며 각 표본은 결과 전 해시로 선정한다. TEST의 새 상태/익숙한 T0와 새 T2, TRAIN의 익숙한 상태/새 T2/T3를 분리한다. 같은 부모도 **새 max64 프로토콜로** 평가하고 과거128답과 직접 비교하지 않는다. 모든 고정 정답+EOT가64 안에 있고 전체 prompt+64가1024 안에 있는지 GPU 전에 확인한다. 부족하면 조용히 자르거나 제외해 분모를 바꾸지 않는다.

| 단계 | 내용 | 다음 선결·상태 |
|---|---|---|
| Stage4etW0 ✅ 작성 완료·소비 HOLD | source/그룹/quotas/encoder/CE분모/스케줄·64토큰 회귀 및 실제CPU | 결과101§302·실제CPU127.28초/19manifest·독립 실제 소비불일치64replay/pass·모델0 |
| Stage4etCa/Cb/Cc/Cd | 네 팔 각각 같은 새 부모에서8update 비용, CP저장0 | 공통 실제 source·마스크·native와 optimizer receipts 일치 |
| Stage4etTa/Tb/Tc/Td | 네 팔 각각384update/4epoch, 최종CP1개씩 | 네 cost8·시간상한/VRAM·실제 target분모·부모 지문 일치 시만 |
| Stage4etEp/Ea/Eb/Ec/Ed | 부모·네 학생의1694실답/같은 원문32crop | 원답/입력/종료·CP불변·분모 정합 |
| Stage4etR | 원형 재집계·사전 표본 실제 답 판독 | 새 모델 기본값 자동승격 없음 |

### 5. 판정 기준

기술선결은 기존 원P090B 본체 `E854AB4E...`·chat32 `9716F40E...`·순차4pass·384업데이트·물리 micro8×accum16·seq1024·checkpointON·compiledefault·MTPoff·teacher0·새 optimizer의 완전 일치다. 현재 정본 make_optimizers의 Adam5e-5/Muon2e-4·RMS4·모든groupWD0·clip1을 그대로 사용하며 추가 반감하지 않는다.

각 update의16micro CE 합을 **그 update 전체 assistant target 수**로 정규화한다. 추가로 native8개1025token 창의 CE를8192targets로 정규화해 합하고 한 번 clip/step한다. micro 평균을 다시16으로 나누지 않는다. 네 팔의 같은 행/정답·양성target분모/EOT지도·native창 벡터가 같아야 하며 입력 token 차이는 별도 보고한다. 전수 clip전 L2 grad_max와 원문 손실을 남기며 grad>10을 안정이라고 적지 않는다.

품질은 가족·언어·seen/unseen state·T0/T2/T3·CQ/QC별 실제 정답, 상태 짝의 두 답 모두정답, 종료·길이·오류유형과 실제 원답으로 판단한다. Boolean 상수/조회 첫값·대상만/속성만 기준도 병기한다. 한 seed이고 동일 조건 재현 분산/새 보편 품질문턱이 없어 통계적 확정/범용지능·배포 채택을 선언하지 않는다. 문구·위치의 주효과와 교호작용은 같은 표본쌍에서만 기술하며 다중 비교/그룹 의존을 보고한다. 반복학습의 같은 사실 노출을 고유75M 확보로 세지 않는다.

### 6. 비용

4×384=1536 optimizer 업데이트, 팔당384×8×16×1024=50,331,648 padded positive slots다. 실제입력/지도량은 CPU 인코딩에서 별도로 계측한다. 네 팔 각각49,152양성행 노출이며 팔당 native3072개 완전창·3,145,728target이다. 같은 창 벡터를 네 팔이 재사용하며 native풀597,995,000token 안에서 창끼리는 비겹치게 고른다. 정상 LM 새대량풀≥2배를 주장하는 실험이 아니라 기존 승인 소형 deliberate4pass 연구다.

실험 전체 driver 활동 상한8h, 평가예비2h·기록예비1h를 먼저 떼고 cost8 실제 첫 compile+warm7과 epoch평가/저장 예비로 학습시간을 다시 계산한다. 네 cost 결과가 없거나 예상합계가 상한/권한잔여를 넘으면 학습은 열리지 않는다. 추정2~5h는 과거짧은 모델/학습을 참고한 후보이며 실측 보장은 아니다. 부모가 MAX_NEW를 반복하면 평가가 학생보다 훨씬 느릴 수 있어 QPOS50초를 외삽하지 않는다. 모든 모델 작업은2026-10-20 17:00KST 전 종료하고 학습은 최소3h 앞서 닫는다. 장시간 작업도60초 이상 무통신하지 않고 주기적으로 기록한다.

### 7. 실행

SH15개와 독립4코드의 실행 전 검증을 완료했다. 실제CPU 동결 뒤에만 네 cost8을 수행한다. cost와 본학습은 분리하고 write-once namespace/출력에 종료8보류·오류·완료를 구분한다. 모델 로딩 전 사전검사·회귀, 사용자 입력 대기 없음,20MB 미만 행 경계 샤드, 새CP만 저장, 완료 source/명령/Git 선보존 뒤 정확 삭제 원칙을 유지한다.

- `run_P106B_Stage4etW0_question_transfer_cpu.sh` — `prepare`, 상한600초.
- `run_P106B_Stage4etCa_fixed_last_cost8.sh` — `cost fixed_last`, 상한900초.
- `run_P106B_Stage4etCb_varied_last_cost8.sh` — `cost varied_last`, 상한900초.
- `run_P106B_Stage4etCc_fixed_balanced_cost8.sh` — `cost fixed_balanced`, 상한900초.
- `run_P106B_Stage4etCd_varied_balanced_cost8.sh` — `cost varied_balanced`, 상한900초.
- `run_P106B_Stage4etTa_fixed_last_train384.sh` — `train fixed_last`, 상한7200초.
- `run_P106B_Stage4etTb_varied_last_train384.sh` — `train varied_last`, 상한7200초.
- `run_P106B_Stage4etTc_fixed_balanced_train384.sh` — `train fixed_balanced`, 상한7200초.
- `run_P106B_Stage4etTd_varied_balanced_train384.sh` — `train varied_balanced`, 상한7200초.
- `run_P106B_Stage4etEp_parent_actual_answers.sh` — `evaluate parent`, 상한3600초.
- `run_P106B_Stage4etEa_fixed_last_actual_answers.sh` — `evaluate fixed_last`, 상한1800초.
- `run_P106B_Stage4etEb_varied_last_actual_answers.sh` — `evaluate varied_last`, 상한1800초.
- `run_P106B_Stage4etEc_fixed_balanced_actual_answers.sh` — `evaluate fixed_balanced`, 상한1800초.
- `run_P106B_Stage4etEd_varied_balanced_actual_answers.sh` — `evaluate varied_balanced`, 상한1800초.
- `run_P106B_Stage4etR_transfer_readback.sh` — `readback`, 상한600초.


### 8. 한계

모델은 같은 기존부모 하나·학습 seed하나이며 새75M/300M 본교육을 대체하지 않는다. 이름 binding/수치 조합·문구 일반화와 새 논리함수·세계지식을 구별한다. 자연 QA의 기존 주석 오류 가능성도 유지하며 aliases를 후행 변경하지 않는다. 부모 사전학습 전체의 사실 미노출은 검증하지 않았다. 더 많은 새 데이터·LR·헤드·내부thinking·양자화·재귀·폭을 한 팔에 섞지 않는다. 보호 사전/TinyDataset·다운로드·공용검사기·기존CP/원본 수정·외부 상태변경은 권한 밖이다.

### 9. 실행 이력 / 사전점검

2026-10-19 새 Stage4et를 계획했다. CPU/GPU/새자료/학습/실제답 모두 아직 NOT_RUN이며 기존 완료결과를 승격하지 않는다. 독립 정의 검토에서 문구×위치의 완전교차·Boolean 이름쌍 split·산수 첫답 coverage·max64와 옛128 helper의 충돌을 확인해 위 계약에 반영했다. 작은 모든 필드의 실제 encoder/SHA/수는 구현 후 먼저 검증한다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

### 초안 선보존과 실행 전 계보 수리 이력

초안은 로컬 커밋 `d1d58ce`에4코드·15SH·56/독립56·P1 두건을 먼저 보존했다. 이후 driver/test 두파일만 CP의 exact소유경로를해시전검사하고, 완료384·현재code/corpus/cases/events/본체·닫힌활동원장·실제ID타입/종료/본문decode·절대권한을 묶도록 보완했다. 순수 data/test2파일·질문/정답·분할·스케줄·학습목적은 불변이다. 최종후보66합성회귀에는8470메모리양성연결과 잘못된경로/오래된source/cases/미완료train/잘못된토큰/본문불일치 반례가 포함된다. 이 양성연결은 합성입력/decoder로만 수행했고 실제8470생성을 뜻하지 않는다. 독립최종검토 전 실물동결/모델은 여전히 미실행이다.

총괄의 실제 읽기전용 토큰 사전계측24.788초에서는1694평가질문의 전체prompt 최대521·정답+EOT 최대27로64/1024예산실패가0이었다. 선택한자연QA4096과T0CQ 한pass12288행의 실제입력은2045891x·지도75664·EOT18752(24.783%)였다. 산수는2048한영행이나지도4618/75664(6.103%)·content2570/56912(4.516%)로행비율과다르다. 현재목적을바꾸지않고학습결과뒤필요한경우만[리뷰08 §19](../docs/methods/08_paper_review2.md)의종료지도보존재가중을검토한다. 이사전검사는새코퍼스namespace/CP를쓰지않았고모델/GPU/학습0이다.

**실행 전 수리 검증 완료:** 독립 최종 감사 `handoff/audit/WIP_20261019_QUESTION_TRANSFER_FINAL_INDEPENDENT_CPU_REVIEW.json`(69346B·SHA `621D5AE4B7338714984EE9E406037D4EA46C2894337DB522F4FEB045E851F36B`)은 guarded66/66·37음성차단/5양성·실제asset/model/GPU0을 확인했다. driver `F7284ED86A37DF86E003F28440589E9953959F6CDB6E2D7AB7AF09EE2B6944EB`와 test `2D053078863E0BCDAF0D3AA3DC296A5D25321FCDB40E01D841D56178315664AD`로 동결하며 순수data2파일은 초안과 byte가 같다. 29개 기존함수/상태·자료·학습수학이 보존됐고 train의 추가는 x_tokens 로깅뿐이다. 8h는 실제worker 활동이며 회귀/선결wrapper의 모든 process벽시간 보장이 아니다. source/preflight/budget도 절대허가 종료는 검사한다. 최신전수정적은67PASS/공용profile오류1/NOT_RUN6이며 공용수리승인대기는 그대로다. 이제원형선커밋→실제Stage4etW0→유휴5분뒤cost8부터진행하며 실제동결/새학습/정답성은아직미판정이다.

**실제 CPU 완료(10:57:58KST):** d216de4 원형 선보존 뒤 Stage4etW0 회귀66/선결/실물동결을 모두 종료0으로 마쳤다([101 §302](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). worker127.280441초·공개CPU56746B/CFA9214F…·16팔/pass와coded/cases/dev의19manifest다. 각pass12288/75664targets/18752EOT·한영행6144씩이며 target/turnowner·96update순서/분모가네팔에서전량동일했다. 문구변형은x/pass6272가늘며위치만변경은이번합계가같았다. 실제GPU/학습/새CP/답안0이므로설계효능은아직미판정이다. 독립파생재집계→유휴5분뒤4cost8을먼저수행하고8h예약계산을통과해야384네팔을연다. CPU SH는done으로보존한다.

**독립 소비 HOLD 정정:** 위 CPU 작성 완료 뒤 실제 reader 전량 검산에서64replay/pass·16자료1024복사본의 무시라벨/양의 owner를 새 reader가 과잉 거부함을 발견했다. 원형 F728·자료·음성은 보존하고14미실행 SH를 hold로 둔다. 교정 첫 오답은 y=-100으로 계속 문맥 전용이며 잘못 학습됐다는 결과가 아니다. Stage4eu/v2의 소비복구·원형 동등성·모델 전 실제 읽기 선결을 완료하기 전 cost/GPU를 실행하지 않는다. 상세는101§302의 후속 정정과 독립 actual CPU 감사가 소유한다.

## 2026-10-19 Stage4eu — 무시된 교정 턴을 보존하는 실제 소비 복구

### 1. 왜

[101 §302](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)의 작성기는 통과했지만 실제 학습 reader는64개 replay/pass의 무시라벨·양의 turn owner를 거부했다. 잘못된 첫 답을 문맥으로만 사용하는 기존 producer가 타당하므로 자료를 버리거나 마스크를 바꾸지 않고 새 독립 버전으로 복구한다. v1 원형·원로그·동결본·음성은 커밋 `b46d90f`와 원래 source `d216de4`에 보존한다.

### 2. 질문

| 번호 | 질문 | 이유 |
|---|---|---|
| Q1 | 무시된 교정 첫 답을 그대로 유지한 실제 reader가 전량 통과하는가 | 모델 적재 뒤 지연 실패 방지 |
| Q2 | v2의 실제 x/y/owner/질문/정답·스케줄이 v1과 같은가 | 버그 수리와 자료 변경 분리 |
| Q3 | 같은 사실·답에 질문 표현과 위치를 함께 바꾸어 학습하면 새 상태/표현의 생성이 개선되는가 | 한국어 새 표현0/64·기초 산수 실패를 겨냥 |

### 3. 예측

소비 호환은 회복될 것으로 예상하지만 모델 효과는 미확인이다. 첫 오답이 이미 무시 라벨이므로 해당 owner를 허용해도 직접 양성 target이 추가되지 않는다. 다만 그 문맥은 후속 정답의 조건이므로 입력 embedding을 통한 후속 gradient가 없는 것은 아니다. 자료/학습수학을 유지하므로 표현 일반화·산수·망각 실패는 그대로 남을 수 있다. 작성 완료와 학습 소비 완료를 구별한 이번 실제 음성도 보존한다.

### 4. 단계 설계

기존 Stage4et의 네 팔·배치·초기화·목적·384회·64토큰/1694실답·32native crop·8h 예산/평가예약은 변경하지 않는다. 새 tag/schema는 `p106b_question_transfer_v2_s1337`/`P106B_QUESTION_TRANSFER_V2`이고 과학적 자료 선택·문항 ID·표시 표본 key는 v1 그대로다. 데이터/test 두 순수 파일과 기존 producer/core는 수정하지 않는다.

| 단계 | 수행 | 다음 관문 |
|---|---|---|
| Stage4euW0 ✅ 완료 | 회귀71·source 선결·새 CPU151.04초; 실제16팔/pass·DEV384 소비 | 독립19manifest/35shard·3042327조건 동등성/불일치0·모델0 |
| Stage4euCa/Cb/Cc/Cd ✅ 완료 | 각 새 부모8update·CP0, 4cost 종료0 | 원시32행 재검산·같은 optimizer/target/native·8h 예약 통과 |
| Stage4euTa/Tb/Tc/Td ✅ 학습 완료 | 네 조건 각각384update·4epoch·새CP1, 총4CP 완료·원형 검산0오류 | 전체 source pass/DEV는 모델 전 통과; 실제답은 평가 전 |
| Stage4euEp/Ea/Eb/Ec/Ed ✅ 완료 | 부모/네 학생의1694첫답씩 | 결과101 §313~317·같은 max64/FP32 MATH/greedy/KV-on/MTP-off·1694원형/본문/종료·본체 검산0불일치 |
| Stage4euR ✅ 완료 |8470실답과원형집계·30표본/모델 판독 | 결과101 §318·위치 JSON 회복 대산수/대상 실패, 일반 assistant 비채택 |

CPU prepare는 인코딩뿐 아니라 닫힌 샤드의 실제 `records_for`를16자료에 사용한다. 각 cost/train도 해당 팔4pass와 DEV를 모델/GPU 허가조회·출력디렉터리·optimizer보다 먼저 읽는다. 첫 오답의 y=-100·segment1은 보존하며 지도되는 토큰만 양의 owner를 요구한다.

### 5. 판정 기준

복구는 전량 소비 통과·v1/v2 payload 동등성·직접 무시위치 logit gradient0과 후속 정답 gradient 양성을 모두 요구한다. 소비 수리로 과거 음성이나 새 자료 불량을 PASS로 바꾸지 않는다. 비용/학습/평가는 기존 Stage4et의 명시 게이트를 유지하고 서로 대신하지 않는다. 단일 seed의 실답 변화는 관측 표본의 기술 결과이며 표준 사전학습 sigma를 이 Muon SFT에 복사하지 않는다.

### 6. 비용

CPU 재동결은 v1의127.28초에 실제 소비 전량 검증을 더하므로 약3~5분 예상이며 아직 실측 전이다. v1과 동일 비교의 의미가 없는 비용을 재사용하지 않고 네 cost8을 새로 잰다. 각cost 상한900초·각train7200초, 부모평가3600초·학생평가1800초다. 실제 worker 전체8h 상한, 평가2h·기록1h 예약과 사용자20일17시 권한이 별도다. 5분 유휴·GPU 단독 비용 계측과 CPU 동시부하 금지를 지킨다.

### 7. 실행

- `run_P106B_Stage4euW0_question_transfer_cpu.sh` — `prepare`, 상한600초.
- `run_P106B_Stage4euCa_fixed_last_cost8.sh` — `cost fixed_last`, 상한900초.
- `run_P106B_Stage4euCb_varied_last_cost8.sh` — `cost varied_last`, 상한900초.
- `run_P106B_Stage4euCc_fixed_balanced_cost8.sh` — `cost fixed_balanced`, 상한900초.
- `run_P106B_Stage4euCd_varied_balanced_cost8.sh` — `cost varied_balanced`, 상한900초.
- `run_P106B_Stage4euTa_fixed_last_train384.sh` — `train fixed_last`, 상한7200초.
- `run_P106B_Stage4euTb_varied_last_train384.sh` — `train varied_last`, 상한7200초.
- `run_P106B_Stage4euTc_fixed_balanced_train384.sh` — `train fixed_balanced`, 상한7200초.
- `run_P106B_Stage4euTd_varied_balanced_train384.sh` — `train varied_balanced`, 상한7200초.
- `run_P106B_Stage4euEp_parent_actual_answers.sh` — `evaluate parent`, 상한3600초.
- `run_P106B_Stage4euEa_fixed_last_actual_answers.sh` — `evaluate fixed_last`, 상한1800초.
- `run_P106B_Stage4euEb_varied_last_actual_answers.sh` — `evaluate varied_last`, 상한1800초.
- `run_P106B_Stage4euEc_fixed_balanced_actual_answers.sh` — `evaluate fixed_balanced`, 상한1800초.
- `run_P106B_Stage4euEd_varied_balanced_actual_answers.sh` — `evaluate varied_balanced`, 상한1800초.
- `run_P106B_Stage4euR_transfer_readback.sh` — `readback`, 상한600초.

### 8. 한계

작은 코드검증 교과는75M고유/300M본교육이 아니다. 입력한영행 수와 토큰 비율을 구별하며 반복4pass footprint를 고유지식량으로 부풀리지 않는다. 자연QA 원주석의 의미정답과 의학/일반상식 정확성은 전수 보증하지 않는다. OLD v1의14SH는 보류이며 새 code를 연결해 조용히 재실행하지 않는다. shared checker/환경·보호원천·기존CP/캐시·원본 로그·타WIP는 변경하지 않는다.

### 9. 실행 이력

2026-10-19 Stage4eu 복구 구현 후 합성71회귀를8.414초에 통과했다. masked-turn 왕복·직접 logit gradient·정상 target owner0 거부·늦은 pass/DEV 오염의 모델 전 중단을 포함한다. 이는 새 실제CPU·GPU·품질 결과가 아니다. 실물 동결과 원형 대조를 완료한 뒤 여기에 실제 결과를 기록한다.

**설계 점검:** padded SFT는384×8×16×1024=50331648 slots/팔이다. 이는 실제 x나 지도token이 아니다. 실제 미래 x는 기존 동결본의8183564/8208652와 새 동등성으로 확인하며 native3145728target은 별도다. 4epoch 제한의 소형 SFT이므로 사전학습의 무반복2배풀 조건을 통과했다고 하지 않는다. 새 namespace/CP는 정확한 경로로 충돌을 확인하고 광범위 레거시 registry 전체 조회는 대체하지 않는다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

**복구 코드 독립 검토 완료:** 감사 `WIP_20261019_QUESTION_TRANSFER_V2_INDEPENDENT_CPU_REVIEW.json`은13234B·SHA `3FE553CE7BBFB7BD0AA4261DAFB6A139C58A1A1F951CE4C72CAAA4D540E81832`다. 독립 guarded71/71·7개 dispatch fixture를 통과했고6함수의 선언된 수리 외 AST와36정의·순수data2파일이 불변이다. 실제 source/model은 아직 미실행이며 닫힌 샤드 작성 뒤 보고 전 소비검증이 실패하면 새 partial namespace를 보존/HOLD한다. 정적검사 중 보류14TSV행을 활성으로 남긴 등록 결함2건은 역사 주석으로 고쳐 재검사67PASS/기존공용smoke profile오류1/NR6을 보존했다. 공유 checker는 수정하지 않았다.

**실제 소비·동등성 완료:** 11:34:10~11:37:02KST Stage4euW0를회귀71/선결/본단계 모두0으로 수행했다. worker151.040185초·모델/업데이트/새CP/CUDA0, 실제16팔/pass 각12288행/75664target·64masked replay와DEV384/1626target을읽었다([101 §303](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). 독립 실제19manifest/35shard 대조는버전당201118행·3042327조건/불일치0, 감사59606B/3227BACE…다. x/y/owner/id/cases/정답/선택/schedule/native가불변이며 source의새 의미정답 판정은아니다. heavyCPU11:44:47.274576KST 종료→5분뒤4cost8 선결로진행한다. 과거v1 reader음성은보존하고W0done 원형SHA84BA1B05…를8a2dfea와대조했다.

**Stage4euCa 비용8 완료:** 11:50:12~11:51:48KST 종료0·CP0, 같은부모E854…/그룹과6211 SFT·65536 native targets를확인했다([101 §304](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). 첫42.002초/warm7mean2.010668초·torch reserved3062MiB·전체gradmax22.627573/clip8이며 새품질은미평가다. 첫팔보수예측1244.61초는384실측이아니고나머지3cost/8h예약이선결이다. 경고max_autotune_gemm은8회/정상종료를막지않았다. 다음Cb는5분유휴뒤11:56:49KST이후다.

**Stage4euCb 비용8 완료:** 11:57:06~11:58:36KST 회귀71/선결/8회모두0·CP0. 첫40.418845초/warm7mean1.998698초·torchreserved3062MiB,6211SFT/65536native target·실제x167090이다([101 §305](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). Ca와동일부모/optimizer·전체raw8행통계일치를확인했지만실제x는511다르며품질비교가아니다. 다음Cc는12:03:37KST이후5분유휴이며나머지2cost/8h게이트는미실행이다.

**Stage4euCc 비용8 완료:** 12:03:54~12:05:16KST 회귀71/선결/8회모두0·CP0, first35.344448초/warm7mean1.999806초·torchreserved3062MiB/allocated2529.024414MiB다([101 §306](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). 같은부모/그룹·6211SFT/65536native targets·실제x166579, gmax21.473997/clip8과원시8행집계일치를확인했다. 남은Cd는12:10:17KST이후5분유휴로열고공식8h예약전본384교육을하지않는다.

**네 비용과 예산 완료·첫 학습 시작:** Ca/Cb/Cc/Cd각8업데이트와회귀/선결은모두0·CP저장0이다. 공식Stage4euB0 budget은12:12:27KST 종료0으로전체예약16173.582169초/8h·admission=true를확인했다([101 §307~308](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). 평가7200초·기록3600초를예약하고같은부모네384회의보수학습합계4956.704302초를계산했다. 5분유휴뒤12:17:48KST Ta fixed_last 본학습을시작했고64회까지진행을확인했다. 아직최종CP/384완료/품질은미확정이다. 보류v1 14SH는직접호출해도현재v2를호출하지않도록환경/자식호출전에명시HOLD8을반환하며14구문/직접호출시험을통과했다. 원래명령은아래에이력으로남고b46d90f에서복구가능하다.

**첫 실제 학습 완료·두 번째 진행:** Ta fixed_last는12:32:45KST에384회/4epoch·새CP1개를완료했다([101 §309](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). 실제x8183564/지도302656/native3145728, torchreserved3104MiB·전체gmax22.554010/clip384이며raw384/CP SHA 재검산불일치0이다. DEV8.608869→.300511과고정원문32crop CE3.504207→3.540014(+.035807)를구별하며실제첫답은아직평가전이다. 완료CP052B5FFB…는Stage4euEa/R필수입력으로checkpoints.tsv에keep등록했다. 5분유휴뒤12:38:13KST에Tb varied_last를같은원부모에서독립시작했고진행중이다. 현재코드/목적/자료를변경하지않으며75M×4본목표도유지한다.

**두 번째 실제384회 완료:** Tb varied_last는12:53:18KST에384회/4epoch·새CP C24C4630…를완료했다([101 §310](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). 실제x8208652/지도302656/native3145728·torchreserved3104MiB·gmax22.701906/clip384, raw384/CP SHA재검산0오류다. DEV.305340/native32 3.540622(+.036415)는실답이나전체언어성적이아니며Ta와작은차이를품질우열로삼지않는다. CP2개는각Ea/Eb/R현재소비자로keep, 다음Tc는12:58:19KST이후독립원부모에서시작한다.

**세 번째 실제384회 완료:** Tc fixed_balanced는12:58:32~13:13:58KST에384회/4epoch와 새CP E2B53169…를 완료했다([101 §311](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). 실제x8183564/지도302656/native3145728·torchreserved3104MiB·gmax21.473631/clip384이며 전384행/CP바이트/코드SHA 재검산불일치0이다. DEV.320586/native32 3.543319(+.039112)는 실제답이나 전체언어성적이 아니다. CP3개는각Ea/Eb/Ec/R 소비자로keep, 마지막Td는13:18:59KST 이후 같은 원부모에서 독립 시작한다.

**네 번째 완료·전체 평가 준비:** Td varied_balanced는13:19:05~13:34:11KST 384회/4epoch·새CP10AF22B6…를 종료0으로 완료했다([101 §312](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). 전384raw/새CP/코드 SHA 검산0오류, 실제x8208652/지도302656/native3145728·torchreserved3104MiB·gmax21.841431/clip384다. DEV.327295/native32 3.542127(Δ+.037920)는 실제답 정답률과 구별한다. 네 조건CP는 각 실제 평가 필수입력으로keep이고 표시ID는30개/모델이다. Ta/Tb/Tc done3771B만 Git원형/명령 선보존 뒤 정리했으며 현재 Td done은원형커밋전보존이다. 다음은13:39:12KST 이후 부모/네 학생의1694답씩·총8470 실제답과MAX_NEW 메타데이터 전량검산이다. 기존 profile 오류1을 포함한 전수 정적67PASS/6NR도 별도로 보존했다.

**부모/네 학생과 종합실답 완료:** 14:36:18KST까지 Ep/Ea/Eb/Ec/Ed 각1694답과 R의8470원형 검산을 모두 종료0으로 마쳤다([101 §313~318](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). ROOT 전량 body decode/코드 정답/종료·계보 검산0불일치, 사전 고정30표본/모델의 실제 질문·답을 읽었다. ‘표면 변형과 위치 균형이 모든 과제를 올릴 것’이라는 기대는 **일반적으로 불성립**이다. 질문 앞 JSON은0/128→112/116으로 회복했지만 산수22~31/256·문맥 대상 혼동·일반 설명 실패가 남고 Boolean의 일부 조건은 감소했다. 같은 TRAIN 상태의 T2/T3 평가가 실제 학습 입력 재현은 아니므로 암기/전이는 다음 별도 진단에서 가른다. 현 네 모델은 일반 assistant 비채택, 학습 seed1/고정 native32의 한계와75M 부족은 그대로다. 완료7개(Td·Ep·Ea·Eb·Ec·Ed·R)SH는 done 처리했고 명령·Git 원형을 선보존한 뒤 정확 정리한다.

## Stage4ev — 학습 때 본 표면의 내용 선택·종료와 자유답 진단

**완료:** 실제 CPU와 세 모델768답·원형 검산을 모두 종료0으로 마쳤다([101 §319~323](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). 새 학습·CP0이며 아래 미실행 문구는 설계 당시 이력이다. 실제 학습 T0의 산수도 고정4/16·변형0/16으로 약해 새 표현만의 실패라는 해석은 불성립이다. 형식·Boolean 개선은 제한된 과제에 한정한다. 사용자 사용량 지시에 따라 새 구현/학습 없이 최종 인계한다.

### 왜·질문

결과101 §318의 TRAIN평가도 새 T2/T3 표현이어서 실제 학습 질문의 최종 fitting이 확인되지 않았다. 새 학습보다 같은 상태의 T0/T2와 TEST를 TF/자유답으로 먼저 나눈다. 상세 범위·비교대안·preflight는 [범위 감사](../handoff/audit/WIP_20261019_QUESTION_CONTENT_SCOPE.md)가 소유한다.

### 예측

학습 때 본 T0에서 더 맞으면 표면 전이 부족 가설이 살아 있고, T0도 틀리면 새 표현만의 문제로 축소할 수 없다. 낮은 평균 CE가 쉬운 구문/EOT에 가려진 내용 실패일 수 있지만 실제로 관측해야 한다. varied_balanced의 T0-CQ는 최종 가중치 기준 과거1회 노출이므로 final failure가 never learned의 증명은 아니다.

### 설계와 단계

| 단계 | 동작 | 상태 |
|---|---|---|
| Stage4ev0W | 동결 coded/wire·실제 TRAIN prefix membership·CPU 계약256표면 | 완료·101 §319, 모델0 |
| Stage4evWa | 원부모256 TF/첫logit/실제 자유답 | 완료·101 §320 |
| Stage4evWb | fixed_last256, 학습 T0-CQ4회 이력 | 완료·101 §321 |
| Stage4evWc | varied_balanced256, T0-CQ1회 이력 | 완료·101 §322 |
| Stage4evR |768원형·토큰/본문·정답·가족별 content/EOT·paired T0/T2 검산 | 완료·101 §323 |

split별 가족8query·KO/EN×T0/T2·CQ 고정이며 lookup/JSON은 부모 전체를 보존한다. 기존 코호트의 ID로 고르고 결과별 표본 교체는 하지 않는다. 부모와 학생의 학습 이력은 다르며 fixed_last/varied_balanced는 표현·위치 노출도 다르므로 두 모델 차이를 단일 효과로 분해하지 않는다.

### 측정·판정·비용

FP32-MATH의 content/EOT CE·모든 TF target argmax·첫 gold rank/tie/margin·EOT/EOS, prefix-only와 full-TF 첫 predictor, 기존 emit64 실제 응답을 연결한다. 자유생성에는 gold/candidate를 주지 않는다. JSON은 구문·키·payload와 전체 엄격 일치를 구분한다.

모든 TF target이 맞고 free IDs가 다르면 경로/수치 검토 flag로 남기며 바로 구현 오류라고 부르지 않는다. 모델 오답을 technical gate 오류로 만들지 않고 이전 원답도 보존한다. 새 학습/CP0이며 old-split TEST는 탐색 진단이지 새로운 blind benchmark가 아니다.

CPU≤300초, 각 GPU≤600초·합계5~10분 추정에 모델 간 유휴는 별도다. 최종 권한20일17시 전에1시간 기록 예약을 둔다. 현재75M×4epoch·micro8×accum16·checkpoint-on 본목표는 변경하지 않는다.

### 실행·한계·이력

드라이버·회귀와 SH5개를 작성했고 ROOT의 가드 CPU모의46개가 통과했다. 실제 CPU준비·모델은 아직 미실행이며 전수 정적과 동결 커밋 뒤 실행한다. 새 source projection만 검증하므로 원래 HF/보호 원천을 새로 감사했다고 주장하지 않는다. TF는 logged BF16 training CE 재현이 아니라 최종 가중치의 FP32 진단이다.

- `run_P106B_Stage4ev0W_content_probe_cpu.sh` — prepare, worker 상한300초.
- `run_P106B_Stage4evWa_parent_content_probe.sh` — evaluate parent, worker 상한600초.
- `run_P106B_Stage4evWb_fixed_last_content_probe.sh` — evaluate fixed_last, worker 상한600초.
- `run_P106B_Stage4evWc_varied_balanced_content_probe.sh` — evaluate varied_balanced, worker 상한600초.
- `run_P106B_Stage4evR_content_probe_readback.sh` — readback, worker 상한600초.

공개 진입점은 회귀→선결→본단계이며 각 worker 시간상한과 전체 wrapper 소요를 구분한다. 중첩/누락된 원형과 실패 활동은 통과로 바꾸지 않고, 완료 활동도 OS 종료 증거를 대신하지 않는다. ROOT가 실제 raw footer·pipeline returncode를 별도 확인한다.

2026-10-19 설계 당시: 총괄이 TF-only·TF+fresh768·TF+일부옛응답재사용을 비교하여 새768회수를 선택했다. 이후 실제 CPU는 아래와 같이 완료했고 모델은 미실행이다.

**실제 CPU 완료:** 16:21:17~16:21:38KST 회귀46/선결/prepare 모두0, worker5.869562초·모델/CUDA0이다([101 §319](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)). 256표면/content1032/EOT256·최대prompt69를 동결했고 정확한 TRAIN T0 노출은 fixed_last4회/varied_balanced1회, 다른 표면0과 첫 target/owner 충돌0이다. 이는 검사한8개 pass의 기술 결합이며 fitting/전이 예측은 실제 모델 뒤에만 대조한다.

## 2026-10-19 후속 Stage4ew — 내용 평균 P와 토큰 평균의 통제 대조

### 1. 왜

[101 §319~323](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)의 학습 표면 산수도0~4/16이며 최초 생성 경로의 불일치는 관측하지 못했다. 사용자에게 문헌 채택·부모/무부모·자료와영어의 한계를 먼저 설명했고, 그 설명 뒤 새 주도 CPU/GPU를2026-10-20 17시KST까지 허가받았다. [문헌08 §19~24](../docs/methods/08_paper_review2.md)의 P를 실제로 구현하되 과거 네팔은 수정하지 않는다.

### 2. 질문과 변경축

같은 varied_balanced 교과·순서·네pass·부모·seed·optimizer·native windows에서 내용 위치 가중만 바꾸면 실제 내용 선택이 개선되는가? 새 아키텍처 head·MTP·재귀·토크나이저·자료를 섞지 않는다. 부모를 버린 같은 SFT의 기존실패를 그대로 재실행하지 않으며, 초기화별 기초교육은 별도 설계다.

업데이트128대화·16micro에서 대화별 content CE합/수 C_i,c_i, 전체content N_C, EOT합 E/수 N_E, N=N_C+N_E, content가있는대화수 B_+를 사용한다.

```text
token   = (sum_i C_i + E) / N + native_CE_sum / 8192
content = N_C/(N*B_+) * sum_{c_i>0}(C_i/c_i) + E/N + native_CE_sum/8192
```

각 EOT 위치의 계수1/N과 총content계수N_C/N을 보존한다. 길이와 연관된 과제·언어의 비중, 전체gradient·clip·EOT어휘행gradient까지 동일한 것은 아니다. C2의 무시된 옛오답은 owner가양수여도 계속 무시한다. 여러assistantturn은한대화로묶고 EOT-only와전무지도update를구분한다. 이수식은총괄의통제설계이며특정논문식의그대로재현이나최적계수주장이아니다.

### 3. 예측·반증

짧은 정답의 내용fitting이 약한 조건에서 P가 산수·대상 선택을 도울 수 있다. 반대로 길이와과제난도는같지않아 자연QA나 JSON을 악화시키고 gradient 방향/망각만 바꿀 수도 있다. 학습손실이나 종료만 좋아지고 실제첫답이그대로면 내용개선 가설을 지지하지 않는다. seed1·이미모니터한코호트이며 통계적우위나일반지능승격을자동선언하지않는다.

### 4. 단계·예산·선결

| 단계 | 내용 | 선결·비용 | 초기 상태 |
|---|---|---|---|
| Stage4ewW0 | 전체4pass/DEV·owner·128분모와 양policy 계수실물검산 | CPU상한600초·모델0 | 코드49회귀통과; 실물NOT_RUN |
| Stage4ewWa / Stage4ewWb | 같은부모 양팔각cost8·CP0 | W0·각GPU≤900초·직전5분유휴·큰CPU중지 | NOT_RUN |
| Stage4ewWc | 양cost의완료activity·원시8행·예상384와평가/기록예비 | 보수예측이stage6h·학습종료목표안에들어야함 | NOT_RUN |
| Stage4ewWd / Stage4ewWe | fresh parent에서양팔각384회·4pass | 양cost/예산완료·source/그룹불변 | NOT_RUN |
| Stage4ewWf / Stage4ewWg | 각같은1694실제첫답·native32 | 정확자기CP/실제tokenizer/completeactivity | NOT_RUN |
| Stage4ewWh | 총3388새실답·raw/token decode·paired 분모검산 | 양평가완료activity·원답manifest/SHA | NOT_RUN |

과거384회15분은앵커이지새구현실측예측이아니다. 무인입력0·기본최상위배치별공유회귀→선결→본단계→최종영수증. 전체stage작업자는6h이내,평가1200초/기록600초예비를두고절대마감은20일17시다. 새학습은14시이후열지않으며비용측정직전5분유휴를총괄/실행자가확인한다.

### 5. 측정·판정

정상종료와과학채택을분리한다. 실제pass마다행·source/target/owner/순서·EOT/내용·언어/lane의계수질량과update raw·gradient L2/clip·actual optimizer group을기록한다. 한micro의평균을단순평균하거나 weighted를다시16으로나누지않는다.

같은FP32-MATH greedy0/topk1/KV-on/MTP-off/max64의첫답을비교하고 coded 산수/조회/Boolean/JSON·자연alias·산수canary·사용자질문을각분모로분리한다. 원어휘head와정답/후보미제공을유지한다. 자연주석EM은의미정답확정이아니고 native32는전체언어보존이아니다. 전체TF가아닌free응답을실제로회수한다.

별도새분모의TRAIN표면진단이나실제멀티턴/bench를추가할때는그계보를따로적는다. 미세한차이를승자·Falcon동급으로선언하지않고 긍정/퇴행문항과단일seed한계를함께읽는다. 보정/일반대화확대의선택은이실제결과와남은시간에따른후속판단이다.

### 6. 자료·재현·보존

부모는dense_chat32_p090b_s1337의같은373MB파일/coreE854…이고, m8/a16/seq1024/ckptON/compiledefault·Adam5e-5/Muon2e-4·WD0·clip1을유지한다. SFT의50,331,648패딩슬롯을실입력으로세지않는다. 원래varied_balanced의실제SFTx8,208,652·assistant302,656·별도native3,145,728은예상동일노출이며새source소비때다시검산한다. SFT4pass는기존승인된반복정책이고 native는TRAIN597.995M중동일3072창만읽어2배풀정책을우회하지않는다.

새태그 `p106b_content_recovery_v1_s1337` 아래 부모/기존corpus를읽기재사용하며덮어쓰지않는다. 생성참조는data_cache, raw응답은runs/eval, 작은수치·SHA/학습events는test_result/evidence, 원로그는test_result/101_log로분리한다. 파일당20MB미만,raw/가중치/원문은Git제외다.

- `run_P106B_Stage4ewW0_content_objective_cpu.sh` — `--mode prepare --max-wall-sec 600 --execute`.
- `run_P106B_Stage4ewWa_token_cost8.sh` — `--mode cost --arm token --max-wall-sec 900 --execute`.
- `run_P106B_Stage4ewWb_content_cost8.sh` — `--mode cost --arm content --max-wall-sec 900 --execute`.
- `run_P106B_Stage4ewWc_content_objective_budget.sh` — `--mode budget --max-wall-sec 600 --execute`.
- `run_P106B_Stage4ewWd_token_train384.sh` — `--mode train --arm token --max-wall-sec 3600 --execute`.
- `run_P106B_Stage4ewWe_content_train384.sh` — `--mode train --arm content --max-wall-sec 3600 --execute`.
- `run_P106B_Stage4ewWf_token_actual_answers.sh` — `--mode evaluate --arm token --max-wall-sec 1800 --execute`.
- `run_P106B_Stage4ewWg_content_actual_answers.sh` — `--mode evaluate --arm content --max-wall-sec 1800 --execute`.
- `run_P106B_Stage4ewWh_content_pair_readback.sh` — `--mode readback --max-wall-sec 600 --execute`.

### 7. 현재 구현·한계·이력

새순수helper/driver와49개CPU회귀가통과했다. 실제자산·모델·GPU는아직NOT_RUN이며전수정적과동결커밋뒤실물W0부터회수한다. 기존53/67원로그나19일오전44팔을새P학습의증거로합산하지않는다.

본문rawtoken복사의별도CPU128검토에서는첫정답ID지원20/128과문자oracle106/128을구분했다. 단순혼합학습을먼저확대하지않고기존저장spanhead의실제추출readout을더작은후보로검토한다. 이구조/기초교육/부분일반대화는설계확정뒤별도단계로등록하며현재P에몰래추가하지않는다.

### 실제 CPU 이력 — 2026-10-19 20:31KST

[101 §324](../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)에서 W0를 회귀49/선결/본단계 모두0으로 완료했다. 실제4pass/DEV를 소비했고 pass마다 입력2,052,163x·지도75,664(내용56,912/EOT18,752)와 마스크를 보존했다. 원문 복사/모델/학습/CP0, 다음은 전체 스모크 뒤 단독 cost8이다. 작성 당시 NOT_RUN 표는 역사 기록이며 현재 완료는 이 절과 결과§324가 소유한다. 예측한 사전 분모 검산은 성립했고 실제 내용 개선은 아직 미확인이다.

## 2026-10-19 후속 Stage4ex — 보존된 질문 조건 span head의 실제 추출 출력

### 1. 목적·범위

이전에 학습한 `p106b_grounded_span_exec_v3_s1337:span03`의 본체와 **그 모델 자신의** rank64 head를 함께 읽는다. 예전 보조 head는 학습 loss에만 사용했고 실제 답은 어휘 head에서만 생성했다. 이번에는 같은 prefix에서 어휘 생성과 원문 span 추출을 별도 출력으로 비교하여 대상 선택 실패와 어휘 렌더링 실패의 관측을 보완한다. 새학습·CP저장0이며 제품 생성/기본값·기존 원형 수정0이다.

raw token-copy는 현재128문항에서 첫 gold token ID가 source bank에 없는108건이 있었으므로 즉시 혼합하지 않는다. 이는 문자로 답을 추출할 수 없다는 뜻이 아니다. 새 helper는 원래 token offsets로 선택한 원문 범위와 outer whitespace trim만 반환한다. 조사·문장부호를 임의로 제거하지 않는다.

### 2. 가설·반대 위험

질문 조건 head가 올바른 본문 위치를 알고 어휘 head만 답을 잘못 만든다면 추출 EM이 상대적으로 높을 수 있다. 반대로 기존 head의 DEV 양경계 정확도가 낮았으므로 둘 다 실패할 가능성도 크다. oracle 위치·정답을 주고 얻은 span 정확도를 head 능력으로 세지 않는다. head에 제한된 source range를 주므로 이 결과는 **extractive readout 비교**이지 자유 대화/일반 지능 개선이 아니다.

### 3. 조건·입력과 누설 통제

- 고정 CP SHA `E3D632CE40B549B8FC3384294850472EFEFCED8392B09DCF35FEEFF0D52B1446`; v3 자기 학습 report/source/code/토크나이저를 실제 검산한다.
- 본체·head 전후 SHA/상태 불변, FP32-MATH/no-grad/eval. 어휘 생성은 greedy0/top-k1/KV-on/max64, head는 answer-free 전체 prefix의 no-KV hidden만 읽는다.
- TRAIN 자연QA는 답을 보기 전 태그해시로 KO64/EN64, DEV/TEST는 자연QA 각256 전량: 총640질문. replay는 포함하지 않는다. TRAIN 노출과 DEV/TEST 성적은 따로 보고한다.
- 실제 inference API 인자는 prefix와 원래 선언 reference 범위뿐이다. gold/답위치/labels/locations를 주지 않는다. gold는 출력 이후 별도 채점에만 사용한다.
- 정책1 independent: start/end 독립 argmax, 끝이 앞이면 INVALID로 남긴다. 정책2 valid_joint: start≤end 전체 쌍에서 점수합 최대, gold 길이 제한 없음. 둘을 미리 고정하고 사후 좋은 정책만 남기지 않는다.
- 원래 source의 정확24word 분할 검산과 한영 번역의 미감사 한계는 유지한다.

### 4. 단계·비용·선결

| 단계 | 수행 | 선결·상한 | 작성 시 상태 |
|---|---|---|---|
| Stage4exW0 | 새 helper/driver 회귀·실물 source/CP byte SHA·640 prefix/bank 동결 | CPU≤600초, 모델0·새 namespace만 | NOT_RUN |
| Stage4exWa | 같은 자기 본체의 어휘640답과 두 추출정책 | W0 완료·GPU≤1200초·같은 source/code·activity 종료 | NOT_RUN |
| Stage4exWb | raw scores/bank/원문/어휘 token decode·분모 독립 검산 | 실제완료 activity·manifest/SHA·CPU≤600초 | NOT_RUN |

총 활동 상한2400초, 승인 종료20일17시보다600초 기록 예비를 남긴다. 새 모델 학습비용은0, head196608 FP32인자는0.75MiB이며 이 수치를 모델 전체 상주/실측 peak로 대체하지 않는다. 실제 peak/속도는 이 진단에서 함께 기록하되 benchmark는 아니다.

### 5. 판정

소형 회귀/원형·기술 closure는 의미 정확성의 보증이 아니다. 언어·분할별 어휘 EM/token-F1, 두 추출 EM/F1·역순/범위·조사/공백 경계 오류, 동일 질문 대응표·실제 표본을 보고한다. 새학습0인 구조적 readout의 효과로만 해석한다. 학습 때 본 source 성적을 미학습 일반화로 합치거나 Falcon 동등성으로 올리지 않는다.

### 6. 저장·재현

새 tag는 `p106b_span_readout_v1_s1337`이다. 참조는 data_cache, 실제 prompt/답/점수는 runs/eval, 작은 계약/집계는 test_result/evidence의 같은 tag에 저장한다. 전부 write-once·20MB 미만 샤드로 보존한다. SH는 입력대기 없이 회귀→선결→실행→최종판정을 출력한다. 기존 P 목적함수 대조와 소스/활동 namespace를 분리한다.

### 7. 실행 이력·예측 대조

계획 작성 시 순수 helper32회귀만 통과했고 실물 source/모델/새 답은 모두 NOT_RUN이다. 실제 source와 strict checkpoint를 검증한 후에만 다음 단계를 연다. 원래 음성·미사용 head 판정은 그대로 보존한다.
