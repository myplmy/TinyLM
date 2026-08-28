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

## 9. 🚫**토크나이저-프리는 우리 체급에서 근거가 없다** (2026-08-28 원문 3편 확인 후 갱신)

| 기법 | **텍스트 최소 학습 규모** | 임베딩 파라미터 보고 | 상주 MiB 보고 | 한국어 | 왜 우리에게 안 오나 |
|---|---|---|---|---|---|
| **ByT5** | Small/Base(~300–580M) | ○ | ✗ | ✗ | 소형에서 이긴 것은 사실이나(GLUE Small 75.6 → 80.5) ★**이득의 원천이 "mT5 가 파라미터의 66%(582M 중 256M)를 어휘에 쓰던 낭비를 되찾은 것"** 이다. 우리는 256K 를 쓸 계획이 없어 **그 이득이 이미 없다.** 추론이 과제별 **1.5–9.5배** 느리다 |
| ★**MEGABYTE** | ★**텍스트는 758M+262M**(베이스라인 Transformer 320M) | ✗**수식만** | ✗ | ✗ | 125M·83M·62M 모델은 **전부 이미지·오디오 전용**이다. ★**100M급 텍스트 검증이 논문에 없다.** 그리고 **후속 통제 실험(SpaceByte)이 반증**했다 — *"MegaByte's performance **significantly lags behind** a subword-level Transformer"*, *"10¹⁹ FLOPs 로 학습한 MegaByte 가 **10% 의 FLOPs** 로 학습한 SentencePiece Transformer 보다 파레토 전 구간에서 나쁘다"* |
| **BLT** | 400M(실 537M) | ✗**논문이 보고하지 않는다** | ✗ | ✗ | 공식 코드 기본값 `30000×512×3×2 = 92.2M 파라미터`, 논문 설정(500K 해시·dim 768)이면 **≈384M**. 우리 본체보다 크다 |
| **MambaByte** | 353M | ✗ | ✗ | ✗ | SSM 전제. 우리는 Transformer |
| **H-Net** | 760M | ✗ | ✗ | ✗ | 공백이 정보를 안 주는 언어에서 이득이 크다는 신호는 긍정적이나 **100M 검증 없음** |
| ★**SpaceByte** | ★**표 기준 151M+38M**, 그리드는 **D=384**(비임베딩 ⚙14–28M) | ★**○ 공식 제공**(Table 5) | ✗ | ✗(**중국어 예비실험에서 subword 보다 나쁨**) | ★**세 편 중 유일하게 우리 체급을 실제로 학습**했다. 🚫**그러나 그 구간 수치를 공개하지 않았고**, 저자가 *"컴퓨트 예산이 **클수록** subword 대비 유리해진다"* 고 명시했다 — **우리는 그 반대 끝**이다 |

### 9.1 ★**SpaceByte 가 유일하게 파라미터를 세어 준다** — 그리고 우리 예산에서 상쇄된다

Table 5 의 공식(비임베딩, de-embedding 포함)에 논문의 어휘값을 넣으면:

| | subword(V=50,257, D=1024) | byte(V=256, D_local=512) |
|---|---:|---:|
| de-embedding 파라미터 | **51.46M** | **0.131M** |

**차이 51.3M.** PG-19 에서 SpaceByte **201M+50M = 251M** / bpb **1.009** 가
Transformer(SentencePiece) **454M** / bpb **0.989** 와 겨룬다 —
**파라미터 45%·FLOPs 25% 절감에 bpb 2% 손해.**

🚫★★**그런데 우리는 그 절감분을 이미 갖고 있다.** `emb_rank 256` 인수분해로
`32,768×256 + 256×768 = 8.59M` 이다. **바이트화로 없앨 수 있는 것은 최대 8.59M 파라미터**이고,
그 대가는 **시퀀스 4배 이상**(논문: *"the length of a sequence typically increases by about a factor of four"*)
→ **KV 캐시 4배**다. 🚫**두 논문 다 KV 캐시를 회계에 넣지 않는다.**
**32–40 MiB 예산에서 KV 4배는 8.59M 절감을 즉시 잡아먹는다.**

### 9.2 ⚠️★**FLOPs-per-byte 지표가 우리 배포 조건에서 무효다**

SpaceByte 각주 4 원문: *"in order for **memory bandwidth to not be a bottleneck during inference**,
the batch size must be sufficiently large and e.g. **grouped-query attention must be used**."*

★**우리 배포는 CPU · batch 1 · 상주 메모리 제약**이다 — **정확히 그 반대 조건**이다.
그리고 결과 014 §12.2 가 우리 조건에서 **디코드 시간은 FLOPs 가 아니라 "방문 수" 에 선형**임을 실측했다.
🚫**FLOPs-per-byte 로 우리 배포를 예측하지 않는다.**

### 9.3 ★★한국어가 SpaceByte 의 **최악 케이스**다 (의사코드로부터 도출)

SpaceByte 의 패치 경계 규칙은 **UTF-8 선두 바이트(≥0xC0)를 spacelike** 로 본다(Listing 1 의사코드).
⚠️**본문 2페이지는 "continuation bytes 를 spacelike 로 정의한다" 고 적어 의사코드와 모순**이다 —
각주 2 가 의사코드와 일치하므로 **본문이 오타**로 판단된다. **인용은 의사코드 기준으로 한다.**

한글 음절(U+AC00–U+D7A3)은 UTF-8 3바이트이고 선두 바이트가 0xEA–0xED(≥0xC0)다.
→ ⚙**한글은 음절마다 global block 이 삽입되어 평균 패치가 ≈3바이트**가 된다.
논문 실측 영어 PG-19/arXiv **≈6바이트**, Github **≈8바이트**의 **절반 이하**다.
→ 지배 항 `2·m_global·(T_global/T_local)` 이 **약 2배**가 된다.

🚫**이것은 우리 계산이지 논문의 측정이 아니다**(논문에 한국어 실험은 0건).
그러나 저자가 *"중국어에서는 subword transformer 보다 나쁘다"* 는 예비 실험을 적어 뒀고,
중국어·한국어 모두 **CJK 3바이트** 계열이다.

### 9.4 ★결론 문장 (인용용)

> 바이트 레벨·토크나이저-프리는 **우리 조건에서 채택 근거가 없다.**
> MEGABYTE 는 텍스트에서 100M급을 검증한 적이 없고(최소 758M+262M) **후속 통제 실험이 반증**했다.
> SpaceByte 는 우리 체급을 실제로 학습했으나 **그 구간 수치를 공개하지 않았고**, 저자 스스로
> *"컴퓨트가 클수록 subword 대비 유리"* 라고 적어 **우리 저컴퓨트 조건이 불리함을 인정**한다.
> 어휘 임베딩 **8.59M 절감은 시퀀스 4배에 따른 KV 캐시 증가로 상쇄**되며
> (두 논문 다 상주 메모리를 측정하지 않는다), 한국어는 UTF-8 3바이트 때문에
> SpaceByte 패치가 ⚙3바이트로 잘게 쪼개져 **global 블록 호출이 영어의 2배**가 된다.
> → **SentencePiece 32,768 + 인수분해 임베딩(E=256)을 유지한다.**
> ⚠️**단 32,768 이라는 값은 SentencePiece 논문이 근거가 아니다** — §9.5.

### 9.5 🚫★★**SentencePiece 논문에 32k 는 없다** — 우리가 그동안 오인용할 뻔한 것

원문을 열어 확인한 결과:

| 흔한 인용 | **실제** |
|---|---|
| *"SentencePiece 가 vocab 32k 를 권장·검증했다"* | 🚫**32k 는 논문에 한 번도 나오지 않는다.** 등장하는 어휘값은 **8k(BLEU 실험) · 16k(속도 실험) · 80k(단어 베이스라인)** 뿐이고 **어휘 크기 스윕 자체가 없다** |
| *"unigram 이 BPE 보다 좋다"* | 이 논문은 반대로 *"BPE and unigram language models show **almost comparable** performance"* 라고 적는다. 품질 우위 주장은 **Kudo 2018(Subword Regularization)** 소관이다 |
| *"약 380배 빠르다"* | 본문 주장이나 **표(Table 2)는 216.2s vs 5.9s = 약 36.6배**다. 영어에 대해서는 논문 스스로 *"almost comparable"* 이라고 쓴다 |
| *"LM 에서 검증됐다"* | **NMT 전용**(KFTT 영–일 440k 문장). LM 실험 0건 |
| *"한국어에 대해 검증됐다"* | **서론에서 이름만 언급.** 실험 0건 |

★**논문이 실제로 뒷받침하는 것**(우리가 쓸 수 있는 것):
**무손실 복원**(`Decode(Encode(Normalize(t))) = Normalize(t)`, 공백을 `▁` U+2581 로 escape) ·
**pre-tokenizer 없이 원문에서 직접 학습** · **어휘 크기를 직접 지정**(merge 횟수가 아니라) ·
**self-contained 모델 파일**(Protocol Buffer + NFKC 부분집합 FST) ·
★**en→ja 에서는 pre-tokenization 이 오히려 BLEU 를 떨어뜨린다**(21.62 → 20.86) —
**공백이 형태소 경계와 어긋나는 언어에서 pre-tokenizer 없이 가도 손해가 없다**는 유일한 직접 근거다.

> ⚠️★**따라서 우리 어휘 32,768 은 자체 실측으로 정당화해야 한다.** 그것이 §10 의 T1 이다.

## 10. ★★**토크나이저 실험 3안 — 2026-08-28 사용자 승인.** 계획서 [P075](../../test_plan/P075_토크나이저-어휘예산과-한국어-분절.md)

> ✅**2026-08-28 승인.** 계획서 `test_plan/P075_토크나이저-어휘예산과-한국어-분절.md` 를 만들었다.
> ⚠️**T1 은 §13 의 공통 원문 선결이 풀려야 판정이 가능하다** — 어휘가 다르면 `common_bpb` 만 유효한데
> 지금 그 도구가 **영문 전용**이고, 그 영문 원문조차 **오염 여부가 미검증**이다.
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
| ~~SentencePiece (Kudo & Richardson 2018, arXiv:1808.06226)~~ | ✅**2026-08-28 원문 확인**(사용자 제공 PDF). **EMNLP 2018 System Demonstrations, D18-2012, DOI 10.18653/v1/D18-2012.** → §9.5 |
| ~~MEGABYTE 본문 BPB 표·모델 크기 (arXiv:2305.07185)~~ | ✅**2026-08-28 원문 확인**(arXiv:2305.07185v2, NeurIPS 2023). Table 2·3·12 전수 확인 → §9 |
| ~~SpaceByte 모델 크기·BPB (arXiv:2404.14408)~~ | ✅**2026-08-28 원문 확인**(arXiv:2404.14408v3, **NeurIPS 2024**, 단독저자 Kevin Slagle). Table 1·3·5 전수 확인 → §9.1~9.4 |
| BLT 논문 내 해시 임베딩 파라미터 수 | ★**논문이 보고하지 않는다.** 계산식은 공식 코드에서 확인, 총량은 우리 계산 |
| KLUE 사전학습 코퍼스 규모·토크나이제이션 ablation 표 | **미확인** |
| byte-fallback 의 통제된 downstream delta | ★**전용 논문을 찾지 못했다** |

---

## 12. ★★2026-08-28 추가 — **gemma 를 빼놓았다.** 이유가 없었다

사용자 지적: *"왜 `models--google--gemma-3-1b-pt` 및 `gemma-3-270m` 토크나이저·교사를 제외했는지?"*

> 🚫★**타당한 이유가 없다. 누락이다.**
> 이 문서를 쓸 때 나는 **문헌**과 **우리가 실제로 돌린 P067 실험(Qwen)** 만 보고 썼고,
> **저장소가 이미 갖고 있는 gemma 조사를 열지 않았다.** 그 조사는 두 곳에 있었다:
> [`docs/20260820_Qwen-Gemma-토크나이저-교사모델-적용성-분석.md`](../20260820_Qwen-Gemma-토크나이저-교사모델-적용성-분석.md) 와
> [`test_plan/P067`](../../test_plan/P067_외부-토크나이저와-외부-교사.md) §의 모델 실사표.
> ★**남이 쓴 문헌은 열었는데 우리가 쓴 문서를 안 열었다** — 규칙 R32 의 거울상이다.

### 12.1 저장소가 이미 확인해 둔 것 (P067 실사표)

| 모델 | 아키텍처 | 교사 가능 | 층 | dim | **어휘** | dtype | 로컬 보유 |
|---|---|---|---:|---:|---:|---|---|
| `Qwen3-0.6B-Base` | `Qwen3ForCausalLM` | ✅ | — | — | **151,936** | bf16 | ✅ |
| ★**`gemma-3-270m`** | `Gemma3ForCausalLM` | ✅**YES** | **18** | **640** | ★**262,144** | bf16 | ✅ |
| ★**`gemma-3-1b-pt`** | `Gemma3ForCausalLM` | ✅**YES** | 26 | 1152 | ★**262,144** | bf16 | ✅ |
| `gemma-4-E2B` | `Gemma4ForConditionalGeneration` | 🚫**NO** | 35 | 1536 | 262,144 | bf16 | ✅ |

### 12.2 ★**gemma 가 특히 값어치 있는 이유 세 가지**

| # | 왜 |
|---|---|
| ★**1** | **어휘 축의 세 번째 점**이다 — 우리 **32,768** / Qwen **151,936** / gemma **262,144**. §1 의 어휘 크기 논쟁을 **8배 범위**에서 잰다. 두 점으로는 곡선을 못 그린다 |
| ★★**2** | **`gemma-3-270m` 은 270M** 이다. Qwen3-0.6B(600M)보다 **우리 100M 에 훨씬 가깝다.** 교차 토크나이저 증류 문헌(§7)이 말하는 *"교사–학생 격차가 작을수록 정렬이 쉽다"* 를 시험할 수 있는 유일한 로컬 교사다 |
| **3** | 어휘 262,144 는 §5 의 **가지치기 위험구간**을 정면으로 친다 — `32,768 / 262,144 = 12.5%` 로 Bogoychev 2024 의 중국어 붕괴 사례(20.6%)보다 **더 공격적**이다. 가지치기 한계를 재는 자연 실험이 된다 |

### 12.3 🚫★★**2026-08-29 정정 — 내가 P075 의 제약을 P067 에 적용했다**

종전 이 절은 *"gemma 262,144 는 int8 상주 64.2 MiB 라 **학생 후보가 아니다**"* 라고 적었다.
🚫**틀렸다.** 사용자 지적:

> *"P067 실험에서는 토크나이저로 인해 학생의 상주 메모리가 증가하더라도 그 부분은 신경쓰지 말고,
> 실제 토크나이저가 학생의 품질을 얼마나 향상시킬 수 있는지를 확인해야 한다."*

★**그리고 그것이 P067 계획서에 이미 적혀 있다** — §6 X5:

> *"★**X2 가 이겨도 배포 모델로는 못 쓴다** … ★**이 실험은 "KD 가 원리적으로 되는가" 를 묻는 것이지
> 배포안이 아니다**"* / *"어휘 축소는 **별도 실험**이고, 사용자도 그렇게 지시했다."*

→ ★**P067 은 상주를 판정 기준에서 뺀 실험**이고 **P075 가 상주를 보는 실험**이다.
**두 실험의 제약을 섞은 것은 내 잘못**이고, 그 결과 *"gemma 는 후보가 아니다"* 라는
**계획에도 없는 배제**를 문서에 써 넣었다.

### 12.4 ★★그럼 **얼마나 좋아야 값어치가 있나** — 바(bar)를 숫자로 놓는다

사용자 논지가 맞다 — *"토크나이저가 상주 증가 이상으로 품질을 올리면 더 큰 토크나이저를 쓸 타당성이 생긴다."*
그 *"이상"* 을 우리는 **레버 가격**으로 쓸 수 있다. 기준선은 `mC_g16` 의 **0.000447 nats/MiB**
(`EXPERIMENT_BASELINES` §2.2c). **그보다 싸게 품질을 사면 이득**이다.

`emb_rank 256` · **임베딩 int8**(이미 채택, +0.0001) 기준으로 계산하면:

| 토크나이저 | 어휘 | 임베딩 파라미터 | int8 상주 | 우리 대비 증가 | ★**넘어야 하는 품질 바** |
|---|---:|---:|---:|---:|---:|
| **우리(현재)** | 32,768 | 8.59M | **8.19 MiB** | — | — |
| **Qwen3** | 151,936 | 39.09M | 37.28 | **+29.1** | ★**−0.0130 nats** |
| **gemma-3** | 262,144 | 67.30M | 64.18 | **+56.0** | ★**−0.0250 nats** |

> ★★**바가 우리가 측정해 온 효과 크기 범위 안에 있다.**
> 비교: 재귀 R2 **−0.0202** · CLA1 **−0.0268** · 순환 방문 **−0.0157** · 36층 ag4 **+0.0072**.
> → 🚫**"예산 밖" 이라고 잘라 말할 근거가 없다. 재 보면 되는 크기**다.
>
> ⚠️**단 바는 임베딩 저장 형식에 따라 크게 달라진다** — fp32 로 계산하면 Qwen 바가
> **−0.0520**, gemma 가 **−0.1000** 으로 4배가 된다. **어느 배포 형식을 전제하는지 반드시 함께 적는다.**
> 🚫**그리고 이 바는 상주만 본다** — KV 캐시·벽시계는 안 들어 있다.

### 12.5 ★그래서 gemma 의 자리

| 실험 | gemma 의 역할 | 상주를 보나 |
|---|---|---|
| ★**P067**(외부 토크나이저·교사) | ★**학생 토크나이저 후보 + 교사 후보 둘 다.** 제약 없음 | 🚫**안 본다**(계획 §6 X5) |
| **P075**(어휘 예산) | **비교군**(어휘 축의 세 번째 점) | ✅**본다** — 여기서 §12.4 의 바로 판정한다 |

## 13. ★★★공통 원문(common text) — **무엇이고, KorQuAD·SQuAD 가 적합한가**

사용자 질문: *"한국어 공통 원문이라는 것이 벤치마크/토크나이저 성능 검증용 데이터를 의미하는 것이라면 KorQuAD 활용 가능한가."*

### 13.1 무엇인가 — **과제 벤치마크가 아니다**

> ★**공통 원문 = 어휘가 서로 다른 모델들을 같은 자로 재기 위한 "같은 바이트 열" 이다.**

토크나이저가 다르면 **토큰 수가 다르므로** 토큰당 손실(CE)·perplexity 를 직접 비교할 수 없다 —
**어휘가 클수록 자동으로 유리하게 나온다.** 그래서 The Pile §3.1 의 정의를 쓴다:

```
bpb = (L_T / L_B) · log₂(e^ℓ)        L_T = 토큰 수, L_B = UTF-8 바이트 수
```

**분모가 바이트**이므로 토크나이저가 달라도 비교가 성립한다. 이때 필요한 것은
**정답도, 과제도 아니고 "모든 후보가 통과하는 동일한 원문"** 이다.
→ 🚫**KorQuAD 의 질문·정답은 쓰지 않는다. 쓰는 것은 `context` 지문의 바이트 열뿐이다.**

### 13.2 ★적합성 요건 다섯

| # | 요건 | 왜 |
|---|---|---|
| **C1** | **학습 데이터와 겹치지 않는다** | 겹치면 그 모델만 외운 것을 잰다. 사용자 지적 그대로 |
| **C2** | 자연스러운 산문 | 목록·표·코드는 bpb 를 비정상적으로 낮춘다 |
| **C3** | 충분한 바이트 | 현 영문 원문은 **2.97 MB / 4,000문서** — SE 를 계산한 적이 없다 |
| **C4** | 도메인이 한쪽으로 안 쏠린다 | 위키 전용이면 위키를 많이 본 모델이 유리하다 |
| **C5** | 재현 가능한 고정 스냅샷 | 판정을 6개월 뒤에도 재현해야 한다 |

### 13.3 🚫★★**C1 이 위험하다 — KorQuAD 도 SQuAD 도**

| 원문 후보 | 출처 | 우리 학습 풀 `ko-en` 의 해당 절반 | **겹칠 가능성** |
|---|---|---|---|
| **KorQuAD 1.0 context** | **한국어 위키백과** 1,647문서 | ★**`wikimedia/wikipedia`(ko) — 182,795문서, 문자의 24.3%**(결과 031 §1.1) | 🚫★★**매우 높다.** 같은 코퍼스다 |
| **SQuAD v2 context**(현재 사용 중) | **영어 위키백과** | `HuggingFaceFW/fineweb-edu` — CommonCrawl 파생 | ⚠️**중간~높음.** fineweb-edu 는 교육적 텍스트를 선호하는 분류기를 쓰므로 **위키백과가 높은 점수를 받는다.** 배제했다는 근거를 우리는 갖고 있지 않다 |

> 🚫★★★**즉 지금 인용 중인 bpb 수(결과 053: 1.3075 / 1.3363 / 1.3440 / 1.3999)조차
> 오염 여부가 검증되지 않았다.** 우리 모델(`mC_initonly`)이 가장 낮은 bpb 를 낸 것이
> **토크나이저가 좋아서인지 그 원문을 학습에서 봤기 때문인지 구분되지 않는다.**
> ⚠️**이것은 새로 생긴 문제가 아니라 처음부터 있었고 아무도 확인하지 않은 것**이다.

### 13.4 ★검증 실험 — **GPU 0, 학습 0**

계획서 [P075 §5](../../test_plan/P075_토크나이저-어휘예산과-한국어-분절.md) 에 단계 0 으로 넣었다.

| 무엇 | 어떻게 | 판정선 |
|---|---|---|
| **O1 겹침 측정** | 후보 원문을 문장 단위로 자르고 **13-gram(문자) 해시**를 만들어 `data_cache/ko-en_600000000` 스트림의 해시 집합과 대조 | **문서의 13-gram 이 1% 이상 히트하면 그 문서를 제외**한다(GPT-3 계열 관행) |
| **O2 대조군** | 학습 풀에서 뽑은 문서로 같은 측정 | O1 이 도구의 민감도를 갖는지 확인한다. **대조군이 100% 근처가 안 나오면 측정이 고장난 것** |
| **O3 SE** | 원문을 10등분해 bpb 를 따로 재고 표준오차 | C3. **0.008 분해능이 이 원문에서 실제로 성립하는지** 처음 확인한다 |

### 13.5 ★그래서 한국어 공통 원문으로 무엇을 쓰나 — **세 후보**

| 후보 | 장점 | 위험 | 판정 |
|---|---|---|---|
| **KorQuAD 1.0 context** | 자연 산문·문단 단위·고정 스냅샷·이미 로컬 | 🚫**C1 위반 가능성 매우 높다**(위키 = 학습 풀) | ⚠️**O1 통과분만** 쓴다. 전부 탈락하면 아래로 |
| ★**KLUE-YNAT / 뉴스 계열** | ★**위키가 아니다** → C1 이 훨씬 안전. 자연 산문 | 문장이 짧다(제목 위주) → C2·C3 확인 필요 | ★**O1 을 통과하면 1순위** |
| **국립국어원 모두의말뭉치** | 규모·도메인 균형 | 라이선스·신청 필요, 스냅샷 고정이 번거롭다 | ⏸사용자 판단 |

★**권장**: **KorQuAD 를 후보에서 빼지 않는다.** 다만 **O1 을 먼저 돌려 겹치는 문서를 제외**하고,
남은 바이트가 **1 MB 미만이면 KLUE 계열로 교체**한다. 판단 기준을 숫자로 정해 두는 것이 요점이다.

### 13.6 ⚠️영문 쪽도 같이 고친다

**SQuAD 를 계속 쓰되 O1 을 통과한 문서만 남긴다.** 그리고 **결과 053 의 bpb 네 수에는
"오염 미검증" 표시를 유지**한다 — O1·O3 가 끝나면 그때 표시를 뗀다.
🚫**그 전에는 이 수로 토크나이저 서열을 확정하지 않는다.**
