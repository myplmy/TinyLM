# SFT용 Fresh 코퍼스 v2 작성 계약

- prompt version: `SFT-FRESH-V2-AUTHORING-20260913`
- dataset name: `SFT용 Fresh 코퍼스 v2`
- canonical version: `1`
- serializer: `chatml`
- tokenizer: `Z:\TinyLM\data_cache\tok-ko-en-32768.json`

## 목적

기존 학습·평가 문장을 재사용하지 않고, 한국어 base LM이 자료에서 질문의 대상을 찾고
직접 답하며 근거와 형식 제약을 지키도록 하는 positive SFT 자료를 작성한다. 모든 지식과
상황은 가공어로 만든 닫힌 문맥 안에서 완결한다.

## 고정 조건

1. v1 레코드와 source를 편입·복사·변형하지 않는다.
2. train은 ChatML로 직렬화한 실제 토큰이 10,000,000 이상이 되는 최초 120건 경계에서 멈춘다.
3. semantic task는 `identity`, `attribute`, `function`, `relation`, `boundary`,
   `counterexample`을 레코드 수 기준으로 정확히 균등하게 둔다.
4. 등급은 T1/T2/T3/T4를 50/25/15/10으로 둔다.
5. T1은 `meta.grading`에 `scoring_mode=multiple_choice`, 후보 4개, 0 기반 `gold`,
   `ranking_eligible=true`를 둔다. assistant 답은 정답 후보와 바이트 단위로 같아야 한다.
6. T1 정답 위치는 네 위치에 정확히 균등하고, 정답은 문자 길이와 tokenizer 토큰 길이에서
   모두 유일 최장·유일 최단이 아니어야 한다.
7. T1·T3·T4 assistant 본문은 100~250 tokenizer 토큰이다. T2는 정규화 가능한 단답 예외다.
   T3·T4는 2~4문장으로 쓴다.
8. 모든 레코드에 `required_elements`, `forbidden_elements`, `normalization_rule`을 둔다.
9. T4는 `ranking_eligible=false`이고 서로 다른 참조답안 두 개 이상을 둔다.
10. 모든 레코드의 `meta.generator`에 model, prompt_version, batch_id를 기록한다.
11. source 한 건에서 SFT 한 건만 만들고 source_id는 null이 될 수 없다.
12. train과 eval 사이에는 source_id, source_family, primary_concept, 정규화 source 문장의
    교집합이 없어야 한다.
13. 같은 topic_label의 train 점유율은 5% 이하이고, 가공어 primary_concept는 전부 고유하다.
14. 자연어는 한국어로 작성한다. 메타데이터 enum과 경로는 학습 입력이 아니다.
15. source가 지지하지 않는 지식, 최신 시사, 의료·법률 판단, 실제 인물·기관·제품을 쓰지 않는다.
16. rejected와 rejected_reason은 만들지 않는다.

## T1 후보 작성 규칙

- 네 후보의 핵심 결론은 서로 동시에 참일 수 없게 만든다.
- 오답은 핵심 명제가 명백히 거짓이어야 하며, 정답 일부를 섞어 애매하게 만들지 않는다.
- 길이 균형용 무관한 정형 문장을 붙이지 않는다. 각 문장은 해당 후보의 결론과 근거를 설명한다.
- assistant에는 선택지 번호나 해설 머리말을 붙이지 않고 정답 후보 문자열만 기록한다.

## 계측과 제출

- `messages`만 학습 직렬화 대상으로 센다.
- 본문 토큰, ChatML 직렬화 토큰, assistant 본문 토큰, assistant end 경계를 포함한
  supervised-loss 토큰을 분리해서 기록한다.
- held-out v2.8과 ko-en 600M `train.bin`의 모든 연속 8-token 창을 비교한다.
- LLM 심판은 사용하지 않는다. T4는 규칙 키와 복수 참조답안을 가진 진단 전용 자료로 남긴다.
- GPU, 모델 로딩, 학습, 체크포인트, 생성 평가를 수행하지 않는다.
