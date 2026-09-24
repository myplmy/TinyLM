# 제안 — T0/T1 학습 기반 위에 출력 손실 융합·업데이트 단위 양자화 재사용·MTP 예산화를 적용한다

> **작성** 2026-09-23 · **상태** 승인 후 진행 중 · **분류** 실험계획 / 학습시간 / 런타임
> 양식: [proposal/README.md](https://github.com/myplmy/TinyLM/blob/ea363b34ebb42f3fb4a9bf3187467bc9df991223/proposal/README.md) §3 및 [_TEMPLATE.md](https://github.com/myplmy/TinyLM/blob/ea363b34ebb42f3fb4a9bf3187467bc9df991223/proposal/_TEMPLATE.md).
> 대상: **myplmy/TinyLM만** · 확인 commit: `ea363b34ebb42f3fb4a9bf3187467bc9df991223`.
> 문서·계산·서식 검사만 수행한다. 저장소 수정, 런처 작성, 설치, 모델 로딩, GPU 실행, 학습, PR/commit은 수행하지 않았다.
> 제안의 구현·동적 검증 상태: **DESIGNED / NOT_RUN**. 문서 작성 요청을 실험 실행 승인으로 해석하지 않는다.
> 권장 경로: `proposal/20260923_TinyLM-학습시간-T0-T1-S1-S3-최적화-제안서-approved-on-going.md`.
> **2026-09-24 후속 검토**: 당시 원안 미승인. 특히 S3 표본 손실의 분모·선택확률과 1.2B 확인 단계는 아래 10절 정정이 우선한다.

---

## 1. 배경 — 왜 지금 이 제안을 하나

### 1.1 현재 문제

기존 지능향상 제안의 E384, 다중 미래 토큰 예측(MTP), 지식 학습 팩과 후속 SFT는 추가 계산을 발생시킨다. 이 문서는 모델을 작게 만들거나 정답 데이터를 덜 학습해 시간을 줄이는 대신, 먼저 **동일 학습량·학습목표의 실행 비용을 줄이는 구현**을 제안한다. MTP 선택 계산처럼 gradient 분산을 바꾸는 안은 별도로 구분한다.

이전 제안의 M0/C0/U2는 모델 구성 이름이며 아래 T0/T1/S1/S2/S3는 학습 실행 전략 이름이다.

| 이름 | 구성 | 증거 상태 |
|---|---|---|
| T0 | M0에서 완주한 BF16 + compile(default) + no-ckpt + M8192 + accum16 + CE 청킹 + Muon RMS4 + KD off | 실측 운영 기준. 모든 형상의 전역 최속 조합이라는 뜻은 아님 |
| T1 | T0 + 안정 장기런의 평가·저장 주기 정리 + 준비된 로컬 토큰 캐시 재사용 | 기존 기능의 통합 후보. 추가 시간 이득 미측정 |
| S1 | 학습용 loss-first head 및 fused linear CE | 새로운 구현. loss·gradient 보존을 목표 |
| S2 | 한 optimizer update 안의 유효 양자화 가중치·STE 재사용 및 불필요한 CPU scalar 읽기 제거 | 새로운 구현. 수학적 동등성 목표, 수치·autograd 검증 필요 |
| S3 | 무작위 균형 MTP-head 선택 + SFT 길이 bucket | MTP는 확률적 학습 변화. bucket은 패딩 제거이나 배치 조성 통제 필요 |

### 1.2 실측 출발점 T0

결과 078 §13과 실행 로그를 사용한다.[L1][L2]

| 항목 | 확인 값 |
|---|---|
| checkpoint tag | `d16_cla2_norecur_rms4_t1200` |
| 구조 | `m100s12`, 총 16층, dim768, FFN2048, E256, vocab32768, CLA2, 재귀 없음 |
| 입력 배치 | micro_bs 8 × seq1024 = 8192토큰; accum16; 131072토큰/update |
| 학습량 | 9156 update; **1,200,095,232 draw tokens** |
| 옵티마이저 | Muon RMS ×4, matrix WD0; 나머지 parameter는 해당 AdamW 규약 |
| 실행 경로 | BF16 autocast, compile default, gradient checkpointing off, CE chunk2048, KD off |
| 정상 update 중앙값 | **2216.6 ms** |
| 보고된 wall | **344.6분** |
| VRAM reserved / allocated | **9.04 / 7.93 GiB** |
| full-val | **3.3833**; 해당 평가 언어 한국어 0%이므로 한국어 지능 증거가 아님 |
| 안정성 | skip0 |

344.6분은 로그의 학습 wall이다. 데이터 생성·다운로드·부모 학습·외부 LLM 비용까지 포함하는 프로젝트 전체 시간은 아니다. 원 실행은 Windows 경로였으므로 현재 WSL에서 같은 절대시간을 보장하지 않는다. M0의 더 낮은 손실을 Muon의 update 자체가 더 빠르다는 증거로 바꾸지 않는다.

### 1.3 기존 성과의 중복 합산을 금지한다

| 과거 실험/방법 | 현재 해석 | 본안 처리 |
|---|---|---|
| no-ckpt, 초기 dense 2982→2467ms | 해당 대조에서 약17.3% 단축 | T0에 이미 들어 있으므로 추가 이득 0으로 계산 |
| M=8192 무릎 | 특정 어휘·형상에서 micro-batch 확대 이득 포화 | E384/MTP에서 VRAM은 재측정; M을 무조건 증가시키지 않음 |
| 기존 NTP 스트림 packing | 이미 패딩 0 | 사전학습에 패딩 제거 이득을 다시 붙이지 않음 |
| KD 제거 | 일부 조건에서 품질·시간·메모리 모두 개선 | 현재 KD off, 교사 최적화는 기본 대상 아님 |
| BF16 optimizer state | 무KD에서 시간·reserved 실익 작음 | 속도 레버로 기본 승격하지 않음 |
| P060B | 3시드 전체 학습 on/off ms 비율 평균0.9988 | 부분 forward의 큰 가속을 전체 학습 가속으로 쓰지 않음 |
| P022C / P025B | cached FP8·희소 primitive의 일부 결과와 전체 wall 성공은 다름 | 기본 off, 동일 음성 실험 반복 금지 |
| P068 | _wq BF16만으로 시간 개선 미검출 | dtype 축소와 S2의 계산 횟수 감소를 구별 |

원장·후속 결과는 [L3]~[L5]를 참조한다. 옛 no-ckpt·KD 제거의 비율을 서로 곱해 T0의 미래 이득으로 포장하지 않는다.

## 2. 목적 — 무엇을 알아내거나 얻으려 하나

**M0/C0/U2 및 MTP·지식팩 학습의 입력량·주요 품질을 유지하면서, S1의 출력 비용·S2의 반복 양자화와 동기화·S3의 보조 head/패딩 비용을 각각 줄여 실제 wall time과 목표 품질 도달 시간을 개선한다.**

단일 목표 지표는 `같은 고정 평가 품질까지의 end-to-end wall`이며, `같은 입력 토큰·optimizer update 수의 wall`을 별도 보조 지표로 둔다. step/ms만으로 효율을 판정하지 않는다.

## 3. 성과물 — 승인하면 무엇이 생기나

| 산출물 | 형태·완료 판정 |
|---|---|
| 실행 조건 명세 | checkpoint/tokenizer/cache hash, precision, shape, optimizer, loss별 유효 타깃 수, 라이브러리 버전 |
| S1 loss-first 학습 API | hidden 반환·공유 어휘 행렬·masked row gather·fused linear CE, 기존 inference API 보존 |
| S2 update-local cache API | versioned 유효 가중치, FP32 gradient 누적, 기존 STE pullback, skip/eval/resume 무효화 |
| S3 sampler/collator | 균형 horizon 선택, valid-target 정규화, 128/256/512/1024 bucket |
| 검증 도구 | loss·모든 parameter gradient·한 optimizer update·직렬화/재개 검증 |
| 시간/메모리 보고 | warm/cold 분리, 동기 wall, compile/eval/save 시간, VRAM·RSS·입출력·타깃 계수 |
| 비교 결과 | S1/S2/S3 개별 A/B, 통과한 구성만 통합, 품질·속도 음성도 원장에 보존 |
| 배포 확인 | MTP head 실제 제거, 학습 캐시 미포함, model 구조·추론 결과 보존 |

신규 파일 이름·CLI는 승인 후 실제 소유 경로·옵션 충돌을 확인해 등록한다. 본 문서는 존재하지 않는 옵션을 실행 가능한 명령으로 제시하지 않는다.

## 4. 비용

모든 신규 개발·성능 수치는 **추정**이다. 아래는 실제 학습시간의 약속이 아니라 실험 예산 제안이다.

| 항목 | 양 |
|---|---:|
| AI 작업 / 엔지니어 작업 | 추정 38~70 engineer-h: S1 10~18, S2 18~32, S3 8~16, 문서·통합 2~4 |
| GPU — correctness/timing 게이트 | 추정 2~4 GPU-h, 3개 방법의 1차 조사 합계 |
| GPU — 100M paired 및 통과 구성 통합 | 추정 추가 4~8 GPU-h; 모든 후보 장기학습은 하지 않음 |
| GPU — 조건부 1.2B 확인 | 선택된 대조·후보 1쌍만 추정 10~15 GPU-h; 앞 단계 통과 후 별도 승인 |
| 디스크 | 체크포인트·커널 캐시·로그용 추가 10~25 GiB, 원천 코퍼스 별도 |
| host RAM | S2 surrogate gradient·SFT collator 관리용 증가분 별도 측정; GPU FP32 dW surrogate는 약0.37GiB 규모 가능 |
| 사용자가 직접 해야 하는 일 | CPU/GPU 검사와 속도 A/B 실행, 실행 로그 제공, 통합·후속 학습 승인 |
| 이번 문서 작성의 GPU 학습 | **0 GPU-h** |

2~4 + 4~8 = 초기 검증 전체 추정 6~12 GPU-h다. 개발비를 회수할 만큼 후속 학습이 많은지도 계산한다. 예를 들어 총 8 GPU-h의 검증비에 절감률20%라면 GPU 시간만의 손익분기 후속 학습량은 40시간이다. engineer-h는 GPU-h와 교환하지 말고 별도로 보고한다.

## 5. 원리·근거

### 5.1 우리 실측과 구현

현재 trainer는 매 micro-batch에 모델 전체 logits를 먼저 만들고 CE를 청크로 나눈다. 이 청킹은 `M×V` logits의 최초 생성 자체를 제거하지 않는다. `M=8192, V=32768, bf16` logits 한 벌은 정확히512MiB다.[L6]

현재 모델 forward는 `refresh_quant()`를 호출하며, optimizer는 accum micro-batch들을 처리한 뒤 한 번 실행한다. 따라서 update 내부의 같은 weight에 대한 중복 전처리를 줄이는 경로를 설계할 수 있다. 단 기존 STE·detach·어닐 의미를 보존해야 한다.[L7][L8]

### 5.2 외부 근거의 사용 범위

- [E1] Liger 공식 README의 FusedLinearCrossEntropy 및 독립 연산 조합 기능을 확인했다. 타 모델의20% 수치를 TinyLM에 전이하지 않는다.
- [E2] Apple의 Cut Your Losses 소개에서 어휘 logits의 materialization을 줄이는 방향을 확인했다. gradient filtering 같은 근사 옵션을 쓸 경우 별도 학습 변경이며 첫 비교는 근사 없는 모드로 한다.
- [E3] PyTorch CUDA 문서의 비동기 실행·동기화·CUDA graph 제약을 참고한다. graph 사용만으로 고정적인 추가 가속을 보장하지 않는다.

### 5.3 정직한 예측

S1은 head가 작은 경우, S2는 compile이 이미 전처리 비용을 대부분 숨기는 경우 이득이 작을 수 있다. S3는 개별 update를 빠르게 해도 gradient 분산 때문에 목표 품질까지 더 많은 update가 필요할 수 있다. 따라서 모든 예측은 개선0 또는 회귀의 가능성을 포함한다.

## 6. 방법

### 6.1 T1 — 기존 기법의 통합 운영안

T0를 유지한다. 안정 장기런의 `eval_every=500`, `save_every=1000`을 후보로 사용하고, 개발·기능 검사에서는 eval100을 유지한다. `save_every`는 best 저장을 막지 않는다는 현재 코드 규약을 명시한다.[L6]

```text
micro_bs: 8
seq: 1024
accum: 16
bf16_autocast: on
compile: on
compile_mode: default
grad_checkpoint: off
ce_chunk: 2048
optimizer: muon
muon_scale: rms
muon_lr_mult: 4
matrix_weight_decay: 0
KD: off
EMA: off
```

LR·quant anneal·학습 지평은 비교 실험의 정본을 유지한다. 속도를 이유로 이어학습을 초기 QAT 상태로 돌리지 않는다. 평가 주기를 바꿨으면 final checkpoint를 같은 고정 크롭으로 다시 평가한다.

T1의 T0 대비 예상 추가 이득은0~3%, 중심1.5%다. 현재 부대비용이 작다면0에 가깝다.

### 6.2 S1 — loss-first 출력 경로

1. `forward_hidden` 또는 동등한 새 학습 API로 마지막 hidden을 받는다. 생성 API는 유지한다.
2. 주 헤드·MTP 보조 헤드에 대해 factorized projection 뒤 fused linear CE를 수행한다.
3. SFT의 `labels=-100` 위치는 **trunk에서는 계산·역전파를 유지하고**, 출력 헤드에서만 제외한다.
4. 각 horizon의 마지막 위치·EOS·문서/assistant 경계 타깃을 따로 마스킹한다.
5. 공유 embedding gradient와 hidden gradient를 모두 모아 trunk backward를 **micro-batch당 한 번** 수행한다.
6. 청크512/1024/2048만 초기에 조사한다. memory 최소가 아니라 전체 wall 최소를 고른다.
7. 학습 head cache나 MTP parameter는 배포 export에서 실제 제거한다.

보조 loss0.2/0.1은 가중치이지 계산량 비율이 아니다. 동일한 `V`를 쓰는 head 두 개를 계산하면 그 두 GEMM·loss 비용을 지불한다.

**예측:** NTP E256은3~8%, E384+전량 MTP는6~18%(중심12%) 추가 절감. 다음의 30%와1.7배는 미측정 설계 가정이다.

```text
head+loss 비용 비중 fH = 0.30
그 부분의 구현 speedup rH = 1.70
추가 관리비용 epsilon = 0.005
절감 = fH × (1 - 1/rH) - epsilon = 약 11.85%
```

head-only gradient를 즉시 모델 weight에 업데이트하지 않는다. micro-batch·head·청크별 clipping은 금지한다. 모든 대상 gradient를 누적한 뒤 원래 optimizer 경계에서 clipping한다.

### 6.3 S2 — update-local 유효 가중치와 STE 집약

기존 식은 `Q(W) + (1-a)×stop_grad(W-Q(W))`이다. forward는 혼합되지만 backward를 단순한 혼합 미분으로 바꾸면 다른 알고리즘이다.[L7]

**구현 계약:**

1. update 시작에 weight·어닐·연결 mask 버전을 고정한다.
2. 동일 update의 모든 micro-batch가 같은 유효 가중치 수치를 사용한다.
3. 유효 가중치의 gradient를 FP32로 누적한다.
4. 모든 micro-batch 종료 후 기존 STE의 VJP를 한 번 적용해 실제 parameter gradient로 전달한다.
5. clipping·Muon's NS update·AdamW update는 종전 순서를 유지한다.
6. update/skip/로드/precision·mask 변경 시 즉시 무효화한다. 평가에서도 상태를 명시한다.

고정된 W에서의 항등식은 다음이다.

```text
sum_j J_STE(W)^T G_j = J_STE(W)^T sum_j G_j
```

이는 수학적 근거이며 실제 BF16 graph의 비트 동일성을 뜻하지 않는다. 현재 문서에는 재현하지 않은 과거 toy검사의 특정 오차값을 새 검증 성과로 싣지 않는다.

첫 구현은 center_weights·Arenas·LoRA·dynamic connectivity·KD off인 M0 계열만 지원한다. 미지원 옵션은 자동 fallback 또는 명시적 거절로 처리한다. 단순한 inference `freeze_quant()`나 optimizer-update 간 stale cache로 대체하지 않는다.

동시에 `loss.item()`, `ce.item()`, `valid.sum().item()`의 불필요한 micro-batch별 CPU 전송을 줄인다. loss 통계는 device tensor에 모으고 로그에서 읽는다. finite-gradient 안전 검사는 유지한다. 이 동기화 제거 후에는 기존 Python step timer와 단순 비교하지 않는다.[L6]

**예측:** T1+E384+전량 MTP 대비3~12%, 중심7%. compile 없는 과거 `refresh_quant` 8.2~11.2%를 현재 비용으로 그대로 쓰지 않는다.[L5]

```text
fQ = 0.045                 # 현재 비용이 아닌 가정
accum = 16
제거 가능한 sync 비용 = 0.028
새 cache/gradient 관리비용 ≈ 0.0002
절감 ≈ fQ × 15/16 + 0.028 - 0.0002 ≈ 7.0%
```

### 6.4 S3 — MTP 선택 계산

주 NTP head는 항상 실행한다. 16개 micro-batch를 update마다 무작위8개/8개로 나누어 한 집합은 horizon2, 다른 집합은 horizon4만 실행한다. 단순한 매번 고정 짝홀 구분은 데이터 순서와 결합할 수 있으므로 사용하지 않는다.

```text
원래 목표: L1 + 0.2 L2 + 0.1 L4
각 보조 head 선택확률: 1/2
선택된 보조 항의 가중: 원래 가중 / 선택확률
분모: 해당 update 전체에서 계산한 그 horizon의 유효 타깃 수
```

각 micro-batch 평균을 똑같이 더하면 타깃 수가 다를 때 원래 목표와 달라진다. `N1`, `N2`, `N4`를 각각 기록한다. 선택 확률은 타깃의 손실 크기에 의존시키지 않는다.

보조 gradient 기댓값은 조건부로 보존되지만 분산·clipping·Muon/AdamW의 비선형 갱신 때문에 전체 학습 궤적은 달라진다. **계산 보존형 S1/S2와 동급의 exact 최적화로 부르지 않는다.**

**예측:** 전량 MTP 대비6~14%, 중심9%. 이는 전체 학습 비용의 보조 head 몫이 약18~20%라는 가정에서 나온다. NTP-only 런에는 이득0이다. 마지막 감쇠는 원래 학습 계약대로 유지하고 계수가 정확히0인 head만 호출을 생략한다.

### 6.5 S3의 SFT 길이 bucket

길이128/256/512/1024에 micro_bs64/32/16/8을 대응시켜 micro-batch 슬롯8192를 출발값으로 사용한다. 긴 답변을 자르지 않는다. 1024 초과 레코드는 기존 길이 계약으로 따로 처리하며, 짧은 bucket에 억지로 밀어넣지 않는다.

손실은 update의 전체 응답 지도 토큰을 분모로 정규화한다. 패딩을 학습토큰으로 세거나, 같은 step 수만 유지해 실제 지도량을 줄이지 않는다. 최대4개 shape의 컴파일·메모리 비용을 합산한다.

```text
eta = 실제 비패딩 토큰 / 계산한 슬롯 토큰
예: eta_before=0.50, eta_after=0.90, 관리비용5%
시간비 ≈ 0.50/0.90 × 1.05 = 0.5833
예시 절감 약41.7%
```

위 eta는 실제 KnowledgePack 측정값이 아니다. 기존 NTP 스트림은 이미 패딩0이므로 이 이득을 적용하지 않는다. arbitrary block mask packing은 현 CLA·SDPA 경로에서 별도 커널 검증 전 도입하지 않는다.

### 6.6 사전등록 wall 예측표 — 확정 성과 아님

공통 예시 앵커를 다음으로 정의한다.

```text
T0 실측 = 344.6분
T1 중심 가정 = 344.6 × 0.985 = 339.431분
E384+전량 MTP 비용 가정 = T1 × 1.25 = 424.28875분
```

E384+MTP의25% 증가는 미측정이다. 실제 증가율이15%/35%면 비교 앵커부터 바뀐다. 아래 시간은 데이터 구축·교사 호출·후보 생성 제외, 동일1.2B 논리 입력 예산의 예시다.

| 적용안 | 해당 앵커 대비 추가 절감 | 중심 시간 | 조건부 시간 범위 |
|---|---:|---:|---:|
| S1 단독 | 6~18%, 중심12% | 373.4분 | 347.9~398.8분 |
| S2 단독 | 3~12%, 중심7% | 394.6분 | 373.4~411.6분 |
| S3 선택 MTP 단독 | 6~14%, 중심9% | 386.1분 | 364.9~398.8분 |
| 통과한 S1+S2+S3 | 겹침 재산정 후20~28%를 연구 목표 범위로 둠 | 예시 중심318.2분 | 305.5~339.4분 |

마지막 행은 개별 비율의 합이나 곱이 아니다. 특히 S1과 S3는 동일한 head 비용을 줄여 겹친다. 독립 profile을 합쳐 compute/head/quant/sync/eval/save의 비용 항목을 재분해한 뒤 결합값을 갱신한다. 예측 범위는 신뢰구간이 아니며 실패·회귀도 가능하다.

S3가9% 빨라져도 같은 품질까지 update가9.89% 이상 증가하면 단축은 소멸한다: `0.91 × 1.0989 ≈ 1`.

### 6.7 단계와 게이트

| 단계 | 무엇 | 비용(추정) | 다음으로 가는 조건 |
|---|---|---:|---|
| G0 | 실제 환경·shape·목표·프로파일 계약 고정 | CPU 문서작업 + GPU0.2~0.5h | cache/tokenizer/weights/precision/valid-target 일치 |
| G1 | S1 또는 S2 하나만 correctness 검사 | GPU0.2~0.5h/안 | 모든 parameter loss/gradient/update 허용오차 통과, skip0 |
| G2 | 같은 세션 A/B/B/A 블록 wall | GPU0.5~1h/안 | 전체 wall3% 이상 개선 방향 반복, 자원 문턱 통과 |
| G3 | 100M 고정 입력 paired 학습 | GPU1~2h/안 | 고정 직접질의+언어모델링 비퇴행, 목적 품질까지 시간 절감 |
| G4 | 통과 구성만 통합 | GPU0.5~1.5h | 결합 후 다시 correctness/timing 통과 |
| G5 | 최종1개 구성의 1.2B 또는 실제 후속학습 | 별도10~15h 예산 | G4와 추가 사용자 승인 |

FP32 단위검사 초기 허용값은 loss abs1e-5, gradient 상대L2 1e-5(0 norm은 abs검사), 한 update 상대L2 1e-5를 제안한다. BF16은 고정 숫자를 기억에서 복사하지 말고 동일 baseline의 커널 변화 오차 바닥을 먼저 계측한다. 주 품질 비열등성은 실제 직접질의 세트에서 사전에 정한 허용폭으로 판정하며, 권장 초기 허용폭은 전체 정답률−2%p다. 문항 상관을 반영해 source/family별 재표집하고 작은 표본의 미유의를 동급으로 선언하지 않는다.

### 6.8 계측 및 rollback

warmup 후 `synchronize → 여러 update 연속실행 → synchronize`의 구간 wall을 측정한다. GPU event는 내부 분해용이며 최종 채택을 대신하지 않는다. cold compile, 평가, 저장, 데이터 읽기, 마지막 GPU drain도 job wall에서 빠뜨리지 않는다.

필수 로그는 `logical_input_tokens`, `physical_token_slots`, `supervised_tokens`, `aux2_targets`, `aux4_targets`, `updates`, `wall_sec`, `eval_sec`, `save_sec`, `compile_sec`, `peak_allocated`, `peak_reserved`, `RSS`, `n_skip`이다.

실험 실패 시 새 옵션을 off로 돌리고 baseline checkpoint·optimizer·RNG·sampler·스케줄 상태를 복원한다. 새 epoch 명칭만으로 재개하지 않는다. prior checkpoint나 원시 로그는 삭제하지 않는다.

## 7. 거절하면 못 하는 것

기존 T0 학습은 계속 수행할 수 있다. 거절했다고 지능향상 연구 자체가 불가능해지는 것은 아니다. 다만 E384·MTP head의 추가 비용, update 내부 중복 전처리, 짧은 SFT의 패딩 비용을 이번 설계로 줄이지 못한다. 기존 커널·학습 목표를 유지하면서 비용을 더 지불하는 대안은 남는다.

## 8. 위험 — 실행하면 무엇이 잘못될 수 있나

| 위험 | 어떻게 드러나나 | 완화 |
|---|---|---|
| 계측 비동기 착시 | item 제거 후 Python 시간만 급감 | 동기 구간 wall과 마지막 GPU drain 포함 |
| CE 동등성 실패 | shared embedding gradient 누락, 마스크 분모 변화 | 모든 parameter gradient·모든 head의 valid count 검사 |
| S2 stale cache | weight update 뒤 이전 유효가중치 사용 | version key·invalidate 단언·resume 테스트 |
| S2 STE 오변경 | forward만 맞고 parameter gradient가 다름 | detach와 STE VJP 정본 보존 |
| 추가 메모리 | surrogate dW·head buffers로 OOM | 실측 후 micro-batch·chunk 조정, 시간 증가도 기록 |
| MTP 분산 증가 | 고정 토큰 품질 저하·회복 update 증가 | 동일 품질 도달시간 판정, 실패 시 전량 MTP 복귀 |
| SFT 데이터 가중 변화 | bucket별 짧은 응답 과대표집 | source·지도토큰 quota, 동일논리입력 대조 |
| compile 다형성 | shape·mask별 재컴파일 폭증 | 유한 bucket·서명 캐시·compile 비용 상한 |
| 과거 효과 중복 | no-ckpt·KD off 이득을 또 합산 | T0 기준 증가분만 계산 |
| 전체 품질 오인 | loss만 낮고 실제 질의 정답률은 악화 | 직접질의 평가를 유지하고 benchmark 개발로 대체하지 않음 |

## 9. 대안

| 안 | 무엇 | 장점 | 단점 |
|---|---|---|---|
| **A** | T1 이후 S1→S2, 필요 시 S3를 순차 적용 | 목표 보존형부터 시작, 원인 분리·회수 가능 | 구현·검증비 지불 |
| **B** | S1만 적용하고 S2/S3는 보류 | 위험·공수 작고 MTP 비용에 직접 대응 | 중복 양자화·배치 비용은 남음 |
| **C** | 현재 T0 유지 | 신규 개발비0, 기존 계보 보존 | 추가 학습 비용을 그대로 지불 |

### 권장안과 근거

**A안을 권장한다.** 첫 실사용 승격은 S1만으로 제한하고, S2는 correctness와 전체 wall을 통과해야 합친다. S3는 단순 NTP 가속 기능이 아니며 전량 MTP 품질이 유지되는 경우에만 승격한다. 데이터셋 생성·정답 체계·배포 구조는 바꾸지 않는다.

### 조회 근거

[L1]: https://github.com/myplmy/TinyLM/blob/ea363b34ebb42f3fb4a9bf3187467bc9df991223/test_result/078_20260911_P005b-RMS4는-jordan20을-이겼지만-한-형상이다.md
[L2]: https://github.com/myplmy/TinyLM/blob/ea363b34ebb42f3fb4a9bf3187467bc9df991223/test_result/078_log_20260916_P005b_stage12_rms_1200M_transfer.txt
[L3]: https://github.com/myplmy/TinyLM/blob/ea363b34ebb42f3fb4a9bf3187467bc9df991223/docs/methods/05_training_speed.md
[L4]: https://github.com/myplmy/TinyLM/blob/ea363b34ebb42f3fb4a9bf3187467bc9df991223/test_result/051_20260821_P065-B2는-무해하지만-무익하다-그리고-no-ckpt가-열렸다.md
[L5]: https://github.com/myplmy/TinyLM/blob/ea363b34ebb42f3fb4a9bf3187467bc9df991223/test_result/035_20260807_P022B-단계0-per-tensor로도-FP8은-거의-공짜다.md
[L6]: https://github.com/myplmy/TinyLM/blob/ea363b34ebb42f3fb4a9bf3187467bc9df991223/tinylm/train/trainer.py
[L7]: https://github.com/myplmy/TinyLM/blob/ea363b34ebb42f3fb4a9bf3187467bc9df991223/tinylm/model/ternary.py
[L8]: https://github.com/myplmy/TinyLM/blob/ea363b34ebb42f3fb4a9bf3187467bc9df991223/tinylm/model/transformer.py
[E1]: https://github.com/linkedin/Liger-Kernel
[E2]: https://machinelearning.apple.com/research/cut-your-losses
[E3]: https://docs.pytorch.org/docs/main/notes/cuda.html

---

## 10. 2026-09-24 타당성 재검토 — S3 수식 정정이 선결

원안 1~9절은 역사적 제안으로 유지한다. 현 [trainer](../tinylm/train/trainer.py), [삼진 STE](../tinylm/model/ternary.py), [기준표](../docs/EXPERIMENT_BASELINES.md)와 [P006 MTP 계획](../test_plan/P006_MTP-학습aux-및-FastMTP추론.md)을 대조했다. 구현·GPU·모델 프로파일은 `NOT_RUN`이다.

### 10.1 타당한 것과 아직 측정되지 않은 것

| 부분 | 타당한 이유 | 반드시 보존할 한계 |
|---|---|---|
| T0에서 no-ckpt/KD-off의 과거 이득을 다시 합산하지 않음 | 같은 출발점에 이미 포함된 속도 개선을 이중 계상하지 않는다 | T1의 eval/save 주기 변경은 학습 wall뿐 아니라 best 선택 시점도 바꿀 수 있어 final·고정 평가를 맞춘다 |
| S1 loss-first | 현재 trainer는 `model(x)`의 full logits 뒤 CE chunk를 적용해, M8192×V32768 BF16 한 벌이 512MiB다 | [Liger FusedLinearCrossEntropy](https://github.com/linkedin/Liger-Kernel)는 출발 구현 참고이지 TinyLM의 **factorized·tied** `emb_up→emb` 및 다중 head에 무변경 드롭인이라는 뜻이 아니다. shared embedding을 포함한 전 parameter gradient 확인 전 속도 채택 금지 |
| S2 update-local 유효 가중치 | optimizer update 전 weight가 고정이면 VJP의 선형성으로 micro-batch gradient를 합칠 수 있다 | 현재 `refresh_quant()`와 STE·mask·anneal·skip의 그래프를 바꾸므로 기존 구현과 동일하다고 선언할 수 없다. finite 검사를 남기고 수치·메모리·wall을 함께 잰다 |
| SFT 길이 bucket | 패딩이 많은 SFT에서 낭비 제거 가능 | 기존 NTP 스트림은 padding0이고 같은 8192 슬롯도 seq별 attention 계산량은 다르다. source·지도토큰 수·compile 변형을 통제 |

### 10.2 **수정 필수: S3의 불편추정 식이 현재 문구대로는 성립하지 않는다**

원안 6.4절은 horizon별 선택확률 `p=1/2`의 역수를 손실에 곱하면서 **선택된 micro-batch의 유효타깃 수**로 나눈다. 모든 micro-batch의 유효 수가 똑같아도 `2 × mean(selected loss)`의 기댓값은 원래 전체 평균의 **2배**다. 유효 수가 제각각이면 random denominator에 따른 비율 편향까지 생긴다. 따라서 원안의 “보조 gradient 기댓값 보존” 주장은 **현재 수식에 대해서는 부당**하다.

고정 논리 update의 전 horizon 유효타깃 수를 `N_k = sum_j n_kj`로 **선택 전** 계산하고, micro-batch j의 선택지시자 `I_kj`와 포함확률 `p_kj=1/2`를 쓰면, target 수가 0이 아닐 때 다음의 Horvitz–Thompson형 보조항을 제안한다.

```text
Lhat_k = lambda_k / N_k * sum_j (I_kj / p_kj) * sum_valid_t CE[k,j,t]
```

이는 고정 batch·고정 모델에서 **clipping 전 loss/gradient 총합의 기대값**만 원안의 전량 MTP와 일치시킨다. gradient clipping, Muon/AdamW update, 이후 학습 궤적까지 같게 만들지 않는다. 16 micro-batch에서 정확히 8개를 균형 선택하더라도 각 j의 주변 포함확률이 1/2인지 확인하고, `N_k=0`이면 해당 head를 생략·계수한다. 전량/표본 추정량을 작은 FP32 fixture로 비교한 뒤에만 속도·품질 gate를 연다. 구현 전에 [P006 Part A](../test_plan/P006_MTP-학습aux-및-FastMTP추론.md)의 후속 단계로 등록한다.

### 10.3 추가 제약과 3안 비교

- G5의 신규 1.2B 확인은 [기준표 1절](../docs/EXPERIMENT_BASELINES.md)의 600M 한국어 gate HOLD·1.2B SH 금지와 충돌한다. 과거 M0 1.2B는 역사 측정이지 현 재실행 승인 아니다. 300M 대응 실험이나 **실제 후속학습 예산**을 사용하고, 더 긴 실험은 한국어 평가·풀≥2배·사용자 별도 승인을 받은 뒤에만 재계획한다.
- S1+S2+S3의 20~28%는 중복 절감·관리비 재측정 전 **단순 연구 목표**다. 같은 GPU 점유·precision·logical draw·유효지도토큰에서 cold compile부터 마지막 drain까지 기록하고, target 품질까지 필요한 update도 센다.
- S2의 FP32 gradient buffer가 추가되면 GPU 메모리와 update-local graph 관리비가 커진다. `loss.item()` 동기화를 없애는 효과와 양자화 재사용 효과는 서로 다른 ablation으로 나눈다.

| 안 | 내용 | 장점 | 단점·영향 | 판단 |
|---|---|---|---|---|
| A | T1 계측만 먼저 하고 현재 T0 유지 | 구현 위험 최소 | eval/save 절감이 작으면 이득 없음 | 안전한 기준선 |
| B | T1 뒤 S1 단독 loss/gradient·whole-wall gate | 목표 변경 없이 head 병목 직접 시험 | factorized tied head의 자체 통합 필요 | **첫 구현 후보** |
| C | S1 이후 S2를 개별 검증, S3는 위 estimator 정정·MTP 전량 품질 통과 후 별개 시험 | 추가 속도 레버 분리 | 큰 구현·수치/품질 위험 | 조건부 후속 |

**권장: A로 현재 wall 비중을 재고, S1만 별도 승인 뒤 구현한다.** S3의 현 수식은 계획·런처에 복제하지 않는다.

> 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.
## 11. 2026-09-24 사용자 승인과 구현·검증 경계

사용자가 §10의 권장 순서(T1 확인 후 S1 우선)를 승인했다. 별도 [P102A 계획](../test_plan/P102A_T1-S1-S2-S3-학습시간-기능계약.md)과 사용자 실행 [Stage0W SH](../run_P102A_Stage0W_speed_math_contract.sh)를 만들었다. factorized CE 행 청크, 고정 유효 가중치의 VJP, 전체 valid-token 분모를 사용한 S3 HT 추정량의 CPU FP32 reference는 PASS했다.

이는 **fused loss 커널이나 trainer 가속의 구현 증거가 아니다**. 공유 입출력 embedding까지 포함한 S1 전 parameter gradient/update, S2 실제 STE refresh/optimizer 연결, S3 MTP trainer 연결, A/B/B/A whole-wall 및 품질은 NOT_RUN이다. 현재 전체 승인 범위는 미완료이므로 `-approved-on-going`을 유지하고 1.2B 학습 SH를 만들지 않는다.

## 12. 2026-09-24 막힘 상태 재감사 — T1 결과와 S1 코드 작성의 선결 구분

이전 WIP 3B는 T1 GPU whole-wall 로그가 없다는 이유로 S1/S2 구현까지 `막힘`으로 묶었다. §10 권장 순서는 **속도 우선순위·채택 판단**의 순서이지, 기본 off인 수치정합 코드를 사전에 작성할 수 없다는 뜻은 아니다. 따라서 GPT 구현 작업은 진행 중으로 되돌리고, T1 측정과 A/B/B/A 실속도 채택만 사용자 로그 전 `NOT_RUN`으로 둔다.

| 구성 | 이번 확인 | 계속할 GPT 작업 | 동적 판정 선결 |
|---|---|---|---|
| T1 | trainer host phase-wall·100M paired SH 준비 | 로그가 오면 비교 조건·순서효과·전체 wall 귀속을 판독 | 사용자 GPU 2팔 결과 |
| S1 | FP32 row-recompute CE의 hidden/up/shared emb gradient CPU PASS; `--loss-first` dense·비KD·비compile 기본 off trainer 경로와 hidden 반환 코드 연결 | 별도 [Stage0bW](../run_P102A_Stage0bW_loss_first_model_gate.sh)에서 전 모델 gradient/update 검증 후 AMP 수치·whole-wall 계측 | 실제 모델·GPU whole-wall·peak NOT_RUN |
| S2 | 고정 유효 가중치의 VJP 합 수학 fixture | 실제 STE cache 버전·skip/anneal/optimizer 무효화 코딩 | 정확한 update·memory/whole-wall 결과 |
| S3 | 전량 유효분모 HT 수학·8/16 private RNG fixture PASS; `--mtp-sample-half` 기본 off trainer 코드 STATIC_ONLY | 사용자 full MTP 기준선 기능·품질 뒤 모델/AMP·whole-wall 계측 | 전량 MTP 기준선·품질/시간 실제 `NOT_RUN` |

현재 S1 CPU 수치 PASS와 기본 off trainer 배선은 **코드 수준 STATIC_ONLY**다. 실제 TinyLM 모델·AMP/compile 변형·GPU 속도 이득의 증거가 아니다. 제안서 `approved-on-going`을 유지하며, 사용자 T1 로그 부재를 GPT의 남은 S2/S3 코딩을 정당화하는 포괄 사유로 쓰지 않는다.

### 12.1 S2 기본 off STE update cache 선결 — 2026-09-24

[P102A 계획](../test_plan/P102A_T1-S1-S2-S3-학습시간-기능계약.md)에 Stage0cW를 추가했다. 모델은 update 시작에 삼진 STE graph를 한 번 만들고 micro별 detached surrogate gradient를 누적한 뒤 clipping 전에 원래 graph로 VJP를 한 번 전파한다. `--ste-update-cache`는 별도 `p102a_s2` 태그, dense·비KD·비compile·FP32 STE에서만 켜진다. 기본 경로는 바뀌지 않는다.

[사용자 실행 게이트](../run_P102A_Stage0cW_ste_update_cache_model_gate.sh)는 3 micro 소형 모델의 loss·전 parameter gradient·clip·SGD update를 기존 매-forward refresh와 비교한다. 정적 구문과 `--check-only`는 PASS, **실제 모델 gate·CUDA BF16·peak·whole-wall·품질은 `NOT_RUN`**이다. 이 구현 자체는 S2 가속이나 채택 증거가 아니다. 사용자 T1 로그 부재도 S2 코드 작성 중단 사유가 아니지만, 실제 성능 판정은 여전히 별도다.

### 12.2 S3 반수 MTP 보조계산 opt-in 선결 — 2026-09-24

P101A 전량 MTP trainer가 기능 코드로 생겨 `--mtp-sample-half`를 기본 off로 연결했다. horizon2/4 각각 16 micro 중 독립 private RNG의 균형8개를 선택하고, 원래 **전체 update의 유효타깃 분모**에 포함확률 `p=1/2`의 역수를 곱한다. 선택된 head에서만 FP32 CE를 계산하므로 추정식의 clipping 전 기대값은 전량 보조 loss와 같다. 4-micro 가능한 모든 선택의 수학 fixture와 16-micro 재현/전역 RNG 보존 fixture PASS.

이 등가는 clipping·Muon update·이후 학습 궤적·품질을 보존한다는 뜻이 아니다. P101A 전량 MTP 실제 모델/품질 기준선이 `NOT_RUN`이므로 S3 사용자 학습 SH는 작성하지 않았고 속도·품질 채택도 열지 않았다.
