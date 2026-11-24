# 6. 학습 품질·안정

2026-11-23 통합 P109C의 원문·교과 혼합에서 첫 실사용 정답은 0→4/16, FINAL200 실사용은 0→33/200이었다. 같은 원문의 인과 NLL은 0.370 높았고 Core6은 3.38%p 낮았다. 일상 답과 근거 교차가 약했던 원인 후보로 일반 교과의 학습 답 길이 제한과 노출 편중을 확인했다. 일반 교과 입장, 초기 응답 배율과 원문 표집을 각각 통제 대조한다. [결과109 §§120~126](../../test_result/109_20261119004016_P109-기존G4-방문-세정책-실제갱신.md#p109c-v2-common-answers-result)

2026-11-19 실제 Qwen ACTD를 같은 초기 dense14에 적용하자 STE·GSQ가 각각 8회 갱신했다. 사전 지정한 GSQ 일정에서 스케일은 744,447개 변했고 결정론적 삼진 코드 변경은 0이었다. AdamW의 8회 로짓 이동 상한 0.0016175에 비해 마스크와 활성 부호의 거리 4.6이 컸다. 장치 최고는 STE 7.74 GB, GSQ 12.37 GB였다. 현재 조건에서 GSQ 우선 채택 근거는 확보하지 못했다. [결과101 §691](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md#p106b-gsq-actual-actd-start)

2026-11-13 [101§591~593](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md):
Qwen3.5 고정1024 scorer가원가변폭FP32음성을보존한채새prefix16/직접CE·순서검사를통과했고
공식cost192/576닫힘뒤full을수행중이다. 학생개선으로귀속하지않는다. ACTD는literal중복항·
고유보집합/전체분모·문자경계·owner의CPU60과정적어휘대응을구현했으나TRAIN128export에
top-k분포가없어실제캐시/학생학습/품질은미완이다. ALM을ACTD로재명명하지않는다.
추가CPU15/원형재준비는CE772를보존한각770위치를닫았다. 최근접미래28(max6)/left0을
구분하고raw22/config33호출누락은모델전CPU에서수리했다. 실제top128/93M미분은full뒤다.
exact legacy 입력확인도별도CPU3/봉인만끝났으며GPU전이다. 기존모델수치음성을취소하지않는다.

2026-11-13 [101§589~590](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md):
원GSQ Adam256/코드0과Lion66완료+67 ALM경계오류를 보존했다. 확률clip 없는 유한logit
log-tail CPU33 뒤 새 두 팔256을 완주했다. ordinary CE0은89/7986위치, 원검사 경계는0/57
chunk였고 새Lion의 최종 코드331845개가 바뀌었다. 이 수치 경로의 실제 필요성과 좌표 이동을
확인했지만 제품ALM/기본학습변경·답변품질·일상대화·본학습 채택은0이다.

2026-11-05 원장64의 연구용 GSQ 좌표/Lion 초안은 빈 시험0건을 실제12계약으로 보완했다.
뒤쪽 NaN/sparse gradient를 모든group 변경 전에 거부하는 방어를 넣고 기존objective12와24통과했다.
첫11중1실패 원로그는 결과101§588에 보존한다. 기본Muon·실제학생학습은 바꾸지 않았고
두256update GPU 기계진단과 추가검증 비용/품질은 NOT_RUN이다.

2026-11-05 [PAD 공유분석 대조](../research/20261105_P101A_PAD_공유분석_대조.md):
기존 crop128 BF16 eager ABBA1.6219256배와Muon update85/157 음성을 원JSON으로 재집계했다.
CE에서 이미 수행한 같은gradient/NS재생을 반복하지 않는다. PAD의 실제gradient쌍·현재자료 분모·compiled/MTP 비용은 별도 미완이며 예상 단축을 실측이나 기본채택으로 승격하지 않는다.

2026-11-05 [101§584·586](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md):
기존binary Gumbel/ALM을재사용한hard GSQ bridge는공유bank/embedding/head·같은microbatch
realization·checkpoint·분모·원복CPU12와전체모델기술3update를통과했다. clip전norm은양팔
100이상이고실제clip1이다. GSQ/STE시간1.349배·예약peak2.155배이며공통Adam lr1e-5는
categorical logit의본학습적합성검증이아니다. source/cursor·teacher품질과분리하고
본학습지능·양자화복원·40MBpacked배포는NOT_RUN으로유지한다.

발산 없이, 주어진 예산에서 더 좋은 최종 모델을 얻는 기법.

| 기법 | 상태 | 버전 | 작동원리(개선 기여) | 트레이드오프 | 특기 |
|---|---|---|---|---|---|
| **QK-norm** | ✅ | v5 | 어텐션 로짓 폭주 억제 → NaN 발산 해결 | 없음 | v4 300M 발산 주원인 해결. 1e-3까지 안정 |
| **NaN 가드** | ✅ | v5 | clip_grad_norm_이 non-finite면 그 스텝 스킵 | — | 가중치 영구 오염 방지(186분 낭비 방지) |
| **삼진 어닐링** | ✅ | v4~ | 학습 중 FP→삼진으로 매끄럽게 전환(배포=종료 시점) | — | train/test 불일치 없음. compile 안전 버퍼(v5) |
| **STE (AMP 안전)** | ✅ | v4~ | 삼진 backward를 weight 함수 윈도로 → grad 선형 | — | GradScaler·배치크기 불변 |
| **공유 MLP LR 1/√g** | ✅ | v4~ | 그룹이 g회 누적 → LR 보정 | — | weight decay는 미보정이 더 나았음 |
| **warmup 비율 수정** | ✅ | v5 | `max(5, min(steps//10,100))` | — | 짧은 런에서 warmup이 학습 절반 먹던 버그 |
| **LR 재조정 (기본 6e-4)** | ✅ | v5 | d=768·유효배치 131K에 2e-3은 과다 | — | 발산 원인이던 LR 하향 |
| **자동 LR 탐색** | 🧪 | v6 (`lrfind`) | range test(발산의 1/3) + grid 스윕 | — | grid는 warmup 램프 포함(cold-start 오판 방지) |
| **베스트 체크포인트** | ✅ | v6 | val 최저 시 `{name}_best.pt` 저장(raw 기준) | 디스크 | 스케일별 이름으로 클로버 방지 |
| **EMA / 체크포인트 병합** | 🧪 | v6 (`--ema`) | 가중치 지수평균 → 무료 품질 향상 | **decay 스케일 주의** | 주 val은 raw 보고, EMA는 부가 `[ema]`. **실측(P002 t_base): 0.999@2289스텝은 무효**(final ema 4.30≫raw 3.96). 짧은 런은 0.99 권장 |
| **WSD 스케줄** | ✅**측정**(결과 015) | v6 (`--sched wsd`) | 긴 plateau + 마지막 20% 감쇠 | dense 에서만 확인 | ★동일 스텝·동일 종료 LR 에서 cosine 대비 **−0.0755(6.3σ)**. plateau 체크포인트 재사용(도메인 분기). 근거 MiniCPM |
| **조기 종료** | 🧪 | v6 (`--early-stop`) | val 개선 없이 N회 → 종료 | 본 실행은 undertrained라 효과 제한 | LR/아키텍처 스윕용 |
| **train-val 모니터** | ✅ | v6 | 매 eval에 `val-train` 출력 | — | 과적합 신호 감시(현재는 undertraining) |
| **스케일별 체크포인트 이름** | ✅ | v6 | `{preset}_{data}_{tokens}_{arch}` | — | tiny 스모크가 300M을 덮어쓰던 버그 해결 |
| **★재현 노이즈 σ** | ✅**측정 완료** | — | bf16 커널 리덕션 순서 차이가 스텝마다 미세 편차 → 혼돈적 증폭 | **판정기준 `±0.07` 의 근거가 없다** | ★결과 007: 동일 설정 두 런(grad-ckpt on/off)이 250스텝에서 **0.11 nats** 벌어짐. **단 이 값은 σ 추정치가 아니다** — 두 런의 `grad_max` 가 10.79/35.38(우리 "10 이상=학습문제" 선 초과)로 **불안정 구간**이었다(2289스텝 런은 0.5~1.2). ★**결과 012: σ = 0.012**(`p6d` vs `p6d_s2`, 시드만 다름, \|Δ\|=0.0119). **2σ=0.024 < 0.07 이라 판정기준 유지.** 실무 분해능 0.024 미만은 구분 불가. 표본 2개 추정이므로 자릿수 판정으로만 사용 |
| **`grad_max` vs 인쇄 `\|g\|`** | ⚠️**함정** | v6 | 로그의 `\|g\|` 는 **10스텝 샘플**, json `grad_max` 는 warmup 이후 **전 스텝 최대** | 인쇄값만 보면 스파이크를 놓친다 | 결과 007: `sp_base` 인쇄 최대 4.51 vs 실제 `grad_max` **10.79**. **불안정 판정은 반드시 json `grad_max`** 로. `grad_peak_warmup` 은 warmup 구간 별도 최대 |
| **짧은 런의 스케줄 왜곡** | ⚠️**함정** | — | `warm = max(5, min(steps//10, 100))` → 250스텝이면 warmup 25뿐 | anneal 개시 시 LR 이 peak 근처 = 불안정 | 결과 007: 250스텝 런은 **속도 외 어떤 것도 긴 런으로 이전 불가**. 품질·안정성 판정 금지 |
| **cooldown-QAT 스케줄 정렬** | ⏸**검출 실패**(결과 015) | v6 (`--anneal-end`) | 완전삼진 도달 지점을 LR 감쇠 시작과 정렬 | 기본값(0.60)은 종전 동작 | **정렬 고유 기여 −0.0128(1.1σ) = 구분 불가.** 이득의 실체는 wsd 자체였다. 5번 표·P026 §단계5 참조 |
| **베스트 체크포인트로 런 비교** | 🚫**금지**(결과 015) | — | — | 주기 eval 50it vs 최종 eval 100it = **다른 추정량**, `best` 는 추첨 최소값이라 **하향 편향** | 결과 015 에서 `best` 로 읽으면 부호가 뒤집혔다. **판정은 `final` 끼리만.** `best.pt` 는 체크포인트 선택용으로만 |

## 2026-09-13 승인 연구의 품질 상태

| 계획 | 분리한 품질 질문 | 현재 상태 |
|---|---|---|
| [P091](../../test_plan/P091_Muon후반-적응적-블록-확장-재학습.md) | selector, local update, expansion을 한 팔에 섞지 않음 | 독립 primitive와 actual tiny-model mapping 계약 PASS([080 §6](../../test_result/080_20260913_P091-Stage0a-계약은-통과했고-실제-배선은-남았다.md#6-r0r1b-실제-tiny-model-mapping-게이트2026-09-19)); selector·학습·품질 `NOT_RUN` |
| [P092](../../test_plan/P092_Dynamic-Sparse-Training-연결희소성.md) | structural/ternary/effective sparsity와 rewiring을 분리 | 30M→100M sparse-dense loss 격차는 감소했으나 기존 중단선 미통과. Stage3Wb 실모델 mask +80.72MiB·decode 두 순서 열세로 현재 구현 속도/상주 가설 음성. 구 Stage3W 3시드 -cancel, 품질 300M·CPU 배포는 `NOT_RUN`([083 §12](../../test_result/083_20260913_P092-import-실패로-DST-계약은-미실행이다.md)) |
| [P098](../../test_plan/P098_재귀-token-embedding-재주입.md) | 재귀 hidden에 초기 token embedding을 cycle별로 재주입 | 3-seed 300M paired off−on +0.0015/+0.0001/+0.0002로 실무 자 0.0018 안. 단순 덧셈 default off 유지; concat adapter/다른 구조는 별도([091](../../test_result/091_20260923_P098-R2-초기임베딩-재주입은-3시드-실무-동급.md)) |
| [P025B](../../test_plan/P025B_2대4-동적희소-프리트레이닝-sparse-master.md) | dense-master와 sparse-master를 분리 | Stage0cW GPU primitive는 1.334~1.386× 후보지만 wall은 0.926~0.959×. sparse-master 학습·TLinear·품질은 `NOT_RUN`([082 §13](../../test_result/082_20260913_P025B-import-실패로-2대4-게이트는-미실행이다.md#13-stage0cw-whole-primitive2026-09-22--gpu-work는-양성-동기-wall은-음성)) |
| [P060B](../../test_plan/P060B_WSL-native-SDPA-GQA-융합백엔드-재개.md) | backend 속도/메모리와 full-val 품질을 분리 | 300M 3-seed on/off는 전부 실무 분해능 안이지만 방향 불일치. cache deploy 정합은 미통과라 품질 동급을 채택 PASS로 승격하지 않음([088 §10](../../test_result/088_20260919_P060B-forced-GQA는-문턱을-못-넘었지만-default는-살았다.md#31-최신-누적-판정-stage2wstage3w2026-09-22--품질은-실무상-동급-cache-배포-정합은-미통과)) |
| [P022C](../../test_plan/P022C_FP8-compute-shadow-precision-분리.md) | compute dtype와 shadow/write-back precision을 분리 | backend PASS. Wb delayed 한 형상 1.148×지만 NRMS 약3.77%·peak 증가로 전체 음성; weight-cache A~E Wc GPU `NOT_RUN`([081 §7~§8](../../test_result/081_20260913_P022C-FP8-backend는-통과했지만-학습이득은-미측정이다.md#7-stage0bwb-종료코드-교정-재실행2026-09-20--속도-한-행-양성수치와-메모리-음성)) |
| [P093](../../test_plan/P093_구조조건부-직접공유와-완화타잉.md) | exact 공유의 종결과 low-rank 완화 후보를 분리 | R1 회계 후보는 남았지만 모델 근사오차·학습·품질 `NOT_RUN`([086](../../test_result/086_20260919_P093-회계상-R1은-남고-D1은-고계산이다.md)) |
| [P095](../../test_plan/P095_Scout-1MiB-LTM-학습가능성.md) | primitive 인과 계약과 실제 기억 학습을 분리 | S0aL 계약 PASS; Transformer 통합·누출 방지·학습성·일반 LM 품질 `NOT_RUN`([087](../../test_result/087_20260919_P095-S0a-memory-primitive-계약은-통과했다.md)) |
| [P096](../../test_plan/P096_held-out-변별정보-난이도-가족편향-품질향상.md) | taxonomy coverage와 사람 의미·실측 변별력을 분리 | Q1b 기계 계약 PASS; 실문항·난이도 단조성·봉인 final `NOT_RUN`([085](../../test_result/085_20260919_P096-Q1b-taxonomy-계약은-통과했고-실문항은-남았다.md)) |

각 계획의 Stage0 PASS가 나오더라도 그것은 기능 가능성의 앞단일 뿐, 품질 채택 판정이 아니다.

## 2026-10-10 — 보정 선택과 규칙뷰 교육량

[P093B 결과103](../../test_result/103_20261010_P093B-MLP잔차와-삼진보정은-실행됐지만-복원문턱에-미달.md)에서 fitting 오차 감소와 새 활성값의 복원 악화가 함께 관측됐다. 과적합·LR·표현력은 원인 후보이지 확정 원인 하나가 아니다. 새 train/dev/test 분할에서 dev만으로 LR·중간 종료를 고르고 독립 test/whole CE/실제 원답은 최종 판독용으로 남긴다. 정상 LM의 best-val 비교 규약을 조용히 바꾸는 것이 아니라 별도 calibration 선택/최종평가 계약이다.

[P106D 결과104](../../test_result/104_20261010_P106D-규칙학습은-종료만-개선하고-교사는-라벨에-막혔다.md)의 각8업데이트·8/64는 조건변경 정답0이었다. old fixed의 무변경 교육과 view의 변경 교육도 교락됐다. 새4096행 양팔은 변경/유지 교육 비율·gold·actual x/target을 맞추고 micro8×accum16·ckptON·LR·4epoch를 유지해128업데이트를 준비한다. old 대비 자료량·구성도 바뀌므로 순수 update 수 인과를 주장하지 않는다. 알려진 oldval64는 train 제외 후 진단에만 재사용하며 fresh64와 분리 보고한다. 새 실물 교육 효과는 NOT_RUN이다.

## 2026-10-11 — local 과적합·자료 미완·정답/종료와 선호학습

[103 §8](../../test_result/103_20261010_P093B-MLP잔차와-삼진보정은-실행됐지만-복원문턱에-미달.md)의r8/16은dev중간점이늦은과적합보다좋았고r32/64는낮은LR250회를골랐지만독립test복원선은모두미달이다. NRMS개선과반복/지시능력은같은목적이아니다. 기존sigma/배치/Muon기본을변경하지않는다.

[104 §8](../../test_result/104_20261010_P106D-규칙학습은-종료만-개선하고-교사는-라벨에-막혔다.md)은3074행에서준비가막혀128update학생0이었다. 수리된실제재표현/key고정·길이bucket의새4096대조는여전히원micro8×accum16/ckptON/LR/4epoch다. [08 §10](08_paper_review2.md)의정답·종료SFT/ORPO 우선후보는무학습A결과이후범위결정이며새손실·pair학습은미구현이다. 정상복사·code·JSON·uniqueanswer보호와별도dev/test·망각검증을선결로둔다.

## 2026-10-11 후속 — 표현 관찰은 손실/학습 개입이 아니다

[103 §10](../../test_result/103_20261010_P093B-MLP잔차와-삼진보정은-실행됐지만-복원문턱에-미달.md)의실물48forward는새손실/학습0이다. 부모/shared/r64같은8입력의cosine/covrank는작은차이였으며전면붕괴가아니지만반복의인과는미확정이다. ORPO/SFT·표현/SimCTG 우선순위는보존하고현재micro8×accum16/ckptON/4epoch를변경하지않는다. 앞으로실제cache/decoder A와정상복사·긴답·언어보존대조를확인한뒤학습범위를정한다.
## 2026-10-11 재감사 — 실제 반복선택 관측과 수치정합은 별도

[103 §11~§12](../../test_result/103_20261010_P093B-MLP잔차와-삼진보정은-실행됐지만-복원문턱에-미달.md)의24답/2186step은학습0이고실제copy선호강화·EOS감소와KV불변/16층변화를측정했다. cached/동일prefix uncached6argmax차이는낮은margin에서관측돼기술8로보존한다. 구현vsBF16/backend 원인은아직분리하지못했다.
원형답안을새SFT의정답/선호쌍으로자동승격하지않고정상반복보호·후행판독을유지한다. 표현의시간수렴은인과나새훈련목적의양성증거가아니다. ORPO/SFT·SimCTG의선택과실행권한은별개며이번모델진단권한은종료했다.
## 2026-10-12 — 국소 인과 개입은 학습 효과가 아니다

[103 §13](../../test_result/103_20261010_P093B-MLP잔차와-삼진보정은-실행됐지만-복원문턱에-미달.md)의이력/MLP/상태/R2/precision 개입은564행·26.079초(별도영공간통제포함)의무학습진단이다. 이력이다음반복선호에영향을줬고cosine이필요조건은아닌국소반례를얻었지만정상SFT 양성대조·학생전후효과는없다. 단순표현유사도패널티를현재교육에자동적용하지않는다.
ORPO/SFT·SimCTG후속은별도feedback-dev/normal-copy/유일답 보호·실제token/update·언어능력보존을맞춘실험이필요하다. 현재micro8×accum16/ckptON·4epoch와75M/300M 목표는변경하지않았다.


## 2026-10-12 — 무부모와 계속학습의 MTP 효과 대조

새 [P101A](../../test_plan/P101A_M0-U2-QK-MTP-기능계약.md)는 scratch/parent 각각의 초기 본체 지문을 맞춘 NTP/MTP 네 팔이다. assistant의 같은 턴 안 horizon2/3/4만 지도하며 사용자·다음턴·PAD는 제외한다. 한글/영어·QA/JSON/멀티턴 자료, main val·실제 답·형식·종료·같은 native crop 언어손실을 보고한다. aux CE 감소만으로 지능 향상을 판정하지 않는다. 약32M/팔의 무부모 SFT가 일반 언어능력을 확보한다는 보장은 없고 기존75M×4epoch 목표를 대체하지 않는다. 새로운 조건의 sigma는 미측정이며 구 CPT의 자를 복사하지 않는다. [092 §10](../../test_result/092_20260925_P100-정성한계-P101A-M0-이식문턱실패.md)의 CPU 검증과 실제 학습효과는 별개다.

## 2026-10-13 — SFT 손실 감소와 보존 실패의 동시 기록

[092 §11](../../test_result/092_20260925_P100-정성한계-P101A-M0-이식문턱실패.md)의MTP finalCE 방향은한seed관측이고parentbestepoch2는NTP가더낮다. 부모의원문32crop CE악화와parentMTPgrad_max>10을보존한다. [104 §9](../../test_result/104_20261010_P106D-규칙학습은-종료만-개선하고-교사는-라벨에-막혔다.md)의128업데이트도종료/절차형답개선과native악화를함께본다. 같은8M/부모/NTP1epoch의jointLR scale1/.1 승인대조로이동량영향을가르며75M×4 본교육설정은불변이다.

## 2026-10-14 — LR 보존과 지시 과제 학습은 서로 다른 축

[092 §12](../../test_result/092_20260925_P100-정성한계-P101A-M0-이식문턱실패.md)의같은8M1epoch lower jointLR은native망각을줄였지만엄격첫답을회복하지못했다.
[101 §96~§97](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)의별도작은문맥/재질문course에서는실제코드첫답이개선됐으나계산갱신·일반8문항·native보존은미달한다.
데이터/평가/노출규모가다르므로두연구의차이를LR단독이득으로빼지않는다.
동일작은course의MTP는aux gradient가실제로흘렀지만한문항이득과더큰native대가를함께본다.
SFT val최저시점·초기포함gradmax·clip1·실제x/assistant targets와padding을별도로공개한다.

2026-10-14 후속 [101 §102](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md): 같은8192/4pass의 high/middle은39개 코드첫답과25개 자유재질문·12개 실제 대화턴을 별도 채점했다. high의 epoch4 val악화와 native CE 상승은 사전계획대로 수행한 결과로 보존한다. 개발24의 재측정과 새 독립평가를 구분하며, 본75M×4·원배치를 바꾸거나 MTP/재귀/폭을 한 팔에 섞지 않는다.

## 2026-10-14 후속 — 낮은 SFT 손실과 올바른 답은 다른 관찰

[101 §108~§110](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)의 source계열은 각32회 실제학습·마스크/whole-update 분모를검산했다.
SFTval 감소와 rawpreclip 큰값·원native32crop 악화·일반지문 미회복을 함께보존한다.
본문보조 목적은 일부보존 방향일뿐 기본채택하지 않으며, 자연형식팔의 자체val은 입력이달라 기존CE와직접순위화하지 않는다.
문자일치가낮아도 source핵심을맞힌재표현은 별도로읽고, 같은문자여도잘못된source답의현실정답을보장하지않는다.
common256 원답의 종료key 집계결함은 원형/codeGit을보존한새CPU readback으로 정정했고 실제모델출력을 다시쓰지않았다.

2026-10-14 추가: [101 §112](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)의64표본·32개발답·전체512를구분했다. 값계약/4view/root일관성·첫값휴리스틱을함께집계해상수출력의50%를내용이해로승격하지않는다. 자료/학습량교락·clip전큰값·native악화와미측정통계자를보존한다.

### 2026-11-18 두 optimizer의 명시 loss-scaling 수치 부품

[107§19](../../test_result/107_20261027131747_P107-가시성과-shift는-검산됐고-학습효과는-미확인.md#p107-scaled-optimizer-group-cpu)은 설치torch2.10에서 별도CPU14로 누적/unscale/clip·전역overflow skip과 fresh scaler state를 검증했다. 일반optimizer 예외를 원복하는 거래는 아니다. 작은 합성MSE/parameter 검증이며 BF16의 필수조건·Native 품질/속도나전체훈련재개로 승격하지 않는다. P107 source/policy/schedule의 skip 규약은 아직 별도다.

### 2026-11-18 P107 선택 scaler와 소비그룹 규약

[107§20](../../test_result/107_20261027131747_P107-가시성과-shift는-검산됐고-학습효과는-미확인.md#p107-scaled-trainer-consumed-group-cpu)은 명시factory/V3·V4·consume-group 규약을 CPU51으로 검증했다. 유한loss 관측그룹의 source/policy/schedule cursor와 실제optimizer 적용/skip을 구분하며 None 세모드의 옛 state해시는 유지했다. 실제Native/BF16-CUDA/Muon/대형교사·75M·품질/가속은 미실행이다. 이전의 scaler 접점 전체미구현은 이제 당시상태이며 실제GPU 입장은 여전히 별도다.

### 2026-11-18 P107 제한 인덱스 source

[107§21](../../test_result/107_20261027131747_P107-가시성과-shift는-검산됐고-학습효과는-미확인.md#p107-indexed-document-source-cpu)은 새offset source의 상주형 동일추출/RNG·작은학습기 재개 CPU15를 닫았다. 기존13source/defaults불변이다.1048576합성 token/4233618B 파일에서 record metadata69890B·최대 raw16538B/문서4096token·4읽기66150B이며 전체토큰payload를 인덱스에 보관하지 않는다. 이는 RSS/가속 실측이나 실제75M/언어품질이 아니다. startup 전체검증·O(문서수)메타데이터·random I/O 비용과 별도 source schema를 기록한다.

### 2026-11-18 source 이름과 실제 근거 문맥

[101§640](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md#p106b-existing-hotpot-family-context-review)에서원HotpotQA의문맥구조와달리로컬Aya6표본은질문/정답뿐이었다. 기존무손실함수24unit보존은참이지만근거문맥·원root/권리를만들지않는다. 원형그대로6개는HOLD이며전체가족의오류율이나독립질문수·75M가용량으로일반화하지않는다.

### 2026-11-18 dataset task label과 본문 역할

[101§641](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md#p106b-existing-soda-narrative-role-review)의SODA2개는dialogue메타데이터와달리서사생성요청/가상답이었다. 바깥user/assistant의lossless8unit검증은등장인물의발화자배열/현실사실검증이아니다. 이고정표본은서사조건/원root입장HOLD이며전체가족/75M가용량으로일반화하지않는다.

### 2026-11-18 서사재구성과엄격입력근거QA의계약

[101§643](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md#p106b-soda-plain-task-and-input-grounding-review)의SODA6원문에서세형식을구분했고명시대화2개를확인했다.4서사답의일부세부는입력대화에명시되지않아엄격근거QA정답으로자동승격하지않는다. 원래서사재구성의오류판정이아니며원답은보존한다. input-only 대화view는세안/권한/원root·rights 입장과별도CPU검증뒤에만준비하며품질효과는미실행이다.

### 2026-11-18 입력대화근거와옛서사답의분리

[101§644](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md#p106b-soda-named-input-prefix-cpu)의새순수view는known suffix앞입력prefix만근거text로반환하며raw/old target은보존한다. CPU12+저장실물2에서정확span·target비간섭/거부를확인했다. trace의원row해시는old target변경시달라지며근거hash와구분한다. 내부speaker/원root/rights·token예산·실제교사/75M/학생품질·기본채택은미검증이다.

### 2026-11-18 원질문파생계보와입력근거/학생wire의분리

[101§645](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md#p106b-soda-parent-evidence-student-wire-cpu)는기존first-user 정규화해시를원질문에서먼저보존하고교사payload/학생참고자료에는명시대화입력만사용했다. CPU11·원문2의작성wire12에서실제chat32 전체최대485토큰·답변/EOT/턴mask와초과거부를확인했다. 두key는달라도이두사례의제안TRAIN분할은같았다. 원SODA root/권리·실제corpus split/편입·생산/교사응답/75M/품질을검증한것은아니다.

### 2026-11-18 여러표현창과명시원천경계

[101§646](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md#p106b-feature-multiwindow-source-boundary-cpu)의새coordinator는committed feature record의before/after 원천경계를여러창에연결한다. CPU19의실제PCG64 합성adapter/중단·prefix·quota·bytes가통과했고382파일을독립검산했다. 강제3x4MiB/3072표현행/618선택위치는언어학습토큰이아니다. 외부교사호출 exactly-once·Native RNG/전체model-optimizer 재개·실제8h/75M·권리/품질/기본채택은미검증이다.

### 2026-11-18 CE전체와KD하위집합의별도분모

[101§647](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md#p106b-complete-ce-bounded-kd-group-cpu)의A CPU14는원CE전체순서를유지하고KD 하위집합만추가한다. CE-only 앞/중간/끝행을포함한CE5/15와KD2/7·45변수독립미분최대오차5.55e-17을확인했다. 기존Native128/772비용은이미전체CE를보존했으며이신규경로와구분한다. B전체optimizer/scaler/RNG 재개·실제Native/75M/권리/품질은미완이다.

### 2026-11-18 작은CPU의전체경계와공개scaler상태이관

[101§648](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md#p106b-tiny-cpu-complete-dskd-training-boundary)의새CPU owner는고정scaler원본을바꾸지않고검증된공개scalar/counter를새callback수/활성optimizer binding으로명시이관한다. A14+B10은전체model/buffer/optimizer/source/세RNG·새객체재개와zero-KD투영보존/overflow/dirty복구를확인했다. 입력소비와applied/skip을구분하며67호출은전체수치시험의실제optimizer호출이지언어학습업데이트가아니다. 실제Native/teacher/생산LR/75M/권리/품질은미완이다.

### 2026-11-18 소비그룹LR의별도소유

[101§649](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md#p106b-consumed-group-lr-schedule-cpu)는기존고정LR/scaler를바꾸지않는명시subclass다. canonical LR 원식과소비시계를공유하며overflow도진행하고zero-KD투영은이전LR까지보존한다. 새10수치검사는수동비스케일업데이트/완전재개exact·old20불변을닫았다. 새schema는과거CP를이관하지않는다. 실제Native/provider/교사75M/권리/품질은미완이다.

[원실험미분/실제provider검토](../research/20261118_DSKD_actual_gradient_limits_review.md)는본체33.315배/−0.161과전체32.856배/−0.171을구분한다. 원scalar의국소Euclidean내적계산은실제Muon/AdamW·유한업데이트·품질보장이아니며생산계수미선택이다. 원진단micro8과새CPU한행callback의실제연결이남아있다. 새동적실험/원로그추가0이다.

### 2026-11-18 불균형평가의정확도와분별력분리

[108§72](../../test_result/108_20261104190525_P108-방향수리는-실행됐지만-정답은-늘지-않았다.md#p108b-boolq-gain-decomposition)는원PRIMARY/Holm11을유지하고동일3270점수를사후분해했다. +74정확도는주로yes방향전환이었고균형정확도와순위AUC의증거를따로남겼다. 사후macro-F1/AUC를새PRIMARY/사전선택기준으로바꾸지않고다시학습/threshold fitting에쓰지않는다. 새유의성/인과/범용품질주장0이다.

### 2026-11-18 과제별PRIMARY를보존한선택지진단

[108§73](../../test_result/108_20261104190525_P108-방향수리는-실행됐지만-정답은-늘지-않았다.md#p108b-other-gains-stored-primary-decomposition)는Winogrande의common continuation과gold index, HellaSwag원선택지문자분모를구분했다. 균형지표/순위의작은관측증가와기존비유의추가효과를따로보존하며BoolQ진단을일반화하지않는다. 프로세스주소의직렬화표시4곳만detached view로대조했고원config/PRIMARY/점수는불변이다. v1실패/v2완료를모두기록하며새학습/모델선택/유의성0이다.

### 2026-11-18 관측field묶음에대한대응민감도

[108§74](../../test_result/108_20261104190525_P108-방향수리는-실행됐지만-정답은-늘지-않았다.md#p108b-observed-group-bootstrap-sensitivity)는결과비사용group census후7지표/100000대응군집bootstrap을고정했다. 묶음전체/양팔같은draw·변하는문항분모·weighted tie AUC와독립저장분포검산을확인했다. BoolQ정확도차이와macro-F1차이는반대부호구간이며균형/AUC·Hella구간은0을포함한다. 관측묶음의원root독립성/사후확증coverage를인증하지않으며원Holm11/야간0of33·새모델0을유지한다.

### 2026-11-18 같은microbatch의여러행과graph수명

[101§650](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md#p106b-causal-microbatch-frame-adapter-cpu)는행별loss수명이배치공통body/quant graph수명과다름을분리한다. 별도어댑터는한forward의마지막real행/KD조각까지retain하고그뒤다음forward를허용한다. 새작은CPU의FP64/FP32-dropout-checkpoint값/전체미분·원RNG와caught음성대조만검증했다. 원배치당1회대비조각backward횟수/전체비용·실제Native/source/private RNG/전체trainer-resume는별도이며성능채택을주장하지않는다.

### 2026-11-19 GSQ의 샘플링 로짓과 최적화 좌표

출발 Gumbel 로짓을 유지하면서 내부 좌표를 4,096으로 나누자 기존 실제 교사 조건의 8갱신에서 결정론적 코드 4,687,128개가 바뀌었다. 원 배율 1에서는 0개였다. 같은 기술 자료의 조기 코드 변경과 실제 배포 경로를 검증한 범위다. 응답은 동일 토큰을 반복했으며 정식 독립 품질과 장기 선택 붕괴를 확인해야 한다. [결과101 §694](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md#p106b-gsq-scaled-actd-native-deploy)
