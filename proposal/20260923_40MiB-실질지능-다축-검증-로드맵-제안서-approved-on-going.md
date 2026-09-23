# 제안 — 40 MiB 제약 아래 실질 지능·대화능력을 확보하는 다축 검증 로드맵

> **작성** 2026-09-23 · **상태** 🔄권장 C안 승인·진행 중 · **분류** 모델 품질 / 데이터 / SFT / 평가
> 양식: [proposal/README.md](README.md) §3. 이 제안은 새 GPU 런이나 배포 기본값의 자동 승인이 아니다.
> 이 문서 초안 작성 당시 큐가 진행 중이라 원본 로그·런처를 읽지 않았다. 2026-09-23 큐 종료 뒤 결과 회수와 §9.3 재우선순위 보완이 있었으며, 신규 GPU 패널은 사용자 실행 전까지 NOT_RUN이다.

## 1. 배경 — 무엇을 설명해야 하나

[4차 리뷰](../docs/review/202609031800_4차리뷰_초안_40MiB-일반지능과-외부모델-벤치마크-대조_absorbed.md)는
당시 TinyLM 81.2M/300M-token base가 HellaSwag 29.8%, PIQA 56.0%, ARC-Easy
39.0%이고 제작자 보고 소형 외부 모델보다 5~12%p 낮다고 적었다. 그러나 같은
문서가 prompt, shot 수, 정규화, tokenizer와 모델 상태가 달라 **직접 뺄셈을
하면 안 된다**고 명시한다. 수천 배의 학습토큰 격차는 강한 가설이지만
**그 격차의 주원인이 토큰량이라고 인과 확정한 실험은 없다**. 파라미터 수,
데이터 종류·정제, 학습 recipe, base 대 instruct/SFT, 채점 harness,
양자화 전후 정확도와 실제 상주가 함께 다르다. 특히 31.1 MB Falcon GGUF는
instruct 판이고 제시된 상식 점수는 원본 bf16의 제작자 수치다. 파일 크기와
실행 peak도 같은 자가 아니다. 이 표는 우선순위 생성용 관찰이지 TinyLM의
동예산 패배나 토큰 하나의 인과효과 증명이 아니다.

저장소에서 직접 확인된 것은 더 좁고 강하다.

| 축 | 이미 확인된 증거 | 이 제안이 금지하는 과장 |
|---|---|---|
| 반복 노출 P087 | 같은 300M pool의 e1/e2/e4 final val 3.64328→3.52781→3.45344, Stage3bW paired full-val 차 −0.2116. [P087](../test_plan/P087_반복노출-1-2-4epoch.md)와 [결과 073](../test_result/073_20260904_P087-두-번째-epoch은-과적합-없이-0.1155를-준다.md) | loader의 복원추출 draw/pool을 정확한 순회 epoch라고 부르지 않는다. 단일 seed loss 이득을 대화·논리능력 이득으로 승격하지 않는다 |
| 데이터 recipe P097 | 공통 평가 완주. control 공통 byte-bpb 1.3355, FineWeb2 KLUE-YNAT 40.9%·ARC-Easy 36.3%; KoBEST/NLI/HellaSwag 전면 우세 아님. [P097](../test_plan/P097_한영-코퍼스-조합-300M-품질-대조.md) | 새 corpus 하나로 지능 문제가 해결됐다고 주장하거나 기본 데이터를 즉시 교체하지 않는다 |
| 평가 | full-val과 downstream 정확도 서열 역전, 한국어 held-out 판본·관계 편향, 영어 소표본 분해능 한계. [6차 리뷰](../docs/review/202609181843_6차리뷰_초안_기준프리셋-승격후보-4안.md) §5, [방법론 10](../docs/methods/10_benchmarks.md) | loss와 정확도와 사람이 읽는 응답을 하나의 종합 점수로 합치지 않는다 |
| 부모·KD | 부모초기화 기여 −0.1386 loss, 300M 내부 KD는 두 seed에서 +0.0208/+0.0219 악화. [방법론 03](../docs/methods/03_knowledge_quality.md) | KD를 기본 지능 해법으로 복귀시키거나 좋은 교사 이름만으로 효과를 가정하지 않는다 |
| SFT | ChatML 직렬화, canonical 스키마, assistant-only mask, 일부 채점 도구는 있으나 기존 ko-en tokenizer의 ChatML 단일 ID는 0개이고 정식 trainer 연결·고품질 다회전 corpus·동적 SFT 결과가 없다. [P090](../test_plan/P090_SFT-경로.md) | base LM의 대화 실패를 곧바로 구조적 지능 부족으로 귀속하지 않는다 |

SFT는 표현 형식·지시 준수·대화 턴 전환을 직접 가르칠 수 있다. 반대로
SFT만으로 없는 사실 지식이나 긴 추론이 자동 생긴다는 보장도 없다. 따라서
사전학습 지식, 행동 정렬, 단기 문맥 활용, 외부 도구가 해결한 능력을 분리한다.

## 2. 목적 — 무엇을 얻나

같은 모델 계보·어휘·예산에서 **데이터 다양성, 반복 draw, SFT, 추론 형식,
구조와 평가 방법**의 기여를 분리해 한국어·영어 응답능력과 40 MiB 배포
Pareto를 올리는 근거를 얻는다. 정확히는 (a) 관련 답변, (b) 형식 준수,
(c) 멀티턴 단기기억, (d) 검증 가능한 논리, (e) 상식/언어 이해,
(f) 모델 파일·상주·속도를 각각 판정한다.

## 3. 성과물 — 승인하면 무엇이 생기나

| 산출물 | 내용과 판정 경계 |
|---|---|
| 능력 기준판 | 동일 checkpoint/tokenizer의 base·SFT 전후를 같은 prompt/seed/decoding으로 비교; 한국어·영어 개별 표 |
| P097 후속 | 기존 control/FineWeb2 강점을 별도 seed·공통 문항에서 확인하고 한국어/영어 split·source mix와 데이터 중복을 기록; 전면 승자 없으면 교체 보류 |
| P087 재질문 | 같은 원천 pool·동일 tokenizer에서 draw/pool 1·2·4를 단계별 확인; 한국어 val이 살아 있고 exposure/step/LR horizon을 분리한 신규 계획이 선결 |
| P090 SFT pilot | 기존 32k tokenizer로 checkpoint 호환을 지키는 ChatML 평문-marker pilot, assistant-only mask·멀티턴 데이터·망각 평가·정확한 중단기준 |
| P075 chat32 별도 계보 | 예약 32 슬롯을 단일 ID로 가진 **새** tokenizer와 **새로 학습한** checkpoint; 기존 embedding/head에 새 어휘를 끼워 넣지 않음 |
| 공개 데이터 카드 | Apache-2.0 후보의 repo/revision/license, 한국어·영어 규모와 선별 규칙, train/val 그룹 split, 중복·오염·품질 감사 |
| 실제 응답 패널 | 원문 prompt, 생성 전체 텍스트, checkpoint hash, tokenizer hash, decoding, gold/rubric, 비맹검/맹검 사람 평가를 JSONL로 보존하는 사용자 실행 경로 |
| 모델별 결과 | LM loss, common byte-bpb, held-out, 영어/한국어 benchmark, format/multi-turn exact checks, sample inspection, 메모리·속도와 실패를 각각 기록 |

승인된 Aya·OASST1 원천 2종을 고정 revision으로 `HF/sft_sources`에
확보했다. v2는 1024토큰 초과 30건을 제외했지만 train/val 첫 질문이
1건 겹쳐 **학습용 무효**로 보존했다. 출처·tree를 가로질러 정규화 첫
질문으로 분할한 v3는 train 2,996(ko 175/en 2,821), val 158(ko 9/en 149),
교차 첫 질문 중복 0·길이 초과 0·빈 mask 0이다. v2의 한국어 OASST
레코드 4건을 다회전 4건으로 읽은 이전 보고는 오류였으며,
v2·v3 모두 한국어 다회전 train/val 0건이다. 따라서 **한국어
멀티턴 능력 판정 자료가 없다**. 독립 `scripts/train_sft_p090.py`의
합성 batch·교차 split 거부 fixture만 CPU PASS했다.
품질·PII·보호 held-out 오염·SFT 모델 학습·직접 프롬프트 실행·진행 중
큐 결과 반영은 `NOT_RUN`이다.

## 4. 비용

| 항목 | 수량·상한 |
|---|---|
| GPU | **지금 0 GPU-h**. 승인 뒤 P097 추가 seed는 기존 계획 기준 ⚙6h, P087 새 반복 패널은 역사적 Stage1/2의 5.1h+6.8h를 상한 참고로 재추정, SFT pilot ⚙1~3h/조건. 합계 ⚙20~35 GPU-h는 계획치이지 예약·실행 사실 아님 |
| AI 작업 | ⚙8~14h: 데이터/토크나이저/SFT 계약·평가 패널·오염 fixture·보고 |
| 디스크 | Aya 원천 약 140 MB와 OASST1 ready trees 약 34 MB + 파생 corpus·새 모델 checkpoint 별도; 실제 checkpoint 크기는 계획 후 측정 |
| P097 추가 원천 | 현재 다운로드 0 GB·GPU 0h. 신규 원천의 실제 크기·라이선스·학습시간은 G1b source 결정과 preflight 전 NOT_ESTIMATED; 위 ⚙20~35 GPU-h에 포함하지 않음 |
| 사용자가 직접 해야 하는 일 | 공개 데이터의 사용조건·샘플 품질 확인 ⚙0.5~1h; 큐 종료 후 GPU 실행 승인과 로그 회신은 단계별 결정 |
| 네트워크 | 사용자 승인 아래 pinned Aya·OASST1 원천 2건을 별도 `HF/sft_sources`에 취득했다. 추가 한국어 Aya Collection 약 974 MB는 큐 중 미다운로드 |
| 보호 범위 | `datasets/TinyDataset/**`의 읽기·나열·검사는 별도 승인 전 0회. 평가 held-out 원본도 직접 열지 않음 |

## 5. 원리·근거

**내부 실측**: P087은 동일 pool 추가 노출이 LM loss를 크게 낮춘다는
증거지만 능력별 답변 증거는 아니다. P097은 데이터 변경이 언어·과제별
장단점을 바꾼다는 증거이며 만능 recipe는 없었다. P090의 기존
ChatML 경계는 현 tokenizer에서 1개가 아닌 여러 토큰이고 1000-record
fresh v1은 당시 계획 권장량에 미달했다는 역사 기록이 있다. 레코드 수와
토큰 수의 분모를 혼동하지 않기 위해 0.7%라는 과거 비율은 여기서 재사용하지 않는다. 현재
보호 원본은 열지 않았으므로 이 수량을 2026-09-23 재확인값이라 하지 않는다.

**공개 자료**: [Aya Dataset 공식 카드](https://huggingface.co/datasets/CohereLabs/aya_dataset)는
204k human-annotated 다국어 instruction pair, Korean/English 포함, Apache-2.0이라고
명시한다. [OASST1 공식 카드](https://huggingface.co/datasets/OpenAssistant/oasst1)는
Apache-2.0·ready conversation trees 10,364개와 한국어 1,553 **메시지**를
기재한다. 이는 한국어 멀티턴 대화 **1,553건**이라는 뜻이 아니다.
공개 원천도 품질·PII·오염·언어태그를 재감사해야 한다.
[Tulu 3 SFT mixture 카드](https://huggingface.co/datasets/allenai/tulu-3-sft-mixture)는
하위 소스에 비상업 조건 등 다른 라이선스가 섞였다고 명시하므로
이번 permissive-first 원천에 그대로 넣지 않는다.

**추론**: 작은 모델에서는 지식이 있어도 지시-응답 형식이 없으면 생성 평가가
낮을 수 있다. 반대로 형식만 개선되면 held-out 선택 정확도·신규 사실
문항이 오르지 않을 수 있다. 이를 분리하기 위해 base continuation,
SFT 생성, 자료가 주어진 단기추론, 외부지식 회상을 서로 다른 패널에 둔다.

## 6. 방법 — 선결이 다음 단계를 연다

| 순서 | 단계·독립변수 | 다음 단계 게이트 |
|---|---|---|
| G0 | 기준 checkpoint·tokenizer·model card·동일 decoding과 prompt 패널, 현재 유효 benchmark profile 고정 | raw 답안과 채점·seed가 재현되고 보호 평가자료 누출 0 |
| G1a | P097의 이미 계획된 control/FineWeb2 추가 seed·한국어/영어 별도 score와 공통 원문을 회수한 뒤, corpus/source/tokenizer 차이를 기록 | 진행 중 큐 로그 잠금 해제 전에는 결과 판정 `NOT_RUN`; 특정 과제만 개선이면 전면 dataset 교체 금지 |
| G1b | **P097 추가 유니크 사전학습 원천**의 라이선스·원문 중복·한국어/영어 token quota·source-stratified val·원천 고갈을 독립 inventory로 확인하고, 현 300M draw의 같은 tokenizer 대조 recipe만 신규 설계 | 어떤 새 source도 이전 P097의 승자로 가정하지 않음; 한국어 val이 없는 600M 이상 cache를 quality gate로 사용 금지. 신규 계획/런처는 큐 종료 뒤 별도 preflight |
| G2 | P087에서 1→2→4 draw/pool을 **동일 pool·동일 tokenizer**에서 단계별로; 각 단계 full-val뿐 아니라 KoBEST/KLUE·영어·held-out·생성 패널 | 한국어 val 구성·중복률·망각·지능 판정이 유효할 때만 다음 노출. 4까지 자동 진행 금지 |
| G3 | P090 기존 tokenizer SFT pilot: 공개 v3는 영어 다회전·한영 단일턴 진단용으로만 쓰고, 공식 한국어 멀티턴은 별도 충분한 train/val 원천을 확보한 뒤 연다. assistant-only mask·stop-token 지도 | 오염·license·mask 0 누출, 무지도 레코드 0, 한국어 다회전 val>0과 사람 품질검토, full-val 망각 및 양언어 score 확인 |
| G4 | P075 chat32 신규 tokenizer/새 pretrained checkpoint와 G3 호환 pilot를 **다른 계보**로 비교 | 같은 원문 byte-bpb·능력·체크포인트 크기·배포 상주와 시간으로만 비교; old checkpoint 이식 금지 |
| G5 | G3가 instruction/format을 개선해도 논리·지식이 남을 때만 verified QA, 짧은 rationale, preference 또는 sequence KD를 각각 별도 축으로 | 기존 KD off 기본 유지; 정답 검증과 matched no-teacher SFT 대조 필수 |
| G6 | 품질 후보를 동일 40 MiB 파일 및 runtime peak·tok/s 제약에서 재평가 | 지능 하나의 과락으로 다른 축을 지우지 않고 Pareto와 실패조건을 사용자에게 선택 요청 |

G1b는 **새 유니크 데이터의 효과**이고 G2는 **같은 데이터 재노출 효과**다.
둘을 한 런에서 동시에 바꾸면 어느 쪽이 지능을 개선했는지 알 수 없다.
과거 P087의 4회 draw는 1.2B 노출에 해당하지만, 사용자 이전 지시에
따라 6차 리뷰용 1.2B 실험 `.sh`를 지금 작성하지 않는다. 한국어
600M 이상 노출·평가 문제는 source-stratified val과 언어별 gate가
확인된 뒤에만 별도 결정한다.

현재 진행 중 큐의 로그·런처를 보지 않으므로 G0 이후의 새 런처, 태그
충돌, registry 조회, 데이터 계보 fingerprint 검증은 **큐 종료 후 preflight**다.
정적 문서와 합성 fixture만으로 GPU 단계가 열린 것으로 표시하지 않는다.

### 실제 프롬프트·답안 검사 계약

최소 아래 8개 case를 한국어/영어 대칭으로 준비한다. 각 case는 exact input
messages, 기대 조건, 금지 조건, temperature=0, max-new, stop 조건을 고정한다.

| ID | 질문 예 | 검사하는 능력·채점 |
|---|---|---|
| KO-FACT | 학습에 포함되지 않도록 봉인한 한국어 사실질문 | 정답/불확실성 분리; 사전학습 지식과 SFT 형식의 변화 |
| EN-FACT | 영어 동형 질문 | 언어 간 비퇴행 |
| KO-CONTEXT | 짧은 제공 문단의 인물·수치 추출 | 제공 정보 이용; 외부 지식 문제와 분리 |
| KO-MULTI | 1턴에 임시 코드명 제시, 2턴에 방해 문장, 3턴에 코드명 회상 | 단기 문맥·역할 전환; 답만이 아니라 직전 사용자 지시 유지 |
| EN-MULTI | 영어로 같은 구조 | 멀티턴 언어 전이 |
| KO-FORMAT | 지정한 두 키의 JSON만 출력 | parse 성공, 필수 키, 추가 설명 0 |
| LOGIC | A→B, B→C와 A라는 닫힌 규칙을 주고 C와 근거 요구 | 제공 규칙의 연쇄 추론, 근거 없는 세계지식 혼입 금지 |
| NEGATION | 비슷하지만 부정된 조건과 distractor 제시 | 부정·선택지 판별, 길이/위치 편향 확인 |

원문·출력 전체를 모델/토크나이저 hash·prompt ID·계보·decoding과
함께 JSONL로 남긴다. 자동 exact 판정과 **맹검 2인/불일치 조정**
정성 판정을 분리한다. benchmark에서는 무작위 20~50문항의 prompt,
모든 선택지, raw log-likelihood·gold margin, 생성 응답을 같은 source ID로
추출해 사람이 직접 오답 유형을 분류한다. 여기서 고른 문항을 SFT train에
섞지 않는다. 이 제안은 경로 설계이며 Codex가 모델을 직접 실행했다는 뜻이 아니다.

## 7. 거절하면 못 하는 것

기존 P087, P097, P090 계획과 현재 base-LM 비교는 계속할 수 있다.
다만 “데이터 부족인지 SFT 부족인지”, “loss 이득이 실제 한국어/영어
문답·형식·멀티턴에 전이하는지”, “40 MiB에서 외부 모델과 공정하게
어느 지점이 다른지”를 한 번의 통합된 인과·능력 판으로 답하지 못한다.

## 8. 위험 — 실행하면 무엇이 잘못될 수 있나

| 위험 | 계측에서 드러나는 신호 | 완화 |
|---|---|---|
| 평가 누출 | train/val 또는 benchmark prompt의 n-gram·source ID 중복 | 다운로드 후 원천 fingerprint, tree 단위 분할, 평가 집합 별도 보관; 보호 데이터는 별도 승인 뒤만 접근 |
| SFT의 겉보기만 개선 | format은 좋아지나 held-out/gold margin·새 사실은 불변 | 지식·형식·문맥·논리 결과를 개별 표로 유지; SFT를 지식 증가로 자동 해석하지 않음 |
| 반복에 따른 한국어 퇴행 | 전체 val 감소해도 한국어 split 악화 또는 source exhaustion | P097 balanced pool과 한국어 source-stratified val; 2회 이후 조기 gate, 4회 자동 진행 금지 |
| tokenizer 호환성 사고 | chat32 새 ID를 기존 checkpoint에 넣어 embedding/head 의미가 달라짐 | 별도 path·별도 checkpoint 계보; 기존 32k tokenizer SFT pilot과 새 pretrained chat32를 혼합 금지 |
| 모델·평가 교락 | 서로 다른 prompt/shot/quantization을 같은 점수처럼 비교 | 4차 리뷰 외부 수치는 기술 표만; 동 harness 재측정 뒤에만 직접 차이 계산 |
| 자원·라이선스 | OASST/Aya 원천 품질·PII 문제, 추가 대형 다운로드나 큐 IO 간섭 | pinned Apache source라도 표본 인적 검수; 이번 두 원천만 별도 HF 경로에 확보, 추가 대형 원천·학습은 보류 |

## 9. 대안

| 안 | 내용 | 장점 | 대가 |
|---|---|---|---|
| A | 데이터량·반복만 늘린다 | base LM loss를 빠르게 낮출 수 있음 | 질문응답 형식과 멀티턴 원인 분리가 안 됨 |
| B | 즉시 SFT만 한다 | 형식·대화 개선을 빠르게 볼 수 있음 | 부족한 지식·한국어 데이터·오염을 가린 채 겉보기 점수만 상승 가능 |
| **C** | **G0→P097/P087→호환 SFT→chat32 별도 계보→능력 패널** | 가설을 분리하고 40 MiB Pareto와 실제 답안을 함께 판단 | 선결·문서·측정 비용이 더 큼 |

### 권장안

**C를 권장한다.** 다만 SFT의 저비용 호환 pilot 준비는 G0/G1과 병행하되,
GPU 실행은 데이터 출처·오염·mask와 현재 큐 종료 뒤에만 결정한다.
P097 전면 승자 없음과 P087 단일시드 loss 이득을 모두 존중하며,
4차 리뷰의 “학습토큰이 가장 큰 설명 변수”를 **검증할 가설**로 낮춘다.

### 9.1 사용자 승인 및 실행 경계 (2026-09-23)

사용자는 C안을 승인했고 한국어 SFT·멀티턴 학습과 **지식 부족 / 문답 형식 부족 /
구조·학습방법 문제**를 구분하는 계획·비간섭 선결 구현을 추가로 요청했다.
[P090](../test_plan/P090_SFT-경로.md)은 SFT 데이터·trainer 계약,
[P100](../test_plan/P100_40MiB-지식-형식-구조-원인분리.md)은 같은 부모·평가자를
고정한 원인분리 실험을 소유한다. 기존 P097 seed 큐와 P087 역사적 결과를
새 실험의 성과로 재표기하지 않는다.

Aya Collection 한국어 분할은 약 416만 **단일 prompt-completion 행**을 담지만,
번역·템플릿·원본 주석이 섞인다. 수량은 한국어 자연 대화 품질이나 다회전 수량이
아니다. pinned 원천별 출처·라이선스·중복·평가 누출·사람 표본 감사를 먼저 수행하고,
한국어 멀티턴은 별도 실제 다회전 원천이 없으면 공식 학습·품질 주장을 열지 않는다.
이 절 작성 당시 두 한국어 train parquet 약 974 MB의 취득은 큐 종료 뒤로
보류했다. 이후 HF 다운로드 허용과 다른 공개 원천 확보는 아래 §9.2가 소유한다.

종료 조건은 데이터 카드, SFT 마스크·오염 gate, 동일 부모·동일 평가의 원인분리
실행 결과, 한국어/영어 실제 답안 검토, 40 MiB 배포 지표와 회귀 판정을
모두 회수하는 것이다. 정적 계획만으로 `done/`에 이관하지 않는다.

### 9.2 후속 사용자 결정과 공개 원천 확보 (2026-09-23)

사용자는 **큐 진행 중 HF 다운로드를 허용**했고 결과 로그 읽기는
금지, 실험 런처는 읽기만 허용·수정 금지라고 재확인했다.
이 경계 아래 [원천 감사 보고서](../docs/20260923_한영일-SFT-멀티턴-공개원천-선별과-확보-감사.md)의
한국어 공감형 대화, CarrotAI 단일턴, OASST2 영어·일본어 대화
원본·README 합계 102,943,956 bytes를 별도 `HF/sft_sources`에
pinned revision으로 확보했다. QA·역할복원·평가 오염·SFT 학습은
`NOT_RUN`이라 **학습 채택이 아니다**. OASST2의 엄격한 동언어
best-rank 경로는 영어 다회전 2,377·일본어 24개 후보이며
번역 pilot은 아직 실행하지 않았다.

Aya Collection 한국어 약 974 MB 전량은 다운로드 **권한이 없어서가
아니라** source별 번역·템플릿 품질과 학습 가치 미확정 때문에
여전히 보류한다. 이 선택은 본문 G3의 한국어 다회전 자료 부족을
해소하지 않는다. 신규 원천 수량을 현재 모델의 지능 향상으로
승격하거나 현재 큐 결과를 미리 해석하지 않는다.

### 9.3 사용자 재검토에 따른 우선순위 교정 — 데이터 단독 로드맵이 아니다

**정정**: 본문 G0→G1a→G1b→G2→G3 순서가 마치 데이터 종류와 반복 노출을 다시 검증해야만 SFT·구조·학습법을 시작할 수 있는 것처럼 읽히는 것은 설계상의 편향이다. 실제로 [결과 013](../test_result/013_20260730190000_P029-정성프로브-1차.md)은 위키 문체와 반복 붕괴를 관찰했고, [결과 090 §8](../test_result/090_20260919_P097-세-cache는-완성됐지만-학습은-0step이다.md)은 네 데이터 recipe를 공통 문항에서 대조해 전면 승자가 없음을 확인했다. [결과 073](../test_result/073_20260904_P087-두-번째-epoch은-과적합-없이-0.1155를-준다.md)은 1→2→4 epoch-equivalent의 loss 감소를 이미 확인했다. 이 성과를 새로 발견할 것처럼 적은 것은 잘못된 우선순위다.

| 기존 단계 | 이미 검증된 부분 | 여전히 미검증인 부분 | 이번 처분 |
|---|---|---|---|
| G0 | 과거 P029 5문항×두 온도의 위키 문체·반복 관측 | **현재 후보**의 한영 지식·형식·문맥·멀티턴 원답안, 동일 prompt/decoding의 유형별 판정 | [P029 Stage2W](../run_P029_Stage2W_wiki_eos_panel.sh)로 역사 증상 재관찰, [P100 Stage0W](../run_P100_Stage0W_capability_baseline.sh)로 현재 능력 기준판 수집; 기존 성공 재시험이 아님 |
| G1a | P097 네 recipe 1 seed 공통평가와 두 recipe 추가 seed 학습 | 추가 seed의 **같은 문항** 영어·한국어 점수/byte-bpb | 기존 [P097 Stage4W](../run_P097_Stage4W_ctrl_fw2_seed_panel.sh)를 보존. 그 결과 전에는 corpus 교체 금지 |
| G1b | 기존 네 데이터 묶음이 보편적 승자가 아님 | 새로운 고유 원천의 **같은 tokenizer·같은 평가** 인과효과 | 확장 자체를 최우선으로 삼지 않고 source 감사·저작권·중복을 선결로 유지 |
| G2 | 1→2→4 draw/pool에서 LM loss 개선, 과적합 신호 부재 | 한국어/영어 문답·형식·망각·멀티턴 개선 여부; 600M 이상 한국어 평가 적격성 | 역사 학습을 반복하지 않는다. 먼저 기존 checkpoint의 능력 패널을 비교한다 |

P097의 결론을 **“데이터 유형은 문제가 아니다”**로 확대하지도 않는다. control은 공통 byte-bpb 1.3355로 앞섰고 FineWeb2는 KLUE YNAT 40.9%로 특정 과제 이득이 커, 데이터·토크나이저 묶음의 영향 자체는 관찰됐다. 동시에 두 축이 함께 바뀌고 다른 과제의 전면 우세가 없어 원천 하나의 인과효과나 기본 recipe 교체는 식별되지 않았다. P087의 loss 이득도 곧바로 대화 지능 증가를 뜻하지 않는다.

#### 교정된 다각도 실행 우선순위

1. **능력 병목을 실제 답안으로 분해**: P029의 EOS 이후 표제·URL/반복은 디코딩 결함과 데이터 문체를 분리한다. P100은 현재 모델에서 closed-book 사실, provided-context, JSON 형식, 한영 다회전 임시기억, 논리·부정을 같은 prompt와 base/QA 형식으로 기록한다. 한국어/영어 원문·모델/토크나이저 SHA와 자동 체크 가능·사람 판독을 분리한다. 이 단계는 새 사전학습 없이 실패 형태를 정한다.
2. **형식·대화 능력은 P090 호환 SFT pilot로 직접 겨룬다**: 기존 32k tokenizer에 새 ID를 끼우지 않고 같은 부모의 no-SFT, 형식 전용 SFT, 검수한 지식 QA SFT, 실제 한국어 다회전 SFT를 목표 assistant token·언어·LR/step에 맞춰 비교한다. 공개 v3 한국어 다회전 0건이라는 선결은 Aya Collection의 대량 **단일턴** 확보로 해결되지 않는다. 새 한국어 다회전 원천의 train/val 품질·역할·중복·오염 검사 뒤에만 공식 팔을 연다. SFT는 지식 증가가 아니라 출력 정책 학습일 수 있음을 골드 마진과 제공문맥 대조로 확인한다.
3. **구조와 학습 recipe는 별도 matched 실험축**: [6차 리뷰](../docs/review/202609181843_6차리뷰_초안_기준프리셋-승격후보-4안.md)의 A(d14 CLA2)는 30.8 MiB·19.19 tok/s·full-val 3.5509의 40 MiB 내 후보다. B/C/D와 LR이 달라 구조 우열을 A의 LR1.5e-3 결과로 직접 빼지 않는다. [결과 078 §16](../test_result/078_20260911_P005b-RMS4는-jordan20을-이겼지만-한-형상이다.md)의 A 내부 LR1.5 3-seed 평균 3.5493·평균 이득 약 0.0027은 A 한정 후보이며 전역 LR 기본값이 아니다. 공통 Muon RMS4·matrix WD0·KD off·부모 초기화·WSD를 유지하고, 형상별 LR/WD, parent의 동일 구조 이식, CLA/KV·깊이/폭·재귀, 양자화 후 **실제** 상주/속도를 한 번에 바꾸지 않는다. P092 구조 희소의 dense-mask 경로는 저장·상주·속도 이득을 만들지 못했고, P060B GQA는 품질 실무동급이어도 cache 배포 정합이 미통과라 기본 경로로 승격하지 않는다.
4. **반복/새 고유 데이터는 표적 후속**: P087 loss 이득은 기정사실로 채택하되, 현재 후보의 한국어·영어 실제 능력/망각을 기존 체크포인트에서 먼저 읽는다. 새로운 300M 데이터 재학습은 G1a의 과제별 원인이 필요할 때 같은 tokenizer와 source-stratified val로만 설계한다. 600M 이상 한국어 평가 문제를 건너뛰거나 1.2B 6차리뷰 SH를 만들지 않는다.
5. **40 MiB 배포 Pareto**: packed 파일, 실제 held tensor/RSS, KV 포함 상주, TTFT·decode tok/s, 한영 능력을 같은 후보별로 병기한다. 희소 mask의 이론 packed MiB를 실제 상주로 바꾸지 않는다. 속도나 단일 loss 개선으로 지능 후보를 단독 승격하지 않는다.

**현재 가장 유망한 통합 시제품(검증 대상, 채택 확정 아님)**: 6차 리뷰 A의 d14·CLA2 계보에 Muon RMS4, 행렬 WD0, KD off, 부모 초기화, WSD를 고정하고 A 한정 LR1.5e-3 후보를 비교한다. 같은 체크포인트에서 먼저 P100 원답안 약점과 P097 Stage4 공통평가를 본 뒤, 호환 32k tokenizer의 검수된 형식/한국어 다회전 SFT를 별도 팔로 적용한다. 학습토큰 증량이나 구조 교체를 동시에 하지 않는다. SFT 뒤 실제 상주·KV·속도와 한국어/영어 비퇴행이 40 MiB 조건을 만족하는지 재측정한다. 이 조합의 **SFT 이후 지능 개선·40 MiB 적격은 NOT_RUN**이다.

**세 접근의 선택**: 데이터/반복만 확대(A)은 이미 관찰된 LM-loss 이득을 되풀이할 위험, SFT만 즉시 학습(B)은 형식과 지식의 분리가 안 되는 위험이 있다. **C: 기존 증거 재사용→원답안 병목 분해→같은 부모 SFT와 matched 구조/recipe를 병렬 설계→동예산 Pareto**를 권장한다. 이는 본문 기존 C안의 이름은 유지하되 데이터 중심의 실제 순서를 교정한 것이다. 새 패널·진단 런처는 작성만 했고 실제 모델·GPU·SFT 결과는 `NOT_RUN`이다.

### 9.4 Aya Collection 원천 취득으로 바뀐 것과 바뀌지 않은 것

사용자 후속 지시로 [한국어 train 원본 두 조각](../docs/20260923_한영일-SFT-멀티턴-공개원천-선별과-확보-감사.md)을 별도 HF 경로에 취득하고 출처 감사까지 진행했다. 973,675,125 byte에서 한국어 train 후보 3,605,618행, 21개 출처·29개 세부 그룹, 출처당 20개씩 검토 표본 420개를 기록했다. 사람 주석 `Aya-Dataset`은 이 분할에서 361행이다. 이는 앞선 §9.2의 “전량 미취득” 상태를 후속 갱신한 것이지, 고품질 한국어 SFT 360만 건 확보라는 뜻이 아니다. 원천별 권리·사실성·중복·PII·벤치 오염과 실제 한국어 다회전 train/val은 계속 미검증이다. Aya를 G1b의 새 고유 **사전학습** 데이터나 G3의 한국어 **멀티턴** 해결책으로 자동 승격하지 않는다. 모델·GPU·SFT 결과는 `NOT_RUN`이다.
