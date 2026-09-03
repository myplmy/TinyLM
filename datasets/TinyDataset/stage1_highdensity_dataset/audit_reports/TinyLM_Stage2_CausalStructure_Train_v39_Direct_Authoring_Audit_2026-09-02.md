# TinyLM Stage2 causal_structure train v39 직접 작성 감사

- 감사일: 2026-09-02 KST
- 판정: **PASS**
- reservation: `S2-A01-T-039`
- family: `생태 복원지 종·서식지 관찰 — 개입 전후 결과와 자연 변동 구분`
- corpus: `stage2_highdensity_dataset/train/stage2_(11)causal_structure_high_density_train_v39.json`
- source: `stage2_highdensity_dataset/sources/train/stage2_(11)causal_structure_high_density_train_v39.source.jsonl`

## 1. 작성·재개·포장 경계

사용자 일시중단 전에 직접 작성한 98행을 해시로 대조해 그대로 보존하고, 재개 승인 뒤 99번째부터 150번째까지 52개의 primary concept, `text`, `relations`를 record별로 직접 작성했다. 자동 semantic-composition, 명사 치환 template, relation round-robin은 사용하지 않았다. 자동화는 JSONL parse, source 계약 검사, ID·고정 metadata 부여, tokenizer·중복·문법·유사도 감사에만 사용했다.

원고는 복원 전후의 기상·계절·장기추세·평균회귀와 개입 효과를 구분하고, 관찰 횟수·조사자·센서·표본 깊이·분류 기준 같은 탐지 변화, 주변 서식지 유입·재난·단계적 개입 같은 대조 근거를 이용해 자연 변동의 몫을 분리한다. 완성 source는 최초 검사에서 구조와 token gate를 통과했고, 전체 Stage2 source-only 감사에서도 cross-record 5-word n-gram 반복이 없어서 문장 수정 없이 포장했다.

## 2. 구조·직렬화

| 검사 | 결과 |
|---|---:|
| source rows / corpus records | 150 / 150 |
| primary unique / text unique | 150 / 150 |
| ID first / last | `S2-CSH-05701` / `S2-CSH-05850` |
| source↔corpus projection 오류 | 0 |
| JSON/JSONL parse 오류 | 0 |
| primary 본문 literal 누락 | 0 |
| 통제어휘 밖 relation | 0 |
| record 내부 relation 중복 | 0 |
| relation cardinality | 4개: 150 records |
| 고유 relation-set / 단일 최대 빈도 | 44 / 15 records |
| `other_type` 불일치 | 0 |

## 3. Relations 분포

총 relation 배정은 600회다.

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 7 |
| `classification` | 54 |
| `boundary` | 85 |
| `contrast` | 30 |
| `comparison` | 127 |
| `function` | 56 |
| `role` | 28 |
| `process` | 129 |
| `state` | 29 |
| `attribute` | 55 |
| `other` | 0 |

`process`는 시간에 따른 자연 변동과 개입 반응, `comparison`은 처리·대조·이전 시기 비교, `boundary`는 개입 효과와 자연 회귀·탐지 변화의 경계를 표시한다. `classification`, `function`, `attribute`, `state`, `role`, `contrast`, `part_of`는 문장에 명시된 판정 설계와 측정·기여·출처에 한정했다. `other`가 0회이므로 자주 나온 `other_type` 5가지는 해당 없음이다.

## 4. 중복·유사도·보일러플레이트

| 검사 | 결과 |
|---|---:|
| exact primary/text/normalized text 중복 | 0 |
| primary+relation-set 중복 | 0 |
| v39 내부 cross-record 5-word n-gram 반복 | 0 / 2,504 assignments |
| 현행 전체 74파일 cross-record 5-word n-gram 반복 | 0 / 199,076 assignments |
| v39 내부 normalized character similarity ≥ 0.80 | 0 pairs |
| v39 내부 최대 character similarity | 0.424779 |
| v39 내부 word-set Jaccard ≥ 0.60 | 0 pairs |
| v39 내부 최대 word-set Jaccard | 0.187500 |
| 기존 Stage2 train 6,000 records 교차 character similarity ≥ 0.80 | 0 pairs |
| 기존 Stage2 train 교차 최대 character similarity | 0.389381 |
| 기존 Stage2 train 교차 word-set Jaccard ≥ 0.60 | 0 pairs |
| 기존 Stage2 train 교차 최대 word-set Jaccard | 0.176471 |
| generic shape fingerprint | 39종, 단일 최대 16/150 = 10.67% |

정확·정규화·5어절 반복과 두 fuzzy 검토선을 넘은 pair가 없다. 39개 일반 문장 형태에 걸쳐 교란 요인과 판정 근거를 바꾸었으며, 단일 형태 최대 점유도 16건이다.

## 5. 한국어·token 감사

- exact tokenizer: `tok-ko-en-32768.json`, SHA-256 `3a69001ecc28a5bdf1e951a1036b234c9bdcb847b310252c6d72cfc6c52c48e3`
- 최종 평균: 43.653333 tokens/record(+EOS)
- 최종 최소/최대: 36 / 54
- Stage2 승인 평균: 41.625, 허용범위 ±10% = 37.4625~45.7875 — file mean PASS
- text 문자 길이: 최소 71, 평균 81.193, 최대 99
- hard grammar finding: 0
- 조사 휴리스틱 warning: 28

28개 warning을 전수 읽었다. `효과와`, `먹이가`, `차이가`, `증가는`, primary 안의 `...과 ...` 연결처럼 정상 단어 내부 또는 어절 경계를 보수적으로 잡은 false positive이며 실제 조사 불일치는 없다.

## 6. 해시와 최종 판정

- source SHA-256: `27d8e23d5e4cd82b66d5907bd223ba7c43f4e605cfa10fc6bb99f7ae6b57e52f`
- corpus SHA-256: `949994562255517567f4475500241075e138db70ac4fb7f6933c1344d5d137e6`
- resume checkpoint SHA-256: `ee72e500260c6a0a40b1a8018816980c31c2040474f2bc356739c0bd00e7ff1d`
- central ledger SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`

`--require-complete --check-only` 감사에서 source 1·corpus 1, missing 0, structural PASS, direct-authoring debt 0을 확인했다. 전체 부분 감사도 74 source/corpus pairs·11,100 records에서 구조·exact/normalized 중복·train/validation exact leakage·5-word n-gram 반복·hard grammar·manual-review debt 모두 0으로 PASS했다. Stage2 누적 6,300 records의 exact tokenizer 평균은 43.078889(+EOS)으로 gate PASS다.

다음 예약은 `S2-A01-T-040`, `stage2_(11)causal_structure_high_density_train_v40.json`, ID `S2-CSH-05851 ~ S2-CSH-06000`, family `생태 복원지 종·서식지 관찰 — 다중 원인의 충분성·기여 범위`다.
