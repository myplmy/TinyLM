# 2026-10-22 제한예산 언어모델 조사 — 공식 평가, 구조적 사전학습, 실제 이식 비용

상태: 문헌 조사·조건부 아이디어. TinyLM 구현·학습·성능 재현은 `NOT_RUN`이다. 현재 실행의 계수·문턱·기본값을 변경하지 않는다.

조사 기준일은 2026-10-22 KST다. 첫 시각 확인은 2026-10-21 21:22:34 UTC였다. 총괄의 이번 연구 종료 시각인 2026-10-22 17:00 KST와 과거 제어기에 들어 있는 종료 시각을 혼동하지 않는다. 아래 웹 문서는 열람 시점의 페이지이며, 고정 commit 전체를 독립 재현한 결과가 아니다.

## 1. 결론과 오늘의 선택지

확인한 대회·프로젝트는 모두 같은 종류의 제한예산 실험이 아니다. BabyLM은 작은 데이터와 노출량, Parameter Golf는 저장 바이트와 다중 GPU 시간, Open SLM Leaderboard는 소형 모델의 비교 표면에 중심이 있다. ChineseBabyLM의 단어 계산·학습 반복 규칙도 영어 BabyLM과 다르다. 소형이라는 이름이나 높은 공개 점수만으로 현재 한영 chat32·삼진 dense14에 효과를 이전할 수 없다.

오늘 검토 가능한 세 후보는 다음과 같다. 세 개 모두 오늘 성능 개선을 보장하거나 구현을 승인한 처방은 아니다.

| 후보 | 얻으려는 정보·효과 가설 | 오늘 가능한 작은 경계 | 영향·비용과 가장 강한 반례 |
|---|---|---|---|
| A. BabyLM 최소쌍 계열의 독립 진단 | 문법·조건/대상 연결·실제 자유답의 병목을 분리한다. | 자산·사용조건 확인과 route-safe likelihood adapter의 계약 준비. 새 학습은 필요 없다. | 코드 영향은 평가 어댑터에 국한할 수 있다. 전체 공식 평가 시간은 미측정이며 자산이 없으면 별도 다운로드 허가가 필요하다. 선택지 우도 성공은 대화 성공이 아니다. |
| B. 어휘 타일형 exact CE의 비용 검토 | 목적함수·추론을 바꾸지 않고 출력 head의 중간 버퍼와 재계산을 줄일 가능성. | 기존 chunk/checkpoint 경로와 새 경로의 값·VJP·실제 head 비용을 먼저 비교하는 설계. | 소규모 손실 소비기 변경이지만 현재 head가 이미 제한되어 있어 순이득이 작거나 음수일 수 있다. 설치·커널 준비·GPU 비용을 확인하지 않았으므로 바로 본학습을 열 근거는 없다. |
| C. 새 scratch의 구조적 Stack 사전 워밍업 | 사전학습 초기에 상태 갱신의 귀납편향을 심어 이후 조건 연결을 쉽게 만들 가능성. | 생성 규칙·토큰 계약·비교 예산을 먼저 고정한 소형 새 초기화 대조의 설계. | inference head·추론 연산 추가는 필요 없지만 새 학습 계보가 필요하다. 기존 CP 뒤에 붙이는 것은 핵심 근거와 다르다. 짧은 대조에서 전이가 없거나 자연어 대조보다 못할 수 있다. |

권장 순서는 A로 평가 가능성을 먼저 닫고, B는 실제 병목이 확인될 때만, C는 새 초기화와 이후 자연어·과제 학습까지 수용할 예산이 있을 때만이다. 이것은 총괄이 이미 진행 중인 실제 종점 회수를 대체하라는 뜻이 아니다. 효과 크기나 시간 문턱은 새로 정하지 않았다.

초기 메시지의 B는 심층 확인으로 범위를 교정했다. Parameter Golf의 fused softcapped CE와 출력 linear까지 타일로 계산하는 CCE는 다른 구현이다. 전자를 현재 head에 그대로 붙이면 큰 절감이 난다고 결론내리지 않는다. C 역시 프로젝트 첫 화면은 준비 중이지만 논문 부록에 저자 generator 저장소가 실제 연결되어 있음을 확인했다. generator의 존재와 9월 논문의 모든 실행 설정 공개·재현은 구분한다.

## 2. 범위·권한·기존 TinyLM 증거

### 2.1 이번 영향도와 실행 경계

| 경로·대상 | 이번 동작 | 제외 |
|---|---|---|
| 이 연구 문서 | `apply_patch`로 신규 작성 | 다른 계획·원장·코드·기준표 갱신 없음 |
| 기존 방법론·P106B 계획/결과·관련 모델/손실 코드 | 필요한 부분 읽기 | 실행·import·모델/CP tensor·원문 캐시 읽기 없음 |
| 공식 논문·저자 저장소·공식 웹/HF 문서 | 웹 열람 | clone·패키지 설치·가중치/데이터 다운로드·계정/약관 동의 없음 |

코드·데이터·테스트의 실제 변경은 없다. 문서 한 개 외 쓰기와 Git 작업은 하지 않는다. 연구 후보의 향후 구현에는 별도 F4, 정식 계획·태그·비교 조건·실물 비용 검증이 필요하다. 이번에는 검사기·fixture·GPU를 실행하지 않았으며, 스킬의 설계 점검을 실제 preflight PASS로 표시하지 않는다. 보호 `datasets/TinyDataset/**`와 다른 환경 지침은 접근하지 않았다.

### 2.2 중복·음성을 먼저 구분했다

열람한 [METHODS의 최근 P106B 기록](/home/uranus/tinyLM/docs/METHODS.md:443)과 [리뷰08](/home/uranus/tinyLM/docs/methods/08_paper_review2.md:1113)을 기준으로 한다. 실행 중인 모델의 새 결과를 추측으로 채우지 않는다.

| 기존 확인 | 이번 조사에 주는 제약 |
|---|---|
| 내용 평균 P의 TEST 637→628/1024, Boolean의 제한적 이득과 산수/형식 손상 | 새로 이름 붙인 짧은 답 CE 재가중을 독립 새 아이디어로 팔지 않는다. [리뷰08 §25](/home/uranus/tinyLM/docs/methods/08_paper_review2.md:1162). |
| 실제 학습 표면에서도 산수·대상 선택 fitting이 약했다. 제한된 첫 토큰 TF/free 경로는 일치했다. | 모든 오답을 새 표현 전이 또는 종료 문제만으로 설명하지 않는다. [리뷰08 §24](/home/uranus/tinyLM/docs/methods/08_paper_review2.md:1156). |
| Q/K head-wise Muon은 동일384회에서 TEST 613→612/1024·자연 EM 10→10/128 | Muon·head 분리라는 이름만 같은 재실험을 최신 문헌의 새 성과로 취급하지 않는다. [METHODS](/home/uranus/tinyLM/docs/METHODS.md:472). |
| 299M/595M 계열은 각각의 풀·스케줄·학습/추론 route를 구분해야 한다. 원문 CE 우위와 실제 지시응답은 달랐다. | 한 seed의 작은 native32 CE, 더 긴 원문학습, 교차 route 전환을 질문 이해의 인과 증거로 사용하지 않는다. [METHODS](/home/uranus/tinyLM/docs/METHODS.md:464). |
| Engram, thinking, 재귀, 입출력 E 확장은 이미 검토된 후보다. | 단순 재소개를 net-new로 세지 않는다. [리뷰08 §27](/home/uranus/tinyLM/docs/methods/08_paper_review2.md:1187), [§28](/home/uranus/tinyLM/docs/methods/08_paper_review2.md:1232), [§31](/home/uranus/tinyLM/docs/methods/08_paper_review2.md:1380). |

기존 Broad의 실제 16원천 표본과 1.191B 풀의 계보는 각각 제한된 관측이다. 새 공개 코퍼스가 좋아 보인다는 이유로 기존 데이터의 의미 문제를 해결했다고 하지 않으며, 601M과 legacy 풀을 독립 고유 데이터로 합산하지 않는다. 새 조사를 위해 corpus/bin/CP를 다시 읽지 않았다.

## 3. 요청한 네 이름의 실재·날짜·예산

### 3.1 BabyLM Challenge

2026 공식 사이트와 현재 평가 저장소를 확인했다. Strict/Strict-Small은 원천 100M/10M 단어, 다국어는 영어·네덜란드어·중국어 중심이다. CFP §4.2는 반복을 포함한 노출을 Strict-Small 100M, 나머지 1B 단어까지로 제한하고 중간 CP를 요구한다. 단어와 chat32 토큰, 원천 규모와 누적 draw는 별개다. 한국어를 주축으로 이미 학습한 현재 CP의 경쟁 참가 적격성은 성립하지 않았다. 평가 도구의 비경쟁 재사용과 참가 자격을 분리한다. [공식 사이트](https://babylm.github.io/), [2026 CFP §4.1–4.2·FAQ](https://arxiv.org/html/2602.20092v2).

CFP v2 표시일은 2026-02-24다. 현재 웹 지침의 간략 예산 설명만 읽고 반복노출 상한을 빠뜨리면 안 된다. 외부 교사·생성 데이터의 별도 규칙도 있어 현 Teacher/SFT 계보를 자동 허용으로 볼 수 없다. 새로운 대회 구조 자체를 2026-05 이후 새 기법으로 세지는 않는다. [2026 지침](https://babylm.github.io/guidelines.html).

### 3.2 OpenAI Parameter Golf

실재하는 OpenAI 주최 대회다. 공식 저장소의 일정은 2026-03-18~04-30이고 공식 회고는 2026-05-12다. 기록 조건은 코드와 압축 가중치를 합한 16,000,000B, 8×H100 SXM의 학습600초와 별도 평가600초다. 고정 FineWeb의 byte당 손실을 쓰며 tokenizer를 바꾼 결과도 byte 계산을 엄격히 확인한다. 따라서 작은 파라미터 수·저장량·동일 학습토큰·CPU 상주·QA 능력은 같은 척도가 아니다. 기본 예제와 기록 제출물도 다르다. [공식 저장소 규칙](https://github.com/openai/parameter-golf), [OpenAI 공식 회고](https://openai.com/index/what-parameter-golf-taught-us/).

공식 기록의 score-first TTT는 이미 채점한 문서 조각으로만 갱신하는 별도 평가 규칙이다. 이를 우리 고정 미적응 CP 비교에 섞으면 다른 실험이다. GPTQ·TTT·어휘/바이트 변환·구조를 합친 BPB 개선을 삼진 구조의 단일 효과로 읽지 않는다. 참가자 설명과 OpenAI의 독립 검증 선언도 같은 증거 수준은 아니다. 공식 repo 안의 데이터 계보 이의 제기만으로 모든 기록을 무효라고 단정하거나, 반대로 clean manifest 재확인 없이 특정 제출물의 수치를 검증 완료라고 하지 않는다.

repo의 [LICENSE는 MIT](https://github.com/openai/parameter-golf/blob/main/LICENSE)지만 데이터·의존 코드·개별 제출물의 고지는 따로 확인해야 한다. 회고가 5월이라는 사실은 3~4월 구현을 모두 5월 이후 신기법으로 바꾸지 않는다.

### 3.3 OpenSLM: 두 이름을 분리한다

원저자 Haidass 모델카드가 연결하는 비교판은 [AxiomicLabs Open SLM Leaderboard](https://huggingface.co/spaces/AxiomicLabs/Open_SLM_Leaderboard)다. 운영자 README는 <150M/<100M/<50M/<10M/<3M 범주와 현재 점수 기반 이력 표시를 설명한다. 이번 도구에서는 live iframe과 index 본문을 읽지 못해 현재 순위·점수·정확한 scorer 설정은 재검증하지 않았다. 최초 공개 날짜도 확정하지 않는다. [운영자 README](https://huggingface.co/spaces/AxiomicLabs/Open_SLM_Leaderboard/raw/main/README.md).

별도의 [OpenSLM.ai Accord](https://openslm.ai/accord/)는 2026-04-25 v0.2 규범 초안이다. 작은 모델의 개방성 원칙 문서이며 그 leaderboard나 데이터 제한 대회가 아니다. 둘을 합친 단일 연구 프로젝트로 보고하지 않는다.

보드에 연결된 [Haidass1.5-143M 저자 카드](https://huggingface.co/DALabCommunity/Haidass1.5-143M)는 2026-08-28 공개, 약400B 학습토큰·64k 어휘·SwiGLU·중영 모델을 선언하며 instruction tuning은 없다고 적는다. 이는 저자 메타데이터이지 이번 독립 재현이나 현재 순위 확인이 아니다. 작은 파라미터 수가 우리의 작은 학습예산을 뜻하지 않는 구체적 반례다.

보드의 [라이선스](https://huggingface.co/spaces/AxiomicLabs/Open_SLM_Leaderboard/raw/main/LICENSE.md)는 제한적이다. 소스/디자인/경쟁 보드용 지표 복제 등을 무조건 허용하지 않는다. 이번에는 연구용 짧은 요약과 링크만 남기며 보드 코드·점수표를 복제하지 않는다. 공개 조회 가능성과 오픈소스 재사용 허가는 다르다.

### 3.4 ChineseBabyLM

실제 NLPCC 2026 shared task다. 공식 페이지는 4월15일 pipeline/data 공개, 6월30일 결과 발표를 적는다. 정리 논문은 v1 2026-07-12, v2 08-17이다. 상세 지침의 예산은 Jieba 0.42.1 기본 모드의102M 단어이며 학습 epoch 제한은 없다. landing page의100M 표기는 상세102M 규칙을 대체하지 않는다. 원천/토큰 계산·반복예산이 영어 BabyLM과 다르다. [공식 사이트](https://chinese-babylm.github.io/index.html), [지침](https://chinese-babylm.github.io/guidelines.html), [정리 논문](https://arxiv.org/abs/2607.10745).

정리 논문은 18팀·28모델과 우승 DeBERTa-v2의 발음 보조목적을 보고한다. 이는 decoder-only·한영·삼진·현재 instruction fitting의 성과가 아니다. 한글 자모/발음 보조교육으로 확장하는 것은 별도 추측이며 오늘 우선 후보로 채택하지 않는다. 공식 pipeline에는 zero-shot, CLUE 미세조정, fMRI 회귀가 섞여 있다. 전체 CogBench는19.3GB라는 별도 자산 비용도 있다. [공식 pipeline의 Token Count·평가 설명](https://github.com/chinese-babylm/chinese-babylm-pipeline-final).

## 4. 2026-05 이후 연구: 원문에서 확인한 범위

### 4.1 Lasting Effects of Abstract Pretraining Beyond Perplexity — 2026-09-30

원문 §3·§6·부록A/B를 읽었다. SmolLM-135/360M에서 Stack→자연어→과제 SFT의 순서를 비교한다. 최종 상태를 예측하는 구조적 워밍업이 핵심이며 native vocabulary를 그대로 써 embedding/head를 이전한다. 자연어 학습량은 약20 tokens/parameter이고 워밍업은 그보다 작은 추가 예산이다. 따라서 논문의 결과 자체를 완전 동일 총토큰 대조로 부르면 안 된다. [원문 §3·§6·A.2](https://arxiv.org/html/2609.38764v1).

우리에게 중요한 제약은 초기 전용 국면이 유리했고 뒤에 붙이거나 섞는 조건은 그 효과를 재현하지 못했다는 점이다. 단순 대상조회나 병렬 사실 비교 전반에 효능을 보장하지도 않는다. 후보 C의 대조는 같은 총 계산과 추가 자연어 워밍업 대조를 구분해야 한다. 보고된 비율·LR·단계 길이는 채택하지 않는다.

저자 [프로젝트 화면](https://zlshinnick.github.io/beyond-perplexity/)은 준비 중이지만, 부록A.1은 실제 [procedural-pretraining 저장소](https://github.com/zlshinnick/procedural-pretraining)를 가리킨다. 기존 procedural 연구의 공식 구현이며, 이번9월 연구의 전체 run/config 공개까지 확인한 것은 아니다. root 화면에서 코드 라이선스도 확정하지 못했으므로 복사 허가를 가정하지 않는다. Stack 출력 방향·입출력 마스크·특수ID 계약은 구현 전에 code와 맞춰 고정해야 한다.

### 4.2 HRM-Text — 2026-05-20

§2.1–2.2·§3.1–3.2·§4.1–4.3을 확인했다. 계층 재귀와 안정화, instruction-response 중심 목적함수, PrefixLM을 묶는다.40B는 고유 토큰이고 실제 노출은60B다.1B reference는16 H100×46시간, 즉736 H100-GPU시간이며 약1,472달러는 특정 단가 가정이다. 단일 소비자 GPU의40시간 비용이 아니다. 65,536 어휘·4096문맥도 다르다. [원문](https://arxiv.org/html/2605.20613v1), [저자 코드](https://github.com/sapientinc/HRM-Text).

소스 §4.2는 n-gram 오염 검사를 수행하지만1B DROP의13-gram에서는 유의한 차이도 보고한다. 전체 공개평가 비오염을 증명한 것으로 쓰지 않는다. 핵심 교훈은 데이터/목표/구조를 따로 통제해야 한다는 것이다. 현재 SFT는 이미 assistant-only이므로 그것만 복사하면 새 개입이 아니다. PrefixLM의 비인과 user-prefix와 계층 재귀는 현재 causal CLA/KV·마스크와 달라 독립 구현 검산이 필요하다.

저자 repo는 Apache-2.0이며 SwiGLU, 두 번의 PrefixLM attention pass, FA3/Hopper 중심 준비를 명시한다. 현재 삼진 커널·CLA·재방문과 동등한 drop-in 구현은 아니다. 단순 MTP head 추가나 inference 재방문을 이 논문의 학습으로 부르지 않는다.

### 4.3 ELAS — arXiv 등록 2026-05-05

§3.1–3.4의 핵심은 저랭크 LORO, SwiGLU를 제거한 두 투영 ReLU², activation top-2-of-4, activation identity STE다. 식(2)–(4)는 이 묶음을 명시한다. §4/Table1의 모델은60M~1B, 학습1.1B~13.1B C4 토큰이며3090/A100 실측이다. §4.3의 작은60M은 dense warmup0에서 NaN도 보고했다. 삼진 weight STE 위에 희소 activation STE를 얹으면 원논문과 다른 두 근사를 결합하는 것이다. [원문 §3–4](https://arxiv.org/html/2605.03667v1).

이번에 직접 연 저자 [ELAS repo](https://github.com/JiaxiLi1/ELAS-Efficient-Pre-Training-of-Low-Rank-Large-Language-Models-via-2-4-Activation-Sparsity)는1 commit·LICENSE만 있었다. MIT 표시는 실행 커널의 공개를 증명하지 않는다.1000-step warmup 같은 수치를 현재 짧은 학습에 복사하지 않는다. 원문의 activation 절감과 low-rank parameter 절감은 서로 다른 항이다. tensor에0을 썼다는 사실만으로 우리 GPU의 sparse GEMM 가속이 생기지도 않는다.

아카이브 등록일과 최초 연구 공개일/심사 이력은 구별했다. 해당 연구의 모든 최초 공개 날짜를 재구성하지는 않았다. 오늘의 단일 안전 변경으로는 보지 않는다.

### 4.4 Hardware-Aware FP4 FlashAttention-4 — 2026-09-03

원문 §2–4·§7.5–7.7을 읽었다. GB200/B300 대상의 forward·backward 경로 연구다.8B 단일 update의 최대 약1.14배와 긴 학습의 안정성은 별도 증거다. MXFP4 P/V는 조사한 장기 경로에서 발산했고 유지한 경로는 FP8 P/V였다. 한 궤적의 안정성을 BF16 동등품질로 부르지도 않는다. [원문 §7](https://arxiv.org/pdf/2609.04105).

우리가 가져올 것은 전체 update·긴 학습·실제 정확도의 계측 경계를 나누는 습관이다. Blackwell 전용 자원과 투영 양자화를 포함한 결과를 현재 소비자 GPU·93M·seq1024·삼진 weight 경로의 속도 근거로 쓰지 않는다. 저자 보고를 독립 재현하지 않았고 해당 커널은 설치하지 않았다. 원래 FA4 본 논문은2026-03-05이므로5월 이후 신논문으로 잘못 세지 않는다. [원 FA4](https://arxiv.org/abs/2603.05451).

### 4.5 원문 확보가 덜 된 최근 색인

- [Structural priors for data-efficient language learning, arXiv:2609.11505](https://arxiv.org/abs/2609.11505): 공식 검색 메타데이터는2026-09-10을 표시한다. 본문/PDF 열람이 실패했으므로 정확한 설정·음성의 범위를 이번 방법 비교의 검증된 근거로 사용하지 않는다.
- [Entropy Regularization: A Free Correction to Cross-Entropy for Verified Demonstrations, arXiv:2609.30572](https://arxiv.org/abs/2609.30572): 공식 검색 메타데이터는2026-09-24를 표시한다. 원문 열람 실패로 제3자 미러에서 보인 수식·성과를 채택 근거로 올리지 않았다. 제목의 free를 무계수·무비용·정답 보장으로 읽지 않는다.

두 항목은 검증 완료 성과가 아니라 후속 열람 색인이다. 이번 보고서는 원문을 열지 못한 논문의 수치를 보완해서 만들어 넣지 않는다.

## 5. 오래된 기법: 추가 효용이 있는 부분만

### 5.1 Primer / MDHA는2021 연구다

원문 §2–3·Figure4·§4를 확인했다. Primer-EZ는 ReLU²와 각 Q/K/V 투영 뒤의 causal width3 depthwise convolution이다. MDHA는 별도2026 연구명이 아니라 그 구성요소다. 원문은 SwiGLU를 포함한 Transformer++도 비교한다. 따라서 ‘SwiGLU 대조가 아예 없다’는 설명도 틀리지만, 현 학습된 SwiGLU 가중치의 함수보존 교체 근거가 있는 것은 아니다. [원문](https://arxiv.org/pdf/2109.08668).

원문은 step 자체가 느려져도 필요한 학습량이 줄면 효율적일 수 있다고 명시한다. headline의 학습비 절감을 현 ms/update 가속으로 바꾸지 않는다. 추가 조사 가치가 있다면 SwiGLU는 고정하고 국소 causal projection 혼합만 떼는 가설이다. Q-only로 줄이면 로컬 변형이지 Primer-EZ 재현이 아니다. CLA의 K/V 소유층·RoPE 순서·증분 convolution 이력·문서/role 경계·KV 재사용 검산 때문에 오늘 무검증 기본값으로 추가하지 않는다.

### 5.2 N-Grammer와 Engram을 합치지 않는다

N-Grammer는2022-07-13 연구다. §3의 embedding product-quantization code와 latent bigram hash/table이 핵심이다. 원문 token-ID bigram과도 같지 않고, Engram의 주소 정규화·hidden gate와도 다르다. [원문 §3](https://arxiv.org/pdf/2207.06366).

현재 Engram 검토와 비교해 새로 확인할 가치가 있는 질문은 ‘고정 실제 byte에서 latent code를 학습하는 비용이 token hash보다 유리한가’ 정도다. table/codebook/projection·optimizer·decode 상태의 실제 바이트를 모두 세야 한다. 같은 지문의 질문 대상 교체를 국소 연상만으로 해결한다는 근거는 없다. Engram-lite·memory head를 새 이름으로 재제안하지 않는다. [기존 검토](/home/uranus/tinyLM/docs/methods/08_paper_review2.md:1187).

### 5.3 fused softcapped CE와 Cut Cross-Entropy는 다르다

Parameter Golf [#1787 참가자 설명](https://github.com/openai/parameter-golf/pull/1787)의 fused CE는 softcap/tanh·log-sum-exp·row loss를 묶는 training kernel이다. 여러 optimizer/gate/TTT 변경과 함께 제출되었으므로 그 BPB를 CE kernel의 단독 효능으로 쓰지 않는다. 현재 TinyLM head에는 그 softcap이 없다. 이를 새로 추가하면 ‘동일 손실 가속’이 아니라 목적함수 경로 변경이 된다.

별도의 [Apple CCE 원논문](https://arxiv.org/abs/2411.09009)은2024-11-13/ICLR2025로 오래된 연구다. 어휘 방향 타일을 순회해 전체 logit 행렬을 HBM에 쓰지 않는 방식이다. 현재 저자 [repo](https://github.com/apple-aiml-research/ml-cross-entropy)는 gradient filtering을 제거하는 `cce_exact`를 명시하고 Ampere 이상·PyTorch/Triton 요구사항을 적는다. 기본 근사 경로와 exact 비교를 섞지 않는다.

로컬 [mtp_sft.components](/home/uranus/tinyLM/tinylm/train/mtp_sft.py:117)는 이미 지도 위치만 고르고 positional chunk2048과 head checkpoint를 쓴다. [_head_logits](/home/uranus/tinyLM/tinylm/model/transformer.py:450)는768→E→vocab의 factorized head다. 한 논리적2048×32768 FP32 logit 텐서는256MiB라는 계산이지만 이는 allocator 전체나 실제 절감량이 아니다. 큰 Gemma 예제의 수십GB 절감을 현재에 인용하지 않는다.

후보 B를 연다면 E로의 투영·공유 embedding 양쪽 gradient·이미 shift된 y·IGNORE/owner·전체 update 분모를 그대로 보존해야 한다. MTP를 나중에 포함하더라도 horizon별 target/segment 계약을 먼저 닫는다. 값의 수학적 동등성은 bf16 reduction의 bit 동일성을 뜻하지 않는다. 새 패키지 보유 여부·실제 kernel 비용은 미확인이다. [Apple LICENSE](https://github.com/apple-aiml-research/ml-cross-entropy/blob/main/LICENSE)는 별도 약관과 하위 고지를 갖고 있어 MIT/Apache라고 임의 표기하지 않는다.

## 6. BabyLM 공식 평가를 로컬에 적용하려면

### 6.1 가능한 것과 아직 성립하지 않은 것

[2026 공식 평가 repo](https://github.com/babylm-org/babylm-eval)는 Strict와 Multilingual을 분리하고 zero-shot 및 fine-tuning 결과, 완전 참가의 checkpoint 평가를 구분한다. 미평가 항목을0으로 취급하는 제출 규칙도 있다. 일부 진단을 돌린 결과를 full BabyLM 점수로 쓰면 안 된다. 공개 HF 업로드·leaderboard 제출은 별도 외부 쓰기이며 이번 권한에 없다.

현재 repo의 root README와 [requirements](https://github.com/babylm-org/babylm-eval/blob/main/requirements.txt)는 열었지만 `strict/README.md`·하위 폴더의 웹 열람은 실패했다. 따라서 현재2026 scorer의 모든 옵션·데이터 다운로드 스크립트를 완독/실행했다고 하지 않는다. 구버전 [2025 공식 pipeline](https://github.com/babylm/evaluation-pipeline-2025)은 별도 고정판 대안이지만2026 결과와 합산하지 않는다.

현재 TinyLM CP가 그 자체로 Transformers의 `AutoModelForCausalLM` 구현이라는 증거는 없다. 전용 HF 호환 wrapper 또는 harness의 custom LM backend와 엄격 loader가 필요하다. task 이름만 복사한 로컬 scorer는 공식 소비와의 동등성을 검산하기 전에는 공식 harness 실행으로 부르지 않는다.

### 6.2 자산·라이선스·다운로드 구분

| 자산 | 확인한 권리·접근 조건 | 로컬 적용에서 남은 것 |
|---|---|---|
| 2026 평가 코드·task 정의 | root requirements는 lm-eval/transformers/statsmodels 등을 선언한다. 이번에는 하위 라이선스 전체를 확정하지 못했다. | 정확 commit·의존 버전·각 task 정의·라이선스를 확인해야 한다. 설치/clone은 하지 않았다. |
| 2025 공식 pipeline | repo는 Apache-2.0을 표시한다. |2026 대신 쓰면 판본을 명시한다. 현재 보유 여부는 미확인이다. |
| BLiMP |[원저자 HF 카드](https://huggingface.co/datasets/nyu-mll/blimp)는 CC-BY-4.0,67개 subset×각1000쌍을 표시한다. | 기본 원본만 계산해도134,000개 문장 score다. 작게 뽑으면 공식 전체 점수가 아니다. 다운로드·출처/버전 동결이 별도다. |
| EWoK |[공식 카드](https://huggingface.co/datasets/ewok-core/ewok-core-1.0)는 CC-BY-4.0 외 TOU 동의와 공개 평문/파생물 배포 제한을 명시한다. | 사용자 계정의 수락 여부를 확인하지 않았다. 비공개 저장·허용된 공개 요약/해시 경계가 필요하다. 평가자료를 훈련에 넣지 않는다. |
| COMPS·Entity Tracking·BLiMP Supplement·GlobalPIQA·human-likeness 자료 |2026 root에서 task 존재를 확인한 수준이다. | 버전·정확 사용조건·필터·숨긴 target 가용성과 scorer별 요구를 개별 확인해야 한다. 일괄 허용으로 처리하지 않는다. |
| BabyLM 훈련 코퍼스 |[2026 Strict-Small 카드](https://huggingface.co/datasets/BabyLM-community/BabyLM-2026-Strict-Small)는 MIT를 표시한다. | 평가만 할 때 훈련 코퍼스 전체 다운로드는 필요하지 않다. 카드 표기가 모든 원천의 권리를 전수 확인한 법률검토는 아니다. |

이 표는 열람한 표시·조건의 기록이지 법률 자문이 아니다. HF 웹 카드에 자동 노출된 일부 미리보기는 자료 품질 판정이나 학습 예제 선정에 사용하지 않았고 보고서에 복제하지 않았다. 로컬 HF/캐시를 넓게 검색하지 않았으므로 ‘이미 있으니 다운로드0으로 가능’이나 ‘확실히 없다’ 어느 쪽도 단정하지 않는다. 먼저 정확 manifest와 허용된 메타데이터를 확인해야 한다.

### 6.3 TinyLM 전용 adapter의 필수 계약 — 아직 구현하지 않는다

1. 해당 native/SFT/Broad 종점의 엄격 loader를 사용하고 `quantization_route`를 끝까지 유지한다. float CP를 일반 생성 loader로 불러 삼진화하지 않는다. [weight_route](/home/uranus/tinyLM/scripts/p106b_weight_route.py:231), [load_routed_state](/home/uranus/tinyLM/scripts/p106b_weight_route.py:301).595M 등 새 부모는 그 단계의 loader를 써야 하며 과거 namespace loader로 우회하지 않는다.
2. 공식 평가는 기본적으로 문자열 우도다. 임의 ChatML 지시문·정답 후보·assistant prefix를 덧붙여 원 scorer를 바꾸지 않는다. 대화형 진단은 별도 프로토콜로 표기한다. 공식 과제마다 sum/mean, 조건부 범위, BOS/EOS, tokenizer 공백 규칙을 원 task 코드와 맞춰야 한다. 이번 하위 scorer 열람 실패를 추측으로 메우지 않는다.
3. 현재 chat32 어휘/특수ID를 그대로 사용한다. 논문의 작은 영어 어휘를 CP에 덮어씌우거나 문자열 길이로 token log-probability 분모를 대체하지 않는다. 문장 우도·continuation 우도·두 후보 정규화 점수를 구분한다.
4. 문맥1024 초과·truncation·padding·정답 위치를 사전에 기록한다. 본문 뒤를 무심히 잘라 정답이나 부정을 없애는 자동 수리를 하지 않는다. 같은 문장 점수·대상 교환·full/prefix·cache 및 route 정합은 별도 작은 회귀의 대상이다.
5. MTP-off·eval/no_grad·선택한 수학 precision을 고정한다. route helper 때문에 모든 parameter의 `requires_grad`를 일괄 바꾸는 방법은 사용하지 않는다. CP/core/tokenizer/code·원문 ID·원점수·pair/가족 분모를 남긴다.
6. zero-shot과 GLUE 미세조정·인간 반응 회귀는 다른 작업이다. 후자는 추가 학습·자산·자원과 평가 전용 CP를 필요로 한다. 현재 assistant CP를 덮어쓰지 않는다.

공식 최소쌍을 잘 구분해도 자유 생성에서 묻는 대상의 정확한 값이 나온다는 뜻은 아니다. 반대로 greedy chat이 약하다고 모든 문법 likelihood가 우연 수준이라고 가정하지 않는다. 이 분리가 A의 실제 목적이다.

### 6.4 오염·판정 한계

기존 Wikipedia/FineWeb 계열과 공개 평가의 exact/near·URL·문항 변형 중복을 이번에 검사하지 않았다. 현 cache의 특정 VAL 제외를 새로운 BabyLM 평가의 비오염으로 확장하지 않는다. 이미 반복 확인한 TEST는 탐색 증거이며 새 hidden/unseen 증거가 아니다. 새 평가 문항의 정답이나 official dev/test 텍스트를 후속 SFT 원천으로 돌리지 않는다.

최소쌍은 템플릿·어휘·가족을 공유하므로 문장 수를 독립 의미문항 수로 세지 않는다. 과제별 점수와 가족 분모를 보존하고 한 지표로 일반 지능·한영 동등성·Falcon 대등성을 선언하지 않는다. 한국어에 대한 직접 근거가 없는 영어/중국어 task를 한국어 성과로 합산하지 않는다.

## 7. 구조·손실·자원의 이식 위험 요약

| 방법 | SwiGLU/삼진 | CLA·증분 KV | MTP·추론 비용 | 이번 상태 |
|---|---|---|---|---|
| BabyLM likelihood adapter | 본체/손실 변경 없음. route 정확성은 필수 | 같은 forward/cache 계약을 검산 | MTP-off. 새 학습0, 평가 시간은 미측정 | 자산·scorer·adapter 선결 |
| exact 어휘 타일 CE | factorized FP head의 손실 소비 변경. weight route는 불변이어야 함 | 본체를 바꾸지 않지만 gradient가 같아야 함 | horizon별 target 보존. inference 경로는 변경하지 않음 | 설치·VJP·cost 모두 미실행 |
| Stack 초기 국면 | 같은 native 어휘와 깨끗한 output-only 지도. 삼진 학습 전이는 미검증 | 새 문서/작업 경계를 명시 | 새 head·추론 연산 추가가 목적은 아님 | 새 scratch 조건부 가설 |
| HRM-Text/PrefixLM | assistant-only 부분은 이미 있음. 재귀/안정화는 새 구조 | prefix의 비인과 attention과 packed 문서 경계가 현재 causal 경로와 다름 | 재귀와 MTP는 다른 축. 실행비 추가 가능 | 오늘 drop-in 아님 |
| MDHA 분리 대조 | SwiGLU 고정 가능하지만 Primer-EZ 원형과 달라짐 | 소유층 K/V convolution·증분 상태가 새 계약 | 새 cache 상태·step 비용이 생김 | 후순위 구조 후보 |
| ELAS | 저랭크·ReLU²·activation STE를 결합. 삼진에 무료 결합 아님 | attention 저랭크까지 바꾸면 별도 검산 | sparse 저장/커널 없이는 step 가속 미성립 | 실행 코드 공개 불충분 |
| Engram/N-Grammer | FP table·codebook의 실제 메모리 증가 | prefix/문서/role 및 token 이력 소유 필요 | lookup 상태·메모리는 남음 | 기존 문헌 후보와 중복 |
| FP4 attention | weight 삼진과 attention 저정밀은 다른 축 | 새로운 kernel/precision/cache 계약 | 실제 전체 update와 장기 품질을 따로 확인 | 현 하드웨어 효과 근거 없음 |

## 8. 실제 연구를 선택할 때의 반증 조건

A는 동일 raw 텍스트에서 공식 likelihood 경로가 같고도 문법·관계 task와 실제 답변이 갈리는지 본다. 그 결과는 학습 성과가 아니라 병목 분리다. 일부 task/표본만 했으면 부분 진단으로 남긴다.

B는 같은 값/gradient 계약부터 시작한다. current positional chunk에 비해 head 시간이 작거나 전체 update가 개선되지 않으면 큰 학습은 불필요하다. gradient filtering·softcap·label shift·LR을 같이 바꾸면 동일 CE 가속 실험이 아니므로 한 묶음의 개선으로 채택하지 않는다. 별도 설치 허가가 없거나 kernel을 오늘 안정적으로 준비할 수 없다면 기존 경로를 유지한다.

C는 같은 초기화·전체 소비량/출력 target·이후 자연어 draw·SFT·평가를 맞춰야 한다. 워밍업만 추가한 baseline, 같은 예산의 자연어 워밍업, 구조를 깨뜨린 통제를 구분하지 않으면 알고리즘 구조의 효과를 알 수 없다. 기존 native CP에 뒤늦게 넣는 조건을 원논문이 지지한다고 쓰지 않는다. masked 입력 길이와 loss 대상 token 수는 따로 세며 기존 full-NTP 분모를 무심히 복사하지 않는다.

모든 비용은 총괄의 실제 단독 cost와 UTC 잔여를 다시 확인해야 한다. Parameter Golf의 학습10분은80 H100-GPU분, HRM-Text의46시간은16대 병렬 시간이다. 이를 단일 RTX의 분 단위 예측으로 환산하지 않는다. [기존 시계 영역 감사](/home/uranus/tinyLM/handoff/audit/WIP_20261019b_CLOCK_DOMAIN_REVIEW.json)가 있으므로 perf 기반 외삽만으로 오늘17시 준수를 보장하지도 않는다.

아직 실물 native/Broad 결과의 기본 과제 fitting을 확인하는 단계라면, 새 구조 여러 개를 동시에 넣는 것보다 기존 종점의 실제 질문/답·학습 표면·조건 교체를 먼저 보존하는 편이 해석 가능하다. 이 권장은 새로운 손실 가중치나 clip 상한을 정한 것이 아니며, 새 장기 학습을 자동으로 여는 gate도 아니다.

## 9. 열람 수준과 남은 검증

직접 열람한 것은 공식 사이트·논문 해당 절·공식/저자 repo의 표시와 필요한 코드다. 모든 논문 전문·모든 구현 파일을 완독하거나 공급자 실측을 재현했다고 주장하지 않는다. 특히2026 BabyLM strict 하위 문서, OpenSLM live scorer/index, 최근 색인 두 논문의 본문은 열람 실패를 보존한다. 논문 링크가 있다는 사실과 실행 코드가 공개됐다는 사실도 구별했다.

`openai-docs`의 공식 문서 도메인 검색에서는 Parameter Golf가 나오지 않았다. 사용자가 요구한 연구의 공식 출처를 확인하기 위해 OpenAI 공식 연구 사이트와 `openai/parameter-golf`를 실제 열었다. 제품 문서가 아닌 참가자 PR은 그 작성자의 주장으로 표시했으며 제3자 해설의 효과 수치로 근거를 대체하지 않았다.

새 파일은 이 문서 한 개다. 모델·GPU·CP tensor·bin·보호 자료·기존 raw 수정·다운로드·설치·Git·하위 agent 생성은 모두0이다. 문헌 조사가 새 구현·계수·문턱·실행 승인을 대신하지 않는다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.

## 10. 후속 확인 — 비교 목표는 정확한 Falcon 90M Base다

### 10.1 모델 정체성·학습량·자료·단계를 구분한다

정확한 대상은 [tiiuae/Falcon-H1-Tiny-90M-Base 공식 카드](https://huggingface.co/tiiuae/Falcon-H1-Tiny-90M-Base)다. 카드는 영어 causal decoder-only·Transformer/Mamba hybrid·90M을 선언하고, HF 파일 정보는 약91.1M/BF16을 표시한다. Instruct·다국어100M·reasoning·coder·tool-calling 모델의 성과와 섞지 않는다. 카드 일부 Usage 예시는 다른 SFT model_id를 가리키므로 예시 문자열을 Base의 학습 계보 근거로 쓰지 않는다.

공식 [Tiny 기술보고서](https://tiiuae-tiny-h1-blogpost.hf.space/)의 정확한 위치는 다음과 같다.

`Falcon-H1-Tiny-English: curriculum vs pre-train with SFT data` → `Curriculum model: final recipe` → `Base model`.

| 확인 대상 | 해당 절에서 확인한 공급자 진술 | 아직 미확인인 것 |
|---|---|---|
| Base 사전학습 | 최종 Base를800GT=800B 토큰으로 사전학습했다고 명시 | 독립 raw 로그/target 계수 재검산·800B 고유 원천량 |
| 최종 자료 | STEM 중심. FineWeb/FineWeb-Edu 계열 web10%/20% 대조 뒤20%를 채택 | 나머지 원천별 정확 비율·문서/샤드 manifest·고유량·모든 오염 제거 |
| 지도형 자료 | Base 최종 혼합에 SFT-style 자료를 넣지 않았다고 명시 | 모든 STEM 원천의 의미·형식을 전수 판정한 것은 아님 |
| Base 내부 일정 | 총800GT 안에100GT WSD decay와20GT batch rampup을 기술 | 별도로 더한900GT가 아님. 실제 GPU시간·완전 실행 영수증은 미확인 |

같은 보고서에서 Base 후속 SFT와 SFT-pretrain/DPO는 별도 모델 경로다. 이 단계를 정확 Base에 합산하지 않는다. 보고서는2026-01-15 발표로 표시되므로5월 이후 새 방법의 증거로 세지 않는다. ‘기억창을 고려한 안전한 무제한 반복’도 저자의 연구 가설이지 우리 기존 풀 반복 허가나 검증된 법칙이 아니다.

### 10.2 구조·tokenizer·문맥의 공개 범위

[정확 Base의 config.json](https://huggingface.co/tiiuae/Falcon-H1-Tiny-90M-Base/blob/main/config.json)을 웹으로 읽었다. 가중치나 tokenizer 전체 파일은 읽지 않았다.

| 항목 | 공개 config 관측 |
|---|---|
| 모델 | `FalconH1ForCausalLM`,24층, hidden512, intermediate768, `hidden_act=silu` |
| attention | Q8/KV2, head_dim64 |
| SSM | Mamba head24, d_head32, d_ssm768, d_state64, d_conv4 |
| 어휘·가중치 | vocab32768, tied input/output embedding, BF16 |
| 특수ID | BOS1, EOS11, PAD0 |
| 위치 설정 | `max_position_embeddings=262144`, `rope_theta=1e11` |

262144는 설정값이다. 실제 pretraining sequence length나256K 문맥에서의 정확도 검증값으로 승격하지 않는다. 정확 Tiny Base의 실제 학습문맥 길이는 이번 카드/보고서 열람에서 확인하지 못했다. 원 Falcon-H1 대형 모델의 설정이나 reasoning 모델의 GRPO 문맥을 대신 쓰지 않는다.

보고서의 `Model Architecture Ablations`는32768 어휘, tied embedding과 LaTeX 토큰·숫자/구두점 처리의 특화를 설명한다. 어휘 수가 chat32와 같아도 token ID·분절·언어 효율이 같은 것은 아니다. `tokenizer_config.json` 직접 열람은 실패했으므로 모든 전처리·추가 token·chat template까지 확인했다고 하지 않는다. Base의 영어 중심 원문학습을 한국어 대화 지도로 읽지 않는다.

### 10.3 600M급 TinyLM과 정량적으로 말할 수 있는 차이

공식 보고치800,000,000,000을 각 한 팔의 native draw로 나눈 단순 계산은 다음과 같다.

| TinyLM 분모 | Falcon 보고 노출 / TinyLM native draw |
|---|---:|
| 반올림한600,000,000 | 약1333.33배 |
| 완료595M 계열의595,460,096 | 약1343.50배 |
| 이전299M 계열의298,975,232 | 약2675.81배 |

이는 서로 다른 tokenizer로 센 누적 노출의 비율이다. 고유 문서·byte·동일한 정보·assistant 지도량·계산량의 비율이 아니다. 두 팔을 합쳐 한 모델의 노출로 세지도 않는다. [기존 로컬 정정](/home/uranus/tinyLM/docs/methods/08_paper_review2.md:1065)처럼 풀 크기와 실제 draw도 계속 구분한다.

따라서 ‘비슷한 파라미터 수지만 학습 노출·언어/자료·구조·정밀도·최적화가 크게 다르다’는 설명은 가능하다. 반면 ‘정답 격차의 몇%가 토큰 부족 때문’, ‘지능이1343배’, ‘도달하려면 반드시800B가 필요’라는 계산은 불가능하다. 영어 대비 한영 분배와 STEM 특화,24층 hybrid 대14층 dense/삼진, full tied embedding 대E256 head 등도 함께 달라져 있다. 동일 자료·단계·예산의 통제 대조 없이 노출량의 단독 인과를 식별하지 못한다.

보고서의 Base 표에서도 GSM8K flexible-extract는2.64로 낮다. 많은 학습량이 이 Base를 곧바로 신뢰할 수 있는 산수/대화 assistant로 만든 것은 아니다. 이 공급자 수치는 로컬 고정팩의 prompt·scorer·분모와 다르므로 현재 실측 정답률을 대체하지 않는다. Falcon을 비교 대상으로 유지하는 것과 모든 과제에서의 성공 기준으로 신격화하는 것은 다르다.

## 11. 후속 원문 확보 — 작은 BabyLM 예산에서 실제로 바꾼 것 세 가지

아래 세 원문은 모두2026-05 이후 공개된 아카이브 논문이다. 이번에는 초록만이 아니라 표시한 본문/부록까지 열었다. 공식 대회의 최종 수상·순위, 모든 코드의 실행 재현, 논문의 모든 인과 주장이 확정됐다는 뜻은 아니다. 특히 §4.5에서 본문 미확인으로 남겼던 Structural priors는 후속 열람으로 보완한 것이며, 앞선 실패 기록을 지우지 않는다.

### 11.1 코드스위칭 생성·검수와 순서 — Macaroni, 2026-09-24

[원문](https://arxiv.org/abs/2609.30535), [PDF](https://arxiv.org/pdf/2609.30535)의 §3–5·Appendix A/B를 확인했다. 약98M GPT-2·16k BPE·100M-word/10epoch 조건이다. 단순 무작위 단어 치환이 아니라 LLM으로 word/sentence code-switch를 만들고 언어 존재·동일/완전번역·길이 검사를 거쳐 이중언어 화자가 표본을 검수한다. 학습은 word-CS→sentence-CS→단일언어 문서 순서이며, 원문 문서 ID를 맞춘 비CS 대조와 shuffled 대조가 있다.

저자는8seed 평균 약+0.36점을 보고하지만 shuffled에서는 유의한 이득이 없다. 더구나 실제 BPE는138.9M 대135.0M으로2.9% 다르다. 동일 단어 예산을 완전히 동일한 token/계산 대조로 부를 수 없다. 각1H100의 학습 약2.3h·평가0.8h와 합성 API 비용이 별도 보고되므로 ‘작은 데이터이니 생성/탐색 비용도0’이 아니다. 영어·네덜란드어·중국어 정렬의 제한된 결과이며 한영 산수·지시답의 큰 향상을 보장하지 않는다.

논문은 [저자 코드](https://github.com/drooryck/multilingual-macaroni)를 연결하지만 이번에 코드 본문 fetch는 실패했다. 대신 실제 연 [저자 HF 카드](https://huggingface.co/drooryck/multilingual-macaroni-models)는24개 모델/8조건×3seed 배포를 설명하고 main에는 카드만 있으며 가중치는 revision별이라고 명시한다. 이는 논문의8seed 결과 전체를 배포 artifact로 대조했다는 뜻이 아니다. 표본/원점수/코드/모델 revision의 연결을 더 확인해야 한다.

### 11.2 언어별 노출 분포와 순서 — Language Exposure Matters, 2026-10-14

[원문 §3–4·Appendix A/B](https://arxiv.org/abs/2610.20102)를 확인했다. 약110M Qwen3형 causal decoder·문맥1024·32k BPE이며 비교 가능 도메인을 만들기 위해 세 언어의 Wikipedia를 사용했다. 각100M byte-premium-adjusted token 구성을 동일하게10회 노출한다. 같은 구성 안에서 처음부터 혼합하는 방법과 주언어 단독→균형 다국어 국면으로 나누는 방법을 비교하며 optimizer/scheduler 상태도 잇는다.

mixed는 대응15개 모두에서 curriculum보다 높은 다국어 평균을 보고했다. 이는 ‘무조건 교과 순서가 좋다’의 반례지만 단일seed42 결과다. 언어 배분을 달리한 구성끼리는 tokenizer도 다시 학습하므로 최적 언어비를 순수 비율 인과로만 읽으면 안 된다. 비교 점수에는 zero-shot과 task fine-tuning이 포함된다. 한영 자유답이나 한국어 최적 비율을 이 표에서 정하지 않는다.

원문이 선언한 코드는 [jinx2321/babylm26](https://github.com/jinx2321/babylm26)이며 직접 fetch는 실패했다. 별도로 열람된 [Leukas의 관련 README](https://github.com/Leukas/babylm26/blob/main/README.md)는 paper 연결을 TBA로 두고 기본값·optimizer·문맥이 원문의 설정과 달랐다. 이를 해당31실행의 정확한 source/config라고 대신 확정하지 않는다. 코드가 공개된다는 진술과 논문 조건이 기본 명령으로 재현된다는 사실은 다르다.

### 11.3 문법/구조적 사전학습의 양성과 음성을 분리 — Structural priors, 2026-09-10

[원문 §3–5·Appendix A/E/H](https://arxiv.org/abs/2609.11505)를 후속 열람했다. GPT-2에 PCFG·cellular automata·music·protein 등을 먼저 가르치고 영어/네덜란드어/중국어를 학습한다. PCFG는 품사 범주의 문법을 샘플링해 token ID로 채우며 균등/Zipf 어휘 빈도를 비교한다. vocab16897에 구조용512개를 두고 다음 국면에서 embedding을 재초기화한다. 추가 영어 Wikipedia 사전학습 대조도 있어 ‘더 먼저 학습한 것’과 비언어 구조 자체를 구분한다.

일부 조건의 언어 CE 개선은 관측됐지만 문법·언어벤치 향상은 일관되지 않았고 추가 자연어 대조보다 효율적이지 않았다. 초기 stopping·CE 곡선 지표를 사용하므로 현재 고정 전체 draw 실험과도 다르다. 부록은 주요 실험 약250 A100-GPUh와 제출용 탐색 약2250 A100-GPUh를 각각 보고한다. 작은 데이터 예산을 적은 전체 개발비로 읽지 않는다. 이 원문은 문법이 무료 일반지능 처방이라는 긍정 사례가 아니라, loss와 능력의 전이를 분리한 구체적 반증이다.

원문 앞의 GWDG GitLab code 연결과 [저자 출판목록](https://jonasmaymar.github.io/publications.html)의 해당 preprint는 확인했지만 코드 저장소의 파일·라이선스 직접 열람은 성공하지 못했다. 실행 가능한 커널/학습법 이식이 완료됐다고 하지 않는다. 이 embedding 재초기화 설정은 §4.1 Stack의 embedding/head 직접 이전과도 같지 않다.

### 11.4 추가 인용 주의 — 논문 뒤의 저자 정정도 읽어야 한다

[Augustinian BabyLM 원문](https://arxiv.org/abs/2609.11870)은2026-09-10의 작은 masked-LM/시각 embedding 초기화 연구다. 이번에 실제 연 [저자 repo](https://github.com/bylinina/augustinian_babylm)는 arXiv v1 §5.2/§6을 수정하는 pair-level 재분석을 맨 앞에 공지한다. 제한된 시각 속성 이득은 남지만 개별 seeded 단어의 인과효과로 귀속할 수 없고 synthetic grounding의 신뢰할 이득도 없다고 정정한다. 최신 저자 코드·분석까지 보지 않고 초록의 긍정 문장만 성공 처방으로 복사하지 않는다. 오늘의 추가 구현 후보로 채택하지 않았다.

## 12. 이번 scratch704 소식에 적용할 해석 경계

총괄이 전달한 ‘scratch704 train 완료, 현재 DEV exact0’은 이번 문헌 담당이 모델/로그로 독립 재검산한 값이 아니다. 전달된 그대로라면 기술적 학습 완료와 효과 양성을 분리해야 한다. 사전지식 없이 약2.2M assistant target만 학습한 해당 자료·마스크·일정·최적화의 결과이지, 동일 파라미터 모델의 일반적인 학습 불가능성이나 모든 작은 데이터 커리큘럼의 기각이 아니다.

위 BabyLM 논문들도 단순히 assistant target 약2.2M만 주고 일반 assistant를 만드는 동일 조건이 아니다. 자연어 사전학습·반복노출·선별/생성·초기화·평가용 fine-tuning 등이 다르다. input token, 지도 target, 고유 문서, 외부 생성 모델의 정보·계산을 분리해야 비교가 가능하다. Falcon800B와 이 target 수를 직접 나누어 필요한 과제 지도량을 추정하지 않는다.

현재 결론은 두 문장을 함께 보존하는 것이다. (1) 비슷한 파라미터 수의 Falcon Base와 우리의 기초학습 노출·자료·방법은 매우 다르다. (2) 큰 노출량이나 BabyLM식 교과라는 이름만으로 현재 실제 질문의 정답이 회복된다고 보장할 수 없다. 새 데이터 생성·문법 감독·언어 순서의 채택은 자료 의미 검산과 동일조건 대조를 거친 별도 결정이며 이번 추가절이 이를 승인하지 않는다.

이 후속 작업도 기존 문서의 끝에만 추가했다. 새 모델/GPU·CP tensor·자료 다운로드·설치·코드 변경·Git·하위 agent 생성은0이며, 새 수치·계수·clip 상한·실행 문턱을 채택하지 않았다.
