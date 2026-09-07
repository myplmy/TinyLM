# TinyLM Stage1 SFT 데이터셋 생성 요청 프롬프트 분석보고 및 개선안 검토요청서

## 문서 상태

| 항목 | 내용 |
|---|---|
| 문서 목적 | 데이터셋 생성 요청 프롬프트의 문제점과 개선안을 상위 총괄 AI 에이전트에게 검토 요청 |
| 현재 상태 | `REVIEW_REQUEST` |
| 작성일 | 2026-09-08 |
| 적용 대상 | 100M급 한국어 TinyLM Stage1 SFT 데이터셋 설계 |
| 실행 권한 | 없음 |
| 데이터 생성 | 시작하지 않음 |
| 모델 학습·평가 | 시작하지 않음 |
| 기존 데이터 수정 | 금지 |

> **중요 실행 게이트**  
> 이 문서는 설계 검토를 요청하기 위한 문서다. 본 문서에 포함된 개선 프롬프트도 현재는 검토용 초안이며, 총괄 AI의 타당성 검토와 사용자의 별도 명시적 승인 전에는 데이터 생성, 파일 작성, 기존 파일 수정, 학습, 평가를 수행해서는 안 된다.

---

## 1. 검토 요청 요약

기존 제안은 고밀도 서술문 코퍼스 34,000건과 저밀도 서술문 코퍼스 900건을 재료로 6,000건의 SFT 데이터셋을 만드는 방안이었다. 사용자는 고밀도 코퍼스와 그로부터 파생된 SFT를 모두 학습할 경우 같은 지식을 두 번 학습하여 과적합하거나 일부 개념을 과도하게 가중할 위험이 있는지 검토를 요청했다.

검토 결과는 다음과 같다.

1. 같은 source에서 SFT를 만들면 **의미 수준의 재노출은 확실히 발생**한다.
2. 고밀도 서술문 학습과 SFT는 조건과 loss 대상이 다르므로 **동일한 학습목표의 완전 중복은 아니다**.
3. 의미 재노출은 이미 아는 지식을 질문-응답 행동으로 연결하는 데 도움이 될 수 있다.
4. 그러나 기존 프롬프트에는 source별 재사용 상한, 원문과 SFT 사이의 복사·유사도 검사, 실제 SFT 직렬화 필드, 학습 노출량 기록이 없어 특정 사실의 과가중과 오답 학습 위험을 통제할 수 없다.
5. 신규 지식 기반 SFT 6,000건과 고밀도 지식 기반 bridge SFT 6,000건을 별도 조건으로 비교하는 개선안은 타당성이 있다.
6. 두 SFT 조건만 비교하면 절대적인 SFT 효과를 알 수 없으므로, 고밀도 학습 완료 후 SFT를 하지 않은 공통 체크포인트를 무처치 기준선으로 유지해야 한다.

본 문서는 다음 개선안을 총괄 AI에게 검토 요청한다.

> **고밀도 학습 완료 공통 체크포인트를 기준으로, 고밀도와 분리된 신규 SFT 6,000건을 능동 대조군으로 사용하고, 고밀도 train source에서 1:1로 파생한 bridge SFT 6,000건을 재노출 실험군으로 사용한다. 두 데이터셋은 6,000개의 matched pair로 설계하고, 무-SFT 공통 체크포인트를 절대 기준선으로 함께 평가한다.**

---

## 2. 배경

### 2.1 모델 상태

- 대상 모델은 약 100M parameter 규모의 한국어 base LM이다.
- 표준 사전학습은 완료된 것으로 제시되었다.
- 지시-응답 SFT는 아직 수행되지 않았다.
- 현재 모델은 4지선다 후보의 우도를 비교하여 답을 고르는 능력은 가질 수 있지만, 사용자 질문에 직접 답하는 출력 형식을 별도로 학습하지 않았다.
- 최소 규모의 SFT로 지식 습득 자체보다 **질문을 해석하고 적절한 답변 형식으로 응답하는 행동**을 학습시키려는 것이 원래 목적이다.

### 2.2 기존 자산

#### A. Stage1 고밀도 서술문 train 코퍼스 34,000건

현재 설계서 기준 train 구성은 다음과 같다.

| 영역 | 레코드 수 |
|---|---:|
| Identity | 6,100 |
| Attribute | 4,650 |
| Function | 4,050 |
| Boundary | 4,650 |
| Part-whole, State-change, Spatial, Comparison, Context, Type-uncertainty 합계 | 14,550 |
| 합계 | 34,000 |

고밀도 파일은 `text`를 모델 입력으로 사용하고 annotation 필드는 학습 입력에서 제외하는 것이 현행 권고다. 기존 고밀도 정본 파일은 수정 대상이 아니다.

관련 정본:

- `stage1_highdensity_dataset/TinyLM_Stage1_Stage7_Dataset_Design_Spec.md`
- `stage1_highdensity_dataset/TinyLM_Stage1_Stage7_Dataset_Corpus_Generation_Guide.md`

#### B. 저밀도 Stage1 train v2 900건

- 파일: `stage1_dataset/train_v2/stage1_train_900_v2.json`
- 원문 900건
- paraphrase 1,800건
- near-negative 2,700건
- 현재 near-negative 고유 문장 2,680건
- 전역 중복 추가분 20건
- 관계 분포가 균일하지 않으며 `boundary` 715건, `is_a` 4건이고 `process`, `subclass_of` near-negative는 없다.

따라서 near-negative를 새 SFT의 `rejected`로 기계적으로 재사용하면 기존 중복과 관계 불균형을 그대로 옮길 수 있다.

#### C. 평가 전용 held-out v2.7 300문항

- 파일: `stage1_dataset/held-out_v2.7/stage1_heldout_benchmark_v2.7_300.json`
- 전체 300문항
- `unseen_concept`: 113
- `seen_concept_control`: 37
- `novel_relation`: 90
- `boundary`: 60
- 4지선다 likelihood 평가용이며 학습·validation·checkpoint 선택·튜닝에 사용해서는 안 된다.

### 2.3 아직 확인되지 않은 전제

표준 사전학습 완료 사실만으로 고밀도 34,000건이 실제로 모델에 공급되었다고 단정할 수는 없다. 중복학습 실험이 성립하려면 다음 provenance가 별도로 확인되어야 한다.

- 고밀도 34,000건을 실제로 학습했는가
- 어떤 파일 version과 SHA-256을 사용했는가
- 고밀도 text가 몇 epoch 또는 몇 sample exposure로 공급되었는가
- annotation이 아니라 `text`만 공급되었는가
- 그 학습이 완료된 정확한 checkpoint가 무엇인가

이 증거가 없으면 개선안의 bridge 조건은 “재노출 실험군”이 아니라 단순한 “고밀도 source 기반 SFT군”으로만 해석해야 한다.

---

## 3. 본 검토의 목적과 비목적

### 3.1 목적

1. 기존 SFT 생성 프롬프트가 중복학습, 평가 누출, 오답 직렬화, 분포 편중을 충분히 통제하는지 판단한다.
2. 신규 SFT와 고밀도 bridge SFT의 공정한 비교 실험 구조를 제안한다.
3. 데이터 생성 AI 에이전트가 따라야 할 provenance, pair matching, audit, 실행 게이트를 명문화한다.
4. 총괄 AI가 `승인`, `수정 후 승인`, `기각` 중 하나를 판단할 수 있도록 결정 사항을 분리한다.

### 3.2 비목적

본 문서는 다음을 수행하거나 입증하지 않는다.

- SFT 데이터 12,000건의 실제 생성
- 고밀도 또는 저밀도 정본 수정
- GPU 학습 또는 checkpoint 생성
- held-out 평가 실행
- 특정 SFT 방식의 성능 우월성 주장
- 일반 지능 향상 주장
- 6,000건이라는 규모가 최적이라는 주장

---

## 4. 기존안

### 4.1 기존안의 산출물

기존 제안은 다음 단일 파일을 만드는 것이었다.

```text
stage1_sft_train_v1.jsonl
```

총 6,000건이며 task 비율은 다음과 같다.

| task | 비율 | 건수 |
|---|---:|---:|
| identity | 30% | 1,800 |
| attribute | 20% | 1,200 |
| function | 15% | 900 |
| relation | 15% | 900 |
| boundary | 10% | 600 |
| counterexample | 10% | 600 |
| 합계 | 100% | 6,000 |

### 4.2 기존 레코드 스키마

```json
{
  "id": "S1-SFT-00001",
  "source_id": "<source id 또는 null>",
  "task": "identity | attribute | function | relation | boundary | counterexample",
  "instruction": "<질문 또는 명령형 한 문장>",
  "input": "",
  "output": "<1~3문장 정답과 근거>",
  "concepts": ["<등장 개념>"],
  "relations": ["<사용 관계 라벨>"],
  "rejected": "<틀린 답>",
  "rejected_reason": "<틀린 이유>"
}
```

### 4.3 기존안의 주요 보호 규칙

- held-out 300문항의 주어 개념과 관계 조합을 만들지 않는다.
- `unseen_concept` 113문항의 주어 개념을 사용하지 않는다.
- `seen_concept_control`의 prompt와 answer를 복사·변형하지 않는다.
- output이 held-out candidates의 표면형과 겹치지 않게 한다.
- instruction에 정답이 노출되지 않게 한다.
- rejected는 애매하지 않은 사실상의 오답이어야 한다.
- 하나의 instruction에 복수 정답이 성립하지 않게 한다.
- task별 output 길이를 고르게 한다.
- 자연어 문장은 한국어로 작성한다.

### 4.4 기존 manifest 요구

- 총 레코드 수
- task별 건수
- 사용 source ID 목록
- held-out과 겹친 개념 목록
- output 평균·최소·최대 길이
- 규칙별 위반 건수와 위반 목록

---

## 5. 기존안 분석 결과

### 5.1 중복학습의 종류를 구분해야 한다

| 구분 | 의미 | 기존안 판정 |
|---|---|---|
| 표면 중복 | 동일하거나 거의 동일한 문장 재사용 | 원문↔SFT 검사 부재로 통제 불충분 |
| 의미 중복 | 같은 개념·사실·관계를 다른 문장으로 재학습 | source 기반 생성 시 확실히 발생 |
| 학습목표 중복 | 동일 조건과 동일 loss target을 반복 | 고밀도 CLM과 assistant-only SFT라면 동일하지 않음 |
| 노출 과가중 | 일부 source가 다른 source보다 훨씬 많이 gradient에 기여 | source별 상한과 token budget 부재로 측정 불가 |
| 평가 누출 | held-out의 답이나 판정축이 학습에 들어감 | 검사 범위가 일부 필드와 표면형에 한정됨 |

고밀도 34,000건 중 서로 다른 source 6,000건에서 하나씩 SFT를 만들 경우 레코드 기준 최대 17.65%가 두 형식으로 재노출된다. 그러나 실제 영향은 다음에 좌우된다.

```text
source의 유효 노출량
= 고밀도 단계의 source 노출 횟수
+ source별 SFT 예제 수 × SFT epoch × assistant target token 가중치
```

따라서 행 수만으로 중복 위험을 판정할 수 없다.

### 5.2 의미 재노출은 반드시 해로운 것은 아니다

고밀도 서술문은 개념과 경계 지식을 자연어 packet으로 학습한다. SFT는 질문이 주어졌을 때 그 지식을 답변 형식으로 인출하도록 학습한다. 두 단계의 조건과 목표가 다르므로, 이미 아는 지식을 질문-응답 행동으로 연결하는 bridge는 의도적인 curriculum이 될 수 있다.

특히 이번 목적이 신규 사실 습득보다 “답하는 형태”의 학습이라면, 이미 아는 지식을 사용하면 지식 습득 난이도와 instruction-following 난이도를 분리하는 장점이 있다.

반대로 동일 source에서 여러 질문을 만들거나 SFT를 여러 epoch 반복하면 100M급 모델에서 다음 위험이 커질 수 있다.

- 일부 개념과 관계에 대한 암기
- 짧은 정답 형식으로의 과도한 수렴
- 고밀도 packet의 복합 관계보다 단일 문답 연결을 우선하는 편향
- source-seen 성능만 상승하고 source-disjoint 일반화가 정체되는 현상
- 기존 언어모델 능력 또는 서술 능력의 망각

### 5.3 기존 프롬프트의 핵심 결함

#### 결함 A — source 재사용 상한이 없다

`source_id`가 중복되어도 금지되지 않으며 `null`도 무제한 허용된다. 따라서 한 source에서 여러 task를 생성하거나 저밀도 900건에 과도하게 집중할 수 있다.

#### 결함 B — 원문과 SFT 사이의 복사 검사가 없다

기존 규칙은 instruction↔output 및 output↔held-out candidate만 다룬다. `source.text`의 문장을 output으로 축약·복사하는 행위를 직접 금지하지 않는다.

#### 결함 C — `rejected`의 실제 학습 경계가 없다

JSON에 `rejected`가 있다는 사실만으로 오답 학습이 되는 것은 아니다. 학습 loader가 어떤 필드를 직렬화하고 어느 token에 loss를 적용하는지가 결정한다.

- loader가 `rejected`를 무시하면 SFT에는 사용되지 않는다.
- loader가 JSON 전체를 직렬화하면 틀린 답과 설명도 next-token target이 될 수 있다.
- pairwise 또는 preference loss로 사용하면 순수 SFT와 다른 실험이 된다.

따라서 positive SFT와 rejected sidecar를 분리해야 한다.

#### 결함 D — near-negative 재사용 규칙이 약하다

현재 near-negative에는 전역 중복과 relation 불균형이 있다. 또한 기존 서술형 오답이 새 instruction에 대한 직접 응답으로 자연스럽고 완전히 틀린지 별도로 검증해야 한다. “재활용할 수 있으면 재활용”만으로는 충분하지 않다.

#### 결함 E — held-out 격리 범위가 불완전하다

기존안의 candidate 비교는 output에만 명시되어 있다. 다음 필드도 검사해야 한다.

- instruction
- input
- output
- 별도 보관되는 rejected
- rejected_reason
- 신규 source ledger의 text
- concepts와 aliases

또한 “표면형이 겹치지 않는다”, “어떤 형태로도 쓰지 않는다”, “서로 다른 사람이 쓴 것처럼”은 자동 검증 가능한 정의가 아니다.

#### 결함 F — source 자산끼리의 중복 상태가 미확정이다

현행 고밀도 감사 문서에는 다른 밀도의 데이터가 생성·중복 비교·감사 기준에서 제외되었다고 명시되어 있다. 따라서 고밀도 34,000건과 저밀도 900건이 의미적으로 완전히 분리되어 있다고 가정할 수 없다.

#### 결함 G — 길이 규칙과 manifest가 일치하지 않는다

- output을 1~3문장으로 허용하면서 근거를 한 문장 덧붙이라고 하여 1문장 허용 여부가 모호하다.
- task별 길이를 맞추라고 했지만 manifest는 전체 평균·최소·최대만 요구한다.
- 평균만 맞아도 일부 task의 극단값이나 분포 차이를 놓칠 수 있다.

#### 결함 H — relation 정본이 불명확하다

고밀도 일부 legacy 파일에는 자유 relation과 `relations_controlled`가 함께 존재한다. 새 SFT의 `relations`가 반드시 13개 통제어휘만 사용한다는 점을 명시해야 한다.

---

## 6. 기존안과 개선안 도출 과정에서 사용자와 논의한 사항

| 순서 | 사용자 요청 또는 결정 | 검토 결과 및 반영 |
|---:|---|---|
| 1 | 고밀도 서술문과 그로부터 만든 SFT를 둘 다 학습하면 같은 내용을 두 번 학습하는지 검토 요청 | 의미 수준 재노출은 발생하지만 고밀도 CLM과 SFT의 학습목표는 다르다고 구분 |
| 2 | 중복 위험이 있다면 개선안 3개와 권장안 요청 | 완전 분리, 제한적 bridge 재사용, 신규·bridge 혼합/비교안을 제시 |
| 3 | 신규 SFT 6,000건과 고밀도 지식→응답 bridge SFT 6,000건을 실험군·대조군으로 사용하는 방안 제안 | 비교 가치가 높다고 판단하되, 신규군은 능동 대조군이고 별도의 무-SFT 기준선이 필요하다고 보완 |
| 4 | 두 조건의 차이를 중복학습 효과로 해석하고자 함 | 두 데이터셋을 task·relation·길이·난이도·사전 지식 수준까지 matched pair로 구성하도록 개선 |
| 5 | 실제 수행은 금지하고 설계만 검토하도록 지시 | 현재까지 데이터 생성·학습·평가를 수행하지 않았으며 본 문서에도 실행 게이트를 명시 |

논의에서 정리된 핵심은 다음과 같다.

1. 신규 SFT군은 “아무 새 질문”이 아니라 고밀도 bridge군과 비교 가능한 구조를 가져야 한다.
2. 신규군이 모델에게 전혀 모르는 사실만 포함하면 source novelty와 지식 난이도가 혼동된다.
3. 따라서 신규 SFT에도 감사용 신규 source packet을 두되, 그 packet 자체는 서술문 학습에 사용하지 않는다.
4. bridge source는 고밀도 train에서 6,000개를 고유하게 선택하고 source당 SFT 한 건만 만든다.
5. 두 SFT군은 동일한 공통 체크포인트에서 독립적으로 분기한다.
6. 기존 held-out 300은 최종 평가 전용으로 계속 보호한다.
7. 자유응답 형식 학습은 기존 4지선다만으로 충분히 측정할 수 없으므로 별도의 완전 격리 자유응답 평가가 필요하다.

---

## 7. 개선안

### 7.1 핵심 연구 질문

> **동일한 고밀도 학습 완료 체크포인트에 같은 규모와 난이도의 SFT를 추가할 때, 이미 고밀도 단계에서 본 지식을 질문-응답 형식으로 다시 제시하는 bridge SFT가 고밀도와 분리된 신규 SFT보다 instruction-following 일반화에 유리한가, 아니면 source-seen 암기와 편중을 증가시키는가?**

### 7.2 권장 비교 구조

| 조건 | 시작점 | 추가 데이터 | 실험 역할 |
|---|---|---|---|
| `B0_HD_ONLY` | 고밀도 학습 완료 checkpoint H | 없음 | 무처치 절대 기준선 |
| `C1_FRESH_SFT_6000` | checkpoint H | 신규·고밀도 비중복 SFT 6,000건 | 능동 대조군 |
| `T1_BRIDGE_SFT_6000` | checkpoint H | 고밀도 train 유래 bridge SFT 6,000건 | 의미 재노출 실험군 |
| `M1_MIXED_SFT_6000`, 선택 | checkpoint H | 신규 3,000 + bridge 3,000 | 혼합 효과 탐색군 |

`M1`은 본 개선안의 필수 조건이 아니다. 총괄 AI가 비용 대비 필요성을 인정할 때만 후속 실험 후보로 남긴다.

### 7.3 공통 시작점의 조건

세 필수 조건 B0, C1, T1은 동일한 checkpoint H에서 시작해야 한다.

```text
동일 base checkpoint
        ↓
동일 고밀도 train 34,000 학습
        ↓
동일 checkpoint H
        ├── B0: 추가 SFT 없음
        ├── C1: Fresh SFT 6,000
        └── T1: Bridge SFT 6,000
```

다음이 동일해야 한다.

- checkpoint bytes 또는 동일 checkpoint hash
- tokenizer
- chat template
- optimizer 초기 상태 정책
- batch 및 gradient accumulation
- learning-rate schedule
- update 수
- assistant target token budget
- seed 세트
- validation 및 checkpoint selection 규칙

이 조건은 향후 학습 실행 설계에 관한 것이며 데이터 생성 완료만으로 충족되었다고 표시해서는 안 된다.

### 7.4 Fresh SFT 6,000건

#### 정의

고밀도 34,000건, 저밀도 900건, held-out 300건, bridge SFT와 분리된 신규 source에서 만든 SFT다.

#### 필수 source ledger

신규 SFT를 곧바로 질문-답 형식으로만 작성하면 bridge군의 풍부한 source packet과 품질 조건이 달라진다. 따라서 다음 비학습 감사 source를 먼저 둔다.

```text
stage1_sft_fresh_source_6000_v1.jsonl
```

이 source ledger는 다음 목적으로만 사용한다.

- 사실성과 단일 정답 검증
- concept·relation provenance
- bridge source와 난이도 matching
- SFT 변환 근거 확인

이 source ledger의 text는 checkpoint H 이전이나 C1 SFT 단계의 서술문 학습 데이터로 사용하지 않는다.

#### ID와 provenance

- Fresh source ID: `S1-SFTN-SRC-00001`~`S1-SFTN-SRC-06000`
- Fresh SFT ID: `S1-SFTN-00001`~`S1-SFTN-06000`
- `source_id`는 null이 아니어야 한다.
- `source_exposure_status`는 `not_in_highdensity_training_corpus`다.
- “fresh”는 Stage1 자산과의 corpus-disjoint를 의미하며 표준 사전학습 전체에서 model-unseen임을 의미하지 않는다.

### 7.5 Bridge SFT 6,000건

#### 정의

고밀도 train 34,000건 중 서로 다른 source 6,000건을 선택하여 각 source에서 SFT 한 건을 만드는 지식→응답 연결 데이터다.

#### source 제한

- 고밀도 **train**만 사용한다.
- 고밀도 validation은 사용하지 않는다.
- held-out은 source, 예시, 교정 기준으로 사용하지 않는다.
- source ID는 6,000건 모두 고유해야 한다.
- 하나의 source에서 여러 task를 만들지 않는다.
- source의 `text`와 기존 필드는 변경하지 않는다.
- 신규 SFT `relations`에는 source의 자유 relation이 아니라 13개 통제 relation만 기록한다.
- `source_exposure_status`는 provenance가 확인된 경우에만 `confirmed_exposed`로 확정한다. 확인 전에는 `unverified`로 둔다.

#### ID

- Bridge SFT ID: `S1-SFTB-00001`~`S1-SFTB-06000`
- source ID는 기존 고밀도 원본 ID를 그대로 참조한다.

### 7.6 6,000개 matched pair

각 Fresh와 Bridge 레코드는 같은 `pair_id`로 연결한다.

```text
S1-SFTP-00001
├── S1-SFTN-00001
└── S1-SFTB-00001
```

각 pair는 다음을 맞춘다.

- task
- 핵심 controlled relation 또는 relation-set 크기
- 질문의 극성
- 직접 답변형·설명형 구분
- 요구 추론 hop 수
- instruction 문장 수
- output 문장 수
- output 어절 수 범위
- 근거의 구체성
- 개념의 추상도
- 도메인 난이도
- 정답과 rejected의 답변 형식

권장 길이 matching 기준은 다음과 같다.

- pair 내 output 문장 수 동일
- pair 내 output 어절 수 비율 0.8~1.2
- 두 군의 task별 평균 output 어절 수 차이 5% 이내
- 두 군의 task별 중앙값과 분위수도 함께 보고

이 수치는 검토용 제안이며 총괄 AI가 언어 자연성을 해친다고 판단하면 수정할 수 있다. 단, 수정 시 두 군의 effective target token budget 동등성을 유지하는 대체 기준을 제시해야 한다.

### 7.7 task 구성

두 데이터셋 각각 정확히 다음 구성을 갖는다.

| task | 각 데이터셋 건수 |
|---|---:|
| identity | 1,800 |
| attribute | 1,200 |
| function | 900 |
| relation | 900 |
| boundary | 600 |
| counterexample | 600 |
| 합계 | 6,000 |

`pair_id`로 연결된 두 레코드의 task는 반드시 같아야 한다.

`relation`과 `counterexample`은 broad task이므로 내부적으로 controlled relation과 오류 유형별 층화 분포를 별도 manifest에 기록한다. task 개수만 맞추고 relation 분포가 달라지는 것을 허용하지 않는다.

### 7.8 SFT와 rejected의 분리

#### 실제 SFT train 파일

SFT train JSONL에는 정답 학습에 필요한 필드만 둔다.

```json
{
  "id": "S1-SFTN-00001",
  "pair_id": "S1-SFTP-00001",
  "provenance_class": "fresh_disjoint",
  "source_id": "S1-SFTN-SRC-00001",
  "source_dataset": "stage1_sft_fresh_source_6000_v1",
  "source_exposure_status": "not_in_highdensity_training_corpus",
  "task": "identity",
  "instruction": "...",
  "input": "",
  "output": "...",
  "concepts": ["..."],
  "relations": ["is_a"]
}
```

Bridge는 `provenance_class: "highdensity_bridge"`를 사용하고 기존 고밀도 source ID를 참조한다.

SFT loader의 직렬화 허용 목록은 `instruction`, `input`, `output`뿐이다. ID와 provenance, concepts, relations는 감사 metadata이며 모델 입력 문자열에 넣지 않는다. loss는 assistant `output` token에만 적용한다.

#### rejected sidecar

오답은 다음 별도 파일로 둔다.

```text
stage1_sft_fresh_rejected_sidecar_v1.jsonl
stage1_sft_bridge_rejected_sidecar_v1.jsonl
```

```json
{
  "sft_id": "S1-SFTN-00001",
  "pair_id": "S1-SFTP-00001",
  "chosen": "...",
  "rejected": "...",
  "rejected_reason": "...",
  "violated_relation": "classification",
  "source_negative_id": null
}
```

규칙:

- SFT 학습 loader는 sidecar를 읽지 않는다.
- 실제 SFT loss는 assistant `output` token에만 적용한다.
- near-negative 재사용은 direct-answer 적합성, 완전한 거짓, 전역 유일성, relation quota를 모두 통과한 경우에만 허용한다.
- rejected를 preference 학습에 사용하는 것은 별도의 승인과 별도 실험으로 분리한다.

### 7.9 문장 작성 규칙 개선

#### instruction

- 한국어 한 문장으로 작성한다.
- 물음표로 끝나는 질문 또는 명확한 명령형이어야 한다.
- 질문 대상 concept의 언급은 허용한다.
- 정답의 핵심 predicate, object, 판정 결론을 instruction에 포함하지 않는다.
- “서로 다른 사람이 쓴 것처럼”이라는 주관적 기준 대신 answer-bearing span 누출 여부를 검사한다.

#### output

- 2~3문장으로 작성한다.
- 첫 문장에 직접 답한다.
- 나머지 한 문장 이상에 source로 검증 가능한 근거를 제시한다.
- source가 말하지 않은 사실을 추가하지 않는다.
- 고밀도 source의 완전한 문장을 복사하지 않는다.
- source와 정규화 동일 문장 0건이어야 한다.
- source에서 그대로 가져온 연속 5어절 이상 구간은 0건이어야 한다.
- task마다 기계적인 고정 어미나 동일한 결론 문구를 반복하지 않는다.

#### 단일 정답성

- 먼저 instruction의 target slot과 허용 답변 granularity를 정의한다.
- 같은 수준에서 두 개 이상의 답이 성립하는 질문은 폐기하거나 수정한다.
- 상위 범주와 하위 범주가 동시에 가능한 identity 질문은 요구 수준을 명시한다.
- 열린 세계에서 거짓이 증명되지 않는 rejected는 사용하지 않는다.

### 7.10 controlled relation

새 SFT의 `relations`에는 다음 13개만 허용한다.

```text
is_a
subclass_of
part_of
classification
boundary
contrast
comparison
function
role
process
state
attribute
other
```

- 배열 안 중복은 허용하지 않는다.
- source의 실제 의미와 일치하는 relation만 기록한다.
- Fresh와 Bridge 두 군의 relation count와 relation-set 분포를 가능한 한 pair 또는 stratum 단위로 맞춘다.
- Identity legacy source의 원본 자유 relation을 그대로 신규 SFT에 복사하지 않는다.

### 7.11 held-out 격리 개선

기존 held-out v2.7 300문항은 학습 source가 아니며 생성 아이디어 source도 아니다. 데이터 생성 과정에서 허용되는 사용은 금지 집합을 구축하고 최종 격리 감사에 사용하는 것뿐이다.

다음 전체를 검사한다.

- Fresh source text
- Fresh와 Bridge instruction
- input
- output
- concepts
- rejected sidecar의 chosen, rejected, rejected_reason

최소 검사 단위:

1. `unseen_concept` 113문항의 주어 concept 및 승인된 alias의 모든 자연어 필드 등장 수
2. 전체 300문항의 주어 concept＋required relation 조합
3. required와 forbidden relation-set
4. prompt, answer, candidates와의 정규화 exact 일치
5. 반복 5어절
6. 문자 n-gram 또는 동등한 fuzzy similarity 상위 쌍
7. 의미가 사실상 같은 paraphrase에 대한 사람 검토

`seen_concept_control` 37문항의 concept 사용은 기존 benchmark 목적과 충돌하지 않는 범위에서만 허용하되, 해당 prompt·answer·candidate의 문장 또는 판정축을 복사·변형하지 않는다.

위반이 1건이라도 있으면 `PASS`로 표시하지 않는다.

### 7.12 source 간 중복과 유사도 감사

Fresh source는 다음 자산과 비교한다.

- 고밀도 train 34,000
- 고밀도 validation
- 저밀도 train v2 900 및 paraphrases, near-negatives
- held-out v2.7 300의 모든 자연어 필드
- 같은 Fresh source 집합 내부

Bridge SFT는 다음을 검사한다.

- source ID 중복 0
- 원문 완전 문장 복사 0
- 연속 5어절 복사 0
- pair 간 instruction exact 중복 0
- pair 간 output exact 중복 0
- concept＋relation-set 중복 현황
- fuzzy similarity 상위 쌍 사람 검토 결과

의미가 같은 source를 bridge로 변환하는 것이 목적이므로 source와 SFT의 semantic equivalence 자체를 위반으로 세어서는 안 된다. 대신 표면 복사와 source별 노출 수를 통제하고 기록한다.

### 7.13 사전 지식 난이도 matching 게이트

Fresh군이 bridge군보다 모델에게 훨씬 낯선 사실이면 비교가 왜곡된다. 따라서 데이터 정적 감사가 끝난 뒤 실제 학습 전에 checkpoint H로 다음을 확인하는 단계를 별도 둔다.

- 정답과 rejected 사이의 base likelihood margin
- 질문 없이 source 사실을 완성하는 base likelihood 또는 동등한 지식 진단
- task·relation별 사전 정답 가능성

Fresh와 Bridge의 분포가 현저히 다르면 pair를 재조정하거나 결과 해석에서 “기존 지식 친숙도” 교란을 명시한다.

이 단계는 모델 실행이므로 데이터 생성 AI가 수행하지 않는다. 사용자 또는 별도 승인된 평가 주체가 수행할 때까지 상태를 `B0_KNOWLEDGE_MATCH_PENDING`으로 유지한다.

### 7.14 산출물 상태 경계

다음 상태를 혼동하지 않는다.

```text
DRAFT_GENERATED
→ STATIC_AUDIT_PASS
→ HUMAN_SEMANTIC_REVIEW_PASS
→ B0_KNOWLEDGE_MATCH_PENDING/PASS
→ EXPERIMENT_READY
→ TRAINING_NOT_STARTED
→ USER_RUN_TRAINING
→ EVALUATION_NOT_STARTED/COMPLETE
```

- 데이터 파일을 작성했다고 `STATIC_AUDIT_PASS`가 되는 것은 아니다.
- 정적 감사 통과가 의미 검토 통과를 뜻하지 않는다.
- 데이터셋 완료가 모델 학습 완료를 뜻하지 않는다.
- 평가 완료 전에는 개선안의 우월성을 주장하지 않는다.

---

## 8. 개선안이 기존안보다 나은 점과 근거

| 개선점 | 기존안 | 개선안 | 더 나은 이유 |
|---|---|---|---|
| 인과 해석 | 단일 SFT 6,000건 | B0, Fresh 6,000, Bridge 6,000 비교 | SFT 자체 효과와 의미 재노출 효과를 분리할 수 있음 |
| source 재사용 | 상한 없음 | source당 SFT 1건, 6,000 source 고유 | 일부 사실의 과가중을 제한 |
| 신규군 품질 | 직접 QA 생성 가능 | 비학습 Fresh source ledger에서 동일 절차로 변환 | bridge군과 provenance·검증 구조를 맞춤 |
| 난이도 통제 | task 비율만 고정 | 6,000 matched pair | 내용 난이도와 format 차이를 줄임 |
| 학습량 통제 | 행 수만 6,000 | assistant target token·update 수까지 동일 | 실제 gradient 노출을 더 정확히 맞춤 |
| 오답 처리 | SFT 레코드 안에 rejected 포함 | 별도 sidecar, SFT loader에서 제외 | 틀린 답의 next-token 학습 위험 제거 |
| 평가 격리 | 일부 조합과 output 표면형 | 모든 자연어 필드·alias·n-gram·fuzzy·사람 검토 | 간접 누출과 변형 누출을 더 폭넓게 탐지 |
| relation 통제 | relations 정의 모호 | 13개 controlled relation으로 한정 | legacy 자유 label 혼입과 군간 분포 차이 방지 |
| 결과 해석 | 단일 개선 여부 중심 | source-seen·source-disjoint·일반 LM 능력 분리 | 암기, 전이, 망각을 구분 가능 |
| 상태 보고 | 생성과 검증 경계가 약함 | 생성·정적 감사·사람 검토·모델 진단·학습·평가 분리 | 미실행 단계를 완료로 오인하는 것을 방지 |

이 개선안의 핵심 근거는 “의미 재노출을 모두 제거해야 한다”가 아니다. 같은 지식의 두 번째 노출이 지식→행동 연결에 유익할 수 있다는 가설과, 그것이 source 암기에 불과할 수 있다는 반대 가설을 **동일 조건에서 구분 가능하게 만든다**는 데 있다.

---

## 9. 평가 및 결과 해석 권고

### 9.1 최소 평가 축

1. 기존 held-out v2.7 300 likelihood 평가
2. Fresh·Bridge source와 모두 격리된 자유응답 instruction-following 평가
3. source-seen 진단과 source-disjoint 진단의 성능 차이
4. 일반 LM validation loss 또는 기존 사전학습 능력 보존 지표
5. 출력 형식 준수율
6. 사실 정확성·단일 정답성·근거 충실성
7. train source와의 복사율 또는 memorization 진단

기존 held-out 300은 4지선다 likelihood 평가이므로 자유응답 형식 학습을 단독으로 판정하기에 충분하지 않다. 별도 자유응답 평가는 두 SFT 데이터셋과 완전히 격리되고 학습 전에 동결되어야 한다.

### 9.2 반복과 보고

- 동일 seed 세트를 양쪽 군에 적용한다.
- 가능하면 최소 3개 seed의 평균과 변동폭을 보고한다.
- 단일 seed 결과를 최종 결론으로 사용하지 않는다.
- checkpoint selection은 공통 validation과 공통 규칙으로 수행한다.
- held-out 결과로 학습률, epoch, 데이터 수정 여부를 결정하지 않는다.

### 9.3 결과 해석표

| 관측 결과 | 우선 해석 |
|---|---|
| C1과 T1이 모두 B0보다 높고 C1≈T1 | 의미 재노출의 뚜렷한 해악 또는 추가 이득이 관측되지 않음 |
| T1이 source-disjoint 자유응답에서도 C1보다 높음 | 익숙한 지식을 이용한 bridge가 일반적 instruction-following 전이에 유리할 가능성 |
| T1이 source-seen에서만 높고 C1이 source-disjoint에서 높음 | bridge의 암기·과특화 가능성 |
| C1이 대부분의 격리 평가에서 T1보다 높음 | 의미 재노출 또는 source 편중이 일반화를 방해했을 가능성 |
| 두 SFT군 모두 일반 LM 지표가 B0보다 크게 하락 | source 종류보다 SFT schedule 또는 망각 문제가 우선 |
| T1만 기존 held-out 300에서 비정상적으로 크게 상승 | benchmark 판정축 재가중 또는 간접 누출 재감사 필요 |

유한한 한 번의 실험으로 “모든 중복학습은 좋다/나쁘다”라고 일반화해서는 안 된다.

---

## 10. 총괄 AI에게 요청하는 결정 사항

다음 항목별로 `승인`, `수정 후 승인`, `기각`과 근거를 요청한다.

1. 무-SFT B0, Fresh C1, Bridge T1의 3조건 구조가 연구 질문에 적합한가
2. Fresh 6,000건을 직접 QA로만 만들지 않고 비학습 source ledger에서 파생하는 것이 타당한가
3. Fresh와 Bridge를 6,000 matched pair로 구성하는 것이 비용 대비 필요한가
4. bridge source당 SFT 한 건과 source ID 전역 고유 제한이 적절한가
5. positive SFT와 rejected sidecar를 분리하는 것이 타당한가
6. assistant `output` token에만 loss를 적용하는 downstream 계약이 적절한가
7. held-out 격리를 모든 자연어 필드와 semantic alias까지 확장하는 것이 적절한가
8. source↔output 연속 5어절 복사 0건 기준이 과도한지, 수정이 필요하다면 어떤 대체 기준이 적절한가
9. task별 고정 비율 30/20/15/15/10/10을 두 군에 그대로 적용할 것인가
10. 사전 지식 likelihood matching을 `EXPERIMENT_READY` 전 필수 게이트로 둘 것인가
11. 선택적 M1 혼합군을 지금 포함할지 후속으로 미룰지
12. 다음 절의 개선 프롬프트가 데이터 생성 AI에게 충분히 명확하고 검증 가능한가

총괄 AI가 수정 후 승인을 권고하는 경우 다음을 명확히 제시해 주기를 요청한다.

- 수정할 규칙
- 수정 이유
- 보호해야 할 기존 규칙
- 새 파일과 source의 범위
- 자동 감사와 사람 검토의 경계
- 데이터 생성 완료, 실험 준비 완료, 실제 학습 완료의 구분

---

## 11. 개선안 적용 시 데이터셋 생성 요청 프롬프트

아래 블록은 **승인 후 사용하기 위한 프롬프트 초안**이다. 현재 문서 검토 단계에서는 실행하지 않는다.

````markdown
[검토용 초안 — 총괄 AI 승인 및 사용자의 별도 명시적 실행 승인 전 실제 수행 절대 금지]

# TinyLM 한국어 Stage1 Fresh-vs-Bridge SFT 6,000쌍 생성

## 0. 실행 게이트

현재 기본 모드는 REVIEW_ONLY다.

- 총괄 AI가 본 개선안을 타당하다고 승인하고,
- 사용자가 별도 메시지로 생성 대상·출력 경로·version을 명시하여 실제 생성을 승인하기 전에는,
- 데이터 생성, 파일 작성, 기존 파일 수정, 감사 결과 생성, 모델 실행, 학습, 평가를 시작하지 않는다.

승인 전에는 이 프롬프트의 모순, 누락, 구현 위험만 검토해 보고한다.

실행이 승인되더라도 데이터 생성 범위만 수행한다. GPU, 모델 load, 학습, checkpoint 생성, held-out 평가를 수행하지 않는다.

## 1. 배경

대상은 표준 사전학습을 완료했으나 지시-응답 SFT를 수행하지 않은 100M급 한국어 base LM이다. Stage1 고밀도 train 34,000건은 자연어 concept packet으로 구성된다.

이번 목적은 두 SFT 조건을 비교할 수 있는 데이터 자산을 만드는 것이다.

1. Fresh SFT: Stage1 기존 자산과 분리된 신규 source에서 만든 SFT 6,000건
2. Bridge SFT: 기존 고밀도 train source에서 지식→응답 형식으로 변환한 SFT 6,000건

두 데이터셋은 6,000개의 matched pair로 대응되어야 한다.

## 2. 기존 보호 자산

다음은 읽기 전용이다.

1. Stage1 고밀도 train 34,000건
2. Stage1 고밀도 validation 전체
3. `stage1_dataset/train_v2/stage1_train_900_v2.json`
4. `stage1_dataset/held-out_v2.7/stage1_heldout_benchmark_v2.7_300.json`

어떤 기존 파일도 수정·재직렬화·이름 변경·이동하지 않는다.

held-out 300은 source, 예시, 문장 생성 재료, 교정 근거, checkpoint 선택 또는 튜닝에 사용하지 않는다. 금지 집합 작성과 최종 격리 감사에만 사용한다.

## 3. 제안 산출물

승인된 출력 디렉터리 아래에 신규 파일로만 작성한다.

### 실제 SFT train

- `stage1_sft_fresh_train_6000_v1.jsonl`
- `stage1_sft_bridge_train_6000_v1.jsonl`

### 감사용 source와 rejected sidecar

- `stage1_sft_fresh_source_6000_v1.jsonl`
- `stage1_sft_fresh_rejected_sidecar_v1.jsonl`
- `stage1_sft_bridge_rejected_sidecar_v1.jsonl`

### manifest와 감사

- `stage1_sft_fresh_train_6000_v1_manifest.json`
- `stage1_sft_bridge_train_6000_v1_manifest.json`
- `stage1_sft_pair_manifest_v1.json`
- `stage1_sft_static_audit_v1.json`
- `stage1_sft_human_review_queue_v1.jsonl`

파일명과 출력 디렉터리는 총괄 AI 및 사용자 승인 내용이 우선한다.

## 4. 공통 task 구성

각 SFT 파일은 정확히 6,000건이다.

- identity: 1,800
- attribute: 1,200
- function: 900
- relation: 900
- boundary: 600
- counterexample: 600

Fresh와 Bridge의 같은 pair는 같은 task를 사용한다.

## 5. 실제 SFT 레코드 스키마

```json
{
  "id": "S1-SFTN-00001",
  "pair_id": "S1-SFTP-00001",
  "provenance_class": "fresh_disjoint | highdensity_bridge",
  "source_id": "<항상 non-null>",
  "source_dataset": "<정확한 source 자산>",
  "source_exposure_status": "not_in_highdensity_training_corpus | confirmed_exposed | unverified",
  "task": "identity | attribute | function | relation | boundary | counterexample",
  "instruction": "<한국어 한 문장 질문 또는 명령>",
  "input": "",
  "output": "<한국어 2~3문장: 직접 답변 후 source 근거>",
  "concepts": ["<등장 개념>"],
  "relations": ["<13개 통제 relation만 허용>"]
}
```

Fresh ID는 `S1-SFTN-00001`~`S1-SFTN-06000`, Bridge ID는 `S1-SFTB-00001`~`S1-SFTB-06000`, pair ID는 `S1-SFTP-00001`~`S1-SFTP-06000`을 사용한다.

실제 SFT loader의 직렬화 허용 목록은 `instruction`, `input`, `output`뿐이다. 나머지는 감사 metadata이며 모델 입력 문자열에 넣지 않는다. instruction과 input은 조건 문맥으로만 사용하고, loss는 assistant output token에만 적용한다.

## 6. Fresh source 규칙

- Fresh source ID는 `S1-SFTN-SRC-00001`~`S1-SFTN-SRC-06000`이다.
- 6,000건 모두 직접 작성한 독립적인 의미 source여야 한다.
- 기계적 개념명 치환, 템플릿 슬롯 교체, 기존 문장 부분 치환으로 만들지 않는다.
- 고밀도 34,000, 고밀도 validation, 저밀도 900과 그 paraphrase/near-negative, held-out 300과 분리한다.
- Fresh source는 SFT 생성과 감사에만 사용하며 서술문 학습 데이터로 포장하지 않는다.
- Fresh SFT의 source_id는 절대 null이 아니다.
- `source_exposure_status`는 `not_in_highdensity_training_corpus`다.
- 표준 사전학습 전체에서 unseen이라고 주장하지 않는다.

## 7. Bridge source 규칙

- 고밀도 train에서만 source를 선택한다.
- 6,000개의 source_id는 모두 고유하다.
- source당 SFT 한 건만 만든다.
- 고밀도 validation과 held-out은 source로 사용하지 않는다.
- 기존 source 파일이나 record는 수정하지 않는다.
- source의 자유 relation 대신 13개 `relations_controlled` 의미만 신규 SFT에 기록한다.
- source의 실제 고밀도 학습 provenance가 확인되었을 때만 `source_exposure_status`를 `confirmed_exposed`로 기록한다. 확인되지 않았으면 `unverified`로 기록하고 재노출 효과를 확정적으로 주장하지 않는다.

## 8. pair matching 규칙

각 Fresh/Bridge pair는 다음을 맞춘다.

- task
- relation 또는 relation-set 크기
- 질문 극성
- 답변 유형
- 추론 hop 수
- output 문장 수
- output 어절 수 비율 0.8~1.2
- 근거의 구체성
- 개념 추상도와 도메인 난이도
- rejected 오류 유형

두 군의 task별 평균 output 어절 수 차이는 5% 이내로 하고 중앙값·최소·최대·분위수를 함께 보고한다. 문장의 자연성을 훼손해서 길이를 기계적으로 맞추지 않는다. 기준을 만족하지 못하면 위반 목록을 남기고 PASS로 표시하지 않는다.

## 9. instruction과 output 규칙

### instruction

- 한국어 한 문장
- 물음표 질문 또는 명확한 명령형
- 정답의 핵심 predicate, object, 결론을 미리 포함하지 않음
- 하나의 target slot만 질문
- 동일 granularity에서 정답이 하나만 성립

### output

- 한국어 2~3문장
- 첫 문장에 직접 답함
- 한 문장 이상의 근거를 덧붙임
- source가 지지하지 않는 사실을 추가하지 않음
- source와 완전 동일 문장 0
- source에서 그대로 복사한 연속 5어절 이상 0
- held-out candidate 특유의 상투 표현을 사용하지 않음
- task별 고정 문구나 단일 어미로 과도하게 수렴하지 않음

질문에 대상 concept가 반복되는 것은 허용할 수 있으나, 정답을 구성하는 answer-bearing span이 instruction에 노출되어서는 안 된다.

## 10. relation 규칙

허용 relation은 다음 13개뿐이다.

`is_a`, `subclass_of`, `part_of`, `classification`, `boundary`, `contrast`, `comparison`, `function`, `role`, `process`, `state`, `attribute`, `other`

- 배열 내 중복 금지
- text와 instruction/output에 실제로 드러난 의미만 사용
- Fresh와 Bridge의 relation 및 relation-set 분포를 pair 또는 stratum 단위로 맞춤
- legacy 자유 label 사용 금지

## 11. rejected sidecar 규칙

rejected는 실제 SFT train JSONL에 넣지 않는다.

```json
{
  "sft_id": "S1-SFTN-00001",
  "pair_id": "S1-SFTP-00001",
  "chosen": "<SFT output과 동일>",
  "rejected": "<instruction에 대한 명백히 틀린 직접 답변>",
  "rejected_reason": "<사람용 한국어 설명>",
  "violated_relation": "<통제 relation>",
  "source_negative_id": null
}
```

- rejected를 만들 때 부정하거나 바꿀 target은 output의 새 지식이 아니라 instruction의 target slot에서 선택한다.
- 애매하거나 부분적으로 옳은 답은 금지한다.
- 열린 세계에서 거짓이 입증되지 않는 문장은 금지한다.
- near-negative 재사용은 새 instruction에 직접 답하고, 완전히 틀리며, 전역 중복이 없고, relation quota에 맞을 때만 허용한다.
- rejected sidecar는 SFT loader가 읽지 않는다.
- preference 학습은 별도 승인 없이는 수행하지 않는다.

## 12. held-out 격리 규칙

다음 전체 필드를 held-out v2.7과 비교한다.

- Fresh source text
- instruction
- input
- output
- concepts
- chosen/rejected/rejected_reason

반드시 다음을 검사한다.

1. unseen_concept 113개 주어 concept 및 승인 alias 등장 0
2. 전체 300개의 주어 concept＋relation 금지 조합 0
3. prompt/answer/candidates 정규화 exact 중복 0
4. 반복 5어절 0
5. required/forbidden relation 조합 누출 0
6. fuzzy similarity 상위 쌍 사람 검토
7. 의미상 후보를 베낀 paraphrase 0

seen_concept_control concept는 허용된 경우에도 해당 문항의 prompt, answer, candidate, 판정축을 복사·변형하지 않는다.

## 13. 중복·유사도·한국어 감사

각 데이터셋 내부 및 양쪽 데이터셋 사이에서 다음을 센다.

- ID 중복
- source_id 중복
- pair_id 누락·불일치
- instruction exact/normalized 중복
- output exact/normalized 중복
- concept＋relation-set 중복
- 반복 5어절
- 반복 도입부
- source↔output 복사
- fuzzy similarity 상위 쌍
- 조사·문법 오류 후보
- 비한국어 자연어 문장
- task·relation·길이 분포 차이
- 복수 정답 또는 사실 오류 후보

자동 감사만으로 의미 정확성을 PASS 처리하지 않는다. fuzzy 상위 쌍, 단일 정답성, rejected의 완전한 거짓은 사람 검토 queue에 남긴다.

## 14. manifest 필수 항목

각 manifest와 pair manifest에 다음을 포함한다.

- 파일명, version, 생성 시각
- source 파일 경로와 SHA-256
- 출력 파일 SHA-256
- 전체 레코드 수
- task별 건수
- relation과 relation-set 분포
- source_id 고유 수와 재사용 histogram
- source provenance 상태
- pair 6,000개 완전성
- task·relation·난이도 matching 결과
- 두 군의 output 문자·어절·token 길이 통계
- task별 평균·중앙값·최소·최대·분위수
- source↔SFT exact/5어절/fuzzy 감사
- Fresh와 기존 자산의 교차 중복 감사
- held-out 격리 감사
- near-negative 재사용 수와 source_negative_id
- rejected 전역 중복과 relation 분포
- 한국어·문법·단일 정답성 감사
- 사람 검토 완료 수와 미검토 수
- 규칙별 위반 건수와 record 목록
- `B0_KNOWLEDGE_MATCH_PENDING` 상태
- `TRAINING_NOT_STARTED`
- `EVALUATION_NOT_STARTED`

위반이 0이 아니면 목록을 숨기지 않는다. 0이라고 적기 전에 실제로 세어야 한다. 정적 위반 또는 사람 검토 미완료가 있으면 `EXPERIMENT_READY`로 표시하지 않는다.

## 15. 완료 보고의 경계

데이터 생성 AI는 다음만 보고할 수 있다.

- 파일 생성 여부
- 정적 감사 결과
- 사람 검토 상태
- 남은 위반과 차단 사항

다음을 보고하거나 암시하지 않는다.

- 모델이 개선되었다
- 중복학습이 유리하거나 불리하다고 증명되었다
- 학습이 완료되었다
- held-out 평가를 통과했다
- 배포 준비가 되었다

모델 load, GPU, 학습, 평가, checkpoint 선택은 사용자가 별도로 수행한다.
````

---

## 12. 개선안이 통과되지 않을 경우 대안 후보 3개

### 12.1 대안 1 — 완전 source 분리안

#### 내용

고밀도 학습에 쓰는 source와 SFT에 쓰는 source를 완전히 분리한다. 고밀도 학습 전에 34,000건 중 일부를 SFT 전용으로 예약하고 그 source의 서술문은 고밀도 학습에서 제외한다. 이미 34,000건을 학습했다면 새로운 source family만으로 SFT를 만든다.

#### 장점

- 의미 수준의 이중 노출을 가장 명확하게 제거한다.
- 실험 provenance와 데이터 독립성이 가장 강하다.
- source 과가중 여부를 해석하기 쉽다.

#### 한계

- SFT가 답변 형식과 새로운 사실을 동시에 학습하게 된다.
- 이미 고밀도 학습이 끝났다면 기존 source 분리는 소급 적용할 수 없다.
- 신규 사실 검증 비용이 크다.
- “이미 아는 지식을 답변으로 전환”한다는 원래 목적과 다소 멀어진다.

#### 적합한 경우

중복 자체를 최소화하는 것이 최우선이거나, 총괄 AI가 bridge 재사용의 과적합 위험을 허용할 수 없다고 판단할 때 적합하다.

### 12.2 대안 2 — Bridge 6,000 단일군＋무-SFT 기준선

#### 내용

신규 SFT 6,000건을 만들지 않고, 고밀도 train의 고유 source 6,000개에서 source당 한 건의 bridge SFT만 만든다. 고밀도 학습 완료 무-SFT B0와 비교한다.

#### 장점

- 데이터 생성과 학습 비용이 가장 낮다.
- “답하는 형식”을 최소 SFT로 주입할 수 있는지 빠르게 확인할 수 있다.
- source provenance와 사실 검증이 상대적으로 쉽다.

#### 한계

- 향상이 SFT 일반 효과인지 기존 지식 재노출 효과인지 구분할 수 없다.
- source-disjoint 대조군이 없어 암기와 일반화의 인과 해석이 약하다.
- bridge가 나쁘게 나와도 SFT 방식 문제인지 중복 문제인지 분리하기 어렵다.

#### 적합한 경우

예산이 매우 제한적이고 먼저 최소 가능성만 확인하려는 pilot 단계에 적합하다.

### 12.3 대안 3 — 단일 Hybrid SFT 6,000안

#### 내용

하나의 SFT 파일을 Fresh 3,000건과 Bridge 3,000건으로 구성하고 provenance를 명확히 표시한다. source당 한 건 제한과 task·relation matching을 유지한다.

#### 장점

- 순수 Fresh 6,000＋Bridge 6,000보다 생성·학습 비용이 낮다.
- 신규 일반화와 기존 지식 인출을 한 학습 과정에서 함께 제공한다.
- 실제 제품용 단일 SFT 혼합물 후보로는 실용적이다.

#### 한계

- Fresh와 Bridge의 독립 효과를 직접 분리할 수 없다.
- 혼합 비율 50:50이 최적이라는 근거가 없다.
- 한쪽 유형이 다른 유형의 효과를 상쇄하거나 가릴 수 있다.
- 원인 규명보다 실용적 mixture 탐색에 가깝다.

#### 적합한 경우

총괄 AI가 인과 비교보다 단일 실용 데이터셋의 비용 효율을 우선할 때 적합하다.

---

## 13. 권장 우선순위

1. **본 개선안: B0＋Fresh 6,000＋Bridge 6,000 matched comparison**
2. 대안 2: Bridge 6,000＋B0 최소 pilot
3. 대안 3: Fresh 3,000＋Bridge 3,000 hybrid
4. 대안 1: 완전 source 분리

본 개선안을 가장 우선하는 이유는 중복을 무조건 제거하거나 허용하는 결정을 사전에 내리지 않고, 동일 조건에서 유익한 bridge 효과와 해로운 과적합을 구분할 수 있기 때문이다.

대안 1은 데이터 독립성은 가장 강하지만, 이번 목적이 신규 지식 습득이 아니라 instruction-following gap 해소라는 점에서 우선순위를 낮게 두었다. 다만 평가 독립성과 중복 제거가 절대 조건으로 결정되면 대안 1이 최우선이 될 수 있다.

---

## 14. 최종 요청

총괄 AI는 다음 형식으로 회신해 주기를 요청한다.

```text
결정: 승인 | 수정 후 승인 | 기각

1. 연구 질문의 타당성:
2. 3조건 비교 구조의 타당성:
3. Fresh source ledger의 필요성:
4. 6,000 matched pair의 타당성:
5. rejected sidecar 분리의 타당성:
6. held-out 격리 규칙의 충분성:
7. 과도하거나 부족한 감사 기준:
8. 승인 전 반드시 수정할 내용:
9. 승인 후에도 사용자 별도 실행 승인이 필요한 단계:
10. 권장 대안 또는 추가 실험:
```

본 문서의 검토·승인은 데이터 생성 승인과 동일하지 않다. 총괄 AI가 개선안을 승인하더라도 사용자가 별도로 실제 생성 범위, 출력 위치, version을 명시하기 전에는 작업을 시작하지 않는다.

---

## 15. 참고 자산 및 확인 범위

이번 보고서 작성 시 다음을 읽기 전용으로 확인했다.

- `stage1_highdensity_dataset/TinyLM_Stage1_Stage7_Dataset_Design_Spec.md`
- `stage1_highdensity_dataset/TinyLM_Stage1_Stage7_Dataset_Corpus_Generation_Guide.md`
- `stage1_highdensity_dataset/train/stage1_(1)identity_high_density_train_v01.json`
- `stage1_dataset/train_v2/stage1_train_900_v2.json`
- `stage1_dataset/held-out_v2.7/stage1_heldout_benchmark_v2.7_300.json`
- `stage1_dataset/STAGE1_900_100_300_USAGE_CHANGE_REVIEW_REQUEST_CORRECTED.md`

확인하지 않았거나 수행하지 않은 범위:

- 모델 checkpoint와 실제 학습 log의 provenance 검증
- 고밀도 34,000건의 실제 모델 학습 여부 확인
- 신규/Fresh 또는 Bridge SFT 생성
- 교차 semantic audit 실행
- 모델 likelihood 기반 사전 지식 matching
- GPU 학습과 평가

따라서 본 문서의 결론은 **설계 타당성 검토 결과**이며 실험 결과가 아니다.
