# P098 — 재귀 token embedding 재주입: R2 이득 포화의 누락 부품을 재다

> 제안 계기: [기준표 B.29.2](../docs/EXPERIMENT_BASELINES.md#b292--재귀--우리-것은-논문의-축약판이다)와
> [COMPASS 재귀 축](../handoff/COMPASS.md). 사용자의 2026-09-21 48시간 queue·선결구현
> 승인에 따라 기본-off 덧셈판을 구현하고 독립 계획으로 분리한다.

## 1. 왜 — 재귀 횟수를 늘려도 이득이 포화된 이유를 구조로 검증한다

현 `train_repeat` 경로는 직전 hidden만 다시 중간 block으로 보낸다. 외부 재귀
Transformer 설계에서 쓰는 입력 embedding 재주입·adapter·절단 역전파가 없다. 우리
실측에서 R2~R3 이득은 있었지만 R6 추가 방문은 이득이 거의 붙지 않았다.
이 계획은 가장 싼 덧셈판만으로 그 누락이 R2에서도 실제 병목인지 묻는다.

## 2. 질문

| # | 질문 | 왜 중요한가 |
|---|---|---|
| Q1 | 추가 uniform cycle 시작에 초기 token representation을 덧하면 R2 full-val이 개선되나 | 재귀 포화가 입력 소실 때문인지 검증 |
| Q2 | seed 1337/2024/31415에서 방향이 같은가 | 시드 한 점을 구조 판정으로 승격하지 않음 |
| Q3 | 상주 불변·벽시계 악화 10% 이내인가 | 자유 품질 레버인지 대가 분리 |

## 3. ★예측 — 정직하게

덧셈이 hidden에 입력 정보를 재공급해 0.003~0.015 nats 개선할 가능성이 있다.
반면 adapter/norm 없는 단순 덧셈은 scale만 흐트러뜨려 악화할 가능성도 크다.
세 seed의 부호가 갈리면 자동 adapter 후속을 열지 않는다.

## 4. 단계 설계

### 단계0 — default-off·경로 계약

- `repeat_embed_reinject=False`는 종전 forward를 유지한다.
- 첫 구현은 `repeat_mode=uniform`, `train_repeat>1`만 허용하고 나머지는 fail-closed다.
- 재주입은 첫 중간 block 통과가 아닌 두 번째 이후 cycle 시작에 한 번씩 발화한다.

### 단계1 — 300M 2x3 seed panel

| tag | seed | 재주입 | 독립변수 |
|---|---:|:---:|---|
| `p098_r2_ctrl_s1337` | 1337 | off | direct control |
| `p098_r2_reinject_s1337` | 1337 | on | cycle embedding 덧셈 |
| `p098_r2_ctrl_s2024` | 2024 | off | seed control |
| `p098_r2_reinject_s2024` | 2024 | on | cycle embedding 덧셈 |
| `p098_r2_ctrl_s31415` | 31415 | off | third-seed control |
| `p098_r2_reinject_s31415` | 31415 | on | cycle embedding 덧셈 |

공통: `m100s8`, dense, CLA2, R2 uniform, Muon RMS4×4, KD off, WSD 0.80,
300,023,808 draw, exact 600M pool, no-ckpt.

## 5. 판정 기준

| 결과 | 판정 |
|---|---|
| 세 seed 모두 reinject-control ≤ −현 재귀 ruler | 후속 adapter/norm 후보 |
| 방향은 같으나 ruler 안 | 관측 보존, 기본값 불변 |
| 부호 역전 또는 세 seed 모두 악화 | 덧셈판 기각 |
| 벽시계 >10% 악화 | 품질 이득이 크지 않으면 기각 |

## 6. 비용

| 단계 | 비용 | GPU |
|---|---:|---|
| 0 | 정적 계약 수 분 | 0 |
| 1 | recurrent 300M 6팔 약 10.8h + paired 약 0.3h | 사용자 GPU |

## 7. 실행

- `run_P098_Stage1aW_r2_ctrl_s1337-done.sh`
- `run_P098_Stage1bW_r2_reinject_s1337-done.sh`
- `run_P098_Stage1cW_r2_ctrl_s2024-done.sh`
- `run_P098_Stage1dW_r2_reinject_s2024-done.sh`
- `run_P098_Stage1eW_r2_ctrl_s31415-done.sh`
- `run_P098_Stage1fW_r2_reinject_s31415-done.sh`
- `run_P098_Stage2W_r2_reinject_pair-done.sh`

## 8. 한계

- 덧셈판은 논문의 concat+adapter를 재현하지 않는 최소 진단이다.
- R2 uniform에만 한정하며 block/progressive/R6로 일반화하지 않는다.
- 학습 토큰은 300M으로, 한국어 평가 문제가 있는 600M 이상 학습을 편성하지 않는다.

## 9. 실행 이력 / 갱신

- 2026-09-21: 사용자의 48시간 queue·선결 구현 지시로 기본-off 덧셈 경로,
  CLI·JSON·W&B config 계약, 2x3 seed launcher를 구현했다. GPU·학습·품질은 `NOT_RUN`.

### preflight

**독립변수**: 같은 seed 안에서 cycle token embedding 덧셈 on/off 하나.
**기준선**: 코드·optimizer·pool·tokenizer·draw·schedule을 같이 실행한 off 팔.
**중단 사유**: 없음. 단 세 seed 출력 전 기본 승격은 금지.
**판정**: 결과 회수 시 현 재귀 계열 ruler를 `scripts/_rulers.py`에서 재조회.

> 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 10. 2026-09-23 Stage1/2W 실제 세 시드 — 단순 덧셈판 미승격

[결과 091](../test_result/091_20260923_P098-R2-초기임베딩-재주입은-3시드-실무-동급.md)은 여섯 300M 학습·세 paired full-val을 모두 회수했다. 학습 exit0·skip0이고 세 seed의 paired off−on은 +0.0015(SE0.0004), +0.0001(SE0.0004), +0.0002(SE0.0005)다. 모두 재귀 실무 자 0.0018 미만이며, 첫 seed의 t=3.47은 그 checkpoint 쌍의 통계 차이일 뿐 3-seed 채택 근거가 아니다.

§3의 0.003~0.015 nats 개선 가능성은 실측과 맞지 않는다. §5의 “세 seed가 재귀 ruler를 넘으면 adapter/norm 후보” 선결은 **불성립**이다. 단순 재주입은 기본 off 유지, 자동 추가 GPU 실험 없음. 부품 전체를 종결하지 않고 concat+adapter/normalization은 다른 독립 설계·비용·문턱이 승인될 때만 재개한다. 40 MiB 배포 tok/s와 실제 한국어 대화·논리 점수는 이 패널에서 NOT_RUN이다.
