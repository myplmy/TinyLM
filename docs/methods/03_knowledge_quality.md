# 3. 지식 품질 향상

압축(타잉·삼진)으로 잃는 지식/성능을 되찾거나, 절대 품질을 끌어올리는 기법.
기존 정본은 val cross-entropy(perplexity)다. P069에서 downstream 평가가 일부 도입됐지만,
외부 토크나이저 체크포인트(Qwen/Gemma)는 아직 그 평가 경로에 연결되지 않았다(§2026-09-01).

| 기법 | 상태 | 버전 | 작동원리(개선 기여) | 트레이드오프 | 특기 |
|---|---|---|---|---|---|
| **KD (내부 dense 교사)** | ✅**측정·300M 표준에서 제거** | v6 (`--kd`) | dense 로짓을 FKL로 따라감 | 교사 forward·큰 KL VRAM. **어휘 일치 필수** | P002에서는 부모초기화와 함께 좋아 보였으나 P050 분해 후 loss 감소 기여는 **부모 +0.1386 vs KD −0.0032**: 절대크기 43배이며 KD 부호는 악화 방향(loss +0.0032). 300M 두 seed에서 KD가 +0.0208/+0.0219 나빴다. 단 100M에서는 **−0.110**으로 예산 의존 |
| **부모초기화 (average-init)** | ✅**측정·채택** | v6 (`--init-from`) | 공유 MLP를 dense 그룹 g층 평균으로 초기화 → 수렴·격차 개선 | dense 체크포인트 필요 | P050 실측 loss 감소 기여 **+0.1386**, KD 기여 **−0.0032의 절대크기보다 43배**. 외부 대형 vocab에서는 shape 불일치로 현재 사용 불가 |
| **더 많은 토큰 / 더 긴 학습** | ✅**측정(부분 기각)** | — | undertraining 해소 → 절대 품질↑ | GPU 시간(선형) | ★결과 006: 절대품질은 개선되나 **수확체감 급격**(100→300M **-0.66**, 300→600M **-0.18**). **"타잉 격차↓" 부분은 기각** — 격차가 6배 토큰에서 +0.149→+0.168→+0.166 로 평평. 300M은 파라미터당 ~4토큰(Chinchilla ~20) |
| ★★**반복 노출(다회 epoch)** | ⏳**미측정** | — | ★**풀을 고정하고 학습토큰만 늘린다** — 같은 토큰을 여러 번 본다. 유니크 토큰 축과 **다른 축**이다 | 학습시간 ×N. ★**배포 상주 증가 0** | 🚫**우리는 평균 0.5 epoch 밖에 안 돌았다**(풀 600M 에서 300M 학습). **1 epoch 을 넘겨 본 적이 없다.** 문헌(arXiv:2305.16264)은 **4 epoch 까지 거의 무손실**이라 하지만 ⚠️**고정 compute 가정이라 우리(모델 크기 고정)에 직접 외삽 불가**. ★제안서 [`20260903_반복노출축-1-2-4epoch.md`](../../proposal/done/20260903_반복노출축-1-2-4epoch-approved.md) |
| **★데이터 풀 다양성** | ✅**측정·채택** | v6 (`--pool-tokens`) | 학습토큰 고정, 샘플 풀만 확대 → 반복 노출 감소 | 토큰화 1회·디스크. 학습시간 증가 **0** | ★결과 006: 풀 300M→600M 만으로 dense **-0.12**(타잉 격차의 70%에 해당). **가장 값싼 품질 레버.** 신규 기준선은 풀 ≥ 2× 학습토큰. 포화점 미측정. 풀이 다른 런끼리 **직접 비교 금지** |
| **ternary-LoRA / 기타 층별 특화** | ⚠️**구 조건 부분 측정(FiLM 제외)** | v6 | 공유층을 층별로 특화 → 표현력 복원 | t_lora32 메모리 1.72×, `grad_max=6.2` | 초기 300M에서 t_base 대비 **−0.0337/−0.0338** 실측. 현재 no-KD+parent 표준에서 독립 재검증은 미실행. FiLM은 아래 P044B에서 별도 기각 |
| **EMA / 체크포인트 병합** | 🧪 | v6 (`--ema`) | 최근 가중치 평균 → 무료 품질 향상 | decay 스케일 주의(6번) | 근거 WSM/EMA(2025) |
| **다운스트림 평가** | ⚠️**부분 도입** | P069/P080 | val CE와 실제 능력을 분리 | 구현·평가·통계 비용 | native에서 HellaSwag·PIQA·ARC-e가 서열 후보. 외부 tokenizer 지원과 TinyDataset 모델 forced-choice는 미구현; v2.4는 파일/token gate만 있고 MANIFEST 정본은 아직 v2.3 |
| **외부 교사 증류(Qwen/Gemma)** | ⚠️**부분 측정** | v6 (`--kd-teacher-hf`) | 더 강한 공개 교사의 token 분포를 모사 | 큰 어휘·부모초기화 상실·교사 forward·평가 배선 | **Qwen −0.0077 common-bpb = 기존 실무 규칙 0.008 바로 아래, 단일 시드. Gemma 270M은 250-step backward/VRAM probe뿐이고 `grad_max`: 무KD GT0 36.9, KD 118.8/488.8로 모두 기존 `>10` gate 실패; 원인이 KD인지 Gemma-vocab 학생 공통인지 미분리, full 품질 미실행.** §2026-09-01 |
| **고품질/curated 데이터** | ⚠️**판정 불가** | v4~(부분) | 교과서·QA·FineWeb-Edu 비율↑ → 적은 토큰으로 목표 loss | 절대품질용(타잉 격차엔 무관) | **이미 부분 적용**: en=FineWeb-Edu. ★결과 009(P012): ko-edu-en(`eliceai/korean-webtext-edu`) 관측은 열세(bpb 1.614 vs 1.234)지만 **토크나이저·val셋이 달라 판정 불가**. 게다가 그 캐시는 train 3.03/val 6.17 = **3.14 nats 괴리**(중복 또는 val 분포이동 의심) → ★**결과 011(P028 단계0): 원인 확정** — val 분포이동(JS 9.9× vs 대조군 1.26×)이 주범, 문서중복(5.69%)이 보조. **P012 무효 확정·캐시 폐기 대상.** P028 |
| **bits-per-byte 지표** | ✅**공통 원문 구현·적용범위 제한** | `scripts/common_bpb.py` | 같은 raw text의 byte당 손실로 이종 tokenizer 비교 | corpus·언어·오염에 의존 | Qwen/Gemma 교차비교의 유효 경로. 현재 정본은 영문 SQuAD train context라 한국어 지능을 못 재며, P075 dev overlap 12%와 split이 달라 train을 재감사해야 함 |
| **★★SEO 스팸 필터로 학습** | ✅**측정** | v6 (`--doc-filter`, P028 단계3) | [결과 018](../../test_result/018_20260731190000_P037-단계1-경계는정상-원인은스팸문서.md)이 실측한 서명(대형 ∧ 줄바꿈~0% ∧ 줄 고유율 100%)으로 문서 제외 후 **그 데이터로 학습** | 학습 예산 고정 시 **유니크 텍스트 13% 감소** | ★재학습 결과 **−0.296 nats(24.7σ)** — 우리가 측정한 **가장 큰 단일 품질 개선**이고 **아키텍처가 아니라 데이터**에서 나왔다. `ko-edu-en` 열세의 **63%가 스팸**이었다([결과 011 §2](../../test_result/011_20260730135000_P028-단계0-캐시진단.md)) |
| **`ko-en` 표준 train 스팸 감사** | ✅**측정·필터 재학습 종결** | [P047](../../test_result/031_20260807_P047-ko-en은-깨끗하다-기준선이-안전하다.md) | 같은 SEO 서명으로 표준 train 전수 검사 | 추가 필터의 기대효과가 비용보다 작음 | 366,819문서 중 6개, 문자 **0.06229%**, 예상 **−0.00098 nats**. `ko-en` 기준선은 안전하며 이 사유의 전 기준선 재학습은 하지 않음 |
| **어휘 재학습(필터 데이터로)** | 💡**가설·미측정** | — (D-7) | 결과 018은 val의 SEO 서명만 측정했으며 tokenizer 20만 표본과의 교집합은 측정하지 않았다. 필터 후 어휘가 좋아질 가능성은 별도 가설 | **전 모델 재학습** | 표준 `ko-en`은 P047에서 거의 깨끗했다. bpb −0.01~0.05는 실측이 아닌 기존 추정이므로 tokenizer-sample audit 전 우선순위 승격 금지 |
| ~~FiLM 층별 조건화~~ | 🚫**기각** | v6 (`--mlp-film`, P044/P044B) | 공유 MLP 은닉을 층별 scale/shift 로 | 0.13MB(정직하게 계상됨) | 결과 027 paired **+0.0003**(SE 0.0004, t=0.65); [P044B 무KD 재검증](../../test_result/063_20260831_P044B-FiLM-은-무KD-표준조건에서도-자를-못-넘는다-종결.md)도 **+0.0003**. 원인은 KD가 자리를 차지해서가 아니라 **이 규모에서 FiLM 자체가 무효**. 부수: `grad_max` 0.847→**1.855** |

## 논거 요약

- 손실(CE/perplexity)은 다운스트림과 **집계적으로** 상관(스케일링 법칙)하나, 과제 의존이고
  사전학습 손실이 파인튜닝 후 성능을 깔끔히 예측하진 못함 → val_loss·격차는 **필요하나 불충분**.
- 타잉 페널티는 규모·학습량↑에서 감소(Tying the Loop 7B에서 g=4 동률).

---

## 2026-09-01 — 외부 교사 KD와 모델 지능 개선 조사 반영

상세 보고서와 실험 설계의 정본은 다음 두 문서다.

- [모델 품질·지능 향상 조사 결과](../20260901_모델-품질-지능-향상-조사결과.md)
- [P082 — Qwen·Gemma 교사 지능향상 KD 후속실험](../../test_plan/P082_Qwen-Gemma-교사-지능향상-KD-후속실험.md)

### 1. 현재 판정

| 항목 | 증거 | 현재 판정 |
|---|---|---|
| 내부 dense KD, 300M | 무KD 3.6776 vs KD 3.6984, 두 시드 대가 +0.0208/+0.0219, VRAM 12.47→5.07 GiB | ✅**표준조건에서는 제거 유지** |
| 내부 dense KD, 100M | KD가 −0.110 | ⚠️**작은 학습예산에서는 재검토 가능** |
| Qwen3-0.6B-Base | `Q256T 1.3363` vs `QT0 1.3440` common-bpb = **−0.0077** | ⚠️**좋은 방향이나 0.008 분해능 미만·단일 시드**. ✅2026-09-02 로그 원본 대조 완료 — 이 두 수가 정본이다(결과 053 §S1.7.1) |
| Gemma 3 270M | 250-step backward/VRAM probe, 14.77GB, full 예상 8.8h. `grad_max`: 무KD GT0 36.9, KD 118.8(narrow 488.8) | 🚫**품질 미측정 + 모두 기존 수치 안정성 gate 실패. KD 원인 미분리, matched N0 안정화 전 full 금지** |
| 외부 KD의 지능 평가 | 외부 tokenizer를 bench/generate가 못 읽음 | 🚫**현재 불가. 평가 배선이 선결** |

★★**따라서 기존 REVIEW2 결론은 폐기하지 않는다.**
“300M 표준조건의 내부 dense KD 제거”는 유효하다. 외부 좋은 교사는 별도 축이며,
Qwen의 작은 신호만으로 표준조건을 되돌리거나 Gemma 효과를 추정하지 않는다.

### 2. 현재 외부 KD가 전달하는 것과 전달하지 않는 것

현재 구현은 같은 입력 crop에서 full-vocab **forward KL**을 계산해
`(1-α)·CE + α·KL`로 학습한다. P067은 `α=0.5`, `T=2`, `kd_every=4`라
2,289스텝 중 573스텝만 교사 forward를 쓴다.

| 구현됨 | 미구현·미연결 |
|---|---|
| HF Base/PT teacher logits, vocab-size 검사, fp32 chunk KL | tokenizer 파일 hash·id mapping·special-token 검증 |
| Qwen/Gemma tokenizer 캐시와 `uint32` | teacher entropy/confidence/advantage 기반 token weighting |
| CE와 FKL 혼합, skip-forward | reverse KL·JSD·skew-KL·mixed on-policy |
| 외부 tokenizer common-bpb | 외부 tokenizer HellaSwag·PIQA·ARC-e·한국어·TinyDataset 평가 |
| chat serializer 유틸리티 | SFT loader, assistant-only loss, rationale/sequence KD |
| 내부 dense offline top-k cache | HF offline cache, 완전한 provenance 검증, tail-mass 보존 |
| `--exact-cache` 옵션 | cache identity의 tokenizer/filter/raw-manifest hash hard fail; `exact=False` 재사용은 이름/token 수 중심이라 P082 금지 |

이 경로는 **generic next-token 모사**다. Base/PT teacher의 raw logits만으로 지식 QA·추론·지시이행이
자동 전수된다고 가정하지 않는다.

### 3. 개선 순서

1. **평가부터 연결**: 외부 tokenizer resolver를 생성·3개 채택 벤치·한국어·TinyDataset에 공통 적용한다. v2.4는 파일과 token shortcut gate만 있고 MANIFEST 정본은 아직 v2.3이므로 먼저 v2.4 승격/hash와 모델 forced-choice evaluator를 확정한다.
2. **정합성 고정**: checkpoint에 tokenizer ID/hash, vocab, special IDs, teacher snapshot hash를 저장·검증하고, `--exact-cache`와 전체 cache identity hard fail을 함께 적용한다.
3. **teacher advantage 측정**: 같은 prompt/shot/채점기로 teacher CE·정확도·entropy·margin을 잰다.
4. **완전한 대조군**: Qwen은 `QT0`, Gemma는 full-budget `GT0`가 직접 대조군이다. native CE와 교차 비교하지 않는다.
5. **직접 유사한 pretraining-KD부터 탐색**: FKL/teacher-top1 NLL, `T={0.5,1,2}`, `every={1,2,4}`, `α={.25,.5,.9}`와 max-LR high-KD→decay WSD schedule을 비교한 뒤 JSD/skew-KL로 넓힌다. ACL 2025 high-α 결과와 내부 300M α sweep의 반대 증거를 함께 검정하고 CE/KD gradient norm·cosine을 기록한다.
6. **짧은 sequence/rationale KD**: 동일 source·수락 문항·assistant token 또는 총 compute로 reference/gold SFT와 teacher answer-only/rationale를 비교한다. 100M급의 짧은 trace 80~95%, 긴 trace 5~20%는 선행연구의 직접 결론이 아니라 시작 가설이다. 현 tokenizer plain-boundary pilot과 P075 새 tokenizer를 분리하고, 새 tokenizer면 부모 row mapping/graft 또는 새 부모가 선결이다.
7. **조건부 mixed on-policy**: prompt→response 경계와 일정 품질의 SFT 학생을 먼저 갖추고 학생 prefix `λ={0.25,0.5}`에서 teacher 피드백을 준다. generic raw-document crop 적용은 별도 pretraining 외삽으로 표기한다.
8. **native-tokenizer 증류**: sequence KD 후 ALM을 먼저 보고, DSKD/CDM/DWA-KD/BLD를 조건부 확장한다. 큰 Qwen/Gemma vocab 이식은 배포 기본안이 아니다.

🚫단순히 KL 인자 순서를 뒤집은 것을 MiniLLM이라고 부르지 않는다. MiniLLM/GKD의 핵심은
학생이 생성한 상태에서 학습하는 on-policy 경로와 안정화다.

### 4. 지능 평가 규칙

- **common-bpb/val CE 개선 ≠ 지능 향상**이다.
- 1차 지표는 정확한 tokenizer로 잰 HellaSwag·PIQA·ARC-e와 검증된 TinyDataset held-out이다.
- seed 3개와 per-item paired bootstrap/McNemar를 사용하고, 한 과제만 오른 결과를 종합 지능 향상으로 부르지 않는다.
- `common_bpb.py`는 SQuAD **train-v2.0**을 쓰지만 P075 overlap audit는 **dev-v2.0**을 썼다. train 정본을 다시 감사하기 전 오염률 12%를 그대로 적용하지 않는다.
- Gemma 250-step probe의 val은 품질 결과가 아니다. 무KD GT0도 `grad_max=36.9`, KD는 118.8/488.8로 기존 수치 안정성 gate를 모두 실패해 원인이 KD인지 Gemma-vocab 학생 공통인지 아직 분리되지 않았다.
- SFT/선호학습, RAG/도구, test-time compute의 효과는 각각 사전학습 지식·내재 능력과 분리한다.

### 5. KD 외 우선 레버

| 우선 | 레버 | 현재 근거 |
|---:|---|---|
| **1** | 부모초기화 | loss 감소 기여 **+0.1386**; KD 기여 **−0.0032**의 절대크기보다 43배 |
| **2** | 데이터 정제·다양성 | SEO 필터 common-bpb **−0.1058**; 가장 큰 단일 실측 레버. 평가 오염 재감사 필요 |
| **3** | 깊이·구조 | dense d8/d12/d16/d20 = 3.6776/3.6130/3.5757/3.5418, 20층까지 미포화 |
| **4** | 재귀/latent compute | HellaSwag·PIQA 양의 신호(30.0→33.7 / 51.7→53.7). ⚠️★**단 정답 CE 는 기준선이 이긴다**(3.6240 vs 3.9226, 결과 056) — **캘리브레이션은 나빠지고 순위만 좋아졌다.** 두 지표가 갈라지므로 *'재귀가 지능을 올린다'* 로 요약하지 않는다. reasoning인지 단순 용량인지 별도 판정 |
| **5** | 고밀도 데이터 실제 연결 | TinyDataset의 관계·paraphrase·near-negative가 현재 학습되지 않음 |
| **6** | SFT→선호학습 | 행동·형식 지능에 직접적이나 loader/mask/evaluator가 선결 |
| **7** | RAG·도구 | 외부 지식 정확도에는 강력하나 모델 자체 지능과 별도 보고 |

### 6. 핵심 선행연구

- [MiniLLM, ICLR 2024 공식 제목/페이지](https://openreview.net/forum?id=5h0qf7IBZZ) · [arXiv v6](https://arxiv.org/abs/2306.08543) · [DOI](https://doi.org/10.48550/arXiv.2306.08543)
- [GKD, ICLR 2024](https://arxiv.org/abs/2306.13649) · [DOI](https://doi.org/10.48550/arXiv.2306.13649)
- [DistiLLM, ICML 2024](https://arxiv.org/abs/2402.03898) · [DOI](https://doi.org/10.48550/arXiv.2402.03898)
- [Pre-training Distillation Design Space, ACL 2025](https://aclanthology.org/2025.acl-long.181/) · [DOI](https://doi.org/10.18653/v1/2025.acl-long.181)
- [Sparse Logit Sampling, ACL 2025](https://aclanthology.org/2025.acl-long.885/) · [DOI](https://doi.org/10.18653/v1/2025.acl-long.885)
- [Sequence-Level Knowledge Distillation, EMNLP 2016](https://aclanthology.org/D16-1139/) · [DOI](https://doi.org/10.18653/v1/D16-1139)
- [Teaching Tiny Minds, CoNLL-BabyLM 2024](https://aclanthology.org/2024.conll-babylm.27/) — 44M/58M·10M-word 영어 조건의 직접 소형모델 근거
- [Capacity Gap, ACL 2025](https://aclanthology.org/2025.acl-long.1097/) · [DOI](https://doi.org/10.18653/v1/2025.acl-long.1097)
- [Small Models Struggle to Learn from Strong Reasoners, Findings ACL 2025](https://aclanthology.org/2025.findings-acl.1301/) · [DOI](https://doi.org/10.18653/v1/2025.findings-acl.1301)
- [Approximate Likelihood Matching, NeurIPS 2025](https://papers.neurips.cc/paper_files/paper/2025/hash/720f9f5dc751eb56952ae4fee2398f73-Abstract-Conference.html) · [DOI](https://doi.org/10.52202/085713-2653)
- [DWA-KD, Findings EACL 2026](https://aclanthology.org/2026.findings-eacl.181/) · [DOI](https://doi.org/10.18653/v1/2026.findings-eacl.181)
- [Byte-Level Distillation, CustomNLP4U 2026](https://aclanthology.org/2026.customnlp4u-1.9/) · [DOI](https://doi.org/10.18653/v1/2026.customnlp4u-1.9)
