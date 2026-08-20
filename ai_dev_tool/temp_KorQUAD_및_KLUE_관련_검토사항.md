# KLUE / KorQuAD 평가 설계 수정 제안

현재 평가 설계의 핵심 방향은 타당하다. 다만 학술적으로 더 정확하게 만들기 위해 아래 사항을 수정한다.

## 1. 가장 중요한 전제 수정

현재 문서의

> EM/F1로 채점하면 안 된다

라는 표현은 너무 강하다.

다음과 같이 수정한다.

> **현재 TinyLM은 100M급 base LM이며 SFT/instruction tuning을 수행하지 않았으므로, 생성형 QA를 통한 공식 EM/F1을 primary evaluation으로 사용하는 것은 현재 연구 목적에 적합하지 않다.**

EM/F1 자체가 잘못된 metric은 아니다.

- KorQuAD의 공식 QA 평가는 EM/F1이다.
- KLUE-MRC 역시 공식 task metric을 사용하는 것이 원칙이다.
- 다만 SFT가 없는 base LM에 질문→답변 생성 형식으로 바로 적용하면 QA 능력과 instruction-following/generation 능력이 혼합된다.
- 따라서 현재 구조/압축 비교 실험에서는 **likelihood-based auxiliary evaluation**을 별도로 설계한다.

즉:

    공식 benchmark evaluation
        → 공식 task formulation + 공식 metric

    현재 TinyLM 구조 비교
        → SFT-free base LM에 적합한 likelihood-based diagnostic

둘을 명시적으로 구분한다.


## 2. YNAT 평가 방식 수정

현재 문서의:

> YNAT → 라벨 우도 argmax → 정확도

는 방법 자체는 가능하지만, **공식 KLUE metric과 구분해야 한다.**

KLUE YNAT의 공식 평가 metric은 **Macro-F1**이다.

따라서 현재 실험에서는 다음과 같이 명명한다.

### Auxiliary metric

각 입력에 대해 후보 label 문자열의 normalized conditional log-likelihood를 계산한다.

예:

    context
    +
    label 후보:
    사회
    경제
    생활문화
    세계
    스포츠
    정치
    IT과학

각 후보에 대해:

    mean log P(label tokens | context)

또는 token-normalized CE를 계산하고 argmax를 선택한다.

그 결과:

    YNAT label-likelihood prediction accuracy

를 계산한다.

이것은 **공식 KLUE YNAT Macro-F1이 아니라 auxiliary likelihood metric**이라고 명시한다.

### 주의

label 문자열 길이가 다르므로 단순 sequence log-probability의 합을 사용하면 긴 문자열이 불리할 수 있다.

따라서:

    normalized / mean token log-likelihood

를 사용한다.

단, 이것은 완전히 편향 없는 semantic classification metric은 아니다.

모델의 일반 corpus에서의 label 문자열 빈도 등 lexical prior가 반영될 수 있으므로, 다음과 같이 정의한다.

> **candidate-string conditional likelihood test**

즉 "의미론적 분류 능력"이라고 과도하게 해석하지 않는다.


## 3. NLI 평가 방식

NLI는 세 가지 label을 후보 문자열로 놓고 동일하게 conditional likelihood를 비교한다.

    entailment / neutral / contradiction

한국어 dataset이라면 실제 label serialization은 dataset 형식에 맞춰 고정한다.

결과:

    NLI label-likelihood prediction accuracy

를 기록한다.

NLI의 공식 metric인 Accuracy와 혼동하지 않도록, **현재 실험의 결과는 auxiliary metric이라는 점을 로그와 문서에 명시한다.**


## 4. KorQuAD answer CE는 유지하되 이름과 해석을 수정

현재 제안한:

    context + question + answer:
        ↓
    gold answer token conditional CE

방식은 **유효한 LM diagnostic**이다.

다만 이를:

> KorQuAD 성능

또는

> KorQuAD F1 대체 점수

라고 부르면 안 된다.

권장 명칭:

> **KorQuAD-derived conditional answer likelihood**

또는

> **KorQuAD gold-answer conditional CE**

정도로 정의한다.

수식:

    CE(answer | context, question)
    =
    -1/T * Σ log P(answer_t | context, question, answer_<t)

이 metric은 다음을 측정한다.

> 해당 benchmark 예제에서 gold answer 문자열이 context + question 조건에서 얼마나 높은 conditional probability를 가지는가.

즉 실제 QA task의 다음 능력을 직접 측정한다고 주장하지 않는다.

    문서를 읽음
    → 질문을 이해함
    → answer span을 찾음
    → answer를 정확하게 추출함

대신:

    context + question
            ↓
    gold answer의 conditional predictability

를 측정한다.

따라서 이것은 **QA benchmark score가 아니라 LM diagnostic**이다.


## 5. KorQuAD CE의 중요한 한계 명시

gold answer CE가 낮다고 해서 모델이 반드시 지문을 읽고 정답을 찾아냈다는 의미는 아니다.

예를 들어 모델이 일반 corpus에서:

    대한민국 ↔ 서울

의 강한 통계적 연관성을 학습한 경우,

context의 실제 reasoning/answer extraction 없이도 gold answer에 높은 probability를 줄 수 있다.

따라서 이 metric은 다음과 같이 해석한다.

> **benchmark example의 gold answer conditional predictability**

이지,

> **실제 QA 수행 능력**

이 아니다.

이 한계를 평가 설계에 명시한다.


## 6. Paired evaluation은 유지하고 핵심 원칙으로 강화

모델 비교에서는 동일한 문항 집합을 반드시 사용한다.

각 문항 i에 대해:

    d_i = CE_model_A(i) - CE_model_B(i)

를 계산한다.

그리고:

    mean Δ
    SD(Δ)
    SE(Δ)
    95% CI
    paired t-test

를 기록한다.

이것은 unpaired comparison보다 적절하다.

왜냐하면 각 문항의:

    문항 난이도
    답변 길이
    희귀어
    context 길이
    질문 특성

등이 모델 A/B에서 공통으로 작용하므로 상당 부분 상쇄되기 때문이다.

특히 TinyLM 구조 변경처럼 **작은 차이를 검출하는 실험에서는 paired design을 primary comparison protocol으로 사용한다.**


## 7. "100문항으로 충분"이라는 결론은 완화

현재:

> KorQuAD CE는 100문항으로 충분하다

라고 단정하는 것은 근거가 부족하다.

paired SE는 다음에 의해 결정된다.

    SE(mean Δ) = SD(Δ) / sqrt(N)

따라서 이전 실험에서 1464개 문항을 사용했을 때:

    SE ≈ 0.0011 ~ 0.0014

가 나왔다는 사실만으로 새로운 100문항 subset에서도 같은 분산을 보장할 수 없다.

권장 방식:

    100문항
    → pilot

    paired variance 확인
    → 필요한 N 결정

    필요 시 500 또는 full dev
    → primary evaluation

즉 **100은 확정 sample size가 아니라 pilot sample size로 정의한다.**


## 8. KorQuAD의 20-token exclusion 규칙은 재검토

현재:

> 정답이 20토큰을 넘으면 제외

라는 규칙은 임의 threshold이므로 권장하지 않는다.

이 규칙은 특정 tokenizer에서 긴 정답을 가진 문항을 선택적으로 제거하는 **selection bias**를 만들 수 있다.

대신:

1. 모든 유효 문항에서 CE를 계산한다.
2. answer token length를 함께 기록한다.
3. 필요하면 length-stratified analysis를 수행한다.

예:

    1~4 tokens
    5~8 tokens
    9~16 tokens
    17+ tokens

이렇게 하면 tokenizer가 긴 한국어 정답을 어떻게 표현하는지 자체도 분석할 수 있다.


## 9. Context length 초과 문항 처리

현재:

> 1024를 넘으면 앞부분을 자르지 않고 문항을 버린다

는 원칙은 비교 실험에서는 합리적이다.

임의 truncation을 적용하면:

    context truncation

이라는 추가 confound가 생기기 때문이다.

다만 다음을 반드시 기록한다.

    total examples
    eligible examples
    excluded examples
    exclusion reason

그리고 **평가 문항 집합은 모델별 tokenizer 처리 결과에 따라 달라지면 안 된다.**

가장 안전한 방식:

    평가 문항 집합을 사전에 고정
        ↓
    모든 모델에 동일한 ID 집합 사용
        ↓
    계산 불가능한 경우 별도 사유 기록

이다.

모델 A에서는 평가되고 모델 B에서는 제외되는 식의 비교는 피한다.


## 10. `[UNK]` 표현 수정

현재 문서의:

> 고유명사가 UNK 조각으로 쪼개질 수 있다

는 tokenizer 구현에 따라 부정확할 수 있다.

BPE tokenizer는 `[UNK]`를 사용하지 않고 더 작은 subword/byte/character-like fragment로 분해할 수도 있다.

따라서 다음처럼 표현한다.

> **희귀하거나 vocabulary에서 효율적으로 표현되지 않는 문자열이 과도하게 긴 subword sequence로 분해될 수 있다.**

실제로 현재 TinyLM tokenizer가:

    [UNK]

을 사용하는지,

아니면:

    subword fragmentation

으로 처리하는지는 tokenizer implementation을 직접 확인한다.


## 11. KLUE 다른 과제를 "의미 없음"이라고 표현하지 않음

현재:

> KLUE-STS / NER / RE / DP / WoS → 파인튜닝 없이는 무의미

는 너무 강한 표현이다.

이론적으로는 base LM도 serialization + likelihood formulation을 통해 일부 task를 평가할 수 있다.

다만 현재 연구의 목적과 구현 비용을 고려하여:

> **본 연구의 base-LM likelihood-only evaluation framework에서는 공식 KLUE task metric 재현 대상으로 채택하지 않는다.**

라고 표현한다.

즉 "불가능"이나 "무의미"가 아니라:

    현재 연구 scope 밖

으로 처리한다.


## 12. 공식 benchmark와 auxiliary diagnostic을 명확히 분리

최종 평가 체계는 다음과 같이 정리한다.

                        TinyLM Base LM
                              │
                ┌─────────────┴─────────────┐
                │                           │
          LM intrinsic                 Downstream
          evaluation                   diagnostic
                │                           │
          validation loss             KLUE/KorQuAD data
          perplexity                        │
                                  ┌─────────┼─────────┐
                                  │         │         │
                                YNAT       NLI      KorQuAD
                                  │         │         │
                             label-LL    label-LL   answer CE
                                  │         │         │
                              accuracy   accuracy   paired Δ

그리고 다음을 명시한다.

    Official benchmark score
    ≠
    current SFT-free auxiliary diagnostic


## 13. KLUE tokenizer / 형태소 pre-tokenization 관련 관찰은 유지

이 부분은 연구적으로 의미가 있다.

KLUE 계열 tokenizer는 형태소 분석을 이용한 pre-tokenization과 BPE를 결합한 방식이다.

반면 현재 TinyLM tokenizer가:

    raw text
        ↓
    pure BPE

라면 두 시스템 사이에 tokenizer inductive bias 차이가 존재한다.

따라서 다음 질문을 향후 분석 대상으로 유지한다.

> **한국어에서 morphology-aware pre-tokenization이 작은 LM의 vocabulary utilization, token efficiency, downstream likelihood에 어떤 영향을 미치는가?**

다만 tokenizer를 지금 당장 변경하지 않는다.

이유:

    기존 TinyLM 실험
            ↓
    tokenizer 변경
            ↓
    token count / vocabulary usage / training dynamics
    전체 변경

으로 인해 기존 실험들과 직접 비교하기 어려워지기 때문이다.

따라서 현재 tokenizer는 고정하고:

    REVIEW3
    Qwen/Gemma tokenizer
    morpheme-aware tokenizer
    tokenization efficiency

에서 별도 분석한다.


## 14. 최종 권장 평가안

### Primary

#### 1. Pretraining validation loss / PPL

기존 LM capability 측정.

#### 2. KorQuAD-derived gold-answer conditional CE

    same examples
    same tokenizer
    same prompt serialization
    same answer span

으로 모델 간 paired comparison.

100개는 pilot로 시작하고 paired variance를 확인해 최종 N을 결정한다.


### Secondary

#### 3. YNAT label-likelihood accuracy

공식 KLUE YNAT Macro-F1과는 별개의 auxiliary metric.

가능하면 500개 이상 또는 충분한 sample size 사용.

#### 4. NLI label-likelihood accuracy

공식 NLI Accuracy와 이름을 혼동하지 않도록 auxiliary metric임을 명시.


### Not adopted

    KorQuAD generation EM/F1
    KLUE MRC EM/ROUGE
    KLUE STS
    KLUE NER
    KLUE RE
    KLUE DP
    KLUE WoS

현재 SFT-free base-LM 연구의 primary/secondary metric으로 사용하지 않는다.

단, 이것은 "평가 불가능"이 아니라 **현재 실험 범위와 목적에 맞지 않아 제외하는 것**이다.


## 15. 문서의 핵심 판정 문구 권장안

최종 문서에서는 다음과 같은 논리로 정리한다.

> **KLUE/KorQuAD의 공식 task metric은 SFT-free base LM에 직접 적용할 수 없는 것이 아니라, 현재 연구의 목적에 비해 해석력이 낮다.**
>
> 본 연구에서는 100M급 base LM의 구조적 차이를 평가하는 것이 목적이므로, instruction-following과 generation ability가 혼입되는 생성형 평가보다 benchmark 데이터를 이용한 conditional-likelihood 기반 auxiliary evaluation을 사용한다.
>
> YNAT/NLI에서는 candidate label의 normalized conditional likelihood를 비교하고, KorQuAD 1.0에서는 gold answer conditional CE를 계산한다.
>
> 이 점수들은 공식 KLUE/KorQuAD benchmark score가 아니며, **SFT-free base LM의 benchmark-conditioned likelihood diagnostic**으로 해석한다.
>
> 모델 간 비교는 동일 문항에 대한 문항별 paired Δ를 primary statistical unit으로 사용한다.
>
> 100문항은 pilot로 간주하며, 관측된 paired variance를 기반으로 최종 sample size를 결정한다.
>
> 공식 EM/F1 benchmark와 본 auxiliary diagnostic은 서로 다른 평가 목적을 가진다.


## 16. 구현 시 추가로 확인해야 할 사항

- [ ] YNAT official metric = Macro-F1임을 문서에 반영
- [ ] 현재 구현은 "label-likelihood accuracy"로 명명
- [ ] NLI도 동일한 naming convention 사용
- [ ] KorQuAD CE는 "QA score"라고 부르지 않음
- [ ] gold answer conditional CE의 정확한 token masking 구현
- [ ] prompt/context tokens에는 loss를 적용하지 않고 answer tokens만 측정
- [ ] tokenizer가 answer를 어떻게 분해하는지 기록
- [ ] [UNK] 사용 여부 실제 구현 확인
- [ ] answer token length 기록
- [ ] context length 기록
- [ ] 모든 모델에 동일한 example ID 집합 적용
- [ ] 제외 문항과 제외 이유 기록
- [ ] 100문항은 pilot로 취급
- [ ] paired Δ / SD / SE / 95% CI / t-test 기록
- [ ] random labels 절대 사용하지 않음
- [ ] 공식 benchmark metric과 auxiliary metric을 로그에서 명확히 구분

## 최종 핵심

**핵심 수정은 `공식 benchmark를 대체한다`가 아니라 `공식 benchmark와 별도로, 현재 SFT-free base LM의 비교에 적합한 likelihood diagnostic을 추가한다`로 개념을 정리하는 것이다.**