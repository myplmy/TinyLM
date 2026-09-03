# TinyLM Stage2 causal_structure train v29 직접 작성 감사

- 감사일: 2026-09-02 KST
- 판정: **PASS**
- reservation: `S2-A01-T-029`
- family: `식품 냉장 유통·품질 유지 — 개입 전후 결과와 자연 변동 구분`
- corpus: `stage2_highdensity_dataset/train/stage2_(11)causal_structure_high_density_train_v29.json`
- source: `stage2_highdensity_dataset/sources/train/stage2_(11)causal_structure_high_density_train_v29.source.jsonl`

## 1. 작성·포장 경계

150개의 primary concept, `text`, `relations`를 record별로 직접 작성했다. 자동 semantic-composition, 명사 치환 template, relation round-robin은 사용하지 않았다. 자동화는 JSONL parse, source 계약 검사, ID·고정 metadata 부여, tokenizer·중복·문법·유사도 감사에만 사용했다.

원고는 냉장유통 개입 전후 차이를 계절·날씨·품목구성·공급처·기준선 추세·평균회귀·측정기준 변경·동시개입·예고효과·파급·자연노화·학습·지연·잔류와 구분한다. 대조군, 차이의 차이, 단절시계열, 위약·음성대조·민감도, 용량반응과 기전 순서를 이용해 후값 하나를 개입효과와 같게 두지 않도록 구성했다.

첫 작성분은 148행으로 계수되어 패키징 전에 중단했고, 자연 기준선 재설정과 실제 가동시점 2행을 직접 보충했다. 150행 source는 최초 평균 41.720000(+EOS)으로 구조·token gate를 통과했다. package 뒤 전체 감사에서 v12와 공유한 위약검사 표현의 5-word n-gram 2종을 발견해 T029 문장을 직접 재서술하고 source·corpus·checkpoint SHA를 동기화했다. 최종 평균은 41.706667이고 누적 반복은 0이다.

## 2. 구조·직렬화

| 검사 | 결과 |
|---|---:|
| source rows / corpus records | 150 / 150 |
| primary unique / text unique | 150 / 150 |
| ID first / last | `S2-CSH-04201` / `S2-CSH-04350` |
| source↔corpus projection 오류 | 0 |
| JSON/JSONL parse 오류 | 0 |
| primary 본문 literal 누락 | 0 |
| 통제어휘 밖 relation | 0 |
| record 내부 relation 중복 | 0 |
| relation cardinality | 3개: 13 records, 4개: 137 records |
| 고유 relation-set / 단일 최대 빈도 | 45 / 15 records |
| `other_type` 불일치 | 0 |

## 3. Relations 분포

총 relation 배정은 587회다.

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 5 |
| `classification` | 65 |
| `boundary` | 150 |
| `contrast` | 34 |
| `comparison` | 101 |
| `function` | 27 |
| `role` | 33 |
| `process` | 89 |
| `state` | 43 |
| `attribute` | 40 |
| `other` | 0 |

`comparison`은 처리·대조, 전후 변화량, 기준선 추세와 민감도 대조를, `process`는 자연변화·개입·지연·잔류의 시간경로를 나타낸다. `classification`은 평균회귀·구성효과·측정변화·간섭·위약검사의 판정 지위를 맡는다. `boundary`는 모든 record에서 단순 전후차와 인과효과의 경계를 명시한다. `other`가 0회이므로 자주 나온 `other_type` 5가지는 해당 없음이다.

## 4. 중복·유사도·보일러플레이트

| 검사 | 결과 |
|---|---:|
| exact primary/text/normalized text 중복 | 0 |
| primary+relation-set 중복 | 0 |
| v29 내부 cross-record 5-word n-gram 반복 | 0 / 2,279 assignments |
| 현행 전체 64파일 cross-record 5-word n-gram 반복 | 0 / 175,059 assignments |
| v29 내부 normalized character similarity ≥ 0.80 | 0 pairs |
| v29 내부 최대 character similarity | 0.358974 |
| v29 내부 word-set Jaccard ≥ 0.60 | 0 pairs |
| v29 내부 최대 word-set Jaccard | 0.212121 |
| 기존 Stage2 train 4,500 records 교차 character similarity ≥ 0.80 | 0 pairs |
| 기존 Stage2 train 교차 최대 character similarity | 0.439024 |
| 기존 Stage2 train 교차 word-set Jaccard ≥ 0.60 | 0 pairs |
| 기존 Stage2 train 교차 최대 word-set Jaccard | 0.222222 |
| generic shape fingerprint | 57종, 단일 최대 18/150 = 12.00% |

generic shape 최대 점유는 문장 수와 어절 수만 치환한 보수적 형태지문에서 12.00%다. 그러나 exact·normalized·5-word n-gram과 문자·단어집합 유사도에서 내부·기존 Stage2 train 교차 검토선을 넘은 pair가 모두 0이고 최대 문자유사도도 0.439024 이하이므로, 명사만 바꾼 lexical boilerplate 증거는 발견되지 않았다.

## 5. 한국어·token 감사

- exact tokenizer: `tok-ko-en-32768.json`, SHA-256 `3a69001ecc28a5bdf1e951a1036b234c9bdcb847b310252c6d72cfc6c52c48e3`
- 최종 평균: 41.706667 tokens/record(+EOS)
- 최종 최소/최대: 35 / 49
- Stage2 승인 평균: 41.625, 허용범위 ±10% = 37.4625~45.7875 — file mean PASS
- text 문자 길이: 최소 69, 평균 79.253, 최대 90
- hard grammar finding: 0
- 조사 휴리스틱 warning: 9

9개 warning 위치를 전수 읽었다. `차이가`, `수준효과와`, `지속효과와`, `측정효과와`, `개입효과와`, `효과와`처럼 정상 단어 내부를 보수적으로 잡은 false positive이며 실제 조사 불일치는 없다.

## 6. 해시와 최종 판정

- source SHA-256: `129694b8be2f9f9d6e3ae0fd33da5fe596b5c88459dfe3225a1e82978656e335`
- corpus SHA-256: `1cf68c1275f178b540eb1201c33d0cb3f63250a6925c11d9133b7b4e7ffdc47e`
- resume checkpoint SHA-256: `575fd36af759c0bf5f6be10dad2a2b40f348f899a67e84e19aae4b65eb2d3077`
- central ledger SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`

`--require-complete --check-only` 감사에서 source 1·corpus 1, missing 0, structural PASS, direct-authoring debt 0을 확인했다. 전체 부분 감사도 64 source/corpus pairs·9,600 records에서 구조·exact/normalized 중복·train/validation exact leakage·5-word n-gram 반복·hard grammar·manual-review debt 모두 0으로 PASS했다. Stage2 누적 4,800 records(현행 validation 포함)의 exact tokenizer 평균은 43.122708(+EOS)으로 gate PASS다. 보호 대상 변경은 없다.

다음 예약은 `S2-A01-T-030`, `stage2_(11)causal_structure_high_density_train_v30.json`, ID `S2-CSH-04351 ~ S2-CSH-04500`, family `식품 냉장 유통·품질 유지 — 다중 원인의 충분성·기여 범위`다.
