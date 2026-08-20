# TinyLM × Qwen/Gemma Teacher Distillation
# Embedding Rank / Input-Output Tying 실험 검토 요청서
#
# 목적:
# 아래 실험계획을 그대로 확정하지 말고, Claude가 반드시 실제 TinyLM 소스코드와
# 현재 관련 실험 결과를 직접 확인한 뒤, 기술적으로 타당한지 검토하고
# 상충되는 부분이나 잘못된 가정을 찾아 수정안을 제시하도록 한다.
#
# 중요:
# 이 문서는 현재 대화에서 논의한 내용을 기반으로 작성한 "검토 요청 초안"이다.
# 아래의 구조/수치/실험조건은 확정사항이 아니라 검증 대상 가설로 취급한다.

---

# 0. Claude에게 먼저 요구하는 검증 사항

아래 실험계획을 실행하거나 확정하기 전에 반드시 다음을 직접 확인한다.

## A. 실제 TinyLM 코드 검증

특히 `tinylm/` 내부를 중심으로 다음을 실제 코드에서 추적한다.

1. tokenizer 생성/로드
2. tokenizer vocabulary size
3. tokenizer가 학습되는 시점
4. tokenizer cache 생성 및 재사용
5. raw text → token IDs → train.bin/val.bin 흐름
6. token ID 저장 dtype
7. model config의 vocab_size 전달 방식
8. embedding 구현
9. emb_rank의 실제 동작
10. emb_up의 실제 역할과 forward 경로
11. input embedding과 output embedding의 실제 weight tying 여부
12. tied/untied 시 실제 parameter 및 memory 변화
13. output logits 계산 방식
14. quantization/ternary 관련 embedding 구현 여부
15. training dtype
16. inference dtype
17. checkpoint 저장 방식
18. optimizer state의 dtype 및 memory
19. m100의 실제 parameter count
20. m100의 실제 runtime resident memory

가능하면 단순 파일 읽기만 하지 말고,
실제 코드 경로를 따라 변수/텐서 shape와 dtype이 어디서 결정되고
어디까지 전달되는지 확인한다.

---

# 1. 연구 목표

이번 실험에서 검증하고 싶은 핵심 질문은 다음과 같다.

> Qwen3.5-0.8B 또는 Gemma 4 E2B의 pretrained tokenizer/vocabulary space를
> 그대로 유지하면서, 약 100M-parameter급 TinyLM student가
> embedding rank를 얼마나 축소할 수 있는가?
>
> 그리고 input/output embedding을 tied로 유지하는 대신 분리했을 때,
> 작은 embedding rank로 인해 발생하는 capability 손실을 회복할 수 있는가?

핵심 연구축:

    Teacher / tokenizer
            ×
    Embedding rank
            ×
    Input/Output embedding tying

이번 단계에서는 tokenizer vocabulary 자체를 축소하거나
tokenizer distillation을 하지 않는다.

즉 Qwen/Gemma tokenizer를 도입하는 조건에서는
원본 tokenizer와 token ID mapping을 그대로 사용하는 것을 기본으로 한다.

---

# 2. 이번 단계에서 포함하는 것 / 제외하는 것

## 포함

### Teacher

- Qwen3.5-0.8B
- Gemma 4 E2B

### Student tokenizer

- Qwen teacher 조건 → Qwen tokenizer
- Gemma teacher 조건 → Gemma tokenizer
- 기존 TinyLM baseline → TinyLM tokenizer

### Student embedding rank

- 256
- 128
- 64

### Input/output embedding

- tied
- untied

### Teacher-student training

동일 tokenizer를 쓰는 조건이므로 가능한 경우:

- hard CE / sequence target loss
- teacher logits 기반 KD
- 필요하면 hidden-state KD

를 검토한다.

단, 실제 TinyLM training code가 이를 제대로 지원하는지는
Claude가 실제 코드 기준으로 판단한다.

---

## 제외

이번 단계에서는 다음을 섞지 않는다.

- Qwen/Gemma tokenizer vocabulary pruning
- 248K → 32K tokenizer distillation
- tokenizer 자체의 neural/end-to-end 학습
- tokenizer merge table 재학습
- embedding INT8
- embedding ternary
- BF16/FP32 dtype ablation
- nonlinear embedding decoder (GELU/SwiGLU 등)
- residual embedding compression
- Tensor decomposition
- adaptive input embedding
- Offline distillation / teacher output pre-generation 및 저장

이번 단계의 teacher-student 학습은 기본적으로
**online distillation**을 전제로 한다.

---

# 3. 1차 실험의 기본 원칙

각 조건은 가능한 한 동일한 training protocol로 독립 학습한다.

다음 항목은 가능한 한 고정한다.

- raw corpus
- validation corpus
- raw-text exposure
- sequence length
- optimizer
- learning-rate schedule
- batch size
- training budget
- seed policy
- checkpoint selection policy

단, tokenizer가 달라지면 token count가 달라질 수 있으므로
"동일 token count"와 "동일 raw-text exposure"의 차이를 반드시 검토한다.

현재 사용 중인 관련 실험에서 training budget을 어떻게 정의했는지 확인하고,
그 기준과 충돌하지 않게 조정한다.

---

# 4. Qwen teacher 조건

## Q256-T

    Teacher:
        Qwen3.5-0.8B

    Teacher tokenizer:
        Qwen

    Student tokenizer:
        동일 Qwen tokenizer

    Student:
        TinyLM
        r_in  = 256
        r_out = 256
        tied

---

## Q128-T

    Teacher:
        Qwen3.5-0.8B

    Teacher tokenizer:
        Qwen

    Student tokenizer:
        동일 Qwen tokenizer

    Student:
        TinyLM
        r_in  = 128
        r_out = 128
        tied

---

## Q64-T

    Teacher:
        Qwen3.5-0.8B

    Teacher tokenizer:
        Qwen

    Student tokenizer:
        동일 Qwen tokenizer

    Student:
        TinyLM
        r_in  = 64
        r_out = 64
        tied

---

## Q64/128-U

    Teacher:
        Qwen3.5-0.8B

    Teacher tokenizer:
        Qwen

    Student tokenizer:
        동일 Qwen tokenizer

    Student:
        TinyLM
        r_in  = 64
        r_out = 128
        untied

목적:

    Q64-T
        vs
    Q64/128-U

를 비교하여 rank reduction에 따른 성능 손실이
input representation bottleneck 때문인지,
output vocabulary representation bottleneck 때문인지 확인한다.

---

# 5. Gemma teacher 조건

## G256-T

    Teacher:
        Gemma 4 E2B

    Teacher tokenizer:
        Gemma

    Student tokenizer:
        동일 Gemma tokenizer

    Student:
        TinyLM
        r_in  = 256
        r_out = 256
        tied

---

## G128-T

    Teacher:
        Gemma 4 E2B

    Teacher tokenizer:
        Gemma

    Student tokenizer:
        동일 Gemma tokenizer

    Student:
        TinyLM
        r_in  = 128
        r_out = 128
        tied

---

## G64-T

    Teacher:
        Gemma 4 E2B

    Teacher tokenizer:
        Gemma

    Student tokenizer:
        동일 Gemma tokenizer

    Student:
        TinyLM
        r_in  = 64
        r_out = 64
        tied

---

## G64/128-U

    Teacher:
        Gemma 4 E2B

    Teacher tokenizer:
        Gemma

    Student tokenizer:
        동일 Gemma tokenizer

    Student:
        TinyLM
        r_in  = 64
        r_out = 128
        untied

---

# 6. 기존 TinyLM baseline

## T0

    Teacher:
        none
        (현재 TinyLM training 방식)

    Student tokenizer:
        TinyLM 자체 tokenizer

    Student:
        현재 baseline configuration

가능하다면 기존에 동일 조건으로 확보된 checkpoint/result를 사용하고,
기존 결과가 없는 경우에만 새 baseline을 학습한다.

---

# 7. 1차 실험 matrix

최소 matrix:

    T0
    Q256-T
    Q128-T
    Q64-T
    Q64/128-U
    G256-T
    G128-T
    G64-T
    G64/128-U

총 9개 조건을 기본 후보로 한다.

단, 실제 코드와 현재 관련 실험 결과를 검토한 후
Claude가 이 matrix에 문제가 있다고 판단하면
조건을 추가/삭제/변경한다.

---

# 8. 각 조건은 독립적으로 학습

다음 방식은 기본적으로 사용하지 않는다.

    Q256
      ↓
    Q128
      ↓
    Q64

각 조건은 동일한 initialization/training protocol에서
독립적으로 학습하는 것을 기본으로 한다.

기존 checkpoint에서 rank만 변경하여 이어 학습하는 경우에는
그것을 별도의 warm-start ablation으로 취급한다.

---

# 9. Teacher-student loss

같은 tokenizer를 쓰는 경우 teacher와 student가
동일 vocabulary space를 가지므로 logit-level KD가 가능한지 검토한다.

기본 후보:

    L = α * L_CE + β * L_KD

예:

    P_T = softmax(z_T / T)
    P_S = softmax(z_S / T)

    L_KD = T² * KL(P_T || P_S)

기본 학습 방식은 **online distillation**이다.

    batch
      ↓
    teacher forward
      ↓
    student forward
      ↓
    CE + KD loss
      ↓
    backward

단, 실제 구현에서는 다음을 반드시 확인한다.

- teacher logits의 실제 shape
- student logits의 실제 shape
- teacher/student token alignment
- teacher inference 비용
- teacher를 매 batch forward하는 데 필요한 memory
- teacher와 student를 동시에 resident로 유지할 수 있는지
- teacher inference와 student training의 device 배치
- 기존 TinyLM training loop와의 통합 난이도
- gradient가 teacher로 전달되지 않도록 올바르게 처리하는지
- teacher를 `eval()` / `no_grad()` 등 적절한 방식으로 실행하는지
- teacher forward 때문에 training throughput이 지나치게 낮아지는지

특히 **teacher output을 미리 생성해서 저장한 뒤 student만 학습하는 offline distillation은
이번 실험 범위에서 사용하지 않는다.**

---

# 10. Teacher tokenizer = Student tokenizer

이번 1차 실험에서는 같은 tokenizer를 유지하는 것이 기본이다.

예:

    Qwen teacher
       ↓
    Qwen tokenizer
       ↓
    teacher tokens

    student
       ↓
    Qwen tokenizer
       ↓
    same token ID space

이렇게 하면 teacher logits와 student logits를
같은 vocabulary coordinate에서 비교할 수 있다.

Gemma도 동일하다.

반대로 tokenizer가 다른 경우의 sequence-level KD / cross-tokenizer KD는
이번 1차 실험의 범위에서 제외한다.

---

# 11. Tokenizer 자체는 이번 단계에서 압축하지 않는다

다음은 이번 단계에서 하지 않는다.

    Qwen 248K
       ↓
    pruning
       ↓
    smaller tokenizer

또는

    Qwen 248K
       ↓
    tokenizer distillation
       ↓
    32K tokenizer

Gemma도 동일하다.

이번 단계에서는 tokenizer의 vocabulary와 token ID mapping을
가능한 한 그대로 유지한다.

---

# 12. Input/output tying에 대한 핵심 연구 질문

현재 TinyLM이 실제로 tied embedding 구조라면
다음 비교가 핵심이다.

    Q64-T:
        r_in  = 64
        r_out = 64
        tied

        vs

    Q64/128-U:
        r_in  = 64
        r_out = 128
        untied

Gemma에서도 동일하게 비교한다.

가설:

> 작은 input embedding rank 자체보다,
> input/output tying 때문에 output vocabulary representation까지
> 같은 작은 rank로 제한되는 것이 성능 병목일 수 있다.

이 가설은 실제 구현의 logits path를 검증한 뒤 확정한다.

---

# 13. `emb_up` 관련 가설도 검증 대상

현재 구조에서:

    token
      ↓
    E(V × r)
      ↓
    emb_up(r → d)
      ↓
    Transformer

라고 가정하고 있다.

단순히:

    r=64
    emb_up: 64 → 2048

처럼 output dimension만 늘리는 것은
입력 bottleneck을 근본적으로 해결하지 않을 가능성이 높다.

왜냐하면 단순 선형 구조에서는
rank가 `r`에 의해 제한될 수 있기 때문이다.

따라서 "emb_up을 키우는 것만으로 rank 감소를 복구한다"는 가설은
실제 코드와 수학적 구조를 확인한 뒤 독립 실험으로 판단한다.

---

# 14. Memory 측정 원칙

parameter count와 memory resident를 절대로 섞지 않는다.

별도의 metric으로 기록한다.

## Parameter metrics

- total trainable parameters
- unique parameters
- embedding parameters
- output embedding parameters
- Transformer parameters

## Memory metrics

- tokenizer artifact size on disk
- tokenizer runtime RSS
- input embedding allocated memory
- output embedding allocated memory
- emb_up memory
- full student runtime resident
- teacher runtime resident
- peak training resident
- peak inference resident
- checkpoint file size

가능하면 actual measurement을 사용한다.

단순:

    number_of_parameters × dtype_bytes

계산은 theoretical lower-bound/reference로 별도 기록한다.

---

# 15. Tokenizer와 model memory를 구분

Tokenizer 파일 크기와 tokenizer runtime RSS를 혼동하지 않는다.

예:

    tokenizer.json size
        ≠
    tokenizer runtime memory

또한:

    embedding parameter count
        ≠
    embedding resident memory

이다.

quantized embedding의 경우에는:

    packed weight
    + scale/zero-point metadata
    + temporary dequantization buffer
    + kernel workspace

등이 있을 수 있으므로
실제 inference resident를 측정한다.

---

# 16. Tokenizer 관련 검증

현재 TinyLM tokenizer가 실제로 어떤 방식으로 만들어지고,
학습 데이터에서 어떤 방식으로 vocabulary가 생성되는지
Claude가 실제 코드를 확인한다.

확인 대상:

- tokenizer algorithm
- tokenizer training sample size
- tokenizer training corpus
- vocab size
- special tokens
- cache path
- cache invalidation
- tokenizer artifact versioning

또한 Qwen/Gemma 도입 시:

- tokenizer class
- vocabulary size
- special tokens
- token ID mapping
- padding behavior
- BOS/EOS behavior
- chat template의 필요 여부
- raw text pretraining에 chat template가 필요한지 여부

를 확인한다.

---

# 17. 중요한 distillation data 검증

Qwen/Gemma teacher tokenizer와 student tokenizer가 같더라도
teacher와 student의 tokenizer configuration이 완전히 동일하지 않을 수 있다.

따라서:

- BOS
- EOS
- PAD
- special tokens
- normalization
- byte fallback
- added tokens

등을 확인한다.

특히 chat/instruct model을 teacher로 사용하는 경우
raw LM pretraining data에 chat template를 적용할지 여부가
teacher behavior에 큰 영향을 줄 수 있으므로 확인한다.

Teacher가 base model인지 instruct model인지도
실제 실험 목적에 맞게 명확히 한다.

---

# 18. Training budget

현재 사용 중인 관련 실험에서 training budget definition을
반드시 먼저 확인한다.

특히:

- total raw tokens
- total tokenizer tokens
- pool tokens
- sequence count
- optimizer steps

중 무엇을 primary budget으로 삼았는지 확인한다.

Tokenizer가 Qwen/Gemma로 달라지면
동일 raw corpus라도 token count가 달라질 수 있으므로
현재 실험 정의와 충돌하는지 평가한다.

가능하면:

    동일 raw-text exposure
    +
    produced-token count 기록

을 동시에 유지한다.

---

# 19. 평가 metric

## Student capability

- validation loss
- perplexity
- bits-per-byte / bits-per-character
- Korean subset loss
- English subset loss
- 필요 시 downstream task

## Distillation

- teacher/student CE gap
- KL divergence
- top-1 token agreement
- top-k agreement
- teacher generated sequence reproduction

## Tokenizer

- bytes/token
- tokens/byte
- tokens/character
- Korean segmentation efficiency
- English segmentation efficiency
- vocabulary utilization
- token frequency distribution

## Runtime

- tokenizer latency
- tokens/sec
- student prefill latency
- student decode latency
- peak RAM/VRAM
- resident memory

---

# 20. 결과 해석 기준

## Case A

    Q256 ≈ Q128 ≈ Q64

이면:

> large pretrained vocabulary를 유지하면서
> embedding rank를 상당히 줄여도
> teacher knowledge transfer가 유지될 가능성

을 검토한다.

---

## Case B

    Q64 << Q128

이면:

> rank bottleneck이 capability bottleneck일 가능성

을 검토한다.

그 이후 nonlinear decoder 연구를 진행한다.

---

## Case C

    Q64/128-U >> Q64-T

이면:

> output-side rank limitation 또는 input/output tying이
> 성능 손실의 중요한 원인일 가능성

을 검토한다.

---

## Case D

    Q64/128-U ≈ Q64-T

이면:

> untied output capacity의 추가 비용 대비 benefit이 작다.

따라서 tied architecture 유지가 합리적인지 평가한다.

---

# 21. 후속 연구 후보

이번 1차 matrix의 결과에 따라 다음 단계에서 하나씩 추가한다.

## A. Nonlinear embedding decoder

    r=64
      ↓
    Linear
      ↓
    GELU
      ↓
    Linear
      ↓
    dim

또는:

    r=64
      ↓
    SwiGLU
      ↓
    dim

## B. Residual decoder

    low-rank embedding
       ├────────────→ skip
       ↓
    nonlinear decoder
       ↓
      add

## C. Quantization

best architecture에 대해:

    FP32
    BF16
    INT8
    ternary

비교.

## D. Tokenizer compression

마지막 단계에서:

    Qwen/Gemma original tokenizer
          ↓
    vocabulary pruning/distillation
          ↓
    smaller tokenizer

를 별도 실험한다.

---

# 22. Claude에게 최종 검토 결과로 요구할 것

위의 9개 조건을 그대로 승인하지 말고,
실제 TinyLM 코드와 현재 관련 실험 결과를 기반으로 다음을 최종적으로 제시한다.

1. 현재 문서에서 실제 코드와 다른 주장
2. 실험적으로 잘못된 조건
3. 누락된 confound
4. 실제 구현에 필요한 파일/함수 변경
5. teacher distillation을 TinyLM에 넣는 가장 현실적인 방법
6. 수정된 최종 experiment matrix
7. 각 조건별 parameter count 계산
8. 각 조건별 memory 계산 및 실제 측정 방법
9. checkpoint naming / metadata 제안
10. 학습 순서 및 validation protocol
11. 어떤 결과가 나오면 다음 단계로 넘어갈지에 대한 decision rule

특히 실제 코드에서 확인되지 않은 내용은 추측으로 확정하지 말고,
"확인 필요"라고 명시한다.

이 문서의 목적은 실험계획을 그대로 실행하는 것이 아니라,
**실제 TinyLM 코드와 현재 관련 실험을 기준으로 계획의 타당성을 먼저 검증하고
상충/오류/누락을 수정하는 것**이다.