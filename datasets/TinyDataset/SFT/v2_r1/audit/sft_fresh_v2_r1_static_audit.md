# SFT용 Fresh 코퍼스 v2 revision1 정적 감사

- 상태: `STATIC_AUDIT_PASS`
- 위반: 0건
- 모델 로드·학습·평가: `NOT_RUN`

## 실제 tokenizer 및 ChatML 계측

| split | records | serialized | assistant body | supervised loss | supervised ratio |
|---|---:|---:|---:|---:|---:|
| train | 23,760 | 10,025,284 | 3,846,663 | 4,012,983 | 40.0286% |
| eval | 360 | 146,063 | 57,315 | 59,835 | 40.9652% |

## 의미 다양성

| split | normalized unique | ratio | max multiplicity | domains | families |
|---|---:|---:|---:|---:|---:|
| train | 23,760 | 100.0000% | 1 | 24 | 576 |
| eval | 360 | 100.0000% | 1 | 24 | 281 |

- train/eval 의미 교집합: `{"normalized_source_types": {"count": 0, "sample": []}, "source_families": {"count": 0, "sample": []}, "situation_domains": {"count": 0, "sample": []}, "coined_stems": {"count": 0, "sample": []}, "primary_concepts": {"count": 0, "sample": []}}`
- T1 정답 위치: `{"0": 2970, "1": 2970, "2": 2970, "3": 2970}`
- T1 길이 선택기: `{"token_shortest_correct": 0, "token_longest_correct": 0, "char_shortest_correct": 0, "char_longest_correct": 0, "denominator": 11880, "token_shortest_accuracy": 0.0, "token_longest_accuracy": 0.0, "char_shortest_accuracy": 0.0, "char_longest_accuracy": 0.0}`
- 등급 분포: `{"T1": 11880, "T2": 5940, "T3": 3564, "T4": 2376}`
- task 분포: `{"identity": 3960, "attribute": 3960, "function": 3960, "relation": 3960, "boundary": 3960, "counterexample": 3960}`

## 격리와 보존

- v1 불변성: 검사 19개, 불일치 0개
- v1/revision1 교집합: `{"source_ids": {"count": 0, "sample": []}, "primary_concepts": {"count": 0, "sample": []}, "concepts": {"count": 0, "sample": []}, "source_texts": {"count": 0, "sample": []}}`
- 실패 draft/revision1 교집합: `{"source_ids": {"count": 0, "sample": []}, "primary_concepts": {"count": 0, "sample": []}, "concepts": {"count": 0, "sample": []}, "source_texts": {"count": 0, "sample": []}}`

이 감사는 구조·분포·정적 source 지지·실제 tokenizer 계측을 검증한다. 모델 품질,
학습 성공, 루트 T1 우도 채점기 동작은 검증하지 않았다.
