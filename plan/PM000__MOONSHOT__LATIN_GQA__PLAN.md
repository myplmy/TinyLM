# PM000__MOONSHOT__LATIN_GQA — 반복 회차별 균형 GQA 재배선

> 상태: **Stage0·Stage0B·sparse34 동적 계약 PASS / 전체 smoke는 check_links 1건 RED / Stage1 HOLD**
> 브랜치: **`moonshot` 전용**
> 작성일: 2026-09-06
> 결과 문서: [`PM000__MOONSHOT__LATIN_GQA__RESULT.md`](../moonshot_result/PM000__MOONSHOT__LATIN_GQA__RESULT.md) — 품질 효과는 아직 미측정

## 0. 비혼합 원칙

이 계획은 일반 실험 계보와 분리한다.

- 계획서는 `plan/`, 배치는 `moonshot_batch/`, 실행 로그와 향후 결과 분석은
  `moonshot_result/`만 사용한다.
- 번호는 `PM000`, 예약 표식은 `__MOONSHOT__`, 필드 구분자는 `__`다.
- `test_plan/`, `test_result/`, `experiments.tsv`, 일반 `run_queue.bat`에는 등재하지 않는다.
- trainer가 공통 구현상 `runs/logs/`에 쓰는 JSON은 `_pm000__` 태그로 구분하고 일반
  `runs/registry.tsv`의 scan/backfill에서 제외한다. PM provenance는
  `moonshot_result/registry.tsv`에만 기록한다.
- `main`과 merge/rebase/cherry-pick/push를 시도하지 않는다.
- 나중에 충분한 성능 향상이 입증되더라도 이 브랜치를 합치는 것이 아니라, 사용자가 별도
  main 작업에서 증거와 필요한 변경만 다시 검토해 이식한다.
- AI는 이 계획의 `.bat`, 학습, 평가, 모델 로딩, torch 진단을 실행하지 않는다.
  실제 실행은 사용자가 `.bat`로만 수행한다.

## 1. 결론과 선택 이유

1차 검증 대상으로 **pass-dependent Latin GQA**를 선택한다.

첨부 분석은 어떤 미적용 수학 모듈도 40 MB급 TinyLM의 일반지능을 크게 올린다고 신뢰할
근거가 없다고 결론 내렸다. 따라서 PM000의 목적은 “대폭 향상”을 전제하는 것이 아니라,
추가 가중치와 KV 엔트리 없이 반복 계산에 서로 다른 연결 역할을 주는 가설을 가장 싼
형태로 반증 가능하게 시험하는 것이다.

후보 비교는 다음과 같다.

| 후보 | 장점 | 핵심 위험 | PM000 판단 |
|---|---|---|---|
| depth-RoPE + 입력 재주입 | 외부 반복모델 근거가 상대적으로 강함 | 신규성이 낮고 두 축이 동시에 바뀌어 귀속이 어려움 | 후속 양성 대조군 |
| **Latin GQA** | 가중치/KV 증가 0, 구현 범위 작음, R1 정확 동일 가능 | KV head 역할 특화를 깨뜨려 악화할 수 있음 | **선택** |
| PLMBC | 수학적 신규성과 구조 OOD 잠재력이 가장 큼 | 상태·커리큘럼·대조 모듈까지 필요해 첫 실험 귀속이 어려움 | PM001 후보 |
| PCAC | CSP 구조추론 잠재력 | 일반 문장·지시이행 전이 가능성이 더 낮음 | 합성 선결 뒤 검토 |

Latin GQA를 먼저 구현하면 재귀 회차 ID를 학습·prefill·cached decoding에 동일하게
전달하는 기반도 생긴다. 이 plumbing은 후속 moonshot에서 재사용할 수 있지만, PM000에서는
다른 모듈을 결합하지 않는다.

## 2. 가설과 수학적 정의

현재 GQA는 query head 그룹 `g`가 모든 재귀 통과에서 같은 KV head를 본다. KV head 수를
`H_kv`, 같은 실제 레이어를 방문한 회차를 0부터 세는 `t`라고 할 때 Latin 조건은 다음이다.

\[
KV_t(g) = (g+t) \bmod H_{kv}
\]

`H_kv=3`, `R=3`이면 각 query 그룹은 세 KV head를 정확히 한 번씩 사용한다.

비교 스케줄은 세 가지다.

| 스케줄 | 한 주기의 shift 순서 | 역할 |
|---|---|---|
| `fixed` | `0, 0, ...` | 기존 연결의 동시대조군 |
| `latin` | `0, 1, ..., H_kv-1` | 순서가 고정된 균형 순환 |
| `random` | `0` 뒤 비영(非零) shift의 seed별 결정적 순열 | 균형 자체와 Latin 순서의 귀속 분리 |

`random`은 전역 난수 상태를 소비하지 않는다. 같은 seed에서는 항상 같은 순열이고, 첫
회차는 반드시 shift 0이며, 한 주기 안에서 각 KV head를 정확히 한 번 사용한다.

### 주가설 H1

동일 파라미터·토큰·레이어 방문 수에서 `latin`이 `fixed`보다 clean full-val CE를 낮춘다.

### 기전가설 H2

이득이 단순한 무작위 교란이 아니라 균형 순서에서 오면 `latin`이 `random`보다 안정적이다.

### 반증가설 H0

고정 KV 역할을 깨뜨리는 비용이 더 커서 `latin`과 `random`이 모두 `fixed`보다 나쁘거나,
차이가 동일 조건의 학습 재현 노이즈보다 작다.

### 범위 제한

CE 한 지표의 개선, 한 seed의 개선, 합성문제 개선만으로 일반지능 향상이라 부르지 않는다.
PM000 1차 단계는 아키텍처 신호를 찾는 단계이며 제품 품질 판정이 아니다.

## 3. 구현 계약

### 3.1 단일 독립변수

한 실험 묶음 안에서는 `gqa_pass_schedule`만 `fixed/latin/random`으로 바꾼다. random 팔의
`gqa_pass_seed`만 순열을 정의하기 위해 다르다. 모델 초기화 seed, 데이터, 토큰 수, 배치,
optimizer, LR schedule, recurrence, CLA, checkpointing은 고정한다.

### 3.2 회차의 정의

`pass_id`는 KV owner의 방문 번호가 아니라 **각 실제 레이어 인덱스의 방문 번호**다.
CLA owner 번호를 쓰면 non-owner 레이어가 잘못된 회차를 받을 수 있으므로 금지한다.

### 3.3 정확성 불변식

1. 기본값 `fixed`에서는 K/V roll 텐서 연산을 수행하지 않는다.
2. R1에서 `latin`과 `random`의 첫 회차는 shift 0이므로 기존 출력과 정확히 같아야 한다.
3. K와 V에는 같은 shift를 적용하고 Q/O 가중치는 바꾸지 않는다.
4. rotate는 cache에 저장된 원본 K/V를 수정하지 않고 attention 소비 직전에만 적용한다.
5. 학습, full prefill, cached decoding이 같은 레이어별 회차 순서를 사용한다.
6. 파라미터 수, state-dict key, KV 엔트리 수는 `fixed`와 동일해야 한다.
7. `reuse_attn_on_dup`는 두 번째 통과 attention을 건너뛰어 처치가 사라지므로 non-fixed와
   함께 쓰면 즉시 거절한다.
8. non-fixed는 실제 GQA인 `n_q_heads > n_kv_heads > 1`에서만 허용한다.
9. PM000의 non-fixed 스케줄은 `repeat_mode=uniform`에서만 허용한다. block/progressive/inplace는
   레이어별 방문 수와 CLA KV 선택 의미가 달라 별도 계획 없이 일반화하지 않는다.
10. `torch.roll` 임시 텐서 때문에 activation/runtime peak와 latency가 늘 수 있다. “비용 0”은
   **가중치와 KV 저장량만 0**이라는 뜻이며 runtime 비용 0을 주장하지 않는다.

## 4. 영향 분석

| 영역 | 변경 | 위험 | 방어 |
|---|---|---|---|
| `tinylm/moonshot/pm000_latin_gqa.py` | 스케줄·검증·layer visit·K/V shift 정본 | 실험 코드가 core에 산재 | torch-free 단일 모듈 + 이식 manifest |
| `tinylm/config.py` | 스케줄·seed 필드와 정본 validation hook | checkpoint 재로드 검증 누락 | `__post_init__` + trainer 이중 검증 |
| `tinylm/cli.py` | 두 CLI 인자 전달 | 파싱만 되고 미사용 | call-kwargs 정적 게이트 + JSON 계약 |
| `tinylm/train/trainer.py` | config 적용·조합 거절·JSON 3필드 | 기본 경로 변형 | 기본 `fixed`, 명시 배너, smoke EXPECT |
| `tinylm/model/transformer.py` | 레이어별 방문 회차 전달 | CLA owner 회차와 혼동 | 별도 `layer_visits` 맵 |
| `tinylm/model/modules.py` | attention 직전 K/V roll | cache 오염·K/V 불일치 | 비파괴 roll, K/V 동시 적용 |
| cached decode | 매 토큰 forward마다 같은 schedule 재구성 | full/cached 불일치 | Stage0 수치 계약 |
| `torch.compile`/checkpoint | Python 회차 상수와 lambda capture | 회차 고정 오류 | pass_id 명시 capture + 사용자 smoke |
| 계측 | schedule/seed/order 기록 | 이름만 있고 축이 죽음 | `check_smoke.py` 필수값 + 실제 nontrivial GQA smoke |
| 배치/로그 | PM 전용 이름과 경로 | 일반 실험에 혼입 | branch/namespace 정적 가드 |

### 의도적으로 건드리지 않는 것

- 일반 실험 계획·결과·레지스트리와 큐
- 데이터셋 내용과 held-out 레코드
- optimizer, 양자화, KD, depth initialization
- 배포 packer와 KV dtype
- main 브랜치와 원격 저장소

## 5. 공통 실험 조건

Stage1과 Stage2의 세 팔은 아래 조건을 공유한다.

| 항목 | 값 | 이유 |
|---|---|---|
| preset / arch | `m100s8` / `dense` | 현재 32 MiB 계열의 얕은 dense 몸통 |
| GQA / CLA | 12 Q, 3 KV / `cla_group=2` | 실제 목표 구조 |
| data cache | `ko-en`, exact 600M | 600M full-val을 써 학습 데이터와 겹치는 300M eval을 피함 |
| 실제 학습량 | 763 steps = 100,007,936 tokens | 500-step 이하를 품질 판정에 쓰지 않음 |
| batch | micro 8, accum 16, seq 1024 | step당 131,072 tokens |
| optimizer/LR | AdamW, `1e-3`, WSD, anneal 0.80, decay 0.2 | 현재 표준 축 유지 |
| seed | model/data seed 1337 | 첫 matched triad |
| init/KD | scratch, no KD | main 체크포인트 반입 금지 및 귀속 단순화 |
| grad checkpoint | on | R3 안전 범위를 R2와 맞춤 |
| compile / CE | on / chunk 2048 | 현행 실행 경로 |

CLI의 `--tokens 600M`은 exact cache와 checkpoint namespace를 뜻한다. 실제 학습 토큰은
JSON의 `steps * eff_batch`가 정본이며 각 태그의 `t100`으로도 명시한다. 이렇게 해야 같은
`600M` clean full-val에서 checkpoint를 직접 찾을 수 있다.

scratch 조건은 기존 main 계열 성능 숫자와 직접 비교하지 않는다. PM000 내부의 matched
`fixed`만 유효한 기준선이다.

## 6. 단계와 실행 순서

코드 변경 뒤 첫 사용자 실행은 저장소 공통 동적 smoke인 `run_smoke_check.bat`다. 여기에
`dense × tinygqa(Q4/KV2) × CLA2 × R3 × compile × latin` 팔과 PM000 계약 진단이 포함된다.
smoke 결과는 `smoketest_logs/`에 남고 PM 성능 결과로 읽지 않는다. smoke가 통과한 뒤 아래
Stage0부터 별도로 기록한다.

### Stage0 — 동역학 계약 진단 — ✅ 완료

사용자 실행 배치:
`moonshot_batch/run_PM000__MOONSHOT__Stage0_contract.bat`

학습 없이 작은 실제 GQA 모델에서 다음을 검사한다.

1. fixed/latin/random 순열 정의와 seed 결정성
2. R1 fixed 대 latin 로짓의 exact equality
3. R3 latin이 실제로 출력을 바꾸는지
4. fixed/latin의 파라미터 수와 state-dict key 동일성
5. R3 latin full prefill 대 cached decoding 수치 일치
6. backward 후 gradient finite

하나라도 실패하면 Stage1을 실행하지 않는다. 이 단계의 loss는 품질 지표가 아니다.

2026-09-06 사용자 실행에서 이 Stage0는 여섯 계약 모두 PASS했다. 정확한 수치와 전체 smoke의
분리 판정은 [결과 문서](../moonshot_result/PM000__MOONSHOT__LATIN_GQA__RESULT.md)에 기록한다.

### Stage0B — 이식 경계 리팩터링 후 계약 재검증 — ✅ 완료

사용자 실행 배치:
`moonshot_batch/run_PM000__MOONSHOT__Stage0B_postrefactor.bat`

Stage0 뒤 PM000 알고리즘을 `tinylm/moonshot/pm000_latin_gqa.py`로 격리했으므로 원 Stage0
로그를 변경 후 소스의 증거로 재사용하지 않는다. 사용자가 최신 `run_smoke_check.bat`의 PM arm을
확인한 뒤 Stage0B를 실행한다. 같은 날 같은 Stage0 이름으로 로그를 이어 쓰지 않도록 새 stage
이름을 쓴다. Stage0B가 실패하면 Stage1을 실행하지 않는다.

2026-09-06 사용자 실행에서 Stage0B는 원 Stage0와 같은 여섯 계약을 모두 PASS했다.
`params=36,136`, `state keys=47`, R1 exact, R3 `max_abs_delta=6.521e-03`,
cached/full `max_abs=3.539e-08`, finite backward를 확인했다. 이는 wiring 증거이며
품질 증거가 아니다.

### Stage1 — R2 matched triad, 100M signal — ⏸ HOLD

사용자 실행 배치:
`moonshot_batch/run_PM000__MOONSHOT__Stage1_r2_signal.bat`

| 팔 | train repeat | schedule | schedule seed | tag 핵심 |
|---|---:|---|---:|---|
| A | 2.0 | fixed | 0 | `r20__gqafixed` |
| B | 2.0 | latin | 0 | `r20__gqalatin` |
| C | 2.0 | random | 17 | `r20__gqarandom` |

세 팔은 독립이므로 한 팔 실패가 나머지 팔 실행을 막지 않는다. 다만 실패 팔을 제외하고
승패를 확정하지 않는다.

### Stage1E — R2 deterministic paired full-val — ⏳ 미실행

사용자 실행 배치:
`moonshot_batch/run_PM000__MOONSHOT__Stage1E_r2_paired_eval.bat`

Stage1 세 checkpoint가 모두 생긴 뒤 실행한다. `--tokens 600M`과
`--match-train-repeat`를 사용한다. paired 비교는 이 세 checkpoint의 eval 노이즈를 줄일 뿐,
아키텍처의 학습 seed 노이즈를 제거하지 못한다.

### Stage2 — R3 완전 균형 주기, 100M signal — ⏳ 미실행

사용자 실행 배치:
`moonshot_batch/run_PM000__MOONSHOT__Stage2_r3_balance.bat`

Stage1/Stage1E에서 correctness·안정성·비정상 runtime 문제가 없음을 확인한 뒤 실행한다.
Stage1이 명백히 악화되거나 결함으로 끝나면 이 배치를 실행하지 않는다.

| 팔 | train repeat | schedule | schedule seed | 목적 |
|---|---:|---|---:|---|
| A | 3.0 | fixed | 0 | 동일 계산량 기준선 |
| B | 3.0 | latin | 0 | `H_kv=3` 전체 Latin 주기 |
| C | 3.0 | random | 17 | 전체 균형이되 순서만 seed별 순열 |

R3은 레이어 방문 수가 늘어난 별도 조건이다. R2 fixed와 R3 latin을 직접 비교해 Latin의
효과라고 귀속하지 않는다. R3 내부 triad만 1차 인과 비교다.

### Stage2E — R3 deterministic paired full-val — ⏳ 미실행

사용자 실행 배치:
`moonshot_batch/run_PM000__MOONSHOT__Stage2E_r3_paired_eval.bat`

Stage2 세 checkpoint가 모두 생긴 뒤 Stage1E와 같은 규약으로 평가한다.

### Stage3 — 300M·다중 seed 확인 — ⏳ **아직 배치 없음**

Stage1/2에서 non-fixed가 matched fixed를 명백히 이긴 경우에만 계획을 갱신하고 배치를 만든다.
후보 schedule 하나와 fixed를 300M에서 최소 3 seed로 비교한다. 지금 배치를 만들지 않는 이유는
선택될 repeat와 schedule seed가 Stage1/2 결과에 달려 있으며, 미리 정하면 불필요한 고비용
실행 파일이 된다.

## 7. 사전 등록 판정 규칙

### Stage0/Stage0B PASS

- 여섯 계약 검사가 모두 통과
- R1 exact equality
- cached/full 오차가 진단 스크립트 허용치 안
- 파라미터/state-dict/KV 엔트리 증가 없음

### Stage1/2의 1차 신호

각 repeat 내부에서 다음 순서로 본다.

1. 세 팔이 동일 조건과 실제 100M 토큰을 기록했는지 JSON 확인
2. NaN/skip/비정상 gradient 및 wall-time·VRAM 이상 확인
3. 600M deterministic paired full-val에서 `latin-fixed`, `random-fixed` 차이와 paired SE 확인
4. training-log 단일 best가 아니라 final/full-val을 우선

한 seed 차이가 0에 매우 가깝거나 기존 동일 계열의 재현 노이즈보다 작으면 `INCONCLUSIVE`다.
손실이 좋아도 runtime peak나 latency가 크게 나빠지면 비용 없는 승리로 기록하지 않는다.

### Stage3 승격 후보 조건

다음이 모두 필요하다.

- 최소 3 seed에서 방향이 일관되고 평균 개선의 신뢰구간이 0 아래
- fixed 대비 파라미터와 KV 저장량 증가 0 확인
- runtime peak와 step/decode latency를 별도 보고
- clean held-out의 정답 CE·argmax 정확도에서 비퇴행
- 한국어/영어 생성·지시이행에서 블라인드 또는 고정 rubric 비퇴행
- 변수/개체명 치환, 규칙 조합, 길이 외삽 중 적어도 하나에서 재현 가능한 개선

이 조건도 “완벽한 일반지능 증명”은 아니다. main 별도 이식 검토를 열 수 있는 증거 기준일
뿐이다. 합성 OOD나 CE만 좋아지면 “특정 구조 신호”로만 기록한다.

## 8. 비용·메모리 회계

- 추가 학습/배포 파라미터: 0 예상
- 추가 KV 엔트리와 KV bytes/token: 0 예상
- 추가 activation/scratch: `torch.roll` 결과 때문에 0이 아닐 수 있음
- Stage1/Stage2 시간: 사용자 실행 전이라 미확정. 각 팔의 JSON wall time과 CUDA peak를 기록한다.
- R3은 R2보다 레이어 방문이 많으므로 schedule 효과와 계산량 효과를 분리한다.
- weights, KV, activations, logits, allocator/reserved peak를 같은 “메모리”로 합쳐 말하지 않는다.

## 9. 실패·중단 규칙

- branch/namespace 가드 실패: 아무 실험도 실행하지 않는다.
- Stage0 실패: Stage1/2 실행 금지, 코드 결함으로 분류한다.
- 한 training arm 실패: 나머지 독립 팔은 계속하되 해당 triad 판정은 보류한다.
- OOM: micro-batch를 임의 변경해 이어가지 않는다. 계획을 갱신해 세 팔 모두 같은 조건으로 재설계한다.
- cache 누락·다운로드 실패·환경 실패는 성능 실패와 분리한다.
- 사용자가 중단한 실행은 미완료이며 결과로 승격하지 않는다.

## 10. 구현·검증 산출물

계획된 코드 산출물:

- torch-free PM000 알고리즘 정본과 [선택 이식 manifest](../tinylm/moonshot/README.md)
- config/CLI/trainer/model의 최소 Latin GQA integration hook
- seed 결정적 균형 순열 함수
- PM000 Stage0 동적 진단 스크립트
- 실제 nontrivial GQA를 타는 사용자 smoke arm과 JSON 계약
- PM 전용 namespace/branch 정적 가드
- Stage0, Stage0B, Stage1, Stage1E, Stage2, Stage2E 사용자 실행 배치

AI가 수행할 검증:

- Python AST/compile, import/call/flag/문서/배치 정적 게이트
- batch flag 검사, lint, dry-run, 이름/단계 검사
- moonshot namespace와 현재 branch 검사

AI가 수행하지 않을 검증:

- `.bat` 실행
- torch import를 수반하는 Stage0 진단
- 모델 생성·forward/backward
- GPU smoke, 학습, 평가, 결과 판정

## 11. 근거와 한계

직접 근거는 사용자가 첨부한 분석의 Latin GQA 정의와 권장 순서다. 비교 배경은 첨부문에
포함된 [GQA](https://arxiv.org/abs/2305.13245),
[Key-Driven/Perturbed GQA](https://arxiv.org/abs/2408.08454),
[Latin-square balancing](https://doi.org/10.1007/BF00173304) 링크를 따른다.

제한적 검색에서 동일한 recurrent-pass 완전 균형 순환을 찾지 못했다는 것은 신규성이나
특허성의 증명이 아니다. 또한 데이터에 없는 지식·어휘·지시행동을 이 연결만으로 만들 수
없다. 현실적인 성공 정의는 같은 파라미터와 토큰에서 결합·규칙·상태추적의 표본효율이
재현 가능하게 좋아지는 것이다.

## 12. 변경 이력

- 2026-09-06: PM000 최초 작성. Latin GQA 선택, namespace·단계·판정 규칙 사전 등록.
- 2026-09-06: 사용자 smoke에서 PM arm과 계측은 PASS했으나 전체 34개 arm 중
  `check_links`와 `diag_sparse34_pack` 2개가 nonzero여서 전체는 FAIL로 분리 판정.
- 2026-09-06: 사용자 Stage0가 여섯 wiring 계약을 모두 PASS. 품질 효과는 미측정.
- 2026-09-06: 향후 선택 이식을 위해 PM000 알고리즘을 torch-free 전용 모듈로 격리하고,
  변경 후 동적 증거를 새로 확보하도록 Stage0B를 추가. Stage1은 재검증 전 HOLD.
- 2026-09-06: 첫 smoke의 역사적 `sm_gqapass` tag가 로컬 일반 registry에 들어간 것을 확인.
  기록은 삭제하지 않고, 이후 smoke tag를 `dense_pm000__sm_gqapass`로 바꿔 일반 registry에서
  제외되도록 경계를 보강.
- 2026-09-06: Stage1 정적 preflight 완료 — 세 tag 미사용, 각 100,007,936 tokens,
  20 visits, CLA2, grad checkpoint on. 동적 재검증 전 HOLD는 유지.
- 2026-09-06: 사용자의 격리 후 공통 smoke PM arm과 Stage0B가 모두 PASS.
  전체 smoke는 `check_links` exit 5와 수정 전 `diag_sparse34_pack` exit 1로 RED.
- 2026-09-06: sparse34의 10비트→8비트 손실 원인을 `8 code / 5 byte` 포맷으로
  수정. AI는 torch/`.bat`을 실행하지 않았으므로 수정 후 공통 smoke 재검증 전 Stage1 HOLD.
- 2026-09-06: 사용자 재실행 `202609061405_smoke_fdce364.txt`에서 sparse34 1,000,000개
  왕복 불일치 0, codebook/tail, 정확히 1.250000bpw, 잘못된 입력 거부와 PM000 arm/contract가
  모두 PASS. 다만 `summarize_smoke.py` 기준 34개 arm 중 `check_links.py` exit 5 한 건이 남아
  전체 smoke는 RED이고 장기 Stage1 HOLD는 유지.
