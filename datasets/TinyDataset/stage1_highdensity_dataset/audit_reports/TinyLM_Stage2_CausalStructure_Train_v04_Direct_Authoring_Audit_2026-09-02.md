# TinyLM Stage2 causal_structure train v04 직접 작성 감사

- 감사일: 2026-09-02 KST
- 판정: **PASS**
- reservation: `S2-A01-T-004`
- family: `스마트 온실 관수·환경제어 — 개입 전후 결과와 자연 변동 구분`
- corpus: `stage2_highdensity_dataset/train/stage2_(11)causal_structure_high_density_train_v04.json`
- source: `stage2_highdensity_dataset/sources/train/stage2_(11)causal_structure_high_density_train_v04.source.jsonl`

## 1. 작성·포장 경계

150개의 primary concept, `text`, `relations`를 record별로 직접 작성했다. 자동 semantic-composition, 문자열 조합 concept 생성, 명사 치환 template, relation round-robin은 사용하지 않았다. 자동화는 JSONL parse, ID 부여, corpus 포장, tokenizer·중복·문법·유사도 감사에만 사용했다.

원고는 스마트 온실의 관수·환기·난방·차광·분무 개입 전후 결과에서 일주기, 날씨, 생육 단계, 동시 개입, 측정 위치·센서 교체, 회귀 효과, 지연·잔류를 자연 변동과 분리하는 판정법을 다룬다. 동시 대조, 시차 개입, 교차·반전 시험, 공통 추세 제거와 인과 결론 보류를 서로 다른 사례로 구성했다. checkpoint는 `source_authoring_method: direct_model_authoring`, manual-review debt 0을 기록한다.

## 2. 구조·직렬화

| 검사 | 결과 |
|---|---:|
| source rows / corpus records | 150 / 150 |
| primary unique / text unique | 150 / 150 |
| ID first / last | `S2-CSH-00451` / `S2-CSH-00600` |
| source↔corpus projection 오류 | 0 |
| JSON/JSONL parse 오류 | 0 |
| 통제어휘 밖 relation | 0 |
| record 내부 relation 중복 | 0 |
| relation cardinality | 3개: 13 records, 4개: 137 records |
| 고유 relation-set / 단일 최대 빈도 | 54 / 15 records |
| `other_type` 불일치 | 0 |

## 3. Relations 분포

총 relation 배정은 587회다.

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 23 |
| `classification` | 39 |
| `boundary` | 150 |
| `contrast` | 35 |
| `comparison` | 117 |
| `function` | 21 |
| `role` | 30 |
| `process` | 71 |
| `state` | 38 |
| `attribute` | 63 |
| `other` | 0 |

`boundary`와 `comparison`이 큰 것은 개입 전후 차이가 자연 변동 범위를 넘는지 대조하는 family 목표와 일치한다. 시간 흐름이나 측정 속성을 실제로 기술한 경우에만 `process`·`attribute`를 붙였다. 문장이 뒷받침하지 않는 `is_a`·`subclass_of`는 넣지 않았다. `other`가 0회이므로 자주 나온 `other_type` 5가지는 해당 없음이다.

## 4. 중복·유사도·보일러플레이트

| 검사 | 결과 |
|---|---:|
| exact primary/text/normalized text 중복 | 0 |
| primary+relation-set 중복 | 0 |
| cross-record 5-word n-gram 반복 | 0 / 2,599 assignments |
| v04 내부 normalized character similarity ≥ 0.80 | 0 pairs |
| v04 내부 최대 character similarity | 0.452174 |
| v04 내부 word-set Jaccard ≥ 0.60 | 0 pairs |
| v04 내부 최대 word-set Jaccard | 0.243243 |
| 기존 Stage2 900 records 교차 character similarity ≥ 0.80 | 0 pairs |
| 기존 Stage2 교차 최대 character similarity | 0.379310 |
| 기존 Stage2 교차 word-set Jaccard ≥ 0.60 | 0 pairs |
| 기존 Stage2 교차 최대 word-set Jaccard | 0.189189 |
| generic shape fingerprint | 67종, 단일 최대 11/150 = 7.33% |

relation-set은 54종이고 최다 조합도 15/150이다. lexical 5-gram 반복과 두 fuzzy 기준의 고유사 pair가 내부·기존 Stage2 교차 비교에서 모두 0이므로 명사만 바꾼 보일러플레이트 증거는 없다.

## 5. 한국어·token 감사

- exact tokenizer: `tok-ko-en-32768.json`, SHA-256 `3a69001ecc28a5bdf1e951a1036b234c9bdcb847b310252c6d72cfc6c52c48e3`
- 평균: 38.853333 tokens/record(+EOS)
- 최소/최대: 31 / 46
- Stage2 승인 평균: 41.625, 허용범위 ±10% = 37.4625~45.7875 — file mean PASS
- text 문자 길이: 최소 69, 평균 79.207, 최대 89
- hard grammar finding: 0
- 조사 휴리스틱 warning: 19

warning은 `차이가`, `효과와` 등에 포함된 `이가`·`과와` 부분문자열을 탐지한 false positive였다. 19개 경고 행을 모두 직접 읽어 조사 결합 오류가 아님을 확인했다.

## 6. 해시와 최종 판정

- source SHA-256: `c86c4c0a105dd4886d7094719242682c032898f306d47203442c34da5e2d2e76`
- corpus SHA-256: `c7b985298721469bff16316276c8b7dbf57cd5313f4d8d9975dac0675d36d843`
- resume checkpoint SHA-256: `1fc0e51bf485d456c4b7b73a0f000dbdb31247a5b9611c260b8e1236b910c0a6`
- central ledger SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`

`--require-complete --check-only` 감사에서 source 1·corpus 1, missing 0, structural PASS, direct-authoring debt 0을 확인했다. 전체 부분 감사도 39 source/corpus pairs·5,850 records에서 구조·exact/normalized 중복·train/validation exact leakage·5-word n-gram 반복·hard grammar·manual-review debt 모두 0으로 PASS했다. Stage1·저밀도·held-out·기존 Stage2~10 pilot과 v02~v03은 수정하지 않았다.
