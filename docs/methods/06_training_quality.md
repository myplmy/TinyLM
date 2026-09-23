# 6. 학습 품질·안정

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
| [P092](../../test_plan/P092_Dynamic-Sparse-Training-연결희소성.md) | structural/ternary/effective sparsity와 rewiring을 분리 | full trainer 30M/100M 8팔 exit0·skip0. 30M sparse 3팔 모두 사전 중단선 +0.15 초과, 100M 최선 dynamic50 dense gap +0.19656>+0.07. 30M dynamic50 grad_max 22.09 경보. Stage3 HOLD([083 §9](../../test_result/083_20260913_P092-import-실패로-DST-계약은-미실행이다.md)) |
| [P098](../../test_plan/P098_재귀-token-embedding-재주입.md) | 재귀 hidden에 초기 token embedding을 cycle별로 재주입 | 3-seed 300M paired off−on +0.0015/+0.0001/+0.0002로 실무 자 0.0018 안. 단순 덧셈 default off 유지; concat adapter/다른 구조는 별도([091](../../test_result/091_20260923_P098-R2-초기임베딩-재주입은-3시드-실무-동급.md)) |
| [P025B](../../test_plan/P025B_2대4-동적희소-프리트레이닝-sparse-master.md) | dense-master와 sparse-master를 분리 | Stage0cW GPU primitive는 1.334~1.386× 후보지만 wall은 0.926~0.959×. sparse-master 학습·TLinear·품질은 `NOT_RUN`([082 §13](../../test_result/082_20260913_P025B-import-실패로-2대4-게이트는-미실행이다.md#13-stage0cw-whole-primitive2026-09-22--gpu-work는-양성-동기-wall은-음성)) |
| [P060B](../../test_plan/P060B_WSL-native-SDPA-GQA-융합백엔드-재개.md) | backend 속도/메모리와 full-val 품질을 분리 | 300M 3-seed on/off는 전부 실무 분해능 안이지만 방향 불일치. cache deploy 정합은 미통과라 품질 동급을 채택 PASS로 승격하지 않음([088 §10](../../test_result/088_20260919_P060B-forced-GQA는-문턱을-못-넘었지만-default는-살았다.md#31-최신-누적-판정-stage2wstage3w2026-09-22--품질은-실무상-동급-cache-배포-정합은-미통과)) |
| [P022C](../../test_plan/P022C_FP8-compute-shadow-precision-분리.md) | compute dtype와 shadow/write-back precision을 분리 | backend PASS. Wb delayed 한 형상 1.148×지만 NRMS 약3.77%·peak 증가로 전체 음성; weight-cache A~E Wc GPU `NOT_RUN`([081 §7~§8](../../test_result/081_20260913_P022C-FP8-backend는-통과했지만-학습이득은-미측정이다.md#7-stage0bwb-종료코드-교정-재실행2026-09-20--속도-한-행-양성수치와-메모리-음성)) |
| [P093](../../test_plan/P093_구조조건부-직접공유와-완화타잉.md) | exact 공유의 종결과 low-rank 완화 후보를 분리 | R1 회계 후보는 남았지만 모델 근사오차·학습·품질 `NOT_RUN`([086](../../test_result/086_20260919_P093-회계상-R1은-남고-D1은-고계산이다.md)) |
| [P095](../../test_plan/P095_Scout-1MiB-LTM-학습가능성.md) | primitive 인과 계약과 실제 기억 학습을 분리 | S0aL 계약 PASS; Transformer 통합·누출 방지·학습성·일반 LM 품질 `NOT_RUN`([087](../../test_result/087_20260919_P095-S0a-memory-primitive-계약은-통과했다.md)) |
| [P096](../../test_plan/P096_held-out-변별정보-난이도-가족편향-품질향상.md) | taxonomy coverage와 사람 의미·실측 변별력을 분리 | Q1b 기계 계약 PASS; 실문항·난이도 단조성·봉인 final `NOT_RUN`([085](../../test_result/085_20260919_P096-Q1b-taxonomy-계약은-통과했고-실문항은-남았다.md)) |

각 계획의 Stage0 PASS가 나오더라도 그것은 기능 가능성의 앞단일 뿐, 품질 채택 판정이 아니다.
