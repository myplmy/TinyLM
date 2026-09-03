# TinyLM Stage2 causal_structure train v38 직접 작성 감사

- 감사일: 2026-09-02 KST
- 판정: **PASS**
- reservation: `S2-A01-T-038`
- family: `생태 복원지 종·서식지 관찰 — 원인 방향·피드백·역인과 판정`
- corpus: `stage2_highdensity_dataset/train/stage2_(11)causal_structure_high_density_train_v38.json`
- source: `stage2_highdensity_dataset/sources/train/stage2_(11)causal_structure_high_density_train_v38.source.jsonl`

## 1. 작성·포장 경계

150개의 primary concept, `text`, `relations`를 record별로 직접 작성했다. 자동 semantic-composition, 명사 치환 template, relation round-robin은 사용하지 않았다. 자동화는 JSONL parse, source 계약 검사, ID·고정 metadata 부여, tokenizer·중복·문법·유사도 감사에만 사용했다.

원고는 복원 개입 뒤의 선후·시차, 양·음의 피드백, 관리 대상 선정과 관측 노력에서 생기는 역인과, 생물·서식 상태의 쌍방향 원인, 그리고 제거·재도입·시계열·요인실험·음의 대조·외생 충격 같은 방향 식별법을 서로 다른 사례로 다룬다. 각 문장은 생태 복원지의 종·서식지 관찰 범위 안에서 원인과 결과의 역할이 시간에 따라 바뀔 수 있음을 직접 설명한다.

최초 150행은 구조상 유효했으나 tokenizer 평균 51.013333(+EOS)으로 Stage2 상한을 넘었다. 의미와 relation 근거를 유지하면서 긴 레코드를 두 차례 직접 압축해 45.740000, 이어진 n-gram 수정 뒤 45.733333으로 낮췄다. 포장 전 전체 source-only 감사가 파일 내부 `젖은 흙이 잎 활동을 높이고`와 기존 v07 교차 `지표에도 같은 상관이 나타나는지 보는` 두 반복을 검출해 해당 v38 문장을 직접 재서술했고, 최종 반복은 0이다.

## 2. 구조·직렬화

| 검사 | 결과 |
|---|---:|
| source rows / corpus records | 150 / 150 |
| primary unique / text unique | 150 / 150 |
| ID first / last | `S2-CSH-05551` / `S2-CSH-05700` |
| source↔corpus projection 오류 | 0 |
| JSON/JSONL parse 오류 | 0 |
| primary 본문 literal 누락 | 0 |
| 통제어휘 밖 relation | 0 |
| record 내부 relation 중복 | 0 |
| relation cardinality | 4개: 150 records |
| 고유 relation-set / 단일 최대 빈도 | 74 / 6 records |
| `other_type` 불일치 | 0 |

## 3. Relations 분포

총 relation 배정은 600회다.

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 37 |
| `classification` | 65 |
| `boundary` | 86 |
| `contrast` | 42 |
| `comparison` | 58 |
| `function` | 63 |
| `role` | 67 |
| `process` | 122 |
| `state` | 26 |
| `attribute` | 34 |
| `other` | 0 |

`process`는 선후·지연·되먹임의 시간 전개, `boundary`는 상관·역인과·단방향 확정 사이 경계에 사용했다. `role`, `function`, `classification`은 원인·결과·매개와 개입·대조·식별법의 역할을, `comparison`과 `contrast`는 전후·방향 후보·피드백 부호의 차이를 담는다. `part_of`, `attribute`, `state`는 순환 경로의 단계와 수위·수분·피복 같은 측정 상태에 한정했다. `other`가 0회이므로 자주 나온 `other_type` 5가지는 해당 없음이다.

## 4. 중복·유사도·보일러플레이트

| 검사 | 결과 |
|---|---:|
| exact primary/text/normalized text 중복 | 0 |
| primary+relation-set 중복 | 0 |
| v38 내부 cross-record 5-word n-gram 반복 | 0 / 2,601 assignments |
| 현행 전체 73파일 cross-record 5-word n-gram 반복 | 0 / 196,572 assignments |
| v38 내부 normalized character similarity ≥ 0.80 | 0 pairs |
| v38 내부 최대 character similarity | 0.471545 |
| v38 내부 word-set Jaccard ≥ 0.60 | 0 pairs |
| v38 내부 최대 word-set Jaccard | 0.181818 |
| 기존 Stage2 train 5,850 records 교차 character similarity ≥ 0.80 | 0 pairs |
| 기존 Stage2 train 교차 최대 character similarity | 0.429630 |
| 기존 Stage2 train 교차 word-set Jaccard ≥ 0.60 | 0 pairs |
| 기존 Stage2 train 교차 최대 word-set Jaccard | 0.157895 |
| generic shape fingerprint | 69종, 단일 최대 9/150 = 6.00% |

직접 수정 뒤 lexical 5-gram 반복은 내부·누적 모두 0이며 문자·단어집합 fuzzy 검토선을 넘은 pair도 없다. 시간 방향, 피드백, 역인과, 상호원인, 식별 설계의 사례와 문장 구성을 분산해 generic shape 최대 점유는 6%다.

## 5. 한국어·token 감사

- exact tokenizer: `tok-ko-en-32768.json`, SHA-256 `3a69001ecc28a5bdf1e951a1036b234c9bdcb847b310252c6d72cfc6c52c48e3`
- 최종 평균: 45.733333 tokens/record(+EOS)
- 최종 최소/최대: 38 / 50
- Stage2 승인 평균: 41.625, 허용범위 ±10% = 37.4625~45.7875 — file mean PASS
- text 문자 길이: 최소 69, 평균 86.473, 최대 108
- hard grammar finding: 0
- 조사 휴리스틱 warning: 14

14개 warning 위치를 전수 읽었다. 모두 `효과와`, `높이가`, `여과와`, `웅덩이가`, `역인과와`, `먹이가`, `피복과`, `차이가`처럼 정상 명사와 조사의 결합 또는 단어 내부를 보수적으로 잡은 false positive이며 실제 조사 불일치는 없다.

## 6. 해시와 최종 판정

- source SHA-256: `b0666c45b9e3d2c0d68a7409b607256d83aa8f3eccf5ececdea0220fcb1f28b8`
- corpus SHA-256: `99ead2237ab72890c79c8d065b943094e2da5d42da05f06198d689b6190dddf1`
- resume checkpoint SHA-256: `fa3e7ba4708776522ca5700b68a1c0bc8103e2908e731a8dd7f41c903c35c3d8`
- central ledger SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`

`--require-complete --check-only` 감사에서 source 1·corpus 1, missing 0, structural PASS, direct-authoring debt 0을 확인했다. 전체 부분 감사도 73 source/corpus pairs·10,950 records에서 구조·exact/normalized 중복·train/validation exact leakage·5-word n-gram 반복·hard grammar·manual-review debt 모두 0으로 PASS했다. Stage2 누적 6,150 records(현행 validation 포함)의 exact tokenizer 평균은 43.064878(+EOS)으로 gate PASS다. 중앙 원장과 9개 manifest의 read-only projection 검증도 PASS했고 보호 대상 변경은 없다.

다음 예약은 `S2-A01-T-039`, `stage2_(11)causal_structure_high_density_train_v39.json`, ID `S2-CSH-05701 ~ S2-CSH-05850`, family `생태 복원지 종·서식지 관찰 — 개입 전후 결과와 자연 변동 구분`이다.
