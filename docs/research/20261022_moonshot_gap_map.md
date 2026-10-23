# 작은 학습예산에서 답변 능력까지 남은 간극과 세 가지 조건부 도약 후보

작성: 2026-10-22. 상태: 문헌·기존 정본의 읽기 전용 분석과 이 문서 신설만 완료. 후보의 구현·학습·효과·실물 비용은 모두 NOT_RUN이다. [앞선 문헌 보고서](/home/uranus/tinyLM/docs/research/20261022_constrained_lm_literature.md)는 동결한 채 수정하지 않았다.

## 1. 결론과 선택지

작은 모델의 낮은 정답률을 곧바로 “파라미터가 작아서”, “삼진이라서”, “원문 토큰이 부족해서” 중 하나로 환원할 수 없다. 현재 남아 있는 서로 다른 가능성은 초기의 상태 갱신 학습, 질문에 맞는 근거 선택과 출력, 과제 학습과 원문 보존 사이의 최적화 간섭이다. 아래는 이 가능성을 각각 겨냥한다. 세 가지를 동시에 넣는 패키지를 권장하지 않는다.

| 후보 | 구체적 개입 | 얻을 수 있는 것 | 가장 강한 반례 | 변경·비용의 성격 |
|---|---|---|---|---|
| A. 초기 구조 워밍업 | 새 scratch에서 Stack 상태 예측 → 공통 자연어 → 공통 SFT | 같은 자연어 이후에도 조건·순차 상태 갱신을 더 빨리 배우는 초기점 | 초기 구조가 언어·단순 조회로 전이하지 않거나 삼진 학습 중 사라짐 | 새 scratch와 별도 합성 교과. 구현 중간, GPU 비용 큼 |
| B. 검증된 근거를 읽는 제한적 복사 | 깨끗한 원주석과 질문 조건의 공동 span 학습·원문 추출 | 주어진 문맥의 올바른 값을 고르고 문자열로 반환하는 경로 | head도 다른 대상을 고르거나 추출만 좋아지고 어휘 생성은 그대로 | 별도 pointer/readout·자료 의미 검산 필요. 비용 중간 |
| C. 보존과 가소성의 분리 | 과제/native gradient를 따로 측정하고 필요한 경우 충돌 성분만 투영 | 같은 지도량으로 실제 질문 fitting을 늘리되 원문 망각의 교환비 관찰 | 간섭이 주원인이 아니거나 Muon 이후 실제 이동량에서 이득이 사라짐 | 추론 구조 변경 없음. 진단은 작고 학습 개입은 중간 |

권장 순서는 C의 작은 원인분리, B의 깨끗한 라벨 대조, A의 새 scratch 탐색이다. C는 가장 빨리 “지도량을 늘리기 전에 같은 자료를 제대로 배우는가”를 분리한다. B는 성공해도 우선 문맥 추출 기능이고, A는 가장 큰 도약 가설이지만 기존 595M 뒤에 붙여 빠르게 검증할 수 없다. 이는 연구 우선순위의 의견이며 신규 실행·손실계수·문턱 채택이 아니다.

## 2. BabyLM의 작은 예산과 현재 TinyLM은 무엇이 다른가

### 2.1 비교의 분모

BabyLM Strict/Strict-Small의 원천 제한 100M/10M은 단어 수다. 2026 CFP §4.2의 반복 포함 노출 상한은 각각 1B/100M 단어이고, 평가에는 언어 우도뿐 아니라 과제별 미세조정도 들어간다. “작은 원천을 썼다”와 “약2.2M assistant target만으로 범용 assistant가 됐다”는 같은 조건이 아니다. 한국어·현재 교사 계보의 경쟁 참가 적격성도 확인되지 않았다. [BabyLM Turns 4 and Goes Multilingual, §4.1–4.4, 2026-02-24 v2](https://arxiv.org/html/2602.20092v2).

| 실제 전제·관측 | 현재 해석 |
|---|---|
| Native595 각 팔은 4543×8×16×1024 = 595,460,096 next-token targets | 한 모델이 양팔 합계 1.19B를 배운 것이 아니다. 원천·crop·WSD 지평이 달라진 299M→595M은 토큰량만의 인과가 아니다. [101 §403–407](/home/uranus/tinyLM/test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md:19636) |
| 약93M 파라미터로 단순 나누면 native 노출은 약6.4 targets/parameter | 세계지식의 수·필요량·성공 보장 수치가 아니다. 한영 언어별 실제 native target 비중은 미계측이다. |
| 같은 Broad704는 x21,621,776, assistant2,210,436, 별도 native5,767,168 targets | 입력 전체와 정답 지도량은 다르다. 한영 assistant target은 KO319,808/EN1,890,628로 약14.5%/85.5%다. 행 수나 번역 쌍의 균형과 다르다. [101 §417·419](/home/uranus/tinyLM/test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md:20168) |
| 무부모 NTP/MTP704의 DEV 첫답은 각각0/512 | 사전지식 없는 해당 초기화·지도·LR·일정의 음성이다. native595 후속 학생 전체나 소형 언어모델 일반의 불가능성으로 확대하지 않는다. [092 §18](/home/uranus/tinyLM/test_result/092_20260925_P100-정성한계-P101A-M0-이식문턱실패.md:783) |
| 현재 문제 표현인 “0~4/512” | 이번에 직접 정본으로 확인한 값은 위0/512다. 다른 코호트의 자연QA4/128·재시도 성공 등을 이 분모에 섞지 않는다. |
| SwiGLU·삼진/float route·E256 공유 어휘 head·CLA/KV 소유 계약 | 다른 모델의 같은 파라미터 수와 같은 표현력·tokenizer·학습 난도를 뜻하지 않는다. 저장 압축과 학습 중 FP32 잠재가중치/gradient 비용도 별개다. |

실제 원문에는 위키 평문 부록·웹 부속물이 확인됐지만 전수 구조 신호가 내용 불량률이나 반복의 인과 기여량은 아니다. 정제된 후보의 학습 효과는 미측정이다. 따라서 “무조건 원문을 더 주기”와 “무조건 더 정제하기”도 각각 별도 가설이다. [101 §436–438](/home/uranus/tinyLM/test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md:20844).

### 2.2 최근 원논문의 긍정뿐 아니라 전제와 음성

| 원논문·공개 날짜 | 실제로 바꾼 것과 해석 제한 | 세 후보에 주는 교훈 |
|---|---|---|
| [Feeding BabyLMs Macaroni: Code-Switching Curricula Cause Cross-Lingual Convergence](https://arxiv.org/abs/2609.30535), 2026-09-24 | LLM 생성·검수한 코드스위칭과 순서. 100M-word/10epoch, 실제 BPE 노출도 대조와 달랐고 이득은 작다. 생성 교사의 정보·비용이 외부에 있다. | 한영을 섞었다는 이름만으로 전이·지도 균형을 보장하지 않는다. |
| [Language Exposure Matters: Distribution and Order in Multilingual BabyLM Pre-training](https://arxiv.org/abs/2610.20102), 2026-10-14 | 같은 언어 노출 안에서 초기 혼합이 단계형보다 유리한 결과. 단일 seed이고 구성 간 tokenizer도 바뀐다. | 순서 변경을 보편적 처방으로 쓰지 않는다. 기존 mixed/staged 반복을 새 아이디어로 세지 않는다. |
| [Structural priors for data-efficient language learning](https://arxiv.org/abs/2609.11505), 2026-09-10 | PCFG 등 선행 학습의 CE 이득이 문법·다운스트림으로 일관되게 이어지지 않았다. 추가 자연어 대조와 embedding 재초기화가 중요하다. | A의 강한 반례다. 구조 교과의 낮은 loss만으로 성공 판정하지 않는다. |

위 세 원문의 해당 본문·부록 열람과 코드 공개 한계는 [동결 보고서 §11](/home/uranus/tinyLM/docs/research/20261022_constrained_lm_literature.md:271)에 남아 있다. 이번 후속의 직접 arXiv 재열람은 세 URL에서 실패했으므로 새 판본까지 다시 확인했다고 하지 않는다. 2026-05 이후 날짜는 앞선 직접 원문 확인값이며 정식 수상·동료평가 확정일을 뜻하지 않는다.

## 3. 기존 수행과 중복을 확인한 범위

전체 저장소·원문 트리를 검색하지 않았다. 아래 네 정본에서 Stack/LIFO/FIFO/구조 워밍업/PCGrad/Gradient Surgery/native 제거/N0/관계 대조/span/content_recovery 등 좁은 문자열과 해당 절을 확인했다.

    docs/METHODS.md
    docs/methods/08_paper_review2.md
    test_plan/P106B_Bonsai-자동번역-pseudo-SFT-온라인-교사학생-검증.md
    test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md

| 이미 수행·기재된 것 | 구분 | 이번 후보가 그대로 반복하지 않으려면 |
|---|---|---|
| 같은 질문의 CE 대 row-softplus, 이후 ROLE_ONLY4/ALL_AXES4 각896회 | 수행됨. 영어 관계 일반화 일부 양성, 한국어 새 표현 graph-all은 세 팔 모두0/64. [101 §299](/home/uranus/tinyLM/test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md:16318) | B를 같은 후보 우도 대조의 재소개로 만들지 않는다. 실제 근거 위치와 추출 경로를 독립변수로 한다. |
| 표현×질문 위치 네 팔384회·TRAIN T0 판독 | 수행됨. 최초 토큰 TF/free 일치에도 학습 표면 산수4/16·0/16, 조회 약절반. [리뷰08 §24](/home/uranus/tinyLM/docs/methods/08_paper_review2.md:1156) | 새 문구·질문 반복만으로 모든 실패를 설명하지 않는다. |
| 내용 평균 P 대 token CE 각384회 | 수행됨. TEST637→628/1024, Boolean242→256/256, 비Boolean395→372/768. [101 §335](/home/uranus/tinyLM/test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md:18024) | C를 짧은 답 CE 재가중으로 바꾸면 반복이다. |
| 질문 조건 rank64 span 보조학습과640개 readout | 수행됨. TEST 어휘13→공동추출16/256, 유일 부분문자열 위치의 의미 결함 발견. [101 §336–337](/home/uranus/tinyLM/test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md:18064) | 깨끗한 원주석을 같은 양팔에 쓰고 공동 span 목적과 출력 경로를 구분한다. 같은 결함 라벨 재실행은 반복이다. |
| mixed/staged Broad, Q/K head-wise Muon | 수행됨. 범용 설명/대상 연결 실패가 남고, head-wise도 기본 채택 근거 없음. [METHODS](/home/uranus/tinyLM/docs/METHODS.md:472) | A는 SFT 순서 변경이 아니고, C는 head별 Muon NS 분할이 아니다. |
| native 제거 N0·coded 가족 균형 F | 기존 문헌/설계 후보. 해당 좁은 정본 조회에서 N0 완료 실물은 확인하지 못함. [리뷰08 §23](/home/uranus/tinyLM/docs/methods/08_paper_review2.md:1134) | N0는 “새 발명”이 아니라 빠진 통제로 적는다. |
| 초기 Stack 전용 국면·PCGrad형 과제/native 투영 | 위 네 정본의 해당 검색에서 수행 기록을 찾지 못함 | 저장소 전체의 부재 증명은 아니다. 정식 계획 전 레지스트리·현재 소유 코드의 추가 확인이 필요하다. |
| 검산 단계가 있는 답과 직접답 대조 | 자료4096 root·CPU 동결은 이미 존재. 당시 비용 실패/복구 보류와 분리. [101 §424–426](/home/uranus/tinyLM/test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md:20387) | “짧은 풀이를 붙이자”를 네 번째 새 도약안으로 포장하지 않는다. |

## 4. 후보 A — 언어를 배우기 전에 상태 갱신을 배우게 하는 초기점

### 원문과 새 부분

[Lasting Effects of Abstract Pretraining Beyond Perplexity](https://arxiv.org/html/2609.38764v1)는 2026-09-30 v1이다. §3·§6·Appendix A.1/A.2/B.1에서 초기 Stack 전용 국면, 같은 native vocabulary의 이전, 입력·separator를 마스킹한 최종 상태 지도, FIFO/출력순열 통제를 확인했다. 135M/360M의 후속 자연어는 2.69B/7.20B이고 과제 SFT도 별도다. 이 문헌은 전반적 지식 향상이 아니라 순차 합성의 제한된 전이 근거다. 늦은 삽입은 초기 전용 국면과 같지 않았다. 저자 [procedural-pretraining](https://github.com/zlshinnick/procedural-pretraining) 연결은 확인했지만 9월 연구 전체 설정·라이선스 재현은 미확인이다.

우리의 새 부분은 이 순서를 한영·SwiGLU·현재 양자화 route에서 대조하는 것이다. 기존 자연QA SFT나 검산 단계 감독과 같은 목적의 일부를 공유하지만 학습 궤적의 시작점이 다르다. 원논문 비율·LR·80M급 워밍업을 그대로 채택하지 않는다.

### 왜 현재 실패에 작용할 수 있는가 / 반례

가설은 “이름과 값의 대응을 쓰고 지우고 유지하는 연산을 먼저 배우면, 자연어를 배운 뒤 질문이 바뀌었을 때 같은 문맥에서 다른 답으로 이동하는 학습이 쉬워진다”이다. 예를 들어 임의 기호의 push/pop 결과를 예측하는 학습은 지식 암기가 아니라 내부 상태 보존을 요구한다.

반례는 강하다. 현재 단순 한 단계 조회도 약하고, 실패가 어휘·지도 희소성·최적화 때문이면 Stack의 순차 구조와 맞지 않는다. 구조 교과만 암기하고 자연어로 전이하지 않거나 삼진 STE/CLA에서 그 초기점이 유지되지 않을 수 있다. 작은 언어 CE 차이 또는 Stack 정확도 상승만 남으면 일반 질문의 개선 가설은 지지되지 않는다. 모르는 사과·농구 지식은 이 기호 과제로 생기지 않는다.

### 최소 반증과 자료 경계

탐색 최소 비교는 같은 초기 seed의 Stack와 추가 자연어 워밍업이다. 구조 자체를 주장하려면 같은 입력 연산·길이·마스크의 FIFO 또는 출력순열 통제가 더 필요하다. 공통 자연어 국면과 공통 SFT는 이후에 같게 한다. 기존595M CP는 참고 앵커이며 새 초기 국면의 엄밀한 무작위화 대조로 재사용하지 않는다.

합성 TRAIN/DEV/TEST는 서로 다른 seed·기호 대응·연산열 root로 미리 분리한다. 기존 평가 질문·답은 생성 재료가 아니다. chat32 특수ID를 임의 기호로 쓰지 않고, 기호의 token/byte 표현과 EOS·shift·output-only 분모를 먼저 고정한다. 논문 방식의 단순 arbitrary ID 과제와 자연어 문자열로 만든 과제도 같은 실험이라고 부르지 않는다.

같은 native 실험 안에서 추가 자연어 워밍업 W를 포함한 누적 draw까지 TRAIN≥2×draw를 다시 계산해야 한다. 현재 1,191,116,192−2×595,460,096=196,000 ID 여유뿐이다. 같은595M 위에 큰 자연어 워밍업을 공짜로 얹을 수 없다. 공통 후속 자연어 길이를 양팔에서 줄이거나 별도 원천·규칙 승인이 있어야 하며, 그때는 원래595M 조리법 그대로의 재현이 아니라고 쓴다. 패딩 연산량·loss target 수·자연어 노출을 동시에 같은 척도로 부르지 않는다.

성공 방향의 관측은 같은 후속 지도량에서 새 기호·새 문구·새 조건의 질문 연결이 개선되고, 언어별 일반QA/보존 손상이 함께 보고되는 것이다. TRAIN만 개선되면 전이 가설은 약해진다. 대조도 못 배우면 난도·지도·양자화와 초기점의 구분이 안 된 것이지 구조 워밍업의 보편적 기각이 아니다.

### 접합과 비용

SwiGLU·공유 어휘 head·attention/CLA 소유·실제 cfg는 고정하고 첫 학습 국면만 추가한다. 양자화 route는 비교 안에서 동일하게 유지한다. float로 구조를 가르치고 삼진으로 바꾸면 초기점과 양자화 전환이 동시에 달라지는 별도 연구다. MTP는 처음에는 끄며 추론 head/KV 상태를 새로 추가하지 않는다. 구조 검증에 성공해도 shared/tied 압축형으로의 전이는 별도다.

실물 비용은 미측정이다. 기존595M 한 팔의 UTC 약3.1~3.2h는 다른 교과·loss·clock 조건에서의 참고치일 뿐이다. 예를 들어 세 팔 각각 native≤4h·워밍업≤1h·공통SFT≤1h, 전체 평가/기록6h·준비/비용검사4h이면 3×6+6+4=28h라는 자원 틀이 가능하다. 이는 상한을 새로 정하거나 실제 소요를 예측한 값이 아니다. 새 초기·말기 경로 cost가 그 틀과 현재 절대기한에 들어가야 ≤40h가 성립한다. 한 seed 세 팔은 탐색이며 반복 seed의 견고성까지 자동 포함하지 않는다.

## 5. 후보 B — 질문에 맞는 원문 span을 선택하고, 복사와 지식을 구분한다

### 원문과 실제 병목

[Get To The Point: Summarization with Pointer-Generator Networks](https://aclanthology.org/P17-1099.pdf)는 2017년 ACL 논문이다. §2.2 식(8)–(9), 인쇄 p.1075에서 생성 분포와 source 위치 확률을 혼합하고 같은 단어의 여러 출현 확률을 합산한다. [저자 코드](https://github.com/abisee/pointer-generator/blob/master/model.py)도 공개되어 있다. LSTM 요약의 선례이지 현재 한영 QA·삼진 모델의 효과 증거나 2026 신기술은 아니다.

이미 수행한 [128-case token 감사](/home/uranus/tinyLM/handoff/audit/WIP_20261019b_COPY_TOKEN_ELIGIBILITY.json)의 고유 원질문은64개다. 실제 전체 prefix의 본문 ID bank가 첫 assistant target ID를 지원한 것은20/128, 전체 content ID는16/128, token 위치 기준432/588이었다. 반면 정답 위치를 아는 사후 문자 oracle은 outer-strip106/128, 어느 정확 출현이든108/128이다. 따라서 raw-ID 혼합을 바로 붙이는 처방보다 원문 구간을 반환하는 경로가 더 직접적이다. 문자열 oracle은 head 정확도가 아니고, target-ID 미지원은 어휘 생성으로 그 문자열을 만들 수 없다는 뜻도 아니다.

### 구체적인 새 방법과 기존 반복의 경계

후보는 “기존 span03을 다시 더 오래 학습”이 아니다. 깨끗한 원주석 offset 또는 코드로 의미가 결정되는 TRAIN 사실 그래프를 양팔에 동일하게 주고, 질문 조건의 유효 공동 span과 어휘 생성을 비교한다. 자연 자료의 원천 후보는 기존 계획에 있는 KorQuAD/SQuAD지만, 이번에 원자료를 열거나 추가 유효량·라이선스·오염을 확정하지 않았다. CoQA 자유답을 reference.index로 찾는 라벨은 재사용하지 않는다.

공동 span의 로컬 목적 후보를 명시하면 다음과 같다. q는 질문을 포함한 실제 prefix, B는 선언된 reference 안의 유효 start/end 쌍, A는 TRAIN 원주석으로 의미가 확인된 정답 span 집합이다.

    z(s,e) = start_score(s) + end_score(e),   (s,e) ∈ B, s≤e
    L_span = −log sum[(s,e)∈A] exp z(s,e) + log sum[(s,e)∈B] exp z(s,e)

이는 원 pointer-generator 식(9)의 재현이 아니라 위치의 중복 정답을 주변화하는 로컬 span안이다. 문자로 우연히 같은 모든 부분을 A에 넣지 않는다. 예측 때는 A·gold·정답 길이·정답 source 위치를 전달하지 않으며 bank는 전체 prefix의 선언된 본문 범위만으로 구성한다. 원문을 따로 재토큰화해 경계 실패를 고치지 않는다. 토큰이 답 경계를 덮으면 실패/복구 가능성을 그대로 별도 계수한다. A가 비는 행에 억지 위치를 붙이거나 log0을 계산하지 않고 CE는 유지하며 span 지도가 없음을 기록한다. 평가에서는 같은 행을 그대로 포함한다.

### 최소 반증과 범위

가장 작은 대조는 같은 깨끗한 TRAIN·부모·batch에서 CE-only와 CE+span을 학습한 뒤, 양팔의 어휘 greedy 답과 span을 실제 학습한 팔의 원문 추출 답을 따로 보는 것이다. 미학습 head를 학습 head와 동급 기준으로 세지 않는다. 이 두 팔만으로는 깨끗한 지도와 새 출력 경로를 합친 패키지 효과까지만 식별한다. 공동 목적 자체가 기존 독립 start/end 목적보다 낫다고 주장하려면 같은 깨끗한 자료로 CE+독립 span을 학습하는 추가 대조가 필요하다.

최소 목적은 “질문에 따라 근거가 바뀌는가”다. 같은 문맥에서 다른 대상·같은 속성을 묻는 쌍과 사실 배정을 바꾸는 새 TRAIN root를 미리 만들되, 이미 반복 관찰한 평가 문항/답을 학습에 옮기지 않는다. 기존 평가팩은 그대로 관찰용이고 새 보류 root는 훈련 전에 분리한다.

잘못된 음성 방지는 답의 종류·동일 문자열·동의 의미·여러 정답 여부를 TRAIN 명세에서 확인하는 것으로 시작한다. 의미상 둘 다 맞거나 같은 값을 가리키면 서로를 음성으로 쓰지 않는다. 후보 보기나 정답 type 힌트를 추론 prompt에 넣어 성적을 올리는 비교도 아니다. 성적이 낮다는 이유로 평가에서 boundary 실패·비추출 문항을 사후 제거하지 않는다.

기존 span은 TRAIN36→77/128과 달리 TEST13→16/256에 그쳤고, “네 번째 생일”의 ‘네’를 긍정답의 근거로 지도했다. 이 반례 때문에 새 이득은 깨끗한 라벨만의 효과, 공동 목적의 효과, 출력 방식의 효과로 구분해야 한다. 깔끔한 위치 주석을 썼어도 질문을 무시하고 같은 사람의 값을 계속 고르면 복사 병목보다 연결 병목이 남는다. 추출만 나아지고 어휘 답은 그대로라면 범용 assistant 개선이라고 쓰지 않는다.

### 접합과 비용

SwiGLU와 기존 shared/E256 어휘 head를 바꾸지 않고, prefix hidden의 FP32 rank64 start/end q/k head를 별도로 두는 방식이 가능하다. 기존 동일 형태는4×768×64=196,608 parameters, 논리 FP32 약0.75MiB였다. 이를 압축 모델의 무료 용량으로 세지 않는다. CLA의 내부 attention 확률을 그대로 pointer 확률이라고 가정하지 않고 마지막 질문 조건 hidden과 source hidden을 쓴다. 추론은 prefix-only/no-KV 추출과 기존 KVon greedy를 각각 기록하고, MTP·자동 라우팅은 첫 대조에 넣지 않는다.

새 byte/문자 경계 head나 생성/복사 gate까지 만들면 또 다른 구조다. 첫 비교에서 그것을 몰래 추가하지 않는다. span 외 답이 필요한 질문·사실판단·설명·산수는 생성 경로가 여전히 필요하고, 자동 선택기는 정답을 보지 않는 별도 학습/검증 대상이다.

CPU 의미/offset 검사와 새 loss 회귀의 개발시간은 미측정이다. 가정상 두 팔 학습 각각≤2h, 양 출력 평가/기록≤3h, 준비/비용검사≤5h이면12h 규모라40h 안 탐색은 가능하다. 기존640 readout이 약73초였다는 사실로 새 head 학습·오프셋 검산·큰 평가가 같은 비용이라고 외삽하지 않는다. 실제 clean TRAIN가 부족하거나 경계 처리가 새로 필요하면 오늘 적용 후보에서 내려도 되며 이는 pointer 원리의 기각이 아니다.

## 6. 후보 C — 같은 답을 배우려는 gradient가 보존 항에 묻히는지 분리한다

### 원문과 로컬 근거

[Gradient Surgery for Multi-Task Learning](https://arxiv.org/pdf/2001.06782)은 2020-01-19 제출, 열람한 v4는2020-12-22다. §2.2–2.4·Algorithm 1, PDF p.3–4는 서로 반대 방향인 task gradient의 투영을 정의한다. 저자는 음의 내적만으로 해롭다고 단정하지 않고 크기 불균형·곡률과의 결합을 다룬다. [저자 PCGrad 저장소](https://github.com/tianheyu927/PCGrad)의 공식 구현은 TensorFlow이며 현재 PyTorch/Muon의 즉시 적용 코드가 아니다. 새2026 논문으로 세지 않는다.

실제 [content driver](/home/uranus/tinyLM/scripts/diag_p106b_content_recovery.py:350)는128대화/16micro의 assistant gradient를 누적한 뒤 native 평균 R/8192를 더하고 clip1을 적용한다. [native route SFT](/home/uranus/tinyLM/scripts/diag_p106b_native_weight_route.py:786)도 두 목적을 합쳐 clip한다. 전체 update의 분모는 [components/normalized_loss](/home/uranus/tinyLM/tinylm/train/mtp_sft.py:117)가 소유한다. native target 수가 많다는 사실만으로 “8192배 지배”라고 하지 않는다.

P가 EOT의 계수 질량을 보존했어도 실제 gradient·clip·망각은 보존하지 못했고, Broad의704/704 clipping도 관찰됐다. clipping 자체는 결함이나 학습 불능의 증거가 아니다. 하지만 gradient 합을 관찰하지 않은 채 자료 부족 하나로 넘어가면 값싼 원인분리가 빠진다.

### 구체적 개입과 최소 반증

먼저 같은 TRAIN의 한 update에서 g_task와 g_native, 합의 norm/내적, clip scale, optimizer 이후 실제 Δθ와 각 gradient의 내적을 따로 기록하는 진단을 제안한다. 동일 원문/질문 표면의 내용 CE·EOT CE·첫답을 함께 보고, 한 점의 음의 cosine만으로 긴 학습을 열지 않는다.

최소 통제는 기존 목적과 N0다. N0는 기존에 제안된 native 제거 극단 대조이지 새 방법이 아니다. 계산량을 맞출 목적이면 N0도 같은 native forward/backward를 수행하되 적용 gradient에서만 제외하고, native를 실제로 학습하지 않았음을 별도 명시한다. 원문 보존 손상을 함께 보아야 한다. N0가 같은 TRAIN fitting도 개선하지 못하면 replay 간섭을 주원인으로 삼는 가설은 약해진다.

간섭과 fitting 개선의 연결이 관찰될 때만 새 개입인 PCGrad형 두 목적 투영을 비교할 근거가 생긴다. 원형은 g_i·g_j<0인 경우 다음을 적용하고 각 수정 gradient를 합친다.

    g_i' = g_i − (g_i·g_j / ||g_j||²) g_j

이는 짧은 답의 계수를 다시 올리는 P와 다르다. 전체 update의 assistant/native CE·EOT 정의·자료·batch·LR·clip은 유지하고 gradient 합성만 바꾼다. 영벡터·공유 parameter의 중복·FP32 누적·분모0·NaN을 처리해야 한다. 기존 양팔의 회귀를 통과했다는 주장도 하지 않는다.

### 왜 도약 가능성인지 / 강한 반례

지식이 어느 정도 있는 본체가 희소한 질문-답 신호를 매번 보존 방향과 상쇄한다면, 추가 지식을 만들지 않고도 같은 지도량의 유효 업데이트를 늘릴 가능성이 있다. 이 경우 새 raw 원문을 수억 토큰 더 주는 것과 다른 비용 대비 이득이 생긴다는 것이 도약 가설이다.

반대로 scratch704의0/512는 사전지식 부족·낮은 SFT LR·부족한 지도량으로도 설명된다. N0 개선만으로 native가 잘못됐다고 할 수 없고 더 큰 망각과 맞바꾼 결과일 수 있다. 투영은 도움이 되는 공동 성분까지 없애거나 두 목적이 거의 정반대일 때 학습을 정체시킬 수 있다. 과제만 좋아지고 원문이 악화하면 Pareto 개선이라 부르지 않는다.

특히 실제 optimizer는 Adam/Muon이다. raw gradient의 직교성이 precondition·NS·momentum·WD 뒤 실제 파라미터 이동에서 보존된다고 보장할 수 없다. 삼진에는 STE 창과 잠재가중치→양자화 출력의 비연속성도 있다. 그러므로 논문의 일반적 수렴 분석을 이 모델의 보존 보장으로 복사하지 않고 실제 Δθ·원문 CE·자유답으로 반증한다.

### 접합·손실효율·비용

이 후보는 SwiGLU·CLA/KV·입출력 shared 구조·추론 MTP를 바꾸지 않는다. 고유 Parameter 단위로 g_task/g_native를 모으고 같은 clip/optimizer에 전달한다. 공유 embedding은 입력과 출력의 기여를 둘 다 포함해야 하며, 같은 parameter를 alias 키 수만큼 중복 투영하면 안 된다. 추가 추론 head/메모리는0일 수 있지만 학습 gradient 저장은 공짜가 아니다.

93M의 FP32 gradient 한 벌은 단순 논리 계산372MB, 두 벌744MB다. 기존 .grad·합성 버퍼·optimizer/compile까지 포함한 peak는 이보다 커 실제 측정이 필요하다. 기존 순차 backward를 저장·분리하면 forward 수를 꼭 두 배로 할 필요는 없지만, 전체 task별 backward를 다시 실행하는 구현이면 비용이 늘어난다. CPU로 옮기면 시간·전송 비용도 별도다.

[Cut Your Losses in Large-Vocabulary Language Models](https://arxiv.org/abs/2411.09009)의 exact CE 경로는 향후 자원 보조 후보일 뿐 이 도약 가설의 필수조건은 아니다. [저자 구현](https://github.com/apple-aiml-research/ml-cross-entropy)의 기본 gradient filtering과 exact 옵션을 구분해야 한다. 이미2048 위치 chunk+head checkpoint가 있으므로 우리32k/E256 head에서 큰 절감을 가정하지 않는다. kernel을 바꾸면 값·gradient·shift·IGNORE·공유 embedding 경로와 전체 update를 먼저 확인해야 하고, 새 설치 승인이 없으면 기존 CE로 한다.

실물 비용은 미측정이다. 가정상 기존/N0/투영 세 팔의 같은 SFT가 각각≤2h, 분리 gradient cost·회귀·준비≤5h, 평가/기록≤4h이면15h다. 실제 추가 버퍼·compile·부분 gradient 비용이 이 안에 들어갈 때만40h 안 탐색이 성립한다. 기존 학습 원답/보고를 엄밀한 같은 조건 기준으로 재사용할 수 있으면 새 기준팔 비용을 줄일 수 있지만, source·mask·부모가 다르면 생략하지 않는다.

## 7. 세 안 공통의 반증·오염·시간 조건

1. 기존 시험 질문·gold·Falcon 답·BabyLM 평가 자산을 새 TRAIN로 옮기지 않는다. TRAIN용 코드 생성/원주석과 보류 root의 분리는 새 학습 전에 고정한다. 이미 본 TEST는 모니터 코호트로 남기고 blind 평가라고 재명명하지 않는다.
2. KO/EN은 입력/target/원천/root/출력으로 나누어 보고한다. 동일 tokenizer의 언어별 부호화 효율과 답 길이를 확인하지 않은50:50 주장, 영어 성적만으로 한국어 개선 주장은 하지 않는다.
3. CE·teacher forcing·후보 순위·추출·greedy 자유답은 별개다. 정답 선택만 나아졌으면 그 범위, TRAIN만 나아졌으면 fitting 범위, 일부 Boolean만 나아졌으면 그 범위로 결론낸다. 현재512문항의0과 다른 평가의4를 합쳐 새 성적을 만들지 않는다.
4. 구조·양자화·지식 공급을 동시에 바꾸지 않는다. 같은 정확 cfg·route·tokenizer·부모·draw·마스크·seed·precision·context·EOS·생성상한과 언어별 평가를 정식 계획에서 동결해야 한다. float를 일반 loader로 삼진화한 비교는 허용하지 않는다.
5. 각 비용표는 “성립하려면 이 안에 들어야 한다”는 산술 예시다. 실측 ETA·새 실행상한·효과 문턱이 아니다. 합성/의미검수·CPU 준비·cost·원답 읽기·실패 보존까지 총예산에 넣어야 하며, 세 후보를 모두40h 안에 하겠다는 합산 계획도 아니다.
6. ≤40h 후속과 오늘2026-10-22 17:00KST 권한은 다른 조건이다. 이미 지난 기한이나 남은 시간 밖의 학습을 자동 승인하지 않는다. UTC/perf 차이의 기존 관측 때문에 perf 외삽만으로 달력 종료를 보장하지 않는다. 비용과 기록 예비는 총괄이 현재 기한에서 다시 판단한다.

## 8. 이번 수행·권한·남은 확인

방법 비교에는 impact-analysis의 세 안 비교, exp-plan/exp-preflight의 예측·반례·비교조건 원칙을 적용했다. 정식 실험계획·태그·새 benchmark·손실계수·clip 상한을 만들거나 채택하지 않았다. 현재 조건의 판정자와 레지스트리 기계 검사는 실행하지 않았으므로 preflight PASS가 아니다.

기존 결과/계획/방법론, 관련 손실 코드의 좁은 부분, 작은 copy 감사 JSON, 공식 논문/저자 repo를 읽었다. 원 논문의 전체 실행·모든 code/config·모든 라이선스를 검증한 것은 아니다. 새 구조의 성과는 모두 가설이고 PCGrad·pointer는 오래된 원리의 새 로컬 조합이다.

실제 변경은 이 연구 문서 한 개다. 기존 동결 보고서·코드·실험 원본·캐시·Git 변경은0이다. CP·bin·보호 datasets/TinyDataset·다른 환경 지침은 접근하지 않았고, 모델/GPU·다운로드·설치·하위 agent 생성도0이다. 기존 원문/질문·답을 복제한 새 자료 파일도 만들지 않았다. 별도 WIP/계획/기준표의 변경은 현재 한 파일 쓰기 권한 밖이라 하지 않았고 총괄이 소유한다.

이 점검은 알려진 설계 실수만 걸러낸 것이고, 실제로 그런지는 돌려봐야 압니다.
