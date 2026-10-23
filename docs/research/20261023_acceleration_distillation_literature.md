# 2026-10-23 학습 가속·이종 토크나이저 증류·반복형 모델 문헌 대조

작성: 2026-10-23 KST. 초기 문헌 단계는 원문·공식 구현 읽기와 이 파일 신설만 수행했다. 이후 명시 승인으로 byte helper·합성 회귀 두 파일을 작성했으며 범위와 미검증 상태는 §9에 분리했다. 모델/GPU/학습/설치/다운로드/Git/삭제는 수행하지 않았다. 문헌 후보의 효과·실물 비용은 `NOT_RUN`이다. 총괄의 동시 실험 결과와 이 문헌 검토의 증거를 합치지 않는다.

[사용자 참고자료](/home/uranus/tinyLM/ai_dev_tool/temp_20261023_작업지시서_참고용.md)는 1~1071행 전체를 읽었다. 자료에 포함된 논문 요약·수치는 검증 대상이다. [전일 문헌 보고서](/home/uranus/tinyLM/docs/research/20261022_constrained_lm_literature.md)와 [전일 간극 지도](/home/uranus/tinyLM/docs/research/20261022_moonshot_gap_map.md)를 재사용하고 수정하지 않았다. 아래 `읽은 범위`는 실제 열람 범위이며 모든 논문 전문·모든 구현 파일의 완독이나 재현을 의미하지 않는다.

## 1. 당장 비교할 후보와 권고

사용자 순서인 기존 작업 마무리 → chat32 가속 → chat32 증류 → 기존 반복형 구조 개선을 유지한다. 정·반 담당과 총괄이 아래 근거로 채택 여부를 판단하며 이 문서가 새 기본값을 정하지 않는다.

| 안 | 구체적인 다음 검증 | 장점 | 강한 반례·위험 | 영향·오늘의 비용 |
|---|---|---|---|---|
| A. 현 CE 대 exact CCE/Liger의 격리 대조 | 이미 있는 유효 위치 선택을 유지하고 출력 손실 소비기만 바꿔 loss·gradient·업데이트와 전체 update 시간을 비교 | 구조·교사·자료를 바꾸지 않는 가속 질문 | 현재 32K/r256·assistant 희소 지도에서는 이미 head 비용이 작다. 설치·compile·재계산 비용이 순이득을 지울 수 있다 | 손실 어댑터와 parity 검증. 실제 소요·순이득은 미측정 |
| B. 같은 교사답 CE 대 ALM 핵심형 | 같은 원문·정답 이력에서 양쪽 TF logp와 byte chunk를 만들고 CE-only와 CE+ALM을 비교 | teacher hidden 없이 다른 어휘에 적용할 수 있다 | 정렬이 적거나 확률이 매우 작으면 신호가 약하다. CE/KD gradient 간섭·교사 오답도 남는다 | 교사 강제이력 scoring·캐시·미분 가능한 per-token NLL 경로가 선결 |
| C. NorMuon/AdaMuon의 별도 최적화 비교 | 기존 Muon RMS4와 논문/공식코드 규약을 명명해 같은 자료·초기점에서 비교 | head와 독립인 데이터 효율 가설 | 학습률·Nesterov·업데이트 크기를 함께 바꾸면 새 알고리즘 효과를 분리하지 못한다 | NorMuon은 행별 상태, AdaMuon은 행렬 전체 상태가 추가. time-to-quality 미측정 |

권고는 A의 작은 정확성·비용 대조를 먼저 끝내고, 교사 신호 경로가 열리는 즉시 B로 진행하는 것이다. A가 느리거나 설치가 필요하면 기존 CE를 유지한 채 B를 진행할 수 있다. C를 B와 동시에 바꾸지 않는 것이 해석에 유리하다. 새 반복 구조는 이 두 단계의 결과를 기다리는 후속 후보다.

이것은 문헌상의 우선순위 의견이다. 새로운 태그·학습 명령·계수·판정 문턱은 만들지 않았다. `impact-analysis`의 3안 비교와 `exp-plan`/`exp-preflight`의 독립변수·반례·예산 원칙을 적용했지만 레지스트리 기계 조회·실물 preflight를 수행하지 않았으므로 `preflight PASS`가 아니다.

## 2. 로컬에서 이미 있는 것과 새 부분

| 직접 확인한 소유 파일 | 현재 구현·기존 결과 | 새 문헌과 구분할 점 |
|---|---|---|
| [mtp_sft.py](/home/uranus/tinyLM/tinylm/train/mtp_sft.py:117) | `IGNORE` 위치를 head 전에 제거하고 위치 chunk·head checkpoint를 사용. optimizer update 전체의 유효 target 분모로 정규화 | 유효토큰 CE 자체는 새 개선이 아니다. CCE의 어휘 타일과 Liger의 fused CE를 별도로 비교한다 |
| [p102a_contract.py](/home/uranus/tinyLM/tinylm/train/p102a_contract.py:26) | FP32 factorized loss-first·행 chunk 재계산 backward·update-local VJP가 존재 | 구현 존재와 현재 chat32 학습 경로의 활성은 별개. 새 CCE와 같은 알고리즘도 아니다 |
| [trainer.py](/home/uranus/tinyLM/tinylm/train/trainer.py:213) | loss-first에 compile/KD 등 사용 제한이 있다 | opt-in 프로토타입을 현재 chat32의 즉시 drop-in으로 부르지 않는다 |
| [muon.py](/home/uranus/tinyLM/tinylm/train/muon.py:74) | Jordan/RMS 두 scaling, NS5, Nesterov, 고유 parameter 분할이 이미 존재 | RMS matching이나 Muon이라는 이름을 신규 효능으로 세지 않는다 |
| [transformer.py](/home/uranus/tinyLM/tinylm/model/transformer.py:680) | prelude/middle/coda 방문 스케줄, TR/IR 구분, eval의 TR 계승이 있다 | MLP 공유·attention 공유·전체 블록 재방문·Huginn state injection을 같은 구조로 합치지 않는다 |
| [결과091 §1~2](/home/uranus/tinyLM/test_result/091_20260923_P098-R2-초기임베딩-재주입은-3시드-실무-동급.md:8) | R2 초기 embedding 단순 덧셈은 3seed에서 해당 실무 분해능 안, default-off 유지 | 단순 덧셈을 새 input injection으로 재소개하지 않는다. 학습 scalar mixing·concat adapter·OrthoInj는 다른 변경 |

기존 재귀의 부정 결과 중 학습/평가 방문 수 불일치로 철회된 항목이 있다. 현재 [기준표 §7](/home/uranus/tinyLM/docs/EXPERIMENT_BASELINES.md:730)은 과거 불일치와 현재 fallback을 구분한다. 이 문헌 담당은 체크포인트·원본 로그를 다시 읽어 전수 결과를 재계산하지 않았다. 새 실물 판정은 총괄의 결과 감사가 소유한다.

## 3. CCE와 Liger는 같은 메모리 알고리즘이 아니다

### 3.1 실제 읽은 원문·공식 코드

- CCE: [2411.09009v2](https://arxiv.org/html/2411.09009v2), §4~5·Appendix B의 방법/정확성 경계와 [공식 README](https://github.com/apple-aiml-research/ml-cross-entropy)의 exact·per-token NLL·LSE API를 확인했다. 논문의 Gemma2-2B 예시를 TinyLM 절감치로 사용하지 않는다.
- Liger: [공식 README](https://github.com/linkedin/Liger-Kernel) 및 [fused_linear_cross_entropy.py](https://github.com/linkedin/Liger-Kernel/blob/main/src/liger_kernel/ops/fused_linear_cross_entropy.py)의 chunk 생성·gradient 처리·`reduction="none"` 분기를 읽었다. 공식 논문 전체의 재현이나 설치된 버전과의 대조는 하지 않았다.

| 경로 | logits 중간 버퍼 | backward와 per-token 손실 | 현재 대비 새 부분 |
|---|---|---|---|
| 현 TinyLM | 선택한 위치 chunk마다 `[N_valid,V]` | checkpoint로 head 재계산 | 기준선 |
| CCE | 어휘 타일을 순회하며 정답 logit과 online LSE 계산. 전체 chunk logits를 HBM에 쓰지 않음 | 기본 gradient filtering과 `cce_exact`를 구분. `none`·`return_lse` 존재 | chunk 내부 어휘 버퍼까지 제거 |
| Liger FusedLinearCE | 공식 main은 `input_chunk @ weight.T`로 `[chunk,V]`를 실제 생성 | CE가 logits 저장소를 gradient로 재사용. mean/sum은 forward 중 gradient 계산. 현재 main의 none은 backward에서 재계산하여 upstream token 가중치를 반영 | CE fusion·버퍼 재사용·일부 재계산 회피. CCE식 무logits와 다름 |

두 외부 코드는 조사 시점 main을 읽었으며 commit 고정·로컬 설치 여부·실행 호환은 확인하지 않았다. 특히 Liger의 과거 구현/설명에는 none의 제약이 있었으므로 이름만 같다고 nonlinear ALM 가중치의 gradient가 맞는다고 가정하지 않는다.

### 3.2 TinyLM 접합 계약과 가장 작은 반증

현재 factorized head의 `h → r → V`에서 `u=h@projection`은 그대로 두고 `u`와 기존 접근자가 반환하는 vocabulary table을 fused 손실에 넘기는 방식이 후보이다. 현재 학습 head는 [FP32 접근자](/home/uranus/tinyLM/tinylm/model/transformer.py:440)를 쓰므로 fused-only 대조에서 임의 삼진화하지 않는다. 입력 lookup·출력 head와 projection의 공유 gradient를 보존한다. 향후 hard 삼진/GSQ head를 도입할 때는 그 effective table과 STE 계약을 별도 검증해야 한다.

검증의 순서는 같은 hidden/labels의 loss → hidden/projection/table gradient → 입력 lookup까지 포함한 한 update이다. 이미 shift된 `y`에 다시 shift하지 않고 IGNORE·sum/mean·누산 전체 분모·softcap 유무를 맞춘다. scalar CE만 비교하지 말고 `sum(w_t * NLL_t)`처럼 위치별 upstream gradient가 다른 경우도 확인해야 ALM/adaptive masking에 필요한 계약을 검사한다. 이는 검증 형태의 예시이며 실제 고정 tolerance를 새로 정한 것은 아니다.

2048개 위치·V32768 FP32 logits 한 벌은 산술상 256MiB다. 유효 위치가 적으면 이보다 작으며 allocator peak 절감과 같지 않다. V248320으로 같은 형상을 키우면 약1940MiB지만 이는 미래 구성의 산술일 뿐이다. 전체 update에서 head가 차지하는 비율·warmup/compile 포함 시간·단독 peak를 실제로 재야 오늘 채택할 근거가 된다.

CCE의 NLL/LSE는 full-vocab KL을 자동 계산하지 않는다. 다만 ALM 핵심형은 target NLL만 필요하므로 loss 경로와 양립할 수 있다. ACTD에는 student anchor logits와 LSE, debiased ALM에는 경계 vocabulary 집합의 질량이 추가로 필요하다.

## 4. NorMuon/AdaMuon: 논문·공식코드·현재 Muon의 세 규약

### 4.1 NorMuon

[2510.05491v1](https://arxiv.org/html/2510.05491v1) §2~4·Algorithm1, [공식 normuon.py](https://github.com/zichongli5/NorMuon/blob/main/normuon.py)의 `normuon_update`와 단일장치 경로를 대조했다. 원문에서 확인한 새로운 부분은 NS 이후 행별 제2모멘트다. 행렬 `W∈R^(m×n)`에 대한 논문 규약은 다음과 같다.

```text
M ← β1 M + (1−β1) G
O ← NS5(M)
v ← β2 v + (1−β2) mean_columns(O²)       # v has m entries
U ← O / (sqrt(v) + eps)
W ← (1−ηλ)W − η [0.2 sqrt(mn)/||U||F] U
```

공식 main의 기본 구현은 EMA/Nesterov 뒤 NS를 구하고 `v`로 행을 나눈 후, `||O||F/||U||F`로 기존 NS norm을 보존하고 Jordan aspect 배율 `sqrt(max(1,m/n))`을 곱한다. 즉 논문 Algorithm1의 최종 RMS 규약과 같지 않다. 같은 이름의 두 경로 중 어느 것을 재현하는지 먼저 고정해야 한다.

### 4.2 AdaMuon은 최신 v3를 기준으로 한다

[2507.11005v3](https://arxiv.org/html/2507.11005v3), 2025-12-24판의 Algorithm1·§3·Table1을 확인했다. 처음 연 v1에는 없던 sign 안정화가 v3의 핵심으로 추가됐다. [공식 adamuon.py](https://github.com/Chongjie-Si/AdaMuon/blob/main/adamuon.py)는 sign·원소별 상태·RMS 배율을 구현한다.

```text
M ← β M + G
O ← NS(Sign(M))
V ← β V + (1−β) O²                       # V has mn entries
U ← O / (sqrt(V) + eps)
W ← (1−ηλ)W − η [0.2 sqrt(mn)/||U||F] U
```

공식 코드는 Nesterov가 켜지면 그 조합에 Sign을 적용하며 v3와 같이 별도 bias correction을 하지 않는다. v1의 독립 β2·bias correction 설명을 최신 공식 코드에 그대로 섞으면 다른 방법이다. 공식 배포 클래스는 CUDA/distributed 버퍼와 rank/world_size를 요구하므로 TinyLM 단일장치 optimizer에 무조건 복사할 수 있는 형태도 아니다.

### 4.3 비교 시 고정할 항목

| 항목 | 기존 TinyLM Muon | NorMuon 논문 / 공식 main | AdaMuon v3 / 공식 main |
|---|---|---|---|
| 모멘텀 입력 | 누적 `βbuf+g`, 기본 Nesterov | 논문 EMA / 코드 EMA+Nesterov | 누적 / 코드 Nesterov 선택 |
| NS 입력 | momentum 조합 | momentum 조합 | Sign(momentum 조합) |
| 추가 state | 기존 momentum만 | 행별 v | 원소별 V |
| 마지막 scale | Jordan 또는 고정 `0.2 sqrt(max(m,n))` | 논문 RMS0.2 / 코드 norm보존+Jordan | 적응 후 RMS0.2 |
| 같은 LR 값의 의미 | 현재 선택 규약에 종속 | 두 규약을 혼동하면 달라짐 | sign·적응 후 방향도 달라짐 |

상태의 논리 추가비용은 FP32라면 NorMuon `4×Σrows` bytes, AdaMuon `4×P_muon` bytes다. 고유 parameter만 세며 tied alias를 중복 계산하지 않는다. 실제 peak에는 임시 NS·update·compile 버퍼가 더해진다. embedding/norm/scale와 GSQ code logits는 행렬 본체 그룹에 자동 편입하지 않는다.

최소 대조는 finite update·직사각형 행렬·dtype·state resume 뒤 같은 자료/초기점의 loss 대 시간 곡선이다. 특히 NorMuon 공식 단일장치 경로는 `grad=None`도 zero로 대체해 과거 momentum으로 갱신할 수 있고 gradient를 in-place로 바꾼다. 현재 TinyLM의 None-skip과 다르므로 비활성 head/분기의 None와 수치0을 분리한다. 논문의 목표 loss 도달 예산은 optimizer step 가속이나 정상 대화의 보장이 아니다. 삼진 STE에서의 이득은 미측정이다.

## 5. GGUF 교사 신호가 열어 주는 증류 방법

### 5.1 신호 요구표

| 방법 | 반드시 필요한 신호·연산 | native GGUF 생성 API만 있는 경우 | 최소 구현의 실제 경계 |
|---|---|---|---|
| 같은 교사답 CE/SFT | 정답 문자열·student mask | 가능 | 가장 먼저 고정할 대조군. 텍스트 KD와 분포 KD는 별개 |
| ALM 핵심형 | 동일 원문 byte 정렬, teacher/student TF target logp, chunk 합과 binarized divergence | 생성한 토큰의 logp만으로 임의 reference scoring은 안 됨 | teacher forced scoring이 열리면 hidden 없이 가능. debias/hidden 미사용을 명시 |
| ALM outcome debias | 위 신호 + chunk 끝 다음 토큰 중 경계집합 B의 확률 질량 | top-k만으로 exact 집합질량 일반 복원 불가 | full LSE와 집합 partial LSE 또는 해당 합계 추가 필요 |
| ACTD | teacher TF top-k ID/logits, first-subtoken mapping, monotonic boundary alignment, student anchor p와 residual mass | 자기 생성 이력만 있으면 off-policy reference와 다름 | hidden은 불필요. 공식 코드 미공개라 논문 구현이라고 명시 |
| DSKDv2 | teacher hidden, teacher/student prediction heads, 양방향 projector, ETA | logits만으로 불충분 | white-box head 연산·projector 초기화/학습·큰 어휘 계산 필요 |
| DWA-KD | DSKD형 양공간 신호 + embedding/final hidden + attention entropy/Soft-DTW | logits만으로 불충분 | 단순 token confidence weighting만 만들면 DWA 전체가 아님 |
| DVLM | teacher의 PTS 입력·Hybrid Prefix Attention, 새 student-vocab teacher head 훈련 | 현 causal GGUF 호출로 대체 불가 | frozen teacher라도 새 head 학습과 입력 attention 변경이 필요 |

[llama.cpp 공식 server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)의 `n_probs`는 생성 토큰의 확률을 설명하고 `post_sampling_probs`는 sampling chain 뒤 확률을 구분한다. 그 옵션 존재만으로 teacher-forced prompt 전체 scoring을 지원한다고 말할 수 없다. 로컬 b11396/Prism의 실제 출력·sampler 위치·reference token 포함 여부는 총괄의 실행 감사가 소유한다.

읽은 [공식 harness GGUF backend](https://github.com/EleutherAI/lm-evaluation-harness/blob/main/lm_eval/models/gguf.py)의 `_score_position`은 자연 reference prefix의 token IDs를 넣고 다음 target을 bias로 강제한 뒤 실제 target ID와 pre-sampling logp를 확인한다. 이는 현재 upstream의 TF 경로 후보이지 로컬 binary의 검증 결과가 아니다. [server-context.cpp](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/server-context.cpp)의 pre/post 분기와 [server-common.cpp](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/server-common.cpp)의 `get_token_probabilities`도 대조했다. 읽은 CPU pre-sampling 경로는 전체 logits로 softmax한 뒤 top-k만 내보내므로 top-k 안에서 재정규화한 분포와 다르다. target이 top-k 밖인 사례·bias 변화에도 동일한 원확률인지·저확률 underflow·prefix/shift를 별도 확인해야 한다. 위치마다 요청하는 fallback의 처리량은 bulk C++ scoring과 같다고 가정하지 않는다.

teacher cache에는 원문/정답 ID·hash, teacher 파일/engine/tokenizer revision, 실제 TF token IDs, template/BOS/EOS, byte offset, shift·mask, temperature, logp/normalizer 정의를 결합한다. 양자화 GGUF의 신호는 그 양자화 교사의 분포이며 원 BF16 teacher 분포로 표현하지 않는다. teacher MTP draft 확률을 주모델 확률로 대신하지 않는다.

### 5.2 ALM의 정확한 최소형과 원문 내부 충돌

[ALM 최신 v4](https://arxiv.org/html/2503.20083v4)의 §3·Appendix E/I와 [tokenkit](https://github.com/bminixhofer/tokenkit)을 확인했다. tokenkit 주 구현은 JAX다. 초기에는 guide notebook 렌더가 제한됐으나 추가 요청에서 raw 원문을 확보해 byte 변환·정렬·TF gather·chunk loss 셀을 직접 읽었다(§5.6). 실행·TinyLM 호환 검증은 하지 않았다.

같은 byte chunk의 TF logp 합을 `C_T`, `C_S`라 하고 `q_T=exp(C_T/τ)`, `q_S=exp(C_S/τ)`로 두면, ALM은 `(q,1−q)`의 binarized f-divergence를 비교한다. 단순 logp MSE가 아니다. hidden alignment와 outcome debias는 선택 기능이다. 최신 원문 Appendix I는 TVD·무한 온도의 특수 극한에서 chunk logp 절대차 형태도 설명한다. 이 특수형을 유한온도·KL형 일반식과 혼용하지 않는다.

원문 §3은 binarized divergence가 upper bound라고 쓰지만 Appendix E의 Jensen/data-processing 증명은 lower bound를 준다. **논문 내부 표기 충돌을 보존한다.** 이 문서는 ALM을 full-distribution KL의 상계나 전체 분포 복원으로 소개하지 않는다. 한 chunk를 맞춘 것만으로 다른 모든 정답/사건의 확률이 같아지는 것도 아니다.

오늘 가장 작은 가설은 `ALM core, no hidden, no outcome debias`다. byte round-trip·공동 경계·특수토큰/정규화·한국어 다중byte를 먼저 검사하고, reference의 모든 실제 target logp를 얻어야 한다. log 공간의 chunk 합과 안정적인 `log(1−exp(C/τ))` 계산이 필요하다. ALM의 chunk 분모와 CE의 assistant-token 분모는 다르므로 전체-update 정규화 계약도 명시해야 한다. student가 오답을 생성하더라도 정답 prefix teacher forcing으로 시작할 수 있다. 그 가능성이 품질 향상을 보장하지는 않는다.

### 5.3 ACTD: tail을 보존하는 KL이 아니다

[ACTD v1](https://arxiv.org/html/2608.29662v1) §3.1~3.2·Table1·Appendix D를 읽고 [공식 repo](https://github.com/hyhy892/ACTD)를 확인했다. 조사 시 repo에는 README만 있고 코드 공개 예정이다. §3.2는 teacher top-k를 재정규화하고 first-subtoken으로 학생 anchor에 대응시킨 뒤 L1 anchor 오차와 학생 non-anchor 확률합을 최소화한다. teacher tail은 버리며 residual 목표는0이다.

teacher top-k 재정규화는 이 논문 방법의 일부다. 이를 full-vocab KL이라고 부르는 것이 오류이지 ACTD 자체의 정의 위반은 아니다. 학생의 residual은 `1−Σ_unique_anchor p_S(a)`로 구할 수 있으므로 vocabulary 전체 p 배열 저장은 필수가 아니다. top-k teacher token들이 같은 student ID로 충돌할 때 논문 Eq7의 중복 항과 Eq8의 집합 분모가 달라짐에 유의해야 한다. 임의로 합산·dedup하면 별도 변형이므로 toy 충돌 사례로 목적함수를 먼저 고정한다.

Table1의 주학생은 사전학습 Qwen3-1.7B-Base이고 Avg@8/Pass@8 수학 추론 비교다. scratch 약100M/한영 chat32/고정삼진의 증거가 아니다. mapping용 재토큰화는 BOS/EOS 자동 삽입을 꺼야 한다. 특수토큰·빈 decode·부분 UTF-8·충돌의 처리도 명시한다. 그렇지 않으면 실제 first subtoken 대신 BOS에 anchor가 몰릴 수 있다. residual 억제는 anchor 밖 정답을 벌할 수 있으며 mapping 오류와 교사 신뢰도는 별개다.

### 5.4 DSKDv2·DWA-KD·DVLM의 오늘 경계

- [DSKDv2 v1](https://arxiv.org/html/2504.11426v1), §III-A/B와 [공식 코드](https://github.com/songmzhang/DSKDv2)를 확인했다. 양쪽 hidden을 다른 공간으로 투영하고 공통 head를 통과시키며 ETA로 정렬한다. 임의 top-k score matching은 그 최소 구현이 아니다. GGUF frozen head를 외부 미분 경로로 쓸 수 있는지부터 확인해야 한다.
- [DWA-KD v1](https://arxiv.org/html/2602.21669v1), §3·Appendix D.2/Table7을 읽었다. 양공간 entropy weighting에 Soft-DTW의 lexical/contextual 정렬을 더한다. Table7의 batch4 peak는 DSKD26.38GB 대 DWA29.92GB, step0.35s 대0.45s이며 그 논문 설정이다. 이 숫자를 우리16GB 비용으로 환산하지 않는다. 확인한 원문에 공식 구현 URL은 없었고 저자 귀속의 실행 repo를 확정하지 못했다.
- [DVLM v1](https://arxiv.org/html/2609.33816v1), §3·Appendix A.4/A.6을 읽었다. PTS는 teacher 원토큰열과 student token별 재토큰화 group을 함께 넣고 HPA로 참조 범위를 제한한다. stageI 새 head, stageII OPD가 별개다. 보고 자원은 stageI 1×H200, stageII4×H200이며 공개 코드가 submission 뒤 제공될 예정이라고 적는다. 단순 head 부착·현재 GGUF causal mask로 원문 재현을 주장하지 않는다.

### 5.5 GSQ를 이종 교사 CE/KD에 쓰는 것은 원형 PTQ와 다른 실험이다

[GSQ 최신 v2](https://arxiv.org/html/2604.18556v2), 2026-05-15판 §3~4.1·Appendix B/F와 [공식 ternary quantizer 108행](https://github.com/IST-DASLab/GSQ/blob/main/src/quantization/gumbel_quantizer_ternary.py)을 읽었다. 원형은 GPTQ 초기값에서 `W=s×mask×sign`의 두 logit/좌표와 group scale을 학습한다. 공식 forward는 noisy sigmoid의 **soft** mask/sign이고 hard weight는 별도 추출한다. CUDA RNG를 저장·복원해 backward에서 같은 표본을 재계산한다. hard 삼진 forward+surrogate gradient는 이 코드의 그대로 재현이 아니다.

v2는 task loss도 원리상 허용하지만 실제 큰모델은 블록/전문가별 재구성이며 embedding/head 및 일부 불안정층을 제외한다. 전체 TinyLM·tied embedding/head까지 삼진으로 CE+cross-tokenizer KD를 거는 것은 새 QAT/KD 설계다. 원문은 온도/큰 logit gap의 gradient 소실, 초기값 의존과 보조 logits 메모리도 명시한다. Lion을 썼다는 사실이 우리 code logits optimizer의 최적 선택을 증명하지 않는다.

정상 자유답변을 시작 조건으로 둘 필요는 없다. 검증된 정답 prefix의 CE/ALM 신호는 처음부터 정의된다. 다만 기존 STE와 **같은** 원문·정답·초기 hard codes/scales·노출예산을 유지하고 soft train/hard eval gap, sign/mask 점유·gradient·변경률을 먼저 분리해야 한다. 현재 FP32 head까지 삼진화하는 효과를 Gumbel 선택 효과와 섞지 않는다. 부가 logits만 FP32이면 `8×P_quantized` bytes이며 gradient/optimizer/activation은 별도다. 최종40MB와 이 학습 메모리를 대체하지 않는다. 코드 생성·계수 선택·실물 검증은 하지 않았다.

기존 head checkpoint는 재계산 시 RNG를 보존하지 않는 선택이 있다. GSQ를 접합한다면 공식 backward의 forward 샘플 재생과 **checkpoint가 forward 자체를 다시 부를 때**의 샘플 동일성을 별도로 정의해야 한다. tied input embedding/head·여러 호출이 같은 code sample을 공유할지, update별/호출별로 달라질지도 실물 학습 계약이다. 이를 정하지 않고 기존 deterministic STE와 동등한 대조라고 부르지 않는다.

### 5.6 추가 검토: native ID를 보존하는 ALM core 정합 계약

추가 요청 범위는 공식 코드·현재 tokenizer JSON 읽기와 이 문서 보강뿐이다. tokenizer 로딩/토큰화, HTTP 요청, canary, gradient 계산, 모델 실행은 모두 `NOT_RUN`이다. 아래 계약은 총괄의 CE 대 ALM 계획에 넘기는 검증 항목이며 새 구현·온도·계수·합격 tolerance의 채택이 아니다.

#### 5.6.1 실제 공식 코드에서 확인한 것

| 직접 읽은 공식 파일·범위 | 확인한 기능과 그대로 가져오면 생기는 차이 |
|---|---|
| [byteify.py](https://github.com/bminixhofer/tokenkit/blob/main/tokenkit/byteify.py), `_init_vocab`, 생성자, `load_byteify_tokenizer`, `to_byte_level_tokenizer` | id→byte 표면 매핑과 **256-byte 어휘로 교체**하는 `conversion=byte`는 다르다. 후자는 현재32K 모델의 ID를 보존하지 않는다. 생성자는 일부 Unicode normalizer를 제거하며 loader는 special 추가·BOS/EOS 설정도 한다 |
| [model_kinds.py](https://github.com/bminixhofer/tokenkit/blob/main/tokenkit/model_kinds.py), Base/Qwen2/Qwen3/Llama3/Gemma2 및 byte fallback | ByteLevel 계열은 identity, SentencePiece는 `▁`와 `<0xHH>`를 공통 byte 문자로 바꾼다. Qwen3 규약은 편의상 BOS를 추가하므로 GGUF native 규약으로 무조건 전용하지 않는다 |
| [align.py](https://github.com/bminixhofer/tokenkit/blob/main/tokenkit/align.py), `get_alignment_indices`, unconstrained/space/unbiased 분기 | 모델별 표지 치환 후 선두 `Ġ` 수를 맞추며 토큰 표현을 수정한다. 누적 길이의 공동 경계를 만들고, `check=True`는 표현 불일치 chunk를 warning 후 제거한다. 성공 반환만으로 전량 정렬을 뜻하지 않는다 |
| [utils.py](https://github.com/bminixhofer/tokenkit/blob/main/tokenkit/utils.py), `preprocess_messages`, `encode_prompt` | 중립 role 표지를 각 템플릿으로 확장하고 일반 구간은 special 자동 삽입 없이 encode한다. 기존 TinyLM serializer와 무조건 같은 token IDs라는 보장은 없다 |
| [PyTorch guide raw notebook](https://raw.githubusercontent.com/bminixhofer/tokenkit/main/docs/pytorch_alm_from_scratch.ipynb), 토큰화·정렬·목적함수 셀 | 다음 target logp gather와 token→chunk 행렬을 함께 한 칸 민다. shortest-chunk/no-debias·binary CE 예제이며 온도/epsilon이 있다. 예제 수치를 기본값으로 채택하지 않았다 |
| [training/losses.py](https://github.com/bminixhofer/tokenkit/blob/main/tokenkit/training/losses.py), `log1mexp`, `compute_sft_loss`, `compute_alm_loss`의 gather/마스크/합계 경로 | CE와 ALM의 전역 분모를 구분하며 alignment에 loss mask를 곱한다. 이 연산 자체가 마스킹 후 양쪽 byte 사건의 동일성을 검사하는 것은 아니다 |

[byteification 안내](https://github.com/bminixhofer/tokenkit/blob/main/docs/byteification.md)의 기능보존 설명을 위 코드의 normalizer 제거·추가 special·`conversion=byte`까지 포괄하는 무조건 보장으로 읽지 않는다. main 소스는 commit 고정 전이므로 향후 가져오는 revision에서 재확인해야 한다.

#### 5.6.2 우리 tokenizer와 byte fragment 처리

직접 읽은 [chat32 JSON](/home/uranus/tinyLM/data_cache/tok-ko-en-32768-chat32.json:322)은 `normalizer=null`, ByteLevel pre-tokenizer(`add_prefix_space=false`, `trim_offsets=true`), ByteLevel post-processor/decoder, BPE(`byte_fallback=false`)다. pad/bos/eos ID0/1/2와 ChatML ID3/4가 special로 있다. **이 파일의 BOS 존재가 자동 BOS 삽입을 뜻하지는 않는다.** TemplateProcessing의 BOS 삽입 규칙도 아니다. 실제 encode/API가 만든 ID열을 canary로 확인해야 하며, BPE의 `byte_fallback=false` 역시 tokenpiece가 항상 온전한 Unicode 문자라는 뜻이 아니다.

열람 범위는 tokenizer 설정·special·일부 어휘/merge 원문이다. 전체어휘의 byte 변환·native ID 보존·왕복은 아직 실행하지 않았다.

| 경계 | 보존·검사할 계약 | 금지할 근사/오인 |
|---|---|---|
| 학생 일반 piece | JSON 어휘의 ByteLevel 문자들을 역byte 표로 변환한다. [공식 상수](https://github.com/bminixhofer/tokenkit/blob/main/tokenkit/constants.py)의 `Ġ→32`, `Ċ→10` 같은 일대일 표가 기준 후보 | byte 표면 문자열에 다시 UTF-8 encode하거나 `decode([id])`의 대체문자를 실제 byte로 취급 |
| 교사 `/tokenize` piece | [공식 API](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)의 `with_pieces=true`는 **string 또는 byte 정수 배열**이다. string은 UTF-8 bytes, 배열은 순서 그대로 raw bytes로 해석하고 ID에 결합 | `str(piece)`, `errors=replace/ignore`, completion의 예쁜 token 라벨을 raw piece로 사용 |
| fragment와 길이 | byte fragment는 개별 UTF-8 decode가 실패해도 유효할 수 있다. 비교·누적 길이는 bytes로 하고 전체 일반본문 재결합이 원문 UTF-8 bytes와 같은지 확인 | 문자 수/학생 token 수를 teacher byte offset으로 대체. 각 fragment가 Unicode 완성문자여야 한다는 조건 |
| 특수토큰 | ID와 역할을 별도 기록. 같은 철자라고 일반본문 bytes로 자동 편입하지 않는다. 초기 보수형은 BOS/PAD/template/EOT를 KD 밖에 두고 기존 CE의 end supervision은 유지하는 후보 | `skip_special_tokens=True`로 지운 뒤 offset을 원래 ID열에 사용. Qwen/Gemma 이름으로 이 학생의 BOS/EOS를 추정 |
| 공백·정규화 | 선두/연속/끝 공백, tab, CRLF/LF, NBSP, 결합문자·분해형 한글을 구분한다. adapter 전후 native IDs와 재결합 bytes가 같아야 한다 | `.strip()`, NFKC/NFC, casefold, 줄바꿈 교환, 선두 공백 합성을 정렬 편의상 조용히 적용 |
| 템플릿·conditioning | 교사·학생 실제 template/think mode와 각 prefix를 고정한다. 서로 다른 native template이면 대응 assistant 본문의 bytes만 같게 하고 conditioning 차이는 명시 | 모델별 다른 system/thinking prefix를 누락. 출력 본문만 같다는 이유로 두 모델의 조건분포가 같다고 표현 |
| mask·shift | padding attention mask와 assistant loss mask는 다르다. prefix는 문맥에 남기고, 정렬 후 양쪽 모두 assistant 본문에 완전히 들어가는 chunk만 KD 선택 | assistant mask를 attention mask로 넘겨 질문을 지움. chunk의 한쪽 일부만 masking하고 같은 사건으로 간주 |
| 절단·offset | 실제 full native ID열에서 공통 byte 경계를 찾는다. 서로 다른 token 제한이면 양쪽 완결 chunk의 공통 범위만 사용하고 제외량 기록 | prompt와 answer를 따로 encode한 ID를 full encode와 같다고 가정. 길이 차이·끝 미정렬을 묵인 |

로컬 [SFT loader](/home/uranus/tinyLM/tinylm/data/sft.py:94)는 현재 원문을 encode하고 **문자 offset**의 완전포함으로 CE mask를 만든다. ByteLevel fragment들이 같은 문자 offset을 공유할 수 있어 이 offset만으로 각 ID의 byte 경계를 재구성하지 않는다. [sft_targets](/home/uranus/tinyLM/tinylm/data/sft.py:135)의 shift도 이미 한 번 있다. 같은 파일의 NFKC/casefold는 split-key용이고 tokenizer의 학습본문 정규화가 아니다. [canonical.normalize](/home/uranus/tinyLM/tinylm/chat/canonical.py:132)도 구조 정규화이므로 Unicode 정규화와 구분한다.

#### 5.6.3 구현 방향 세 가지와 보수적인 권고

| 안 | 내용·장점 | 위험·영향 | 수행비용 |
|---|---|---|---|
| A | native IDs/CE serializer 유지, id→raw bytes의 읽기 전용 뷰와 shortest 공동경계만 접합 | 새 작은 adapter·mask/shift parity 필요. 새 tokenizer·normalizer는 도입하지 않음 | 중간: byte 왕복·coverage·gradient 계약 |
| B | tokenkit을 고정 revision으로 접합하고 학생 전용 model-kind 정의 | 정식 라이브러리 재사용. 추가 special/BOS/normalizer/JAX 의존이 현재 CE 대조를 바꿀 수 있어 격리 필요 | 높음: API·의존성·encode parity 감사 |
| C | CE를 유지하고 teacher raw cache·coverage만 먼저 확보 | 학습 경로 변경 없음. ALM 효과는 아직 측정하지 못함 | 낮음: 신호 검증 선행, 후속 adapter 필요 |

문헌상 권고는 **A의 수학·byte 계약이 닫히면 A**, 아직 닫히지 않으면 C다. B의 byteification이 곧 모델을256어휘로 바꾸는 작업은 아니지만, `conversion=byte`를 선택하면 실제 어휘 교체가 되므로 현재 대조에 넣지 않는다. 방법 비교만 수행했으며 실제 채택은 총괄이 결정한다.

정확한 공동경계의 최소 의미는 양쪽 일반본문 piece의 누적 byte 길이가 만나는 곳에서 chunk를 닫고, **길이뿐 아니라 재결합한 raw bytes가 동일**한지 확인하는 것이다. 반환 구간은 원래 token IDs의 반열린 구간이어야 하며 순서·비중복을 지킨다. 같은 길이의 다른 문자열도 가능한 반례이므로 tokenkit warning/제거를 우리 쪽 성공 처리로 바꾸지 않는다. 특수토큰 치환과 선두 공백 보정은 별도 이벤트로 남기고 strict byte 검증을 우회하지 않는다.

#### 5.6.4 coverage와 NLL gradient의 최소 식별 계약

coverage는 수치를 미리 정하는 gate가 아니라 관측 대상이다. 동일 TRAIN/dev 문장에 대해 적어도 `본문 전체 byte 수`, `KD가 덮은 byte의 합집합`, `student/teacher 지도토큰 포함률`, `chunk 수와 양쪽 길이 분포`, `1:1/다:1/1:다/다:다`, `제외 사유별 수`를 기록한다. 한영·선두 공백·한글 분해형/결합문자·emoji/ZWJ·역슬래시/개행·특수토큰처럼 보이는 리터럴·첫/마지막 assistant 경계를 나눠 읽는다. 언어별 coverage와 chunk확률/gradient 크기도 함께 보아 긴 chunk의 사실상 무신호를 감춘 평균을 피한다. coverage가 높다는 사실이 좋은 지식 전달을 증명하지는 않는다.

student 실제 target NLL 벡터 `n_i`를 미분 경로에 유지하고 `C_S=−Σ_chunk n_i`로 모은다. teacher 상수는 detach하되 student를 cache/리스트로 꺼내 detach하지 않는다. 아래는 binary CE 선택 시 **이 문서가 도출한** 검사식이며 실행 결과가 아니다. 별도 온도 보정 배율·epsilon을 쓰면 그 규약도 반영한다.

```text
q_T = exp(C_T/τ), q_S = exp(C_S/τ)
ell = −q_T log(q_S) − (1−q_T) log(1−q_S)
∂ell/∂n_i = (q_T−q_S) / [τ(1−q_S)]    # 해당 chunk의 각 target NLL
```

검사할 것은 (a) target gather/shift·chunk 합이 dense 기준과 일치, (b) NLL perturbation의 유한차분/독립 미분 기준과 위 도함수 일치, (c) nonlinear ALM을 통과한 hidden/projection/tied-table gradient가 dense 경로와 일치, (d) 누산 분할을 바꿔도 같은 전체-update loss/gradient인지다. 같을 때 binary CE의 **gradient**는0이지만 loss값은 teacher binary entropy라0일 필요가 없다. teacher의 reference 확률이 student보다 낮으면 ALM이 그 gold NLL을 올리는 방향도 가능하므로 CE와의 간섭을 관측한다.

빈/양쪽 한쪽만 남은 chunk는 목적함수에 넣지 않는다. 무효 chunk를 먼저 제외하지 않고 `0×inf`로 감추면 NaN이 남을 수 있다. `log1mexp`의 보완사건 안정성만으로 q 자체의 underflow·긴 chunk의 gradient 소실까지 해결되지는 않는다. 큰 음수 chunk logp, 확률0/1 부근, padding, zero-chunk microbatch, 서로 다른 chunk 수를 별도 검사한다. CE의 유효 assistant target 분모와 ALM의 유효 chunk 분모는 각각 전체 update 기준으로 고정하고, microbatch별 평균의 단순 평균으로 대신하지 않는다. 위 검사는 구현 정합성 증거이지 품질 증거가 아니다.

#### 5.6.5 server 강제-bias exact target logp의 local canary

§5.1의 upstream 코드는 TF 가능성의 근거다. 다음은 **현재 로컬 binary/교사에서 총괄이 확인해야 하는** 계약으로, 여기서는 요청하지도 실행하지도 않았다.

| canary | 필요한 관측·반례 |
|---|---|
| 실제 이력·target ID | reference의 전체 native ID열에서 `ids[:i]`로 `ids[i]`만 평가한다. 응답 sampled ID가 target과 다르면 fail. 반복된 같은 ID만 있는 예제 외에 서로 다른 target·다중byte를 포함해 shift 오류를 드러냄 |
| 원확률 대 biased 확률 | 자연스럽게 top-k에 든 target의 무bias logp와 강제 후 logp가 같아야 한다. 강제 성공하는 bias 크기를 바꿔도 원 logp가 같아야 하며 post-sampling의1/0으로 변하면 안 됨 |
| top-k 밖 target | 자연 top-k 밖 target도 자체 logp가 finite·음수로 반환되는지 확인. top-k 수를 바꿔도 target logp는 같아야 함. 강제 성공/값 불변만으로 정확성 증명은 부족하므로 가능한 direct raw-logit/LSE 기준과 대조 |
| 설정·메인모델 | pre/post-sampling, grammar/penalty/temperature, speculative/MTP, backend sampling 상태와 raw 응답을 보존. cache에는 원 main-model logp를 저장하고 ALM 온도는 목적함수 쪽에서 적용 |
| byte·BOS·template | `/tokenize`의 ID/piece와 scoring ID가 일치하고 BOS가 누락/중복되지 않음. `add_special`, `parse_special`, template/think mode를 고정. 보통문자열 요청과 ID-array 요청을 무검증 혼용하지 않음 |
| 문맥·cache | prefix가 길어져도 실제 reference 이력이며 truncation/context shift가 없음. cold/재사용 prefix·slot 변경에서 같은 분포인지 확인하고 cache 키를 원문·prefix IDs·revision에 결합 |
| 수치범위 | 희귀 target의 p underflow→logp=−inf, logp의 부호 오류·기본값0, 응답 누락을 별도 검출. FP32 p를 log한 값의 정확도와 raw-logit/LSE의 안정성을 혼동하지 않음 |

단순 숫자·산수 정답은 byte/shift/API의 기술 canary로 쓸 수 있지만 ALM 효과를 보장하는 실험이 아니다. CE 대 CE+ALM의 실제 학습 비교는 같은 원문·정답·노출/초기점·기존 CE mask를 보존한 별도 품질/회귀 평가가 필요하다. canary 또는 NLL gradient parity의 통과를 그 결과로 승격하지 않는다.

## 6. 반복형 후속 9개: 실제 읽은 범위와 기존 문제의 연결

아래 후보는 chat32 증류 뒤의 검토다. full-core 반복·MLP 공유·추론 재방문을 구분하고 고정삼진/r256/CLA2/MTP는 각각 호환성 검사 대상이다. 외부 float·B급 모델 성과는 TinyLM 실측이 아니다.

| 문헌·읽은 버전/절 | 직접 확인한 조건·반례 | 공식 구현 확인 | 로컬에 남는 질문·오늘 비용 |
|---|---|---|---|
| [Part I 2610.23036v1](https://arxiv.org/html/2610.23036v1), §2~3/Table1~2·§4 | 730M stored/112 logical layers, TxT360336B, seq8192, AdamW. sandwich만의 Table2는 ARC-C−0.94·HumanEval+−1.22도 있다. 전체 Huginn 구성의 우위와 다름 | [xllm-loop](https://github.com/ifm-ai/xllm-loop)의 PartI 실행기·recipe 안내와 `models/looped.py`를 확인 | 기존 prelude/coda 존재는 중복. 새 부분은 full-core/injection/state 설계의 분리. 구조·KV 변경이 커 오늘 앞단 가속의 대체재가 아님 |
| [Part II 2610.06833v1](https://arxiv.org/html/2610.06833v1), §3~5/Table1~3·§5.5 | 100M/21.5B~1.6B/343.6B, Jais64K. 고정R 학습은 terminal KV sharing을 손상. prior와 injection·prefill·RL 숫자는 다른 실험 | 같은 [공식 repo](https://github.com/ifm-ai/xllm-loop)의 PartII 학습/증류/평가 진입점, OrthoInj 구현 확인 | 기존 first-pass KV 재사용과 다름. 정확한 iteration KV 기준 후 terminal 근사를 별도 평가. prior/OrthoInj와 cache를 한 번에 바꾸지 않음 |
| [Closing the Loop 2610.00673v1](https://arxiv.org/html/2610.00673v1), §3~5/Table1~2·AppI | 1.4B310B토큰. 같은토큰 dense1.4B보다 학습계산약4배. Qwen1.7B 변환은 learned scalar mixing+smoothed exit loss. compute-matched 큰dense가 이기는 영역도 남음 | 원문/저자 연결에서 공식 실행 repo를 이번에 확정하지 못함. 방법식은 직접 확인 | P098의 단순 덧셈과는 다름. 기존 exit gate가 없는 경로에 smooth loss만 복사할 수 없음. scalar/init·전반부/후반부 손실을 먼저 분리할 비용 |
| [LoopCD 2610.02185v1](https://arxiv.org/html/2610.02185v1), §2~3/Table3·AppB.4/C/D.9/G | Hidden은 coda 이전 `h_R+ω(h_R−h_b)`, Logits는 coda 이후 대비라 비선형 coda면 비동치. Table3 Huginn R16 HumanEval Base21.95→28.05. 고정ω의 GSM8K R32는42.91→41.62로 악화 | 지정논문 공식 repo 귀속 미확인. `byeonghoyu/LoopCD`는 다른 연구, `tchayintr/apple-loopcd-off-the-shelf`는 제3자 | Huginn Hidden의 reference는 burn-in h6/h7이지 항상h1이 아님. 낮은 통합비용 후보지만 새분포/MTP계약·동일총비용 평가 필요 |
| [MoDr ICLR2026 최종PDF](https://proceedings.iclr.cc/paper_files/paper/2026/file/8a81180649011d1690e05c68bfeaa57c-Paper-Conference.pdf), §3~4·AppA.9~A.11 | Huginn3.56B,4 LoRA branches,32회 학습/마지막8회 BPTT,평가R16. Table10 학습3h58→16h26,속도14→13tok/s. 같은시간 Table9 top1 이득은0.25점 | [저자 MoDr repo](https://github.com/zhangxjohn/MoDr)의 train/eval·실행 템플릿 확인. 전체 코드 대조는 아님 | router·FP adapter·branch state 추가. 고정삼진 예외를 공짜로 확대하지 않음. 현 단일 core 정상화보다 후순위 |
| [CDB 2608.09444v1](https://arxiv.org/html/2608.09444v1), §2·4~6·AppC | Ouro1.4B/Huginn3.5B 다중요청GPU서빙. shared KV는 attention 의미를 변경. scheduling과 exit/cache 효과를 분리해야 함 | [저자 CDB repo](https://github.com/kschwethelm/continuous-depth-batching)는 greedy 전용 연구 구현이며 완성 serving engine과 구분 | 가변깊이·정확한 KV와 다중요청부하가 선결. CPU단일요청/학습가속으로1.5~1.9배를 전용하지 않음. 오늘 통합비용 높음 |
| [STARS 2605.26733v1](https://arxiv.org/html/2605.26733v1), §4~6/Table2·AppB/C | random R+Jacobian proxy. Table2 AVG는 **5개**수학과제이며 첨부6개는 정정. R4 70.46→74.18, R8 52.97→65.55지만 STARS도R8<R4 | [공식 addition/train.py](https://github.com/njuyxw/STARS/blob/main/train_addition/train.py)의 regularizer는 기본1회 VJP·`norm(Jᵀv)²`; JVP 코드는 주석. Ouro 학습기 호출도 확인했지만 수정 modeling 파일은404 | P098 이후 R외삽/상태발산이 문제로 확인됐을 때만. 원문 JVP/README Frobenius/실제addition VJP를 구분. proxy는 안정·정답 보증이 아니며 고차미분/STE 호환과 비용 미측정 |
| [TaH2 2609.35748v1](https://arxiv.org/html/2609.35748v1), §3~5·AppA | Qwen1.7/4/8B. AIME24~26,32samples,출력4K~16K의 accuracy/compute slope. extended duo-causal attention·lookahead supervision 포함 | [공식 TaH repo](https://github.com/thu-nics/TaH)의 TaH2 공개·별도 의존성과 `tah2/minisgl` 안내 확인 | 단순 entropy exit head가 아님. attention/stop-policy·KV·weighted logits·추가head연산 변경이 커 고정R 뒤 후보 |
| [LTO 2509.26314v3](https://arxiv.org/html/2509.26314v3), §4/Alg1·§6/Table1·AppG/H | Huginn3.5B에서 여러 latent 궤적을 LRM reward로 확률 선택. Table1 제공수치와 일치. 학습된 LRM은 불완전하여 reward 오용 가능성을 본문도 인정 | [저자 ninglab/LTO](https://github.com/ninglab/LTO)의 Huginn/GeneralLLMs·README와 큰 latent 저장 경고 확인 | 현재 후보에 정답이 없으면 selector가 만들 수 없음. 정상 rollout·정오답 학습표본·별도평가와 다중후보비용이 선결. 오늘 첫증류 경로로 두지 않음 |

### 6.1 논문 요약에서 실제 적용에 영향을 주는 정정

1. Part I의 sandwich placement 하나가 모든 benchmark를 높였다는 뜻은 아니다. 결과를 전체 recipe와 구성요소별 효과로 분리한다.
2. Part II의 prefill1.79배와 RL2배·KV3배를 곱하지 않는다. §5.5는 distilled prefill이 정확도와 교환되는 조건을 명시한다.
3. Closing the Loop의310B 대7.7T는 같은 구조의 서로 다른 학습 recipe 비교다. 같은토큰 작은dense 대비 training FLOPs가 감소했다는 근거가 아니다.
4. MoDr의 headline +7.2/+21.21은 raw base 대비이고, SFT 대조 대비 이득은 훨씬 작다. Table10에서 출력속도가 그대로라고 읽지 않는다.
5. STARS의 안정화는 외삽 퇴화를 완화했고 제거하지는 않았다. fixed-point 안정성은 문맥·질문의 정답성을 뜻하지 않는다.
6. TaH2의53%는 정확도 상대상승이 아니라 계산 두배당 정확도 기울기 개선이다. slope가 높아도 같은총비용 점수가 낮을 수 있다는 원문의 부정결과도 유지한다.
7. LTO 최신v3는 일반LM에서도 전체LTO를 평가한다. 초기v1의 classifier만 확인한 요약을 최신전체기법의 범위로 고정하지 않는다.
8. LoopCD의 AppD.9 FLOPs는512-token prefill의 분석값이다. Huginn R32→16의 Hidden48.2%·Logits46.0% 절감을 wall-clock decode로 읽지 않는다. 적응ω에는 unguided top2 logit이 필요해 원문 Hidden은 고정ω만 평가했다. Table1/3의 baseline도 달라 교차차감하지 않는다.

Part I의 재주입 원천은 prelude 출력이고 기존 P098은 token embedding projection이다. 단순 덧셈 대 scalar/concat/orthogonal뿐 아니라 주입 위치와 원천도 독립변수다. 공식 xLLM 코드의 terminal KV는 prefix의 terminal bank에 현재 토큰/chunk의 각 iteration KV를 붙이고 마지막 상태를 저장하므로 첫 cycle 재사용과 다르다.

### 6.2 현재 구조와 접합할 때 구분할 최소 비교

| 확인된 문제/다음 질문 | 작은 분리 비교 | 반증·한계 |
|---|---|---|
| R증가가 학습된 함수 밖에서만 나쁜가 | 같은CP에서 학습R·실제방문목록·KV정책을 명시하고 R별 TF/free·비용 곡선을 기록 | 새학습 없이 반복수만 올린 음성은 반복형 전체의 기각이 아님 |
| 재주입이 새 정보를 유지하는가 | 기존P098 덧셈 기록을 대조로 보존하고 scalar/concat/orthogonal 중 한 변경만 추가 | 새head·prior·cache도 바꾸면 injection 효과를 모름 |
| KV감소가 의미를 바꾸는가 | iteration별 exact 기준 대 terminal-state 근사. TF·incremental/full-prefill과 실제답을 별도 비교 | first-cycle reuse 결과를 terminalKV 성공/실패로 전용하지 않음 |
| random R만으로 충분한가 | 같은평균core실행예산에서 fixed·random·random+JSRR를 단계 분리 | 평균R만 같아도 분포/역전파길이/노출량이 달라질 수 있음 |
| decoding 대비가 도움 되는가 | LoopCD의 Hidden/Logits·reference depth를 구분해 같은R와 같은총계산 비교를 각각 시행 | 새분포 점수를 기본likelihood·MTP검증분포와 섞지 않음 |

모두 후보의 최소 식별 조건이다. 논문계수·norm 위치·R분포·exit threshold를 새 기본값으로 정하지 않았다. 예산·데이터·태그·원본 보존·실행기 parity를 총괄의 정식 계획에서 닫아야 한다.

## 7. 추가 아이디어 — 알고리즘 발명과 기존 기능의 접합을 구분한다

전일 간극 지도의 Stack·깨끗한 span·task/native gradient 진단은 별도 기존 후보다. 이름을 바꿔 오늘의 새 제안으로 세지 않는다. 아래 세 개는 이번 문헌에서 드러난 구현/계측 간극에 관한 가설이다.

| 아이디어 | 현재 구현과 다른 부분 | 검증 가능한 가장 작은 관측 | 비용·반례 |
|---|---|---|---|
| 출력 전체 대신 필요한 통계만 내는 손실 경계 | 현scalar CE를 per-token target NLL·LSE·선택 anchor logit·경계집합 LSE로 확장. CCE API 일부를 재사용하는 접합이며 새KD알고리즘은 아님 | 같은hidden에서 dense 기준의 NLL·anchor p·boundary mass와 값/gradient 일치 | per-token nonlinear gradient·tied STE가 깨질 수 있음. CCE가fullKL을해준다는주장이아님 |
| byte 정렬의 양만큼 신뢰성도 함께 계측 | 현재 exact TF 신호에 chunk길이·경계coverage·mapping충돌·teacher확률/tail을 결합 | 같은원문 한영 TRAIN dev에서 정렬/anchor가 gold를 포함하는 비율과 실패사례 공개 | 낮은coverage가곧나쁜KD라는법칙은없음. 평가gold로train자료선별하지않음 |
| 같은질문의 반복별 손실/정답 궤적 분해 | 최종CE만보지않고 iteration별 gold margin·hidden변화·실제답을 함께 읽음 | 학습R안에서 개선/악화하는토큰·질문군과head비용을 먼저관측 | 상태수렴/낮은entropy는정답verifier가아님. 미학습중간head를학습head로간주하면오류 |

우선권은 첫 아이디어의 작은 수학계약 확인에 있다. 두번째는 ALM/ACTD 사이 선택의 진단, 세번째는 이후 반복형 개선의 문제정의다. 새일반지능효과·40MB달성·학습시간절감을 예측하지 않는다.

## 8. 증거·쓰기 범위·남은 확인

문헌 단계에서는 이 파일만 작성했고, 후속 구현 승인 뒤 추가한 두 파일은 §9에 명시했다. 그 외 문서·원장·코드·기준표·실험목록을 수정하지 않았다. 보호 `datasets/TinyDataset/**`, 체크포인트 tensor·원문캐시·금지된 환경지침에 접근하지 않았다. 원본로그/모델을 실행·수정하거나 Git/외부계정을 변경하지 않았다. 별도 하위 agent도 만들지 않았다.

후속 명시 요청에 따라 `data_cache/tok-ko-en-32768-chat32.json`의 tokenizer 설정과 일부 어휘 원문만 읽었다. tokenizer/model 로딩·토큰화·교사 HTTP·canary·gradient 계산은 하지 않았다.

정정: 후속 구현 진행 보고 1건을 중국어로 전송해 사용자의 중국어 금지·한국어 보고 지시를 위반했다. 같은 인터페이스·상태 내용을 한국어로 다시 보냈다. 이후 보고·설명·질문은 전송 전에 문장 언어가 한국어인지 확인하며, 영어 코드 식별자·논문명과 자연어 보고를 구분한다. 이 언어 위반을 기술 검증 실패나 모델 결과와 섞지 않는다.

추가 정정: §10 후속 검토 초안에도 비한국어 문구가 일시 혼입되어 제거했다. 최종 열람에서 해당 문자 혼입이 없는지 다시 검색했다. 언어 점검은 문서·진행 보고 양쪽에 적용하며, 이 검색을 수식/실험 검증으로 표현하지 않는다.

실제 비용은 총괄의 단독 측정이 필요하다. 이 문헌 담당의 TF 신호·loss parity·optimizer·recurrent 실험 실행은 모두 `NOT_RUN`이다. 현재 `main` 브랜치 웹코드의 API가 로컬 설치판과 같다는 증거도 없다. 문헌에 나온 모델규모·정밀도·데이터·benchmark/출력길이·R·하드웨어와 현재chat32를 분리한다.

LoopCD는 초기 HTML/PDF 열람 실패 뒤 다른 연결 검색기로 같은 공식 v1 본문을 확보해 §6을 보완했다. 남은 원문검증은 그 공식코드 귀속, ClosingLoop·DWA·DVLM의 공식 실행repo, STARS의 미확보 Ouro modeling 파일과 논문/README/addition 코드의 규약 차이다. 열람실패를 방법실패나 코드부재의 증거로 해석하지 않는다. 총괄의 실제 교사 reference scoring·C++ API 검증이 들어오면 GGUF feasibility 행의 상태를 갱신할 수 있다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 9. 후속 승인: Stage7b 순수 byte helper·회귀 작성

총괄의 명시 지시로 아래 두 코드 파일을 새로 작성했다. 사전 계약은 [P106B Stage7b0W/Stage7bW](/home/uranus/tinyLM/test_plan/P106B_Bonsai-자동번역-pseudo-SFT-온라인-교사학생-검증.md:7299)이며 계획서·수치 loss·학습·교사 cache 구현은 총괄 소유로 수정하지 않았다. Stage7a 14요청 성공은 총괄이 전달한 다른 담당의 실측 상태이지 이 담당의 실행 증거가 아니다.

### 9.1 착수 전 중복·영향·권한 대조

`scripts/diag_vocab.py`와 `diag_val_lang.py`에는 GPT-2 byte alphabet 생성이 이미 있다. 그러나 numpy/config/prepare 등의 import 경로와 표시용 lossy decode가 있어 이 helper에서 import하지 않았다. byte 표 자체를 새 알고리즘으로 세지 않으며, native ID별 exact 재구성·공통경계·감독/턴 검사·원본/shifted index 보존이 새 접합 범위다.

| 경로 | 승인된 동작 | 제외·영향 |
|---|---|---|
| [p106b_alm_bytes.py](/home/uranus/tinyLM/scripts/p106b_alm_bytes.py) | stdlib-only 순수 함수·불변 구조 신설 | tokenizer/model/torch/lm_eval·파일/HTTP·수치 loss·cache 없음 |
| [test_p106b_alm_bytes.py](/home/uranus/tinyLM/scripts/test_p106b_alm_bytes.py) | 합성 unittest 작성 | 실제 tokenizer/원문 corpus 없이 작성만 함. import·실행·구문검사는 총괄 소유 |
| 이 연구문서 | 계약·한계·정정 기록 | 원장·계획/결과·기준표 연쇄는 총괄 소유이며 이 담당이 수정하지 않음 |

`impact-analysis` 관점에서 기존 호출부 변경은 없고 새 테스트만 새 helper를 참조한다. 데이터/체크포인트 migration은 없으며, 회귀 실행과 native tokenizer 접합은 남는다. `wip-ledger`는 읽었지만 이 하위 작업의 허용 파일에 원장이 없어 새 원장을 만들거나 총괄 원장을 수정하지 않고 상태를 총괄에게 전달했다. GPU/모델·데이터 소유권·비교조건·증거 수준은 위 승인 경계 그대로다.

### 9.2 인터페이스와 거부 계약

- `SpecialToken(raw_index, token_id, kind, source_bytes)`는 원본 index/ID와 실제 source byte 소비량을 함께 선언한다. literal marker는 비어 있지 않은 bytes로 offset을 소비하고, 자동 삽입은 명시적 `b''`다. missing/empty 일반 piece는 거부한다. 이미 special로 선언된 ID의 다른 등장도 각 index에서 명시해야 한다.
- `build_student_stream`은 GPT-2 ByteLevel 역표를, `build_teacher_stream`은 string/정수 byte-array 합타입을 쓴다. 같은 길이의 다른 bytes·미완성 원문·부정확한 special 선언·중복 index·일반 ID의 상충하는 piece를 거부한다. byte fragment 자체에 Unicode decode를 강요하지 않는다.
- `align_assistant_chunks`는 **양쪽 full input bytes가 같은 경우만** 처리한다. 누적 경계 교집합의 가장 짧은 chunk를 실제 bytes로 재확인하고, special·부분 감독·turn 혼합/불일치·raw index0을 제외 사유와 함께 돌려준다. 0-byte special이 공통경계 내부에 끼면 enclosing chunk를 제외한다. 경계 위의 자동 special은 별도 index 목록에 보존한다.
- 채택 chunk에는 `byte_start/end`, `data`, `turn_id`, 양쪽 `raw_indices`와 `shifted_indices`가 있다. `raw_to_shifted`는 `i→i−1`만 수행한다. 반환값은 tuple처럼 쓰는 `ShiftedTargetIndices`로 태그되어 그대로 재입력하면 중복 shift를 거부한다. 외부 복사로 태그를 지운 숫자는 자체 판별이 불가능하므로 caller의 provenance 표지가 필요하다.

shifted index는 IGNORE 제거 전 **전체 shifted sequence**의 행이다. 현 유효토큰 gather 후 압축된 NLL 벡터의 위치와 같지 않으므로, 총괄 NLL 경로가 full-position 벡터 또는 명시적 compact 위치 맵을 제공해야 한다. helper의 supervised byte 수는 입력 mask가 선언한 일반토큰 bytes이며 특수토큰·분모 정의를 대신하지 않는다.

합성 회귀는 모든 byte 값, 한글 fragment·잘린 UTF-8·공백/개행·특수 마커·자동 BOS/EOT, 같은 길이 다른 bytes, 부분 감독·turn 경계, overlap·index 중복·중복 shift를 포함한다. **작성 완료이지 PASS가 아니다.** import·unit test·모델·수치 계산을 이 담당은 실행하지 않았다.

### 9.3 한계와 총괄 인계

이 helper는 다른 native template를 의미적으로 같게 만들지 않는다. special metadata가 실제 모델 vocabulary에 맞는지, assistant mask/turn ID가 진짜 대화 경계인지도 토크나이저/모델 없이 증명할 수 없다. 누락 선언을 토큰 철자만 보고 추측하지 않으며 native ID→piece 진실성은 총괄의 API/tokenizer 감사가 소유한다. 높은 byte coverage나 작은 synthetic 예제는 ALM gradient·지식 전달·대화 품질의 증거가 아니다.

P106B Stage7b가 선택한 이항 KL의 수치 구현과 teacher cache는 이 파일들 밖이다. §5.6의 binary CE 도함수는 teacher entropy 상수만 다른 gradient 참고식이며, KL값0·gradient parity·update 분모·teacher 신호·실제 학습 판정은 총괄이 별도 확인해야 한다. 언어 지시 위반과 한국어 사전 점검 정정은 §8에 보존했다.

## 10. 후속 검토: TRAIN gradient 교정과 논문 GradMag를 구분한 ALM core 대조

### 10.1 이번 검토의 대상·권한·관측 수준

총괄이 제시한 후보는 동결 TRAIN 1024행(한영 각512, 명시 문맥 QA, 원래 CE target≤64)의 **원문 정답**에 대한 Qwen GGUF TF target logp를 이용해, 같은 초기화·행·순서의 CE-only와 CE+ALM을 각각32 update/4 epoch 비교하는 것이다. 새 교사 답안 생성이나 학생 on-policy rollout이 아니다. 여기서 행/캐시의 실제 내용·분포·학습 결과를 확인한 것은 아니며, 이 전제는 총괄이 전달한 설계다.

이번에는 [현재 ALM core](/home/uranus/tinyLM/tinylm/train/alm.py:19) 전체, [기존 교육 경로의 whole-update 누산·clip·양 optimizer](/home/uranus/tinyLM/scripts/p106b_education_followup.py:756), [출력 head 접근자](/home/uranus/tinyLM/tinylm/model/transformer.py:450), [Muon의 물리 parameter 분리](/home/uranus/tinyLM/tinylm/train/muon.py:144), P106B Stage7b0W/W를 읽었다. 기존 교육 경로가 새 ALM 학습기의 실제 호출부라는 뜻은 아니다. `impact-analysis`·`exp-preflight`·`exp-plan` 절차를 읽고 설계 경계를 대조했으나 정식 계획·레지스트리의 수정과 실행은 총괄 소유다. §10과 §8의 언어 정정 기록만 보강했으며 gradient 계산·모델/교사 실행·설치·추가 코드 변경은 하지 않았다.

`alm.py`는 이미 shifted target의 원래 위치를 보존한 per-target NLL, 공통 chunk의 NLL 합, τ=100의 `KL(Bern(qT)||Bern(qS))`, teacher detach, CE target/KD chunk의 서로 다른 whole-update 분모를 구현한다. hidden·outcome debias·GradMag·τ² 배율은 없다. 따라서 이 팔의 이름은 **ALM core, no hidden/no outcome debias, fixed weight**가 정확하다. §5.6의 binary CE와는 teacher entropy 상수만 다르므로 내부 확률의 gradient 식은 같지만 loss값을 같은 것으로 보고하지 않는다.

### 10.2 논문·공식 구현에서 실제 확인한 GradMag

[ALM v4 §3.3·Appendix A.4/Table9·B](https://arxiv.org/html/2503.20083v4)를 이번 쟁점에 맞춰 다시 읽었다. 논문 GradMag는 매 단계 task별 마지막 층 gradient `G_i`를 구하고 `w_i ∝ 1/||G_i||`, `Σw_i=1`로 결합한다. 학습 시작점 TRAIN 표본에서 한 번 크기를 맞춘 뒤 고정하는 절차가 아니다. Table9의 Gemma2-2B IT→Qwen2 tokenizer/5k-step 조건에서 ALM+SFT는 GradNorm56.1 대 GradMag55.4이며, DSKD는 고정β=1/3의52.0 대 GradNorm/GradMag 각51.4다. 자동 균형이 항상 우월하다는 해석은 원표 자체와 맞지 않는다. 수십억 모델·LoRA 중심의 이 조건을 현재 소형 삼진·32 update에 이식하는 근거도 없다.

공식 [cross_tokenizer_distill.py](https://github.com/bminixhofer/tokenkit/blob/main/scripts/cross_tokenizer_distill.py#L925)와 [multitask.py](https://github.com/bminixhofer/tokenkit/blob/main/tokenkit/training/multitask.py#L78), [param.py의 layer mask](https://github.com/bminixhofer/tokenkit/blob/main/tokenkit/models/param.py#L386)를 원문으로 대조했다. 2026-10-23 웹 `main` 열람이며 고정 commit 재현·로컬 설치판 확인은 하지 않았다.

- `approx_gradmag_preserve_mag`는 `get_layer_n_mask(...,-1)`와 train mask의 교집합, 즉 **마지막 Transformer block의 trainable parameter**를 사용한다. lm_head/embedding 표만 고르는 구현이 아니다. LoRA라면 그 block의 trainable adapter 부분이 대상이다.
- task별 Jacobian norm의 역수는 `a_i=1/(||G_i||+1e-8)`이고 stop-gradient한다. preserve 모드는 `Σa_i`로 나누며 비preserve 모드는 이 분모가1이다. 단순화한 두 task에서 상대 weight는 역노름 비지만 전체 gradient scale도 달라진다.
- 공식 설정 주석은 `approx_gradmag*`에서 사전 `loss_weights`가 크기 균형에 의해 상쇄된다고 경고한다. 양의 배율·epsilon 무시 조건에서의 상쇄이지, 0 weight/극소 norm에도 정확히 동치라는 뜻은 아니다. 현재 TinyLM의 고정 λ와 이 옵션을 동시에 켜고 같은 실험이라고 부르면 안 된다.

paper형 정규화 혼합 `wC*LC+wK*LK`와 현재 형태 `LC+λ*LK`는 `λ=wK/wC`여도 전체 배율 `wC`만큼 다르다. clip·momentum·Adam/Muon·weight decay가 있는 실제 경로에서 같은 update라고 가정하지 않는다. 전체 norm이나 head-only norm의 일회 교정을 GradMag 재현으로 명명하지 않고, GradNorm의 보조 optimizer/상대 학습률 적응까지 구현했다고도 표현하지 않는다.

### 10.3 세 대안과 이번 규모의 조건부 권고

| 안 | 분리되는 질문·장점 | 비용·실패 위험 |
|---|---|---|
| A. 사전 고정 λ, gradient는 관측만 | 사람에게 가장 명료한 고정 목적함수. 교정용 학습 경로가 없음 | 단위·분모·τ 때문에 KD가 사실상 없거나 과대할 수 있음. loss값 비율로 정하면 gradient 균형이 아님 |
| B. TRAIN-only 일회 norm/cosine 교정 후 λ 고정 | 초기 신호 크기와 간섭을 확인한 뒤32 update 동안 같은 λ. 이번 질문에 가장 작은 접합 | 추가 forward/backward·메모리·시간은 필요. 표본/parameter 집합/집계량에 의존하며 이후 norm drift는 보정하지 않음 |
| C. 매 단계 논문식 GradMag | 마지막 block의 task별 크기를 온라인으로 균형화하는 별도 알고리즘 질문 | Jacobian/별도 역전파·epsilon·scope·전체 배율·공식 구현 검산이 추가됨. 현재 OFF 계약 및 고정 λ 대조와 다름 |

**권고는 B를 신호 감사로 한정하고, 유한·비영 신호와 대표성/안정성을 확인한 경우에만 고정 λ 대조로 넘기는 것**이다. B가 실패하면 신호를 만들 때까지 λ를 키우지 않고 ALM 팔을 HOLD하고 CE 기준선을 보존한다. A도 합법적인 별도 대조지만 단위 선택의 불확실성이 크다. C는 논문 재현을 별도로 묻는 후속이며 오늘의 기본값으로 채택하지 않는다. 실제 λ·상대 크기 목표·허용 drift/cap·표본 크기는 이 문헌 검토가 결정하지 않는다.

교정의 예시는 `λ0=ρ*||gC||/||gK||`다. `gC=∇(CE_sum/N)`, `gK=∇(KL_sum/K)`이고 ρ는 **결과를 보기 전에 총괄이 정할 상대 크기 목표**다. 이 식 자체가 효과적인 ρ나 λ를 알려 주지는 않는다. loss값/교사 entropy·한 미니배치 norm의 숫자만으로 효과를 예측하지 않는다. 추정기 `||Σg_b||`, `Σ||g_b||`, batch별 norm비의 중앙값은 서로 다르므로 관측 뒤 유리한 것을 고르지 않는다.

### 10.4 일회 측정이 유효하려면 먼저 고정할 계약

1. **자료와 목적함수.** 교정 행은 동결 TRAIN 안에서만 결정·기록하고, 한영/길이/coverage 편향을 확인한다. held-out 점수나 평가 정답으로 λ를 고르지 않는다. 실제 CE 전 target에는 EOT 등 KD 제외 target이 남고, KD는 양쪽 assistant에 속한 일반 byte chunk만 쓴다. N·K·제외 사유·양쪽 token 수·byte coverage·chunk 길이/logq 분포를 함께 남긴다. 512:512행은 token/chunk 기여의 균등을 뜻하지 않는다.
2. **실제 update 정규화.** micro별 평균을 비교하지 않고 같은 optimizer update의 총 N과 K로 각각 정규화한 gradient를 비교한다. gradient accumulation 전후가 같아야 한다. 한 microbatch의 값이면 그 범위라고 제한하며 전체 update의 norm으로 승격하지 않는다. 정렬된 부분만의 CE 진단과 실제 전체 CE 목적함수를 혼동하지 않는다.
3. **측정 위치와 상태.** 같은 초기 checkpoint·동일 forward의 CE/KD에서, AMP loss-scale을 제거하고 **clip·optimizer step·weight decay 전**의 task gradient를 사용한다. finite 여부·각 task norm·dot/cosine·결합 norm을 별도 저장한다. 측정으로 optimizer/scheduler/momentum·parameter·RNG·자료 순서가 바뀌지 않게 해야 하며, 두 팔의 학습 시작 상태는 같아야 한다. 교정에 든 wall/peak와 추가 읽기 횟수는 학습32 update 비용과 분리한다.
4. **parameter 좌표와 중복.** 물리 parameter ID로 dedup하고 같은 trainable 집합을 비교한다. 전체/마지막 block/head 표/embedding projection 중 어디인지 명시한다. 지금 head는 `_emb_up_w()`·`_emb_w()`의 FP32 latent 접근자이며 입력과 공유된다. 전체 graph에서의 공유 표 gradient에는 입력 경로도 들어간다. hidden을 detach한 head-only probe, 실효 dense head `W_eff`, factorized 두 leaf의 norm은 서로 같은 좌표가 아니다. `None`과0의 정책·비활성 분기는 별도 기록한다.
5. **언어·표본 민감도와 drift.** 한영을 나눈 norm/cosine, update별 신호 변동, q가1/0에 가까운 chunk를 따로 관측한다. 한 표본의 평균 cosine으로 전체 TRAIN/미래 update를 보장하지 않는다. 학습 중 로깅은 가능하되 같은 팔에서 λ/τ·mask/자료를 다시 조정하면 일회 고정 대조가 아니라 새 조건이다. 로깅 부담도 두 팔의 시간 비교에 명시한다.

기존 `OptimizerAudit`는 선택 행렬의 gradient/update RMS를 남길 수 있지만 **task별 분리 norm/cosine 측정기 자체는 아니다**. 선택 최대8개 행렬의 통계를 전체 gradient라고 바꾸지 않는다. 기존 경로에서 재사용할 계측과 새 task 분리 계측을 구별해야 한다. 새 probe 구현·실행은 이 담당이 하지 않았다.

### 10.5 이 core에서 예상 가능한 간섭: 해석식이지 실행 결과가 아니다

§5.6의 식을 현재 KL/whole-update 평균에 적용한 **직접 미분**이다. chunk c의 각 target NLL `n_i`에 대해 내부 확률 `0<qS,qT<1`이면:

```text
LC = sum_i n_i / N
LK = sum_c KL(Bern(qT_c) || Bern(qS_c)) / K
qS_c = exp(-sum_{i in c} n_i / tau)
d LK / d n_i = (qT_c-qS_c) / [K*tau*(1-qS_c)]
d (LC+lambda*LK) / d n_i
  = 1/N + lambda*(qT_c-qS_c)/[K*tau*(1-qS_c)]
```

같은 chunk 안에서는 각 gold NLL에 같은 KD 계수가 곱해진다. 원문 정답만 쓰는 이 최소형의 teacher 신호는 reference chunk 확신도의 제약이며, 대안 토큰별 teacher 확률·새 설명·새 정답을 직접 주는 full-vocab KD가 아니다. qT<qS면 KD 성분은 그 gold NLL을 올리는 방향이고, λ가 충분히 크면 결합 계수 자체가 음수가 될 수 있다. qT>qS라도 여러 예제/공유 parameter의 전체 gradient cosine이 항상 양수라는 보장은 없다.

따라서 qT≈qS에서의 작은 KD norm은 정상적인 일치일 수 있고, 긴 chunk의 underflow·정밀도/마스크·detach 결함으로 인한 작은 norm과 분리해야 한다. 큰 λ만으로 무신호를 치료하지 않는다. τ=100을 썼다는 이유로 같은어휘 softmax-KD의 τ² 보정을 자동 추가하면 현재 목적함수와 weight 단위가 바뀐다. `log1mexp`만 안정화해도 q의 underflow·gradient 소실이 없어지는 것은 아니다.

`nC=||gC||`, `nK=||gK||`, `c=cos(gC,gK)`라 두면 결합 gradient norm 제곱은 `nC²+λ²*nK²+2λ*nC*nK*c`다. 단순 SGD의 국소 CE 하강 성분은 `gC·(gC+λgK)=nC²+λ*nC*nK*c`이므로, norm만 맞추고 c가−1에 가까우면 상쇄될 수 있다. 이는 분석적 경고이며 Muon의 직교화/Adam 사전조건·momentum·clip 이후 실제 update 방향·일반화·정답률의 보증이나 새 중지 임계값은 아니다. cosine<0 자체를 무조건 실패로 처리하지도 않는다.

### 10.6 중지·재설계·판정의 경계

| 구분 | 확인할 사건 | 해당 팔의 처리·주장 한계 |
|---|---|---|
| 정합 중지 | cache/source/hash/template·byte/mask/shift가 어긋남, native target이 아닌 logp, overlap/이중 shift, nonzero λ인데 update K=0 | 학습을 열지 않고 원인/제외 사유 보존. 편의상 chunk/행을 팔별로 바꿔 계속하지 않음 |
| 수치 중지 | nonfinite loss/gradient·양의 logp·부정확한 경계 처리·분리 gradient의 graph 단절 | FAIL/미확인을 신호 부족과 구분. `qS=1,qT<1`은 현 core의 명시적 `StudentProbabilityBoundary`이며 silent clipping으로 우회하지 않음 |
| 교정 불능/대표성 부족 | nK=0 또는 비가용 norm/cosine, 극소 신호의 원인 미분리, 언어별/표본별 비율이 교정 규칙으로 설명되지 않음 | 고정 λ 결정은 HOLD. 정상 q 일치·평범한 gradient 상쇄도 가능하므로 곧바로 구현 버그/방법 전체 실패로 단정하지 않음 |
| 운영 중지 | 사전 wall/메모리/저장/종료 cap, 한 팔만32 update 완주 가능 | 불완전 대조로 남김. 다른 팔의 추가 epoch·여분 tuning으로 승자를 만들지 않음 |
| 해석 중지 | TRAIN loss만 감소, 작은 paired 표본만 개선, 평가를 보고 λ 재선택, 조건·분모 차이 발견 | 품질/유의/일반 지능 개선을 선언하지 않음. 새 조건은 새 계획과 별도 검증 필요 |

실제 `qT=qS=1`은 내부 확률의 gradient0 검사와 다르게 한쪽 경계 미분으로 분류한다는 현 계획·소스 규약을 유지한다. clip 한 번이 norm을 제한해도 task 간 방향 충돌이나 λ의 상대 기여가 해결되는 것은 아니다. λ/ρ의 상한·drift 허용·운영 중지값은 이번에 문헌 수치에서 복사하지 않았고, 기존 표준 사전학습 σ를 이 소형 SFT의 품질 판정자로 전용하지 않았다.

32 update/4 epoch는1024행을 모두 매 epoch 쓸 때 총4096행 제시다. 기존 micro8×accum16을 그대로 쓴다는 추가 전제가 성립하면8 update/epoch이지만, 새 호출부의 실제 batching·마지막 partial·shuffling은 총괄이 확인해야 한다. 총 padded input tokens·실제 conversation tokens·감독 CE targets·KD chunks·추가 교정 비용은 별도 원장이다. 반복 SFT 자체를 표준 사전학습300M의 새 비교라고 부르거나, 행 수/epoch 일치만으로 유효 token·compute까지 일치했다고 말하지 않는다.

비교의 최소 질문은 **같은 frozen reference SFT에서 이 고정 λ의 ALM core를 더한32 update가 무엇을 바꾸는가**다. TRAIN 진단으로 λ를 선택하는 것은 손실 단위 교정이지 held-out 효과 증명이 아니다. 평가 셋·checkpoint 선택·paired 출력/채점 규칙·시간 예산은 실행 전에 총괄의 Stage7c 정식 계획으로 닫아야 한다. 한 seed·작은32 update가 음성이어도 ALM 전체를 기각하지 않고, 양성이어도 정상 대화/산수/한국어 품질을 보증하지 않는다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 11. 후속 소스 감사: BabyLM2026 minimal BLiMP의 무설치 호출 경계

### 11.1 결론·열람 대상·권한

**현재 내려받은 원모듈을 정상 import해서 바로 실행할 수 있다는 판정은 불가하다.** BLiMP 계산에 쓰지 않는 `scipy.stats.spearmanr`가 `compute_results.py:9`의 무조건 상단 import다. 기존 감사처럼 SciPy가 없는 환경에서는 이 직접 경로가 막히며, 이번에는 평가 venv의 현 설치 상태를 재조회하지 않았다. 함수 본문을 바꾸지 않는 선택 로더는 후속 후보지만, 구현·실제 import·동일성/모델 parity를 하지 않았으므로 **`SOURCE_AUDITED / SELECTIVE_LOADER_DESIGNED / IMPORT_AND_EVAL_NOT_RUN`**이다. “공식 코드가 단순하다”를 실행 가능 증거로 대신하지 않는다.

고정 원천은 `babylm-org/babylm-eval@6f825c291e2c4c78ad33b1935fd64d45f52642dc`다. [반입 manifest](/home/uranus/tinyLM/data_cache/p106b_official_eval_tools/babylm_eval_6f825c291e2c4c78ad33b1935fd64d45f52642dc_minimal_blimp/manifest.json)는14개 선택 파일의 부분 반입이며, [라이선스 추가 영수증](/home/uranus/tinyLM/data_cache/p106b_official_eval_tools/babylm_eval_6f825c291e2c4c78ad33b1935fd64d45f52642dc_minimal_blimp/license_addendum_manifest.json)은 `strict/LICENSE`를 더한15개를 기록한다. 이 담당은 영수증과 코드 내용을 읽었지만 hash를 재계산하거나 원격 반입을 재현하지 않았다. 소스의 Apache-2.0 표기는 평가 자료의 권리를 대신하지 않는다.

아래에서 `S`는 위 경로의 `source/strict/`다. `S/evaluation_pipeline/__init__.py`, `sentence_zero_shot/{run.py,compute_results.py,read_files.py,dataset.py,__init__.py,README.md}`, root/strict README, requirements, eval shell의 관련 원문을 읽었다. 긴 dataset/compute 파일은 causal·collate·집계·import와 필요한 다른 분기만 읽었고, 패키지 전체 완독을 주장하지 않는다. `utils.py`의 상단 SciPy 의존도 읽었으나 **현재 BLiMP import 그래프에 이 파일을 요구하는 내부 import는 찾지 못했다.**

현재 [작업원장](/home/uranus/tinyLM/handoff/WIP_20261022_작업원장.md:33)과 [기존 공식 평가 감사](/home/uranus/tinyLM/docs/research/20261023_antithesis_official_eval_and_methods.md:112)를 재사용했다. 원장의 Core6 진행 상태는 다른 담당의 기록이며 이 담당의 실행 증거가 아니다. `impact-analysis`는 호출·공식성의 세 대안 비교에, `exp-preflight`·`exp-plan`은 비용 관측/비교 유효성의 경계 확인에 사용했다. `wip-ledger`를 다시 읽었지만 이 하위 작업의 쓰기 권한은 소유 연구문서뿐이므로 총괄 원장은 바꾸지 않는다. 신규 코드·source 수정·설치·다운로드·패키지/tokenizer/model import·GPU/평가 실행은 모두0이며 §10 GradMag 검토는 보존한다.

### 11.2 실제 import 경로와 아직 닫히지 않은 의존성

정상 package import의 내부 연결은 다음과 같다. 경로의 모든 함수가 호출 전부터 import된다는 점과 실제 task에서 호출되는 점을 분리했다.

```text
evaluation_pipeline/__init__.py
  -> transformers import + TokenizersBackend 호환 alias 설정 시도
sentence_zero_shot/run.py
  -> transformers AutoModelForCausalLM/MaskedLM/Seq2SeqLM, torch
  -> dataset.py -> transformers.AutoProcessor, torch, pad_sequence
                -> read_files.py -> datasets.load_dataset, aiohttp
  -> compute_results.py -> torch/F/DataLoader, scipy.stats.spearmanr,
                           math, Counter/defaultdict, tqdm, argparse
```

| 지점 | 원문으로 확인한 실제 경계 | 현재 판단 |
|---|---|---|
| `compute_results.py:9` | `spearmanr`는 상단 import이고 읽은 파일 내 다른 사용은 없음 | BLiMP에서 안 쓴다고 정상 import가 생략되지는 않음. `spec_from_file_location`/`runpy`만으로도 이 import를 건너뛸 수 없음 |
| package `__init__.py` | transformers에 `TokenizersBackend` alias를 넣는 부작용을 try/except로 감쌈 | 하위모듈 정상 import도 parent를 실행. 무부작용 소스 읽기와 다름 |
| `dataset.py` | AutoProcessor 상단 import와 `from_pretrained(...trust_remote_code=True)` 생성자, ValueError/KeyError일 때만 fast tokenizer fallback | TinyLM/Falcon의 기존 strict loader를 자동 재사용하지 않으며 fallback이 ImportError 등을 모두 복구하는 것도 아님 |
| `read_files.py` | images=None이어도 `datasets`·`aiohttp`는 상단 import | 원문 JSONL만 읽는다는 이유로 stdlib-only 모듈로 분류할 수 없음. `load_dataset` 호출 자체는 images 분기에 있음 |
| 실제 설치된 transformers 소스 | `models/auto/processing_auto.py`가 image/feature/processing/video 모듈을 import. `processing_utils.py`는 audio/image/video helper를 import하며 audio는 일부 설치 가용성에 따라 librosa/soxr/torchaudio를 더 import | text-only AutoProcessor에도 넓은 import 경로가 있음. 가용성 조건의 실제 분기·평가 venv 전체 transitive closure는 실행하지 않아 미확인. SciPy 하나만 해결하면 전부 가능하다는 결론은 안 됨 |

마지막 행은 `/home/uranus/miniforge3/envs/tlm_torch/lib/python3.10/site-packages/transformers/`의 실제 `models/auto/{__init__,processing_auto}.py`, `processing_utils.py`, `audio_utils.py`, image/video helper 상단을 읽은 근거다. 평가 venv의 동작을 학습 환경 소스 존재로 증명하지 않는다. 기존 최소 의존성 감사의 SciPy 미설치 기록은 재사용했으나 이 담당이 새 metadata 조회/import를 수행한 것은 아니다. 추가 패키지를 선제 설치하거나 fake SciPy 모듈로 import 성공처럼 꾸미지 않는다.

### 11.3 세 호출안과 최소 함수 폐쇄 후보

| 안 | 실제 경로 | 장점 | 한계·영향·비용 |
|---|---|---|---|
| A. 정상 공식 CLI/모듈 | `get_dataloader → compute_results → process_results` | 원 패키지 경로·공식 예제와 가장 가까움 | 현재 SciPy 등 미승인 의존/AutoProcessor/strict model 로딩 차이로 HOLD. 설치 확대는 별도 승인 사항이며 기존 Core6 환경을 바꾸지 않음 |
| B. 고정 source의 선택 함수 로딩 | 원문 함수 AST/본문을 변경 없이 선택하고 명시적 globals·기존 strict model/tokenizer adapter를 주입 | SciPy 등 미사용 상단 import를 실행하지 않고 **실제 공식 함수 본문** 재사용을 검증할 수 있는 후보 | 새 선택 로더·closure·원문 동일성·wrapper parity가 필요. package 정상 import/공식 CLI 완료가 아니고 현재 구현/실행은 NOT_RUN |
| C. 기존 Core6 sum scorer 또는 별도 복제 | 기존 adapter의 문장 합우도에 BLiMP 집계 규칙을 새로 접합 | 기존 모델 수치 경로 재사용 가능 | BOS/첫 target/offset/tie/UID 차이가 남음. 같은 합우도 이름만으로 공식 likelihood 함수와 동치가 아니며 `LOCAL_VARIANT`로 제한 |

**무설치 제한 아래 후속 검토 권고는 B지만 현재 채택/구현 승인은 아니다.** A의 의존 해결은 새 권한이고, C는 이번 “같은 공식 함수” 질문에 직접 답하지 못한다. B도 아래 폐쇄와 실제 parity를 닫기 전 가능/공식 PASS로 표현하지 않는다.

소스의 causal BLiMP에 필요한 최소 후보는 `decode_blimp → process_causal_sentences → get_causal_collate_fn → compute_causal_results → rank_and_evaluate → process_results`다. `update_subset_to_stats`를 함께 보존한다. 보충도 `task='blimp'`와 별도 directory로 같은 연결을 쓰는 것이 공식 `eval_zero_shot.sh`의 방식이다. 이 shell 전체는 EWoK·Entity·COMPS·reading까지 호출하므로 BLiMP만의 입구로 실행하면 범위가 커진다.

- `decode_blimp`는 입력 dict와 filename만 쓰므로 dataset/HTTP import가 필요 없는 함수 본문이다. `process_results`도 args.task와 집계 dict를 쓰며 model loading을 요구하지 않는다. annotation은 원문의 `from __future__ import annotations`와 함께 보존해야 한다.
- 공식 token/phrase 처리와 collate까지 보존하려면 native tokenizer가 내는 `input_ids/attention_mask/offset_mapping`을 processor 인터페이스에 맞게 넘기는 접합이 필요하다. `process_causal_sentences`는 class method라 `self.processor` 등 필요한 속성도 명시해야 한다. AutoProcessor 생성자를 몰래 부르거나 tokenizer JSON을 HF용으로 덮어쓰는 방식은 제외한다.
- 계산 함수의 실제 globals 폐쇄 후보는 `torch`, `F`, `Counter`, `defaultdict`, `tqdm`, `DEVICE`, `LENGTH_NORMALIZED_TASKS`, 위 보조 함수들이다. collate에는 `pad_sequence`가 더 필요하다. `compute_results` dispatch까지 선택한다면 미사용 backend 이름도 causal-only 계약에서 어떻게 거부할지 명시해야 한다. 선택 노드/함수 원문 hash·상수·globals allowlist·소스 파일/줄 provenance를 남기고, 누락 global을 임의 stub으로 채우지 않는다.
- 위 목록은 수동 소스 추적의 **설계 후보**다. 실제 AST 자유변수 검사·compile/import·합성 함수 호출·모델 실행을 하지 않았다. 함수 본문이 같아도 model logits·tokenizer 입력·DEVICE/precision·RNG가 달라지면 결과는 같지 않다.

### 11.4 공식 likelihood·tie·UID의 정확한 규약

[고정 compute source](https://github.com/babylm-org/babylm-eval/blob/6f825c291e2c4c78ad33b1935fd64d45f52642dc/strict/evaluation_pipeline/sentence_zero_shot/compute_results.py#L60), [dataset source](https://github.com/babylm-org/babylm-eval/blob/6f825c291e2c4c78ad33b1935fd64d45f52642dc/strict/evaluation_pipeline/sentence_zero_shot/dataset.py#L55), [decode source](https://github.com/babylm-org/babylm-eval/blob/6f825c291e2c4c78ad33b1935fd64d45f52642dc/strict/evaluation_pipeline/sentence_zero_shot/read_files.py#L96), [집계 source](https://github.com/babylm-org/babylm-eval/blob/6f825c291e2c4c78ad33b1935fd64d45f52642dc/strict/evaluation_pipeline/sentence_zero_shot/run.py#L84)를 실제 로컬 원문과 대조했다.

1. BLiMP는 good/bad **문장 전체**가 각각 completion이며 label0이다. causal collate는 `inputs=tokens[:-1]`, `targets=tokens[1:]`, phrase mask도 `[1:]`로 한 번 민다. 계산은 `log_softmax(logits/temp)`에서 target을 gather한 뒤 phrase mask를 곱해 **합**한다. BLiMP/보충에는 token/문자/byte 길이 정규화가 없다. τ=100인 ALM과도 별개이며 공식 CLI의 기본 평가 temperature는1이다.
2. phrase mask는 offset의 `end > start_char_idx`인 token을 선택한다. special offset(통상0,0)은 일반 본문과 다르다. BOS가 자동 추가되지 않는 tokenizer라면 첫 실제 token은 shift 과정에서 채점되지 않는다. 공식 함수는 BOS를 일괄 삽입하지 않는다. “whole sentence”라는 문구만 보고 별도 빈 prefix/BOS를 더하면 첫 token 포함 여부가 바뀐다.
3. `rank_and_evaluate`는 NaN score를−inf로 바꾼 뒤 최대값의 **정확한 동점**에서 `torch.randint`로 후보를 균등 무작위 선택한다. 첫 후보 우선·strict greater·항상0.5 credit·epsilon 근접동점은 이 함수와 다르다. 양쪽 NaN/−inf도 동점 무작위 판정으로 흘러갈 수 있으므로 raw score/NaN·inf·정확 동점 수를 별도 보존하고 수치 무효를 정상 성과로 발표하지 않는다. NaN 행만 빼고 분모를 줄이는 것도 규약 변경이다.
4. 본 BLiMP의 `UID`는 원문 필드다. `field`가 없는 보충은 `UID=file_name.stem`, field/linguistics_term은 supplement다. 최종 average는 `UID`별 accuracy의 **동일 가중 macro 평균**이다. 67개 파일이 각1000쌍인 원본 BLiMP의 수량을 BabyLM filtered 자료에 복사하거나 모든 pair의 micro 평균으로 대신하지 않는다. 본·보충 UID를 한 번에 합쳐 평균하는 것도 두 별도 보고와 다르다.
5. 예측 ID는 `UID`마다 만난 순서의 `uid_0,uid_1,...`다. `read_files`는 directory `iterdir()`를 정렬하지 않는다. 원 source 경로/행/원문 ID와 순서 manifest를 별도 보존해야 하며, 정렬 변경과 batch 순서 변경은 tie RNG 및 저장 ID에도 영향을 줄 수 있다. CLI 자체에는 seed 인자가 없으므로 통제 seed/RNG 기록은 추가 재현 계약으로 명시한다.
6. CLI는 temperature가 여럿이면 그 **평가 accuracy가 가장 높은** temperature를 선택하고 동점이면 먼저 만난 값이 남는다. 이를 고정 temperature1의 zero-shot 대조와 섞지 않는다. 이번 후속 후보는 temperature를 사전 고정하고 평가 점수로 tuning하지 않는 것이 최소 비교다. 최고온도 탐색이 원 기능이라는 사실은 TEST를 이용한 모델/λ 선택의 승인이 아니다.

### 11.5 TinyLM·Falcon 접합에서 확인해야 할 반례

기존 [Core6 adapter](/home/uranus/tinyLM/scripts/p106b_official_lm_adapter.py:366)는 `(context,continuation)`과 빈 context의 prefix를 소유하는 TemplateLM 경로다. BabyLM의 문장 전체 tokenize→shift 경로와 같지 않으므로 이 adapter의 이전 oracle 성공을 BLiMP parity로 이월하지 않는다. 원 TinyLM tensor 반환은 공식 계산 함수가 요구하는 tuple 또는 `{'logits':...}`와도 다르다. model wrapper가 `input_ids/attention_mask`를 받고 실제 full-position logits를 반환하는 별도 접합이 필요하다.

| 항목 | 실제 소스에서 확인한 차이 | 후속 검증/실패 조건 |
|---|---|---|
| chat32 native tokenizer | §5.6의 JSON은 normalizer=null, ByteLevel, BOS ID1이 있으나 BOS 삽입 TemplateProcessing은 없음 | 실제 processor adapter의 native IDs·문자 offsets·attention·phrase mask와 첫/마지막 채점 target을 기록. 빈/한 token 문장·선두 공백·구두점·개행·special처럼 보이는 문자열 포함 |
| 단일 token의 입력 shape | 공식 `process_causal_sentences`는 `len(tokens)==1`이면 batch 차원으로 보고 `[0]`을 취함. processor가 평평한 `[id]`를 반환하면 이 분기가 정수로 축약할 수 있음 | processor의 실제 shape를 확인해야 하는 조건부 반례다. 빈/단일 token canary 실패를 숨기려고 BOS나 가짜 token을 추가하지 않음. 입력 shape 접합과 원 함수 변경을 구분하고 실행 미확인을 보존 |
| 정확 Falcon Base | 현재 Core6 source가 지명한 snapshot `7994372...`의 config는 bos1/eos11/pad0, tokenizer JSON은 normalizer=null/post_processor=null. tokenizer_config에는 eos만 명시되고 BOS 자동삽입 설정은 확인되지 않음 | model config의 BOS ID와 tokenizer의 실제 자동 삽입은 별개다. 기존 Core6 HFLM은 add_bos_token=False와 빈 context prefix를 쓰므로 그대로 같은 score라고 보지 않음. tokenizer 실행 확인은 NOT_RUN |
| native 분절 | Falcon은 Punctuation/regex/ByteLevel/숫자 분리의 Sequence이고 chat32와 다름 | 두 모델의 어휘 수가 같아도 token 수·공백 분절이 같다는 전제 금지. 같은 원문 pair에서 각 모델 native tokenizer를 사용하고 실제 채점 token 수를 각각 보존 |
| model 호출·padding | 공식 causal 함수는 `attention_mask`를 넘기고 full `B×T×V` logits를 사용. TinyLM 기존 helper는 tensor 직접 반환·별도 causal route | tuple/dict wrapper와 right-pad 불변을 검산. attention mask를 assistant loss mask로 바꾸지 않음. Falcon recurrence/KV·TinyLM의 repeat/route 상태는 요청마다 초기화하고 singleton/batch/순서 교환 parity를 각각 확인 |
| 수치·경계 | 공식 합은 gather 뒤 mask 곱셈이며 0×NaN/−inf도 NaN이 될 수 있음. text 입력에서 logits 길이가 다르면 이미지 경로를 가정해 뒤를 자르는 코드가 있음 | FP32 수학·MTPoff/no-cache·native head를 고정하고 실제 위치/logits shape·finite 여부를 별도 검사. text-only 길이 불일치를 자동 crop으로 성공 처리하지 않음 |
| 문맥 cap | 읽은 causal processor/collate에는 공통1024 cap·skip/rolling이 없음 | 각 native token 길이를 먼저 확인. 한 모델만 초과하여 자르거나 누락하면 같은 full 평가가 아님. 공통 subset/cap 변형은 제외 수와 원문 단위의 별도 결과이며 공식 full로 명명하지 않음 |
| 동점·정밀도 | 정확한 같음만 무작위 판정. 부동소수점 경로가 바뀌면 동점 여부도 바뀔 수 있음 | CPU tie RNG와 입력 순서/seed 상태를 보존. model별 tie/근접 margin/비정상 수를 별도 남기고 실제 sampled tie 선택을0.5로 사후 대체하지 않음 |

Falcon은 tokenizer/config 텍스트의 위 설정만 읽었고 weight를 열거나 모델/tokenizer를 실행하지 않았다. strict loader·native ID·source fingerprint·eval/no_grad·precision·cache·원 CP 불변은 총괄의 기존 runtime 계약을 유지해야 한다. Base와 Instruct·GGUF 양자화본의 점수를 같은 모델 결과로 합치지 않는다.

### 11.6 단어 예산·공식성·비용 관측의 한계

고정 [Strict README](https://github.com/babylm-org/babylm-eval/blob/6f825c291e2c4c78ad33b1935fd64d45f52642dc/strict/README.md#L139)는2026의 strict-small100M/strict1B **word** checkpoint 예산을 설명하며 누적 제시량 기준을 명시한다. 과거 연도의10M/100M을 이번 트랙에 자동 대입하지 않는다. TinyLM의 native token draw·고유 풀·SFT target·반복 epoch, Falcon의 별도 사전학습 노출은 이 word 예산과 같은 단위가 아니다. 이번에 모델들의 raw corpus word 수/누적량/적격성을 재검산하지 않았으므로 같은 parameter 규모나 BLiMP 점수만으로 데이터 효율·대회 적격·동일 예산 우열을 주장할 수 없다. 한국어 문법/대화 능력의 직접 평가도 아니다.

원문 함수 재사용은 leaderboard 제출·완전 BabyLM suite·공식 서버 채점과 다르다. BLiMP와 supplement 두 과제만의 score를 전체 zero-shot·fine-tuning·AoA/reading·checkpoint-fast 종합점수로 쓰지 않는다. 원 자료 LICENSE 미명시와 모델 학습 오염 여부 미감사는 기존 감사 경계를 유지한다. 실제 선택 로더를 쓰면 **“고정 BabyLM2026 공식 함수 재사용, 별도 native adapter, 부분 과제”**라고 범위를 남기고 공식 CLI의 무수정 실행과 구별한다.

후속 비용 관측은 승인 후 총괄이 아래 순서로 설계할 대상이다. 이 담당은 명령·새 태그·실행 파일을 만들지 않았다.

1. **모델 없는 함수 계약부터.** 선택 노드/hash/globals 폐쇄·모듈 부작용을 감사하고 합성 logits의 shift/offset/첫 token·good/bad 순서·정확 동점·NaN/−inf·UID별 불균등 표본·보충 filename UID·macro 평균을 독립 oracle와 대조한다. 원모듈을 정상 import할 수 없는 상태면 이 검사만으로 원 CLI runtime parity PASS라고 하지 않는다.
2. **대표 표본 비용은 성과와 분리.** 사전 지정된 본/보충·짧은/긴/native 분절 경계 표본으로 TinyLM·Falcon을 하나씩 측정한다. 기존 Core6와 모델 상주를 겹치지 않는다. source/CP/tokenizer 검산·기동·tokenization/offset·warmup·steady likelihood·집계·저장/종료 wall을 나누고, batch·정밀도·유효 input/target tokens·padding·원문 pair/UID 수·peak VRAM/RSS를 보존한다. 짧은 canary의 평균으로 최악 길이 비용을 보장하지 않는다.
3. **전수 비용은 실제 filtered 분모로.** 후속 reader가 실제 본67/보충5 파일의 행/UID 수와 token 길이 분포를 먼저 닫아야 한다. 현재 이 담당은 평가 본문을 읽거나 행수를 집계하지 않았다. 본/보충 각각2문장/pair의 실제 비용을 모델별 추정하고 startup/긴 꼬리/저장 여유를 더한다. full softmax는 logits와 log_probs가 각각 `B×T×V`를 차지하므로 기존 target-row-only 경로의 메모리/속도를 복사하지 않는다. 기본 batch64가 안전하다는 추정도 금지한다.
4. **운영/판정.** 시간·메모리·종료 cap과 partial 보존을 사전 계획으로 닫고 두 모델 같은 원문 분모의 완주 여부를 남긴다. 부분 UID만 끝나면 해당 subset 결과다. NaN·초과 길이·자료/원문 hash·shift/UID 불일치·wrapper float fallback은 모델 능력0점과 구분해 중지/무효로 보존한다. 기존 다른 계열 σ와 supplier 점수를 새 scorer 점수의 향상 판정에 대입하지 않는다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 12. 긴급 소스 감사: Qwen27B의 no-thinking template와 raw TF 경계

### 12.1 핵심 답과 소스 정체성

**`POST /apply-template`에는 `"chat_template_kwargs":{"enable_thinking":false}`를 실제 JSON boolean으로 전달하는 계약이 있다.** top-level `"enable_thinking":false`만으로 같은 효과를 얻는 읽힌 경로는 없다. raw `/completion`은 chat template parser를 호출하지 않으므로 같은 kwargs를 raw 요청에 더하는 것만으로 기존 prompt의 `<think>` 문맥이 바뀌지 않는다. 먼저 template가 반환한 정확 prompt를 확정하고 그 native token prefix에서 TF해야 한다. 이 결론은 코드 경로 감사이며 실제 요청 성공·원확률 개선을 측정한 결과가 아니다.

로컬 `/home/uranus/llama-b11396/`에는 지명된 binary/shared library가 있으나 요청받은 `tools/server/`·`common/` 소스 디렉터리는 없었다. “로컬 C++ 소스를 읽었다”고 쓰지 않는다. 대신 기존 [TF report](/home/uranus/tinyLM/test_result/evidence/p106b_qwen_tf_v1_s1337/report.json:327)의 `/props` 기록 `build_info="b11396-2e7c58c54"`를 읽고 그 commit prefix의 공식 GitHub 원문을 열었다. report의 build 식별자와 웹 source의 연결이며 binary 재해시·재빌드/실행 동일성 증명은 아니다. exact tag의 GitHub API 열람은 실패했고, 아래 원문은 `main`이 아니라 `2e7c58c54`를 사용했다.

총괄이 전달한 “raw ChatML 첫 숫자 target logp≈−27, top1 `<think>`≈1”은 이 담당의 재측정이 아니다. 해당 관측은 **형식/conditioning 불일치와 양립**하지만 원인 전체의 확정이나 교사 수학 지식 부재를 뜻하지 않는다. 코드·자료·원 cache·teacher profile·서버 설정은 수정하지 않았고 API·모델/GPU·템플릿 렌더 실행·설치/다운로드는 하지 않았다. 이 문서의 새 절만 작성하며 §10 GradMag와 §11은 보존한다.

### 12.2 실제 함수 연결·요청키·기본값

| 공식 소스·함수 | 확인한 계약 |
|---|---|
| [tools/server/server.cpp](https://github.com/ggml-org/llama.cpp/blob/2e7c58c54/tools/server/server.cpp#L241) HTTP 등록 | `/completion`은 `routes.post_completions`, `/apply-template`은 `routes.post_apply_template` |
| [server-context.cpp: server_routes::init_routes, post_apply_template](https://github.com/ggml-org/llama.cpp/blob/2e7c58c54/tools/server/server-context.cpp#L4806) | 요청 JSON을 `oaicompat_chat_params_parse(body,meta->chat_params,files)`로 처리하고 `data.prompt`만 반환. 추론은 하지 않음 |
| [server-common.cpp: oaicompat_chat_params_parse](https://github.com/ggml-org/llama.cpp/blob/2e7c58c54/tools/server/server-common.cpp#L1223) | `add_generation_prompt` 기본true. 서버 default kwargs에 요청 `chat_template_kwargs`를 key별 덮어씀. nested `enable_thinking` boolean false를 읽어 inputs를 false로 설정. 문자열 `"false"`는 invalid type 오류 |
| 같은 함수의 reasoning 옵션 | top-level `reasoning_effort="none"`는 inputs.enable_thinking=false와 effort 제거. `reasoning_format="none"`는 출력 parser 형식이고 no-thinking과 다름. 충돌 kwargs를 함께 보내지 말고 위 boolean false를 명시하는 것이 가장 직접적 |
| [common/chat.cpp: common_chat_templates_apply_jinja/direct_apply_impl](https://github.com/ggml-org/llama.cpp/blob/2e7c58c54/common/chat.cpp#L848) | inputs 및 kwargs를 Jinja context로 전달. extra kwargs가 기본 context를 덮으므로 서로 모순되는 enable_thinking/effort 조합의 우선순위를 단순화해 설명하지 않음 |
| [common/common.h](https://github.com/ggml-org/llama.cpp/blob/2e7c58c54/common/common.h#L582) | use_jinja=true, prefill_assistant=true가 source 기본. 실제 서버 실행 인자에 따른 override는 별도 |

`server-common.cpp`는 `inputs.add_generation_prompt=true`와 non-NONE `continue_final_message`를 동시에 요구하면 오류를 낸다. 단, 마지막 assistant에 대한 **자동 prefill** 분기는 generation prompt를 false로 바꾸므로 기본값 조합의 의미가 달라진다. `continue_final_message=false`를 보내도 NONE으로 해석된 뒤 서버 prefill 기본이 다시 AUTO로 바꿀 수 있어, 이를 “자동 prefill을 끄는 요청키”로 가정하지 않는다.

### 12.3 기존 `/props`에 실제 들어 있는 Qwen template의 차이

[보존 props의 chat_template](/home/uranus/tinyLM/test_result/evidence/p106b_qwen_tf_v1_s1337/report.json:328)를 읽었다. 전체 파일을 새 GGUF에서 추출하거나 실행한 것은 아니다. 다음은 template 조건의 해석이며 반환 bytes의 실제 canary가 남는다.

- **새 assistant generation prompt:** `add_generation_prompt`가 true이면 assistant 시작을 추가한다. `enable_thinking`이 명시적 false면 `<think>`의 **닫힌 빈 블록**을 붙이고, 그렇지 않으면 열린 `<think>`로 끝낸다. no-thinking은 think 마커를 모두 삭제한다는 뜻이 아니다.
- **기존 assistant message:** assistant 본문 렌더는 `enable_thinking`과 별개의 `preserve_thinking`/마지막 user 이후 위치 조건을 쓴다. 기본 preserve는 켜져 있고, `reasoning_content`가 없어도 빈 think 블록이 들어갈 수 있다. `preserve_thinking=false`여도 마지막 user 이후 assistant는 위치 조건으로 블록이 남을 수 있다.
- **system conditioning도 바뀜:** thinking이 켜졌을 때 reasoning_effort default xhigh 등의 지시를 만들며, enable_thinking=false이면 이 지시 생성 분기가 꺼진다. 단순 raw ChatML 뒤에 닫힌 태그만 손으로 추가하는 것은 native template 전체 적용과 무조건 같지 않다.
- **본문 전처리:** 이 props template는 message content/reasoning_content에 `trim`을 사용한다. 학습 원문/assistant target의 끝·앞 공백을 보존한 기존 raw serializer와 차이가 날 수 있다. 동일 target bytes·mask 정합을 재검산해야 한다.

표시상 newline의 정규형은 아래와 같지만, JSON escape/Jinja literal의 실제 렌더 bytes는 `/apply-template` 반환 문자열을 보존해 확인해야 한다. 문서 표기를 직접 prefix로 복사해 실행 정합을 대신하지 않는다.

```text
thinking on : <|im_start|>assistant\n<think>\n
thinking off: <|im_start|>assistant\n<think>\n\n</think>\n\n
```

### 12.4 정확한 JSON 요청 예 — 작성만 했으며 전송하지 않음

**A. 마지막 메시지가 user인 새 답안 prefix를 no-thinking으로 렌더:** `POST /apply-template` body다. 마지막 assistant를 넣지 않아 자동 assistant-prefill과 분리한다.

```json
{
  "messages": [
    {"role": "user", "content": "17 + 25의 결과 숫자만 답하세요."}
  ],
  "add_generation_prompt": true,
  "chat_template_kwargs": {"enable_thinking": false}
}
```

응답의 `prompt`가 native no-thinking prefix다. TF는 **이 prefix에 reference 정답을 잇는 실제 native ID열**에서 시작해야 한다. 전체 encode와 target 경계, 특수 token·BOS·공백 및 양 모델의 byte/mask 정합은 별도 검사한다. 숫자 target에 닫힌 think 블록을 gold로 포함시키거나 student의 원래 정답/CE mask를 조용히 바꾸지 않는다.

**B. 이미 있는 assistant 내용을 이어 쓸 때의 명시적 content continuation:** 마찬가지로 `POST /apply-template` body다. 이 예시는 빈 새 답 prefix와 같은 사건이 아니다.

```json
{
  "messages": [
    {"role": "user", "content": "17 + 25의 결과 숫자만 답하세요."},
    {"role": "assistant", "content": "4"}
  ],
  "add_generation_prompt": false,
  "continue_final_message": "content",
  "chat_template_kwargs": {"enable_thinking": false}
}
```

숫자 전체 `42`를 assistant content에 이미 넣고 그 뒤에서 첫 숫자의 TF logp를 읽으면 gold 누설/shift 오류다. 부분 prefix 예시의 `4`와 채점할 다음 target도 구분한다.

**C. chat 요청의 간단한 별도 off 표현:** `POST /apply-template`의 top-level `"reasoning_effort":"none"`도 코드상 disable 입력을 만든다. 다만 `chat_template_kwargs.enable_thinking=true` 같은 상충 kwargs와 섞지 않는다. 서버 default kwargs에 이미 enable_thinking=true가 있는 경우도 이 충돌 검사에 포함한다. 이 필드는 inputs를 false로 만들지만 남은 kwargs의 최종 Jinja 덮어쓰기까지 무조건 이긴다는 계약은 아니다. API의 `reasoning_effort`와 props template가 직접 허용하는 xhigh/medium/low를 혼동하지 않는다. parser가 none을 소비하므로 none 문자열을 Jinja effort로 그대로 넘기는 경로와 다르다.

```json
{
  "messages": [
    {"role": "user", "content": "17 + 25의 결과 숫자만 답하세요."}
  ],
  "add_generation_prompt": true,
  "reasoning_effort": "none"
}
```

### 12.5 마지막 assistant 자동 prefill과 과거 assistant history는 다르다

기본 prefill_assistant가 true이고 마지막 role이 assistant면 `oaicompat_chat_params_parse`는 continuation AUTO와 add_generation_prompt=false를 택한다. 마지막 assistant가 연속2개면 오류다. [common/chat.cpp](https://github.com/ggml-org/llama.cpp/blob/2e7c58c54/common/chat.cpp#L1167)는 마지막 메시지를 임시로 떼고 AUTO를 통상 CONTENT로, content 없이 reasoning_content만 있으면 REASONING으로 분류한다.

[common/chat-auto-parser-generator.cpp: peg_generator::generate_parser](https://github.com/ggml-org/llama.cpp/blob/2e7c58c54/common/chat-auto-parser-generator.cpp#L27)는 continuation prefix를 다시 만들며, reasoning 시작이 감지된 template에서는 시작 태그·reasoning_content를 붙이고 CONTENT continuation이면 끝 태그도 붙인 뒤 content를 잇는다. 이 분기는 새 assistant generation suffix의 enable_thinking=false 분기와 동일한 단순 문자열 덧셈이 아니다. 실제 감지된 delimiter/공백은 local 반환 prompt로 확인해야 한다.

반면 history 속 완결 assistant는 props의 message별 렌더 조건을 적용받는다. [common/jinja/caps.cpp: caps_apply_preserve_reasoning](https://github.com/ggml-org/llama.cpp/blob/2e7c58c54/common/jinja/caps.cpp#L19)는 `preserve_reasoning`을 `preserve_thinking`, `clear_thinking` 등의 template 변수로 매핑한다. history 보존 끄기와 새 답의 thinking 끄기를 같은 옵션으로 설명하지 않는다. `add_generation_prompt=false` 하나만으로 모든 기존 assistant의 think 삽입이 사라지지도 않는다.

### 12.6 raw `/completion`과 실제 TF cache로 넘길 때의 중지 경계

[server-context.cpp의 post_completions](https://github.com/ggml-org/llama.cpp/blob/2e7c58c54/tools/server/server-context.cpp#L4664)는 원 body를 `handle_completions_impl`에 직접 넘긴다. chat 요청만 거치는 `oaicompat_chat_params_parse`를 호출하지 않는다. `handle_completions_impl`은 data.prompt를 tokenize하므로 raw text/ID를 이미 정한 뒤 `chat_template_kwargs`를 더해도 template가 다시 적용되지 않는다. budget/출력 reasoning parser·sample 제어는 prompt 자체를 native no-thinking prefix로 바꾸는 작업의 대체가 아니다.

| 후속안 | 분리할 목적 | 한계·비용 |
|---|---|---|
| A. user로 끝난 `/apply-template` + nested false | 새 정답 prefix의 native no-thinking bytes/IDs를 먼저 확정 | 가장 직접적 source 계약. 교사·학생 conditioning 차이와 mask 재검산 필요 |
| B. 기존 assistant content continuation | 이미 존재하는 답 prefix를 이어 가는 TF/생성 | 자동 prefill·분리/재합성·기존 content 누설 위험이 추가됨 |
| C. raw serializer에 마커를 수동 추가 | template 호출 없이 고정 prefix 사용 | source의 system/trim/history 처리까지 재현했는지 별도 감사. native template 동등성을 전제할 수 없음 |

소스상 첫 비교에 적합한 것은 A이며 총괄의 실제 채택/실행은 별도다. 원 rawChatML 음성·−27 관측을 지우지 않고, no-thinking prefix 변경을 **새 cache namespace/설정/원문 hash**로 구분한다. 생각 모드를 바꿔도 첫 정답 확률이 올라간다고 보장하지 않는다. 원 target 정답은 그대로 둔 채 template suffix·native token ID/shift·pre-sampling logp의 진실성을 먼저 비교해야 한다.

후속 canary에서 확인할 것은 반환 prompt와 props/실행 source의 식별, nested false의 실제 반영, 열린/닫힌 think suffix·기존 assistant 분기의 차이, 원 gold 첫 token의 정확한 앞 prefix, BOS 중복/특수 token 처리, 원 logits와 강제-bias 신호의 정합이다. 새로운 teacher 이력/문맥을 썼다면 기존 ALM의 교사 신호가 같다고 부르지 않는다. 실제 API/렌더/학습 효과는 이 담당 기준 전부 `NOT_RUN`이다.

## 13. 후속 구체화: BabyLM 선택 함수와 기존 encoded LL의 최소 연결

### 13.1 이번 질문의 답과 세 경로의 정확한 이름

§11을 함수 인자·shape·클로저 수준에서 다시 추적했다. 고정 BabyLM commit은 그대로 `6f825c291e2c4c78ad33b1935fd64d45f52642dc`, 기존 LL의 harness commit은 `d6de81643928d653435c431bae19945d41d32520`다. **공식 decode/rank/집계 함수는 미사용 module import를 피한 선택 로딩 후보가 있고, 기존 encoded-token LL과 연결하는 작은 접합을 설계할 수 있다. 그러나 그 접합은 원 `compute_causal_results` 자체를 호출하는 것과 다르다.** likelihood 수학/입력·수치 parity가 확인되기 전 전체를 “같은 공식 likelihood 함수 실행”으로 보고하지 않는다.

| 경로 | 실제로 재사용하는 것 | 판단·영향·비용 |
|---|---|---|
| A. 정상 공식 package/CLI | 원 import·AutoProcessor/모델 로딩·compute/집계 전체 | §11의 무조건 SciPy import가 남는다. 새 설치를 하지 않는 현재 범위에서 바로 가능한 경로로 선언하지 않음 |
| B. 선택 함수 + 기존 encoded LL | 공식 decode·원 token/phrase 처리·collate·rank·UID 집계, 모델 수치는 기존 `_loglikelihood_tokens`/`core.score_encoded` | 새 TinyLM LM adapter·새 모델 loader가 필요 없는 최소 연결 후보. 원 causal likelihood loop를 대체한다는 사실과 수학/실물 parity 필요를 공개. 선정 로더/작은 orchestration도 아직 미구현·미실행 |
| C. 선택한 원 causal 함수의 합성 oracle | 원 `compute_causal_results`에 미리 정한 합성 logits를 주고 공식 gather/mask/합을 독립 확인 | B의 likelihood 재계산을 검산하는 작은 기준. 실제 모델·전체 CLI의 대체가 아니며 그대로 모델 평가에 쓰려면 full-logits 호출 인터페이스가 별도 필요 |

**현재 요청의 최소 후속 방향은 B를 C와 독립 계산으로 먼저 대조하는 것**이다. B의 지원 범위를 유한 score·고정 temperature1·truncation 없는 native ID열로 제한하고, 못 맞추는 경우 새 adapter로 확장하지 말고 HOLD한다. 이번에는 `impact-analysis`를 실제 호출 경로·대안·공식성 영향 분석에 사용했다. 코드·fixture 파일·실제 평가 본문·모델/토크나이저 import·설치·Git·새 agent·수치 실행은 모두0이고, 이 절만 추가한다. 현재 평가 venv의 새 import 성공이나 패키지 전체 의존 충족을 확인한 것은 아니다.

### 13.2 선택 로딩의 전역·데코레이터·클로저 감사

아래는 §11의 로컬 `source/strict/evaluation_pipeline/sentence_zero_shot/` 실제 원문을 다시 읽은 결과다. 정상 import를 피한다는 것과 함수의 의미까지 자동 보존된다는 것은 다르다.

| 선택 대상·원문 위치 | 호출 인자와 런타임 의존 | 분리 시 보존할 것 |
|---|---|---|
| `read_files.py:92 decode_blimp` | `(raw_dict,file_name)`; builtins와 `file_name.stem`만 본문에서 사용 | annotation의 `Any/pathlib`는 future annotations로 지연됨. 함수를 쓰기 위해 `datasets/aiohttp`를 import할 필요는 없는 본문이지만 원 모듈 정상 import에는 필요 |
| `dataset.py:55 process_causal_sentences` | `(self,sentence_dict,image)`; text-only는 `image=None`, `self.processor`, `torch` | **인스턴스 메서드이며 `@classmethod`가 아니다.** 본문에는 super/`__class__` capture가 없음. 원 node를 선택하고 명시적 self/processor를 넘기는 후보. 전체 class/생성자를 실행하면 AutoProcessor 로딩으로 범위가 커짐 |
| `dataset.py:420 get_causal_collate_fn` | `(pad_idx)`가 내부 `collate_fn(batch)`를 반환; `torch/pad_sequence` | **실제 클로저가 있다: pad_idx를 capture한다.** 내부 함수만 떼어내지 말고 원 outer factory를 통째로 선택·호출해 closure를 생성해야 함 |
| `compute_results.py:51 update_subset_to_stats` | `(subset_to_stats,metadatas)`; `Counter` | 첫 metadata의 key만 보고 field별 counter를 만든다. batch metadata schema 일관성이 전제 |
| `compute_results.py:60 rank_and_evaluate` | `(args,stats,all_log_probs,raw_sentences,labels,metadatas,uids,predictions)`; `torch` | 외부 lexical closure는 없지만 torch의 전역 RNG/default device/dtype에 의존. stats/predictions를 in-place 변경하며 자동으로 copy하지 않음 |
| `run.py:74 process_results` | `(args,results)`; 본문은 builtins·입력 dict | 원 module의 AutoModel import·DEVICE가 이 함수 호출에 필요한 것은 아님. BLiMP는 args.task만 참조하며 UID별 percent/macro 순서를 보존 |
| `compute_results.py:90 compute_causal_results` | `(args,model,dataloader,temperatures)`; `defaultdict/tqdm/DEVICE/F/torch/LENGTH_NORMALIZED_TASKS` 및 위 두 보조 함수 | oracle C에 한정. 선택 함수만 호출하면 바깥 dispatcher의 no_grad 문맥이 사라지므로 caller가 명시적으로 보존해야 함 |

선택한 함수에는 데코레이터가 없고 mutable default argument도 없다. 그러나 **`compute_results`의 `with torch.no_grad()`는 데코레이터가 아니라 외부 호출 문맥**이다. `compute_causal_results`만 골랐다고 no_grad가 따라오지 않는다. `get_causal_collate_fn`의 pad closure와 ranking의 torch 전역 RNG도 의미 있는 의존이므로 “전역/클로저가 없다”는 요약은 틀리다.

선택 AST 후보는 원 파일 bytes/hash·node 이름/범위·body/decorator/default·허용 globals를 고정하고 `from __future__ import annotations`를 포함해야 한다. annotation을 삭제하거나 다른 의미의 class를 주입해 import를 통과시키지 않는다. runtime annotation introspection은 이 최소 경로에 필요 없고, 사용하면 미해결 annotation 이름에 별도 의존이 생긴다. 원 함수의 globals namespace를 하나로 유지해 보조 함수가 정확한 공식 원문을 참조하도록 해야 한다.

`ast.parse`/node 선택 자체와 `compile/exec`에 의한 함수 생성은 다른 단계다. 이번에는 둘 다 실행하지 않았고 **수동 원문 감사**만 했다. 전체 모듈에서 SciPy import 한 줄만 없앤 파일을 만들거나 `sys.modules`에 fake SciPy를 넣는 방법은 제안하지 않는다. parent package의 TokenizersBackend alias·`DEVICE=torch.cuda.is_available()` 초기화도 이 선택 경로에서는 자동 실행하지 않으며, 생략한 초기화와 명시한 globals를 provenance에 남겨야 한다.

### 13.3 구체 입력·출력·중간 shape

아래 호출 표기는 구현 파일이나 실행 명령이 아니라 연결 계약이다. 본·보충을 각각 `args.task='blimp'`, temperature key `1.0`, text-only로 처리한다. `save_predictions=True`면 prediction dict 준비도 필요하다.

B의 공식 rank/집계만 부를 때 필요한 args 필드는 `task='blimp'`, `save_predictions=True`다. C의 원 causal 함수를 직접 부르면 `images_path=None`이 추가로 필요하고 `temperatures=[1.0]`를 넘긴다. 바깥 `compute_results` dispatcher까지 부를 때만 `backend='causal'`도 필요하다. 경로별로 필요한 실제 필드를 구분하며 CLI의 model_path/download 관련 필드를 채웠다는 이유로 새 loader를 호출하지 않는다. B의 decode/mask/collate/rank/집계 본문에 대해 추적한 폐쇄는 기존 torch와 stdlib 범위이고, C는 추가로 기존 tqdm 등의 명시적 globals가 필요하다. SciPy/AutoProcessor/datasets 호출을 피하는 선택 후보이지 실제 선택 로딩 성공을 확인한 것은 아니다.

1. `decode_blimp(raw_dict,Path(filename))`는 `sentences/completions=[good,bad]`, `prefixes=[None,None]`, label0와 metadata를 반환한다. 본 과제는 원 UID·field·linguistics_term, 보충은 filename stem UID다. `syntax_semantics` field의 `syntax/semantics` 표준화도 원 함수에 맡긴다.
2. `process_causal_sentences(self,sentence_dict,None)`에서 self.processor는 원 native tokenizer의 text·offset 계약을 제공해야 한다. 호출은 `processor(text=sentence,return_offsets_mapping=True)`이며 결과는 같은 길이 L의 IDs/attention/offsets다. 공식 method가 만드는 candidate별 `tokens/attn_mask/phrase_mask`는 CPU LongTensor `[L]`, image는None이다. §11의 단일-token flat list 오인 분기를 포함해 실제 반환 shape를 검증해야 한다. 토크나이저를 새로 만들거나 BOS를 더해 이 분기를 우회하지 않는다.
3. `get_causal_collate_fn(native_pad_id)`로 얻은 closure에 item의 5-tuple `(raw_sentence_dict,processed,label,metadata,uid)` 목록 B개를 넣는다. 각 candidate j는 별도 최대 길이 `Lmax_j`로 right-pad된다. 입력/target/attention/phrase는 `[B,Lmax_j−1]`; 입력은 padded tokens의 `[:-1]`, target과 phrase는 `[1:]`다. 반환은 `(raw_sentences,sentence_dict,labels,metadatas,uids,images)`의6-tuple이고 raw_sentences/labels/metadatas/uids 목록은 각각 길이 B, images=None이다.
4. B의 기존 LL 연결은 다음 절의 **원 native IDs와 phrase mask**를 받아 candidate별 scalar loglikelihood를 반환한다. `all_log_probs[1.0]`은 `[good_scores_B,bad_scores_B]`, 각 원소가 CPU `[B]` tensor여야 한다. 원 rank의 `torch.stack(...,dim=1)` 결과는 `[B,2]`다. B개의 `[good,bad]` tensor 목록을 그대로 넘기면 전치/분모 오류가 생길 수 있으므로 B=3 이상의 합성 예제로 드러낸다.
5. stats는 `{1.0:{}}`, predictions는 `{1.0:defaultdict(list)}` 형태로 시작한다. 같은 순서의 `metadatas`로 공식 `update_subset_to_stats`를 부른 뒤, 위8개 인자를 공식 `rank_and_evaluate`에 넘긴다. 각 metadata key의 `total/correct` Counter와 UID별 prediction list가 갱신된다. 원 함수의 zip은 길이 불일치를 자동 검출하지 않으므로 모든 행·score·label·UID 개수를 caller가 먼저 대조해야 한다.
6. 공식 `process_results(args,stats)`는 `(accuracies,average_accuracies)`를 반환한다. 각 정확도 단위는 **0~100 percent**이고 final은 UID 정확도의 macro 평균이다. Core6의0~1 fraction과 단위를 섞지 않는다. 원 compute 함수의 최종 prediction 포장은 `{temp:{uid:{'predictions':list}}}`이므로 ranking 중의 defaultdict(list)와 저장 포장도 구분한다.

원 공식 causal loop C의 중간 shape는 logits `[B,T_j,V]` → `log_softmax(logits/1.0)` `[B,T_j,V]` → targets를 gather한 `[B,T_j]` → shifted phrase mask 곱·합 `[B]`다. BLiMP에는 길이 나눗셈이 없다. 양쪽 후보의 T는 서로 같을 필요가 없다. 원 함수와 B를 비교할 때 dtype·선택된 full-vocab logits·reduction 축·pad 폭을 함께 보존해야 한다.

### 13.4 새 TinyLM adapter 없이 기존 LL을 잇는 범위

[기존 TinyLM encoded LL](/home/uranus/tinyLM/scripts/p106b_official_lm_adapter.py:256)과 그 [토큰 메서드](/home/uranus/tinyLM/scripts/p106b_official_lm_adapter.py:416), [고정 HFLM 메서드](/home/uranus/tinyLM/data_cache/p106b_official_eval_tools/lm_eval_d6de81643928d653435c431bae19945d41d32520/source/lm_eval/models/huggingface.py:1329)를 읽었다. 두 런타임의 `_loglikelihood_tokens([(None,context_ids,continuation_ids),...],disable_tqdm=True)`는 같은 encoded request 형태를 받는다. TinyLM은 이미 존재하는 `core.score_encoded`로, Falcon HFLM은 기존 모델/FP32 log-softmax 경로로 간다. 새 모델·TinyLM LM class·생성/tokenizer loader를 만드는 설계가 아니다. 이 메서드는 고정 source의 private 인터페이스이므로 새 버전에 대한 안정 API 보증은 없다.

문장 native IDs를 `t[0:L]`, 원 **unshifted** phrase mask를 m이라 하고 `J={i:1≤i<L,m[i]=1}`로 둔다. 원 BabyLM의 score는 `Σ(i∈J) log p(t[i]|t[:i])`다. J가 하나의 연속 구간 `[a,b]`이면 기존 LL에 **context=t[:a], continuation=t[a:b+1]**를 넘기는 것이 최소 수학 대응이다. raw 첫 token은 조건으로 남고 두 번 encode/shift하지 않는다. padding ID와 EOS를 일괄 지우는 것이 아니라 원 m이 정한 target 집합을 따른다.

- BOS가 없는 일반 문장의 m이 전부1이면 a=1이다. 첫 실제 token을 context로 두고 나머지만 채점한다. 빈 문자열 context의 `loglikelihood('',sentence)`를 쓰면 TemplateLM이 prefix/BOS를 더할 수 있어 같은 사건이 아니다. model config에 BOS ID가 있다는 사실만으로 원 tokenizer에 BOS를 삽입하지 않는다.
- BOS가 실제 ID열 앞에 있고 offset(0,0)으로 m=0이면 그 BOS를 context에 보존해 첫 본문 token부터 채점한다. 뒤 EOS가 m=0이면 점수에서 제외하되 중간에 있는 비채점 token은 이후 target의 prefix에서 삭제하면 안 된다. EOS/BOS의 존재와 자동 삽입 여부는 모델별 actual encode 계약을 기록한다.
- J가 불연속이면 연속구간마다 **원 t의 전체 앞 prefix**를 context로 유지하고 해당 구간만 continuation으로 채점해 합하는 수학 대안이 있다. 다만 호출 수/합산 dtype·순서/상태 reset이 추가된다. 최소 구현이 이 경우를 지원하지 않으면 조용히 다른 score를 내지 말고 해당 입력 계약에서 HOLD한다.
- J가 비거나 문장/입력이 너무 짧으면 기존 LL은 빈 continuation을 허용하지 않는다. 원 causal loop의 유한 logits·zero mask에서 합0이 되는 특수형을 그대로 흉내 내며 모델 호출을 생략하면 masked NaN의 차이를 감출 수 있다. 이 경우를 정상0점으로 만들지 말고 합성 oracle의 정의/무효 분류로 먼저 닫는다.
- 기존 LL은 긴 context를 자를 수 있다. **채점할 마지막 raw 위치 b가 model max_length 이하이고 context truncation이0**인 범위부터 사용한다. 원 함수 C와의 입력 유효성도 맞추려면 각 전체 native 문장의 L−1 및 candidate별 batch 폭 Lmax_j−1도 모델 문맥 이내인지 함께 확인한다. 비채점 EOS/suffix를 뺀 B만 문맥에 맞는 경우는 원 full-input 호출과 같은 지원 범위가 아니다. HFLM은 내부 길이 정렬 뒤 `get_original`로 순서를 되돌린다. 반환 순서를 다시 임의 정렬하지 않는다. cache key None과 기존 logits-cache OFF를 유지해 평가 요청 cache를 새로 쓰지 않는다.
- B는 temperature1 전용이다. 기존 scalar LL을 단순히 온도로 나누면 `log_softmax(logits/tau)`가 되지 않는다. 여러 temperature/TEST 최적 온도 선택을 지원한 것처럼 표시하지 않는다.

**수학적 일치와 bitwise 일치는 다르다.** 원 causal loop는 masked/padded 전체 T를 합하고, 기존 LL은 continuation 부분을 합한다. trailing EOS·pad의0 항을 빼더라도 reduction 길이/순서·batch padding·kernel이 달라지면 마지막 bit가 달라질 수 있다. float64로 재합산하거나 scalar를 새 dtype으로 반올림하면 exact tie도 바뀔 수 있다. 특히 Falcon의 기존 HFLM causal 호출은 attention_mask를 넘기지 않는 반면 원 BabyLM loop는 넘긴다. right-pad/문맥·recurrent state의 singleton/batch parity가 실물에서 확인되기 전 무조건 동등하다고 하지 않는다.

원 함수 C는 tuple 또는 logits dict를 기대하고 기존 TinyLM LL 객체는 scalar/greedy를 반환한다. scalar LL을 가짜 logits로 변환해 C를 호출한 것을 원 likelihood 실행으로 세는 우회는 제외한다. 최소 B에서 official 함수 재사용을 주장할 범위는 **decode/mask/collate/rank/집계**, likelihood는 **기존 LL 경로의 대응 검증**이라고 분리하는 것이 정확하다.

### 13.5 RNG·집계의 재현 순서와 불가한 단축

순서는 본/보충별 입력 manifest → 원 file/row 순서의 decode → native token/mask → 모델 LL 내부 정렬·원순서 복원 → good/bad score 벡터 → metadata 초기화 → 공식 rank의 tie RNG → 전체 Counter → 공식 UID macro다. `UID` dict의 최초 등장 순서와 합산 순서도 보존한다. 파일 `iterdir()`가 원래 미정렬이라는 사실과 기록한 한 실행의 순서가 있다는 사실을 구분한다. 본·보충 각각의 stats/RNG 시작·끝/예측 ID 범위를 남기고 두 macro를 섞지 않는다.

원 rank는 **torch 전역의 기본 RNG**를 쓴다. default device가 CPU인 통상 조건이면 CPU RNG이지만, source에 device/generator 인자가 없으므로 default-device 변경까지 무시한 “항상 CPU” 계약은 아니다. §11의 CPU tie RNG 표현에는 이 기본-device 전제가 붙는다. 실제 환경의 default device/dtype·CPU/CUDA RNG 상태·temperature 순서·batch 순서·직전 난수 소비를 고정/기록해야 한다. 후보별 LL 완료 순서와 무관하게 rank는 원 item 순서로 호출한다.

한 번의 seed 설정만으로 모델 쌍의 tie 선택이 문항마다 같아지는 것은 아니다. 두 모델의 tie 위치/개수가 다르면 소비하는 난수열도 달라진다. 원 함수에 없는 item별 재seed·local generator·epsilon 동점·0.5 credit를 넣으면 별도 규약이다. 독립 재계산은 시작 RNG 상태를 보존해 동일한 exact-tie 순서로 `randint` 호출을 재생하고 실제 chosen index·Counter·prediction을 대조해야 한다. 예측 문자열만 저장하면 같은 문자열 후보의 선택 index는 식별되지 않을 수 있어 실제 chosen index도 진단 기록 대상으로 둔다.

NaN score를−inf로 바꾸는 원 rank, exact tie 무작위, UID macro는 그대로다. 기존 TinyLM LL은 nonfinite를 오류로 거부하므로 **비정상 입력에서 원 rank의 무작위 결과까지 같은 pipeline이라고 주장할 수 없다.** NaN/inf는 별도 수치 무효로 보존하고 행을 삭제해 분모를 축소하지 않는다. 입력/shape/prefix·tie 정의를 고친 뒤에도 예전 점수를 같은 공식 점수로 개명하지 않는다.

### 13.6 합성 fixture와 독립 재계산의 최소 조건 — 전부 미실행

아래는 실제 평가자료를 읽지 않고 만든 검증 명세다. fixture 코드나 파일은 작성하지 않았다. source를 그대로 썼다는 확인과 독립 oracle 일치를 분리한다.

| fixture | 합성 계약·반례 | 독립 확인 기준 |
|---|---|---|
| shift/no-BOS | t=[1,2,3], m=[1,1,1] | 원 inputs=[1,2], targets=[2,3], shifted mask=[1,1]. 기존 LL context=[1], continuation=[2,3]. 별도 BOS로 token1까지 채점하면 실패 |
| actual BOS/EOS | t=[99,1,2,88], m=[0,1,1,0], special offsets=(0,0) | 본문 targets1/2만 채점하고 BOS는 prefix에 남음. EOS88은 점수 밖. 원 T와 LL의 더 짧은 T가 만드는 수치 차이도 기록 |
| 내부 mask 구멍 | t=[99,1,77,2,88], m=[0,1,0,1,0] | 두 번째 target2의 prefix에77이 남아야 함. score에77의 NLL을 더하거나 prefix에서77을 지우면 다른 사건 |
| shape/길이/pad | B=3, good/bad의 L을 서로 다르게 지정, 적어도 한 row는 right-pad | candidate별 `[B,T_j]`와 rank `[3,2]`, row/UID/label 수가3인지 확인. pad ID가 실제 EOS와 같아도 phrase/attention으로만 제외 |
| decode/보충 | 합성 dict의 field=`syntax_semantics`와 별도 field 없는 dict, filename=`toy_suffix.jsonl` | 원 decode의 field 표준화·label0·good-first·보충 UID=`toy_suffix`를 독립 dict 기대값과 대조. 실제 corpus/문항은 사용하지 않음 |
| macro 대 micro | UID A는2행 중1정답, UID B는1행 정답 | 원 macro는75 percent, micro는2/3. 3×2 score 행렬과 raw count를 독립 계산해 두 지표 혼동 검출. 빈 UID/영 total은 무조건0으로 채우지 않음 |
| tie RNG/NaN | 서로 다른 두 후보의 같은 finite score, 한쪽 NaN, 양쪽 NaN/−inf, 근접하지만 다른 score를 별도로 지정 | finite exact tie만 동일 RNG 상태에서 선택 재생. 한쪽 NaN은 finite 후보 우세, 양쪽 무효는 원 함수상 tie가 될 수 있으나 수치 무효로 분류. 근접값을 임의 tie로 만들지 않음 |
| 집계/반환 순서 | 길이가 다른 요청을 LL에 섞고 파일/UID/row의 원 순서를 별도 기록 | HFLM의 내부 정렬 후 original 복원, rank의 good/bad 열, UID별 누적 예측 ID를 독립 순서표와 대조 |
| single/empty·상태 | 단일-token flat/batched processor 형태와 빈 tokens, 같은 원문을 singleton/batch·앞뒤 순서 교환 | 원 method의 flatten 조건과 zero-target/길이 오류를 명시. 캐시/recurrence/quant route 잔존으로 실물 score가 달라지면 HOLD; 합성 구조 성공을 실물 PASS로 올리지 않음 |

수치 oracle는 작은 **고정 full-vocab logits**에서 각 target에 `logit_y−logsumexp(all_logits)`를 독립 계산하고, 원 phrase mask·shift를 적용해 합해야 한다. 같은 공식 `F.log_softmax/gather/sum`을 그대로 두 번 호출하는 것은 독립 재계산이 아니다. 예를 들어 정답 token의 확률이 각1/2인 두 위치와 각1/4인 두 위치를 지정하면 합우도는 각각 `log(1/4)`·`log(1/16)`이며, 길이 나누기/첫 token 포함·마스크 오염을 분리할 수 있다. 실제 Torch FP32와 독립 고정밀 계산의 오차/score margin을 함께 기록하고 tolerance는 실행 전 총괄이 정한다.

검산은 (a) source 선택/closure/hash, (b) 합성 full-logits 공식 C 대 독립 수치 oracle, (c) 같은 합성 encoded target의 B 대 C, (d) 실제 native tokenizer의 IDs/offsets/마스크, (e) 실제 기존 모델 LL의 singleton/batch·precision/무절단/무상태 parity의 순서다. 이 담당은 어느 단계도 실행하지 않았다. source-only 결론은 **미사용 SciPy import를 피할 함수 수준의 설계 가능성과 명확한 잔여 계약**이며 현재 평가환경에서의 성공 확정·공식 full BLiMP 완료·지능/문법 향상 판정은 아니다.

## 14. V5 TF의 UTF-8 fragment 확률 누락 — llama.cpp b11396 고정 소스 감사

### 14.1 범위·핵심 결론

총괄이 보고한 관측은 V5 batch0/1 각16행 완료 뒤 batch2의 `alm_000034`, native target ID36054 강제·`n_predict=1`에서 `content='�'`, `tokens=[]`, `completion_probabilities` 누락이다. 관측 위치는 `/home/uranus/tinyLM/HF/sft_ready/p106b_alm_context_v5_s1337/teacher_cache/batch_000002`다. **이 담당은 해당 자료의 문맥·정답·의미나 실제 요청/응답 파일을 열지 않았다.** 아래는 공식 `ggml-org/llama.cpp`의 commit `2e7c58c54`에 고정한 읽기 검토이며, §12의 기존 build-info 식별 근거를 재사용한다. 바이너리 재빌드·해시 동등성까지 입증한 것은 아니다.

**불완전 UTF-8에서 보류되는 것은 화면 문자열만이 아니다. 현 구현은 그 단계의 확률 객체 저장도 건너뛴다. `return_tokens=true`는 ID 진단에는 도움이 되지만 확률 누락을 복구하지 않는다. `stream=true`나 단순 다중-token 연장도 첫 target 확률 복구를 보장하지 않는다.** 원 prefix에서 다른 정상 출력 token을 선택하고 그 단계의 원 top-K에서 target ID를 직접 찾는 방법은 조건부 API 대안이며, 모든 target에 대한 보장은 full-vocab 반환 또는 출력과 독립적인 scorer 변경이 필요하다. 다음 선택지는 미실행·미채택이다.

이번에는 `impact-analysis`를 출력 옵션만 변경하는 경우·우회 회수·별도 scorer의 영향/비용/공식성 비교에 적용했다. 학습 목표·ALM 수식·기존 §10 GradMag 및 §11/13 BabyLM 설계는 바꾸지 않는다.

### 14.2 원인 경로: 문자열 보류와 확률 객체 소실

[공식 server-context.cpp](https://github.com/ggml-org/llama.cpp/blob/2e7c58c54/tools/server/server-context.cpp)의 다음 순서를 직접 확인했다.

| 위치 | 소스에서 확인한 동작 |
|---|---|
| `3669~3720`, 일반 sampling 경로 | 현재 prefix에서 sampling한 후 해당 단계의 확률 객체를 만들고 `process_token`에 전달 |
| `1750~1761` | generated byte 문자열에 piece를 붙임. 요청 시 raw ID도 별도 저장한 뒤 UTF-8 말단 검사 |
| `1764~1790` | **말단이 불완전하지 않을 때만** 확률 객체 추가와 streaming partial 전송 |
| `458~465` | `add_token`은 전달된 **현재 객체 하나**만 append; 누락된 과거 객체를 복구하는 대기열이 아님 |
| `1793~1808` | 불완전하면 계속 생성하려 하지만, 뒤의 token 예산 검사에서 다시 종료 가능 |
| `1978~2027` | final은 별도 ID열·누적 문자열·저장된 확률 목록을 사용; 중단된 단계 확률 재계산 없음 |

따라서 첫 단계가 이 말단 검사에 걸리고 예산이1이면 확률 목록은 비어 있을 수 있다. 뒤 token으로 문자가 완성되더라도 새로 저장되는 객체는 그 **뒤 단계의 조건부 확률**이다. 여러 token의 문자열이 한꺼번에 출력됐다는 이유로 그 객체를 첫 native target에 대응시키면 잘못된 TF cache가 된다. 위 흐름은 보고된 현상과 일치하지만, ID36054의 실제 piece와 요청 필드를 이 담당이 직접 검산한 실물 재현은 아니다.

`validate_utf8`라는 이름을 완전한 Unicode 검증기로 해석하면 안 된다. [공식 server-common.cpp:844](https://github.com/ggml-org/llama.cpp/blob/2e7c58c54/tools/server/server-common.cpp#L844)는 마지막 최대4바이트에서 2/3/4-byte 선두 바이트의 부족 여부만 검사한다. prefix의 마지막 bytes는 이 generated-text 검사에 포함되지 않는다. 예컨대 합성 `[0xEA]`는 부족하지만 독립 continuation `[0x80]`은 이 함수에서 전체 길이를 반환할 수 있다. 이는 실제 ID36054의 bytes를 가정한 예가 아니며, 모든 fragment가 똑같이 누락된다는 뜻도 아니다.

누락과 대체문자는 서로 다른 경로다. [공식 server-task.cpp:323](https://github.com/ggml-org/llama.cpp/blob/2e7c58c54/tools/server/server-task.cpp#L323)는 non-stream final의 확률 목록이 비면 해당 JSON key를 아예 만들지 않는다. `tokens`의 기본 저장은 [server-task.h:46](https://github.com/ggml-org/llama.cpp/blob/2e7c58c54/tools/server/server-task.h#L46)의 `return_tokens=false`다. 따라서 빈 ID열만으로 생성0개라고 판정할 수 없다. 문자열 직렬화는 [common/json.cpp:314](https://github.com/ggml-org/llama.cpp/blob/2e7c58c54/common/json.cpp#L314)의 잘못된 UTF-8 대체 모드를 사용한다. `�`에서 원 piece를 역추정하거나 이를 원문의 실제 대체문자로 캐시하면 안 된다.

### 14.3 옵션별로 가능한 것과 불가능한 것

| 옵션·경로 | 원 첫 target logp/top2 회수 판단 |
|---|---|
| `/completion`, `return_tokens=true`, `stream=false` | raw ID 진단을 추가하는 후보. **확률 저장 gate는 그대로**이므로 단독 해결 아님 |
| `/completion`, `stream=true` | 불완전 단계의 partial 자체가 생기지 않음. 이후 partial의 ID/prob는 현재 단계이며 final은 확률 목록을 다시 내보내지 않음. SSE로 바꾸는 것만으로 첫 단계 회수 불가 |
| `n_predict>1` | 원 첫 prefix의 계산 자체는 그대로일 수 있으나 첫 단계 확률 객체 소실을 되돌리지 않음. 증가분을 TF target0의 확률로 쓰거나 확률 배열 index=생성 index로 단정하지 않음 |
| 강제 bias 유지한 다중 token | 같은 bias가 다음 단계에도 적용될 수 있어 올바른 UTF-8 완성/정답 suffix를 보장하지 않음. 예산 증대만으로 해결된다고 하지 않음 |
| `grammar`로 문자/ID열 강제 | sampling 제약이지 확률 저장 gate 해제 옵션이 아님. 문자열 grammar는 다른 native 분절을 선택할 수도 있음 |
| `/v1/completions`로 변경, `echo=true` | 원 확률 저장 누락을 공통 출력 포맷 변경으로 복구하지 못함. OAI parser는 echo=true를 명시 거부 |
| prompt에 target을 넣고 `n_predict=0` | prompt 평가만 하는 API 계약을 prompt target의 logprobs 반환 API로 간주하지 않음. 누락 위치 확률을 나중 단계 확률로 대체하지 않음 |
| `/v1/systemone` | 일반 raw-logits API가 아님. decision-model 종류 검사·전용 template/label 설정이 있어 Qwen native TF 우회로로 제시하지 않음 |

streaming JSON 조건과 partial의 단일 prob 객체는 [server-task.cpp:983](https://github.com/ggml-org/llama.cpp/blob/2e7c58c54/tools/server/server-task.cpp#L983), echo 거부는 [server-common.cpp:969](https://github.com/ggml-org/llama.cpp/blob/2e7c58c54/tools/server/server-common.cpp#L969), `n_predict=0`/옵션 계약은 [공식 README](https://github.com/ggml-org/llama.cpp/blob/2e7c58c54/tools/server/README.md), decision 설정은 [server-decision.cpp:61](https://github.com/ggml-org/llama.cpp/blob/2e7c58c54/tools/server/server-decision.cpp#L61)에서 확인했다. README의 확률 배열 길이가 `n_predict`라는 일반 설명은 이 불완전-byte 소스 분기에서 성립한다고 믿을 수 없다.

이 commit의 grammar는 [src/llama-grammar.cpp:170](https://github.com/ggml-org/llama.cpp/blob/2e7c58c54/src/llama-grammar.cpp#L170)에 native-ID 표기 `<[36054]>` 파서도 갖는다. 따라서 “GBNF는 문자만 다룬다”는 반론은 정확하지 않다. 다만 같은 파일 `989~1029`, `1286~1295`, `1369~1413`은 partial UTF-8 상태와 token 규칙의 상호작용을 검사하므로 **파싱 성공만으로 fragment-ID 강제 성공을 보장할 수 없다.** 정확 ID열 grammar를 쓰더라도 서버의 확률 누락 원인은 별도로 남는다. 단순 진단용 요청 형태는 `"grammar":"root ::= <[36054]>"`이나 실제 유효성·선택 ID·실행 가능성은 미검증이며, 오늘 cache 회수의 확정 해결책이 아니다.

### 14.4 원 pre-sampling 확률을 유지하는 대안 비교

원 사건은 `log p_T(y_i | x_0,...,x_{i-1})`다. native prefix IDs·BOS·template·KV 상태를 그대로 두고 **생성 뒤의 화면 처리만 달라져야** 한다. prefix에 ASCII를 먼저 넣거나 fragment를 포함한 문자열을 다시 tokenize하면 일반적으로 다른 사건이다. 문자가 같다는 사실은 native ID열 동등성 증명이 아니다.

[공식 common/sampling.cpp:125](https://github.com/ggml-org/llama.cpp/blob/2e7c58c54/common/sampling.cpp#L125)는 원 logits에서 sampler용 후보 배열을 따로 복사한다. 같은 파일 `563~637`에서 grammar/bias 등의 sampling이 그 후보에 작용한다. pre-sampling 확률은 별도 원 logits에서 구하며, 원 서버는 이 확률이 필요할 때 backend sampling을 비활성화한다. 따라서 **올바른 설정·동일 prefix·실물 canary를 전제로**, 선택 token만 정상 UTF-8 ID로 바꾸고 원 top-K의 target ID 확률을 읽는 방법을 검토할 수 있다. `post_sampling_probs=true`는 이 계약이 아니다.

| 대안 | 정확 API·구현 위치 | 장점·선결·위험 |
|---|---|---|
| A. 정상 UTF-8 probe 선택 + 원 top-K에서 target 조회 | 기존 `POST /completion`; `n_predict=1`, `post_sampling_probs=false`, `backend_sampling=false`, `return_tokens=true`, `stream=false`, `n_probs=K`, 정상 probe ID의 양수 bias | 바이너리 변경 없는 조건부 후보. **target이 실제 반환 top-K에 있어야 함.** 없으면 logp를 만들 수 없으며 K=2만으로 임의 target을 보장하지 못함. 필요 시 K=V가 보장 범위지만 응답/CPU 비용이 큼 |
| B. 출력과 독립한 확률 보존 패치 | `process_token` 전후에 native step별 확률 저장을 별도로 설계하고 final JSON에서 bytes/ID와 함께 반환 | 첫 fragment도 K=2 및 sampled-target logp로 보존하는 구조 후보. 서버 소스 변경·빌드·배포·새 canary가 필요하며 현재 승인 범위 밖. gate 바깥으로 줄 하나 이동하는 것만으로 stop-word 절삭/stream 계약까지 안전하다고 단정하지 않음 |
| C. libllama native-ID TF scorer | `llama_decode` 후 `llama_get_logits_ith(ctx,i)`의 full-vocab row에서 target logit와 LSE/top2 직접 계산 | 문자열 생성/샘플러에 의존하지 않는 원리적 후보. 새 driver·ABI/동일 모델 설정·KV reset·shift/row 선택의 검증이 필요. 별도 모델 중복 상주나 실행을 자동 승인한 것이 아님 |

**권장 순서는 A를 비용 상한이 있는 소형 canary 후보로만 검토하고, target 포함을 확인할 수 없거나 K=V가 기존 응답/시간 한도를 넘으면 중단하는 것**이다. 장기 반복 TF에는 B/C처럼 출력과 수치 취득을 분리하는 방향이 낫지만, 이 문서에서 새 핵심코드/서버 교체를 채택하지 않는다. 기존 fragment 강제+다중 token 방식을 조용히 계속 돌리는 것은 첫 확률 복구 근거가 없다. 실행 옵션 변경·client 변경·서버 변경 중 무엇을 허용할지는 총괄/사용자가 정한다.

대안 A의 **JSON 구조 예**는 아래와 같다. `P_PREFIX`는 원 prefix의 정수 ID 목록, `A_VALID`는 bytes가 완전한 비특수 probe의 검증된 정수 ID, `B_FORCE`는 선택을 실제 확인할 유한 bias, `K`는 총괄이 정할 반환 상한이다. 이들은 설명용 치환명이지 그대로 보내는 값이 아니다. 구문에 맞는 예시 숫자만을 위해 실제 어휘 ID·bias·vocab 크기를 날조하지 않는다.

```text
POST /completion
{
  "prompt": P_PREFIX,
  "n_predict": 1,
  "n_probs": K,
  "post_sampling_probs": false,
  "backend_sampling": false,
  "return_tokens": true,
  "stream": false,
  "cache_prompt": false,
  "temperature": 0,
  "logit_bias": [[A_VALID, B_FORCE]]
}
```

반환의 바깥 `completion_probabilities[0].id/logprob`는 **probe**의 것이다. target36054는 `top_logprobs`를 **정수 ID로 검색**하여 얻어야 하며 바깥 logprob를 target으로 잘못 복사하면 안 된다. 원 top2도 같은 목록의 첫 두 원소를 취하되 순위 동점 정책은 별도로 기록한다. probe를 실제 정답 token열에 append해 후속 prefix로 사용하지 않는다. 실제 다음 target의 prefix는 처음부터 동결된 원 native 정답 ID열로 만든다. 이 요청만으로 server CLI의 기존 stop 문자열 등이 모두 해제되었다고 가정하지 않으며, stop_type/실제 선택 ID/무절단도 확인한다.

A의 수치와 비용 근거는 [server-common.cpp:1444](https://github.com/ggml-org/llama.cpp/blob/2e7c58c54/tools/server/server-common.cpp#L1444)의 전체 후보 softmax·상위 K 정렬과 [server-task.cpp:251](https://github.com/ggml-org/llama.cpp/blob/2e7c58c54/tools/server/server-task.cpp#L251)의 ID/bytes/logprob 직렬화다. **상위 K를 다시 정규화하지 않는다.** K=V는 O(V) 객체·문자열/bytes JSON과 정렬 비용을 추가한다. 실제 크기·지연은 미측정이며 기존 응답 byte/time/RSS 한도를 먼저 고정해야 한다. top-K에 없다는 것은 0확률이 아니다. `response_fields`도 target-ID 조건 검색 API로 쓰지 않는다.

C의 공식 함수 계약은 [include/llama.h:1017](https://github.com/ggml-org/llama.cpp/blob/2e7c58c54/include/llama.h#L1017)에 있다. decode에서 output을 요청한 token row와 vocab 축을 구분하며, 원 prefix의 마지막 output row가 다음 target을 예측한다. 고정 raw logits에서 `logit_y−logsumexp(all_logits)`와 raw top2를 계산하는 것이 목표이지 sampler 후 재정규화가 아니다.

### 14.5 검증 선결·중지 조건 — 실제 실행 없음

이하 canary는 제안 계약일 뿐 요청·fixture·수치 계산을 실행하지 않았다. 기존 Stage7a의14요청 성공이 이번 fragment 경로까지 검증했다는 뜻은 아니다.

1. **원 bytes·ID 사건:** 실제 실패 request의 반환 옵션·native prefix hash/길이·target ID와 `/tokenize` 원 piece bytes를 소유 실행자가 대조한다. 이 담당은 source/정답 내용을 열지 않는다. replacement 문자열로 byte reconstruction을 하지 않는다.
2. **gate 재현:** 합성 3-byte 문자 분절·독립 continuation·완전한 ASCII/Korean piece를 구분한다. `n_predict=1`, return_tokens OFF/ON, stream OFF/ON에서 predicted count·raw IDs·prob entry 개수·bytes·SSE event 순서를 각각 확인한다. Unicode가 완성되는 다중-token 예도 first-step object가 보존됐는지 확인해야지 마지막 문자열만 보지 않는다.
3. **bias 비왜곡 canary:** 같은 native prefix에서 정상 probe A/B 및 서로 다른 강도, 무강제 기준을 비교한다. `post_sampling_probs=false`·backend sampling OFF·spec/MTP OFF·같은 GGUF/정밀도/문맥 설정을 고정한다. 실제 선택은 달라도 동일 ID들의 원 logp와 raw top2가 허용 오차 내 같아야 한다. fragment target이 top-K에 없는 경우는 포함 성공으로 세지 않는다.
4. **수치 한계:** 서버 softmax는 FP32 `expf`/누적합 뒤 log를 취한다. K가 달라지면 정렬 및 누적합 순서가 달라져 마지막 bit가 달라질 수 있다. 0으로 underflow한 p는 JSON log에서 FP32 최저 유한값으로 바뀌므로 이것을 정확 logp라고 허용하지 않는다. 별도 scorer의 안정 LSE와 수치 tolerance·top2 근접/동점 기준은 실행 전 정한다.
5. **무오염/정규화:** target ID가 정확히1회 존재하는지, top2와 target의 ID/bytes·원 위치가 맞는지, full-vocab normalizer를 보존했는지 확인한다. 더 긴 생성·probe 문자열·grammar 대체분절을 원 정답 노출로 섞지 않는다. cache 재시작/독립 slot·singleton/batch의 원 prefix parity를 보존한다.
6. **비용과 중지:** K/응답 크기/RSS/지연/요청 수를 먼저 한정한다. target 누락·확률 key 누락·선택 ID 불일치·underflow sentinel·비유한값·문맥 절단·원 top2/logp 비정합·기존 응답 상한 초과 시 그 행을 HOLD한다. 행을 버리거나0 NLL/마지막 단계 logp로 채우지 않는다. 기존 V5 결과를 성공 cache로 승격하거나 변경 전후 provenance를 섞지 않는다.

**증거 수준:** 공식 고정 소스의 함수·분기를 수동으로 추적한 `STATIC_ONLY` 분석이다. 이번 추가 절 외 코드·자료 변경0, 실제 HTTP/모델/GPU/설치/다운로드/Git/추가 agent0이다. 소스 열람은 공식 웹 원문 읽기이며 로컬 소스 취득/빌드는 하지 않았다. 현상 설명과 API 대안의 조건은 확인했으나 V5 실패 행의 실물 재현·원 target 회수·canary 통과·ALM 학습 효과는 전부 미확인이다.

## 15. ASCII probe 확률 회수용 순수 helper — 착수·소유권·검증 기록

### 15.1 착수 전 영향도와 범위

총괄이 §14 대안 A를 조건부 준비하도록 승인했다. 착수 당시 상태는 구현 진행이었고 **현재 담당 완료 범위는 §15.5**가 소유한다. `impact-analysis`와 `wip-ledger`를 읽었다. 새 WIP를 만들 권한은 이번 세 파일 허용목록에 없으므로 공유 원장을 쓰거나 정식 WIP를 흉내 내지 않는다. 착수·미완료·재개 지점을 이 소유 절에만 남기고 총괄 원장은 총괄이 관리한다.

| 파일·경로 | 예정 동작 | 현재 권한 근거 | 제외 |
|---|---|---|---|
| `/home/uranus/tinyLM/scripts/p106b_alm_utf8_probability.py` | stdlib-only 순수 helper 신설 | 총괄의 이번 명시 파일 승인 | HTTP·모델·토크나이저·자료/캐시 접근 없음 |
| `/home/uranus/tinyLM/scripts/test_p106b_alm_utf8_probability.py` | 합성 회귀 신설·CPU 실행 | 총괄의 합성 CPU 회귀 직접 실행 승인 | 실제 prefix/실패 행/서버를 사용하지 않음 |
| 본 연구 문서 | 계약·검증·한계 추가 | 기존 소유 연구 문서 승인 | 기존 문헌/GradMag/BabyLM 절 보존 |

기존 중복은 `diag_p106b_teacher_tf.py:59/74`의 순수 payload/확률 파서와 `diag_p106b_alm_cache.py:769`의 실제 controller 호출부에서 확인했다. 기존 함수는 selected target을 직접 강제하고 cold-cache 일부를 검사하지만, ASCII probe와 별도 reference target의 top-K 조회·엄격 UTF-8 판별·실제 응답 provenance 검사를 함께 제공하지 않는다. **기존 controller는 읽기만 하고 연결·수정하지 않는다.** 기존 bytes helper의 decoder도 바이트 보존용으로 이미 있으므로 새 helper는 tokenizer piece 변환을 중복 구현하지 않고 명시적 bytes만 받는다.

| 영향 축 | 판단 |
|---|---|
| 코드/호출·의존성 | 새 독립 순수 모듈과 새 회귀만 추가. 기존 caller0, stdlib 외 import0 |
| 데이터/스키마 | 자료·cache 변경0. helper의 반환 계약만 신설하며 실제 cache 스키마 채택은 총괄 소유 |
| 테스트 | 합성 정상/실패 경로·무변이·import 경계 검사. 실제 forcing/probe/fragment canary는 총괄 소유 |
| 정본 연쇄 | 실험/기준/판정 상태를 바꾸지 않아 등록부·METHODS·COMPASS 변경 없음. 실제 후속 채택 시 총괄이 처리 |
| 기술부채/비용 | pinned native response 전용 fail-closed 검사. 모델별 probe ID/bytes·special 등록·수치 parity는 외부 증거가 필요 |
| GPU·동시 작업·비교·증거 | 모델/GPU·실데이터·서버0, 다른 담당 파일 수정0. 합성 계약 통과와 실물 확률 동등성은 분리 |

| 선택지 | 장점 | 단점·영향/비용 |
|---|---|---|
| A. 새 순수 helper | 승인한 파일만 바꾸며 실제 controller와 분리 | 호출자는 이후 명시적으로 연결해야 함; 낮은 구현 비용 |
| B. 기존 controller에 즉시 fallback 내장 | 현장 호출 수 감소 가능 | controller 소유권·캐시/재시도 의미가 함께 바뀌어 이번 범위 밖; 중간 이상 검증 비용 |
| C. 서버/libllama scorer 변경 | UTF-8 출력과 확률을 구조적으로 분리 | 빌드·ABI·상주·실물 parity의 새 권한 필요; 높은 비용 |

총괄이 승인한 **A만 구현**한다. K는 사전64/512/2048, bias는100/200이고 helper가 네트워크 재시도·K 상승·자료 선택을 하지 않는다. `MISSING_TARGET`에는 target logp/rank를 None으로 남기며 유한0·selected probe logp로 대체하지 않는다. 첫 probe 선택은 reference 정답을 학습 신호로 검증하는 것이 아니다.

착수 재개 지점: strict bytes/검증 probe → 무변이 payload → 실제 응답 계약/target 조회 → 합성 회귀 → 본 절에 실행 범위·잔여 한계 기록. 실제 서버 canary와 root의 전체 소스 재독/회귀 재실행 전에는 실물 PASS가 아니다.

### 15.2 구현 인터페이스·엄격 계약

- `piece_is_complete_utf8(piece_bytes)`는 비어 있지 않은 **불변 bytes**에 Python strict UTF-8 decode가 성립하는지만 판별한다. 빈 piece는 False, 문자열/list/bytearray는 오류다. byte 내용을 바꾸거나 replacement/정규화하지 않는다. 독립 continuation·잘린 선두·overlong·surrogate·범위 밖 code point는 거부하고, 정상 한글/공백/개행은 완결로 판별한다.
- `ValidatedAsciiProbe(token_id,piece_bytes,vocab_size,special_token_ids)`는 immutable contract다. 표시 ASCII와 TAB/LF/CR 중 비어 있지 않은 bytes, 어휘 범위 내 실제 정수 ID, 명시 tuple의 special ID 제외를 검사한다. **객체를 만들었다는 것만으로 실제 native 어휘 조회/비특수성/forcing 성공이 증명되지 않는다.** 실제 ID↔bytes·완전한 special registry·모델 어휘 크기는 총괄의 provenance 전제다.
- `build_probe_payload(tf_payload,probe=...,n_probs=64|512|2048,bias=100|200)`는 prefix/seed를 그대로 복사하고 기존 target bias만 probe bias로 바꾼다. n_predict1/cache false/raw false/stream false의 기존 계약을 검사하고 반환에는 backend_sampling false/return_tokens true도 명시한다. 중립 수치와 temperature-only sampler를 고정한다. grammar/stop/LoRA/alias 등 미지의 기존 필드는 조용히 전달하지 않고 거부한다. native 정수 prefix에서 BOS·말단 byte·ID 반복을 지우거나 재tokenize하지 않는다.
- `parse_probe_response(response,request_payload=...,probe=...,reference_target_id=...)`는 실제 final/non-stream/limit 종료, 무절단, predicted1, 같은 prefix 길이, 생성 ID1개, content/probe bytes·확률 객체의 같은 ID, timings.cache_n0, 실제 settings의 raw/backend false·neutral sampler/K/seed/bias를 검사한다. 고정 공식 response는 `generation_settings.logit_bias`를 요청의 pair list가 아니라 **token/bias 객체 목록**으로 직렬화하므로 둘을 구분한다. 실제 source는 [server-task.cpp:17/89](https://github.com/ggml-org/llama.cpp/blob/2e7c58c54/tools/server/server-task.cpp#L17), sampler 독립 bias와 중립 chain은 [common/sampling.cpp:307](https://github.com/ggml-org/llama.cpp/blob/2e7c58c54/common/sampling.cpp#L307)에서 추가 확인했다.

성공 조회는 `status=FOUND`, 별도 `reference_target_id`, `target_logprob`, **1부터 세는 target_rank**, `target_probability_origin`을 반환한다. `probe_id/chosen_probe`는 끝까지 별도다. `requested_n_probs`는 요청 K, `actual_n_probs`는 실제 list 길이다. 실제 원 pre-sampling 경로는 길이 min(K,V)를 기대하므로 모자란 list는 정상 누락이 아니라 계약 오류다. target만 원 top-K에 없으면 **MISSING_TARGET + target_logprob/rank/origin/raw_target=None**이며 원 top2와 probe 관측은 보존한다. `lookup_origin`에는 조회한 공식 필드 경로를 남긴다.

원 top2와 전체 top-K entry는 순서·부가 byte 표시까지 deepcopy로 보존하며 정렬·반올림·clamp·재정규화하지 않는다. ID 타입/범위/중복, 양수 logp, 비유한/비수치, sentinel·계산상 exp underflow, 순위 역전, chosen와 top의 동일 ID 수치 불일치를 거부한다. target이 한글 fragment여도 표시 문자열을 decode해 찾지 않고 정수 ID로 찾는다. helper가 probe를 원 정답 prefix에 append하거나 K/bias를 자동 상승시키지 않는다.

### 15.3 재정규화 검사와 실물 증거의 한계

부분 확률을 합1로 다시 만드는 코드는 없다. 실제 flags가 sampling 후 확률이라고 말하거나 `prob/top_probs`가 섞이면 거부한다. 원 top-K와 그 밖 chosen probe의 확인된 질량이1을 넘으면 거부하며, K<V인데 확인된 질량이 정확히1로 포화하면 **부분-어휘 재정규화/수치 포화를 구별할 수 없어 HOLD**한다. tolerance를 새로 골라 위반을 숨기지 않는다.

이 엄격 검사는 **정상 원 분포에도 false HOLD 가능성**이 있다. 아주 확신하는 FP32 분포는 tail이 작아 상위 질량이1 또는 약간 초과로 반올림될 수 있다. 반대로 잘못 재정규화한 숫자가 반올림으로1보다 조금 작고 flags도 원 확률처럼 남으면 부분 response만으로 모든 경우를 식별할 수 없다. 따라서 “재정규화의 모든 위조를 판별했다”는 보장은 불가능하며, 총괄의 독립 native forcing 대 probe logp/top2 canary가 필수다. 이 한계 때문에 신호를 보정·클램프하거나 허용 tolerance를 독자 채택하지 않는다.

request prefix의 값/순서는 보존하지만 응답의 prefix 길이 하나만으로 서버 내부의 실제 ID열/KV 상태까지 입증하지는 못한다. binary/GGUF/template identity, 실제 MTP OFF, context bound, 전체 special registry, budget/원문 보호 및 cache writer/controller는 총괄이 확인한다. probe의 원 확률 자체가 sentinel이면 target이 list에 있더라도 fail-closed한다. helper의 FOUND는 **조회 계약 성공**이지 실물 raw 확률 동등성·정답성·품질 PASS가 아니다.

### 15.4 합성 실행·정정·잔여 검증

첫 `python -B -m unittest ...`는 현재 shell에 python alias가 없어 **exit127·실행 시작 실패**였다. 설치/환경 변경 없이 기존 python3를 사용했고 `python3 -B -m unittest scripts.test_p106b_alm_utf8_probability -v`는 첫 구현에서 합성26/26 통과했다. 이후 seed/underflow·tie/순위 회귀를 보강했으므로 최종 재실행 결과를 아래에 따로 기록한다. `-B`로 bytecode 부산물을 만들지 않는다.

초안 테스트 주석에 일본어 조사1개가 혼입된 것을 발견해 첫 회귀 실행 전에 한국어로 정정했다. 자유서술 보고는 고정 한국어 문장만 사용하며 최종 소유 세 파일에 혼입 문자 검사를 수행한다. 이 정정과 시험 결과를 실물 모델 증거로 올리지 않는다.

최종 재개 지점: 보강한 합성 회귀 재실행 → 소유 세 파일 언어/쓰기 범위 재확인 → 최종 합성 결과 기입. root의 전체 파일 재독·합성 회귀 재실행·정상 token forcing 대 probe 수치동일·실패 fragment 포함 실제 canary는 이 담당의 미실행/대리 미판정 범위다.

### 15.5 최종 담당 산출물·합성 검증 결과

담당 범위의 순수 helper와 합성 회귀를 작성·검증했다. [helper](/home/uranus/tinyLM/scripts/p106b_alm_utf8_probability.py:79)의 UTF-8 판별, [probe 계약](/home/uranus/tinyLM/scripts/p106b_alm_utf8_probability.py:98), [요청 생성](/home/uranus/tinyLM/scripts/p106b_alm_utf8_probability.py:170), [응답 조회](/home/uranus/tinyLM/scripts/p106b_alm_utf8_probability.py:210) 및 [합성 회귀](/home/uranus/tinyLM/scripts/test_p106b_alm_utf8_probability.py:63)가 산출물이다. 기존 TF/cache controller·자료/모델/서버·다른 담당 코드는 연결하거나 수정하지 않았다.

| 검사 | 실제 관측 | 증거 범위 |
|---|---|---|
| `python3 -B -m unittest scripts.test_p106b_alm_utf8_probability -v` | 최종 **28/28 통과**, exit0, 인쇄0.033초 | Python3.12.3의 합성 CPU 계약 검증 |
| 원본/반환 무변이·origin/K/rank·MISSING_TARGET | 합성 prefix/seed/ID/bytes·raw top2/전체 list 보존과 별도 target/probe 필드 확인 | 실제 V5 prefix/fragment 자료를 읽거나 검산한 결과가 아님 |
| 오류·정규화·동점 | 잘린 UTF-8·잘못된 ID/flag/count/cache·중복·양수/비유한/underflow·부분 질량 합1·순위 역전을 거부하고 동점 원순서를 보존 | 재정규화의 모든 수치 위조를 검출했다는 뜻 아님; §15.3 한계 유지 |
| 의존·부작용 | helper의 import는 future/copy/dataclasses/math뿐. fresh import 및 합성 build/parse에서 파일·socket·process 호출 차단 회귀 통과 | 합성 mock 경계이며 서버/모델 E2E가 아님 |
| 한국어 점검 | 소유 세 파일에서 한자/일본어 혼입 문자 검색 결과0건 | 중간 초안 주석의 정정 이력은 §15.4에 보존 |
| 권한/쓰기 | 실제 패치 경로는 승인된 새 두 Python 파일과 본 연구 문서뿐 | 전체 concurrent worktree 상태를 Git/hash로 감사한 것은 아님 |

실행한 명령의 작업 디렉터리는 `/home/uranus/tinyLM`이다. python alias 부재로 시작하지 못한 최초 시도와 python3에서 성공한26개/보강28개 회귀를 구분한다. 다른 Python 버전·프로젝트 전체 static/smoke·실제 HTTP·교사/학생 모델·GPU·설치·다운로드·Git·삭제·추가 agent는 실행하지 않았다. 이번 수정은 `impact-analysis`의 소유권 분리와 순수 helper 선택에 따라 기존 controller/평가/학습 경로의 상태를 바꾸지 않았다.

**남은 총괄 소유 검증:** 새 두 파일을 전체 읽고 같은 합성 회귀를 재실행한 뒤 실제 native 어휘의 probe ID↔bytes/특수 제외를 확인한다. 정상 target 강제와 probe 조회에서 원 logp/top2 수치동일을 대조하고, V5의 실제 실패 fragment가 사전 K 안에서 ID로 회수되는지 별도로 확인해야 한다. 원 로그/응답 byte 한도·MTP OFF·cache_n0·무절단을 함께 지키며 실패하면 해당 행은 HOLD다. 현재 산출물은 **합성 회귀 통과의 준비 구현**이며 실물 raw-logp 회수 PASS나 ALM 품질 보증이 아니다. 이 담당의 추가 실행/변경은 새 요청 전까지 중단한다.

## 16. 부분 top-K 질량 hard-HOLD 재검토 — 코드 변경 없는 정정·대안 비교

### 16.1 현재 권한과 판정 정정

총괄은 helper341행과 회귀394행을 전체 읽었고 기존 실제 V5의 generation_settings와 응답 형태를 비교했다고 회신했다. 이는 **총괄의 검토 회신**이며 이 담당이 실제 V5 자료나 원 확률을 다시 확인한 것은 아니다. 추가 지시는 연구 문서만 갱신하는 읽기 검토다. helper/회귀를 수정하거나 실행하지 않는다. `impact-analysis`를 다시 읽고 방법 비교에 사용했다. 아래는 새 임계값·수치 보정의 채택이 아니다.

**재검토 결론: 현재 부분 질량의 정확한1/미세 초과를 자동 HOLD로 삼는 검사는, 확인하고 싶은 “원 pre-sampling 확률인가”를 판정하는 데 부적절하다. 원값은 보존하고 질량은 관찰치로만 기록하며, 실제 source/API 설정과 동일-prefix·동일-K의 독립 forcing/probe 수치 parity를 본질적 근거로 삼는 쪽을 권장한다.** 기존 §15.3은 false HOLD 가능성을 이미 밝혔지만 실제 구현은 이 가능성을 자동 차단 정책으로 채택했다. 그 정책을 안전성 증명처럼 취급한 것은 과도했고, 이 절에서 권고를 명시적으로 정정한다. **현재 helper 코드는 아직 기존 hard-HOLD 그대로다.**

현재 [helper의 질량 분기](/home/uranus/tinyLM/scripts/p106b_alm_utf8_probability.py:309)는 top-K의 exp(logp)를 합하고, top-K 밖의 chosen probe 질량까지 더한 뒤1 초과 또는 부분 어휘의1 포화를 거부한다. [해당 합성 회귀](/home/uranus/tinyLM/scripts/test_p106b_alm_utf8_probability.py:302)는 이 정책이 실행되는지만 확인한다. 그 회귀의 통과는 **이 정책이 정상 FP32 서버 출력과 양립한다는 검증이 아니다.** 이전28개 합성 통과는 구현 당시 범위의 역사로 보존한다.

### 16.2 정상 원 softmax라도 질량이1 이상으로 관측되는 이유

고정 commit의 [server-common.cpp:1444~1488](https://github.com/ggml-org/llama.cpp/blob/2e7c58c54/tools/server/server-common.cpp#L1444)를 재열람했다. 원 logits에서 최대를 뺀 expf, float 누적합, float 나눗셈을 수행한다. [server-task.cpp:251~291](https://github.com/ggml-org/llama.cpp/blob/2e7c58c54/tools/server/server-task.cpp#L251)는 그 float 확률에서 log를 취해 float logprob로 내보낸다. helper는 전달받은 logprob를 Python exp/fsum으로 다시 처리한다. 이는 정확 실수 확률을 같은 연산으로 역변환한 값이 아니다.

수학적으로 정확한 부분 확률의 합이1 이하라는 사실과, **FP32 softmax → FP32 log → JSON → Python exp/합**의 산출물이 정확히 그 부등식을 만족한다는 주장은 다르다. source에 근거한 분석은 다음과 같다. 별도 수치 실험은 하지 않았다.

- 원 최대 logit의 exp 항은1이다. 그 뒤 작은 양수 tail 항들이 float 누적합의 반올림 단위보다 작으면 일부가 분모에 반영되지 않을 수 있다. 원 tail이 존재해도 반환 최대 확률이1로 반올림되는 경로가 있다.
- 반환 최대 확률이1이면 그 logprob는0이다. 이를 다시 exp하면1이고 다른 정상 finite logprob의 exp는 비음수가 된다. 이 조건의 top-K 합은 Python 반올림 뒤에도1 또는 초과가 될 수 있어 **현재 분기는 정상 원 경로에서도 HOLD**한다. top-K 밖 probe를 더하는 현재 known_mass 검사 역시 이 모호성을 해소하지 않는다.
- 최대 확률이 정확히1이 아니어도 분모의 누적, 개별 나눗셈, log 반올림, 재exp의 오차 방향은 같을 필요가 없다. 빠진 tail 질량이 작으면 그 오차와 구별되지 않는다. fsum은 helper의 덧셈 오차를 줄일 뿐 **이미 반올림된 원 확률/logp를 복구하지 않는다.**
- 따라서 질량이1 또는 조금 초과했다는 관측은 재정규화의 증거가 아니다. 반대로 질량이1 미만이라는 관측도 pre-sampling/full-vocab 정규화의 증명이 아니다. 잘못된 재정규화 값이 반올림으로1 미만이 되거나 다른 잘못된 분모를 쓴 경우도 이 관측 하나로 배제할 수 없다.

특히 **매우 집중된 원 분포**에서 현재 조건이 오탐을 일으킬 가능성은 단순한 비정상 입력 가정이 아니라 실제 소스의 정밀도 경로에서 나온다. 다만 이번에 실제 응답·prefix를 읽지 않았으므로 “자주 발생했다”, 발생 비율, V5의 어느 행이 해당한다는 실증 수치는 없다. 여기서는 가능 경로와 판정의 비타당성을 확인한 것이며 빈도를 추정하지 않는다.

### 16.3 질량 처리의 세 안과 기존 회수 경로 비교

아래 세 안은 **기존 ASCII probe 회수 경로를 유지한 상태**의 질량 처리 비교다. 서버·scorer 교체를 새로 승인하거나 선택한 것이 아니다.

| 안 | 내용 | 장점 | 단점·실패 위험 | 영향·비용 |
|---|---|---|---|---|
| 1. 현재 exact hard-HOLD 유지 | 부분 합의1 또는 초과를 자동 거부 | 구현/회귀 변경 없음, 명확한 현재 동작 | 정상 FP32 포화/반올림을 오류로 거부하며 질량1 미만의 잘못된 정규화도 놓침. 행/상황에 따른 선택적 중단을 유발 | 코드 비용0, 실제 cache 중단/재시도 비용과 표본 선택 위험 |
| 2. 오차대역을 정한 hard-HOLD |1 주변 일부를 허용하고 그 밖은 거부 | 미세 오탐을 줄일 가능성 | 새 수치 정책의 근거·정밀도/어휘/K 의존성 검증이 필요. 대역 안/밖이 원 확률 여부를 증명하지 않음 | 중간 검증 비용, 이번 담당은 임계값을 정하거나 채택하지 않음 |
| 3. 질량 관찰 전용 + 원 provenance/parity 검증 | 합·known_mass·K를 진단으로 기록하되 질량만으로 수용/거부하지 않음. 원 logp/top2는 불변 | 관찰과 유효성 근거를 분리하고 정상 FP32 반올림으로 인한 임의 중단을 피함 | flags만으로 내부 수치를 보증할 수 없으므로 source/build identity와 별도 실제 canary가 반드시 필요. 질량 수치는 원인 진단용으로 유지 | 작은 국소 구현/회귀 변경이 후속으로 필요. 현재 요청에서는 구현하지 않음 |

**권장: 3안.** 검사하려는 계약에 직접 대응하는 근거는 source의 원 logits 경로, 실제 raw/backend sampling 설정, cold/no-truncation·native ID/step 대응, 동일 조건의 독립 확률 비교다. 질량으로부터 무리하게 새로운 유효성 이진판정을 만들지 않고 원값을 보존하는 편이 타당하다. 질량을1로 나누거나 logp에 공통 보정을 더해 합을 맞추는 것은 이 권고가 아니다. 독자 tolerance를 추가하는2안도 채택하지 않는다.

§14의 원래 세 회수 경로와도 구분한다. **A(기존 서버 ASCII probe)**는 위3안의 관찰 원칙을 적용할 조건부 최소 경로로 유지할 수 있다. **B(서버의 step별 확률 보존)**는 UTF-8 누락 구조를 고치지만 동일한 FP32 확률을 내보내면 합1 문제가 저절로 사라지지 않는다. **C(libllama raw-logit scorer)**는 안정 LSE 등 별도 수치 경로를 검증할 여지가 있지만 JSON 유한 logp에서 exp/합을 재구성한 값의 exact 합1을 보증하는 방법은 아니다. 이번 질량 검사 문제만으로 B/C의 더 큰 구현·빌드/ABI·상주·실물 parity 비용을 정당화하지 않는다.

### 16.4 그대로 남겨야 할 검증과 후속 변경 조건

질량 hard-HOLD의 부적절성을 인정해도 **유효성 검사 전체를 끄는 것은 아니다.** actual post_sampling_probs/backend_sampling false, cache_n0, 무절단·생성1, 원 native prefix·probe ID/bytes, 확률 객체1개, K 길이/정수 ID/중복/순위·선택 probe와 원 target 분리, 양수/비유한/underflow sentinel 거부, target 누락의 MISSING_TARGET는 각각 다른 근거가 있으므로 유지한다. 어떤 guard를 바꿀지는 총괄이 명시하고 실제 코드를 재검토해야 한다.

후속으로3안 구현을 승인한다면 관찰할 값은 원 top-K exp 합, 중복 계산하지 않은 chosen probe 포함 합, 요청/실제 K, probe의 top-K 포함 여부, 원 target rank/origin, 합 계산 방식이다. 이들은 **수정한 확률이 아니라 진단 파생값**이어야 한다. 비정상 질량을 보더라도 원 logp/top2/ID/bytes를 지우거나 clamping·재정규화하지 않으며 원 응답과 provenance를 보존한다. 현재 반환에는 top-K 합만 있고, 실패 분기에서는 반환 자체가 없으므로 이 후속 계약은 아직 구현됐다고 쓰지 않는다.

총괄이 실제 canary를 수행할 때는 **양쪽에 동일 K**를 쓰는 것이 비교를 더 직접적으로 만든다. source는 K에 따라 partial_sort 순서가 달라져 float 분모 누적 순서도 달라질 수 있으므로, 강제 target의 K2와 probe의 K64를 비교한 미세 차이를 곧바로 bias 왜곡으로 해석하지 않는다. 기존 canary의 오차 규칙을 확인하고 필요하면 별도 승인·사전 규칙을 사용하되 이 담당은 새 기준을 골라 주지 않는다. 정상 target forcing 대 probe 및 probe A/B의 동일-prefix 수치 parity는 source/build·native ID 대응과 함께 보며, fragment 실물 회수와 모든 후속 행의 품질을 보증하는 것으로 확대하지 않는다.

후속 회귀에서는 **정상 FP32 집중 분포를 모사한 합1/미세 초과도 원값을 바꾸지 않고 관찰로 남는 경우**, 예전 합성 합1 사례에 대한 자동 판결 제거, 원 top2/target 값의 보존, 잘못된 actual flags·ID·누락에 대한 기존 거부를 분리해 확인해야 한다. 이는 명세일 뿐 fixture/코드 작성·수치 계산·시험 실행은 하지 않았다. **이번 변경은 본 연구 문서 새 절뿐이며 helper/회귀·실데이터·HTTP·모델·GPU·설치·Git·추가 agent는 변경/실행0**이다. 정책 변경의 실제 구현과 root 재검토·재회귀·실물 canary는 후속 승인·담당 범위다.

## 17. supported production8h V3 재고 — 기존 준비·실물 소량·당일 마감의 구분

**요약:** 기존 코드는 새 근거문맥 교사 **생산/STOP/명시 재개까지 구현**되어 있다. 현재 확인한 V3 실물은 **파일럿4후보·신규 train 입력943토큰**이며, V3 본생산 디렉터리는 아직 없다. 완성75M·학생 본교육으로 승격할 수 없다. 본 절은 source와 계획, 지정된 소형 report의 메타데이터/스칼라만 읽은 재고이며 코드·교사·회귀는 실행하지 않았다.

| 확인 대상 | 현재 근거·범위 |
|---|---|
| 계획 정본 | [P106B Stage4fs §1~11](/home/uranus/tinyLM/test_plan/P106B_Bonsai-자동번역-pseudo-SFT-온라인-교사학생-검증.md:7118), 역사 실물 [결과101 §434](/home/uranus/tinyLM/test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md:20784). V1 조회권한 실패·V2 선별 중 상한 지연·V3 제어 수정을 분리 |
| 닫힌 V3 파일럿 | [batch_000000/report.json](/home/uranus/tinyLM/HF/sft_ready/p106b_supported_production8h_v3_s1337_pilot/batch_000000/report.json), 파일15,337B. `PRODUCTION_PAUSED/8`, `ProductionBudgetPause`, accepted4/scanned5, raw/candidate manifest 각각4행. 신규 train x943, 전체118.143891532초. assistant target99는 결과101 §434의 별도 소형 실물 영수증 |
| 양과 품질 | report는 `token_target_ready=false`, `formal_train_ready=false`, `student_training=NOT_RUN`, `semantic_quality=NOT_REVIEWED`. public 기초분을 포함한 train 카운터는 EN15,512,564/KO13,510,555이며 신규 교사량과 다름. 남은 train quota는 KO23,989,445/EN21,987,436; 과제/val 부족분도 남음 |
| 본생산/재개 현재 위치 | `/home/uranus/tinyLM/HF/sft_ready/p106b_supported_production8h_v3_s1337`는 관측 시 부재, 따라서 본생산 report0·STOP 부재. 지금 필요한 진입 구분은 **produce**이며, 존재하는 본생산 없이 resume하면 기존 함수가 거부. 별도 pilot4행을 생산 quota로 자동 재생하지도 않음 |
| 교사와 비용 | 파일럿 report의 `mtp=true`, `speculative={type:draft-mtp,n_max:2}`. 기존 Gemma4-12B Q4_0+draft, context8192/thinking1024/output3072, temp1/top_p.95/top_k64 유지. Qwen ALM의 MTP OFF와 별개다.4개 KO QA의118초나7.98179 x/s는 참고문맥·기동/검산이 섞인 소형 관측으로8h 생산성·75M 완성을 예측하지 않음 |

재사용 지점은 아래와 같이 이미 있다. 새 생산기/STOP/재개/모니터를 다시 구현하라고 제안하지 않는다.

- [supported 생산기](/home/uranus/tinyLM/scripts/diag_p106b_supported_production8h.py:20)의 `visible_source/attach_visible_source`는 완전한 원 public 메시지를 학생 질문의 인용 근거로 붙이고 SHA/원 교사질문 계보를 남긴다. `scope`는 옛 cursor를 이어받되 `replay`의 quota에는 **public 기초 + 해당 새 OUTPUT의 지원문맥 후보만** 넣는다. 옛4473은 자동 가산0이며, V2/V3의 같은4원천을8개로 세지 않는다.
- 같은 파일의 `require_pilot(info)`는 **같은 입력 계약·정상 pause8·최소4·두 manifest·지원문맥 계보**를 요구한다. `batches/replay`는 연속 batch·원 token quota·manifest를 검증하며 report 없는 미완결 batch/다른 계약을 거부한다. 오늘 이 함수를 호출하면 원 candidate/shard를 읽게 되므로 **이 담당은 실행하지 않았고 현재 전체 해시/계보 일치 PASS도 선언하지 않는다.**
- `checkpoint_quota`는 원천 선별 중에도 STOP/cap을 확인하고, `scope`의 group은 교사 호출 전 STOP과 온전한 support의768-token 예약을 확인한다. `execute`의 SIGTERM과 `supported_wall_limit`은 `ProductionBudgetPause`로 닫힌 증분 batch를 남긴다. STOP이 남아 있으면 시작 자체를 거부하며 사용자가 이동하기 전 자동 제거/재개하지 않는다. 강제종료·전원차단 미완결 batch의 무손실 자동 복구는 보장하지 않는다.
- [기존 producer.production](/home/uranus/tinyLM/scripts/diag_p106b_gemma_deficit_production.py:121)은 신규 batch/cursor·소모한 원천에 재시도 예산을 새로 주지 않는 처리·disk8GiB·불변 shard/report를 이미 소유한다. `produce_group`은 **턴별 최초 포함3시도**이며 multiturn은 최대3턴이므로 원천 전체가 무조건3요청이라는 뜻은 아니다. [MTP on_scope](/home/uranus/tinyLM/scripts/diag_p106b_gemma_mtp_resume.py:113)가 `GemmaSession(False)` 호출을 실제 ON session으로 바꾸므로 호출문 하나만 보고 OFF라고 판단하면 안 된다. [PersistentMemory/stream_session_scope](/home/uranus/tinyLM/scripts/p106b_memory_stream.py:80)와 기존 RetryingMemoryReader도 재사용 중이다.

**현재17시 창의 핵심 문제는 미구현이 아니라 기한·자원·선결이다.** [produce SH](/home/uranus/tinyLM/run_P106B_Stage4fsWb_supported_teacher8h.sh:1)와 [resume SH](/home/uranus/tinyLM/run_P106B_Stage4fsWc_supported_teacher_resume8h.sh:1)는 둘 다 `--max-wall-sec 28800`을 전달하며 **절대 deadline 인자를 주지 않는다.** 한 번8h는 당일17시 승인과 같지 않아 그대로 시작해서는 안 된다. 기존 `limit_window/execute`에는 `--deadline-utc`·60초 여유·무거운 선결검산 뒤 잔량 재계산이 이미 있다. 오늘17시KST의 절대시각은 `2026-10-23T08:00:00Z`이고, 이를 실제 호출에서 적용하는 운영 결정은 총괄 소유다. 이 담당은 런처를 바꾸거나 실행 명령을 발행하지 않는다.

[idle_before_gpu](/home/uranus/tinyLM/scripts/p106b_gate_runtime.py:246)는 compute app0·free≥14,000MiB를 요구한다. 현재 총괄이 고지한 P078/대기 중 ALM·BabyLM과 동시 상주하도록 만든 경로가 아니다. 선결 replay/원천·교사 asset hash 확인, 여유 disk, 단독 교사 자원, 마감 내 잔량이 먼저이며 과거 파일럿의 VRAM 표본은 현재 가용량/OOM 안전 증거가 아니다. source-only 검토에서 NVML·모델/asset hash·실제 GPU 상태를 조회하지 않았다.

**아직 하지 않은 후속:** V3 본생산, 수량/과제/언어/val quota 충족, 지원문맥 자료 의미검수, 완성75M 최종화, wire/학생 본교육·평가. [기존 control.finalize/learner/evaluate](/home/uranus/tinyLM/scripts/p106b_gemma_deficit.py:128)는 이미 있지만 **supported V3 CLI는 pilot/produce/resume만 노출**한다. 옛 학습 런처의 CORPUS/WIRE/STUDENT namespace를 새 지원문맥 자료에 그대로 대응시켰다고 간주하지 않는다. 완성 corpus/정확 namespace 연결과 wire 선결이 닫힌 뒤 기존 함수를 재사용할 문제이지 지금75M가 준비됐다는 뜻이 아니다.

읽기 경계: report의 scalar/카운터/manifest 총량만 선택 투영했고 raw/candidate·원 QA·CP tensor·TinyDataset은 열지 않았다. 다만 결과문서 키워드 검색에서 그 문서가 인용한 예시질문1줄이 함께 노출되었으며 내용 분석·재인용은 하지 않았다. `require_pilot`/producer/회귀/torch import·HTTP·교사/학생/GPU·설치·다운로드·Git·새 agent·공용 코드 수정은0이고, 이번에는 이 연구 문서만 추가했다.

## 18. check_smoke_diag의 Codex 경로·freshness 진단 — 공용 코드 미수정

### 18.1 확인한 사실과 현재 오탐 경로

총괄이 보고한 전체 정적76개 중 해당 실패에 대해 `impact-analysis`를 읽고 source·기존 freshness/정규화 영수증 회귀·Codex 실행 경로를 읽기 검토했다. **사용자 기본 스모크의 팔/TSV/학습 인자/판정은 바꾸지 않는 것이 전제**다. 이번에는 코드/회귀/실제 스모크를 실행하거나 수정하지 않았고 본 문서만 추가한다.

실제21일 원 로그 [20261021035623_smoke_codex_oct21_final_approved_v1_2503365.txt](/home/uranus/tinyLM/smoketest_logs/20261021035623_smoke_codex_oct21_final_approved_v1_2503365.txt:383)에서 아래 **명령/정적 검사 블록만** 확인했다.

- 실제 child는 `python -I -B .agents/skills/session-handoff/scripts/check_handoff_codex.py`다. `CHECK handoff/202610191811_HANDOFF.md`, `PASS static structure and local links`, `SUMMARY files=1 errors=0`를 인쇄했다. legacy checker가 빠진 것이 아니라 승인된 **다른 실행 정체성**이다. raw에 legacy 이름을 만들어 넣으면 안 된다.
- 같은 원 로그에 `scripts/codex_smoke.py --mode contract --session-id oct21_final_approved_v1`와 해당 원 로그를 가리키는 summary 명령이 있다. [정규화 영수증](/home/uranus/tinyLM/test_result/evidence/codex_smoke/oct21_final_approved_v1/smoke_report.json)은 normalized schema·complete true·returncode0·summary COMPLETE/0·명시 두 substitution을 기록했다. 이는 과거 기록이며 현재 동적 스모크 완료는 아니다.
- 소스/기존 raw의 작은 해시만 읽어 대조했다. **canonical BAT·codex_smoke.py·smoke_execution_contract.py·Codex checker·원 log**의 현재 SHA는 각각 영수증에 기록된 동일 파일 SHA와 일치한다. CP/원 cache/모델 tensor를 해시하지 않았다. 영수증 before/after source-pin 집합은80개이며 `tinylm/train/alm.py`는 기록에 없고 현재 소스에는 존재한다. 따라서 “현재 전체 execution_source_pins와 동등” 조건은 이미 성립하지 않는다. 다른 모든 pin의 전수 동등성까지 검사한 것은 아니다.

핵심 source 흐름은 다음과 같다.

| 위치 | 현재 역할·문제 |
|---|---|
| [check_smoke_diag.log_records/log_blocks](/home/uranus/tinyLM/scripts/check_smoke_diag.py:119) | 실제 닫힌 cmd/exit를 보존해 읽고 basename view에는 `check_handoff_codex.py`로 남김. 이 사실 자체는 정상 |
| [authorized_aliases](/home/uranus/tinyLM/scripts/check_smoke_diag.py:146) | 승인된 versioned receipt로만 두 대체 팔을 매핑. **이미 Codex 지원이 있으므로 새 basename whitelist를 덧붙이는 문제가 아님** |
| [validate_modern_adaptation](/home/uranus/tinyLM/scripts/smoke_execution_contract.py:284) | 원 log/receipt·정확 argv/order/전체 실행 영수증과 함께 현재 source pins의 완전 일치까지 요구. 모델 소스의 추가/변경도 strict 동등성 실패가 됨 |
| [main의 로그 분기](/home/uranus/tinyLM/scripts/check_smoke_diag.py:380) | alias 오류를 먼저 전역 fails에 넣음. aliases가 비면 TSV의 legacy 팔에 대응할 블록도 없어 missing legacy라는 후속 증상이 발생. 이후 stale/input 판별까지 도달해 해결할 수 없는 경로. mtime watched 목록은 전체 source-pin 집합과 별개여서 ALM 소스 추가를 그 자체로 포착하지도 않음 |
| [handoff_input_stale](/home/uranus/tinyLM/scripts/check_smoke_diag.py:256) | 기존 문서 갱신은 handoff 팔만 NOT_RUN/경고로 내림. 그러나 실제 Codex body를 해석하기 전에 alias가 사라지면 이 guard를 적용할 body가 없음 |

따라서 이번 것은 **단순히 log_blocks의 정규식을 바꿀 문제나 legacy 팔 미실행 결함으로만 보기 어렵다.** 같은 핵심 runner/checker·같은 원 log가 보존돼 있어도, 새 모델 소스 때문에 strict current-source validation이 실패하면서 **과거 실행 정체성/진위와 현재 freshness가 한 실패로 합쳐지는 구조**가 있다. 이를 현재 실패의 확정 가능한 source-level 원인으로 확인했다. 실제 gate를 재실행해 전체 stderr/첫 실패 지점을 다시 관찰한 것은 아니다.

### 18.2 Codex 전용 실행과 기본 경로를 보존할 최소 수정 지점

현재 [codex_smoke.build_plan](/home/uranus/tinyLM/scripts/codex_smoke.py:194) → [adapt_actions](/home/uranus/tinyLM/scripts/smoke_execution_contract.py:82)는 **문서 검사만 독립 Codex checker**, 계측 경로만 격리 log 경로로 치환하며 원 run100m 인자는 그대로 둔다. [contract](/home/uranus/tinyLM/scripts/codex_smoke.py:623)는 원 check_smoke의 LOGS만 격리 위치로 바꿔 동일 main을 부른다. [check_static_all의 codex-safe](/home/uranus/tinyLM/scripts/check_static_all.py:58)는 legacy handoff를 NOT_RUN으로 기록하고 독립 checker를 별도 실행한다. 이 경계와 사용자 `tool_smoke.bat`/TSV를 수정할 이유는 없다.

| 안 | 내용 | 장점 | 문제·영향·비용 |
|---|---|---|---|
| A. basename alias/legacy 항목 무조건 생략 | Codex basename이 있으면 legacy 팔 충족으로 처리 | 코드량은 작음 | 미승인 경로·위조/없는 영수증·다른 argv를 숨김. 기존 fail-closed 회귀를 깨므로 기각 |
| B. 검증된 실행 정체성과 freshness 분리 | 엄격한 raw/receipt/명령 검증을 재사용하되 source drift만 별도 **historical/NOT_RUN** 상태로 반환하고 해당 실제 Codex 팔을 해석 | 현재 default 항목/판정과 raw 정체성을 보존하면서 오탐 원인을 직접 분리 | 공통 validator의 작은 내부 분리와 main 연결, CPU 회귀 추가 필요. 권장 |
| C. 새 Codex 전용 TSV/검사기/profile 복제 | 기본 checker 옆에 별도 표/도구를 만듦 | 사용자 기본 경로는 그대로 둘 수 있음 | 동일 규칙/영수증/freshness를 이중 유지하며 원인 분리는 여전히 필요. 이번 국소 문제에는 과함 |

**권장 B의 최소 안전한 경계:**

1. `scripts/smoke_execution_contract.py`에서 normalized receipt의 **증거 검증**과 **현재 전체 source-pin 일치**를 내부적으로 분리한다. raw hash/크기/경로, canonical BAT·runner·Codex checker의 검산 가능한 실행 정체성, before=after로 기록된 완전 pin 집합, substitution/실제 cmd·순서·닫힌 exit/summary/프로세스 안전 영수증 검증은 계속 해야 한다. source drift를 먼저 만났다고 이후의 위조/누락 검증을 건너뛰어서는 안 된다.
2. 기존 `validate_modern_adaptation` 및 `authorized_aliases`의 **strict 기본 계약/tuple API는 유지**하고, 진단용 main에만 `현재 검증됨 / 기록된 과거 실행이며 현재 미실행 / 증거 불일치`를 구분하는 얇은 내부 결과를 제공하는 방식이 작고 안전하다. ValueError 문자열에 “pins”가 있다는 이유로 모든 오류를 경고로 바꾸지 않는다. 핵심 runner/BAT/checker 자체가 바뀌어 과거 topology를 현재 코드로 검산할 수 없는 경우도 별도 미확인/오류로 남기고 임의 historical PASS를 만들지 않는다.
3. `scripts/check_smoke_diag.py`의 `main`에서 이 **검증된 실제 팔 정체성**으로 body/items를 먼저 선택한다. Codex 문서 팔에는 CODEX_ITEMS와 그 body를 사용한 뒤 기존 handoff 입력 freshness를 적용한다. 현재 source drift/새 handoff라면 원 exit를 보존하고 `[NOT_RUN]`을 남긴다. “현재 legacy 팔이 돌았다”거나 “현재 full smoke가 PASS”라고 출력하지 않는다.
4. canonical/비Codex 로그는 기존 no-alias 동작을 유지한다. 다른 현재 팔의 missing marker/nonzero exit, raw/영수증 위조·누락은 여전히 실패해야 한다. handoff 문서가 새로 생겼다는 이유로 다른 현재 팔까지 일괄 경고로 내리면 안 된다. stale과 invalid의 증거 범위도 메시지에 분리한다.

이 방식은 기존 validator를 약화해 현재 동등성이 틀린 로그를 current PASS로 만드는 것이 아니라 **과거 실행의 실제 정체성을 잃지 않은 채 현재 동적 검증은 미실행으로 남기는 수리**다. static checker의 계약 검토가 exit0/경고로 닫혀도 모델 스모크는 NOT_RUN이라는 기존 의미를 유지한다. 새 GPU 스모크는 현재 상태 검증을 위해 후속으로 필요하지만, 과거 로그의 별도 정체성을 알아보는 source-only 검사를 위해 지금 GPU를 먼저 요구할 이유는 없다.

구현 시 한 가지 자기참조 함정도 있다. **공통 validator 파일을 수정하면 그 파일 자체의 source pin도 바뀐다.** 따라서 수정 뒤21일 영수증이 현재 전체 pin과 같아졌다고 처리해서는 안 된다. historical reader가 지원하는 기존 normalized schema/검증자 버전과 실행 topology의 검산 가능성을 명시해야 한다. BAT·runner·checker/파서의 과거 동작을 재구성할 근거가 사라진 경우까지 자동 허용하는 변경은 권장하지 않는다. 이 버전 호환 경계를 추가하기 싫다면 strict 공통 API는 그대로 두고 진단 전용 reader seam을 check_smoke_diag 쪽에 한정하는 대안도 있으나, 임의 예외나 중복 validator를 만들지 않는 범위에서 총괄이 후속 구현 범위를 확정해야 한다.

### 18.3 회귀 추가안과 보존해야 할 기존 실패

기존 [test_smoke_diag_freshness.Tests](/home/uranus/tinyLM/scripts/test_smoke_diag_freshness.py:16)는 새 문서/같은 문서 수정/identity 없음/다른 현재 팔 실패를 검사한다. [NormalizedAliasIntegration](/home/uranus/tinyLM/scripts/test_smoke_diag_freshness.py:269)과 [ModernReceiptTests](/home/uranus/tinyLM/scripts/test_smoke_execution_contract.py:452)는 정상 두 alias, 누락/위조/순서/argv/프로세스 영수증을 엄격히 검사하지만 **정상 Codex 실제 body를 가진 과거 로그 + 모델 source drift + main의 freshness** 조합을 직접 닫는 회귀가 없다. `test_generic_source_driver_helper_or_raw_byte_change_is_rejected` 같은 strict 현재동등성 검사는 그대로 유지해야 한다.

| 합성 fixture | 필요한 판정 |
|---|---|
| canonical legacy 로그, receipt 없음 | 기존 default 결과/legacy items/집합 불변, 새 alias 없음 |
| 정상 normalized receipt·Codex 실제 block, 현재 source/문서 동일 | 검증된 Codex items로 실제 팔 인식. legacy-only marker를 강요하지 않음 |
| 같은 raw/core 정체성, pin before=after 보존, 모델 소스 추가/변경 | strict API는 현재동등성 실패를 유지. 진단 main은 기록된 Codex 실행 body를 잃지 않고 **현재 NOT_RUN**으로 구분 |
| 새 handoff 또는 같은 handoff의 사후 수정 | 실제 Codex body의 원 exit/파일명을 보존하고 문서 팔만 NOT_RUN. body identity가 없으면 자동 freshness 면책하지 않음 |
| 위 source/document drift와 동시에 다른 현재 팔 exit1/marker 누락 | 다른 팔의 현재 실패는 그대로 검출. 전역 blanket warning 금지 |
| source drift와 동시에 raw/footer 누락·중복·실행 순서/ID/argv 위조 | historical 분기로 빠져 통과하지 않고 실패. 정상 raw hash를 새로 적어도 잘못된 실제 명령은 거부 |
| Codex basename만 흉내 낸 다른 경로·-I/-B/정확 checker 명령 변형 | 승인된 대체로 인식하지 않음. 단순 basename/부분문자열 whitelist 금지 |
| receipt 없음/불완전 pin 집합/기록 before≠after/실패 summary/핵심 source 변경 | 기존 invalid/현재동등성 실패를 유지; 새 historical 경고가 은폐하지 않음 |

source drift가 있다는 이유만으로 **현재 실패를 과거로 속이는 반례**와, marker/mtime가 같은데 source 내용만 달라진 반례도 넣는 편이 맞다. 원 로그는 immutable fixture로 두고 raw 블록을 실제 legacy 이름으로 재작성하지 않는다. 회귀 작성·실행은 후속 승인 범위이며 이 담당은 이번에 코드/fixture를 만들거나 어느 회귀도 실행하지 않았다.

**범위/한계:** `.claude/**`, `CLAUDE.md`, 루트00~08은 열거나 호출하지 않았다. 공유 코드의 레거시 경로 문자열은 과거 참조 데이터로만 봤다. 원21일 로그에서 명령/문서 검사/summary 정체성만 읽고 소형 정규화 report를 투영했으며 CP/데이터/모델/GPU·전체 정적·실제 스모크·Git·코드 수정은0이다. 이 문서가 현재76개 종합 통과나 새 Codex 스모크 PASS를 증명하지 않는다.

## 19. 원지시별 이종 증류 누락 감사 — ALM 신호 성공과 방법별 완료를 구분

### 19.1 감사 범위와 상태의 출처

이번 추가 검토는 [첨부 지시서 §3.3~3.5](/home/uranus/tinyLM/ai_dev_tool/temp_20261023_작업지시서_참고용.md:205)의 요청을 이 문서 §5·§9~10·§12·§14~16 및 현재 소스와 대조한 것이다. 첨부1071행 전체를 다시 읽었으나 그 안의 문헌 요약을 검증된 사실로 승격하지 않았다. 방법/우선순위 비교에는 `impact-analysis`의 3안 비교를 적용했다. 쓰기는 이 절뿐이며 계획서·원장·방법론·공용 코드는 갱신하지 않는다.

**총괄 전달 상태:** ALM V7 원17행 canary는 실물 성공, 전체1024 cache와 학생 대조는 대기다. BabyLM 실제4개 cost는 성공, TinyLM3개 full은 진행, Falcon full은1h 상한에 대해5013초 외삽이라 보류다. 이 담당은 이번에 실물 report/raw·QA·CP를 열거나 해당 결과를 재실행하지 않았다. 따라서 이 상태는 총괄 관측의 인용이며, 아래 소스 확인과 증거 출처가 다르다. BabyLM 비용 측정/평가 진행은 어느 증류법의 학습 완료나 효과 증명이 아니다.

### 19.2 원지시별 남은 상태표

| 원지시 | 현재 확인한 범위 | 아직 하지 않은 것·보류 사유 | 정확한 보고 상태 |
|---|---|---|---|
| §3.3 같은 답변의 CE/SFT-only 대조 | [학생 제어기](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py:104)는 같은1024행·초기 core·RNG·optimizer·4epoch/32update의 CE/ALM 두 팔을 설계했다 | 실제 두 팔 학습·사후 평가 대기. 현재 자료는 **새 교사 생성 답변이 아니라 기존 원문 정답**에 대한 TF 지도이므로 새 교사답 SFT를 수행했다고 표현하지 않음 | 구현 있음, 학생 대조 `NOT_RUN` |
| §3.3 ALM + 현재 삼진 학습 | [ALM core](/home/uranus/tinyLM/tinylm/train/alm.py:16), byte 정렬, native no-thinking TF/probe가 있음. 총괄이 V7 원17 성공을 전달 | 전체1024 cache·TRAIN 교정·CE 대조·학습 효과 대기. **현재 학생 제어기 runtime은 `weight_route(model,"float")`를 명시**하므로 예정된 소형 대조도 고정 삼진 학습 완료로 세면 안 됨 | 확률/정렬 canary의 부분 실물 증거. ALM 학습·삼진 결합·품질 효과 미완료 |
| §3.3 가능하면 ALM + GSQ 이산 최적화, §3.4 | §5.5에서 GSQ v2와 공식 quantizer의 soft train/hard 추출·RNG 재생·추가 logits 비용을 검토 | 같은 CE/KD·초기 codes/scales의 STE 대조, hard 삼진 forward/eval, tied embedding/head 포함 검증 미착수. 정상 답변 부재가 원리적 선결이라는 뜻은 아님 | 조건부 후속 요청, 문헌 검토만. 구현/실물 `NOT_RUN` |
| §3.3 ACTD 최소 구현·단기 학습 | §5.3의 원문식·mapping/collision 위험, 공식 repo의 미공개 상태 확인 | ACTD 손실·anchor mapping·전 위치 top-K 캐시·학생 gradient/parity·짧은 학습 모두 미실행 | 논문 기반 구현 가능성 검토만. ACTD 완료 아님 |
| §3.3 DWA-KD/DSKDv2 | 둘을 다른 방법으로 구분했고 필요한 hidden/head/정렬 신호를 확인. DSKDv2 실제 공식 코드 존재 | white-box 교사 신호·양공간 projector/미분 head 접합 없음. 현 GGUF reference/K64로 충족하지 못함 | 방법별 구현/실물 `NOT_RUN`; 현재 인터페이스 신호 부족 |
| §3.3 DVLM | §5.4에서 PTS/HPA·새 head 학습·OPD 두 단계를 확인 | 교사 입력/attention 변경과 학생어휘 head 학습, 후속 OPD 전부 없음 | 문헌 검토만. 구현/실물 `NOT_RUN`; ALM 완료와 별개 |
| §3.5 신호·캐시·총비용 | 원 reference logp의 출처·shift·byte 정렬·특수토큰 제외, 선택 probe와 reference 분리, raw/top-K 보존 경로 있음 | 전체 동결1024의 닫힌 batch64개·완전 manifest·신호 coverage·총 teacher 시간/학생 시간·효과를 별도로 회수해야 함 | 신호 canary 성공을 전체 cache/학습 완료로 올리지 않음 |

로컬 구현 존재 확인은 `tinylm/train`과 현재 ALM 제어기/확률 helper의 내용 검색, `tinylm`·`scripts`·`docs/research` 안의 관련 방법명 파일 검색으로 한정했다. 이 범위에서 ACTD/DSKDv2/DWA-KD/DVLM 학습 구현은 확인하지 못했으며, 보호 데이터나 저장소 전체를 뒤져 부재를 증명한 것은 아니다. 방법별 실제 실행 상태는 총괄의 현재 전달 범위와 대조했다.

삼진 범위의 위 지적은 이번 source audit에서 재확인한 **실제 예정 경로 차이**다. [runtime](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py:586)과 [weight_route의 float 정의](/home/uranus/tinyLM/scripts/p106b_weight_route.py:1)는 latent FP32 가중치/identity gradient를 명시한다. `set_anneal(1.)` 호출이나 마지막 `freeze_quant()`라는 이름만으로 이 float context를 hard 삼진으로 바꿨다고 판단하지 않는다. float 소형 대조는 독립 진단으로 유효할 수 있지만 원지시의 삼진 결합을 대신하지 않으며, 새 삼진 팔 구현·채택은 이 검토의 범위 밖이다.

원지시 §3.3의 X-Token/BLD는 기존 방법이 막히거나 정렬 병목이 확인됐을 때의 대안, BPM/ESCD/CAST/BSD는 정상 학생 rollout 이후의 후속 후보다. 이들을 오늘 필수 완료 방법으로 새로 늘리지 않으며, 반대로 실험했다고 보고하지도 않는다. §3.6의 final holdout/usable-response 판정 역시17행 TF 확률 검증이나 TRAIN 손실로 대체되지 않는다.

### 19.3 공식 원문·구현의 정확한 공개 상태

논문은 앞서 읽은 버전/절을 재사용한다. 이번 웹 재확인은 **공개 구현 여부·실제 파일명·K/온도**가 불확실했던 부분에 한정했다. 아래 `main`은 가변 branch 열람이며 commit pin·로컬 설치·실행 재현을 뜻하지 않는다. 논문 전문/모든 코드의 새 완독을 주장하지 않는다.

| 방법 | 실제 근거 URL·버전·읽은 범위 | 공개 구현에 대해 확인한 사실 | 필요한 교사 신호와 현재 결론 |
|---|---|---|---|
| ALM | [2503.20083v4 §3/AppE/I](https://arxiv.org/html/2503.20083v4), GradMag는 §3.3/AppA.4. [tokenkit 공식 repo](https://github.com/bminixhofer/tokenkit), [PyTorch guide](https://github.com/bminixhofer/tokenkit/blob/main/docs/pytorch_alm_from_scratch.ipynb), §5.6에서 읽은 byteify/align/losses, 모두 당시 main | **공식 코드·guide 존재 확인.** JAX 주 구현과 PyTorch guide를 구분. 우리 native ID 보존 helper는 tokenkit tokenizer 변환을 그대로 호출한 것이 아님 | 동일 답변 byte chunk의 양쪽 TF target logp면 no-hidden/no-debias core 가능. raw K64 전체 분포는 core의 필수 신호가 아님 |
| ACTD | [2608.29662v1 §3.1~3.2/AppD.2/Table4](https://arxiv.org/html/2608.29662v1), [공식 repo main](https://github.com/hyhy892/ACTD) | 이번에도 main 파일 목록은 README뿐이고 공개 예정 문구. **공식 repo 존재와 실행 구현 공개를 혼동하면 안 됨.** 논문의 DistillKit 수정 사용은 ACTD 수정본 공개의 증거가 아님 | TF top-k ID/logp와 native piece, first-subtoken mapping, 위치 대응, 학생 full-normalizer anchor 확률 필요. K64는 조건부 최소형 자료가 될 수 있으나 현 ALM cache가 전 위치에 이를 갖췄다는 뜻은 아님 |
| DSKDv2 | [2504.11426v1 §III-A/B](https://arxiv.org/html/2504.11426v1), [공식 repo main](https://github.com/songmzhang/DSKDv2), [실제 ETA criterion](https://github.com/songmzhang/DSKDv2/blob/main/code/criterions/dual_space_kd_v2_with_exact_token_alignment.py), [distiller](https://github.com/songmzhang/DSKDv2/blob/main/code/distiller.py) | **실제 공식 실행 소스 존재.** 이번에는 `DualSpaceKDV2WithETA.forward/compute_dual_space_kd_loss_with_eta`, `Distiller.projector_init` 등을 직접 확인. 실행 호환/정확성을 검증한 것은 아님 | 양쪽 최종 hidden, 양쪽 native head, projector와 teacher-space input gradient 필요. reference logp/K64만으로 불가능 |
| DWA-KD | [2602.21669v1 §3/AppD.2](https://arxiv.org/html/2602.21669v1), §5.4의 읽은 범위 재사용 | 확인한 공식 원문에서 저자 귀속 실행 repo URL을 확정하지 못함. arXiv HTML 오류신고용 GitHub 링크는 방법 코드가 아님. **공식 구현 없음의 전수 증명도 아님** | 양공간 projection/분포, embedding·최종 hidden, attention-informed Soft-DTW 신호 필요. 단일 reference나 top-K entropy proxy는 원형 아님 |
| DVLM | [2609.33816v1 §3/AppA.4/A.6 및 Reproducibility statement](https://arxiv.org/html/2609.33816v1) | 원문은 심사기간 anonymous repo/보충자료, 이후 공개 예정이라고 설명. 이 담당이 접근 가능한 공식 실행 repo/commit을 확정하지 못함. 기존 GOLD/TRL 공개가 DVLM 수정본 공개를 뜻하지 않음 | PTS+HPA 아래 hidden을 얻고 학생어휘 teacher head를 학습, 이후 학생 rollout OPD. 기존 causal GGUF TF/K64로 대체 불가 |

DSKD와 DSKDv2, DWA-KD를 같은 이름으로 합치지 않는다. [기존 DSKD 공식 repo](https://github.com/songmzhang/DSKD)는 원지시 [B4], DSKDv2는 [B5]이며, 그 코드가 있다는 사실로 DWA-KD의 Soft-DTW/weighting 구현까지 공개됐다고 말할 수 없다. DSKDv2 README가 안내하는 축약 파일명 `dual_space_kd_v2_with_eta.py`의 raw URL은 이번 조회에서404였고, [실제 criterion registry](https://github.com/songmzhang/DSKDv2/blob/main/code/criterions/__init__.py)가 가리키는 파일명은 `dual_space_kd_v2_with_exact_token_alignment.py`다. README만 보고 import 경로를 만들어 내면 안 되는 구체 사례다.

### 19.4 raw reference/K64로 할 수 있는 것과 없는 것

**현재 ALM 캐시는 모든 target의 top64 cache가 아니다.** [force_target](/home/uranus/tinyLM/scripts/diag_p106b_alm_cache.py:800)는 정상 UTF-8 target에 `build_direct_payload`를 기본 호출하며 [기본 n_probs는2](/home/uranus/tinyLM/scripts/p106b_alm_utf8_probability.py:187)다. fragment의 [probe_target](/home/uranus/tinyLM/scripts/diag_p106b_alm_cache.py:853)은 사전 K64/512/2048을 순차 시도하지만, 학습용 score에는 reference와 top2·probe 진단을 축약해 남긴다. 한편 [Recorder.request](/home/uranus/tinyLM/scripts/diag_p106b_alm_cache.py:692)는 성공한 원 reply 전체를 raw에 보존한다. 따라서 **raw에는 그 요청의 실제 K가 남지만 정상 target의 K2가 K64로 늘어나는 것은 아니다.** 이번에는 실제 raw를 열거나 전 위치 K 분포를 계산하지 않았다.

| 질문 | 현 신호로 가능한 범위 | 넘을 수 없는 경계 |
|---|---|---|
| ALM no-hidden/no-debias core | 원 reference 각 ID의 logp를 합해 공통 chunk 확률을 비교. 선택 probe의 확률은 목표에 섞지 않음 | K64 밖 reference 누락을0/추정값으로 채울 수 없음. 닫힌 전체 cache/양쪽 byte·mask coverage가 여전히 필요 |
| ACTD 단일 교사·k64 후보 | **같은 prefix의 실제 raw top64 전부**가 있다면 `exp(logp_j−logsumexp(top64 logp))`로 논문식 teacher top64 조건부 분포 구성 가능. τ=1의 원 logp면 원 logits의 공통 상수는 필요 없음 | 현 정상 target의 K2/일부 fragment K64만으로 전 학습 위치의64개 anchor를 복원할 수 없음. 원본 cache의 raw logp를 재정규화해 덮어쓰지 않고 별도 ACTD consumer로 정의해야 함 |
| ACTD 학생 anchor/residual | 학생 anchor logit과 **전체 학생 어휘 LSE**로 p를 구하고 `1−Σ_unique_anchor pS`로 residual 산출 가능 | 학생 anchor만 다시 정규화하면 residual이 사라져 다른 손실이 됨. 현재 ALM per-target NLL만 반환하는 경로에 anchor용 미분 연산은 아직 없음 |
| ALM outcome debias·full-vocab KL·DWA entropy | 일부 알려진 질량의 관측/진단은 가능 | K 밖 경계집합 질량·tail 내부 분포/entropy를 일반적으로 복원할 수 없음. 전체 tail 합 하나를 알아도 내부 entropy는 결정되지 않음 |
| DSKDv2/DWA-KD/DVLM | 현재 source/신호 공백을 정리하는 데만 재사용 | hidden/head geometry, projector input VJP, Soft-DTW의 표현열, HPA 아래 새 student-vocab logits가 raw reference/K64에서 생기지 않음 |

ACTD를 다음으로 구현한다면 §5.3에서 이미 지적한 계약을 먼저 닫아야 한다. **k64는 논문 Table4에 실제 비교된 값이지만 최고값을 보고한 k128 설정과 같지 않고**, 해당 표의 특정 teacher/student 성능은 TinyLM 채택 근거가 아니다. AppD.2의 teacher/student 온도1.0은 이번 재확인 범위다. λres·k·CE 혼합비는 이 검토가 새로 채택하지 않는다.

mapping에서는 `add_special_tokens=False`, BOS/EOS/빈 decode/UTF-8 fragment의 명시 정책, 같은 학생 ID로의 충돌을 먼저 고정한다. 원 byte fragment를 replacement character로 decode한 뒤 first subtoken을 얻으면 native piece 의미가 바뀐다. ALM의 **최단 공동 byte chunk**와 ACTD의 **nearest monotonic character boundary**는 같은 정렬이 아니다. 지금 ALM에서 선택한 teacher 위치만 곧바로 전체 ACTD 위치라고 가정할 수 없다. 충돌의 literal Eq7과 질량합산 dedup 변형도 동치가 아니므로 §5.3/반 문서의 작은 반례를 보존한다. 이런 계약이 미해결인 상태에서 “K64가 있으니 ACTD 구현 완료”라고 보고하지 않는다.

DSKDv2 공식 ETA source도 `output_hidden_states=True`, `teacher_model.lm_head(...)`, 양방향 projected hidden을 실제 사용한다. teacher parameter를 freeze하더라도 student→teacher head의 **입력에 대한 미분**은 남아야 하므로 black-box 점수 조회만으로 재현되지 않는다. TinyLM factorized tied head와 공식 단일 `lm_head.weight` 가정의 접합도 별도다. 이 때문에 기존 ALM helper 재사용과 white-box 방법 구현을 같은 난이도로 볼 수 없다.

### 19.5 남은 비용과17시 창의 우선순위 의견

아래 구현 시간은 **소스 간극에 근거한 작업계획용 거친 인력 추정**이지 실측 runtime·완료 약속이 아니다. 코드 재사용/회귀/캐시 재료 확보를 포함하며, 새로운 의존성·교사 white-box 접근이 필요한 경우 현재 권한에서 즉시 실행할 수 없다. 실제 GPU 시간/메모리/품질 칸은 모두 미측정으로 남긴다.

| 방법 | 현실적으로 추가할 일과 인력 시간의 규모 | 실물 시간·메모리·성능의 현재 상태 |
|---|---|---|
| 현 ALM core | 이미 구현된 prepare→TRAIN 교정→두 팔 cost→32update 두 팔→동일 평가를 재사용. **새 손실 구현 시간이 아니라 cache/실측 비용/입장 선결이 지배**. 새 삼진 대조는 별도 작업 | 1024 cache와 두 팔 결과 미완료. 전체 TF target 수·cold 재검증·모델 시작/종료·raw 저장 시간을 포함해 총괄의 실제 batch 속도로 산정해야 함 |
| ACTD 논문 기반 최소형 | mapping/collision·정렬·anchor 미분 손실·raw reader/캐시 범위 검증·합성 회귀에 **반나절~2작업일** 정도를 계획 여유로 봄. 교사 신호 재취득/학생 학습 시간 별도 | 전 위치 K64가 없으므로 지금 신호만 읽어 학습까지 즉시 닫히지 않음. 구현 source-only 검토로0초 학습 성공을 주장하지 않음 |
| DSKDv2 | differentiable 교사 hidden/head 경로와 projector/ETA/TinyLM head 접합부터 필요. **복수 작업일 규모**, 신호 인터페이스 미확보라 더 정확한 시간 확정 불가 | 현 GGUF endpoint만으로 실행할 수 없음. 논문/공식코드의 메모리를 현재 장치 비용으로 이식하지 않음 |
| DWA-KD | 위 양공간 경로 + representation/attention·Soft-DTW·공식 구현/수식 검산. **DSKDv2 접합 뒤 추가 복수 작업일 규모** | 단일 endpoint weighting 스위치 아님. 논문 Table7 수치는 §5.4의 특정 조건 참고일 뿐 로컬 비용 아님 |
| DVLM | PTS/HPA 교사 경로·새 head 초기화/훈련·student OPD의 독립 두 단계. **복수 작업일 이상**, 새 head 수렴/교사 자원은 미산정 | 기존 GGUF causal 서버를 그대로 쓸 수 없고 논문 H200 자원을 오늘의 시간으로 환산할 근거 없음 |

V7 원17 canary는 [독립 canary namespace](/home/uranus/tinyLM/scripts/diag_p106b_alm_cache.py:45)에 저장하고, 본 cache는16행×64batch의 다른 완료 상태/identity를 요구한다. [execute](/home/uranus/tinyLM/scripts/diag_p106b_alm_cache.py:1420)는 본 cache의 각 닫힌 batch만 재사용한다. **원17을1024에서 자동 공제하거나 과거 V5 일부 cache를 V7 완료량에 가산하지 않는다.** 실제 허용되는 재사용은 총괄의 동일 identity/manifest 검증이 소유한다.

현재 학생 제어기는 [두 cost에 기반한 admission](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py:1048)을 이미 구현했다. `두 팔의 32×실측 update 시간×1.5 + 관측 overhead + 평가 여유3×300초`라는 기존 보수식이며, 마지막 여유는 실측 평가시간이 아니다. 이 식을 다시 구현하거나 그1.5/900초를 이 담당이 새 채택하지 않는다. 특히 [cache HARD_STOP](/home/uranus/tinyLM/scripts/diag_p106b_alm_cache.py:36)와 [학생 DEADLINE](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py:31)은 모두 **16:30KST**이므로 상위17시 허가만 보고 런 내부의 더 이른 입장/정리 마감을 무시하면 안 된다.

| 선택지 | 지금 창에서 배분할 내용 | 장점 | 대가·영향·비용 |
|---|---|---|---|
| A. 기존 ALM/평가의 닫힌 증거 우선 | V7 전체 cache와 기존 소형 두 팔의 선결·비용을 총괄이 판단하고, 진행 중 TinyLM BabyLM 결과를 회수. 미완료 방법별 표를 보존 | 이미 준비한 코드/실물 신호에 집중하고 최소한 한 방법의 효과를 독립 검증할 기회 | ACTD 이후 학습은 후속으로 남음. float/삼진 및17행/1024/학생효과의 구분을 계속 보고해야 함 |
| B. ACTD의 계약 준비까지 추가 | 기존 ALM 진행을 막지 않는 source-only mapping/신호 스키마 감사와 작은 합성 규격만 준비 | 다음 black-box 방법의 실제 공백을 줄임 | 새 구현·신호 취득·학습은 별도 승인/시간 필요. ALM 지연을 감수하며 오늘 완주를 약속할 근거 없음 |
| C. white-box 계열로 즉시 전환 | DSKDv2/DWA-KD/DVLM용 새 교사 접근·head/mask 학습 경로를 시작 | 원지시의 더 많은 방법을 장기적으로 열 수 있음 | 현재 raw 신호로 안 되고 설치/교사 경로/자원·검증 범위가 커짐. 오늘 큐와 마감에 부적합 |

**이번17시 창 권고는 A, 자원과 범위가 겹치지 않을 때만 B의 문서 준비까지다.** C를 현재 GGUF 확률 추출의 옵션 변경으로 취급하지 않는다. Falcon의5013초 외삽은1h 상한을 넘으므로 총괄의 보류를 유지할 근거이며, 다른 방법의 완료 수를 늘리기 위해 상한을 자동 연장하는 근거가 아니다. 총괄의 후속 실물 결과가 오기 전 현재 결론은 **ALM 신호 경로의 부분 성공, ALM 학생 대조 대기, ACTD/DSKDv2/DWA-KD/DVLM의 구현·학습 미완료**다.

**경계/한계:** 이번에는 소스 읽기·필요 최소 공식 웹 확인과 본 문서 추가만 수행했다. source/model/tokenizer import·실제 자료/CP/raw 열람·수치 계산/회귀·HTTP·GPU·설치/다운로드·Git·공용 code 수정·추가 agent는0이다. 기존 §10의 GradMag/고정 weight 설계, BabyLM 절 및 과거 실패는 보존했다. 원리적 신호 충족, 구현 존재, 실물 동작, 품질 효과를 서로 대체하지 않는다.

## 20. Core6의 공통 무절단 부분집합 재감사 — 기존 결과는 보존

### 20.1 결론·권한·원 실행의 정체성

**CPU 재계수 완료:** 네 모델에서 절단된 요청은 모두 같은 `boolq/doc_id=3154`의 보기2개다. 같은 한 문항을 네 모델에서 모두 제외하면 BoolQ는3269문항, 전체는19964문항이며 기존 예측만으로 아래 보조 점수를 얻는다. 원19965문항 결과/report/샤드는 역사 그대로 보존했고 새 학습·모델/평가 실행은0이다.

`log-to-result`의 원형 JSON 대조·비교조건·기존 결과 보존 원칙을 적용했다. 쓰기는 이 절뿐이므로 결과101/계획/기준표/COMPASS/공용 source를 갱신하지 않는다. 읽은 실물 원형은 총괄이 지정한 [Core6 v2](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2)의 네 모델 `full/report.json`·sample/length JSONL 및 그 manifest다. 큰 QA/raw 본문이나 logits는 출력하지 않았고 CP/원 데이터 parquet/ALM cache는 열지 않았다.

기존 Core6의 source identity는 `F6FB22CA9B1F4A54BF1F5DFB350FEF3A7391E0A0A85845169EB166B5B8DC3FA6`, 공식 harness commit은 `d6de81643928d653435c431bae19945d41d32520`, 네 report의 공통 data-manifest 기록은 `431A096364D44980A7D0C6E072E8A06C2FAA109946FAA07E56F7687CADFEA60B`다. 원 data-manifest/parquet 전체를 이번에 재해시한 것은 아니다.

[원 Core6 source 사본](/home/uranus/tinyLM/handoff/audit/source_snapshots/20261023_pre_cache_policy_diag_p106b_official_core6.py.txt)의 SHA `9C2AAD219A7B4B0EAB40D396C0A107F6486FB5C4D123CBB3E16771D5D78771D8`는 네 report에 고정된 evaluator source와 일치한다. **새 BabyLM/V3 cache-policy 수리의 현재 source identity로 과거 Core6를 재인증하지 않았다.** 현재 evaluator와 사본의 `independent_row/audit_samples` AST만 같음을 따로 확인했다. 새 코드 전체가 원 실행 때와 같다는 주장이 아니다.

### 20.2 정확히 어느 문항·어느 요청인가

길이 영수증67106행의 순차 index를 실제 sample의 `arguments` 순서와 **전부** 대응시켰다. 요청 key는 원 source와 같은 `SHA256(json.dumps([context,continuation],ensure_ascii=False).encode("utf-8"))`로 재구성했다. 길이 metadata를 문항 순서만 보고 추정 매핑한 것이 아니다.

| 모델 | task/doc_id·원 idx | 보기 index / 요청 index | 원 context 토큰/보기 토큰 | 요청별 잘린 context 토큰 | 두 요청 합 |
|---|---|---|---|---|---|
| native595-f | boolq/3154, idx3154 | 0/66874, 1/66875 | 1161/1, 1161/1 | 137,137 | 274 |
| native595-q | 동일 | 동일 | 1161/1, 1161/1 | 137,137 | 274 |
| new595-broad-f | 동일 | 동일 | 1161/1, 1161/1 | 137,137 | 274 |
| falcon90m | 동일 | 동일 | 1389/1, 1389/1 | 365,365 | 730 |

`274/730`은 **같은 문맥을 보기 두 개에서 각각 자른 토큰 수의 합**이다. 한 입력에서274/730개를 한꺼번에 삭제했다는 뜻이 아니다. 네 모델 모두 이 문항의 gold=1, raw-score argmax=1로 정답이었다. 이것은 제외 규칙을 정한 이유가 아니며, 제외 규칙은 어느 모델이든 요청 한 개 이상이 잘렸는지만 사용했다. 다른 모든 요청의 `truncated_context_tokens=0`도 전량 검산했다.

원 source의 `length_observer` 및 [plan_tokens](/home/uranus/tinyLM/scripts/p106b_official_lm_adapter.py:176)는 `removed=max(0,C+Y−1025)`와 `last(1025)→input[:-1]`을 따른다. 여기서 보기 Y=1이라 남기는 context는 양쪽 모두1024토큰이다. **토큰 개수가 다르게 잘렸다는 사실은 확인했지만, 실제 남은 suffix의 byte 경계가 서로 정확히 어디인지는 이 길이 ledger만으로 복원하지 못한다.** 이번에는 tokenizer를 실행하지 않았고 해당 위치의 native token-ID열도 재취득하지 않았으므로 유효 입력 suffix의 byte 동일/불동일 자체는 미확인이다.

반면 **절단 전 원문이 같은지**는 별도 근거가 있다. 네 모델의19965개 대응 raw row에서 `doc/arguments/target/doc_hash/prompt_hash/target_hash`를 고정 canonical JSON SHA로 전수 비교해 모두 같았다. 해당 문항의 전체 context는4867 UTF-8 bytes이고 아래 값들도 네 모델에서 같다.

| 원문 정체성 | SHA-256 |
|---|---|
| passage UTF-8 원값 | `8DAC30E078F34948D3EE5D7B82DF59AC85A7BE2B499C8C3213C5CCEAD7801652` |
| question UTF-8 원값 | `DD536442BDF96487C60DBAB07383426C6659E7546A8D2E370441638AF4EC3A53` |
| 실제 절단 전 context UTF-8 원값 | `ECB661B8469A15D183C5A35DC716F417D50DB04326DBC60C38FB098CC41346AE` |
| `doc`의 감사 canonical JSON | `DE82EBCEFCBE5694423D5914FF625F33C256A0330377C30AB6707AB548B9F29A` |
| 두 `arguments`의 감사 canonical JSON | `23EEC07DF0AF7E69B39DD635903180262D09185A02C6FD2B12B1BF60516DE39A` |
| 원 저장 `doc_hash` | `2dc38e272eea4b90dbdff50c773c4c00b8c83d1271fee556f20ed325249c82fc` |
| 보기0의 원 요청 key | `0B8782024D5F6D9736D944C098006BACD696692B2FE1D2912016A3629C10F033` |
| 보기1의 원 요청 key | `FBEF038C4611A676F3D948D6F2EA5FD2961B674E98C6A9A5C17DCC3311D0F706` |

감사 canonical JSON은 `ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False`의 UTF-8이며, 공식 저장 `doc_hash`와 직렬화 계약이 달라 같은 hash명으로 섞지 않는다. 원문 전문을 새 문서/학습 자료에 복사하지 않았다.

### 20.3 공정성 범위와 공통 제외 규칙

[첨부 §6.6의 공통 원문 규칙](/home/uranus/tinyLM/ai_dev_tool/temp_20261023_작업지시서_참고용.md:454)에 따르면 동일1024 cap만으로 모든 모델에서 같은 문맥을 사용했다고 단언할 수 없다. 원 전체 결과는 **같은 공식 문항·원문·1024 cap의 역사적 기술통계**로 보존하되, BoolQ3154를 포함해 전 문항이 공통 무절단/동일 유효 suffix였다는 주장은 하지 않는다. 길이 경계 밖의 tokenizer 정규화·forward 구현 전체를 이번 CPU 감사가 새로 재검증한 것도 아니다.

보조 집합은 `E = union_models{(task,doc_id): 어떤 보기 요청이라도 truncated_context_tokens>0}`를 원형에서 구한 뒤 네 모델에 **같은 E**를 적용했다. 실제 `E=[["boolq",3154]]`다. 모델별로 다른 문항을 빼거나 틀린 답만 골라 제외하지 않았다. 원 doc_id를 재번호화하지 않고 지표 분모만 줄였으며 NLL·예측·보기의 문자 분모·원 정답은 바꾸지 않았다.

이 집합에서 다섯 과제는 원 전체와 같고 BoolQ만3270→3269, 보기 요청 합은67106→67104다. 이를 **공통 원문·공통 무절단 부분집합의 보조 재집계**라고 부른다. 공식 전체 score를 대체하는 새 공식 벤치마크 점수나 모델 품질/ALM 효과의 재실행 결과가 아니다.

### 20.4 원 예측의 CPU 재집계

원 source의 `independent_row`를 호출해 **모든 보기의 finite/nonpositive score**, 첫 argmax tie 규칙, 원 보기 문자열 길이의 `acc_norm`을 다시 계산했다. 원 `audit_samples`로 과제별 doc_id0..N−1·전량/지표도 먼저 확인했다. WinoGrande는 `multiple_input=True`인 공식 `doc_to_text`의 정수 gold를 사용하며, raw row의 문자열 `target`을 임의 정수 변환하지 않는다. HellaSwag는 이미 공식 전처리된 `doc["choices"]`, ARC는 `choices.text/label`, BoolQ는 공식 YAML의 `["no","yes"]`를 쓴다.

| 사전 주지표 | 공통 분모 | native595-f 정답 | native595-q 정답 | new595-broad-f 정답 | falcon90m 정답 |
|---|---:|---:|---:|---:|---:|
| piqa acc | 1838 | 1078 | 1045 | 1078 | 1193 |
| arc_easy acc_norm | 2376 | 907 | 879 | 899 | 1161 |
| arc_challenge acc_norm | 1172 | 262 | 265 | 281 | 330 |
| hellaswag acc_norm | 10042 | 2748 | 2713 | 2765 | 3762 |
| winogrande acc | 1267 | 621 | 629 | 635 | 654 |
| boolq acc | 3269 | 1827 | 1819 | 1839 | 1933 |

| 모델 | BoolQ 정답/분모 | BoolQ acc | 원19965의 6task equal macro | 공통19964의 6task equal macro | macro 변화 |
|---|---:|---:|---:|---:|---:|
| native595-f | 1827/3269 | 55.88865096% | 41.90994695% | 41.90769866% | -0.00224828%p |
| native595-q | 1819/3269 | 55.64392781% | 41.46333362% | 41.46107286% | -0.00226076%p |
| new595-broad-f | 1839/3269 | 56.25573570% | 42.39756260% | 42.39533302% | -0.00222958%p |
| falcon90m | 1933/3269 | 59.13123279% | 48.35875402% | 48.35667100% | -0.00208302%p |

집계식은 `(PIQA_acc + ARC-E_acc_norm + ARC-C_acc_norm + HellaSwag_acc_norm + WinoGrande_acc + BoolQ_acc)/6`이다. 전체19964문항 micro 평균이 아니고, 저장된 반올림 백분율을 평균한 것도 아니다. `Fraction(정답수,과제분모)`로 각 값을 정확히 만든 뒤 마지막 출력만 소수로 바꿨다. 공통 subset의 비율형 macro 원형은 다음과 같다.

| 모델 | exact macro 비율; ×100 전 |
|---|---|
| native595-f | `4779234581256600977/11404192388982635088` |
| native595-q | `1576100171819163181/3801397462994211696` |
| new595-broad-f | `4834845342019606807/11404192388982635088` |
| falcon90m | `29178242295994019/60339642269749392` |

네 모델 모두 제외 문항이 정답이어서 BoolQ/평균이 조금 내려간다. **순위는 그대로지만 변화가 작다는 이유로 공통 입력 규칙의 미충족을 없던 일로 하지 않는다.** 이 재계수는 paired bootstrap/학습 seed 변동/오염/대화능력의 새 검증을 포함하지 않으며 주장 등급은 `DESCRIPTIVE_ONLY`다. 결과101 §446의 원표는 교체하지 않았다.

### 20.5 원형 closure와 SHA 영수증

네 report는 모두 `OFFICIAL_CORE6_FULL_COMPLETE/returncode0`, 원 과제별 분모와 source/policy/data-manifest 기록이 같음을 확인했다. 원 report SHA는 다음과 같다.

| full report | SHA-256 |
|---|---|
| [native595-f](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/native595-f/full/report.json) | `56167EB44003F6859E952234AE91B936826BDF0F224F1440B914C7C2387A07A8` |
| [native595-q](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/native595-q/full/report.json) | `0538084C70FA0A8DB92368BAC830726CD9D8216EE4F114CE29370EA2DDCC80AA` |
| [new595-broad-f](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/new595-broad-f/full/report.json) | `D976EFC8371739537A57D69269A42ADD1FF63555B986DEC421B834D38155C5B3` |
| [falcon90m](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/falcon90m/full/report.json) | `33CD985EDA2F1BB1E113627EC80B2BF938011B1863EF2C8C52CD3D4BDE74BCEC` |

아래 각 JSONL의 bytes·행 수·개별 SHA·연결 SHA는 report 안 manifest와 디스크의 `*_shards_manifest.json`이 같은지 먼저 검사한 뒤, 원 `p106b_shards.verify(directory,manifest)`로 검산했다. 각 샤드20MB 이하/마지막 개행/순서도 이 helper의 검사 범위다. 따라서 아래 SHA는 이름만 인용한 것이 아니라 원형 byte 검산을 통과한 값이다. 과제별 합계19965행과 길이67106행을 네 모델 모두 확인했다.

| 원 JSONL | 행 수 | SHA-256 |
|---|---:|---|
| [native595-f/piqa_samples_000000.jsonl](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/native595-f/full/piqa_samples_000000.jsonl) | 1838 | `AD1AD0EACACBCEFA461E3CFB75B9BE62F5C51AEDDCC2719D35063C23DB1126D7` |
| [native595-f/arc_easy_samples_000000.jsonl](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/native595-f/full/arc_easy_samples_000000.jsonl) | 2376 | `01E7B2781ABAA39E7EF7DE32016E1C0E834B243FC8A6556885FE628A435E7335` |
| [native595-f/arc_challenge_samples_000000.jsonl](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/native595-f/full/arc_challenge_samples_000000.jsonl) | 1172 | `640BA0FDC5B0606EF87D0DCA032477835C3571CABDA51FB13B8B07AEB5D98266` |
| [native595-f/hellaswag_samples_000000.jsonl](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/native595-f/full/hellaswag_samples_000000.jsonl) | 5688 | `50BDE0664761A2B11D82C172F5AD4A0E3A377BE0AC55B9A50CC7AACC1E2B487D` |
| [native595-f/hellaswag_samples_000001.jsonl](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/native595-f/full/hellaswag_samples_000001.jsonl) | 4094 | `9D838753606893EEAC9321DD22F391D64022E6D67B5919A53C96770350091EAA` |
| [native595-f/hellaswag_samples_000002.jsonl](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/native595-f/full/hellaswag_samples_000002.jsonl) | 260 | `ED19304BF244E1DBAF0B795B9974DC71E9DCA8F0F094BAEB58C7048C027D509A` |
| [native595-f/winogrande_samples_000000.jsonl](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/native595-f/full/winogrande_samples_000000.jsonl) | 1267 | `F6EF89F971B08AAD9440C950350421E02F6A64EA80D8CD9DA421A3ABF4A5EFDF` |
| [native595-f/boolq_samples_000000.jsonl](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/native595-f/full/boolq_samples_000000.jsonl) | 3270 | `4C94E52E64B169114F04E5C1EA7135AF0865E8A02BDE9861684DEC1BA3B2B524` |
| [native595-q/piqa_samples_000000.jsonl](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/native595-q/full/piqa_samples_000000.jsonl) | 1838 | `BE83DE6F7282912666988528E2107A3BEB82D479130A44931429F29ECAB1D349` |
| [native595-q/arc_easy_samples_000000.jsonl](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/native595-q/full/arc_easy_samples_000000.jsonl) | 2376 | `8F8C60650C765169AD398466D5BA95C090961F7598E38D6F87F01EC12F3BC149` |
| [native595-q/arc_challenge_samples_000000.jsonl](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/native595-q/full/arc_challenge_samples_000000.jsonl) | 1172 | `0ACA606491445351BCBDC1D991382D7789C2D0D1C7FDAC922EEF569B9302ACCD` |
| [native595-q/hellaswag_samples_000000.jsonl](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/native595-q/full/hellaswag_samples_000000.jsonl) | 5688 | `B53CE30726B4076B4DC1BDD5F1221700C4494A6FBDC59BB7F27A9D52BBAF84A1` |
| [native595-q/hellaswag_samples_000001.jsonl](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/native595-q/full/hellaswag_samples_000001.jsonl) | 4094 | `482CC8740ADB20BD5CBDB11BCDB419946D67A03567E25FDEE4E6F90569EA26ED` |
| [native595-q/hellaswag_samples_000002.jsonl](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/native595-q/full/hellaswag_samples_000002.jsonl) | 260 | `78B1B7BDE29BD05389F5ED63A117216C5ED27412D8C7B72B00FE93C2995B659A` |
| [native595-q/winogrande_samples_000000.jsonl](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/native595-q/full/winogrande_samples_000000.jsonl) | 1267 | `9AE1FB5617CDCA699EDD87DCB799E8FCB0F4CA6F008A01A95316921CE79975EA` |
| [native595-q/boolq_samples_000000.jsonl](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/native595-q/full/boolq_samples_000000.jsonl) | 3270 | `2A5515853150107D7966FF612D9AB03626B540F1DDB8D10CF12F1C2E53B285B3` |
| [new595-broad-f/piqa_samples_000000.jsonl](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/new595-broad-f/full/piqa_samples_000000.jsonl) | 1838 | `B5D90EDA4258C5E6796982712E0733F59CFCCF79A57783185641C1552ACF65FA` |
| [new595-broad-f/arc_easy_samples_000000.jsonl](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/new595-broad-f/full/arc_easy_samples_000000.jsonl) | 2376 | `822786D0970AF443C986DBA9F448B929653AB681263970E29C87B72D6F0A7E9A` |
| [new595-broad-f/arc_challenge_samples_000000.jsonl](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/new595-broad-f/full/arc_challenge_samples_000000.jsonl) | 1172 | `3841F51F9AFC97B7FDD8C6D8C3B508E8E34490B5927C41D6F45920FAF51C4838` |
| [new595-broad-f/hellaswag_samples_000000.jsonl](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/new595-broad-f/full/hellaswag_samples_000000.jsonl) | 5688 | `013310D8127487941D3CB5C4F98B02D1AC8311626307DF9BFFB7F0BC9A0C3D48` |
| [new595-broad-f/hellaswag_samples_000001.jsonl](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/new595-broad-f/full/hellaswag_samples_000001.jsonl) | 4094 | `9D184453A65BED62C310F2FCFDD7BEA0951508C3C6E238B3222B4509B75249FE` |
| [new595-broad-f/hellaswag_samples_000002.jsonl](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/new595-broad-f/full/hellaswag_samples_000002.jsonl) | 260 | `89DEBB4ABC7F70DF978802C37D55B3F24C76CC9A349FC8C96237DD495EEB14E8` |
| [new595-broad-f/winogrande_samples_000000.jsonl](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/new595-broad-f/full/winogrande_samples_000000.jsonl) | 1267 | `1ABC027969A9F0FAB1B17C702E18FCDD3FB77AF2F6CC1F31077F5C657C0EA7CB` |
| [new595-broad-f/boolq_samples_000000.jsonl](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/new595-broad-f/full/boolq_samples_000000.jsonl) | 3270 | `9EF03D75624A670E2EB33355B8CDE74FA78B8CEA453FFB0F526F949FEA8A104F` |
| [falcon90m/piqa_samples_000000.jsonl](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/falcon90m/full/piqa_samples_000000.jsonl) | 1838 | `E8279153889B11C4438AD354128B865342C78D27E310486F5F42FE667351C2BD` |
| [falcon90m/arc_easy_samples_000000.jsonl](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/falcon90m/full/arc_easy_samples_000000.jsonl) | 2376 | `FD1CE9DFF47FF767F0194CA61822B11FD75DB951EBE84E29E928F90A146D3B2A` |
| [falcon90m/arc_challenge_samples_000000.jsonl](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/falcon90m/full/arc_challenge_samples_000000.jsonl) | 1172 | `3B7E3657B5BFD7735C2B06367E24F5BFA8D5FA0DB0FB42C317BE23FD459C1C70` |
| [falcon90m/hellaswag_samples_000000.jsonl](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/falcon90m/full/hellaswag_samples_000000.jsonl) | 5688 | `EF8972AA00ADF053CD0707F73A99D22CBFD9D0908F459C48E79DEE4238199CE4` |
| [falcon90m/hellaswag_samples_000001.jsonl](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/falcon90m/full/hellaswag_samples_000001.jsonl) | 4095 | `033B72C3FE46171989AF26CC48C00EF14A980E5DEA6F189702078BC6C46E9F99` |
| [falcon90m/hellaswag_samples_000002.jsonl](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/falcon90m/full/hellaswag_samples_000002.jsonl) | 259 | `5F774AD4C158153E89558EB76E1572831B2B13F078475DAF259063A08B50BC0A` |
| [falcon90m/winogrande_samples_000000.jsonl](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/falcon90m/full/winogrande_samples_000000.jsonl) | 1267 | `31AEDE4FC28BAECD48AF8EC576FF55E6032214501BD26C6DBE532488CAE403B0` |
| [falcon90m/boolq_samples_000000.jsonl](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/falcon90m/full/boolq_samples_000000.jsonl) | 3270 | `D8B8F25F168778407B9A0B264D18D7E01B7FD36C3253609855F80C2E918DCFEA` |
| [native595-f/token_lengths_000000.jsonl](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/native595-f/full/token_lengths_000000.jsonl) | 67106 | `A6F749BC0D082AAF57AF9E445B328CD16BEE17A26B71207FD3F668609869833B` |
| [native595-q/token_lengths_000000.jsonl](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/native595-q/full/token_lengths_000000.jsonl) | 67106 | `A6F749BC0D082AAF57AF9E445B328CD16BEE17A26B71207FD3F668609869833B` |
| [new595-broad-f/token_lengths_000000.jsonl](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/new595-broad-f/full/token_lengths_000000.jsonl) | 67106 | `A6F749BC0D082AAF57AF9E445B328CD16BEE17A26B71207FD3F668609869833B` |
| [falcon90m/token_lengths_000000.jsonl](/home/uranus/tinyLM/test_result/evidence/p106b_official_core6_v2/falcon90m/full/token_lengths_000000.jsonl) | 67106 | `27B1A1D8F5054DCE7BE7ED3CCBC8EFA25AAC7F9E882B7FA09C0D5F893DB95078` |

단일 샤드 과제는 개별 SHA와 연결 SHA가 같고, HellaSwag3샤드의 별도 연결 SHA는 다음과 같다.

| 연결 원형 | SHA-256 |
|---|---|
| native595-f/hellaswag 3샤드 연결 | `F5F612235A4E0FF2BCAF7C8002647FF39F91C08ABCDB0895F7145819063B4300` |
| native595-q/hellaswag 3샤드 연결 | `D43ED41DCF56A6DF581C94DC3B648353EBFFD1071255264D85BD58D887A933CE` |
| new595-broad-f/hellaswag 3샤드 연결 | `CE0E1A6D199F7F78970075D0B38ED86E17C6D1C17AF35CCFDD48309646431B66` |
| falcon90m/hellaswag 3샤드 연결 | `D930A3DFA43B7723315CA7F2843FBA3A028AE9D1E1ABD1471E652A4AC8F7262C` |

### 20.6 복제할 수 있는 계산 원형과 한계

아래는 이번에 실제 실행해 종료0을 확인한 **읽기 전용 stdlib 계산 본문**이다. 저장소 코드 파일은 만들지 않았다. 총괄은 저장소 루트에서 `python3 -I -B`의 표준입력으로 실행할 수 있다. source 두 함수와 shard verifier, 공식 Wino 함수만 AST로 추출하며 전체 evaluator import·`load_tasks`·`execute`·모델 runtime을 호출하지 않는다. 추출한 함수에는 필요한 `math/Counter/Path/hashlib/MAX_BYTES`만 제공한다. 본문 출력은 SHA/분모/정답/길이/진단 scalar이며 QA·logits 전문이 아니다. 문서에 수록한109행 계산 본문도 AST 구문 확인했으며 코드펜스/끝 개행을 제외한 문자열 SHA는 `778874A5E158A3EF0EDC15DFA4721088927D3A0E292CAD3F927AB256A579B0E4`다.

원 evaluator snapshot SHA는 §20.1과 같고, 실행한 shard helper SHA는 `30CBD7D6B5BE09D4C8B8983CDD607EF07BA379CC3892067C41D3A06DF22E1DA4`, 공식 Wino helper SHA는 `E55327629264A98F1D383FDA24645B6779AFB53FA0BCE2150042B9416B1AE006`다. 현재 evaluator의 순수 두 함수 AST가 snapshot과 같다는 검사와 **현재 파일 전체 SHA가 원 실행과 같다는 검사**를 구분한다. 원 source identity를 현 V3 cache-policy identity로 교체하지 않는다.

코드의 `stable` 객체, 즉 **digest 필드를 추가하기 전** 계산 결과에서 환경 의존 진단필드2개(`python_version/diagnostic_differences`)를 뺀 canonical JSON SHA는 **`26CE6D479A6E46E33388962A9E1AE01EBB255FF63C75936695841C89CEE571DD`**다. 완성된 출력 JSON에서 다시 계산할 때는 자기 자신인 `canonical_audit_sha256` 필드도 제외한다. 코드는 이 digest를 출력하므로 총괄이 원형 감사로 복제할 때 전체 비교 대상도 고정된다.

초기 CPU 시도의 중단도 남긴다. 첫 시도는 `posthoc_label_counts`의 정수/JSON문자열 key 직접 비교로, 다음 시도는 ARC-Challenge의 **랜덤 기대 정답수 진단** `293.18333333333334` 대 원 기록 `293.1833333333333`의 엄격 float 비교로 중단했다. 후자의 근본 환경 원인을 여기서 확정하지 않는다. 최종 검산은 integer histogram을 JSON 왕복하고, 주지표와 정답/분모·다른 진단은 정확 대조하되 랜덤 기대수/SD의 float 차이는 별도 `diagnostic_differences`로 보존한다. 실제 차이는 네 모델의 위 ARC-C 기대수뿐이었고 주지표/원 예측 차이는0이다. 원 evaluator에 이미 있는 official 비율 대조의 `abs_tol=1e-12` 외에 새 품질/학습 문턱을 채택하지 않았다.

성공한 계산은 Python3.12.3의 CPU stdlib에서9.07초, 공통 report/source/policy 검산을 더한 마지막 동일 계산은7.30초에 종료0이었다. 파일 캐시 등이 다른 실행시간이므로 둘을 평가 처리량/실물 모델 속도로 해석하지 않는다. 총괄의 모델/GPU 계산은 계속 별도 소유이며 이 감사는 NVML·torch·tokenizer/model import·HTTP·학습/새 평가·설치·Git·삭제·공유 코드 수정0이다.

```python
import ast, hashlib, json, math
from collections import Counter
from fractions import Fraction
from pathlib import Path
ROOT=Path('/home/uranus/tinyLM')
BASE=ROOT/'test_result/evidence/p106b_official_core6_v2'
MODELS=('native595-f','native595-q','new595-broad-f','falcon90m')
COUNTS=dict(piqa=1838,arc_easy=2376,arc_challenge=1172,hellaswag=10042,winogrande=1267,boolq=3270)
PRIMARY=dict(piqa='acc',arc_easy='acc_norm',arc_challenge='acc_norm',hellaswag='acc_norm',winogrande='acc',boolq='acc')
SNAP=ROOT/'handoff/audit/source_snapshots/20261023_pre_cache_policy_diag_p106b_official_core6.py.txt'
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest().upper()
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def value_sha(value):return hashlib.sha256(canonical(value)).hexdigest().upper()
def request_sha(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False).encode('utf-8')).hexdigest().upper()
def text_sha(value):return hashlib.sha256(value.encode('utf-8')).hexdigest().upper()
def selected(path,names,env):
    nodes=[n for n in ast.parse(path.read_text(encoding='utf-8')).body if isinstance(n,ast.FunctionDef) and n.name in names]
    assert {n.name for n in nodes}==set(names)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),env)
    return {n.name:ast.dump(n,include_attributes=False) for n in nodes}
env=dict(math=math,Counter=Counter)
old_ast=selected(SNAP,('independent_row','audit_samples'),env)
new_ast=selected(ROOT/'scripts/diag_p106b_official_core6.py',('independent_row','audit_samples'),dict(math=math,Counter=Counter))
assert old_ast==new_ast
shards_path=ROOT/'scripts/p106b_shards.py'
sv=dict(Path=Path,hashlib=hashlib,MAX_BYTES=20_000_000)
selected(shards_path,('verify',),sv)
wino=ROOT/'data_cache/p106b_official_eval_tools/lm_eval_d6de81643928d653435c431bae19945d41d32520/source/lm_eval/tasks/winogrande/preprocess_winogrande.py'
wv={};selected(wino,('doc_to_text','doc_to_target','doc_to_choice'),wv)
def rows(directory,manifest):
    sv['verify'](directory,manifest)
    for s in manifest['shards']:
        with (directory/s['path']).open(encoding='utf-8') as f:
            for line in f:yield json.loads(line)
def choice_gold(task,doc):
    if task=='piqa':return [doc['sol1'],doc['sol2']],doc['label']
    if task.startswith('arc_'):return doc['choices']['text'],doc['choices']['label'].index(doc['answerKey'])
    if task=='hellaswag':return doc['choices'],int(doc['label'])
    if task=='boolq':return ['no','yes'],doc['label']
    return wv['doc_to_choice'](doc),wv['doc_to_text'](doc)
reports={};bad_keys=set();ledger=[]
for model in MODELS:
    d=BASE/model/'full';r=json.loads((d/'report.json').read_text(encoding='utf-8'));reports[model]=r
    assert r['status']=='OFFICIAL_CORE6_FULL_COMPLETE' and r['returncode']==0 and r['actual_counts']==COUNTS
    assert digest(SNAP)==r['source_identity']['files']['scripts/diag_p106b_official_core6.py']
    assert digest(shards_path)==r['source_identity']['files']['scripts/p106b_shards.py']
    assert r['framework_commit']=='d6de81643928d653435c431bae19945d41d32520'
    lm=r['lengths_manifest'];assert lm==json.loads((d/'token_lengths_shards_manifest.json').read_text(encoding='utf-8'))
    lr=list(rows(d,lm));assert len(lr)==67106 and [x['index'] for x in lr]==list(range(67106))
    bad=[x for x in lr if x['truncated_context_tokens']]
    assert sum(x['truncated_context_tokens'] for x in lr)==r['token_lengths_summary']['context_tokens_removed']
    assert len(bad)==r['token_lengths_summary']['context_truncated_requests']
    bad_keys.update(x['key_sha256'] for x in bad);reports[model]['_lengths']=lr
    ledger.append(dict(model=model,report_sha256=digest(d/'report.json'),length_manifest_sha256=digest(d/'token_lengths_shards_manifest.json'),lengths_sha256=lm['concat_sha256'],truncated=bad))
assert all(reports[m]['source_identity']==reports[MODELS[0]]['source_identity'] and reports[m]['policy']==reports[MODELS[0]]['policy'] and reports[m]['data_manifest_sha256']==reports[MODELS[0]]['data_manifest_sha256'] for m in MODELS)
assert len(bad_keys)==2
baseline={};exclude=set();results={};truncated=[];raw_ledger=[];diagnostic_differences=[]
for model in MODELS:
    d=BASE/model/'full';r=reports[model];lengths=r['_lengths'];request_index=0;full={};kept={};excluded=[]
    for task,count in COUNTS.items():
        man=r['sample_manifests'][task];mp=d/(task+'_samples_shards_manifest.json')
        assert json.loads(mp.read_text(encoding='utf-8'))==man
        records=list(rows(d,man));assert [x['doc_id'] for x in records]==list(range(count))
        raw_ledger.append(dict(model=model,task=task,manifest_sha256=digest(mp),concat_sha256=man['concat_sha256'],shards=[{k:s[k] for k in ('path','sha256','rows','bytes')} for s in man['shards']]))
        class Task:
            eval_docs=[x['doc'] for x in records]
            multiple_input=task=='winogrande'
            def doc_to_choice(self,doc):return choice_gold(task,doc)[0]
            def doc_to_target(self,doc):return choice_gold(task,doc)[1]
            def doc_to_text(self,doc):return choice_gold(task,doc)[1]
        audited=env['audit_samples'](Task(),records,count)
        normalized=json.loads(json.dumps(audited)); expected=r['independent_audits'][task]
        diff={k:[normalized.get(k),expected.get(k)] for k in set(normalized)|set(expected) if normalized.get(k)!=expected.get(k)}
        assert not (set(diff)-{'random_expected_correct','random_independent_sd'}), (model,task,diff)
        if diff:diagnostic_differences.append(dict(model=model,task=task,diff=diff))
        metric=PRIMARY[task];full[task]=audited['correct_norm' if metric=='acc_norm' else 'correct']
        official=r['official_results'][task]['results'][task][metric+',none']
        assert math.isclose(official,full[task]/count,abs_tol=1e-12)
        kept[task]=[0,0]
        for row in records:
            ident=(task,row['doc_id'])
            signature=value_sha({k:row[k] for k in ('doc','arguments','target','doc_hash','prompt_hash','target_hash')})
            if model==MODELS[0]:baseline[ident]=signature
            else:assert baseline[ident]==signature
            choices,gold=choice_gold(task,row['doc'])
            check=env['independent_row'](choices,gold,[x[0] for x in row['filtered_resps']])
            has_bad=False
            for ci,arg in enumerate(row['arguments']):
                lr=lengths[request_index];assert lr['key_sha256']==request_sha(arg)
                assert lr['truncated_context_tokens']==max(0,lr['context_tokens']+lr['continuation_tokens']-1025)
                if lr['key_sha256'] in bad_keys:has_bad=True
                if lr['truncated_context_tokens']:
                    x=dict(model=model,task=task,doc_id=row['doc_id'],choice_index=ci,**lr)
                    x.update(original_doc_idx=row['doc'].get('idx'),stored_doc_hash=row['doc_hash'],stored_prompt_hash=row['prompt_hash'],stored_target_hash=row['target_hash'],doc_canonical_sha256=value_sha(row['doc']),arguments_canonical_sha256=value_sha(row['arguments']),context_utf8_sha256=text_sha(arg[0]),passage_utf8_sha256=text_sha(row['doc']['passage']),question_utf8_sha256=text_sha(row['doc']['question']),context_utf8_bytes=len(arg[0].encode('utf-8')),gold=gold,pred=check['pred'],correct=check[metric])
                    truncated.append(x)
                request_index+=1
            if has_bad:
                exclude.add(ident);excluded.append(dict(task=task,doc_id=row['doc_id'],correct=check[metric],gold=gold,pred=check['pred']))
            else:
                kept[task][0]+=check[metric];kept[task][1]+=1
    assert request_index==67106 and len(excluded)==1
    full_macro=sum((Fraction(full[t],COUNTS[t]) for t in COUNTS),Fraction())/6
    subset_macro=sum((Fraction(*kept[t]) for t in COUNTS),Fraction())/6
    results[model]=dict(full_correct=full,subset_correct_denominator=kept,full_macro_fraction=str(full_macro),full_macro_percent=float(full_macro*100),subset_macro_fraction=str(subset_macro),subset_macro_percent=float(subset_macro*100),macro_change_percentage_points=float((subset_macro-full_macro)*100),excluded=excluded)
assert exclude=={('boolq',3154)}
out=dict(schema='P106B_CORE6_COMMON_UNTRUNCATED_CPU_AUDIT_V1',python_version=__import__('sys').version,diagnostic_differences=diagnostic_differences,source_snapshot_sha256=digest(SNAP),shard_helper_sha256=digest(shards_path),wino_helper_sha256=digest(wino),helper_asts_equal=True,all_raw_doc_argument_target_identities_equal=True,data_manifest_sha256=reports[MODELS[0]]['data_manifest_sha256'],framework_commit=reports[MODELS[0]]['framework_commit'],excluded=sorted(exclude),report_ledger=ledger,raw_ledger=raw_ledger,truncated_requests=truncated,results=results)
stable={k:v for k,v in out.items() if k not in ('python_version','diagnostic_differences')}
out['canonical_audit_sha256']=value_sha(stable)
print(json.dumps(out,ensure_ascii=False,sort_keys=True,separators=(',',':')))
```

## 21. Q32 ALM의 CE/KD 역방향 신호 해석 — 관측·미분식·미확인을 구분

### 21.1 현재 확인한 결과와 해석 범위

**이번 Q32 조건에서 CE+ALM은 CE-only보다 DEV CE가0.13307185 nats/target 높았고, fixed64 literal exact는 부모/CE/ALM 모두0이었다.** 이는 해당 Q 부모·동결 자료·한 seed·32update·고정 손실의 부정 결과이지 ALM 논문 전체의 기각이나 구현 버그의 증명은 아니다. 총괄이 확인한 사용자8개의 반복/오답 유지도 별도 관측으로 보존한다. 이 담당은 생성 답안 원문을 다시 읽거나 의미 재채점하지 않았다.

§19의 대기/float-only 상태는 당시 기록으로 남기고 여기서 후속을 누적한다. 총괄은 V7 원1024 TF cache의 종료와 F의 자체 교정 완료/cost 진행을 전달했다. 이 담당은 **닫힌 Q calibrate/train/evaluate report6개와 그 source pin만** 직접 읽었다. F의 진행 중 report나 원1024 QA/교사 raw/CP를 열지 않았으며, 새로운 모델/GPU·수치 gradient·학습/평가를 실행하지 않았다. 아래 파생값은 저장된 scalar의 CPU stdlib 산술이다.

| Q 평가본 | DEV TF CE; 공통2977 target | fixed64 strict literal exact | 관측 |
|---|---:|---:|---|
| 부모 | 6.1321680942 | 0/64 | 출발점 |
| CE-only32 | 4.6361323040 | 0/64 | 부모보다 CE1.4960357902 감소 |
| CE+ALM32 | 4.7692041522 | 0/64 | 부모보다 CE1.3629639420 감소, CE-only보다0.1330718482 높음 |

두 학습 팔은 report상32update·CE target23588·정렬 chunk17020으로 같고, 초기 core/RNG·32개 update의 ordered-record SHA/row-ID 순서도 서로 같음을 메타데이터로 대조했다. Q profile은 `native595-q / ternary_v1`, **TLINEAR_WEIGHTS_ONLY의 ternary/STE**이며 embedding/head는 `FP32_TIED_EMBEDDING_AND_HEAD`다. 전 모델/어휘 head까지 hard 삼진으로 바꾼 실험은 아니다. F는 다른 부모와 자체 교정을 쓰므로 Q의 λ/cosine을 이식하거나 Q−F를 양자화 단독 효과로 해석하지 않는다.

### 21.2 실제 core의 목적함수와 부호

[alm.py](/home/uranus/tinyLM/tinylm/train/alm.py:16)의 `target_nll/binary_kl_logq/chunk_kl/normalized_loss` 전체와 [학생 제어기](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py:809)의 `ALMCore/gradient_stats/last_block_parameters/calibrate`를 실제 읽었다. teacher logp는 detach한 원 reference-token logp의 합이며 대안 토큰 분포나 새 교사 답안을 추가하지 않는다. 학생 NLL도 이미 한 번 shift한 target에서 구한다.

chunk c의 학생 NLL 합을 Uc, 교사 raw logp 합을 Tc라 두면 현재 계산은 다음과 같다.

```text
ni = -log pS(reference_token_i | gold prefix)
Uc = sum_{i in c} ni,          Tc = sum_{j in teacher_chunk(c)} log pT(reference_token_j | gold prefix)
qS,c = exp(-Uc / tau),         qT,c = exp(Tc / tau),        tau = 100
Dc = qT,c*log(qT,c/qS,c) + (1-qT,c)*log((1-qT,c)/(1-qS,c))
L = (sum_i ni)/N + lambda*(sum_c Dc)/K
lambda = 36.32277684798984,    N = CE target count,         K = aligned chunk count
```

`0<qS<1`의 내부점에서 chunk 안 target 하나에 대해 직접 미분하면 다음과 같다. teacher qT=1의 별도 분기는 dDc/dni=1/τ로 이어지고, qS=1/qT<1은 코드의 명시적 경계 중단이므로 아래 내부식에0을 대입해 처리하지 않는다.

```text
dDc/dni = (qT,c - qS,c) / [tau*(1-qS,c)]
dL/dni  = 1/N + lambda*(qT,c-qS,c)/[K*tau*(1-qS,c)]
gC = sum_i (1/N)*grad(ni)
gK = sum_c sum_{i in c} [(qT,c-qS,c)/(K*tau*(1-qS,c))]*grad(ni)
```

따라서 **qS>qT인 chunk는 KD가 그 reference NLL을 올리는 쪽**이다. CE가 항상 원 정답의 NLL을 내리려는 것과 반대일 수 있다. 이는 KL 부호를 잘못 구현해야만 생기는 현상이 아니다. 같은 byte 답이라도 교사가 그 **정확한 native 토큰 경로/표현**에 학생보다 낮은 확률을 주면 정의상 생긴다. 교사의 `not-this-reference` 보완사건에는 틀린 답뿐 아니라 다른 유효 표현/대안 분절도 들어갈 수 있으므로, qT를 문장의 사실성·교사의 지식·정답 가능성 판정기로 읽지 않는다.

특히 q는 원 확률 p가 아니라 **p의1/100제곱**이다. 여기서 τ=100은 학생/교사 전체 어휘 logits에 softmax temperature를 걸고 다시 정규화하는 연산과 다르다. chunk logp 합에 적용하며 token/byte 수로 나눈 평균이 아니다. 따라서 q가1에 가깝다고 원 reference의 확률이나 내용 신뢰도가 거의1이라고 말할 수 없다. τ를 바꾸면 gradient 크기뿐 아니라 위치별 상대 기여도 바뀌므로 일회 norm 교정이 그 효과 전체를 상쇄하는 것도 아니다. τ² 배율은 현재 OFF이고 이번에 추가하지 않았다.

### 21.3 길이·정렬·분모가 같다는 말의 정확한 범위

[frozen_record](/home/uranus/tinyLM/scripts/diag_p106b_alm_train.py:559)는 원 token ID/labels/turn을 유지하고 `raw i→shifted i−1`·연속/비중첩 chunk·동일 turn·특수/EOT 제외를 검사한다. V7은 **답변 내용 byte**를 대응시키며 전체 teacher/student chat template가 동일하다는 계약은 아니다. 두 native tokenizer의 token 수가 달라도 같은 byte chunk의 **각 경로 logp 합**을 비교한다. 이는 모든 가능한 tokenization 경로를 주변화한 정확 byte-string 확률이나 full-vocab 분포의 복원이 아니다.

교정128행(한영 각64)의 실제 분모는 CE N=772, KD K=561이다. 한국어는 CE277/학생 KD213/교사 KD286/212chunk, 영어는 CE495/학생 KD431/교사 KD397/349chunk였다. 답변 내용은 각각818/1570bytes 전부 덮였지만 CE에는 KD에서 뺀128target도 남는다. **byte coverage100%와 CE/KD 목적함수·가중치의 동일성은 다르다.** 행수64:64도 token/chunk/gradient 기여의50:50을 뜻하지 않는다.

| 교정 언어 | 언어 자체 평균 CE norm | 언어 자체 평균 KD norm | cosine | 같은 λ의 weighted KD/CE norm 비 |
|---|---:|---:|---:|---:|
| 한국어 | 6.5444126450 | 0.0299596229 | −0.9891913316 | 0.1662817972 |
| 영어 | 2.5655965525 | 0.0261276914 | −0.9313268489 | 0.3699062912 |

언어별 norm은 **각 언어 자체의 CE/KD 분모로 재정규화한 값**이다. 이 두 norm/cosine을 산술평균해서 전체 교정값을 만들면 안 된다. 두 언어에서 모두 음의 cosine이 관측됐으므로 전체 역방향을 단순히 한영 합산만의 산물이라고 확정할 수도 없다. 어느 chunk/parameter가 얼마나 기여했는지는 이 aggregate만으로 분해되지 않는다.

교정의 `calibrated_signal_summary`는 학생/교사 exp-underflow0·boundary0, 결합 NLL 계수 음수는 **한국어2+영어1=3/561chunk**라고 기록한다. 이는 부호상 실제 반대 신호가 일부 있음을 보이지만 **KD 자체의 부호 건수나 parameter gradient cosine과 같은 통계가 아니다.** 대부분의 결합 계수가 양수여도 KD 성분은 CE를 부분 상쇄할 수 있고 공유 parameter에서 여러 위치의 벡터가 합쳐진다. 이3개만이 −0.97546 cosine의 원인이라고 단정하지 않는다. teacher/student q의 min/max도 짝지어진 순서를 보존하지 않으므로 그것만 보고 대부분의 qS>qT를 주장하지 않는다.

`1/(1-qS)` 때문에 qS가1에 가까운 일부 chunk의 NLL 계수가 커질 수도 있다. 실제 교정 qS 최대는 한국어0.9999989629/영어0.9999960359이고, 실제 첫 학습 update의 영어 결합 NLL 계수 최소는−0.0687984163이었다. 이는 유한한 현재 수식과 양립하며 곧바로 NaN/부호 버그의 증거가 아니다. 반대로 finite/coverage100%만으로 raw teacher 신호의 의미 적합성이나 전체 구현 무오류를 증명한 것도 아니다.

### 21.4 한 교정 표본의 합성 gradient를 계산하면 무엇이 나오는가

교정은 `visit_schedule()`의 마지막 실제 layer13과 참조 MLP/attention의 **중복 제거한 trainable10개 parameter**만 쓴다. FP32 gradient 입력을 누산하고 norm/dot 통계는 FP64로 산출했으며 report의 None count는0, core/RNG 불변·optimizer update0이다. 전체157개 parameter나 head-only gradient가 아니다. Q에서는 이 값도 실제 hard-code 목적함수의 고전적 미분이 아니라 **현재 STE graph/FP32 master 좌표의 surrogate gradient**라는 점을 덧붙여야 한다.

```text
C = ||gC|| = 3.980677255763522
Knorm = ||gK|| = 0.027397941465368846
c = cos(gC,gK) = -0.9754605940151176
dot(gC,gK) = -0.10638603685620292
lambda = rho*C/Knorm, rho=0.25
||gC + lambda*gK||^2 = C^2 + lambda^2*Knorm^2 + 2*lambda*dot(gC,gK)
```

| 위10개 좌표·같은 교정128행에서의 파생값 | CPU scalar 계산 |
|---|---:|
| weighted KD norm λ·Knorm | 0.9951693139 =0.25·C |
| 합성 gradient norm | 3.0178934416 |
| 합성 norm / C | 0.7581356758 |
| CE 축에 대한 합성 projection / C | 0.7561348515 =1+0.25·c |
| 합성 방향과 CE 방향의 cosine | 0.9973608624 |
| CE와 합성 gradient의 내적 | 11.9815551381 >0 |

따라서 **λ가36이라 KD gradient가 CE의36배라는 해석은 틀리다.** 이 교정 범위에서는 weighted norm이 CE의25%다. 강한 역방향이지만 CE를 전부 상쇄/역전한 것도 아니며, 합성 벡터는 CE와 거의 같은 방향이고 norm이 작아졌다. 이는 고정한 두 벡터의 대수적 해석이다. 미분 가능한 같은 그래프의 그 좌표에 한정한 단순 SGD의 1차 CE 성분과 연결할 수는 있지만, **hard 삼진 forward/STE의 실제 손실 하강·모델 전체 update·품질을 보장하지 않는다.**

### 21.5 이것을 실제 유효 학습률/전체 update norm으로 부르면 안 되는 실물 반례

1. **표본과 분모가 다르다.** 교정은 TRAIN의 언어별 첫64행으로 만든 한128행 집합이다. 실제 첫 학습 update는 한국어70/영어58행, N=734/K=533이다. 같은 부모라도 첫 학습 batch 자체가 교정 집합과 다르므로3.017893를 첫 update의 실측 norm으로 쓸 수 없다. λ는32 update 동안 고정되고 task별 norm/cosine은 매 update 재측정·재교정되지 않았다.
2. **전체 parameter의 실측은 반대 크기다.** 같은 초기 core/RNG와 같은 첫 학습 자료에서 report의 **전체157개 preclip norm**은 CE28.1566658020 대 ALM40.1433486938이었다. 교정10개 좌표의0.758배를 전체에도 적용하면 이 관측을 설명하지 못한다. 이것만으로 어느 다른 parameter가 원인인지나 전체 task cosine을 복원할 수는 없다.
3. **두 팔 모두 매 update clip했다.** [기존 one_update](/home/uranus/tinyLM/scripts/diag_p101a_padding_gpu.py:506)는 전체 parameter를 norm1로 clip한 뒤 Adam/Muon을 실행한다. CE32회의 preclip 범위는20.6696758270~33.6651268005, ALM은20.0489673615~49.0161018372였고 모두1보다 컸다. 이때 raw norm 감소율을 그대로 optimizer step 감소율로 읽지 않는다. 다른 block/head의 gradient와 전체 clip 배율도 영향을 준다.
4. **optimizer와 surrogate graph가 남는다.** Muon의 momentum/직교화·RMS scaling, Adam의 상태/사전조건은 단순 Euclidean SGD가 아니다. 공유 embedding/head와 앞 block은 교정10개 집합 밖이다. 한 번의 방향 통계로32회 뒤 파라미터 변화나 DEV CE를 역산할 수 없으며, 삼진 코드의 불연속 변화도 별도다.

특히 위 첫 update의40.14>28.16은 “KD를 더해 전체 gradient가0.758배로 작아져 학습이 느려졌다”는 **확정 설명에 대한 반례**다. 신호 간섭은 현재 결과와 양립하는 가설이지만, 그것이 DEV 격차0.13307을 전부 설명한다고 확정하려면 여기 없는 task별 전체 gradient/update 정보가 필요하다. 이 담당은 이를 얻기 위해 새 GPU 실행이나 gradient 재계산을 요구·수행하지 않았다.

### 21.6 원 논문과 현재 결과가 말하는 것·말하지 않는 것

현재는 [ALM v4 §3/AppE/I](https://arxiv.org/html/2503.20083v4)의 **reference chunk binarized KL core**에 해당하는 의도적 최소형이다. 임의 logp MSE로 바꾼 것은 아니지만 **논문의 전체 학습 레시피·실험 재현은 아니다.** hidden alignment/outcome debias는 OFF이고, §10에서 이미 대조한 논문/공식 tokenkit의 online GradMag도 OFF다. 지금 `lambda=rho*C/Knorm`는 TRAIN-only 일회 교정 후 고정한 변형이며 task weight를 매 단계 갱신·합1 정규화하는 논문 GradMag와 다르다. 이 구분은 이번 음성 결과를 본 뒤 새로 만든 예외가 아니라 실행 전 §10에 기록된 범위다.

동결 원문 답변에 대한 teacher-forced 신호이므로 교사가 새 답/추론을 생성해 전달한 실험도 아니다. 교사가 exact reference를 학생보다 덜 선호하면 CE와 반대일 수 있고, 서로 다른 native template/토큰 경로·정답의 표현 대안·양자화 교사의 확률이 관여할 수 있다. **어느 요인이 이번 결과를 지배했는지는 미확인**이다. raw prefix/logp/정렬 결함도 일반적으로 가능한 별도 감사 항목이지만, 음의 cosine이나 낮은 exact 하나만으로 그 결함이 발견됐다고 보고하지 않는다.

DEV TF CE의 두 팔 모두 개선은 gold history 아래 평균 target 예측이 개선된 관측이다. 그것이 자기 생성 이력에서의 안정성/정답성으로 자동 이어지지 않으며 strict literal exact0과 사용자8개의 반복/오답 유지가 반례로 남는다. 동시에 literal exact는 annotation 문자열의 일치 지표라서 이0만으로 모든 가능한 정답 표현을 의미심사했다고 주장하지 않는다. 기존 평가 report도 `OLD_DEV_STRING_DIAGNOSTIC_NOT_FRESH_TEST_NOT_GENERAL_DIALOGUE_SCORE`로 한정한다.

**현 판정은 해당 Q32 고정 조건에서 ALM 추가 이득이 확인되지 않았고 DEV CE는 CE-only보다 나빴다는 것**이다. 한 seed·짧은 반복·old DEV의 point estimate이며 통계적 유의/전체 ALM 불가능/교사 무능·오답 여부는 결론에 포함하지 않는다. 결과를 맞추기 위한 τ/λ·ρ·chunk/자료 재선택, 논문 GradMag 추가, 신규 모델/GPU 검사는 하지 않았다. F는 자체 실물 결과가 닫힌 뒤 그 부모 안의 CE 대 ALM으로 따로 판단해야 한다.

### 21.7 직접 읽은 영수증과 재계산 식

모든 링크는 Q의 닫힌 report다. source2개와 기존 clip/update helper의 현재 SHA가 report pin과 같음을 확인했으며, CP tensor·실제 답변/교사 원문을 재검산한 것은 아니다.

| Q 닫힌 report | SHA-256 |
|---|---|
| [calibrate](/home/uranus/tinyLM/test_result/evidence/p106b_alm_train_ternary_v1_s1337/calibrate/report.json) | `A5407F989B4D0DD6C8218CB4ED70658351DBBE686CD37DF50184DC074B34BA13` |
| [train_ce](/home/uranus/tinyLM/test_result/evidence/p106b_alm_train_ternary_v1_s1337/train_ce/report.json) | `2B1B4EFF2B4F7BC64CEB63E35A1C32760A24B5980DD52F30B04DC4A346AB4C94` |
| [train_alm](/home/uranus/tinyLM/test_result/evidence/p106b_alm_train_ternary_v1_s1337/train_alm/report.json) | `766F2BF7B540CFBBA150456DB819918F7F18CFD12CFC5997CC83C7F7E1C9FB5D` |
| [evaluate_parent](/home/uranus/tinyLM/test_result/evidence/p106b_alm_train_ternary_v1_s1337/evaluate_parent/report.json) | `6A344507A3AC2DC398A53052325448D43387DDA6B4DD70A9559D286014EE4C92` |
| [evaluate_ce](/home/uranus/tinyLM/test_result/evidence/p106b_alm_train_ternary_v1_s1337/evaluate_ce/report.json) | `AEAB335DAFF99CEEBDA34805FF9AE66EA97B1A70574AD7EB74BB4FA23144BD34` |
| [evaluate_alm](/home/uranus/tinyLM/test_result/evidence/p106b_alm_train_ternary_v1_s1337/evaluate_alm/report.json) | `4205F82430A7D50C47ABC90107A1BE96AB1C469467D06D8DC5295B28FF38CF18` |

수식 소유 파일의 SHA는 `tinylm/train/alm.py=59466D0810237477E4AB06BB2545138887508D168AAAC257D5096E925A7EBAFA`, `scripts/diag_p106b_alm_train.py=C8EFF2B4F84AE31EA66DD55F8EC3F22771E1CCE89FD9EFB992D18F34F103E51E`다. 기존 `scripts/diag_p101a_padding_gpu.py`는 `B3F5B020E5D579380D2511185AD9F94F0F8B430C3AA92FA0C0095D6480487F9A`다. §20의 과거 Core6 source identity와 섞지 않는다.

합성 norm은 저장된 세 scalar와 고정 λ로 다음처럼 복제할 수 있다. 새 모델/torch를 import하지 않는 CPU 산술이며 optimizer update를 재현하는 코드가 아니다.

```python
import json, math
from pathlib import Path
p = Path('/home/uranus/tinyLM/test_result/evidence/p106b_alm_train_ternary_v1_s1337/calibrate/report.json')
r = json.loads(p.read_text(encoding='utf-8'))
g = r['global_stats']
C, K, D, w = g['ce_norm'], g['kd_norm'], g['dot'], r['weight']
combined = math.sqrt(math.fsum((C*C, w*w*K*K, 2*w*D)))
print(dict(weighted_kd_norm=w*K, combined_norm=combined,
           norm_ratio=combined/C, ce_projection_ratio=(C*C+w*D)/(C*C),
           cosine_to_ce=(C*C+w*D)/(C*combined)))
```

이번 변경은 이 문서 새 절뿐이다. 기존 §10/19의 당시 설계·한계와 §20의 원형 감사는 보존했으며, 원 결과·학습 파라미터·캐시·공유 코드·Git·설치·다운로드·외부 상태를 바꾸지 않았다.

## 22. source25375의 bedform 용어 검토: 표면 형상과 내부 층리를 구분

### 22.1 정확한 대상·열람 범위

**이 원문의 bedform을 ‘층리형’이라는 확정 표준어로 승인할 근거는 확인하지 못했다.** 국내 1차 자료에는 `층형(bedform)`, `층면구조(bedform)`, 하천 분야의 `하상형상(Bedform)`이라는 서로 다른 용례가 있다. 따라서 어느 하나를 유일한 공식 표준 번역으로 선언하지 않는다. 이 원문에서는 이동하는 표면의 모양과 그 아래 만들어지는 층리를 구별하는 것이 핵심이다.

총괄이 예시로 지목한 [packet000027](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/non_sft_translation_packets/non_sft_translation_000027.json)의 sources에는 25375가 없다. 정확한 대상은 [packet000026](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/non_sft_translation_packets/non_sft_translation_000026.json)의 `source_id=eos_segment_index=25375` 한 객체다. 이 객체의 `original_english` **2685문자 전체**를 읽었다. 다른 객체의 원문·번역 후보·교사 출력은 읽지 않았다. ‘층리형’이라는 후보 표기는 총괄이 전달한 보고를 검토한 것이며, 실제 후보 문장 전체의 충실도까지 심사한 것은 아니다.

| 식별 항목 | 읽기 전용 확인값 |
|---|---|
| packet000027 SHA-256 / 해당 ID 수 | `42EE796BC6DC0CB3D561EFD9B0E248F193BB42AE18242485F566F20B8ED49F94` / 0 |
| packet000026 SHA-256 / 해당 ID 수 | `1F89421BAE7B53438A142E1776F218289ECCA90CC0D7CEBD611D4F08DFBF4BBF` / 1 |
| 원문 UTF-8 SHA-256 | `A787D706AA102F7849D68EF3E15909F77AC4295915F251CA173DB363032B78A6` — 저장 `source_sha256`와 재계산 일치 |
| 저장 출처·상태 | `source_kind=ORIGINAL_TRAIN_EOS_SEGMENT_FROM_PRIOR_NATIVE_IMPORT`, `source_url=null`, `quality=NOT_VERIFIED`, `training_admission=NOT_ADMITTED` |

원문 제목은 `USGS Bedform Movie Explanation`이고 Rubin의 자료·옛 USGS 링크를 소개하지만, 실습에서 영상을 쓰겠다는 1인칭 해설도 들어 있다. **제목이나 인용 링크만으로 이 단락의 집필자를 USGS/Rubin이라고 확정하지 않는다.** 원 게시 페이지·저자·수집 경로는 이번에 확인되지 않았다.

### 22.2 이 원문에서 가리키는 것

| 원문의 시각적 대상·역할 | 여기서 보존해야 할 의미 구분 |
|---|---|
| 회색 음영의 surface, 일정한 shape를 유지하며 하류 방향과 위쪽으로 이동 | bedform은 이 **퇴적물 표면의 지형적 형상**을 가리킨다. 원문 자체가 bedform과 surface를 연결한다. |
| 표면이 이동하며 남기는 흰 선 laminae, 표면과 만나면 침식되는 부분 | 내부에 남는 얇은 퇴적층과 그 배열이다. 표면 형상 자체와 같은 대상이 아니다. |
| ripple/dune의 직선형·굴곡형 구분, 마지막의 침식·회전 후 cross stratification 관찰 | 표면의 이동으로 생긴 내부 구조를 보고 원래 표면의 모양을 해석한다는 설명이다. |

그러므로 이 맥락에서 ‘층리형’만 쓰면 **층리의 유형/모양**을 뜻하는 것으로 읽혀, 층리를 만들어 가는 표면 형상과 결과인 층리를 섞을 위험이 있다. 이는 이 원문과 후보 단어의 의미 적합성에 관한 판단이지, 해당 단어가 국내 어느 문헌에도 쓰이지 않는다는 부재 증명은 아니다.

### 22.3 국내 1차·공식 자료와 실제 읽은 범위

| 자료·직접 URL | 확인한 국문 용례와 의미 | 증거의 범위·한계 |
|---|---|---|
| 윤석훈·조영진(2019), 지질학회지55(3):277–289, [몬트니층 퇴적상 논문 §5.3.1–5.3.2](https://jgsk.or.kr/_PR/view/index.php?aidx=20291&bidx=1618), [DOI](https://doi.org/10.14770/jgsk.2019.55.3.277) | §5.3.2에서 **‘층형(bedform)’**을 명시한다. 연흔의 이동과 표면 형상이 사엽층리 생성에 관여한다는 설명이며, 같은 절에서 사층리/사엽층리와 층형을 별도로 쓴다. | 학회가 제공하는 HTML의 서지정보와 해당 절을 직접 열람했다. 국문 학술 용례의 직접 증거지만, 이 논문이 용어 표준을 제정한 것은 아니다. 전 절 완독 주장이 아니다. |
| 기원서 등(2007), 지질학회지43(3):311–333, [읍천단층 논문 공식 보관 PDF](https://data.kigam.re.kr/ieg/cmmn/downloadFile.do?fileName=A430304.PDF), [공식 서지 레코드](https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART001187891) | p318 검색색인 발췌에는 **‘층면구조(bedform)’**, 별도로 **‘층형(bed geometry)’**이 나온다. 한 논문에서 확인한 ‘층형’만으로 일대일 유일 대응을 선언할 수 없다는 반례다. | KIGAM 원문 PDF 직접 열기는 도구에서 실패했다. 해당 페이지의 공식 PDF 검색색인 발췌와 공식 서지정보에 한정하며, PDF 본문/도판을 직접 대조한 증거로 승격하지 않는다. |
| 이민재·박용성(2025), 물과미래58(4), p56 시작, [한국수자원학회 공식 목차](https://www.kwra.or.kr/publication/p-magazine/list/Vol.58%20No.4/), [해당 학술기사 PDF](https://www.kwra.or.kr/media/17/publication/2025/03/31/Vol.58_No.4_56.pdf) | p57의 공식 PDF 검색색인은 **‘하상형상(Bedform)’**을 명시하고 높이·길이·형상비를 구분한다. 하천 분야에서 내부 층리가 아니라 바닥의 기하학적 형상을 가리키는 용례다. | 공식 목차는 직접 열람했고, PDF는 약13MB 크기 제한으로 직접 열지 못했다. 용어·p57 문맥은 검색색인 발췌다. 학회 학술기사의 용례이지 국가/학회 용어 표준의 확인은 아니다. |
| Rubin·Carter(2005), [USGS Open-File Report2005-1272 소개](https://pubs.usgs.gov/of/2005/1272/), [USGS 공식 서지정보](https://www.usgs.gov/publications/bedforms-40-matlab-code-simulating-bedforms-and-cross-bedding) | bedform 표면 지형의 생성·이동과 그 아래 cross-bedding 단면의 생성을 따로 설명한다. source25375에서 읽은 회색 표면 대 내부 흰 선의 구분과 부합한다. | 공식 서지 페이지는 직접 열람했다. 보고서 소개의 관련 설명은 공식 페이지 검색색인으로 확인했으며, 소개/PDF 직접 열기는403이었다. 보고서13쪽·모형 코드·영상 전체를 읽거나 실행하지 않았다. 한국어 표준어의 근거로 사용하지 않는다. |

**미확인:** 국가표준·공인 용어집에서 bedform의 단일 권장 번역을 정한 항목은 확보하지 못했다. 위 자료만으로 ‘층형은 항상 맞고 다른 용어는 항상 틀리다’고 결론 내리지 않는다. ‘하상형상’은 하천 문맥의 명확한 용례지만, 일반 퇴적학의 bedform을 모두 하천 바닥으로 제한하는 일괄 치환도 피한다.

### 22.4 선택지와 권고 — 실제 번역 수정은 하지 않음

| 선택 | 장점·위험 | 이번 권고 |
|---|---|---|
| 기존 ‘층리형’ 유지 | 수정은 없으나 표면과 내부 층리의 구별이 불명확하고 표준어라고 승인할 직접 근거가 없다. | 확정 표준 번역으로 승인하지 않는다. |
| 근거가 있는 국문 용례+원어 병기 | 일반 퇴적학 문맥의 `층형(bedform)`은 직접 읽은 학회 논문에 근거한다. 하천 문맥이면 `하상형상(bedform)`의 분야 용례도 있다. 다만 서로 다른 대상을 가리키는 국문 용례가 있어 문장별 의미 확인이 필요하다. | 전문 용어를 국문화한다면 검토 가능한 후보다. 임의 동의어 일괄 교체나 유일 표준 선언은 하지 않는다. |
| `bedform`을 보존하고 원문 안의 surface/shape 설명으로 대상을 명확히 하기 | 미확인 표준어를 단정하지 않으면서 원어 대응과 표면/층리 구분을 남긴다. 원어가 남는다는 비용이 있다. | **표준성 불확실성이 남는 현재에는 가장 보수적인 권고다.** 예컨대 검토 주석에서는 ‘이 원문의 bedform은 회색 음영으로 표시되어 이동하는 퇴적물 표면의 형상’이라고 설명할 수 있다. |

마지막 설명은 **검토 주석의 의미 해설**이지 실제 번역 본문에 추가하라는 지시나 반영된 번역문이 아니다. 원문에도 있는 표면·이동·층리의 관계를 번역에서 충실히 드러내는 것과, 외부 자료의 유동식/형성환경/새 사실을 본문에 몰래 덧붙이는 것은 구분한다. 원문의 저서·연도·옛 브라우저 플러그인 서술을 최신 사실로 고치거나 보강하는 작업도 하지 않았다.

이번 수행은 정확 ID의 원문 읽기·작은 JSON 식별/해시 확인·공식 웹 문헌 검토와 **이 절 추가**뿐이다. 원문·후보·교사·코드·데이터 상태는 수정하지 않았고, 모델/GPU·추가 생성·학습·설치·Git은0이다. 용어 한 건 검토가 source25375 전체의 의미 검증이나 학습 투입 승인을 대신하지 않으며, 저장된 `NOT_VERIFIED/NOT_ADMITTED` 상태도 그대로다.

## 23. source25123의 emergent macrophytes: 정수식물이라는 생활형을 보존

### 23.1 정확한 원문과 원출처 대조 범위

**이 문맥의 ‘정수식물’은 공식 용어 정의와 국내 학술 용례에 부합한다.** 원어 구성까지 드러내려는 ‘정수성 대형수생식물’도 의미상 타당한 후보지만, 그 긴 표현을 유일하게 확정된 표준어라고 선언하지 않는다. 특히 정수라는 말은 여기서 **수면 위로 지상부가 나오는 식물의 생활형**을 뜻하며, 물이 정체된 환경이나 창발적 성질을 뜻하는 말로 바꾸면 안 된다.

먼저 [packet000026](/home/uranus/tinyLM/data_cache/p106b_text_work_20261022/non_sft_translation_packets/non_sft_translation_000026.json)의 `source_id=eos_segment_index=25123` 객체만 골라 `original_english` **2414문자 전체**를 읽었다. 번역 후보·다른 객체의 원문·교사 출력은 열지 않았다. packet SHA-256은 §22와 같은 `1F89421BAE7B53438A142E1776F218289ECCA90CC0D7CEBD611D4F08DFBF4BBF`이고, 해당 원문 UTF-8 SHA-256의 재계산값은 저장값 `C9971AC20676F3873B496361C49B79E8E4AF1EBE9C9E0496EE86C47CEFC86125`와 일치한다. 정확 ID의 객체는1개다.

원문은 Gulis·Su·Kuehn(2019), **Fungal Decomposers in Freshwater Environments**, 책의 pp121–155에 해당하는 **초록**이다. [출판사 DOI 페이지](https://link.springer.com/chapter/10.1007/978-3-030-16775-2_5)의 제목·저자·최초 공개2019-05-14와 공개 초록 전체, [저자 소속 대학의 별도 레코드16420](https://aquila.usm.edu/fac_pubs/16420/)의 초록·서지정보를 직접 읽었다. 원문의 두 용어 출현 및 탄소손실 수치·생태계 대비가 이 초록들과 일치함을 대조했다. **유료 본문35쪽이나 그 수치의 개별 실험 원논문까지 읽은 것은 아니다.**

출처 관련 별도 관측: 저장 필드 `source_url`은 `null`이지만, 원문 끝에는 [대학 레코드16889](https://aquila.usm.edu/fac_pubs/16889/)가 제시되어 있다. 그 페이지는 같은 초록을 보여 주면서 끝에 **자료가 철회되었다는 문구**도 표시한다. 표시의 이유나 적용 범위는 이번에 확인되지 않았다. 별도16420과 출판사 페이지가 존재한다는 사실을 함께 기록하며, **이 레코드 표시만으로 출판된 장 자체가 연구부정 등으로 철회됐다고 확정하지 않는다.** 원 출처 필드·교재·학습 허용 상태를 이 담당이 고치거나 갱신하지 않았다.

### 23.2 국문 용례·정의의 1차/공식 근거

| 직접 URL·확인 범위 | 확인한 내용 | 이 검토에서의 한계 |
|---|---|---|
| [국립국어원 온용어의 정수식물 항목2445079](https://kli.korean.go.kr/term/trgtWord/indexTrgtWord.do?trgtWordNo=2445079), 표제·정의·자료 설명 직접 열람 | 얕은 물의 바닥에 뿌리를 두고 줄기·잎의 대부분이 물 위로 나오는 식물을 가리킨다. 페이지는 출처를 우리말샘으로, 수록 자료를2023-06 기준 전문 용어로 설명한다. | ‘정수식물’이라는 국문 용어와 의미를 뒷받침한다. 영어 복합어 전체의 유일 공식 번역을 정한 항목이나 별도 국가표준 제정 사실로 확대하지 않는다. |
| 이철호 등(2019), 응용생태공학회 논문집6(4):267–276, [공검지 식생 조사 논문](https://www.jeri.or.kr/articles/xml/W51A/), [DOI](https://doi.org/10.17820/eri.2019.6.4.267); 국·영문 초록·§3.3·§4.1 직접 열람 | 영문 초록의 수면 위로 나온 식생과 국문 초록의 정수식물이 대응한다. 실제 조사에서 정수식물·침수식물·부엽식물·습생식물을 구분한다. | 국내 현장 연구에서 쓰는 생활형 구분의 직접 근거다. 이 논문은 곰팡이 분해율이나 source25123의 탄소손실 수치를 검증한 연구가 아니다. |
| [국립생태원 공식 습지식물 자료 PDF의 유형 분류표](https://www.nie.re.kr/nie/cmmn/file/fileDown.do?atchFileId=6399676c89184992aa032d1ecf1ac112&fileSn=1), ‘습지식물 유형과 수생형 분류’ 표2 검색색인 | 국문 ‘수생식물-정수식물’과 영문 `Aquatic emergent macrophyte`를 직접 대응시키며, 바닥에 뿌리가 고정되고 지상부가 공기 중에 노출되는 유형으로 설명한다. | 공식 PDF 검색색인에 나타난 해당 표만 확인했다. 약66.6MB의 PDF 직접 열기는 도구 크기 제한으로 실패했으므로, 발간물 전체·본문 페이지를 읽었다고 하지 않는다. |

세 근거는 **정수라는 생활형을 보존해야 한다는 점**에서 일치한다. 반면 ‘정수성 대형수생식물’이라는 결합 표현 자체가 단일 표준 번역이라는 직접 인증은 확보하지 못했다. ‘대형’이라는 말을 이유로 원문에 없는 구체 크기 기준이나 종 목록을 덧붙이지 않으며, 모든 수생식물/습지식물 또는 물에 뜨는 식물 전체로 의미를 넓히지도 않는다.

### 23.3 용어를 바꾸더라도 유지해야 할 원문 범위

| 원문에서 읽은 대상·한정 | 후행 검토에서 보존할 조건 |
|---|---|
| 첫 출현: 잎·목재와 함께 분해 대상인 식물 유기물의 사례로 제시 | 살아 있는 식물을 곰팡이가 모두 직접 분해한다거나 모든 담수 유기물 분해의 보편적 법칙으로 확대하지 않는다. 원문이 다루는 식물 잔해·곰팡이 중심의 문맥을 유지한다. |
| 두 번째 출현: `standing-dead emergent macrophyte systems in wetlands` | **서 있는 채로 고사한 정수식물**이라는 조건과 습지의 해당 시스템이라는 범위를 보존한다. 단순히 ‘죽은 수생식물’, 바닥에 누운 낙엽, 모든 살아 있는 정수식물로 바꾸면 정보가 달라진다. |
| 하천 낙엽 탄소손실23–60%의 일부 추정: 곰팡이 동화, 즉 생산+호흡 | 총 습지 탄소손실이나 곰팡이 생물량 비율로 바꾸지 않는다. 그 추정에는 곰팡이가 매개한 미세입자·용존 유기탄소 손실을 포함하지 않는다는 한정을 유지한다. |
| 습지의 서서 고사한 정수식물 시스템에서의 기여 추정47–65% | 일부 추정이 더 높을 수 있다는 진술이지 모든 습지의 고정 비율이 아니다. 앞 범위와 수치가 겹치므로 모든 경우에 반드시 더 높다고 재표현하지 않는다. |
| 하천·강·담수 습지, 흐르는 계와 고인 계, 마지막의 하천 대 담수 습지 차이 | 용어 ‘정수’를 근거로 글 전체를 고인 물/호수만의 생태계로 축소하지 않는다. 곰팡이 군집·동태의 차이가 있다는 마지막 대비도 지우지 않는다. |

위는 공개 초록의 한정을 지키기 위한 **번역 의미 감사 조건**이다. 해당 기여율을 이 담당이 독립 실험/계산으로 재검증했다는 뜻이 아니며, 장 본문을 읽지 않고 어떤 종·습지·기간의 측정값인지 새로 특정하지 않는다.

### 23.4 권고와 미확인

이 원문에서는 **‘정수식물’이 가장 직접적인 국문 용례를 갖는 간결한 후보**다. `macrophyte`의 범주를 더 명시하려면 첫 출현을 ‘정수성 대형수생식물’로 설명하고 원어를 병기하는 선택도 가능하다. 원어를 남기는 보수적 선택도 열어 두되, 같은 문단에서 같은 대상을 지칭하는 두 출현을 임의 동의어로 다르게 바꾸지 않는 것이 중요하다. 어떤 선택도 유일한 정답이나 이미 반영된 수정으로 보고하지 않는다.

특히 뒤의 표현은 필요 시 검토 주석에서 **‘서 있는 채로 고사한 정수식물의 계’**처럼 구성 의미를 설명할 수 있지만, 이는 확정 번역문이나 본문에 외부 설명을 추가하라는 지시가 아니다. 실제 문장에서는 원문의 습지·추정·탄소손실 한정까지 함께 유지되어야 한다. 산림청/국립국어원 등의 외부 정의나 갈대·부들 같은 예시를 원문에 없는 본문 내용으로 몰래 삽입하지 않는다.

이 담당은 이번에 원문·후보·교사·코드·공유 정본·교육 상태를 수정하지 않았다. 저장된 `quality=NOT_VERIFIED`, `training_admission=NOT_ADMITTED`는 그대로이며, 이 용어 검토만으로 전체 문장의 의미 검증이나 학습 투입 승인을 대신하지 않는다. 수행은 정확 객체의 읽기·해시 확인·공식 웹 자료 열람과 **소유 문서의 새 절 작성**뿐이고, 모델/GPU·생성·학습·설치·Git은0이다.
