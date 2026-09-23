# 제안 — M0를 기준으로 C0·E384/QK 스케일·기존 코퍼스 MTP의 지능 개선을 검증한다

> **작성** 2026-09-23 · **상태** 승인 후 진행 중 · **분류** 실험계획 / 아키텍처 / 학습목표
> 양식: [proposal/README.md §3](https://github.com/myplmy/TinyLM/blob/ea363b34ebb42f3fb4a9bf3187467bc9df991223/proposal/README.md), [정식 _TEMPLATE.md](https://github.com/myplmy/TinyLM/blob/ea363b34ebb42f3fb4a9bf3187467bc9df991223/proposal/_TEMPLATE.md)의 아홉 절을 따른다.
> 대상: **myplmy/TinyLM만**. 기준 commit: `ea363b34ebb42f3fb4a9bf3187467bc9df991223`.
> 문서 작성만 수행했다. 저장소 수정·PR·런처 생성·학습·모델 로딩·새 데이터 제작은 수행하지 않았다. 제안서 작성 요청을 실험 실행 승인으로 해석하지 않는다.
> 권장 저장 위치: `proposal/20260923_TinyLM-M0-C0-E384-QK-MTP-지능향상-제안서-approved-on-going.md`.
> **2026-09-24 후속 검토**: 당시 원안은 미승인이었다. 아래 10절의 C0 학습량·P006 귀속·배포예산 정정을 먼저 읽는다.

---

## 1. 배경 — 왜 지금 이 제안을 하나

### 1.1 문제와 범위

현재 필요한 것은 위키 형식문자의 출력을 억제하는 처방이 아니라, **같은 작은 배포 모델이 새로운 질문에서 사실·관계·조건을 더 정확히 사용하는 능력을 얻는 방법**이다. 본 제안은 새로운 사전학습 데이터셋을 번갈아 시험하지 않는다. 기존 코퍼스·토크나이저를 고정하고 깊이, 입출력 랭크, 어텐션 스케일, 미래 토큰 예측을 분리한다.

이번 범위는 다음 네 항목이다.

| 이름 | 정체 | 상태 |
|---|---|---|
| **M0** | 16층·CLA2·무재귀·Muon RMS4·1.2B 학습 체크포인트 | 과거 실측 출발점. 종합 지능의 절대 1위라는 주장은 하지 않음 |
| **C0** | 18층·CLA2·무재귀·Muon RMS4·1.2B 학습 | 기존 기법을 묶은 후보. 전체 조합의 성능은 미측정 |
| **U2** | 16층·E384·헤드별 학습 가능한 QK 스케일 | 앞선 대화의 ‘최종개선안 2’. 새 구조 제안 |
| **MTP** | 같은 입력에서 1·2·4토큰 뒤를 예측하는 보조 학습 | 새 데이터 제작 없이 기존 캐시로 적용할 신규 구현 |

**지식 학습 팩은 본 제안의 선결이 아니다.** 그 설계는 별도 TinyDataset 문서가 소유한다. 본 실험에는 반사실 QA·새 SFT 코퍼스·교사 증류를 섞지 않는다. 이후 능력 학습팩을 사용할 때에도 아래 구조 실험과 결과 계보를 구분한다.

### 1.2 M0의 확인된 정보

M0는 `d16_cla2_norecur_rms4_t1200`이며, 결과 078 §13과 원 로그를 기준으로 한다.[L1] [L2]

| 항목 | 값 / 해석 |
|---|---|
| 프리셋 / arch | `m100s12` / `dense` |
| 층 | prelude 2 + middle 12 + coda 2 = **16층**, 반복 방문 없음 |
| 폭 / FFN | **768 / 2048**, SwiGLU |
| 어텐션 | Q 12헤드 / KV 3헤드 / head_dim 64 / CLA2 |
| 임베딩 | vocab **32768**, factorized rank **256**, 입력과 출력 행렬 공유 |
| 파라미터 | 로그상 **약 105.4M**. ‘90M 모델’이라고 부르지 않음 |
| dense의 뜻 | MLP 직접 타잉 없음. **고정밀 FP 모델이라는 뜻이 아님**: Q/K/V/O와 MLP에 TLinear 사용 |
| 초기화 | 20층 `m100_ko-en_300M_dense.pt`에서 role-aligned 부모 초기화 |
| 옵티마이저 | Muon RMS ×4, 행렬 WD 0; 임베딩 등 특수 그룹은 별도 정책 |
| LR / schedule | base LR 0.001, WSD, anneal_end 0.80, decay_fraction 0.20 |
| 배치 | micro 8 × accum 16 × seq 1024 = **131072 입력 토큰/업데이트** |
| 학습 길이 | **9156스텝 / 1200095232 draw tokens** |
| 학습 풀 | nominal 1.2B, 실제 train **1194000000** 토큰 |
| sampling | 무작위 시작점 복원추출. 1회 순차 epoch가 아님 |
| 언어 | 풀의 한국어 약 25.0155%, 영어 약 74.9845%; 실제 draw별 언어비는 별도 확인 필요 |
| 평가 | 해당 1.2B 풀 full-val, **한국어 0%** |
| 안정성 | skip 0, reserved/allocated **9.04/7.93 GiB** |
| 시간 | 해당 런 **344.6분**, 정상구간 중앙값 약 2216.6 ms/step |

같은 16층·동일 풀·동일 학습 길이에서 확인한 full-val은 AdamW **3.4117**, Muon jordan15 **3.3878**, RMS4 **3.3833**이다. RMS4의 직접 차이는 각각 −0.0284, −0.0045 nats다. JSON final **3.37875**는 다른 평가 눈금이므로 full-val과 혼합하지 않는다.[L1]

이는 **동일 조건의 언어모델링 결과**이다. 한국어 지능, 자유 생성 정답률, 모든 실험을 통틀어 최고의 모델이라는 결론으로 확장하지 않는다. M0의 가용 파일 경로·해시는 실행자가 로컬에서 확인해야 한다. GitHub의 로그 존재는 현재 작업 컴퓨터의 체크포인트 존재를 보장하지 않는다.

### 1.3 배포 수치의 정정

16층 동일 구조에 대한 LUT 코드·스케일 + int8 임베딩 + bf16 KV@1024의 **텐서 합산은 34.0 MiB**다. 18층의 대응 예산은 **37.1 MiB**로 보고됐다. CPU 속도는 별도의 저장·언팩 경로에서 측정한 값이다.[L3][L4]

따라서 `34.0 MiB + 과거 tok/s` 또는 `37.1 MiB + 15.84 tok/s`를 하나의 실행 경로가 동시에 보장한 수치로 취급하지 않는다. 텐서 합산은 프로세스 RSS, 프레임워크, 활성값, 임시 언팩 버퍼, allocator까지 포함한 최대 메모리도 아니다. 새 후보의 통과 조건은 **동일 배포 경로에서 품질·메모리·속도를 함께 측정**하는 것이다.

### 1.4 이미 끝난 실험과의 중복 방지

최신 COMPASS와 결과 원장에는 P098 단순 임베딩 덧셈의 3시드 실무 동급, P097 추가 시드 학습 후 공통평가 미완, 직접 타잉의 현 조건 기각, P014D scalar native v1의 속도 채택선 미달이 기록돼 있다.[L4]

U2의 E384와 학습 가능한 QK 스케일은 단순 임베딩 재주입·FiLM·층별 선형 승수의 반복 제안이 아니다. 다만 ‘다른 기법’이라는 사실 자체는 효과의 근거가 아니므로 별도 대조를 둔다. MTP도 기존 순환 방문 증가와 구별한다.

---

## 2. 목적 — 무엇을 알아내거나 얻으려 하나

**M0를 출발점으로, 기존 코퍼스와 배포 제약을 유지한 채 C0의 깊이 조합 및 U2의 입출력 랭크·QK 스케일·MTP 보조 목표가 실제 응답의 사실·관계·조건 정확도를 개선하는지 각 변경축과 계산 비용을 분리해 확인한다.**

Falcon-H1-Tiny-90M-Base는 외부 비교 목표이며, 달성을 보장하거나 본 제안의 구현 성공과 동일시하지 않는다. 영어 Base 비교와 한국어 추가 목표를 분리하고, instruction-tuned TinyLM과 무템플릿 Falcon Base의 차이를 ‘Base 지능’으로 오인하지 않는다.

---

## 3. 성과물 — 승인하면 무엇이 생기나

| 산출물 | 형태 / 소유 위치 제안 | 판정 이후 바뀌는 것 |
|---|---|---|
| M0 자산 명세 | checkpoint/config/tokenizer/cache 해시·평가경로 manifest | 비교 기준점 고정 |
| C0 구성 명세 | 총 18층·RMS4·동일 예산의 신규 후보 | 18층 전체 조합의 가치 판정 |
| U2 모델 변경 | `tinylm/config.py`, `model/transformer.py`, `model/modules.py` | E384와 QK 스케일을 독립 opt-in으로 제공 |
| 가중치 이식기 | rank 확장·effective-weight 보존·추가 파라미터 감사 | 미세조정을 처음부터 다시 학습하는 것으로 오인하지 않음 |
| MTP 학습 경로 | hidden readout·보조 head·미래 타깃·경계 마스크·손실 정규화 | **기존 캐시 재사용**, 새 학습 데이터 제작 0건 |
| 학습 재개 계약 | 원 체크포인트 불변, 새 optimizer/schedule, 양자화 상태 계승 | resume/부모 이식/continue를 구별 |
| 테스트 | off 동등성·초기 함수 보존·타깃 shift·EOS·gradient·배포 제거 검사 | 무동작·미래정보 누설·평가경로 불일치 방지 |
| 결과 | 질문별 응답, NTP CE, 자원, 3시드 대응 비교 | 실제 개선이 확인된 부품만 채택 |
| 배포 체크포인트 | MTP 보조 모듈을 실제 삭제한 codec 산출물 | 배포 파라미터 증가를 정확히 회계 |

경로는 **구현 제안**이며 현재 생성했다고 주장하지 않는다. 기존 API와 이름 충돌을 확인한 뒤 실제 파일 위치를 확정한다. 승인 전 P번호·실험 큐·기본 프리셋은 변경하지 않는다.

---

## 4. 비용

아래 수치는 **설계용 추정**이다. M0의 1.2B 런 344.6분을 길이에 단순 비례시키면 100M 약 0.48 GPU-h, 300M 약 1.44 GPU-h다. 새로운 head·E384·데이터 로딩·컴파일 비용은 그 비례식에 포함되지 않는다.[L1]

| 항목 | 양 |
|---|---:|
| GPU: 작은 수치·gradient·메모리 gate | 추정 **0.2 GPU-h 상한** |
| GPU: M0 기반 6팔 × 100M 탐색 | 입력 합 약 **600M**, 추정 **3.5~6 GPU-h** |
| GPU: 채택 후보와 대응 대조의 총 3시드 × 300M 확인 | 입력 합 약 **1.8B**, 추정 **10~18 GPU-h** |
| GPU: C0 18층 1.2B 조합 | **독립 선택 항목**, 추정 **7~10 GPU-h** |
| GPU: 고정 질문·언어별 평가·배포 점검 | 추정 **2~6 GPU-h**; CPU 벤치는 별도 |
| GPU 총 실행 상한 | **45 GPU-h**. 실제 처리량으로 상한 초과가 예상되면 자동 확장하지 않음 |
| AI 작업 | 실제 수행 약속이 아닌 구현 투입 추정 **24~40 인시**: 모델·학습 경로, gradient 시험, manifest·보고 |
| 사용자가 직접 해야 하는 일 | 로컬 M0·부모·캐시 존재 확인 1회, 승인 범위 결정, 승인된 GPU 실행, 고정 평가 문항 200개 이상 의미 검토 |
| 디스크 | 신규 데이터셋 **0 GiB**; checkpoint/optimizer **15~30 GiB 계획 상한**, 로그·응답 **1 GiB 이하 목표**; 실제 checkpoint 크기로 재산정 |

**코드 정확성을 확인하는 100~250스텝 시험의 loss를 품질 우열로 사용하지 않는다.** 속도는 GPU event만이 아니라 동기 wall·전체 업데이트·생성 경로에서 측정한다.

MTP의 parameter overhead는 작아도 logits와 역전파 메모리는 작지 않을 수 있다. 8×1024×32768 BF16 logits 한 벌은 **512 MiB**다. 보조 2개를 동시에 만들면 forward logits만 추가 1024 MiB다. ‘보조 파라미터 수가 작다 → 학습 비용도 0’이라는 추론을 금지한다.

---

## 5. 원리·근거

### 5.1 우리 실측과 구현

| 근거 | 확인한 내용 | 적용 범위 |
|---|---|---|
| 결과 078 §13 | M0 full-val 3.3833, 같은 길이에서 RMS4 우세 | 영어 중심 동일 조건의 optimizer 비교 |
| 결과 014 §18 | d16 LUT+int8 embedding+bf16 KV@1024 = 34.0 MiB | 해당 텐서 회계만 |
| 최신 COMPASS | d18 37.1 MiB 후보, P098 동급, P097 전면 승자 미확정 | 새 기본 부품의 과장·중복 방지 |
| `_head_logits()` | hidden → emb_up 전치 → 공유 어휘표 | E256의 선형 로짓 경로 존재 |
| `Attention` | Q/K를 parameter-free RMSNorm 후 SDPA에 투입 | normalization 뒤 gain을 추가할 위치가 명확함 |
| `Loader.__call__()` | S+1 토큰을 읽어 x와 y로 나눔 | 기존 한 배치에서 horizon 2·4 타깃 구성 가능 |

M0의 logits는 행벡터 표기에서 `logits = h × U × Wᵀ`다. `h: D`, `U: D×E`, `W: V×E`이다. 로짓들의 선형 표현 랭크는 E의 영향을 받지만, 이것을 **모델 전체 지능이 E차원으로 제한된다**거나 확률행렬 전체가 반드시 같은 랭크라고 표현하지 않는다.[L5]

### 5.2 외부 근거와 읽은 범위

| 문헌 | 실제 조회 범위 | 본 제안에 쓰는 범위 / 쓰지 않는 주장 |
|---|---|---|
| Gloeckle et al., 2024, arXiv:2404.19737 | **초록 확인** | shared trunk 위 다중 미래 head의 연구 근거. TinyLM에서도 개선·무오버헤드·추론 3배를 약속하지 않음 |
| Henry et al., 2020, arXiv:2010.04245 | **초록 확인** | 정규화 후 학습 가능한 QK 스케일의 근거. 원문의 L2 norm과 본 제안의 RMSNorm은 동일 구현이 아님 |
| Yang et al., 2018, arXiv:1711.03953 | **초록 확인** | 출력층 표현력 병목의 문제 설정. E384의 실제 이득이나 MoS와의 동일성을 주장하지 않음 |

**성공 가설:** E384가 답변 후보를 표현할 여유를 늘리고, QK gain이 필요한 문맥 선택의 강도를 조절하며, MTP가 같은 본문에서 조금 더 긴 예측 정보를 배우도록 돕는다.

**실패 가설:** 현재 병목이 사실·개념 경험 부족이어서 이 자유도가 쓰이지 않을 수 있다. E384가 연산만 늘릴 수 있고, tau가 1 근처에 머물 수 있으며, 보조 미래 타깃의 높은 불확실성이 주 NTP 학습을 방해할 수 있다. 기존 작은 모델에 관한 효과 크기는 모른다.

### 5.3 근거 링크

- [L1: 결과 078, §13·14](https://github.com/myplmy/TinyLM/blob/ea363b34ebb42f3fb4a9bf3187467bc9df991223/test_result/078_20260911_P005b-RMS4는-jordan20을-이겼지만-한-형상이다.md)
- [L2: M0 원 로그](https://github.com/myplmy/TinyLM/blob/ea363b34ebb42f3fb4a9bf3187467bc9df991223/test_result/078_log_20260916_P005b_stage12_rms_1200M_transfer.txt)
- [L3: 결과 014, §18](https://github.com/myplmy/TinyLM/blob/ea363b34ebb42f3fb4a9bf3187467bc9df991223/test_result/014_20260731003000_P030-CPU추론실측-양자화오버헤드.md)
- [L4: COMPASS](https://github.com/myplmy/TinyLM/blob/ea363b34ebb42f3fb4a9bf3187467bc9df991223/handoff/COMPASS.md)
- [L5: transformer.py](https://github.com/myplmy/TinyLM/blob/ea363b34ebb42f3fb4a9bf3187467bc9df991223/tinylm/model/transformer.py)
- [L6: modules.py](https://github.com/myplmy/TinyLM/blob/ea363b34ebb42f3fb4a9bf3187467bc9df991223/tinylm/model/modules.py)
- [L7: loader.py](https://github.com/myplmy/TinyLM/blob/ea363b34ebb42f3fb4a9bf3187467bc9df991223/tinylm/data/loader.py)
- [L8: trainer.py](https://github.com/myplmy/TinyLM/blob/ea363b34ebb42f3fb4a9bf3187467bc9df991223/tinylm/train/trainer.py)
- [L9: EXPERIMENT_BASELINES](https://github.com/myplmy/TinyLM/blob/ea363b34ebb42f3fb4a9bf3187467bc9df991223/docs/EXPERIMENT_BASELINES.md)
- [E1: Multi-token Prediction](https://arxiv.org/abs/2404.19737)
- [E2: Query-Key Normalization](https://arxiv.org/abs/2010.04245)
- [E3: Softmax Bottleneck](https://arxiv.org/abs/1711.03953)

---

## 6. 방법

### 6.1 네 구성과 독립변수

| 구성 | 층 | E | QK gain | 보조 미래 head | 데이터 |
|---|---:|---:|---|---|---|
| M0 | 16 | 256 | 고정 1 | 없음 | 과거 1.2B 풀 |
| C0 | 18 | 256 | 고정 1 | 없음 | 비교용 동일 1.2B 풀 |
| U2 | 16 | 384 | 학습 가능 | 없음 | M0와 동일 캐시 |
| U2+MTP | 16 | 384 | 학습 가능 | horizon 2·4 | M0와 동일 캐시 |

C0는 **M0에서 층 두 개를 임의 삽입한 모델**로 정의하지 않는다. 과거 18층 계열과 같이 20층 부모의 role 초기화를 사용해 1.2B를 학습하는 독립 조합안이다. 반면 U2는 M0에서 함수 보존 확장 후 계속 학습한다. 이 계보 차이를 숨긴 채 C0와 U2의 차이를 ‘층수 효과’로 빼지 않는다.

### 6.2 C0의 명시적 설정

```text
preset: m100s14                # middle 14 + edges 4 = 총 18층
arch: dense                    # 직접 MLP 타잉 없음, 고정밀 모델의 동의어 아님
dim: 768
ffn_dim: 2048
emb_rank: 256
cla_group: 2
attn_group: 1
train_repeat: 1.0
optimizer: muon
muon_scale: rms
muon_lr_mult: 4
matrix_weight_decay: 0
base_lr: 0.001
sched: wsd
anneal_end: 0.80
lr_decay_fraction: 0.20
micro_bs: 8
accum: 16
seq: 1024
steps: 9156
draw_tokens: 1200095232
pool_nominal_tokens: 1200000000
pool_actual_train_tokens: 1194000000
parent_init: 동일 m100 20층 부모, role 대응
KD / FiLM / LRM / sparse34 / reinject: off
```

이는 새 CLI 명령이나 실제 런처가 아니라 **승인 대상 설정 명세**다. `--tokens`의 파일명·캐시 네임스페이스와 실제 draw를 구분한다. 기존 기준표의 신규 1.2B 실행 HOLD·한국어 구성 gate를 자동 해제하지 않는다. **이 제안 승인 시 C0의 역사 조건 비교를 예외로 허용할지 명시해야 하며**, 미승인 시 C0는 문서 후보로만 남는다. E384/MTP 탐색은 C0 완주를 기다릴 필요가 없다.[L9]

### 6.3 U2: E256 → E384 함수 보존 확장

기존 임베딩 `W: 32768×256`, 투영 `U: 768×256`에서 다음을 만든다.

```text
W_new = concatenate(W, R, axis=1)      # R: 32768×128, 작은 비영 난수
U_new = concatenate(U, zeros, axis=1)  # zeros: 768×128
```

실수 산술에서 `W_new × U_newᵀ = W × Uᵀ`, `h × U_new × W_newᵀ = h × U × Wᵀ`다. 입력 경로와 출력 경로를 함께 바꾸어 시작 함수가 보존되도록 한다. 양쪽 추가 행렬을 모두 0으로 두지 않는다. 첫 업데이트에서 새 U 블록의 gradient가 비영이고 이후 R에도 gradient가 흐르는지 검사한다.

초기 함수 보존은 **학습 중 FP32 master/현재 effective-weight 경로**의 성질이다. 새 R 때문에 per-row int8 scale이 바뀌면 배포 양자화 후 동등성까지 자동 보장되지 않는다. 초기 로짓·첫 greedy 토큰과 양자화 후 차이를 따로 검사한다.

추가 parameter 계산:

```text
ΔP = 32768×128 + 768×128 = 4292608
배포 추가량 가정 = embedding int8 4194304 B + projection fp32 393216 B
                 = 4587520 B = 4.375 MiB
QK gain 192개 fp32 = 768 B = 약 0.000732 MiB
M0 34.0 MiB + 위 가정 = 약 38.376 MiB
```

따라서 **16층을 유지**한다. 18층의 37.1 MiB에 E 확장을 더하면 약 41.476 MiB이므로 40 MiB 목표를 넘긴다. 본 계산은 기존 반올림된 34.0과 37.1에 기반한 예산 추정이지 새 측정값이 아니다. scale 수·alignment·metadata·작업 버퍼는 export 시 다시 합산한다.

### 6.4 U2: 정규화 후 헤드별 QK gain

정규화된 q·k에 대해 아래 식을 사용한다.

```text
score(layer, head) = tau(layer, head) × (q_norm @ k_norm.T) / sqrt(64)
tau = 0.5 + 3.5 × sigmoid(a)
a 초기값 = log(1/6)      # tau=1을 재현
```

- 총 **16×12 = 192개** scalar를 둔다. WD는 0, base learning rate의 0.1배로 시작한다.
- QK-norm을 제거하지 않는다. gain은 Q 정규화 **이후**에 적용한다. RoPE와 scalar 곱의 순서를 일관되게 유지한다.
- q에 tau를 곱하고 k는 그대로 두는 한 위치로 구현한다. q와 k 양쪽에 같은 tau를 곱하면 tau 제곱이 되어 명세와 달라진다.
- 학습, full forward, prefill, cache decode, 진단 확률 재계산에 동일 규약을 적용한다.
- tau의 이동량은 동작 검사이며 성능 근거가 아니다. 경계 0.5/4에 몰리는 비율, NaN/skip, attention entropy, 실제 정답률을 함께 기록한다.
- `off`는 종전 경로를 그대로 호출한다. 구 checkpoint 로드 시 새 key가 없어도 명시적인 migration을 거쳐 tau=1로 초기화하며, 다른 missing key까지 무시하지 않는다.

### 6.5 MTP의 조건: 별도 데이터셋 제작은 불필요하지만 학습 경로 변경은 필요하다

**현재 Loader가 이미 반환하는 x·y만으로 구현 가능하다.** 모델에 head만 달고 종전 NTP loss만 계산하면 MTP가 아니다. 필요한 변경은 head, target 구성, mask, loss, gradient·메모리 처리다. 토큰 캐시 자체와 토크나이저는 변경하지 않는다.[L7]

#### A. 출력 head

```text
h_t: 토큰 위치 t까지 본 trunk의 마지막 정규화 은닉상태, 폭 768
주 head: 기존 U를 사용하여 바로 다음 토큰 예측
aux_2: 독립 A2(768×E)와 공유 어휘 W로 t+2 예측
aux_4: 독립 A4(768×E)와 공유 어휘 W로 t+4 예측
aux logits = h_t × Ak × W.T
```

처음 A2·A4는 현재 U의 복사에서 출발한다. **복사 뒤 별도 파라미터**이며 U와 storage를 공유하지 않는다. 이 설계는 논문의 독립 head 원리를 저랭크 readout으로 옮긴 **TinyLM용 변형**이다. 원 논문과 완전히 같은 구조라고 부르지 않는다.

추가 학습 파라미터는 E256에서 **393216**, E384에서 **589824**다. 배포 시 두 head를 state_dict와 optimizer에서 제거하므로 최종 모델의 파라미터 증가는 0이다. ‘사용하지 않는다’만으로는 제거로 세지 않는다.

#### B. 타깃 정렬 — 입력 토큰과 loss 개수를 구별

현재 x·y는 같은 길이 S이며, 내부 raw는 S+1 길이다. 이미 읽은 배치로 복원한다.

```python
raw = torch.cat([x[:, :1], y], dim=1)  # shape (B, S+1)
# horizon k의 유효 위치 수: S+1-k
# logits_k[:, :S+1-k] 와 raw[:, k:]를 비교한다.
```

예: raw가 `[A, B, C, D, E]`, x가 `[A, B, C, D]`이면:

| head | 사용할 hidden 위치 | 정답 |
|---|---|---|
| k=1 | A, B, C, D까지 본 상태 | B, C, D, E |
| k=2 | A, B, C까지 본 상태 | C, D, E |
| k=4 | A까지 본 상태 | E |

**B·C·D를 입력받은 뒤 A 위치의 예측으로 쓰지 않는다.** 본래 causal mask를 유지한다. S+4를 새로 읽지 않으므로 기존 sampler 범위·시드·주 NTP의 입력과 타깃이 바뀌지 않는다. 끝부분에 없는 미래 타깃은 그냥 마스킹한다.

#### C. EOS와 문서 경계

EOS ID는 tokenizer에서 확인한다. 빈도나 고정값 2로 추정하지 않는다.

```text
segment_id(j) = raw의 j 이전에 나타난 EOS 개수
aux k의 조건: segment_id(t) == segment_id(t+k)
```

EOS 자체를 미래 정답으로 예측하는 것은 허용하지만, 그 EOS **뒤 문서로 넘어가는** 보조 타깃은 제외한다. crop 시작 전의 문서를 알 필요 없이, crop 안에서 보이는 EOS로 필요한 경계 판정을 할 수 있다. EOS가 원문 리터럴과 충돌하거나 cache boundary가 불명확하면 해당 cache에서 MTP gate를 중단한다.

첫 비교에서는 **주 NTP loss는 기존 그대로** 둔다. 주 NTP의 문서 경계 처리까지 바꾸면 독립변수가 추가되기 때문이다. ‘EOS 뒤 어텐션 차단’은 이 제안에 포함하지 않는다.

향후 SFT와 결합할 때에는 EOS만으로 부족하다. canonical의 assistant message별 문자 span을 토큰에 매핑해 **같은 assistant 응답 구간의 source/target**만 보조 지도한다. 단순히 target의 `label != -100`만 확인하면 서로 다른 응답을 건널 수 있다. 이 확장도 새 데이터 제작이 아니라 기존 메시지 경계 metadata의 사용이다.

#### D. 손실과 일정

```text
L = L_NTP + lambda2 × mean(valid CE_2) + lambda4 × mean(valid CE_4)
lambda2 최댓값 = 0.20
lambda4 최댓값 = 0.10
처음 5% updates: 0 → 최댓값 선형 증가
5~80%: 유지
마지막 20%: 최댓값 → 0 선형 감소
```

각 head는 **자기 valid target 수**로 나눈다. NTP valid가 없는 배치는 실패 처리한다. 보조 head의 valid가 0인 배치는 그 항만 0으로 놓고 횟수를 기록한다. 각 microbatch의 mean을 다시 단순 평균하지 않고, accumulation 구간 전체의 valid-token 합으로 정규화한다.

보조 target 수를 입력 draw 수에 더하지 않는다. `input_draw_tokens`, `ntp_targets`, `aux2_targets`, `aux4_targets`, `wall_seconds`, `peak_memory`를 각각 저장한다. `L_NTP`와 보조 합산 loss의 숫자를 과거 val CE와 직접 비교하지 않는다.

#### E. 메모리와 gradient 구현

정확성 reference 구현을 먼저 만들되, 실물에서 세 head의 전체 logits를 동시에 보관하지 않는다. 작은 chunk로 logits를 계산하는 것만으로 autograd의 saved tensor가 전부 사라진다고 가정하지 않는다.

메모리 절감 후보는 **trunk를 1회 계산 → head 입력 hidden을 detach한 leaf로 받음 → 256행 단위로 각 head의 loss/backward 수행 → hidden gradient를 누적 → 원 trunk에 1회 backward**다. 공유 어휘표의 head-side gradient와 input-embedding-side gradient를 모두 합산해야 하며, head/chunk 사이 optimizer step은 금지한다. gradient clipping과 optimizer step도 유효배치당 한 번이다.

이 경로는 reference의 전체 loss와 모든 parameter gradient를 CPU FP32 작은 fixture에서 대조한다. 같은 계산을 불필요하게 여러 번 clipping하거나, detached hidden 때문에 trunk가 학습되지 않는 구현은 거절한다. BF16 실물 허용오차는 같은 연산의 반복 측정으로 별도 설정한다.

#### F. off·배포 계약

보조 lambda가 0일 때에는 head를 불러 계산하지 않는다. 완전히 비활성화한 구 프리셋은 주 경로의 loss/logits/gradient를 유지해야 한다. 배포 checkpoint는 보조 파라미터 key 0개, 동일 shape의 주 head, 동일 tokenizer hash를 검사한다. 보조 head 삭제 전후 주 NTP logits는 같은 가중치에서 동일해야 한다.

본 제안은 MTP를 **훈련 보조 목표로만** 사용한다. speculative decoding·추론 3배 가속·추가 head로 여러 토큰을 바로 확정하는 기능은 포함하지 않는다.

### 6.6 계속 학습의 공통 설정

M0 기반 탐색은 다음 조건을 모든 팔에서 같게 둔다. 수치는 미측정 설계값이며 기존 1e-3 사전학습 최적값의 자동 전이가 아니다.

| 항목 | 제안 설정 |
|---|---|
| 초기 checkpoint | 동일한 M0 가중치; 원본 불변 |
| cache/tokenizer | 동일 1.194B train cache / 동일 32768 tokenizer; hash 일치 |
| batch/seq | 8×16×1024; 부족하면 4×32×1024로 **모든 대조를 함께** 조정 |
| optimizer | Muon RMS4, matrix WD0; embedding 등 그룹 정책도 전 팔 동일하게 기록 |
| base LR | **2e-4**, 워밍업 100 updates, 이후 WSD, 마지막 20% 감쇠 |
| 양자화 | 현재 checkpoint의 effective function을 보존. **계속 학습 시작 시 anneal=0 자동 초기화 금지** |
| 부가 parameter | aux head의 optimizer 그룹·QK gain 0.1×LR·WD0를 명시 |
| 저장 | 종료본 + NTP 기준 best + 평가 시점 snapshot; 이전 파일 미덮어쓰기 |
| 평가 선택 | 보조 loss가 아닌 고정 NTP 및 고정 질문 성공률 |

기존 CLI의 `--resume` 또는 `--init-from`을 새 fine-tune 인터페이스로 오용하지 않는다. 가중치만 로드하는 continued-training 경로와, optimizer 상태를 포함한 동일 런 재개를 별도 계약으로 구현한다.

### 6.7 단계별 gate와 비교표

| 단계 | 무엇 | 비용 | 다음으로 가는 조건 |
|---|---|---:|---|
| G0 | 자산 hash·계보·토크나이저·주 함수·평가 경로 확인 | GPU 0, 실행자 로컬 검사 | M0·캐시 식별 완료; 유효 가중치 로드 확인 |
| G1 | E384 함수 보존, tau=1, MTP off/shift/EOS/gradient 검사 | 작은 CPU 시험, GPU 상한 0.2h | 정확한 reference와 일치, 미래정보 누설 0 |
| G2 | 아래 6팔, 각 100M | 추정 3.5~6 GPU-h | 유효 품질·안정성·시간 제약을 넘은 변경만 보존 |
| G3 | G2 채택 후보와 B0, 300M씩 총 3 seed의 후속학습 | 추정 10~18 GPU-h | 지능 primary와 비퇴행 기준 동시 통과 |
| C0 별도 | 18층 신규 1.2B 조합 | 추정 7~10 GPU-h | 별도 승인·언어 한계 명시; 전용 대응 비교 |
| G4 | 동일 실제 배포 경로에서 export·메모리·속도·정답률 | 추정 2~6 GPU-h + CPU | 40 MiB 목표 회계 범위와 속도 하한 동시 검증 |

G2 팔 구성:

| 팔 | E384 | QK gain | MTP | 직접 비교 |
|---|---|---|---|---|
| B0 | off | off | off | 계속 학습만 한 대조 |
| B1 | on | off | off | B1−B0: 랭크 |
| B2 | off | on | off | B2−B0: QK gain |
| B3 | on | on | off | 결합과 상호작용 |
| B4 | off | off | on | B4−B0: MTP |
| B5 | on | on | on | B5−B3: U2 위 MTP |

seed는 1337/2024/31415를 사용하되, **같은 M0에서 갈라지는 3개 후속학습 seed**다. 원천 사전학습 전체의 독립 3시드 증거라고 부르지 않는다. 작은 gate가 통과했다고 자동으로 모든 대형 팔을 연속 실행하지 않는다.

### 6.8 데이터가 바뀌지 않는 지능 평가

사용자 방식인 **대형 LLM 직접 질의·답변 판정**을 primary로 한다. 새 학습 데이터셋 제작을 요구하지 않는다. 평가자는 기존 고정 질문을 재사용하고, 없을 때만 학습과 분리된 질문 패널을 한 번 고정한다. adaptive 후속질문은 진단 로그로 분리한다.

- 모델 선정용 고정 panel: 영어 1000, 한국어 500 질문을 목표로 한다. 너무 어려워 모두 오답이면 모델 간 순위를 만들지 말고 기초 항목의 결과를 함께 보고한다.
- Base 비교는 양쪽에 동일한 completion/few-shot 형식으로 수행한다. chat SFT 유무가 다른 점을 가리지 않는다.
- 답변 내용의 정답/부분정답/오답/판정불가를 기록한다. 말투·길이 점수를 primary에 섞지 않는다.
- 질문 ID·원문·generation seed·judge 버전·채점 rubric을 고정하고 모델명을 가린다. 계산·형식은 가능한 한 프로그램 판정을 사용한다.
- 같은 fact/topic에서 파생된 질문은 cluster로 묶어 bootstrap한다. prompt별 수를 독립 표본 수로 과대계상하지 않는다.

**실험용 설계 판정값:** primary macro 성공률 평균 +3%p 이상, paired cluster 95% 구간 하한 >0, 후속 3 seed에서 같은 방향 2개 이상을 최종 채택 기준으로 둔다. 언어별 −3%p 이상의 명확한 퇴행이나 정상 NTP CE +0.02 nats 이상의 반복적 악화는 HOLD 사유로 삼는다. 이 숫자는 기존 ‘자의 0.0018/0.0024’를 옮긴 통계적 사실이 아니라 이번 proposal의 실무 문턱이다. 표본수 부족으로 구간이 넓으면 **미확정**으로 보고하며 사후 문턱을 바꾸지 않는다.

Falcon 동급은 별도 영어 대응 평가에서 비열등성 허용폭 −3%p를 미리 정하고 그 신뢰구간으로 판정한다. 한국어 개선은 별도 요구사항이며 영어 전용 참조모델과 섞어 합산하지 않는다.

### 6.9 비용·실패 중단과 이력

MTP의 same-input 조건에서 whole-step wall이 B0보다 **35% 이상 증가**하면 동일 draw의 품질 외에 동일 GPU 시간 대조를 추가하거나 비용 미달로 보류한다. 학습 VRAM의 목표 상한은 해당 16GB 장치에서 **reserved 14 GiB**이며, OOM 회피를 위해 배치를 바꾸면 모든 대응 팔을 함께 바꾼다. 이는 실행 안전 예산이지 실제 가용 메모리 보장이 아니다.

100M에서 목표품질이 올라가지 않아도 ‘MTP 원리 전체 기각’이라고 하지 않는다. 이번 저랭크 head·모델·예산 조합의 음성으로 기록한다. 최고점 하나만 골라 C0·U2·MTP 모두 성공했다고 합산하지 않는다.

현재 이력: **2026-09-23 문서 작성, 모든 신규 구현·품질·배포 실험 NOT_RUN**. 승인 이후에는 계획서 번호, 구현 commit, 명령, 실제 조건과 이탈, 원 로그 링크를 추가한다.

---

## 7. 거절하면 못 하는 것

기존 모델 사용과 기존 실험 결과의 활용에는 아무 제한도 생기지 않는다. M0는 그대로 남는다. 다만 현재 코퍼스로 **입출력 랭크 확대·어텐션 선택 강도·미래 예측 학습이 추가 지능을 만드는지**는 알 수 없다. 지식 학습 팩 제작과 검증 기반 후속학습은 별도 경로이므로 본 제안을 거절해도 진행 가능하다.

C0를 거절하면 18층 전체 조합의 가치만 미확인으로 남는다. **U2/MTP를 시작하기 위해 C0를 반드시 먼저 만들 필요는 없다.**

---

## 8. 위험 — 실행하면 무엇이 잘못될 수 있나

| 위험 | 어떻게 드러나나 | 완화 |
|---|---|---|
| 계측: en full-val을 한영 지능으로 오인 | 한국어 질문은 그대로인데 loss만 감소 | 언어별 고정 생성 평가, source별 loss 별도 |
| 계측: MTP로 target 수가 늘어 입력량도 늘었다고 계산 | 처리 토큰 보고가 head 수배로 증가 | input draw와 각 head target을 분리 |
| 미래 누설·shift 오류 | 작은 fixture가 비정상적으로 쉽게 풀림 | 위 A~E shift oracle, causal gradient 접근 시험 |
| 문서/대화 경계 오염 | EOS 다음 문서/다른 assistant 답을 미래 정답으로 사용 | segment ID 및 message ID mask |
| E384 초기화 손상 | 학습 0에서 원 logits가 변함 | 입력·출력 동시 확장, dtype별 reference, 양자화 별도 시험 |
| 양자화 상태 재설정 | continue 시작 시 갑작스러운 함수·loss 변화 | 현재 effective function 보존, anneal 자동 reset 금지 |
| 큰 hidden-head 그래프 메모리 | logits chunk를 써도 backward OOM | detach/누적 gradient 경로를 reference와 대조; peak 실측 |
| 거짓 지능 개선 | 장문·위키 형식은 좋아지고 정답은 그대로 | 내용 정확도 primary, 형식·유창성 분리 |
| 출력 랭크의 미사용 | 새 rank에 gradient만 있고 성능 이득 없음 | E-only ablation, head 연산 증가까지 포함한 채택 |
| QK 포화 | tau 상한 집중, 검색형 문항만 좋아짐 | bounded tau, layer/head 통계, 과제별 성능 |
| 배포 숫자 혼합 | 작은 LUT 메모리와 다른 int8 경로 속도를 결합 | 하나의 실행 경로·dtype·context에서 동시 측정 |
| 다중 비교·선택 편향 | 6팔 중 우연 최고를 바로 확정 | 별도 seed·고정 confirmation panel·실패도 기록 |
| 검증능력 선결의 무한 확장 | 새 벤치 제작만 반복하고 개선 학습 안 함 | 평가 패널 1회 고정; 새 데이터셋 구축을 선결로 두지 않음 |

효과가 없다고 교사 반복 이식이나 임의의 새 코퍼스로 자동 전환하지 않는다. 별도 분석 문서의 외부 정답 기반 개선안은 별도 승인 항목이다.

---

## 9. 대안

| 안 | 무엇 | 장점 | 단점 |
|---|---|---|---|
| **A** | C0 18층 1.2B 조합만 만든다 | 대부분 기존 코드·실험 부품 사용 | 새로운 지능 학습 신호는 없고 한영 평가 한계가 남음 |
| **B** | **M0에서 U2와 MTP를 분리한 6팔의 bounded 설계를 우선한다. C0는 독립 선택 항목** | 새 데이터셋 없이 표현력·학습목표를 구분, 추가 부품을 검증 후에만 합침 | 모델/학습 구현 및 gradient 검증 필요 |
| **C** | 변경 없이 M0를 사용한다 | 신규 GPU·개발 비용 0 | 이번 구조·목표 변경의 가치를 알 수 없음 |

### 권장안과 근거

**B를 권장한다.** C0를 먼저 완성해야만 개선 실험을 할 수 있다는 불필요한 선결을 제거하고, M0의 가중치와 코퍼스를 활용해 실제 기여를 분리한다. 결합 최종 후보는 **16층·E384·QK gain·MTP 훈련 / 배포 시 MTP 삭제**이지만, E-only·Q-only·MTP-only 중 일부가 음성이면 그 부품은 제외한다.

승인 단위는 **G0~G2 구현·작은 검사·100M 탐색**과 **G3/C0/G4**를 분리한다. 본 문서의 작성으로 어느 단계도 승인·완료 처리하지 않는다. 최종 선택은 구성의 복잡성이 아니라 **같은 배포 제약에서의 실제 답변 정확도와 재현성**에 따른다.


<!-- 본문 참조 식별자: 저장소 외부에서도 링크가 작동하도록 commit 고정 URL을 사용한다. -->
[L1]: https://github.com/myplmy/TinyLM/blob/ea363b34ebb42f3fb4a9bf3187467bc9df991223/test_result/078_20260911_P005b-RMS4는-jordan20을-이겼지만-한-형상이다.md
[L2]: https://github.com/myplmy/TinyLM/blob/ea363b34ebb42f3fb4a9bf3187467bc9df991223/test_result/078_log_20260916_P005b_stage12_rms_1200M_transfer.txt
[L3]: https://github.com/myplmy/TinyLM/blob/ea363b34ebb42f3fb4a9bf3187467bc9df991223/test_result/014_20260731003000_P030-CPU추론실측-양자화오버헤드.md
[L4]: https://github.com/myplmy/TinyLM/blob/ea363b34ebb42f3fb4a9bf3187467bc9df991223/handoff/COMPASS.md
[L5]: https://github.com/myplmy/TinyLM/blob/ea363b34ebb42f3fb4a9bf3187467bc9df991223/tinylm/model/transformer.py
[L6]: https://github.com/myplmy/TinyLM/blob/ea363b34ebb42f3fb4a9bf3187467bc9df991223/tinylm/model/modules.py
[L7]: https://github.com/myplmy/TinyLM/blob/ea363b34ebb42f3fb4a9bf3187467bc9df991223/tinylm/data/loader.py
[L8]: https://github.com/myplmy/TinyLM/blob/ea363b34ebb42f3fb4a9bf3187467bc9df991223/tinylm/train/trainer.py
[L9]: https://github.com/myplmy/TinyLM/blob/ea363b34ebb42f3fb4a9bf3187467bc9df991223/docs/EXPERIMENT_BASELINES.md
[E1]: https://arxiv.org/abs/2404.19737
[E2]: https://arxiv.org/abs/2010.04245
[E3]: https://arxiv.org/abs/1711.03953

---

## 10. 2026-09-24 타당성 재검토 — 원안 보존, 실행은 미승인

이 절은 1~9절을 소급 삭제하지 않는 후속 판독이다. 현 HEAD `6ced9a8`의 [모델](../tinylm/model/transformer.py)·[기준표](../docs/EXPERIMENT_BASELINES.md)·[기존 P006 MTP 계획](../test_plan/P006_MTP-학습aux-및-FastMTP추론.md)을 대조했다. 이 문서 검토만 수행했으며 구현·GPU·모델·런처는 `NOT_RUN`이다.

### 10.1 타당한 부분

| 원안 | 타당성·근거 | 한계 |
|---|---|---|
| M0로부터 E-only, QK-only, MTP-only를 분리 | 같은 부모·캐시·학습 토큰·질문으로 갈라야 기여를 해석할 수 있다 | 역사 M0의 영어 전용 full-val을 한국어 지능 기준으로 승격하지 않음 |
| E256→E384의 `W_new=[W,R], U_new=[U,0]` | 현재 `emb`·`emb_up`의 실수 선형곱은 학습 0에서 보존 가능 | BF16 커널 shape·양자화 export의 비트 동일성은 별도 검사 |
| RMSNorm 뒤 head별 QK gain | 현재 [Attention](../tinylm/model/modules.py)의 조절 지점으로 성립 가능한 TinyLM 변형 | [QKNorm](https://arxiv.org/abs/2010.04245)은 L2 정규화·학습 scale로서 이 설계와 동일 구현 아님 |
| 주 NTP와 분리한 미래 target·head·경계 mask | [MTP 연구](https://arxiv.org/abs/2404.19737)의 shared trunk·독립 head와 방향은 맞는다 | TinyLM 100M·한국어·배포에서 품질·무비용 효과는 미관측 |

### 10.2 필수 정정과 이유

1. **신규 C0 1.2B 학습은 지금 승인 가능한 단계가 아니다.** [기준표 1절](../docs/EXPERIMENT_BASELINES.md)은 새 기준 후보를 300M으로 두고, 600M draw는 한국어 학습·평가 gate 전 HOLD, 1.2B 학습 SH 작성은 금지한다. 원안의 실제 train pool 1.194B/1.200B draw 비율 약0.995는 풀≥2배도 만족하지 않는다. 과거 1.2B full-val은 한국어0%다. §6.2와 C0/G3의 1.2B는 **역사 설명·미래 가설**로만 유지한다. 새 런은 한국어 평가, 충분한 풀, 사용자 별도 예외 승인 전 `HOLD`다.
2. **MTP는 이미 [P006 Part A](../test_plan/P006_MTP-학습aux-및-FastMTP추론.md)가 소유한다.** E384 결합·horizon2/4·loss/gradient는 그 계획의 구체 후속 설계이지 새 번호를 선점할 최초 축이 아니다. 채택 시 P006 본문에 단계·예측·비용을 추가한다. P006 Part B의 추론 FastMTP와 학습용 aux는 별개다.
3. **C0와 U2는 층수만 다른 짝이 아니다.** C0는 20층 부모 role 초기화로 새 학습, U2는 M0 1.2B checkpoint의 계속학습이다. 둘의 CE·정답률 차이는 깊이 효과로 귀속 불가다. M0 기반 100M 탐색의 각 팔끼리도 동일 draw 위치·schedule horizon·질문 ID·원답안 채점을 고정해야 한다. 100M 1시드는 방향·기능 gate이지 일반 지능 승격이 아니다.
4. **40MiB는 예산식이다.** 원안의 추가 `4.375MiB`를 반올림된 `34.0MiB`에 더하면 약`38.375MiB`, 잔여 약`1.625MiB`뿐이다. scale·alignment·codec metadata·실행 버퍼·RSS를 포함하지 않는다. export한 **같은 실행 경로**에서 메모리·속도·답변을 동시 측정하기 전에는 40MiB PASS로 쓰지 않는다.
5. 외부 MTP·QKNorm 논문은 설계 동기다. 우리 RMSNorm+bounded gain, 저랭크 shared head, 한국어 질문의 효과는 `NOT_RUN`이다.

### 10.3 실제 다음 결정 3안

| 안 | 방법 | 장점 | 대가·리스크 | 현재 판단 |
|---|---|---|---|---|
| A | M0에서 같은 역사 cache와 부모로 **100M 이하** E/QK/MTP 분리 대조 | 새 1.2B 학습 없이 기능·방향 확인 | 기존 corpus의 한국어 편향, 지능 확정 불가 | **조건부 첫 단계** |
| B | C0와 맞춤 16층 대조를 같은 부모·한영 pool로 **300M씩** 새 학습 | 층수 효과를 직접 시험 | M0 역사값과 paired 비교 불가, GPU 비용 | 한국어 gate 뒤 별도 승인 |
| C | 원안 C0 1.2B를 바로 진행 | 역사 M0 학습량과 표면상 일치 | 풀≥2배·한국어 gate·SH 금지 위반 | 지금은 불가 |

**권장: A의 정적·작은 기능 gate부터.** 실제 학습은 별도 승인 후 P006의 후속 계획에서 토큰 산식, pool/val 언어비, 태그 충돌을 preflight한다. C0/B는 대응 16층 대조를 갖춘 뒤 판단한다.

> 이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.
## 11. 2026-09-24 사용자 승인과 구현·검증 경계

사용자가 §10의 권장 첫 단계인 **작은 기능 게이트부터 진행**을 승인했다. 별도 [P101A 계획](../test_plan/P101A_M0-U2-QK-MTP-기능계약.md)과 사용자 실행 [Stage0W SH](../run_P101A_Stage0W_u2_mtp_function_gate.sh)를 만들었다. E384 함수 보존과 EOS를 넘지 않는 MTP 표적은 CPU tensor fixture에서, QK gain은 기본 off인 opt-in 모델 경로와 소형 모델 게이트 코드에서 분리했다. CPU 수학 fixture는 PASS; 실제 소형 모델 게이트·M0 checkpoint 이관·GPU/품질은 NOT_RUN이다.

현재 승인 범위의 **전체 구현 완료가 아니다**. 독립 MTP aux head와 trunk/공유 어휘 gradient, 같은 유효 배치의 loss 집계, 실제 M0 함수 보존 이관, G2의 품질·속도 비교는 남아 있다. 신규 C0 1.2B 학습 SH는 기준표의 한국어/풀 제약에 따라 만들지 않는다. 이 종료조건 때문에 `-approved-on-going`을 유지한다.

## 12. 2026-09-24 막힘 상태 재감사 — 구현과 사용자 검증 분리

이전 WIP 3A가 실제 소형 모델·M0 로그 부재를 이유로 전체 `막힘`이 된 것은 범위가 넓었다. 사용자 실행 [Stage0W](../run_P101A_Stage0W_u2_mtp_function_gate.sh)의 로그는 **작성된 코드의 함수·gradient 판정과 G2 실행 개방**에 필요하다. 독립 MTP aux head, 공유 어휘 gradient, 유효토큰 분모와 배포 제거의 기본 off 구현을 작성하지 못하게 하는 권한·기술적 선결은 아니다. 사용자 승인 A안의 구현 요청을 §11의 '작은 gate만'으로 축소해 읽은 부분은 교정한다.

| 구분 | 현재 직접 증거 | AI 작업 / 사용자 증거의 경계 |
|---|---|---|
| 작성된 코드 | E/QK strict 이식, 독립 MTP aux head·배포 payload 제거, FP32 3-head loss/공유 emb gradient CPU 계약 | 실제 M0·작은 모델 gate는 NOT_RUN, 전체 trainer·계속학습 경로는 미구현. GPT 작업을 계속한다 |
| 사용자 검증 | Stage0W 소형 모델, 실제 M0 hash/함수 | Codex 모델 로딩 금지 때문에 사용자 결과가 필요하지만 코드 집필 전체의 정지 사유는 아님 |
| 채택·G2 | 같은 부모·풀·어닐·optimizer와 100M 대응 팔 | Stage0/G1 PASS 및 GPU 실행 뒤에만 효과 판정. 1.2B/C0 런처는 종전 금지 유지 |

현재 제안서는 `approved-on-going`이다. WIP는 GPT 구현 중으로 유지하고, 동적 `NOT_RUN`과 필요한 사용자 로그는 이 절 및 [P101A 계획](../test_plan/P101A_M0-U2-QK-MTP-기능계약.md)에 기록한다. 작은 CPU 계약 PASS를 실모델 기능 완료나 지능 향상으로 승격하지 않는다.
