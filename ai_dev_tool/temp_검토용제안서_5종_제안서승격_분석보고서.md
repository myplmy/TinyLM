# 검토용 제안서 5종의 정식 제안서 승격 가능성 분석

작성일: 2026-09-12  
상태: **읽기 전용 검토 결과 — 승격·번호 배정·구현·실험 실행은 하지 않음**

## 0. 결론

| 문서 | 판정 | 정식 제안서 처리 권고 | 핵심 이유 |
|---|---|---|---|
| `temp_FP8 compute와 shadow precision을 분리해 연다(검토용).md` | **승격하지 않음** | v2가 승계한 초안으로 보존 | v2가 변수·게이트·문헌을 더 엄밀하게 재작성해 독립 정본 가치가 없다. |
| `temp_FP8 compute와 shadow precision을 분리해 연다_v2(검토용).md` | **조건부 승격 가치 있음** | 신규 P번호보다 **P022/P022B 후속 개정안으로 병합** | compute C0/C1과 precision probe는 이미 P022/P022B에서 상당 부분 수행됐다. 신규성은 low-precision shadow/write-back 진단과 masterless 경로다. |
| `temp_proposal-20260911_Muon후반-적응적-블록-확장-재학습(검토용).md` | **현재 승격 보류** | 연구 메모로 유지하고 controller 예측력 게이트를 먼저 축소 설계 | 내부 동기는 있으나 제안서 스스로 외부 직접 근거가 없다고 명시한다. selector·expansion·fold·optimizer를 한 계획에서 여는 것은 인과 식별과 구현 위험이 크다. |
| `temp_20260912_Dynamic-Sparse-Training으로-연결희소성을-학습한다(검토용).md` | **조건부 승격 가치 있음** | 2:4 문서와 경계를 합의한 뒤, 비정형 DST feasibility만 별도 계획화 | P016/P025와 질문은 다르지만 sparse-master·churn·resurrection·freeze 축은 다른 검토안과 겹친다. 실제 wall-clock 가속 경로는 아직 없다. |
| `temp_TinyLM 2_4 동적 희소 프리트레이닝 및 sparse-master 실험 제안서(검토용).md` | **독립 승격하지 않음** | **기존 P025 확장 개정안**으로 흡수 | 2:4, 동적 mask, 마이크로벤치, 학습 가속이라는 실험축이 P025에 이미 있다. sparse-master와 topology 계측은 유용한 보강 내용이다. |

따라서 정식 계획으로 바로 올릴 문서는 0개다. 문서 내용 중 살릴 것은 다음 두 갈래다.

1. FP8 v2의 `shadow/write-back` 부분을 P022/P022B의 후속 단계 후보로 축소한다.
2. 희소성은 P025 개정안(2:4)과 신규 비정형 DST 후보를 분리하고, 공유 계측 계약은 한 곳에서 소유한다.

## 1. 검토 범위와 방법

- 저장소 중복은 `test_plan/`, `test_result/`, `docs/`, `scripts/`, `tinylm/`, `experiments.tsv`에서 제안의 핵심 키워드와 기존 실험 번호를 대조했다.
- 문헌은 가능한 경우 arXiv, PMLR, NeurIPS proceedings, OpenReview, NVIDIA 공식 문서처럼 원문 또는 공식 색인을 우선 확인했다.
- 초록이 뒷받침하는 주장과 본문까지 확인해야 하는 주장을 구분했다. 논문이 실재한다는 사실은 TinyLM 적용성이나 재현성을 증명하지 않는다.
- 제안서의 시간·메모리 추정은 실제 실행 증거로 보지 않았다.
- 현재 실행 중인 P088 Stage10과 모델·체크포인트는 이 검토에서 읽거나 실행하지 않았다.

## 2. 저장소 내 중복 지도

| 제안축 | 기존 정본/구현 | 중복 정도 | 남는 신규 질문 |
|---|---|---:|---|
| FP8 GEMM feasibility·속도 | P022, 결과 010, `scripts/bench_fp8_gemm.py` | 높음 | scaling recipe별 end-to-end 비교 |
| FP8 weight 표현 오차 | P022B, 결과 035, `scripts/diag_fp8_precision.py` | 높음 | optimizer proposal을 FP8 저장 격자에 직접 write-back할 때의 update visibility |
| 저정밀 optimizer state | P022B, `tinylm/train/adamw_bf16.py`, `--opt-dtype` | 높음 | masterless/partial-master와는 별도이나 공통 기준선으로 재사용 가능 |
| Muon 자체의 효과 | P005/P005b, 결과 076/078 | 높음 | 후반부 어느 unique block에 계산을 배분할지 |
| 반복 노출·후반 추가학습 | P087/P088 | 중간 | 짧은 probe가 장기 block utility를 예측하는지 |
| 3:4 희소 삼진 | P016, 결과 008 | 높음 | 비정형 DST와 2:4는 각각 다른 topology 제약 |
| 2:4 semi-structured | **P025** | 매우 높음 | dense-master를 제거한 sparse-master와 topology lifetime 계측 |
| 비정형 prune/regrow DST | 직접 대응 계획 없음 | 낮음 | TinyLM ternary pretraining에서 connectivity 자체를 학습할 가치 |

## 3. 문서별 판정

### 3.1 FP8 v1

#### 확인된 가치

- compute precision과 shadow/storage precision을 혼동하지 말아야 한다는 핵심 구분은 옳다.
- dead-update, transition recall, saturation/underflow를 단순 reconstruction error보다 우선한다는 방향도 타당하다.

#### 승격하지 않는 이유

- v2가 format, scaling, stochastic rounding, write-back, 단계별 gate를 더 구체적으로 재작성했다.
- v1을 별도 제안으로 유지하면 같은 실험군의 비용과 상태가 둘로 갈린다.
- 외부 근거가 NVIDIA 문서 중심으로만 서술되어 정식 참고문헌 추적성이 v2보다 약하다.

#### 권고

파일을 삭제하거나 개명하지 말고, v2 승계 초안이라고 문서 첫머리에 표시하는 정도만 별도 승인 후 수행한다.

### 3.2 FP8 v2

#### 승격 가치가 있는 부분

- `compute dtype`, `shadow/storage dtype`, `optimizer state dtype`을 서로 다른 축으로 분리했다.
- invisible-update fraction, ULP visibility margin, quantized update distortion, update-direction cosine, ternary transition precision/recall 같은 진단 계약은 기존 P022B를 보강한다.
- stochastic rounding을 기본값으로 섞지 않고 deterministic write-back 실패 뒤 rescue arm으로 여는 순서가 인과적으로 적절하다.

#### 기존 작업과 중복되는 부분

- C0 GEMM 가능성은 P022 결과 010에서 이미 Ada 실제 형상으로 확인했다.
- 단순 weight FP8 왕복 정밀도는 P022B 결과 035와 `diag_fp8_precision.py`가 이미 다룬다.
- optimizer state 저정밀화는 P022B 구현과 결과가 존재한다.
- 따라서 C0/C1/C2를 새 계획의 신규 단계처럼 다시 세면 같은 질문을 재실험하게 된다.

#### 문헌 대조

| ID | 대조 결과 | 판정/수정 필요 |
|---|---|---|
| R1 Micikevicius et al., arXiv:2209.05433 | E4M3/E5M2 조합과 FP8 training 범위를 뒷받침한다. | **적합**. [원문](https://arxiv.org/abs/2209.05433) 링크 추가 필요. |
| R2 Sun et al., NeurIPS 2019 | forward/backward의 수치 요구가 같지 않다는 hybrid 8-bit 근거로 적합하다. | **적합**. 공식 proceedings 링크를 참고문헌에 명시해야 한다. |
| R3 Noune et al., arXiv:2206.02915 | exponent/mantissa 및 bias 설계가 학습 가능성에 영향을 준다는 근거로 적합하다. | **적합**. [원문](https://arxiv.org/abs/2206.02915) 추가. |
| R4 Kuzmin et al., arXiv:2208.09225 | exponent allocation과 분포 의존성은 뒷받침하지만 논문의 중심은 FP8 quantization/PTQ이고 QAT는 일부 범위다. | **부분 적합**. full-training 직접 근거처럼 확장하지 않는다. [원문](https://arxiv.org/abs/2208.09225) |
| R5 MXFP8, arXiv:2506.08027 | block scaling과 E4M3 recipe의 가설 근거는 된다. | **조건부 적합**. Blackwell MXFP8 결과를 Ada current-scaling backend 증거로 쓰면 안 된다. [원문](https://arxiv.org/abs/2506.08027) |
| R6 FP8-LM, arXiv:2310.18313 | 고정밀 master가 update 정보 보존에 중요하며 FP16+scaling master를 선택했다는 기술과 맞는다. | **적합**. masterless 성공 근거가 아니라 실패 위험 근거다. [원문](https://arxiv.org/abs/2310.18313) |
| R7 ECO, arXiv:2601.22101 | full-precision master 없는 quantized training에서 보상/반올림 설계가 필요하다는 근거다. | **적합하나 최신 preprint**. 버전 고정 필요. [원문](https://arxiv.org/abs/2601.22101) |
| R8 arXiv:2607.09800 | 논문은 실재하나 제목·내용이 버전 사이에서 바뀌었다. 현재 v4 색인 제목은 v2 문서의 `Reference Traces...`와 다르다. | **버전 드리프트 경고**. 반드시 `2607.09800v3` PDF와 조회일을 고정하거나 최신 v4로 주장·제목을 재감사한다. |
| R9 Zhao et al., PMLR 304 | low-precision weights 직접 업데이트와 stochastic rounding을 실제로 다룬다. | **적합**. 정확한 서지는 PMLR 304:1150–1165, 2025, paper `zhao26b`. [원문](https://proceedings.mlr.press/v304/zhao26b.html) |
| R10 Transformer Engine | Ada SM89+ current scaling과 HYBRID/E4M3는 공식 문서 범위와 맞고, MXFP8은 Blackwell 경로다. | **적합**. current scaling과 MXFP8 문서를 별도 인용해야 한다. [Current Scaling](https://docs.nvidia.com/deeplearning/transformer-engine/user-guide/examples/fp8_primer.html), [MXFP8](https://docs.nvidia.com/deeplearning/transformer-engine/user-guide/examples/fp8_primer.html#mxfp8-block-scaling) |

#### 정식화 전 필수 수정

1. P022/P022B의 완료 단계는 재실행하지 않고 결과 010/035를 선결 증거로 가져온다.
2. 신규 범위를 `S0 observer → S1 deterministic write-back → 필요 시 SR rescue`로 축소한다.
3. 실제 packed/masterless storage 절감은 별도 구현·시스템 검증 gate 뒤에 둔다.
4. R8 버전과 제목을 고정하고, 표에만 있는 R1–R10의 직접 링크·버전·조회일을 참고문헌 절로 만든다.
5. 신규 P번호를 예약하지 말고 P022B 개정 여부를 먼저 결정한다.

### 3.3 Muon 후반 적응적 블록 확장·재학습

#### 내부 근거의 적합성

- P005/P005b가 Muon 배수와 RMS 정규화를, P087/P088이 반복 노출과 token scaling을 실제로 다뤘다는 연결은 유효하다.
- 하지만 `Muon이 전체 학습에서 이득`과 `짧은 후반 probe가 block별 장기 중요도를 예측`은 다른 명제다.
- P089 width 실험이 현재 구현 오류로 미실행인 상태이므로 width·block 확장 일반화를 뒷받침하지 못한다.

#### 외부 근거 공백

문서는 신규 외부 논문을 사용하지 않는다고 명시한다. 연구 메모로는 가능하지만, selector·확장·fold라는 비표준 조합을 정식 실험 제안으로 올릴 때는 인접 연구와 차이를 밝혀야 한다.

| 인접 연구 | 실제로 뒷받침하는 것 | 이 제안을 직접 증명하지 못하는 것 |
|---|---|---|
| [LISA](https://arxiv.org/abs/2403.17919) | 일부 layer만 선택해 업데이트하는 memory-efficient fine-tuning | TinyLM from-scratch 후반 pretraining, Muon, MLP block expansion |
| [ReLoRA](https://arxiv.org/abs/2307.05695) | low-rank update를 병합·재시작해 high-rank 학습을 근사 | block importance controller와 foldable latent expansion |
| [SwitchLoRA](https://arxiv.org/abs/2406.06564) | pretraining 중 low-rank subspace를 점진적으로 교체 | unique MLP block별 후반 선택과 Muon 결합 |
| [GaLore](https://arxiv.org/abs/2403.03507) | gradient low-rank projection으로 optimizer memory 절감 | physical/unique block 확장 후 정확한 fold 가능성 |

#### 권고

- 먼저 expansion 없이 `probe score → holdout 장기 이득`의 rank correlation·top-k regret만 검증한다.
- selector가 재현 가능하고 장기 이득을 예측한 뒤에만 fixed selected-block retraining을 연다.
- latent expansion과 fold는 그다음 별도 구현 제안으로 분리한다.
- 문서의 미승인 P번호 표기는 승인 전 번호 예약이므로 제거하거나 “번호 미정 후보”로 바꾼다.

현재 문서 전체를 정식 제안으로 승격하면 실패 원인이 selector, expansion, fold, optimizer 중 어디에 있는지 분리하기 어렵다.

### 3.4 비정형 Dynamic Sparse Training

#### 기존 작업과의 관계

- P016의 고정 3:4, P025의 2:4 N:M과 달리 global/unstructured connectivity를 prune/regrow한다는 질문은 비중복이다.
- 반면 active-only optimizer state, topology churn, resurrection, annealing/freeze는 2:4 sparse-master 검토안과 공통이다.
- sparse kernel이 없는 현행 PyTorch mask 구현은 수학적 FLOP 감소를 wall-clock 가속으로 바꾸지 못할 수 있다. 1차 성공 기준은 품질·안정성·메모리 구조 가능성으로 제한해야 한다.

#### 문헌 대조

| 문헌 | 대조 결과 | 수정 필요 |
|---|---|---|
| SET, Nature Communications 2018 | magnitude death + random birth와 연결 수 유지 설명이 맞다. | DOI 링크의 `utm_source=chatgpt.com` 제거. [DOI](https://doi.org/10.1038/s41467-018-04316-3) |
| Sparse Momentum, arXiv:1907.04840 | momentum 기반 regrowth/allocation 및 sparse training speedup 주장이 논문 범위에 있다. | speedup은 해당 구현/하드웨어 결과로만 유지. [원문](https://arxiv.org/abs/1907.04840) |
| RigL, ICML 2020 | magnitude prune + gradient-based regrow 설명이 맞다. | PMLR 원문 링크로 정리. [원문](https://proceedings.mlr.press/v119/evci20a.html) |
| Mixed Sparsity Training, TMLR 2025 | warm-up·ultra-sparsification·restoration과 GPT-2 약 4× FLOP 감소 설명이 맞다. | “실제 wall-clock 4×”로 읽히지 않게 FLOP와 시간을 분리. [원문](https://openreview.net/pdf?id=XosdLS7KVE) |
| SMET, arXiv:2606.00888 | regrown Adam state cold-start, optimizer warm-up, density-aware LR, active-only state라는 요약과 맞다. | 2026 preprint이므로 버전·조회일을 고정하고 Hugging Face 2차 페이지 대신 [arXiv](https://arxiv.org/abs/2606.00888)를 우선한다. |
| Data-scarce sparse scaling, arXiv:2606.01155 | 반복 데이터에서 중간 sparsity가 loss 최적일 수 있다는 요약과 맞다. | 후속 결합 동기일 뿐 1차 DST 알고리즘 선택 근거가 아님을 유지한다. [arXiv](https://arxiv.org/abs/2606.01155) |

#### 정식화 전 필수 수정

1. 1차 범위를 static-unstructured 대 RigL/SET 한 축으로 줄인다.
2. sparse-master와 active-only optimizer state는 correctness 검증 전 성공 산출물로 약속하지 않는다.
3. 2:4 문서와 공통인 churn/resurrection 정의는 별도 공통 계측 계약으로 단일 소스화한다.
4. 실제 wall-clock 가속, 수학적 nonzero FLOP, 저장공간, runtime allocation을 별도 열로 판정한다.
5. 2026년 preprint 두 편은 버전과 조회일을 고정한다.

### 3.5 2:4 dynamic sparse-master

#### P025와 직접 중복

P025에는 이미 다음이 있다.

- 2:4 마스크와 Ada sparse Tensor Core 적용
- 실제 shape 마이크로벤치 후 `>1.3×` gate
- 동적 mask 또는 annealing 후 고정
- dense 기준선 대비 품질과 wall-clock 판정
- Windows/cuSPARSELt 지원 위험

그러므로 새 정식 제안서로 올리면 P025와 소유권이 충돌한다. 다만 검토안의 다음 내용은 P025를 실질적으로 개선한다.

- dense-master와 true sparse-master를 별도 단계로 분리
- flip rate 외 topology lifetime, resurrection, churn value 계측
- adaptive freeze와 pre-registered gate
- SR-STE, S-STE, Top-KAST, CHTs24까지 확장한 문헌 지도

#### 문헌 대조

| 문헌 | 대조 결과 | 주의점 |
|---|---|---|
| [SR-STE, arXiv:2102.04010](https://arxiv.org/abs/2102.04010) | N:M from-scratch training, SR-STE, SAD 설명이 맞다. | 논문의 2×는 지원 GPU·해당 실험 조건이며 TinyLM 보장이 아니다. |
| [Hu et al., ICML 2024](https://proceedings.mlr.press/v235/hu24r.html) | transformer FFN, flip rate, transposable mask, 실제 shape 가속 설명이 맞다. | “transformer 전체 2×”가 아니라 shape별 가속과 end-to-end를 분리해야 한다. |
| [S-STE, NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/3b576711b12ab036b45130fc8eb78504-Abstract-Conference.html) | discontinuous pruning의 세 문제와 continuous projection 설명이 맞다. | FP8 등 다른 기법과 묶인 결과를 continuous projection 단독 효과로 해석하지 않는다. |
| [RigL, ICML 2020](https://proceedings.mlr.press/v119/evci20a.html) | prune/regrow의 일반 동기는 맞다. | N:M 2:4 직접 학습법은 아니다. |
| [Top-KAST, arXiv:2106.03517](https://arxiv.org/abs/2106.03517) | forward/backward 상시 sparse와 dense materialization 회피 설명이 맞다. | 2:4 Tensor Core 직접 근거는 아니다. |
| [CHTs24, PMLR 328](https://proceedings.mlr.press/v328/lyu26a.html) | 2:4 sparse-to-sparse, SR-STE 대비 LLM linear-layer 결과, ViT retraining 결과가 보고돼 있다. | “full LLM pretraining 전체에서 sparse-master가 검증됨”으로 확대하면 안 된다. eDSrT의 완전한 end-to-end LLM 증거도 별도 확인이 필요하다. |

#### 권고

새 P번호를 만들지 않고 P025를 다음 순서로 개정한다.

1. 현 GPU/Windows에서 2:4 sparse GEMM과 backward 경로 feasibility를 학습 없이 확인한다.
2. 통과하면 dense-master 2:4 correctness와 flip-rate를 확인한다.
3. 품질과 실제 wall-clock 모두 통과한 경우에만 sparse-master 구현 연구를 연다.
4. CHTs24는 구현 아이디어의 직접 선행연구로 쓰되, TinyLM 전체 pretraining의 성공 증거로 쓰지 않는다.

## 4. 두 희소 제안 사이의 정리안

세 가지 안을 비교하면 다음과 같다.

| 안 | 장점 | 단점 | 판정 |
|---|---|---|---|
| A. 두 문서를 각각 신규 P로 승격 | 문서 경계가 단순 | 공통 계측·sparse-master 구현이 중복되고 P025까지 삼중화 | 비권장 |
| B. 모든 희소 실험을 P025 하나에 병합 | 단일 소스 유지 | N:M hardware 질문과 비정형 connectivity 학습 질문이 섞임 | 비권장 |
| C. **P025 개정 + 비정형 DST 별도 후보 + 공통 계측 계약** | hardware-compatible 2:4와 algorithmic DST를 분리하면서 중복 계측을 제거 | 공통 계약 문서가 하나 필요 | **권장** |

권장안 C의 소유권은 다음처럼 둔다.

- P025: 2:4 feasibility, dense-master 2:4, 실제 sparse GEMM, 이후 조건부 sparse-master.
- 신규 DST 후보: global/unstructured density, SET/RigL, layer allocation, loss spike.
- 공통 계측 계약: flip/churn/resurrection/lifetime, optimizer-state 초기화, 수학적 FLOP와 실측 wall-clock 구분.

## 5. 승격 전 공통 체크리스트

- [ ] 기존 계획 번호와 완료 결과를 재실행 단계처럼 적지 않았는가?
- [ ] 새 P번호를 `실험계획목록.md`와 `experiments.tsv` 확인 전에 예약하지 않았는가?
- [ ] 원문 URL, 논문 버전, 조회일이 참고문헌에 있는가?
- [ ] 초록에서 확인한 사실과 본문·부록에서만 확인 가능한 세부 주장을 구분했는가?
- [ ] 논문의 하드웨어·모델·데이터 조건을 TinyLM 실측처럼 서술하지 않았는가?
- [ ] 수학적 FLOP, kernel speed, end-to-end wall-clock, 저장크기, runtime allocation을 분리했는가?
- [ ] 한 단계 실패 시 다음 구현·학습 단계가 자동으로 열리지 않도록 gate가 있는가?
- [ ] 현재 P088 Stage10과 필요한 체크포인트를 침범하지 않는 실행 순서인가?

## 6. 최종 권고 순서

1. FP8 v1은 v2 승계 초안으로 유지하고 독립 승격하지 않는다.
2. FP8 v2에서 기존 P022/P022B 중복 단계를 제거한 축약 개정안을 만든다.
3. 2:4 문서는 P025 개정 재료로 병합한다.
4. 비정형 DST는 P025와의 공통 계측 계약을 먼저 정한 뒤 별도 feasibility 제안으로 다시 심사한다.
5. Muon 적응 블록안은 expansion 구현 전에 selector 예측력만 검증하는 축소 제안으로 다시 작성한다.

이 순서에서는 새 실험계획 번호, 구현, GPU 시간 배정이 아직 발생하지 않는다. 승격 결정 후에도 `impact-analysis`와 `exp-preflight`를 거쳐 각 단계의 중복·선결·예산을 다시 확인해야 한다.
