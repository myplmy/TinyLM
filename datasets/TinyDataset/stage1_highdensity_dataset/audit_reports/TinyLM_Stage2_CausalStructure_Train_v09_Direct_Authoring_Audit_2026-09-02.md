# TinyLM Stage2 causal_structure train v09 직접 작성 감사

- 감사일: 2026-09-02 KST
- 판정: **PASS**
- reservation: `S2-A01-T-009`
- family: `도시 상수도 정수·배수 운영 — 개입 전후 결과와 자연 변동 구분`
- corpus: `stage2_highdensity_dataset/train/stage2_(11)causal_structure_high_density_train_v09.json`
- source: `stage2_highdensity_dataset/sources/train/stage2_(11)causal_structure_high_density_train_v09.source.jsonl`

## 1. 작성·포장 경계

150개의 primary concept, `text`, `relations`를 record별로 직접 작성했다. 자동 semantic-composition, 명사 치환 template, relation round-robin은 사용하지 않았다. 자동화는 JSONL parse, ID 부여, tokenizer·중복·문법·유사도 감사와 source 계약의 기계적 표면 정렬에만 사용했다.

첫 source gate는 긴 primary 표제가 본문에서 축약된 148행을 차단했다. 그중 본문 첫 주제부가 명확한 116행은 직접 작성한 표제를 보존하며 주제부와 은/는 조사만 기계적으로 정렬했고, 나머지 32행은 문장별로 직접 다시 썼다. 이 과정에서 객체·관계·개입 방향은 바꾸지 않았고 generator provenance나 manual-review debt를 만들지 않았다.

원고는 취수·정수·송배수·계측·운영 개입의 전후 차이에서 강우, 계절, 수온, 유량, 수요, 원수 난이도, 설비 연령, 측정법 변화와 회귀평균을 분리한다. 후반부는 중단시계열, 차이의 차이, 합성·부정적 대조, 물질·열수지, 철회·재도입과 민감도 보고를 다룬다.

## 2. 구조·직렬화

| 검사 | 결과 |
|---|---:|
| source rows / corpus records | 150 / 150 |
| primary unique / text unique | 150 / 150 |
| ID first / last | `S2-CSH-01201` / `S2-CSH-01350` |
| source↔corpus projection 오류 | 0 |
| JSON/JSONL parse 오류 | 0 |
| primary 본문 literal 누락 | 0 |
| 통제어휘 밖 relation | 0 |
| record 내부 relation 중복 | 0 |
| relation cardinality | 3개: 4 records, 4개: 146 records |
| 고유 relation-set / 단일 최대 빈도 | 43 / 18 records |
| `other_type` 불일치 | 0 |

## 3. Relations 분포

총 relation 배정은 596회다.

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 19 |
| `classification` | 79 |
| `boundary` | 150 |
| `contrast` | 33 |
| `comparison` | 112 |
| `function` | 47 |
| `role` | 24 |
| `process` | 34 |
| `state` | 36 |
| `attribute` | 62 |
| `other` | 0 |

`comparison`은 자연 기준선·동시 대조·전후 격차를, `classification`은 설계·교란·측정 효과의 판정을, `attribute`는 유량·수온·농도·부하의 보정값을 나타낸다. `boundary`는 자연 변화와 개입 효과의 경계를 모든 레코드에 부여했다. `other`가 0회이므로 자주 나온 `other_type` 5가지는 해당 없음이다.

## 4. 중복·유사도·보일러플레이트

| 검사 | 결과 |
|---|---:|
| exact primary/text/normalized text 중복 | 0 |
| primary+relation-set 중복 | 0 |
| cross-record 5-word n-gram 반복 | 0 / 2,407 assignments |
| v09 내부 normalized character similarity ≥ 0.80 | 0 pairs |
| v09 내부 최대 character similarity | 0.481481 |
| v09 내부 word-set Jaccard ≥ 0.60 | 0 pairs |
| v09 내부 최대 word-set Jaccard | 0.212121 |
| 기존 Stage2 1,500 records 교차 character similarity ≥ 0.80 | 0 pairs |
| 기존 Stage2 교차 최대 character similarity | 0.527273 |
| 기존 Stage2 교차 word-set Jaccard ≥ 0.60 | 0 pairs |
| 기존 Stage2 교차 최대 word-set Jaccard | 0.264706 |
| generic shape fingerprint | 55종, 단일 최대 14/150 = 9.33% |

최종 lexical 5-gram과 두 fuzzy 기준의 고유사 pair는 내부·기존 Stage2 교차 비교에서 모두 0이다. 주제부 표면 정렬 뒤에도 exact·normalized 중복과 반복 n-gram이 새로 생기지 않았다.

## 5. 한국어·token 감사

- exact tokenizer: `tok-ko-en-32768.json`, SHA-256 `3a69001ecc28a5bdf1e951a1036b234c9bdcb847b310252c6d72cfc6c52c48e3`
- 평균: 38.633333 tokens/record(+EOS)
- 최소/최대: 22 / 48
- Stage2 승인 평균: 41.625, 허용범위 ±10% = 37.4625~45.7875 — file mean PASS
- text 문자 길이: 최소 48, 평균 77.093, 최대 92
- hard grammar finding: 0
- 조사 휴리스틱 warning: 18

18개 warning 행을 직접 읽었다. `차이가`, `효과와`, `기여를`, `결과와` 같은 정상 어휘 내부를 조사 의심 패턴으로 탐지한 false positive이며, 실제 은/는·이/가·을/를·와/과 불일치는 없었다.

## 6. 해시와 최종 판정

- source SHA-256: `324492030bec90a4e85e76b29b6f5a9257db9b2fa1937c056dd4d82bdeb6ccc3`
- corpus SHA-256: `0588971d57c1af84c67072b79a8bfa6d66354794031488866a2669dbaf86152b`
- resume checkpoint SHA-256: `eebcd409257086c616c4ccb56886917b19e82a823080775518397acca11b3f75`
- central ledger SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`

`--require-complete --check-only` 감사에서 source 1·corpus 1, missing 0, structural PASS, direct-authoring debt 0을 확인했다. 전체 부분 감사도 44 source/corpus pairs·6,600 records에서 구조·exact/normalized 중복·train/validation exact leakage·5-word n-gram 반복·hard grammar·manual-review debt 모두 0으로 PASS했다. Stage1·저밀도·held-out·기존 Stage2~10 pilot과 v02~v08은 수정하지 않았다.

다음 예약은 `S2-A01-T-010`, `stage2_(11)causal_structure_high_density_train_v10.json`, ID `S2-CSH-01351 ~ S2-CSH-01500`, family `도시 상수도 정수·배수 운영 — 다중 원인의 충분성·기여 범위`다.
