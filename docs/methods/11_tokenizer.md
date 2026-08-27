# 11. 토크나이저

어휘 설계·기존 토크나이저 재활용·임베딩 테이블 압축·교차 토크나이저 증류.

- **작성** 2026-08-27 · **상태** 📄**문헌 정리 + 우리 실측 대조.** 실험은 아직 없다
- **이 저장소의 현 상태**: 자체 SentencePiece **32,768**, `emb_rank` **E=256** 저랭크 분해,
  입출력 타잉, per-row int8/bf16 임베딩 양자화(결과 016 §20·§22)
- ⚠️**인용 규약**: 아래 표의 모든 수치는 **원문을 실제로 열어** 확인했다. 열지 못한 것은
  **미확인**으로 §7 에 따로 두고 요약하지 않는다(CLAUDE.md).

---

## 0. ★★왜 지금 이 축인가 — **임베딩이 남은 최대 비삼진 항이다**

REVIEW3 §1 이 실측으로 정리한 상주 회계(`mC_d36_ag4_nokd`, LUT 1.6bpw 이후):

```
삼진 8.88 MiB  +  임베딩·기타 33.2 MiB  =  42.1 MiB      -> 40 MiB 아슬, 32 MiB 불가
                  ^^^^^^^^^^^^^^^^^^^ 이 항의 대부분이 임베딩이다
```

임베딩 int8 로 **9.1**, bf16 로 **16.6** 까지 내렸다(결과 016). 🚫**그러나 그것은 같은 표를
좁게 저장한 것이지 표를 작게 만든 것이 아니다.** 어휘 자체를 건드리는 축은 아직 손대지 않았다.

---

## 1. 어휘 크기 — **작게** 쪽으로 근거가 모인다. 단 하한이 있다

| 기법·주장 | 상태 | 작동원리(개선 기여) | 트레이드오프 | 특기 |
|---|---|---|---|---|
| **어휘 스케일링 법칙** `Nv ∝ Nnv^0.83` | 📄 | 비어휘 파라미터보다 **어휘가 느리게** 커야 최적. 3B 를 32K→43K 로 올려 동일 FLOPs 에서 ARC-C **29.1 → 32.0** | LM 손실 기준이지 다운스트림·메모리 기준이 아니다 | Tao 2024. 논문 Table 1 은 3B/7B/13B 만 있고 **100M 예측값은 없다** — 아래 §1.1 참조 |
| **과학습이면 최적 어휘가 커진다** | 📄 | 같은 논문이 undertrained 에서 최적 어휘가 **작아진다**고 보고(2.87B @2.8e20 FLOPs: 32K→**24K**) | 우리는 300M 토큰으로 100M 을 돌린다 = **과학습 아님** | Tao 2024 |
| ★**100M 한국어 모델이 12K 어휘로 성립한다** | 📄**직접 대조군** | KR-BERT **96.1M 파라미터 / 어휘 12,367**(서브문자) · **99.3M / 16,424**(문자)가 NSMC 에서 **mBERT(어휘 119,547) 87.08 을 90.10 으로** 이긴다 | BERT 인코더·분류 과제다. 인과 LM 아니다 | Lee 2020. **우리 체급과 언어가 같은 유일한 1차 근거** |
| **어휘 크기와 다운스트림의 상관이 무의미** | 📄 | 1.5B, 어휘 32k–256k 에서 HumanEval Pass@1 **20.5/20.6/20.8/20.5**, Pearson **−0.13 (p=0.87)** | 1.5B·코드 도메인. 100M 에서는 어휘가 총량의 지배적 비중이라 **메모리가 먼저 걸린다** | Dagan 2024 |
| **어휘 파라미터 ≤ 전체의 20%** | 📄**경험칙** | 42.69M 터키어 모델에서 어휘 7k–66k 스윕. BPE·WordPiece 는 **작은 어휘에서 이미 포화** | 교착어·인코더 | Toraman 2023. 한국어와 형태론이 가깝고 체급도 우리급 |
| **입력 어휘만 키우기(비대칭)** | 💡 | 입력 n-gram 어휘를 키우면 전 체급에서 이득, **출력 어휘를 키우면 소형에서 오히려 해** | 12.8M 엔트리는 32–40 MiB 예산과 정면충돌 | Huang 2025. ★"출력은 작게, 입력은 크게" 라는 **비대칭 원리만** 가져올 수 있다 |

### 1.1 ★우리 예산이 실제로 허용하는 어휘 (내 계산, `d=768` · 입출력 타잉)

`E=256` 저랭크이므로 임베딩 파라미터 = `V×256 + 256×768`.

| 어휘 V | 임베딩 파라미터 | fp32 | **bf16** | **int8** | ⚙ternary(1.6bpw) |
|---:|---:|---:|---:|---:|---:|
| 8,192 | 2.29M | 8.7 | 4.4 | 2.2 | 0.44 |
| 16,384 | 4.39M | 16.7 | 8.4 | 4.2 | 0.84 |
| **32,768**(현재) | **8.59M** | **32.8** | ★**16.6**(실측) | ★**9.1**(실측) | ⚙1.6 |
| 65,536 | 16.97M | 64.7 | 32.4 | 16.2 | 3.2 |
| 151,936(Qwen3) | 38.9M | 148.4 | 74.2 | 37.1 | 7.4 |

> ★**실측과 계산이 맞는다** — 32,768 · bf16 계산 16.4 vs 실측 **16.6**(norm·gate 포함분 0.2).
> ★**어휘를 절반(16,384)으로 줄이면 int8 임베딩 항이 9.1 → 4.2 MiB.**
> REVIEW3 안 B 의 합이 **18.4 → 13.5 MiB** 가 된다. **32 MiB 목표에서 그 5 MiB 가 크다.**
> 🚫**그러나 품질 대가를 우리는 모른다.** §6 이 그 실험이다.

---

## 2. 분절 알고리즘 — **pre-tokenization 이 알고리즘보다 중요하다**

| 기법 | 상태 | 작동원리 | 트레이드오프 | 특기 |
|---|---|---|---|---|
| **Unigram(SentencePiece) > BPE** | 📔**LM 사전학습에서** | 어휘 20,000 고정, 알고리즘만 교체. SQuAD1.1 F1 **88.2 → 89.3**, MNLI **81.4 → 82.8**, ★**일본어 TyDi QA EM 41.4 → 53.7 (+12.3)** | 영·일 인코더 실험 | Bostrom & Durrett 2020. ★**일본어 격차가 압도적**인 것이 한국어에 시사적 |
| **Unigram ≈ BPE (NMT 단독)** | 📄 | 정규화(샘플링) 없이는 거의 동급: IWSLT en→vi BPE 25.61 / Unigram 25.49. **이득은 subword regularization 에서** 온다(27.68) | NMT | Kudo 2018. 위와 모순 아님 — 과제가 다르다 |
| **보편적 승자는 없다** | 📄 | 토크나이저 24종 × 2.6B 모델 × 52.6B 토큰. 게르만어는 BPE, 로망스어는 Unigram. 영어 단일 최적 **33k**, 다국어는 **3배** 필요 | 2.6B | Ali 2024. 영어 전용 토크나이저를 다국어에 쓰면 학습비 **+68%** |
| ★**압축률은 품질을 예측하지 못한다** | 📄**중요** | 64개 LM(350M–2.4B). 압축률과 다운스트림의 Pearson **0.241**. 대신 **pre-tokenization 이 결정적** | 350M 이상 | Schmidt 2024 |
| **Rényi efficiency(α=2.5)** | 📄**보조지표** | fertility 대신. BLEU 와 Pearson **0.78** vs 시퀀스 길이 **−0.32 (p=0.118, 무의미)** | NMT | Zouhar 2023 |
| ★**우리 실측이 이것과 일치한다** | ✅**실측** | 영문 SQuAD 공통 원문에서 우리 32k 는 **bytes/token 4.366**(Qwen 4.622 보다 **나쁜 압축**)인데 **bpb 1.3075 < 1.3363**(더 좋은 품질) | ⚠️모델도 함께 다르다 — 토크나이저 단독 기여 아님 | **결과 053 §S1.7.4** |

> ★★**"토큰이 적을수록 좋다" 는 틀렸다.** 문헌 셋과 우리 실측 하나가 같은 방향이다.
> → 🚫**토크나이저 후보를 fertility 로만 고르지 않는다.** 최소 (bytes/token, Rényi, 한/영 각각의 bpb) 세 가지를 함께 적는다.

---

## 3. 한국어 — **자모(sub-character)가 소어휘 제약에서 이긴다**

| 기법 | 상태 | 작동원리 | 트레이드오프 | 특기 |
|---|---|---|---|---|
| **형태소-인지 subword** | 📄 | BERT-Base 한국어, 어휘 4K–64K 스윕. KorNLI 최고 **84.29**(형태소-인지 64K), KorQuAD 최고 **74.04 EM**(순 subword 64K) | 형태소 분석기(MeCab 등) 의존 = 배포 시 **추가 상주** | Park 2020. ⚠️64K 가 최고인 것은 **그들이 시험한 최대값** |
| ★**자모 분해 + BPE** | 📄★**우리 조건과 일치** | 한글 음절 11,172자가 **68 자모**로 분해된다. En→Ko 제한어휘에서 **positional jamo 20.77 BLEU vs 음절 16.78 (+3.99)**. ★**\|V\|=1000–1500 자모가 \|V\|=2000 음절보다 시퀀스 25–40% 짧다** | **고자원·충분어휘에서는 이점 소멸**(차이 0.3 BLEU 이내). 근거가 NMT 이고 LM 아님 | Lee 2025 (LoResMT). ★**우리는 메모리 때문에 강제로 소어휘 레짐**이다 = 이 논문이 이득을 보고한 바로 그 조건 |
| **자모 단위 = 문자 단위와 동급** | 📄 | KR-BERT 서브문자(12,367) NSMC **89.86** vs 문자(16,424) **90.10**. ★**어휘를 25% 줄이고 성능은 자 안** | 인코더·분류 | Lee 2020 |
| **형태소+자모 조합** | 📄 | MorWP-MD(64K)가 MorWP 대비 NIKL-CoLA **+2.17**, HSD **+1.17** | ★**통사 과제에서만** 이득. 의미·감성은 무이득~소폭 손해 | Jeon 2023 |
| **한국어 fertility 문제** | 📄 | mBERT 한국어 fertility **≈1.8** vs 단일언어 **≈1.3**. 통제 실험에서 **토크나이저만으로 QA 3.9 EM** 차 | — | Rust 2021 |

> ★**자모 분해가 이 저장소에서 검토 가치가 실제로 있다.** 이유가 셋이다 —
> (a) 우리는 **소어휘 레짐**에 강제로 놓여 있고, (b) 자모는 **어휘를 줄이면서 시퀀스도 줄인다**
> (보통은 상충한다), (c) 68 자모는 **어휘 표의 하한**을 극단으로 낮춘다.
> ⚠️**그러나 근거가 NMT·인코더뿐이고 인과 LM 이 없다.** 그리고 시퀀스가 길어지면
> **어텐션 비용이 오른다** — 우리 배포는 CPU 1스레드 36 tok/s 다. 🚫**공짜가 아니다.**

---

## 4. 기존 토크나이저 재활용 — **재학습 비용이 두 자릿수로 갈린다**

| 기법 | 상태 | 작동원리 | 재학습 비용(실측) | 특기 |
|---|---|---|---|---|
| **ZeTT**(하이퍼네트워크) | 📄 | 새 토크나이저의 임베딩을 하이퍼넷이 **예측**. 재학습 0 토큰 | 즉시 **−1.2~−4.9pp** → **800M 토큰** 후 격차 0.3~2.0pp | Minixhofer 2024. 하이퍼넷 학습이 TPU v4-32 3일 |
| **Trans-Tokenization** | 📄 | 번역 정렬로 타깃 임베딩을 소스의 가중합으로 | ★**107M 토큰**(임베딩 41M + 상하 2×2층 66M), **10 GPU-hour 미만** | Remy 2024. 이 목록 중 **가장 싸다** |
| **FVT**(Fast Vocabulary Transfer) | 📄 | 새 토큰 임베딩 = 구 토크나이저가 쪼갠 조각들의 **평균** | 인도메인 MLM **1 epoch** | Gee 2022. 도메인 텍스트면 값싸고, ★**범용 텍스트(CoNLL03)에서는 F1 −7.04 로 무너진다** |
| **FOCUS** | 📄 | 겹치는 토큰의 보조 임베딩 유사도로 초기화. **초기화 직후 MLM loss 4.0–8.2 vs random 24.0–25.5** | ⚠️저자 예산은 **12.8B 토큰** | Dobler 2023. "재학습이 적게 든다" 는 **이 논문이 증명한 바가 아니다** |
| **WECHSEL** | 📄 | 정적 워드벡터 공간의 유사도로 초기화 | 6.55B–65.5B 토큰 | Minixhofer 2022. RoBERTa XNLI **+5~7pp**, GPT-2 PPL 개선은 **0.4~1.0 뿐** |
| **CLP-Transfer** | 📄 | 작은 타깃어 모델 + 큰 소스어 모델을 조합 | from-scratch 대비 **토큰 50%**(1.5B), **20%**(6.4B)에서 동률 | Ostendorff 2023 |
| ⚠️**토크나이저 교체 후 회복선** | 📄★**가장 보수적인 수** | 1.5B·7B 에서 baseline 회복에 **>50B 토큰**. 5–25B 로는 격차가 남는다 | — | Dagan 2024 |

> 🚫★**이 절 전체가 우리에게 직접 적용되지 않는다.** 전부 **"잘 학습된 대형 백본을 재활용"**
> 전제다(7B·1.5B·XLM-R 278M). **from-scratch 100M 에는 이식받을 대상 모델이 없다.**
> ★**우리가 쓸 수 있는 방향은 하나** — 교사(Qwen3-0.6B)의 어휘를 **학생 쪽으로 옮기는** 설계,
> 즉 §5 의 교차 토크나이저 증류다.

---

## 5. 어휘 가지치기 — **151k → 32k 는 안전구간 밖이다**

| 기법 | 상태 | 작동원리 | 트레이드오프 | 특기 |
|---|---|---|---|---|
| **Vocabulary Trimming** | 📄**정전** | 타깃 언어가 실제로 쓰는 토큰만 남긴다. **다국어 LM 은 임베딩이 전체의 80% 를 넘을 수 있다.** mT5 를 **원본의 35%** 까지, XLM-R 은 어휘 40%·전체 60% 감축까지 성능 유지 | ★**재학습 불필요**(특히 파인튜닝 **이후** 자르면 보존) | Ushio 2023 · 도구 [`lm-vocab-trimmer`](https://github.com/asahi417/lm-vocab-trimmer). ★**도구 권고는 "원 어휘의 약 50%", 기본 60k, 60k 미만은 저하 경고** |
| ⚠️**비라틴 문자가 위험구간** | 📄★**우리 조건 경고** | 유니코드 필터 유지율: 중국어 **20.6%**, 불가리아어 9.1%, 영·스페인 ~75%. ★**중국어에서 유니코드 필터링은 o-BLEU 53.32 로 붕괴, 코퍼스 빈도 기반은 66.17** | — | Bogoychev 2024 |
| ★**가지치기 이득은 CPU·소형에서만 난다** | 📄★ | BLOOM-560M 임베딩 메모리 **−50%**, **CPU 추론 5–20% 가속(소형)**. ★**GPU 에서는 오라클 기준을 써도 가속 0** | 모델이 클수록 이득 급감 | Bogoychev 2024 |

> ★★**우리는 이득 구간(CPU·소형)과 위험 구간(비라틴)에 동시에 있다.**
> `32,768 / 151,936 = 21.2%` 는 위 중국어 사례 **20.6%** 와 거의 같은 비율이다.
> → 🚫**한글 유니코드 블록으로 자르지 않는다. 반드시 한·영 코퍼스 빈도로 자른다.**

---

## 6. 임베딩 테이블 압축 — **화려한 배수는 대부분 다른 체급 이야기다**

| 기법 | 상태 | 작동원리 | 트레이드오프 | 특기 |
|---|---|---|---|---|
| **저랭크 분해(ALBERT)** | ✅**채택중** | `V×H` → `V×E + E×H` | 로짓 랭크가 E 로 제한 | ★**Lan 2020 Table 3: E=128 이 16M/79.6 인 E=256 보다 12M/80.1 — 파라미터 25% 적고 점수 0.5 높다.** ⚠️영어 인코더+층공유 조건 |
| **입출력 타잉** | ✅**채택중** | 같은 표를 입력·출력에 | 없음 | Press & Wolf 2017: PTB PPL **78.4 → 74.3**, NNLM 66M→51M. Inan 2017: 66M/73.4 → 51M/**68.5**. ★**줄이면서 좋아진다** |
| **임베딩 양자화** | ✅**실측** | per-row int8 / bf16 | int8 +0.0001, bf16 +0.0000 (⚠️둘 다 **autocast 조건**) | 결과 016 §20·§22. ★**CPU fp32 재측정 미완** |
| **소형에서의 텐서분해 한계** | 📄★**가장 관련 깊은 경고** | Cerebras/OPT **111M–1.3B** 를 Tensor-Train 분해. ★**안전 압축률은 2.0× 까지**. 그 이상은 PPL 급락 | ★**작은 모델(111M–256M)이 큰 모델보다 압축에 *덜* 강건** | Xu 2025 (TensorSLM). Raspberry Pi 5 에서 쿼리당 에너지 −50% |
| **DPQ / 코드 학습** | 💡 | 미분가능 product quantization | ★**end-to-end 학습 필수 — 사전학습 임베딩에 사후 적용 불가** | Chen 2020: PTB LM **58.7–163.2×**, PPL 83.3 vs 83.4. ★**from-scratch 인 우리에게는 오히려 유리한 조건** |
| **Deep compositional codes** | 💡 | Gumbel-softmax 이산 코드 | MB 단위 실측 없음 | Shu & Nakayama 2018. 논문 동기가 **"모바일 배포"** |
| **MorphTE** | 💡 | 단어를 형태소 벡터의 텐서곱으로. **20× 무손실** | ★**언어별 형태소 분절기 필요**, 실험이 전부 인도유럽어 | Gan 2022 |
| **해시 임베딩** | 🚫**부적합** | 해시 버킷 + 학습 가중치 | ★**근거가 전부 bag-of-words 분류**. 자기회귀 LM 출력층 증거 없음 | Svenstrup 2017 |
| ★**소형에서 임베딩 비중** | 📄 | 어휘 32k·dim 512 의 125M 모델에서 임베딩이 **전체의 20% 초과**(LLaMA-7B 3.7%, 70B 0.7%). 타잉으로 파라미터 −11.8%/정확도 −0.2pp, 그 손실을 **층 추가로 메워 +0.4pp** | — | Liu 2024 (MobileLLM). ★sub-1B 는 **깊고 얇게** |

> ★**우리 현 조합(E=256 + 타잉 + per-row int8)은 이 지형에서 이미 보수적으로 안전한 위치**다.
> 다음 한 걸음의 후보는 **E=128**(Lan 2020 이 E=256 보다 낫다고 보고) 과
> **어휘 축소**(§1.1) 이고, **텐서분해·해시·PQ 는 근거가 우리 체급 밖**이다.

---

## 7. 교차 토크나이저 증류 — **여기가 유일하게 전이가 잘 되는 절이다**

우리는 **Qwen3-0.6B 교사 ↔ 자체 32k 학생**이라는 정확히 이 문제를 안고 있다(P067).

| 기법 | 상태 | 작동원리 | 실측 순위 | 특기 |
|---|---|---|---|---|
| **ALM** | 📄★**현 최강** | 비교 가능한 **토큰 청크**를 찾아 우도 차를 최소화 | Gemma2-2B→Qwen2 토크나이저 평균 **55.1 vs MinED 53.0**. 바이트 전환 **50.6 vs 47.1 vs SFT 46.5** | Minixhofer 2025. 증류 예산 **약 0.6B 토큰** |
| **DSKD-CMA** | 📄★**우리와 가장 닮은 페어** | hidden state 를 서로의 공간에 사영 + cross-model attention 으로 토큰 정렬 | ★**Qwen1.5-1.8B → GPT2-120M(어휘 상이)**: SeqKD 16.13 / MinED 17.46 / ULD 17.11 / **DSKD-CMA 18.02** | Zhang 2024. ★**이 설정에서 ULD 가 MinED 보다 낮다** |
| **ULD** | 📄 | KL 대신 **Wasserstein**. 확률을 정렬하면 닫힌 해 → O(n log n) | 학생 160M–1B 에서 추출 QA F1 **74.33 vs 72.03** | Boizard 2024/TMLR 2025 |
| **MinED** | 📄 | 최소 편집거리 토큰 정렬 | 위 두 표의 baseline | Wan 2024 (FuseLLM) |
| ✅**우리 실측** | ✅ | Qwen3-0.6B 교사로 KD. **Q256T 1.3363 vs QT0 1.3440 = −0.0077 bpb** | 🚫**실무 분해능 0.008 바로 아래 — UNRESOLVED** | **결과 053 §S1.7.2**. ★랭크 64 로 줄이면 **+0.0636 = 8σ** |

> ★★**우리 결론이 문헌보다 비관적인 이유가 설명된다.** 우리가 쓴 것은
> **로짓 랭크 절단 + 단순 정렬** 계열이고, ALM·DSKD-CMA 는 **정렬 자체를 학습**한다.
> 결과 053 의 *"KD 기여가 자 안"* 은 **"KD 가 무용하다" 가 아니라 "이 정렬 방식으로는 자 안"** 이다.
> 🚫**그래도 REVIEW2 의 무KD 표준을 되돌리지 않는다** — 되돌리려면 ALM·DSKD 를 구현해야 하고,
> 그것은 **상주 메모리를 1 MiB 도 줄이지 않는다.**

---

## 8. 품질을 직접 올리는 토크나이저 선택

| 기법 | 상태 | 작동원리 | 트레이드오프 | 특기 |
|---|---|---|---|---|
| **SuperBPE** | 📄 | 2단계 커리큘럼으로 **공백을 넘는 superword** 학습. 어휘 200k 고정에서 bytes/token **4.46 → 6.63**, 토큰 최대 −33% | ★**어휘 200k 전제.** 8B·330B 토큰. **비영어 실험이 논문에 없다** | Liu 2025 (COLM). 30과제 평균 **+4.0%p**, MMLU **+8.2%p**, 추론 연산 −27% |
| **자릿수 정렬** | 📄 | 8-shot 덧셈 GPT-3.5 L2R **75.6%** vs R2L **97.8%** | ⚠️**논문은 1자리 vs 3자리 청킹을 직접 비교하지 않았다** — "digit splitting 이 좋다"의 근거로 인용하면 안 된다 | Singh & Strouse 2024. 인용은 **"자릿수 정렬이 원인"** 으로 |
| **어휘 확장(한국어)** | 📄 | TinyLlama-1.1B 에 한국어 어휘 append. **UNK 48.61% → 0.98%**, 문장당 토큰 **325.27 → 128.92 (−60%)** | 내재적 지표 위주, **추론 속도 미측정** | Seo 2025 |
| **merge 뒤에 append** | 📄 | 기존 merge 리스트 **뒤에** 새 merge 를 붙이면 토큰화 효율이 **절대 나빠지지 않는다**(보장) | 확장 방향 논문 | Herold 2025 |
| **byte-fallback** | 🚫**미확인** | — | — | ★**통제 측정한 논문을 찾지 못했다. 요약하지 않는다.** 자체 실측이 빠르다 |

---

## 9. 🚫**토크나이저-프리는 우리 체급에서 근거가 없다**

| 기법 | 최소 검증 규모 | 왜 우리에게 안 오나 |
|---|---:|---|
| **ByT5** | Small/Base(~300–580M) | 소형에서 이긴 것은 사실이나(GLUE Small **75.6 → 80.5**), ★**이득의 원천이 "mT5 가 파라미터의 66%(582M 중 256M)를 어휘에 쓰던 낭비를 되찾은 것"**이다. 우리는 256K 를 쓸 계획이 없어 **그 이득이 이미 없다**. 추론이 과제별 **1.5–9.5배** 느리다 |
| **BLT** | 400M(실 537M) | ★**해시 n-gram 임베딩 비용을 논문이 보고하지 않는다.** 공식 코드 기본값 `30000×512×3×2 = 92.2M 파라미터`, 논문 설정(500K 해시·dim 768)이면 **≈384M**. 우리 본체보다 크다 |
| **MambaByte** | 353M | SSM 전제. 우리는 Transformer |
| **H-Net** | 760M | 공백이 정보를 안 주는 언어에서 이득이 크다는 신호는 한국어에 **긍정적**이나 **100M 검증 없음** |
| **SpaceByte** | 미확인 | 설계 원리가 **공백 경계** — 한국어는 어절이 길고 공백 밀도가 낮아 패치가 과도해진다 |

> ★**바이트 수준은 상주 파라미터를 줄이는 기술이 아니라 다른 곳(해시 테이블·깊은 dense·긴 시퀀스)으로 옮기는 기술**이다.

---

## 10. ★★제안 — **토크나이저 실험 3안** (사용자 승인 전, 계획서 미작성)

> 🚫**계획서를 만들지 않았다.** 아래는 제안이고, **승인 후에** 계획서를 만든다.
> ⚠️**번호를 미리 붙이지 않는다**(의사결정함정 D16 — 붙이면 정적 게이트가 "참조되는데 계획서가 없다" 로 잡는다).
> 지금 이것들은 **후보**이지 계획이 아니다.
> 우선순위 근거는 **상주 감축량 ÷ 비용**이다.

| 안 | 무엇 | 왜 이것부터 | ⚙상주 이득 | ⚙비용 | 선결 |
|---|---|---|---:|---:|---|
| ★**T1** **어휘 반감** | 자체 SentencePiece 를 **16,384** 로 재학습 → 처음부터 학습 | ★**가장 큰 상주 항을 직접 절반으로.** §1 의 문헌 넷과 KR-BERT 실측이 **12K 가 성립한다**고 말한다 | ★**int8 임베딩 9.1 → 4.2 MiB** (안 B 합 18.4 → **13.5**) | 학습 1회 ⚙1.7h + 토크나이저 학습 ⚙20분 | **없다.** 지금 돌아간다 |
| **T2** **자모 pre-tokenization** | 한글을 68 자모로 분해한 뒤 BPE. 어휘 8,192 | §3 이 **소어휘에서만** 이득을 보고했고 우리가 그 조건 | ⚙**2.2 MiB** | 학습 1회 + **구현**(정규화·역변환·round-trip 검증) | 🚫**구현 선결.** `prepare` 에 자모 정규화 |
| **T3** **`E=128` 재확인** | `emb_rank 128` 을 **무KD 표준조건**에서 | Lan 2020 이 E=128 > E=256 을 보고했는데 우리 구 측정(결과 030)은 **KD 조건**이었다 | ⚙**int8 9.1 → 4.9** | 학습 1회 ⚙1.7h | 없다 |

### 10.1 ⚠️**측정 규약** — 어휘가 다르면 자가 달라진다

🚫**어휘가 다른 두 모델의 `full-val` 이나 perplexity 를 비교하면 안 된다.**
큰 어휘가 자동으로 유리하게 나온다. 유일하게 유효한 것은 **`common_bpb`**
(`BPB = (L_T/L_B)·log₂(e^ℓ)`, The Pile §3.1 정의)이고, 우리 실무 분해능은 **0.008 bpb** 다.

⚠️**현재 `common_bpb` 는 영문 SQuAD context 전용**이다(결과 053 한계). 어휘 실험은
**한국어 공통 원문이 없으면 절반만 답한다.** → T1 착수 전에 한국어 공통 원문 확보가 **선결**이다.

### 10.2 사용자에게 요청할 수 있는 것

| # | 무엇 | 왜 |
|---|---|---|
| 1 | 한국어 공통 원문 후보 결정(KorQuAD context / 위키 dump 일부) | §10.1 의 선결 |
| 2 | ⚙원문 PDF 3편(SentencePiece Kudo&Richardson 2018 · MEGABYTE 본문 · SpaceByte 본문) | §7 의 미확인 3건 |

---

## 11. 참고문헌 — **전부 원문을 열어 확인했다**

| 약칭 | 서지 | id/DOI |
|---|---|---|
| Tao 2024 | Scaling Laws with Vocabulary: Larger Models Deserve Larger Vocabularies (NeurIPS 2024) | [arXiv:2407.13623](https://arxiv.org/abs/2407.13623) |
| Dagan 2024 | Getting the most out of your tokenizer for pre-training and domain adaptation (ICML 2024) | [arXiv:2402.01035](https://arxiv.org/abs/2402.01035) |
| Huang 2025 | Over-Tokenized Transformer: Vocabulary is Generally Worth Scaling (ICML 2025) | [arXiv:2501.16975](https://arxiv.org/abs/2501.16975) |
| Toraman 2023 | Impact of Tokenization on Language Models: An Analysis for Turkish (ACM TALLIP) | [10.1145/3578707](https://doi.org/10.1145/3578707) · [arXiv:2204.08832](https://arxiv.org/abs/2204.08832) |
| Bostrom & Durrett 2020 | Byte Pair Encoding is Suboptimal for Language Model Pretraining (Findings EMNLP) | [10.18653/v1/2020.findings-emnlp.414](https://aclanthology.org/2020.findings-emnlp.414/) |
| Kudo 2018 | Subword Regularization (ACL 2018) | [10.18653/v1/P18-1007](https://aclanthology.org/P18-1007/) |
| Ali 2024 | Tokenizer Choice For LLM Training: Negligible or Crucial? (Findings NAACL) | [2024.findings-naacl.247](https://aclanthology.org/2024.findings-naacl.247/) |
| Schmidt 2024 | Tokenization Is More Than Compression (EMNLP 2024) | [2024.emnlp-main.40](https://aclanthology.org/2024.emnlp-main.40/) |
| Zouhar 2023 | Tokenization and the Noiseless Channel (ACL 2023) | [2023.acl-long.284](https://aclanthology.org/2023.acl-long.284/) |
| Rust 2021 | How Good is Your Tokenizer? (ACL 2021) | [2021.acl-long.243](https://aclanthology.org/2021.acl-long.243/) |
| Park 2020 | An Empirical Study of Tokenization Strategies for Various Korean NLP Tasks (AACL-IJCNLP) | [2020.aacl-main.17](https://aclanthology.org/2020.aacl-main.17/) |
| Lee 2020 | KR-BERT: A Small-Scale Korean-Specific Language Model | [arXiv:2008.03979](https://arxiv.org/abs/2008.03979) · [github](https://github.com/snunlp/KR-BERT) |
| Lee 2025 | Jamo-Level Subword Tokenization in Low-Resource Korean MT (LoResMT 2025) | [2025.loresmt-1.8](https://aclanthology.org/2025.loresmt-1.8/) |
| Jeon 2023 | Improving Korean NLP Tasks with Linguistically Informed Subword Tokenization and Sub-character Decomposition | [arXiv:2311.03928](https://arxiv.org/abs/2311.03928) |
| Seo 2025 | How does a Language-Specific Tokenizer affect LLMs? | [arXiv:2502.12560](https://arxiv.org/abs/2502.12560) |
| Ushio 2023 | Efficient Multilingual LM Compression through Vocabulary Trimming (Findings EMNLP) | [2023.findings-emnlp.981](https://aclanthology.org/2023.findings-emnlp.981/) |
| Bogoychev 2024 | The Ups and Downs of LLM Inference with Vocabulary Trimming by Language Heuristics | [arXiv:2311.09709](https://arxiv.org/abs/2311.09709) |
| Herold 2025 | Vocabulary Customization for Efficient Domain-Specific LLM Deployment | [arXiv:2509.26124](https://arxiv.org/abs/2509.26124) |
| Minixhofer 2024 | Zero-Shot Tokenizer Transfer (NeurIPS 2024) | [arXiv:2405.07883](https://arxiv.org/abs/2405.07883) |
| Minixhofer 2022 | WECHSEL (NAACL 2022) | [2022.naacl-main.293](https://aclanthology.org/2022.naacl-main.293/) |
| Minixhofer 2025 | Universal Cross-Tokenizer Distillation via Approximate Likelihood Matching (NeurIPS 2025) | [arXiv:2503.20083](https://arxiv.org/abs/2503.20083) |
| Dobler 2023 | FOCUS (EMNLP 2023) | [2023.emnlp-main.829](https://aclanthology.org/2023.emnlp-main.829/) |
| Gee 2022 | Fast Vocabulary Transfer for Language Model Compression (EMNLP Industry) | [10.18653/v1/2022.emnlp-industry.41](https://aclanthology.org/2022.emnlp-industry.41/) |
| Remy 2024 | Trans-Tokenization and Cross-lingual Vocabulary Transfers (COLM 2024) | [arXiv:2408.04303](https://arxiv.org/abs/2408.04303) |
| Ostendorff 2023 | Efficient LM Training through Cross-Lingual and Progressive Transfer Learning | [arXiv:2301.09626](https://arxiv.org/abs/2301.09626) |
| Yamaguchi 2024 | An Empirical Study on Cross-lingual Vocabulary Adaptation (Findings EMNLP) | [2024.findings-emnlp.396](https://aclanthology.org/2024.findings-emnlp.396/) |
| Boizard 2024 | Universal Logit Distillation Loss (TMLR 2025) | [arXiv:2402.12030](https://arxiv.org/abs/2402.12030) |
| Zhang 2024 | Dual-Space Knowledge Distillation for LLMs (EMNLP 2024) | [arXiv:2406.17328](https://arxiv.org/abs/2406.17328) · [github](https://github.com/songmzhang/DSKD) |
| Wan 2024 | Knowledge Fusion of Large Language Models — MinED (ICLR 2024) | [arXiv:2401.10491](https://arxiv.org/abs/2401.10491) |
| Lan 2020 | ALBERT (ICLR 2020) | [arXiv:1909.11942](https://arxiv.org/abs/1909.11942) |
| Press & Wolf 2017 | Using the Output Embedding to Improve Language Models (EACL) | [E17-2025](https://aclanthology.org/E17-2025/) |
| Inan 2017 | Tying Word Vectors and Word Classifiers (ICLR 2017) | [arXiv:1611.01462](https://arxiv.org/abs/1611.01462) |
| Xu 2025 | TensorSLM: Energy-efficient Embedding Compression of Sub-billion LMs (ICML 2025 WS) | [arXiv:2506.13514](https://arxiv.org/abs/2506.13514) |
| Chen 2020 | Differentiable Product Quantization (ICML 2020) | [arXiv:1908.09756](https://arxiv.org/abs/1908.09756) |
| Shu & Nakayama 2018 | Compressing Word Embeddings via Deep Compositional Code Learning (ICLR) | [arXiv:1711.01068](https://arxiv.org/abs/1711.01068) |
| Gan 2022 | MorphTE (NeurIPS 2022) | [arXiv:2210.15379](https://arxiv.org/abs/2210.15379) |
| Svenstrup 2017 | Hash Embeddings for Efficient Word Representations (NIPS 2017) | [proceedings](https://proceedings.neurips.cc/paper/2017/hash/f0f6ba4b5e0000340312d33c212c3ae8-Abstract.html) |
| Liu 2024 | MobileLLM (ICML 2024) | [arXiv:2402.14905](https://arxiv.org/abs/2402.14905) |
| Liu 2025 | SuperBPE (COLM 2025) | [arXiv:2503.13423](https://arxiv.org/abs/2503.13423) |
| Singh & Strouse 2024 | Tokenization counts: the impact of tokenization on arithmetic | [arXiv:2402.14903](https://arxiv.org/abs/2402.14903) |
| Xue 2021 | ByT5 (TACL 2022) | [arXiv:2105.13626](https://arxiv.org/abs/2105.13626) |
| Pagnoni 2024 | Byte Latent Transformer | [arXiv:2412.09871](https://arxiv.org/abs/2412.09871) · [github](https://github.com/facebookresearch/blt) |
| Wang 2024 | MambaByte (COLM 2024) | [arXiv:2401.13660](https://arxiv.org/abs/2401.13660) |
| Hwang 2025 | Dynamic Chunking for End-to-End Hierarchical Sequence Modeling (H-Net) | [arXiv:2507.07955](https://arxiv.org/abs/2507.07955) |
| Gao 2021 | The Pile — bits-per-byte 정의 §3.1 | [arXiv:2101.00027](https://arxiv.org/abs/2101.00027) |
| Park 2021 | KLUE | [arXiv:2105.09680](https://arxiv.org/abs/2105.09680) |
| Lim 2019 | KorQuAD 1.0 | [arXiv:1909.07005](https://arxiv.org/abs/1909.07005) |

### 11.1 🚫**미확인 — 요약하지 않았다**

| 항목 | 상태 |
|---|---|
| SentencePiece (Kudo & Richardson 2018, arXiv:1808.06226) | **미확인.** 다른 논문의 인용으로만 확인 |
| MEGABYTE 본문 BPB 표·모델 크기 (arXiv:2305.07185) | **미확인.** 초록만. 수치는 MambaByte 논문 인용으로 교차확인 |
| SpaceByte 모델 크기·BPB (arXiv:2404.14408) | **미확인.** 초록만 |
| BLT 논문 내 해시 임베딩 파라미터 수 | ★**논문이 보고하지 않는다.** 계산식은 공식 코드에서 확인, 총량은 우리 계산 |
| KLUE 사전학습 코퍼스 규모·토크나이제이션 ablation 표 | **미확인** |
| byte-fallback 의 통제된 downstream delta | ★**전용 논문을 찾지 못했다** |
