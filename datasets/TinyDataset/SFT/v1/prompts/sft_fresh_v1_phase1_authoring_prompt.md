# SFT용 Fresh 코퍼스 v1 — Phase 1 작성용 프롬프트

프롬프트 식별자: `SFT-FRESH-V1-AUTHORING-PROMPT-20260909`  
적용 batch: `SFT-FRESH-V1-PILOT-20260909`

## 역할

당신은 한국어 100M급 base LM이 문맥을 읽고 질문에 직접 답하는 행동을 익히도록 positive SFT 파일럿을 직접 작성한다. 기존 코퍼스의 지식을 다시 설명하거나 문장을 변형하는 것이 아니라, 각 행마다 독립적인 짧은 가상 사실·상황을 새로 쓴다.

## 절대 경계

1. 보호 자산의 문장, 개념 슬롯, 사건 구조, prompt, answer, candidate를 복사·부분 치환·의역하지 않는다.
2. held-out v2.7과 신규 평가의 주어 concept, alias, concept＋relation 조합, 문장 및 8-token 연속 표현을 train에 넣지 않는다.
3. 최신 시사, 실제 인물, 의료·법률 판단, 위해 절차, 전문 사실 검증이 필요한 내용을 쓰지 않는다.
4. source 한 건에서 SFT 한 건만 만든다. source ID는 null일 수 없다.
5. rejected와 rejected_reason은 만들지 않는다.
6. Phase 2, 모델 로드, GPU, 학습, checkpoint 및 모델 평가는 수행하지 않는다.

## 각 원고의 필수 요소

- `source_text`: 직접 작성한 한국어 사실·상황 1~4문장
- `atomic_facts`: source가 명시한 최소 사실
- `primary_concept`: 해당 행에서만 쓰는 명확한 target
- `semantic_task`: identity, attribute, function, relation, boundary, counterexample 중 하나
- `response_type`: grounded_qa, exact_short, choice_with_reason, constraint_response, open_explanation 중 하나
- `relations_controlled`: 승인된 13개 라벨 중 의미에 필요한 것만, 중복 없이
- `instruction`: target 하나만 묻는 한국어 한 문장 질문 또는 명령
- `output`: 질문에 바로 답하는 1~3문장; source 밖 지식과 상투적 서론 금지
- `answer_key`: source와 output이 모두 지지하는 고유 정답 요소
- `forbidden_key`: 포함되면 명백히 오답인 요소
- `topic_label`, `source_family`: split 격리와 분포 감사용

## 작성 원칙

- 문맥은 고유한 가상 명칭, 공방·보관소·정원·안내소·실험 장치 같은 저위험 일상 micro-world를 사용한다.
- 질문에 답 문장을 그대로 미리 넣지 않되, 답을 판정할 사실은 문맥에 명시한다.
- 같은 granularity의 정답이 하나만 성립하도록 수량, 위치, 명칭, 역할 또는 위반 사례를 분명히 한다.
- identity는 종류·명칭, attribute는 속성·상태, function은 용도·역할, relation은 포함·순서·비교, boundary는 적용 범위, counterexample은 명백한 규칙 위반을 묻는다.
- choice 문항은 후보를 instruction 안에 제시하고 하나만 정답으로 만든다.
- constraint 문항은 답의 길이·문장 수·표현 조건이 자동으로 확인 가능해야 한다.
- open explanation은 2~3문장이되 deterministic 요소 채점을 함께 제공하며 모델 서열 결정에는 쓰지 않는다.
- 자연어는 한국어로 쓴다. 숫자·단위·고유명사 표기만 예외로 둔다.

## 재현 가능한 일괄 작성 규칙

- 반복 가능한 로컬 작성 도구를 쓰는 경우에도 보호 자산을 입력으로 읽지 않으며, 사실 목록과 표현 규칙을 이 코퍼스용으로 직접 작성한다.
- 기존 문장의 명칭만 바꾸는 방식은 허용하지 않는다. task별 사건 구조와 정답 predicate를 새로 정의한다.
- 각 행의 source와 primary concept는 고유해야 하며, 구조적 일괄 작성 여부를 provenance의 method detail과 manifest 집계에 공개한다.
- 구조가 비슷한 Fresh source 쌍은 숨기지 않고 내부 fuzzy 후보로 보고한다. 파일럿 단계에서는 측정값을 자동 폐기 문턱으로 바꾸지 않는다.

## 분포

- train 1,000건: semantic task `167/167/167/167/166/166`, response type 각 200건
- eval 300건: semantic task 각 50건, response type 각 60건
- 같은 topic_label은 train 전체의 5% 이하
- train/eval 사이 primary concept, source family, topic label은 교집합 0

## canonical 변환

최종 train 및 eval 레코드는 canonical version 1을 사용한다. user text는 `자료: {source_text}\n질문: {instruction}`, assistant text는 `output`이다. 학습 입력은 `messages`만이며 `meta`와 source ledger는 학습 문자열에 포함하지 않는다.
