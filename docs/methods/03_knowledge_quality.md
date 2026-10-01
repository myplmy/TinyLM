# 3. 지식 품질 향상

압축(타잉·삼진)으로 잃는 지식/성능을 되찾거나, 절대 품질을 끌어올리는 기법.
기존 정본은 val cross-entropy(perplexity)다. P069에서 downstream 평가가 일부 도입됐지만,
외부 토크나이저 체크포인트(Qwen/Gemma)는 아직 그 평가 경로에 연결되지 않았다(§2026-09-01).

| 기법 | 상태 | 버전 | 작동원리(개선 기여) | 트레이드오프 | 특기 |
|---|---|---|---|---|---|
| **KD (내부 dense 교사)** | ✅**측정·300M 표준에서 제거** | v6 (`--kd`) | dense 로짓을 FKL로 따라감 | 교사 forward·큰 KL VRAM. **어휘 일치 필수** | P002에서는 부모초기화와 함께 좋아 보였으나 P050 분해 후 loss 감소 기여는 **부모 +0.1386 vs KD −0.0032**: 절대크기 43배이며 KD 부호는 악화 방향(loss +0.0032). 300M 두 seed에서 KD가 +0.0208/+0.0219 나빴다. 단 100M에서는 **−0.110**으로 예산 의존 |
| **부모초기화 (average-init)** | ✅**측정·채택** | v6 (`--init-from`) | 공유 MLP를 dense 그룹 g층 평균으로 초기화 → 수렴·격차 개선 | dense 체크포인트 필요 | P050 실측 loss 감소 기여 **+0.1386**, KD 기여 **−0.0032의 절대크기보다 43배**. 외부 대형 vocab에서는 shape 불일치로 현재 사용 불가 |
| **더 많은 토큰 / 더 긴 학습** | ✅**측정(부분 기각)** | — | undertraining 해소 → 절대 품질↑ | GPU 시간(선형) | ★결과 006: 절대품질은 개선되나 **수확체감 급격**(100→300M **-0.66**, 300→600M **-0.18**). **"타잉 격차↓" 부분은 기각** — 격차가 6배 토큰에서 +0.149→+0.168→+0.166 로 평평. 300M은 파라미터당 ~4토큰(Chinchilla ~20) |
| ★★**반복 노출(epoch-equivalent)** | ✅**1·2·4회 측정·paired 회수** | P087/P088 | ★**풀을 고정하고 draw·steps를 늘린다.** Loader가 복원추출 random crop이라 순차 epoch가 아니라 `draw/pool`의 편의명이다 | 학습시간 ×N, WSD 절대 지평도 함께 증가. ★**배포 상주 증가 0** | [결과 073](../../test_result/073_20260904_P087-두-번째-epoch은-과적합-없이-0.1155를-준다.md): 같은 300M pool에서 **3.64328→3.52781→3.45344**, 과적합 징후 0. Stage3 누락 paired는 3.3728 vs3.5844, Δ−0.2116·t−246.93로 회수됐다. 단일시드 checkpoint 판정이며 4회 역사 런을 신규 후보 SH로 반복하지 않는다 |
| **★데이터 풀 다양성** | ✅**측정·조건부 채택** | v6 (`--pool-tokens`) | 학습토큰 고정, 샘플 풀만 확대 → 기대 유니크 토큰 증가 | 토큰화 1회·디스크. 학습시간 증가 **0**. 한국어 원천 소진 시 언어비 교락 | 결과 006의 로그-val `−0.1196`은 pool별 시험지 변화와 섞였다. 같은 영어 common text에서는 300M draw의 pool 600M→1.2B가 **bpb 1.2878→1.2728(−0.0150)**였으나 큰 pool은 영어 비중도 높다([결과 075](../../test_result/075_20260905_P088-토큰은-스텝이었고-full-val-은-학습데이터였다.md)). 다양성 방향은 유지하되 **언어비를 보존하고**, 풀이 다른 로그 val은 직접 비교하지 않는다 |
| **ternary-LoRA / 기타 층별 특화** | ⚠️**구 조건 부분 측정(FiLM 제외)** | v6 | 공유층을 층별로 특화 → 표현력 복원 | t_lora32 메모리 1.72×, `grad_max=6.2` | 초기 300M에서 t_base 대비 **−0.0337/−0.0338** 실측. 현재 no-KD+parent 표준에서 독립 재검증은 미실행. FiLM은 아래 P044B에서 별도 기각 |
| **EMA / 체크포인트 병합** | 🧪 | v6 (`--ema`) | 최근 가중치 평균 → 무료 품질 향상 | decay 스케일 주의(6번) | 근거 WSM/EMA(2025) |
| **다운스트림 평가** | ⚠️**부분 도입** | P069/P080 | val CE와 실제 능력을 분리 | 구현·평가·통계 비용 | native에서 HellaSwag·PIQA·ARC-e가 서열 후보. 외부 tokenizer 지원과 TinyDataset 모델 forced-choice는 미구현; v2.4는 파일/token gate만 있고 MANIFEST 정본은 아직 v2.3 |
| **외부 교사 증류(Qwen/Gemma)** | ⚠️**부분 측정** | v6 (`--kd-teacher-hf`) | 더 강한 공개 교사의 token 분포를 모사 | 큰 어휘·부모초기화 상실·교사 forward·평가 배선 | **Qwen −0.0077 common-bpb = 기존 실무 규칙 0.008 바로 아래, 단일 시드. Gemma 270M은 250-step backward/VRAM probe뿐이고 `grad_max`: 무KD GT0 36.9, KD 118.8/488.8로 모두 기존 `>10` gate 실패; 원인이 KD인지 Gemma-vocab 학생 공통인지 미분리, full 품질 미실행.** §2026-09-01 |
| **고품질/curated 데이터** | ⚠️**세 시드 공통평가·전면 승자 없음** | v4~·P097 | 같은 원문 평가에서 source/tokenizer recipe를 분리해 확인 | source+tokenizer bundle과 recipe별 차등 오염 미측정 | [결과090 §14](../../test_result/090_20260919_P097-세-cache는-완성됐지만-학습은-0step이다.md): FineWeb2 YNAT 수치방향 3/3(유의2/3), control 영문 SQuAD-context bpb 3/3 낮음. NLI/Hella 우연 부근·ARC 방향 불일치, 기본 dataset 교체 근거 없음 |
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

## 2026-09-19 구조·selector·held-out 계약의 품질 한계

- P091 R2는 pipeline 계약을 통과했지만 selector `S`가 seed별 `rho=-1.0~0.4`라 안정적 품질
  신호가 아니다. `U`의 `rho=1.0`도 작은 fixture의 순위 계약이며 학습 개선 증거가 아니다.
- P093 Stage0c의 best rank16 output NRMS는 `0.974`이고 rank0 대비 개선은 약 `0.75%`뿐이다.
  단조 감소만으로 “근사 가능”이라 하지 않고 viability floor를 통과하기 전 모델 품질 실험을 열지 않는다.
- P095 S0b는 causal memory state의 계약과 backward만 확인했다. 기억 내용의 유용성·장기
  retention·Transformer 품질은 `NOT_RUN`이다.
- P096 Q2a의 320 synthetic canary는 schema/provenance/preservation 계약이다. 보호 실문항과
  사람 의미검토가 없으므로 held-out 품질 향상으로 승격하지 않는다.
- P097 네 recipe는 300M 학습·공통평가를 완주했으나 one-seed bundle 비교다.
  control/FineWeb2 교환을 세 seed에서 재현하기 전 새 혼합 recipe를 기본으로 승격하지 않는다.

## 2026-09-27 P106 외부 교사 자산과 지식 품질의 경계

[결과098 §5](../../test_result/098_20260925_P106-검증형-교사-레코드-계약만-통과했다.md)에서 공식 SHA와 같은 Bonsai 2 27B PTQ1_0의 Prism CPU/GPU 기술 구동 및 한 산술 문항 출력4를 확인했다. 모델 카드의 Apache-2.0 출처와 GPU 속도는 **독립 검증된 교사 정답률**이 아니다. 질문 가족별 한영 정답·완료/거절/불확실·accepted sample당 총 비용, 별도 verifier와 사람 품질 검토가 없으므로 검증형 P106의 교사 `ACCEPT`와 공개 한국어 데이터 `TRAIN_READY`는 아직 미판정이다. 원격·로컬 모델의 유창함만으로 **검증형 정답**이라 수락하지 않는다. 이는 별도 P106B에서 미검증 `PSEUDO_UNVERIFIED` 출력으로 소형 학습 기능을 시험하는 것을 금지한다는 뜻은 아니다.

[결과098 §6~§7](../../test_result/098_20260925_P106-검증형-교사-레코드-계약만-통과했다.md)의 GDN 융합 복구와 합성 학생 1-step 공존도 기술적 비용/자원 게이트일 뿐이다. 생성 한 문항, 합성 학생 손실과 공존 OOM0을 교사 정답성·검증 sample의 SFT 학습 적격성이나 학생 지능 향상으로 바꾸지 않는다.

[P106B 결과101](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)은 OASST2 영어 원답16개를 Bonsai가 한국어로 번역한 첫 형식 게이트에서 완결9/16(56.25%)·사전등록12/16 미달을 관찰했다. 뒤 학생 온라인 SFT는 상류 선결에서 중단되어 학습0회다. `INCOMPLETE` 7건의 개별 종료사유·사고내용/최종내용을 원본 코드가 버렸으므로 생각 토큰이 원인이라고 확정하지 않는다. 다만 학생 목표 구성 코드는 `message.content`의 완결 `user_ko`/`assistant_ko`만 canonical ChatML user/assistant로 보내고 `reasoning_content`를 받거나 지도하지 않는다. 새 재시험은 교사의 사고·최종답·종료사유를 데이터 원장에 **분리 저장**하고, 학생에게는 최종 assistant 본문만 전달하는 계약을 확인해야 한다. 새 모델 E2E와 사후 벤치 오답은 여전히 `NOT_RUN`이다.

후속 [결과101 §7~§9](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)은 실제 API의 사고/최종 필드를 분리했다. 권장 sampler·medium·ctx4096에서 과거 실패를 과표집한 같은4쌍의 cap768은 `length`4/4·최종0, cap3072는 `stop`/JSON3·사고만 남긴 `length`1이었다. 그러나 형식 회복만으로 데이터 품질은 회복되지 않는다. 원 OASST2 답의 WebRTC `getUserMedia` 인자 설명은 틀렸고 번역 교사는 이를 복제했다. 교정형 교사는 WebRTC API 주장을 바로잡았지만 GPT‑3 175B를 **175억**으로 새 오기했다(정본 1750억). 교사의 `CORRECTED`는 자기 보고일 뿐 독립 verifier가 아니다. 원문/번역/사고/교정본 v1/v2/v3와 [한정 점검표](../../test_result/evidence/P106B_Stage1dW_repair_review.json)를 보존하되 현재 교육 target 채택0, 학생 학습0으로 분리한다. 이를 교사 교정 불가나 한국어 품질 전면 음성으로 확대하지 않고, 이후 v4의 근거·거부행·오답 분석 계약 선결로 삼았다.

2026-09-28 [결과101 §10](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)의 v4 교정형16/16 구조화 출력은 형식 실패를 해소했지만 [16행 직접 검토](../../test_result/evidence/P106B_Stage1fW_candidate_review.json)에서 원문과 다른 성별·역명, 문자권 혼입, 문답 역할 역전 등 명백 결함8을 찾았다. 추가검토4·잠정4도 `ACCEPT`가 아니며 학생 지도토큰/업데이트0이다. 사용자 승인 A로 결함8만 강화 프롬프트와 응답별 bounded validator(최대3회)에서 새 v5로 보존하는 [Stage1gW](../../test_plan/P106B_Bonsai-자동번역-pseudo-SFT-온라인-교사학생-검증.md)를 준비했다. 정적 검사에서 과거8/8 결함을 재검출해도 새 교사 답·독립 사실/권리·학생 능력은 `NOT_RUN`이다. 형식률을 지능 향상률로 바꾸지 않는다.

2026-09-28 사용자 [Stage1gW 결과101 §11](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)은 결함8행에 교사13요청·28,677 completion 토큰·474.232초를 써 명시 문구 lint7/8만 통과해 음성 exit8이었다. [실제 v5 답안 직접 감사](../../test_result/evidence/P106B_Stage1gW_candidate_review.json)는 lint 통과 답에도 인명 변형·혼합 한영 어휘·태양 거리 10~100배 축소·부자연한 역할 문장을 찾아 명백 결함5·추가검토2·잠정1로 분류했다. 이는 단순 문구검사와 교사 `CORRECTED` 자기신고를 교육 정답성으로 올릴 수 없다는 실물 근거다. 교사는 질문/답의 **내용만**, 코드가 원문·출처·언어·턴 순서와 canonical/ChatML, assistant-only 마스크를 소유해야 한다. 현재 옛 Stage1b가 일부 wrapping을 한 함수 안에 두었지만 v4/v5는 학생에게 전달한 적 없으며 학생 품질은 계속 `NOT_RUN`이다.

같은 날 [결과101 §12~§13](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)은 이를 새 단계로 분리했다. 공개 v3의 출처별 유한 교사 job 5,429개를 train/val 선분리·20MB 이하 SHA 샤드로 만들었지만, 실제 답안은 아직0이고 ko/en 학생 **토큰** 균형이나 요청 주제의 의미 폭은 미확인이다. 교사 4문항×세 사고강도 직접 실측은 `none/low/medium`의 형식 완결4/4·4/4·2/4, 요청 wall18.568/83.406/121.882초였다. 이전 `none`은 thinking sampler를 써서 모델카드의 instruct sampler를 적용할 새 팔과 직접 비교할 수 없고, `low`의 지원 여부는 현재 카드 문구와 로컬 실측이 일치하지 않는다. 별도 Stage2iWa/b/c 온라인 학생 **5 optimizer 업데이트**는 각 사용자 실행 SH만 정적 준비했으며 품질·한영5:5·300M/600M은 `NOT_RUN`이다. 교사 사고 원문은 sidecar에만 남기고 학생 target은 코드가 만든 ChatML의 답변 본문에 한정한다.

후속 [결과101 §14~§22](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)가 위 문단의 당시 `NOT_RUN` 일부를 갱신한다. OASST2 고정16문항은 태그15·JSON14 형식 완결, 태그 한국어13 train/2 val을 만들었다. 이 **13행을 반복한** Stage2g 학생 배선2업데이트는 동작만 확인했고 검증 손실과 일반화는 측정하지 않았다. 반면 공개 v3 원천은 OASST2가 아니라 **OASST1과 Aya Dataset**이며, Stage2f 한영32문항은 25문항 뒤 교사 HTTP500으로 종료9, Stage2iWa 동시 온라인5회는 교사33응답 뒤 HTTP500으로 학생 optimizer0·체크포인트0이다. Stage2j 교사-only 같은 실패 문항26에서 `peg-native` 출력/파서 불일치500을 재현했지만 원 Stage2i 실패의 원인은 아직 분리되지 않았다. 파서 우회는 HTTP200이어도 출력4096토큰 상한과 불완전 tagged 답이어서 학생 target으로 쓸 수 없다. 이후 소스별 고유 개념·답과 실제 비패딩 학생 처리토큰, 한영/주제 분포, 정답 오류를 별도 분모로 본다. **문자 1,200개는 서버 context 제한이 아니라 옛 보수적 필터**다. 새 Stage2kW는 `/apply-template`·`/tokenize`로 입력토큰을 세고 직접 입력 가능하면 원문 그대로 사용하며, 초과 시에만 부모 계보를 유지한 별도 압축 QA 후보로 보내 숫자·제약 누락을 검사한다. 이는 의미 보존의 충분한 증명이 아니며 새 teacher/학생 품질은 `NOT_RUN`이다.

2026-09-28 추가 [결과101 §23~§24](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)는 Stage2kW 사용자 읽기 전용 87,361 **job**과 Stage2fWb의 한영 형식 후보 KO14/16·EN15/16을 확정했다. 26번 한국어 문항은 작은 실제 입력817/839토큰에서 서버 PEG-native500이 두 번 재현돼 무효 후보로 남았다. 문턱 각12/16 통과는 **형식 기능**의 회복이지 32/32답·교사 정답·사전 사용권·한영 학습5:5가 아니다. 합쳐진 학생 후보 처리토큰의 한국어 비율은40.94%이고 학생 optimizer0이다. [새 Stage2kWb 계획](../../test_plan/P106B_Bonsai-자동번역-pseudo-SFT-온라인-교사학생-검증.md)은 공개 원천 job만 별도 ignored HF에 출력하고 보호 사전은 읽기/쓰기0으로 둔다. 별도 물리 저장은 라이선스와 계보 관리에 유익하지만, 사전의 보호되는 표현을 변형한 행이나 나중에 공개할 모델/출력의 법적 상태를 자동 해제하는 증거가 아니다. 공식 [사전 정책](https://krdict.korean.go.kr/kor/kboardPolicy/copyRightTermsInfo)과 [CC BY-SA 2.0 KR 법문](https://creativecommons.org/licenses/by-sa/2.0/kr/legalcode.ko)의 표시·동일조건·편집물 구분을 후속 권리 검토의 기준으로 둔다.

사용자가 고른 첫 보호 경로는 사전 파생 후보를 `CC_BY_SA_2_0_KR_CANDIDATE`로 **격리 저장하고 나중에** 원문·재합성 후보의 유사성/의미를 비교하는 것이다. [합성 격리 어댑터](../../scripts/p106b_rights_isolation.py)는 후보를 일반 canonical 상위 행이 아닌 제한 envelope로 기록해 기존 SFT loader가 단순 경로 입력으로 수락하지 못하게 했다. 이는 현재의 accidental mix 한 경로만 막는다. 다른 로더/수동 재포장과 모델 공개의 권리 판단까지 끝낸 것이 아니다. 후일 유사성 검사는 짧은 공용표현의 n-gram 오탐을 감안해 부모·사전 미사용 팔의 생성, 긴 드문 문자열, 사람 문맥검토를 함께 쓰고 검출0을 법적 보증으로 바꾸지 않는다.

2026-09-29 [결과101 §25~§28](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)은 사용자 새 smoke43/0/0/0 뒤 공개 전용 Aya Dataset/OASST2 source job10,528을 실제 생성했고, **다른 기존 OASST1** 원천에서 동시 교사+학생 low1·none5 optimizer를 완료했다. medium은 한국어 유한365개를 모두 써 4/5에서 음성 exit8이었다. 이 팔의 형식 후보611 중 실제 업데이트에 적용된 것은512이므로 canonical 기록만 보고 교육 완료로 부르면 안 된다. none5의 비패딩141,422토큰/약52분과 medium4의100,408토큰/약316분은 sampler·ctx·출력상한·완료량이 교락된 **처리율 설명**이며 지능 향상 비교가 아니다. 서버의 반복 KV-cache 경고와 함께 장시간 로그 버퍼에서 초기 GDN 메시지가 사라져 두 manifest의 `false`는 실제 비활성 증거가 아니다. 그 당시 계측은 별도 시작 신호로 고정하도록 보완했다. 체크포인트/held-out/검증형 `ACCEPT`/formal `TRAIN_READY`는 여전히 없다.

같은날 후속 [결과101 §29](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)의 **새 공개 medium We**는 시작 GDN latch true를 남겼지만 `nvidia-smi` timeout을 daemon sampler가 잡지 못해 모니터만 죽었다. 사용자 Ctrl+C 뒤 v15 raw141/후보123·optimizer0을 보존했고 로그를 삭제한 재실행은 HF version 충돌9였다. `sample_errors=[]`라는 자기보고가 스레드 생존이나 전체 VRAM peak 정상성을 보증하지 않는 실제 반례다. `TimeoutExpired`를 공유 실패신호로 전달·다음 backward/optimizer 전 tool fail9, Ctrl+C는130/status/phase·미완 ID로 저장하도록 수리한 CPU 회귀5개는 PASS다. 교사 raw 사고·최종과 학생 canonical을 따로20MB 이하 ignored HF에 보존하며 후보123을 학습완료로 세지 않는다. 사용자 결정은 medium 보류·새 공개원천 low Wg1→통과시Wh5이고, 이전 OASST1 low1 성공과 source가 달라 기술 검증을 별도로 둔다. 새 코드 GPU/모델 품질은 NOT_RUN이다.

2026-09-30 회수 [결과101 §30](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)는 새 공개 low Wg의 실제128답/optimizer1·비패딩25,133/지도18,735를 확인했다. 교사69.307분·학생2.796분(cold), completion61.43tok/s와 유효대화 공급6.04tok/s는 다른 분모다. length55건이 교사시간43.635%를 쓰고도 target에 들어가지 않아 단순 RAM 버퍼/학생 감속만으로 생산 병목을 풀 수 없다. 현재 train10,030 job의 소형 수락률 외삽은 고유약1.29M·4epoch5.14M이며300M을 달성한 것이 아니다. 사용자 A1 단일교사1/2slot·A2 생산/소비 겹침·B2→4답·독립C4 정확4pass와 통합1회 뒤 작은4epoch 실교육을 [Stage3 계획](../../test_plan/P106B_Bonsai-자동번역-pseudo-SFT-온라인-교사학생-검증.md)에 구현했다. 사고 target0·형식/마스크/계보와 실제답 사후검토를 분리하며 새9SH의 GPU/품질은 NOT_RUN이다. 큰300M 풀의 P087 복원추출4배 무과적합을100행 SFT 안전 보증으로 옮기지 않는다.

2026-09-30 사용자 [결과101 §31](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)은 그 후속의 증거수준을 바꿨다. A1의 동시 두슬롯은 첫쌍1.140×/역순1.015×·KO완결1~2/4로 속도+형식 문턱 음성이고, A2는 serial KO4/8에서 멈춰 overlap 자체가 미측정이다. B2/B4는 한영4/4 **형식**을 통과했으나 교사 내용의 참/거짓을 검증하지 않았다. C4는 보존100행×정확4pass·실제4 optimizer 후 같은 SFT-val3.700334→3.571472로 내렸지만 base full-val3.600580→3.619024 악화, 고정8질문 중 요구한 답+형식 동시 충족0이다. 운영0.1nat 중단선 PASS는 능력향상이 아니다. legacy32 채팅 마커8/7분절 대 chat32의 단일ID3/4와 EOS 전용 정지 경로를 원인 후보로 구분했지만 어느 하나의 인과효과는 아직 측정하지 않았다. 사용자 승인 A1Wb/A2Wb는 질문군·출력예산을 늘린 새 기술 진단으로 준비하고 통합/후속교육은 재검토 전 HOLD다. 과거 P087 대규모 복원추출4배 무과적합은 이 소형pseudo-SFT의 반복 안전 증명이 아니다.

후속 [결과101 §33](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)은 A1b 두슬롯 음성을 보존하면서 A2단일슬롯의 통합128행/optimizer1·실제대화24,187/지도17,110을 확인했다. 교사42시도에서 신규64행을 얻고 제한재요청으로6task 형식을 복구했지만, 고정16답의 부분검토에kana 혼입·부자연한한국어·원문맥부족을 확인했다. 형식retry와학생고정답retry는다른분모다. 기존C4는문항당부모/학생각1회였고새후속은first/최대3시도·raw를따로기록한다. checkpoint0이므로후속은원래부모에서시작한다. 사용자 승인 C자료교정→B선평가/chat324epoch·Alegacy대조는같은교정원문을두어휘로분리인코딩하며각자cache의loss전후와같은질문의실제답을평가한다. 부모14층dense/20층tied·어휘/pretrain도함께달라진다. 선택ChatML 단일/다중토큰정지는기본EOS경로를보존한opt-in으로구현했고새GPU·지능결과는NOT_RUN이다.

다음 [결과101 §34](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)은 B chat32부모의고정8질문×3시도24답 first/within3 모두0/8과한영4nativeprefix의반복을직접관측했다. nativefull-val3.590418과유한사전학습실행은instruction/SFT품질을보장하지않는다. exact pretrain train597.995M/val3.005M에서ChatML ID3/4는각각0회라어휘예약과역할표지학습을구분한다. C교정은명백한코드의미등록source_transform·writer/reader주소불일치9에서실패했고j/k/l/m은모델/교육0이었다. 따라서SFT4epoch나자료교정의과학적실패로이코드예외를해석하지않는다. 실제C→registered wrapper→양mask→consumer fixture와유료응답예외원형보존을추가했고, 사용자선택의관측된기준선 유지/작은C→전체C→B/A교육은새v30의NOT_RUN단계다.

2026-09-30 [결과101 §35](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)는 C 코드연결 수리 뒤 실제4후보의 canonical/양어휘 연계를 확인했지만, 고정4그룹8요청 중5건이출력4096 절단이었다. KO다중답은3회모두사고블록에서끝나 KO1/2·EN2/2가언어별75%를못넘었고 뒤5단은교육0/선결8이다. 27,315 completion/419.242초와922 후보대화/668지도토큰은학생실학습량이아니며절단5건이시간74.9169%를썼다. 형식수락한내용에도자리대리 같은표현과미검증의학답안이남았다. 사용자A로동일원천/low/sampler와문턱을유지한6144/8192 새v31·정확원인재시도/원형보존·조건부두교육을준비했으며16+12 CPU회귀는동적개선·P106 ACCEPT·formal TRAIN_READY의근거가아니다.

2026-09-30 [결과101 §36](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)는출력확장뒤KO다중답2회완결/양mask를확인했으나입력질문의오조어를보존하라는명령과질문까지거부하는내용화면의충돌을확인했다. canonical8/selected4와형식응답ko3/선택그룹ko1은다른단위다. 교사자료만실행됐고후속5단은선결8/교육0이므로SFT전체불가능의근거가아니다. 사용자A로질문의의도/조건은보존하고오조어문자열은수리·정확위치feedback·single/multi공통계약·배선pilot와전체언어별75%내용gate를분리했다. 같은사고8K/total16K/ctx32K 대응12에서low/medium/xhigh와유효자료속도/actual최종문구를남기고명시선택후두교육을연결한다. 구4문항low83.406/medium121.882는토큰량차이이며tok/s61.938/61.789·truth미검증이다. card의low미지원/불안정교정과로컬실측을함께보존하고xhigh의속도/정답성우위는새실험전NOT_RUN이다.

2026-10-01 [결과101 §37](../../test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md)는 같은4원천×3effort12요청·사용자xhigh선택·전체96교정99요청/128행·양계보각4update를 실제 관측했다. SFT CE 감소와 자기 native CE 약0.014 악화·좁은rubric전후0/8·실제 질문복창을 함께 기록한다. 일부 논리결론은 맞아0/8을 내용전부오답으로 확대하지 않는다. 동일 raw/4pass라도 서로다른 tokenizer/구조/부모라 chat32 단독효과나교차CE순위는아니다.

사용자 조건부승인으로 온라인에서는 모든잘못된문구리스트/의미검사를 폐지하고 언어문자는정상인용 가능성을표시하는 경고만 사용하며, 맥락/논리/오조어의 판별·격리·교정은 동결자료의 후행검증이 소유한다. 이 정책은 전수정답확인 전에는 pseudo교육조차 못한다는 뜻이 아니다. 무입력/원답보기·기존3시도 공유 예산을 구현했고 유일출력 분류·유사도·새지표는 별도제안/재승인 전 미구현이다. **옛 품질 필드의 호환 방식 선택 전 수락/학습허용 소비자는 재해석하지 않고 신규 온라인 GPU큐를 열지 않는다.** 현재 word gate 코드가 남아 있다는 사실을 정책 전환 구현완료로 보고하지 않는다.
