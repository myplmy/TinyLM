# 제안 — Scout + 1 MiB 장기기억을 먼저 더해 학습가능성부터 검증한다

> **작성** 2026-09-16 · **상태** 🔄권장안 A 승인·S0 대기 · **분류** 실험계획
> 양식: `proposal/README.md` §3. 아홉 절을 모두 작성한다.
> 저장소 기준: `AGENTS.md` → 최신 유효 handoff → `handoff/COMPASS.md` → `docs/EXPERIMENT_BASELINES.md` → 실제 코드·결과문서 순으로 대조한다.
> 🚫 **이 문서는 제안서다. 승인 전에는 구현·학습·배치파일 생성을 시작하지 않는다.**
>
> **승인 기록(2026-09-18):** 사용자가 권장안 A를 승인했다. 실험계획은
> [P095](../test_plan/P095_Scout-1MiB-LTM-학습가능성.md)로 이관했다. S0 causal-isolation과
> 물리 회계, 구현·smoke·GPU·배치·재현은 남아 있어 `-approved-on-going` 상태다.
>
> **제안 핵심:** 기존 TinyLM backbone을 줄이거나 tying으로 비용을 먼저 상쇄하지 않는다.
> 기존 모델에 작은 causal Scout와 **논리적 배포용량 1 MiB의 explicit long-term memory(LTM)** 를 그대로 추가하여,
> 1. 기억을 쓸 수 있는가,
> 2. 충분히 지연된 뒤 다시 찾을 수 있는가,
> 3. 실제 출력이 그 기억에 인과적으로 의존하는가,
> 4. learned WRITE 및 KV→LTM consolidation까지 학습 가능한가
>
> 를 싼 순서대로 검증한다.
>
> **동예산 Pareto 비교는 위 기능이 성립한 뒤의 후속 단계로 미룬다.**

---

## 1. 배경 — 왜 지금 이 제안을 하나

TinyLM은 현재 저사양 CPU·엣지 환경에서 제한된 상주 메모리 안에 최대한 높은 품질을 넣는 연구를 진행하고 있다. 최신 `handoff/COMPASS.md` 기준으로 plain MLP tying과 plain attention tying은 현 조건에서 품질 대가 때문에 배포 레버로 기각되어 있고, CLA/KV는 여전히 가장 유망한 메모리 축 중 하나다. 따라서 새로운 장기기억 구조를 처음부터 MLP/attention tying과 결합하면 **새 memory 구조의 실패와 tying의 기존 품질 손실이 교락**된다.

지금까지의 논의에서 제안된 구조는 다음 네 요소를 가진다.

1. **Main path**
   - 기존 TinyLM Transformer는 정상적인 causal LM 경로를 그대로 유지한다.
   - 새 구조가 실패하더라도 기존 추론경로 자체가 없어지지 않는다.

2. **Scout path**
   - main Transformer의 middle representation을 매우 좁은 semantic bottleneck으로 관찰한다.
   - Scout 자체도 causal하게 앞 단계의 관찰 상태를 누적한다.
   - 최종적으로 장기기억 검색 query와 memory-use gate를 만든다.

3. **1 MiB explicit LTM**
   - raw token span과 압축 activation을 함께 보존한다.
   - activation은 빠른 retrieval/read용 cache이고 token은 provenance 및 activation refresh용 canonical representation이다.
   - 장기적으로는 working KV에서 퇴출되는 중요 정보를 LTM으로 consolidation하는 것을 목표로 한다.

4. **Coda 직전 gated fusion**
   - main final state와 Scout/LTM readout을 low-rank gated residual로 합친다.
   - memory가 없거나 검색이 불확실할 때 memory gate가 0에 가까워질 수 있어야 한다.

그러나 이 구조에 대해서는 현재 TinyLM에서 가장 기본적인 질문조차 `NOT_RUN`이다.

> **1 MiB 정도의 매우 작은 memory와 작은 Scout를 기존 모델에 추가했을 때, write → retrieve → use 회로 자체를 실제 gradient descent가 학습할 수 있는가?**

이 질문을 건너뛰고 곧바로 한 층을 줄이거나 MLP tying으로 1 MiB를 상쇄하면 결과가 나쁠 때 원인을 분리할 수 없다.

따라서 본 제안의 첫 단계는 **메모리 효율성이나 40 MiB 적합성 판정이 아니라 functional learnability 판정**이다.

---

## 2. 목적 — 무엇을 알아내거나 얻으려 하나

**기존 TinyLM backbone에 작은 Scout와 논리적 1 MiB LTM을 추가한 상태에서, 새로운 episodic information을 기록하고 충분한 delay 뒤에 검색해 실제 next-token prediction에 사용하는 회로가 학습 가능한지 인과적으로 검증한다.**

### 2.1 주 독립변수

초기 단계에서는 backbone을 바꾸지 않고 memory 조건만 바꾼다.

| 조건 | Scout | LTM | 의미 |
|---|---|---|---|
| BASE | 없음 | 없음 | 기존 모델 |
| S | 있음 | 없음 | Scout parameter 자체의 효과 |
| M | 있음 | 정상 | 정상 Scout + LTM |
| M-SHUFFLE | 있음 | value/key shuffle | 정보 없는 memory control |
| M-REMOVE | 있음 | 정답 memory 제거 | causal ablation |
| M-NULL | 있음 | 관련 memory 없음 | false retrieval 측정 |

후속 단계에서만 다음 축을 연다.

- oracle WRITE → learned WRITE
- explicit memory hint → hint 제거
- episode-local → batch/session persistent
- fixed candidate → KV-derived candidate
- append-only → dedup/UPDATE/EVICT

### 2.2 이번 제안에서 일부러 답하지 않는 것

초기 단계는 다음을 판정하지 않는다.

- 같은 32/40 MiB에서 한 층을 더 쓰는 것보다 LTM이 우수한가
- MLP tying으로 LTM 비용을 상쇄하는 것이 좋은가
- CPU deployment에서 최종 tok/s가 빨라지는가
- 1 MiB가 최적 memory 크기인가
- 장기 persistent memory가 수십만 optimizer step을 견디는가

이 질문들은 **memory 회로가 실제로 학습된 뒤**에만 의미가 있다.

---

## 3. 성과물 — 승인하면 무엇이 생기나

| 산출물 | 형태 |
|---|---|
| 실험계획 | 승인 후 다음 빈 P번호의 `test_plan/P0NN_...md` |
| Scout 최소 구현 | shared semantic bottleneck + causal Scout state + query head |
| 논리적 1 MiB LTM | token arena + semantic key/value arena |
| memory-specific synthetic benchmark | unseen episodic fact / absent / similar / conflict 세트 |
| causal memory controls | normal / shuffle / remove / null memory 비교 |
| oracle-WRITE 경로 | 기억 위치를 알고 있을 때 READ/FUSION 학습성 검증 |
| learned-WRITE 경로 | explicit hint → hint annealing |
| dedup prototype | exact token hash → semantic duplicate 후속 |
| KV consolidation prototype | working KV candidate → KEEP / CONSOLIDATE / DISCARD |
| memory telemetry | recall@k, write rate, duplicate rate, memory occupancy, gate, hit/miss |
| staleness telemetry | memory age/encoder version별 retrieval hit |
| 일반 LM 비교 | memory arm과 같은 backbone의 val CE/bpb 비교 |
| 최종 판정 | 학습 불가 / 기능만 성립 / LM에 유효 / 후속 동예산 실험 가치 있음 |

성과가 양성일 경우 다음 연구의 질문이 바뀐다.

> “이런 memory가 가능한가?”
> 에서
> **“고정 32/40 MiB 중 몇 MiB를 weight/KV/LTM에 배분하는 것이 가장 유리한가?”**

로 이동한다.

---

## 4. 비용

절대 GPU 시간은 승인 후 `exp-preflight`에서 당시 표준 baseline의 실제 시간을 다시 확인한다.

`H300`을 **같은 장비·같은 당시 표준조건으로 300M token baseline 1회를 학습하는 GPU 시간**으로 정의한다.

| 항목 | 양 |
|---|---:|
| Stage 0 계약·shape·회계 | ⚙ 2–4 engineer-h, GPU 0 |
| Stage 1 synthetic overfit | ⚙ ≤0.02 H300 |
| Stage 2 unseen episodic test | ⚙ ≤0.03 H300 |
| Stage 3 learned WRITE | ⚙ 0.03–0.08 H300 |
| Stage 4 dedup/persistence | ⚙ 0.03–0.10 H300 |
| Stage 5 KV→LTM consolidation | ⚙ 0.05–0.15 H300 |
| Stage 6 30M-token LM screen | ⚙ 약 0.3–0.5 H300, 대조군 수에 따라 변동 |
| Stage 7 100M-token transfer | ⚙ 약 0.7–1.3 H300 |
| Stage 8 300M-token 본비교 | ⚙ 조건부 2–4 H300 |
| 최초 권장 경로 | ⚙ 약 1.0–1.8 H300 |
| 최악 조건부 상한 | ⚙ ≤5 H300 |
| AI 구현·계측·분석 | ⚙ 10–18 engineer-h |
| 사용자 직접 작업 | 승인 + GPU batch 실행 + 로그 회신 |
| 신규 외부 dataset | 0 B |
| synthetic benchmark | ⚙ 수 MB 이하 |
| checkpoint 추가 공간 | ⚙ 기존 보존정책에 따라 수 GB |

### 4.1 1 MiB는 “논리적 deployment budget”으로 시작한다

학습 시 모든 memory tensor를 처음부터 INT8로 연산할 필요는 없다.

배포 목표는 다음과 같이 고정한다.

- 총 LTM logical capacity: **1 MiB = 1,048,576 bytes**
- token arena: 약 **256 KiB**
- semantic arena: 약 **768 KiB**
- vocab 32,768이므로 token ID는 `uint16`으로 표현 가능
- token arena 최대량: 약 **131,072 token IDs**
- memory key: 초기 **64-d**
- memory value: 초기 **128-d**
- deployment-equivalent slot: 약 208–224 bytes 목표
- semantic slot 수: 대략 **3.5K–3.8K**

학습 중 gradient 안정성을 위해 bf16/fp32 tensor를 사용하더라도 **slot 수와 logical byte budget은 위 값에 고정**한다.

실제 INT8 storage/kernel은 기능 검증 후 별도 deployment 단계에서 연다.

---

## 5. 원리·근거

### 5.1 우리 저장소의 현재 근거

| 근거 | 상태/값 | 출처 |
|---|---|---|
| 기본 hidden width | `dim=768` | `tinylm/config.py` |
| GQA | Q12 / KV3 | `tinylm/config.py` |
| factorized embedding | `emb_rank=256` | `tinylm/config.py` |
| middle CLA | `cla_group` 구현됨 | `tinylm/config.py`, `transformer.py` |
| MLP plain tying | 현 조건 g2·g4 모두 dense보다 열세 | `handoff/COMPASS.md`, P045B |
| attention tying | ag2도 현 ruler 밖 열세 | `handoff/COMPASS.md`, P045B |
| CLA/KV | 최신 COMPASS에서 유력 memory lever | `handoff/COMPASS.md` |
| KV dtype | fp32/bf16/fp16 저장경로 존재 | `tinylm/config.py` |
| 현재 optimizer | RMS4 기본 후보지만 seed/토큰 전이 남음 | `handoff/COMPASS.md`, P005b |
| 연구 기본 규칙 | 관측/계산/해석/제안/수행 분리 | `AGENTS.md` |

따라서 Stage 0–6에서는 **main MLP/attention tying을 신규 독립변수로 넣지 않는다.**

Scout/LTM 효과가 검출된 뒤에만 memory 비용 상쇄 실험에서 relaxed/local MLP tying을 재검토한다.

### 5.2 외부 근거

#### R1. LongMem — Wang et al., NeurIPS 2023

- 제목: *Augmenting Language Models with Long-Term Memory*
- arXiv: `2306.07174`
- 핵심: frozen backbone + adaptive residual SideNet + 외부 장기기억.
- 가져올 부분:
  - main path와 작은 side path의 분리
  - 장기기억 retrieval/reader 역할 분리
  - memory staleness를 architecture 수준에서 명시적으로 다룬 점
- 그대로 가져오지 않을 부분:
  - frozen backbone
  - 대규모 past-context KV bank

#### R2. Memorizing Transformers — Wu et al., 2022

- arXiv: `2203.08913`
- 핵심: 과거 internal representation을 non-differentiable `(key,value)` memory에 저장하고 kNN 검색.
- 가져올 부분:
  - internal activation을 memory value로 재사용 가능하다는 근거
  - retrieval 자체가 LM loss에 유의미하게 기여할 수 있다는 근거
- 그대로 가져오지 않을 부분:
  - 매우 큰 recent-memory bank
  - LTM write/evict를 명시적으로 학습하지 않는 구조

#### R3. Dynamic Memory Compression — Nawrot et al., ICML 2024

- arXiv: `2403.09636`
- 핵심: KV compression ratio를 layer/head별로 학습하고 GQA와 결합 가능.
- 가져올 부분:
  - KV compression을 고정 heuristic 대신 학습 가능하게 만드는 관점
  - CLA/GQA와 KV compression을 독립적으로 조합하는 관점
- 본 제안에서의 역할:
  - Stage 5의 `KEEP / CONSOLIDATE / DISCARD` 학습 설계 근거

#### R4. Activation Beacon — Zhang et al., ICLR 2025

- arXiv: `2401.03462`
- 핵심: raw token 요약 대신 각 layer의 K/V activation을 직접 압축.
- 가져올 부분:
  - KV/activation을 장기적인 compact state로 변환할 수 있다는 근거
  - 다양한 compression ratio로 학습하는 curriculum
- 그대로 가져오지 않을 부분:
  - 모든 layer별 압축 KV를 LTM에 저장하는 방식

#### R5. ChunkKV — Liu et al., 2025

- arXiv: `2502.00299`
- 핵심: 개별 token보다 semantic chunk 단위로 KV를 선택하며 layer 간 preserved index 재사용을 제안.
- 가져올 부분:
  - LTM WRITE candidate를 token 하나가 아니라 chunk 단위로 만든다.
  - CLA group과 Scout observation/consolidation group을 정렬하는 후속 근거로 사용한다.

#### R6. R-KV — Cai et al., NeurIPS 2025

- arXiv: `2505.24133`
- DOI: `10.52202/085713-2038`
- 핵심: importance뿐 아니라 key-vector redundancy를 함께 보고 KV를 보존.
- 가져올 부분:
  - “중요하지만 중복된 정보”와 “새로운 정보”를 구분
  - LTM dedup/WRITE 판단의 feature
- 주의:
  - reasoning model의 긴 decode 상황에서 나온 결과를 TinyLM pretraining에 직접 일반화하지 않는다.

#### R7. IndexMem — Yang et al., 2026

- arXiv: `2605.25475`
- 핵심: learnable KV indexer가 중요도를 판단하고, eviction되는 정보를 완전히 버리지 않고 compact latent memory로 넘긴다.
- 본 제안과 가장 직접적으로 연결되는 부분:
  - **working KV → eviction candidate → latent memory**라는 계층
  - eviction과 forgetting을 분리하는 설계
- 차이:
  - 본 제안은 bounded explicit slots, token provenance, FOUND/ABSENT/CONFLICT supervision을 추가한다.

#### R8. Bottlenecked Transformers — Oomerjee et al., ICLR 2026

- 핵심: Cache Processor가 최근 KV를 consolidation하고 일부 과거 KV를 reconsolidation.
- 가져올 부분:
  - 새 memory를 단순 append하지 않고 기존 memory와 비교해 UPDATE하는 개념
  - consolidation을 매 token이 아니라 특정 boundary에서 수행
- 그대로 가져오지 않을 부분:
  - 큰 auxiliary Transformer Cache Processor
  - 모든 retrieval에서 memory를 자동 재작성하는 정책

### 5.3 현재 가설

외부 연구를 종합하면 다음 각각은 이미 별도로 성립한 선례가 있다.

- side-network
- internal-activation memory
- KV compression
- chunk compression
- redundancy-aware retention
- evicted-KV latent memory
- memory consolidation

하지만 TinyLM에서 제안하는 다음 조합은 별도로 검증해야 한다.

> **아주 작은 1 MiB bounded memory + layer-observing causal Scout + explicit presence/absence supervision + token/activation dual storage + KV→LTM consolidation**

따라서 기존 연구를 이유로 성공을 전제하지 않는다.

---

## 6. 방법

### 6.1 v0 아키텍처 — 처음부터 모든 기능을 넣지 않는다

#### Main path

기존 TinyLM backbone을 그대로 실행한다.

```text
tokens
  ↓
Prelude
  ↓
Middle
  ↓
main final H
  ↓
[Coda 직전 fusion]
  ↓
Coda
  ↓
logits
```

Stage 1–6에서는 main layer 수·폭·MLP tying·attention tying을 변경하지 않는다.

#### Scout observation

초기 기본:

```text
middle hidden 768
      ↓
shared RMSNorm
      ↓
shared 768 → 96 bottleneck
      ↓
96-d Scout state
```

CLA2 baseline이면 두 middle layer당 한 번 관찰하는 방식을 1차 후보로 한다.

즉 16 middle layer라면 최대 8회의 Scout update다.

필요하면 각 group의 endpoint뿐 아니라

```text
delta = h_end - h_start
```

를 feature로 추가하되 Stage 1에서 필수로 만들지 않는다.

#### Scout

첫 버전은 작은 2차 Transformer를 만들지 않는다.

- state dimension: 96
- gated recurrent/MLP cell: 1개 공유
- memory query: 64-d
- 모든 middle observation에 같은 Scout cell을 tying
- 모든 layer tap에 같은 bottleneck projector를 tying

즉 tying은 main capacity를 줄이는 데 쓰지 않고 **반복 역할을 하는 보조 subsystem 내부에서 적극적으로 사용**한다.

#### LTM

```text
Token Arena
- raw token IDs
- variable-length span

Semantic Arena
- key: 64-d
- value: 128-d
- token offset
- token length
- utility
- age
- confidence
- encoder version
- flags
```

검색:

```text
q[64] × keys[N,64]
→ exact full scan
→ top-8
→ tiny reranker
→ top-2~4 read
```

약 3.5K slot 규모에서는 graph/HNSW/ANN을 사용하지 않는다.

#### Fusion

```text
H_fused =
    H_main
  + g_s · U_s(Scout)
  + g_m · U_m(MemoryRead)
```

`U_s`, `U_m`은 작은 low-rank projection으로 제한한다.

초기 gate bias는 main-path 보존 방향으로 둔다.

Memory/Scout가 필요하지 않으면 `g_s`, `g_m`이 0에 가까워질 수 있어야 한다.

---

### 6.2 단계 설계

| 단계 | 무엇 | 비용 | ★다음으로 가는 조건 |
|---|---|---:|---|
| **Stage 0 — 계약/회계** | shape, causal mask, 1 MiB logical capacity, empty/full/reset, deterministic retrieval, no-memory fallback | GPU 0 | 정적/단위 계약 전부 PASS |
| **Stage 1 — oracle WRITE overfit** | 정답 memory span을 강제로 WRITE. READ+retrieval+fusion만 학습 | ≤0.02 H300 | train QA ≥99%, recall@4 ≥99%, REMOVE/SHUFFLE에서 성능 붕괴 |
| **Stage 2 — unseen episodic facts** | 매 episode 새 nonce 관계. 학습에서 본 적 없는 key-value 테스트 | ≤0.03 H300 | 정상 memory가 BASE/S/REMOVE보다 ≥30pp 우세, recall@4 ≥90% |
| **Stage 3a — explicit learned WRITE** | “기억해”, “A는 B야”, 계획/상태 지시가 있는 episode | 0.03–0.05 H300 | WRITE F1 ≥95%, QA가 oracle arm의 10pp 이내 |
| **Stage 3b — hint annealing** | explicit hint 100→50→20→0% | 추가 ≤0.03 H300 | hint 0%에서도 oracle 성능의 ≥80% 유지 |
| **Stage 4a — exact dedup** | token hash 동일 memory는 새 slot 금지, TOUCH | GPU 거의 0 | exact duplicate slot rate <1% |
| **Stage 4b — semantic dedup** | nearest-key + compatibility → UPDATE/ALLOCATE/CONFLICT | 0.03–0.05 H300 | 중복 slot ≥50% 감소, QA 저하 ≤2pp |
| **Stage 4c — persistence** | reset-each-episode / batch / multi-batch 수명 랜덤화 | ≤0.05 H300 | 수명 증가 시 원인불명 collapse 없음; staleness telemetry 확보 |
| **Stage 5a — KV candidate** | working KV를 chunk 단위 후보로 만들기. 아직 eviction 없음 | ≤0.03 H300 | 필요한 chunk recall 측정 가능 |
| **Stage 5b — consolidation** | `KEEP / CONSOLIDATE / DISCARD`; CONSOLIDATE만 LTM으로 이동 | 0.05–0.10 H300 | eviction-only보다 memory-dependent QA 유의 개선 |
| **Stage 5c — working-KV 축소** | 20–25% KV budget 감축 시작 | ≤0.05 H300 | full-KV 대비 memory task 저하 ≤5pp 또는 eviction-only보다 명확 우세 |
| **Stage 6 — 30M LM screen** | 같은 backbone의 BASE/S/M/M-SHUFFLE | 0.3–0.5 H300 | M만 memory task 향상 + 일반 LM catastrophic regression 없음 |
| **Stage 7 — 100M transfer** | 살아남은 2~3 arm | 0.7–1.3 H300 | 당시 `_rulers.py` 기준 non-inferior 이상 또는 일반 LM까지 개선 |
| **Stage 8 — 300M 본비교** | 조건부 2~4 arm, seed 후속 | 2–4 H300 | 기능·품질 모두 생존했을 때만 |

---

### 6.3 Stage 1/2 synthetic memory task

Main weight가 사실 자체를 암기하는 shortcut을 막기 위해 **episode마다 관계를 새로 생성**한다.

예:

```text
이번 episode:
"루덴-483의 표식은 자색-27이다."

[distractor / delay]

질문:
"루덴-483의 표식은?"
```

다음 episode에서는 동일한 표면어의 관계를 바꿀 수 있다.

```text
"루덴-483의 표식은 청색-91이다."
```

따라서 weight에 고정 사실을 저장하는 전략으로는 unseen episode에서 성공할 수 없다.

초기에는 답 후보 vocabulary를 제한하여 chance level을 정확히 계산하고, 이후 free generation으로 확대한다.

---

### 6.4 memory가 실제로 사용됐는지 인과적으로 검증

정상 memory arm만 좋아졌다고 끝내지 않는다.

같은 입력에서:

```text
M-NORMAL
M-REMOVE
M-SHUFFLE-KEY
M-SHUFFLE-VALUE
M-NULL
```

를 비교한다.

필수 telemetry:

- recall@1 / @4 / @8
- retrieved slot ID
- memory gate
- Scout gate
- answer CE
- answer accuracy
- top1–top2 retrieval margin
- no-match probability

정상 memory와 제거/shuffle memory가 같은 성능이면:

> **memory를 실제로 사용하지 않은 것**

으로 판정한다.

---

### 6.5 FOUND와 UNKNOWN을 분리

Scout가 학습할 상태:

```text
MEM_FOUND
MEM_ABSENT
MEM_SIMILAR
MEM_CONFLICT
```

최종 answerability:

```text
ANSWERABLE
AMBIGUOUS
UNKNOWN
```

은 별도 head/feature로 둔다.

즉:

```text
MEM_ABSENT ≠ UNKNOWN
```

이다.

Main Transformer의 parametric knowledge만으로 답할 수 있기 때문이다.

counterfactual memory training에는 동일 query를 다음 조건으로 만든다.

1. 정확한 A 존재
2. A 없음
3. A는 없고 유사 B만 존재
4. 충돌 A/A' 존재

---

### 6.6 WRITE curriculum

초기에는 explicit supervision을 허용한다.

```text
"이것을 기억해: A는 B다."
"앞으로 C를 할 예정이다."
"B는 A를 뜻한다."
```

이후 lexical shortcut을 제거하기 위해 hint 비율을 낮춘다.

```text
100% → 50% → 20% → 0%
```

negative example도 반드시 넣는다.

```text
"이 값은 이번 계산에만 쓰고 기억할 필요는 없다."
```

WRITE objective는 next-token CE만으로 맡기지 않고 별도 write target을 둔다.

후기에는 실제 future loss reduction을 보조 target으로 추가할 수 있다.

---

### 6.7 duplicate 처리

첫 구현:

```text
exact token hash match
→ TOUCH
```

기능 성립 후:

```text
candidate C
   ↓
nearest existing key M
   ↓
similarity + compatibility
   ├─ same information → TOUCH
   ├─ same subject + extension → UPDATE
   ├─ contradiction → CONFLICT
   └─ novel → ALLOCATE
```

controller action 후보:

```text
DROP
TOUCH
UPDATE
ALLOCATE
CONFLICT
```

conflict memory는 latent 평균으로 합치지 않는다.

---

### 6.8 KV cache → LTM consolidation

이 단계는 **READ/WRITE 자체가 성공한 후에만** 연다.

1차 memory source는 raw KV 전체가 아니라 chunk candidate다.

```text
working KV
   ↓
recent chunk staging
   ↓
importance + redundancy + Scout features
   ↓
KEEP / CONSOLIDATE / DISCARD
```

- KEEP: working KV에 계속 유지
- CONSOLIDATE: temporal compression 후 LTM으로 이동
- DISCARD: 제거

compression 입력:

```text
chunk token order
+
bottleneck activations
```

compression 연산 후보:

- mean/attention pooling — 가장 단순한 baseline
- 작은 temporal Conv1D — token/chunk 축에만 사용
- gated pooling — 후속

🚫 latent feature dimension 자체를 공간축으로 간주한 Conv1D retrieval은 사용하지 않는다.

Scout의 memory retrieval은 64-d correlation/full scan으로 유지한다.

---

### 6.9 memory staleness

초기 episode-local memory에서는 representation drift가 사실상 없다.

multi-batch persistence를 열 때부터 다음을 저장한다.

```text
raw token span       = canonical source
cached key/value     = fast path
encoder_version      = staleness telemetry
```

오래된 activation이 의심되면 raw token을 현재 bottleneck으로 다시 encode할 수 있다.

Stage 4c에서:

- age bucket별 recall@k
- optimizer step distance별 recall
- refresh 전/후 hit rate

를 기록한다.

staleness가 실제로 관측되기 전에는 EMA encoder나 별도 frozen encoder를 추가하지 않는다.

---

### 6.10 main-model tying은 이번 1차 실험에서 열지 않는다

최신 TinyLM 실측상:

- plain MLP g2/g4는 현재 조건에서 열세
- attention ag2도 현재 ruler 밖 열세
- CLA는 상대적으로 유력

따라서 v0는:

```text
main MLP tying 신규 변경 없음
full attention tying 신규 변경 없음
CLA는 당시 표준조건 유지
```

로 한다.

반대로 **auxiliary subsystem은 강하게 tying**한다.

- 모든 middle tap → 동일 bottleneck
- 모든 tap → 동일 Scout cell
- 모든 memory candidate → 동일 consolidator
- layer relevance key와 LTM key → 동일 64-d 검색 공간 후보

Scout/LTM이 생존한 뒤 비용을 상쇄해야 할 경우에만:

```text
localized MLP sharing
+
layer-wise low-rank LoRA
```

를 별도 후속 실험으로 연다.

그 단계는 이번 제안의 성공 조건이 아니다.

---

### 6.11 일반 LM 단계의 baseline 잠금

현재 COMPASS에서 optimizer 축이 아직 완전히 종결되지 않았으므로 이 제안서에 특정 optimizer/tag를 영구적으로 박지 않는다.

Stage 6 직전 `exp-preflight`에서:

1. 최신 `handoff/COMPASS.md`
2. 최신 유효 HANDOFF
3. `docs/EXPERIMENT_BASELINES.md`
4. `scripts/_rulers.py`
5. run registry

를 다시 확인한다.

그 시점의 **동일 architecture / tokenizer / corpus / pool / token budget / optimizer / seed** 조건으로 BASE와 memory arm을 만든다.

독립변수는 한 문장으로:

> **Scout/LTM memory path의 존재와 memory condition만 다르다.**

라고 쓸 수 있어야 Stage 6을 연다.

---

## 7. 거절하면 못 하는 것

거절해도 기존 TinyLM 연구는 계속할 수 있다.

P005b optimizer 전이, P091, P092, SFT 및 기존 depth/width/CLA 연구에는 필수 선결이 아니다.

다만 다음 질문은 답하지 못한다.

> **TinyLM처럼 매우 작은 모델에서도 수천 개 slot 규모의 explicit activation/token memory를 main Transformer와 병렬로 학습시켜, weight에 없는 episodic information을 실제 출력에 사용하게 할 수 있는가?**

또한 현재 KV cache에서 제거되는 정보를 단순히 버리는 대신 약 1 MiB의 고밀도 장기기억으로 재배분하는 연구축도 열 수 없다.

따라서 본 제안은 **기존 연구를 막는 필수과제는 아니지만, 별도의 memory architecture 축을 열기 위한 선결실험​**이다.

---

## 8. 위험 — 실행하면 무엇이 잘못될 수 있나

| 위험 | 어떻게 드러나나 | 완화 |
|---|---|---|
| Scout-only capacity 효과 | Scout만 붙여도 M과 같은 개선 | S arm을 반드시 둔다 |
| memory 무시 | normal/shuffle/remove 성능이 동일 | causal ablation을 Stage 1부터 강제 |
| memory shortcut | 정답 span을 복사하는 것만 학습 | unseen episodic fact와 hint 제거 |
| never-write collapse | write rate ≈0 | oracle → explicit WRITE curriculum |
| write-everything collapse | memory 즉시 포화 | write cost / fixed slots / negative examples |
| gate collapse | memory gate 항상 0 또는 1 | 초기 main-preserving bias + memory dropout |
| duplicate explosion | 같은 사실이 slot 다수 점유 | exact hash부터 단계적 dedup |
| false merge | 비슷하지만 다른 정보를 UPDATE | conflict/hard-negative dataset |
| staleness | 오래된 memory hit rate 급락 | token canonical source + version telemetry |
| activation leakage | 미래 token 정보가 memory에 들어감 | 모든 WRITE/read에 causal boundary 단위시험 |
| synthetic-only 성공 | toy QA는 성공, LM은 무효 | Stage 6/7 일반 LM gate |
| 일반 CE 희석 | rare memory benefit이 평균 CE에 안 보임 | memory-specific와 general LM 지표 분리 |
| KV importance 오용 | 현재 중요한 token만 LTM으로 들어감 | KV score는 WRITE candidate feature일 뿐 target 아님 |
| 1 MiB 회계 오류 | Python object overhead를 logical bytes로 오인 | logical budget과 physical RSS를 분리 기록 |
| retrieval 비용 과소평가 | top-k보다 full scan/gather가 병목 | key-bank bytes, MAC, latency 별도 계측 |
| current baseline drift | P005b 등으로 표준 조건 변경 | Stage 6 직전 preflight에서 baseline 재잠금 |
| 계측 오염 | 다른 pool/tokenizer/seed 비교 | run registry + condition signature 적용 |

### 8.1 가장 중요한 중단 조건

다음 중 하나면 30M 일반 LM 학습으로 넘어가지 않는다.

- Oracle WRITE에서도 synthetic task를 과적합하지 못함
- unseen episodic QA가 chance 부근
- M-NORMAL과 M-REMOVE/M-SHUFFLE 사이 차이가 없음
- Scout-only가 memory arm 개선을 전부 설명함
- causal leakage가 검출됨
- 1 MiB logical budget 계약이 깨짐

음성 결과는 실패가 아니라 다음을 의미한다.

> **현재 Scout/LTM 구성은 TinyLM에서 functional memory circuit으로 학습되지 않는다.**

이 자체가 연구 결과다.

---

## 9. 대안

| 안 | 무엇 | 장점 | 단점 |
|---|---|---|---|
| **A** | **기존 backbone + Scout + 1 MiB LTM을 그대로 추가하고 기능부터 검증** | 원인분리가 가장 깨끗함. 학습가능성 먼저 확인 | 일시적으로 32/40 MiB 목표를 넘을 수 있음 |
| **B** | 처음부터 KV를 줄여 그 공간에 LTM을 넣음 | deployment 목표에 직접 접근 | memory 실패와 KV compression 손실이 교락 |
| **C** | 처음부터 MLP tying으로 1 MiB 비용 상쇄 | 상주예산 유지 가능 | 현재 TinyLM에서 plain tying 열세가 이미 관측됨 |
| **D** | token-only RAG식 memory | staleness가 적고 구현 단순 | Scout/activation memory 가설을 직접 시험하지 못함 |
| **E** | activation-only memory | READ가 빠르고 작음 | 장기 persistence에서 refresh/provenance 취약 |
| **F** | graph memory | 관계 탐색 표현력이 큼 | 3–4K slot 규모에서 복잡도·pointer overhead 과다 |
| **G** | 아무것도 안 한다 | 비용 0 | bounded neural LTM 축을 검증하지 못함 |

### ★권장안과 근거

**A를 권장한다.**

지금 가장 먼저 답해야 하는 질문은:

> **“1 MiB memory를 어디서 마련할 것인가?”**

가 아니라

> **“그 1 MiB memory와 작은 Scout가 실제로 학습되어, 모델이 새로운 정보를 기억하고 다시 사용할 수 있는가?”**

이기 때문이다.

따라서 순서는 다음으로 고정한다.

```text
1. Oracle WRITE에서 READ/FUSION 학습 가능성
        ↓ PASS
2. unseen episodic memory
        ↓ PASS
3. learned WRITE
        ↓ PASS
4. dedup / persistence
        ↓ PASS
5. KV → LTM consolidation
        ↓ PASS
6. 일반 LM 30M / 100M
        ↓ PASS
7. 300M 본비교
        ↓
8. 그제야 동예산 재배분
   - KV 추가 압축
   - localized relaxed MLP tying
   - depth/width 교환
```

즉 **memory architecture의 기능적 성립과 deployment Pareto를 별도의 질문으로 분리**한다.

이 순서가 실패 원인을 가장 잘 분해하며, TinyLM의 “관측·계산·해석·제안·실제 수행을 분리한다”는 규약 및 “싼 단계가 비싼 단계의 게이트가 되어야 한다”는 실험계획 규약에도 가장 잘 맞는다.

---

## 승인 결과와 남은 후속 작업

2026-09-18 승인으로 아래 1~3은 완료했다. 4 이후는 P095 S0 구현 범위와 별도 실행 승인이
있을 때만 수행한다.

1. ✅ 현재 `실험계획목록.md`를 다시 확인해 P095 배정
2. ✅ [`test_plan/P095_Scout-1MiB-LTM-학습가능성.md`](../test_plan/P095_Scout-1MiB-LTM-학습가능성.md) 신설
3. ✅ 정적 `exp-preflight` 수행
4. Stage 0 계약/계측 구현
5. Stage 0 PASS 후에만 Stage 1 실행 배치 작성
6. 결과가 나올 때마다 계획서 §3 예측 대조와 §9 실행이력 갱신
7. 실제 과학적 판정이 생긴 경우에만 COMPASS/기준표 영향 여부 검토

승인 시점의 실제 색인에서 P093이 이미 사용 중이고 P094가 함께 배정되어, 이 축은 **P095**로
확정했다.

## 비판 검토 부록 — 승격본에 추가하는 필수 보완

### A. 선행연구 대조

원문이 든 LongMem, Memorizing Transformers, DMC, Activation Beacon, ChunkKV, R-KV,
IndexMem, Bottlenecked Transformers의 큰 방향은 실제 논문과 부합한다. 각각 외부 기억 검색,
압축/병합, 장문맥 확장, 병목 경로의 가능성을 지지한다. 다만 **어느 논문도 TinyLM의 96차원
causal Scout + 논리적 1 MiB 이중 arena + gated residual fusion이라는 정확한 조합을 검증하지
않았다.** 따라서 인용은 구성요소의 가능성 근거이고 이 설계의 성공 증거가 아니다.

- LongMem: https://proceedings.neurips.cc/paper_files/paper/2023/hash/ebd82705f44793b6f9ade5a669d0f0bf-Abstract-Conference.html
- Memorizing Transformers: https://openreview.net/pdf?id=TrjbxzRcnf-
- DMC: https://proceedings.mlr.press/v235/nawrot24a.html
- Activation Beacon: https://arxiv.org/abs/2401.03462
- ChunkKV: https://arxiv.org/abs/2502.00299
- R-KV: https://arxiv.org/abs/2505.24133
- IndexMem: https://arxiv.org/abs/2605.25475
- Bottlenecked Transformers: https://openreview.net/pdf?id=fWgKnl4itC

### B. 현재안의 결정적 교락과 보완 게이트

1. **ordinary-context shortcut 차단**: 질의 시점에 정답 fact가 main path의 잔존 context에
   남아 있으면 LTM 없이도 풀 수 있다. Stage1의 첫 게이트는 fact를 main 입력에서 제거하거나
   실제 유지 창보다 긴 delay를 강제하고, BASE가 chance 부근인지 확인해야 한다.
2. **oracle write의 미래정보 누출 금지**: oracle은 현재 시점의 관측과 사전 정의된 write
   위치만 사용한다. 정답 문자열·미래 질의·최종 label에서 write 위치나 key를 만들면 안 된다.
3. **수명과 충돌 계약**: session reset, persistence 범위, 동일 key 재기입, 상충 사실의 최신성,
   tombstone/eviction을 구현 전에 고정한다. nonce·entity·template는 train/eval source-disjoint다.
4. **1 MiB의 의미 분해**: 1 MiB는 key/value payload의 논리 용량으로만 보고 alignment, slot
   index, occupancy/age metadata, Scout 파라미터, 임시 검색 버퍼와 실제 RSS를 별도 보고한다.
5. **검색 비용 계측**: 약 3.5K slot을 64차원 key로 전수 검색하면 질의당 약 224K scalar
   multiply 비교가 생긴다. tap 수까지 포함해 latency·RSS·cache locality를 Stage0에서 잰다.
6. **용량/퇴거 스트레스**: 단일 fact 성공만으로 1 MiB 유용성을 주장하지 않는다. 25·50·100·
   120% occupancy, hot/cold 분포, 중복·상충·퇴거 뒤 회수율을 포함한다.
7. **통계 문턱**: 원문의 30pp·90% 문턱은 point estimate가 아니라 chance 대비 신뢰구간과
   개별 control(remove/shuffle/null)의 하한으로 판정한다. 100M/300M 전에는 최소 2개 seed에서
   방향 재현을 요구한다.

### C. 개선된 단계 순서

| 게이트 | 질문 | PASS 뒤에만 여는 것 |
|---|---|---|
| S0 causal isolation | main path만으로 답할 shortcut·미래 누출이 0인가 | oracle write/read |
| S1 oracle memory | remove/shuffle/null에서 성능이 무너지는가 | learned WRITE |
| S2 capacity | 용량·충돌·퇴거에도 정보가 보존되는가 | dedup/persistence |
| S3 learned WRITE | source-disjoint 조건에서 쓰기 위치·내용을 학습하는가 | KV→LTM |
| S4 deployment | logical 1 MiB와 physical RSS·latency가 예산 안인가 | 일반 LM 30M/100M |
| S5 reproducibility | 최소 2 seed와 CI에서 방향이 유지되는가 | 300M·동예산 Pareto |

### D. 최종 판단

**조건부 승격 타당(A+)**이다. 설계의 강점은 기능 성립과 동예산 최적화를 분리한 데 있다.
다만 승인 시 첫 계획은 원문의 Stage1을 그대로 구현하는 것이 아니라 **S0 causal-isolation
fixture와 물리 메모리 계측**부터 시작해야 한다. P095 계획은 사용자 승인으로 작성됐지만 이
부록은 Scout/LTM 구현·모델·GPU·배치 승인으로 확대되지 않는다.
