# SFT용 Fresh 코퍼스 v2 revision1 제출 보고서

## 판정

canonical 구조, 지정 tokenizer의 실제 ChatML 계측, task·등급 분포, 의미 다양성,
source 격리 및 exact 8-token 감사를 통과했다. 기존 v1과 실패한 v2 draft는 수정하지 않았다.
GPU·모델 로드·학습·checkpoint·모델 평가는 수행하지 않았다.
루트 평가기의 v2 T1 metadata choices 우도 채점은 `V2_T1_SCORER_PENDING`이다.

## 1. 실제 토큰 계측

| split | records | ChatML serialized | assistant body | supervised loss | supervised ratio |
|---|---:|---:|---:|---:|---:|
| train | 23,760 | 10,025,284 | 3,846,663 | 4,012,983 | 40.0286% |
| eval | 360 | 146,063 | 57,315 | 59,835 | 40.9652% |

학습 입력 계측은 canonical record의 `messages`만 live `chatml` serializer로 직렬화했다.
supervised-loss token은 assistant text와 승인된 종료 경계의 live loss span을 offset으로 셌다.

## 2. T1~T4 실제 분포

| tier | count | ratio |
|---|---:|---:|
| T1 | 11,880 | 50.00% |
| T2 | 5,940 | 25.00% |
| T3 | 3,564 | 15.00% |
| T4 | 2,376 | 10.00% |

## 3. T1 정답 위치와 길이 선택기

| gold index | count | ratio |
|---:|---:|---:|
| 0 | 2,970 | 25.00% |
| 1 | 2,970 | 25.00% |
| 2 | 2,970 | 25.00% |
| 3 | 2,970 | 25.00% |

| selector | correct | denominator | accuracy |
|---|---:|---:|---:|
| token shortest | 0 | 11,880 | 0.00% |
| token longest | 0 | 11,880 | 0.00% |
| char shortest | 0 | 11,880 | 0.00% |
| char longest | 0 | 11,880 | 0.00% |

## 4. 점유율과 의미 다양성

| axis | value | count | share |
|---|---|---:|---:|
| topic_label | 카드 정리 | 990 | 4.1667% |
| source_family | 훈련-금속고리-경계판별-공간경계 | 80 | 0.3367% |
| primary_concept | 샘가온결새표본 | 1 | 0.0042% |

| split | normalized unique | ratio | max repetition | domains | families |
|---|---:|---:|---:|---:|---:|
| train | 23,760 | 100.0000% | 1 | 24 | 576 |
| eval | 360 | 100.0000% | 1 | 24 | 281 |

- train/eval 의미 교집합: `{"normalized_source_types": {"count": 0, "sample": []}, "source_families": {"count": 0, "sample": []}, "situation_domains": {"count": 0, "sample": []}, "coined_stems": {"count": 0, "sample": []}, "primary_concepts": {"count": 0, "sample": []}}`
- source_family는 record ID가 아니라 split·situation domain·semantic task·logic archetype으로 재계산했다.

## 5. exact 8-token 연속 일치

| protected asset | query scope | exact shared types | query occurrences | protected occurrences |
|---|---|---:|---:|---:|
| held-out v2.8 | full package natural-language fields | 0 | 0 | 0 |
| ko-en 600M train.bin | train messages only | 0 | 0 | 0 |

## 유지·제외 범위

- v1 manifest 수록 파일은 SHA-256으로 불변성을 재검사했다.
- 실패한 v2 draft와 source_id, primary_concept, concept, source_text의 exact 교집합도 0이다.
- T4마다 서로 다른 reference answer를 2개 이상 포함한다.
- LLM judge는 사용하지 않아 사람 채점 50건 일치율 파일은 적용 대상이 아니다.
- rejected, near-negative, Bridge source는 생성하거나 학습 입력에 포함하지 않았다.
- 루트 evaluator 수정, GPU, 모델, 학습, checkpoint, 모델 평가는 모두 `NOT_RUN`이다.
