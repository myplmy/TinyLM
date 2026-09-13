# SFT용 Fresh 코퍼스 v2 revision1 작성 계약

- prompt version: `SFT-FRESH-V2-R1-AUTHORING-20260913`
- dataset name: `SFT용 Fresh 코퍼스 v2`
- package revision: `revision1`
- canonical version: `1`
- serializer: `chatml`
- tokenizer: `Z:\TinyLM\data_cache\tok-ko-en-32768.json`

## 목적

한국어 base LM이 닫힌 가상 문맥에서 질문 target을 찾고 직접 답하며, 근거와 형식 제약을
지키도록 하는 positive SFT 자료를 만든다. 기존 v1 및 실패한 v2 draft의 문장이나 source를
재료로 사용하지 않는다.

## 고정 계약

1. train은 실제 ChatML serialized token이 10,000,000 이상이 되는 최초 120-record 경계에서
   멈춘다.
2. semantic task 6종은 정확히 균등하고, T1/T2/T3/T4는 50/25/15/10이다.
3. T1은 네 배타 후보, 정확히 균등한 gold 위치, assistant와 gold 후보의 byte identity를
   지킨다. gold는 문자·token 기준 모두 최장·최단이 아니다.
4. T1·T3·T4 assistant는 100~250 tokenizer token이다. T2는 단답 예외다. T3·T4는
   2~4문장이다.
5. 모든 record에 generator model/prompt_version/batch_id와 required/forbidden/normalization
   규칙을 둔다. T4에는 서로 다른 reference answer를 두 개 이상 두고 ranking에서 제외한다.
6. source 한 건에서 SFT 한 건만 만들며 source_id와 primary concept는 모두 고유하다.
7. rejected, near-negative, Bridge source는 만들지 않는다.
8. LLM judge는 사용하지 않는다.

## 의미 다양성 hard gate

1. 각 source는 고유 `coined_stem`을 가지며 감사 시 그 어간을 `<가공어>`로 치환한다.
2. 정규화 train source 고유 유형률은 95% 이상, 최대 반복은 2회 이하다.
3. 정규화 source의 train/eval 교집합은 0이다.
4. `source_family`는 실제 `situation_domain × logic_archetype × semantic_task`로 정의하며
   record ID나 ordinal을 넣지 않는다.
5. train과 eval은 situation_domain, source_family, coined_stem, primary concept를 재사용하지
   않는다.
6. train은 24개 훈련 도메인과 6개 서술 스타일, eval은 별도의 24개 평가 도메인과 4개
   서술 스타일을 사용한다.
7. 각 task는 서로 다른 4개 논리 원형을 고르게 포함한다. 표면 명사만 교체한 동일 상황을
   새 family라고 부르지 않는다.
8. 같은 topic_label 점유율은 각 split에서 5% 이하다.

## 감사와 실행 경계

- canonical·분포·grading·실제 token 계측과 의미 다양성을 생성기와 독립된 도구로 다시 센다.
- held-out v2.8 및 ko-en 600M train.bin의 모든 연속 8-token window를 검사한다.
- 파일 존재나 정적 통과를 모델 품질·학습 성공으로 표현하지 않는다.
- GPU, 모델 loading, 학습, checkpoint, 모델 평가는 수행하지 않는다.
