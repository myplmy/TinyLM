# SFT용 Fresh 코퍼스 v2 정적 감사

- 상태: `STATIC_AUDIT_PASS`
- 위반: 0건
- 모델 로드·학습·평가: `NOT_RUN`

## 실제 토큰 계측

| split | records | ChatML serialized | assistant body | supervised loss | supervised ratio |
|---|---:|---:|---:|---:|---:|
| train | 22,200 | 10,037,990 | 3,877,918 | 4,033,318 | 40.1805% |
| eval | 360 | 154,017 | 61,616 | 64,136 | 41.6422% |

## 분포 및 길이 단서

- train tier: `{"T1": 11100, "T2": 5550, "T3": 3330, "T4": 2220}`
- train task: `{"identity": 3700, "attribute": 3700, "function": 3700, "relation": 3700, "boundary": 3700, "counterexample": 3700}`
- train T1 gold: `{"0": 2775, "1": 2775, "2": 2775, "3": 2775}`
- train T1 길이 선택기: `{"token_shortest_correct": 0, "token_longest_correct": 0, "char_shortest_correct": 0, "char_longest_correct": 0, "denominator": 11100, "token_shortest_accuracy": 0.0, "token_longest_accuracy": 0.0, "char_shortest_accuracy": 0.0, "char_longest_accuracy": 0.0}`
- train topic 최대 점유: 1.6667%
- train source_family 최대 점유: 0.0045%
- train primary_concept 최대 점유: 0.0045%

## 격리

- train/eval 교집합: `{"source_ids": {"count": 0, "sample": []}, "primary_concepts": {"count": 0, "sample": []}, "source_families": {"count": 0, "sample": []}, "source_texts": {"count": 0, "sample": []}, "user_texts": {"count": 0, "sample": []}}`
- v1/v2 교집합: `{"source_ids": {"count": 0, "sample": []}, "primary_concepts": {"count": 0, "sample": []}, "concepts": {"count": 0, "sample": []}, "source_texts": {"count": 0, "sample": []}}`
- v1 불변성: 검사 19개, 불일치 0개

## 판정 경계

이 문서는 구조·정적 의미 계약·실제 tokenizer 계측을 감사한다. 모델 품질, 학습 성공,
T1 우도 채점기 동작은 검증하지 않았으며 루트 평가기는 `V2_T1_SCORER_PENDING`이다.
