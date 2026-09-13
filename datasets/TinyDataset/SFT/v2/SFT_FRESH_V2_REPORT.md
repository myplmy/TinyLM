# SFT용 Fresh 코퍼스 v2 제출 보고서

> **사용 금지:** 후속 의미 다양성 감사에서 `SEMANTIC_SOURCE_FAMILY_AUDIT_FAIL`이
> 확인됐다. eval 360건 전부의 가공어-정규화 source 유형이 train과 겹치므로 이 보고서의
> 앞선 정적 통과만으로 학습·평가에 사용하면 안 된다. 최신 판정은
> `audit/sft_fresh_v2_semantic_diversity_audit.md`와 최종 manifest가 소유한다.

## 판정

데이터 패키지의 canonical 구조, 실제 tokenizer 계측, 명시적 라벨 분포 및
8-token 연속 일치 감사에는 통과했으나, 후속 의미 source-family 감사에는 실패했다.
모델 학습·모델 평가·GPU 실행은 하지 않았다.
현재 TinyLM 루트 평가기는 v2 T1 metadata choices 우도 채점을 지원하지 않으므로
상태는 `V2_T1_SCORER_PENDING`이며 `EXPERIMENT_READY`로 표시하지 않는다.

## 1. 실제 토큰 계측

| split | records | ChatML serialized | assistant body | supervised loss | supervised ratio |
|---|---:|---:|---:|---:|---:|
| train | 22,200 | 10,037,990 | 3,877,918 | 4,033,318 | 40.1805% |
| eval | 360 | 154,017 | 61,616 | 64,136 | 41.6422% |

직렬화 계측은 `messages`만 ChatML로 직렬화한 값이며, supervised loss token은
live serializer의 assistant loss span과 tokenizer offset을 대조한 값이다.

## 2. 등급 분포

| tier | count | ratio |
|---|---:|---:|
| T1 | 11,100 | 50.00% |
| T2 | 5,550 | 25.00% |
| T3 | 3,330 | 15.00% |
| T4 | 2,220 | 10.00% |

## 3. T1 정답 위치와 길이 선택기

| gold index | count | ratio |
|---:|---:|---:|
| 0 | 2,775 | 25.00% |
| 1 | 2,775 | 25.00% |
| 2 | 2,775 | 25.00% |
| 3 | 2,775 | 25.00% |

| selector | correct | denominator | accuracy |
|---|---:|---:|---:|
| token shortest | 0 | 11,100 | 0.00% |
| token longest | 0 | 11,100 | 0.00% |
| char shortest | 0 | 11,100 | 0.00% |
| char longest | 0 | 11,100 | 0.00% |

## 4. 최대 점유율

| axis | value | count | share |
|---|---|---:|---:|
| topic_label | 훈련_기록_작업실 | 370 | 1.6667% |
| source_family | 훈련_기록_작업실_가온결새표갈래 | 1 | 0.0045% |
| primary_concept | 솔가온결새이름 | 1 | 0.0045% |

## 5. 8-token 연속 일치

| protected asset | query scope | exact shared types | query occurrences | protected occurrences |
|---|---|---:|---:|---:|
| held-out v2.8 | full package natural-language fields | 0 | 0 | 0 |
| ko-en 600M train.bin | train messages only | 0 | 0 | 0 |

ko-en 공유 유형은 일반 표현의 우연한 일치까지 포함한 측정치이며 자동 폐기 기준이
아니다. 모든 exact 공유 유형은 `audit/sft_fresh_v2_overlap_match_types.jsonl`에
한 유형당 한 줄로 기록했다. held-out v2.8은 0건을 통과 기준으로 사용했다.

## 유지·제외 범위

- v1 manifest 수록 파일은 SHA-256으로 불변성을 재검사했다.
- train/eval source_id, primary_concept, source_family, source_text는 교집합 0을 요구했다.
- LLM judge는 사용하지 않았으므로 사람 채점 50건 일치율 파일은 적용 대상이 아니다.
- rejected/near-negative/Bridge source는 만들거나 학습 입력에 넣지 않았다.
- GPU, 모델 로드, 학습, checkpoint, 모델 평가는 모두 `NOT_RUN`이다.
