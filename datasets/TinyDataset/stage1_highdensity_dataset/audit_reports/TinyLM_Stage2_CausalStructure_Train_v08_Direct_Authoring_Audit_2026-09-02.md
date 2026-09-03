# TinyLM Stage2 causal_structure train v08 직접 작성 감사

- 감사일: 2026-09-02 KST
- 판정: **PASS**
- reservation: `S2-A01-T-008`
- family: `도시 상수도 정수·배수 운영 — 원인 방향·피드백·역인과 판정`
- corpus: `stage2_highdensity_dataset/train/stage2_(11)causal_structure_high_density_train_v08.json`
- source: `stage2_highdensity_dataset/sources/train/stage2_(11)causal_structure_high_density_train_v08.source.jsonl`

## 1. 작성·포장 경계

150개의 primary concept, `text`, `relations`를 record별로 직접 작성했다. 자동 semantic-composition, 문자열 조합 concept 생성, 명사 치환 template, relation round-robin은 사용하지 않았다. 자동화는 JSONL parse, ID 부여, corpus 포장, tokenizer·중복·문법·유사도 감사에만 사용했다.

원고는 도시 상수도의 취수, 정수 공정, 송배수, 수질 변화, 센서·자동제어, 정비·사고 대응을 따라 원인 방향, 처방에 따른 역인과, 양·음의 피드백, 선택·관측 효과를 다룬다. 후반부는 시간 선후, 물리 전달, 운영 로그, 외생 충격, 시차 노드와 같은 방향 판정 기준을 포함한다. checkpoint는 `source_authoring_method: direct_model_authoring`, manual-review debt 0을 기록한다.

## 2. 구조·직렬화

| 검사 | 결과 |
|---|---:|
| source rows / corpus records | 150 / 150 |
| primary unique / text unique | 150 / 150 |
| ID first / last | `S2-CSH-01051` / `S2-CSH-01200` |
| source↔corpus projection 오류 | 0 |
| JSON/JSONL parse 오류 | 0 |
| 통제어휘 밖 relation | 0 |
| record 내부 relation 중복 | 0 |
| relation cardinality | 3개: 3 records, 4개: 147 records |
| 고유 relation-set / 단일 최대 빈도 | 40 / 13 records |
| `other_type` 불일치 | 0 |

## 3. Relations 분포

총 relation 배정은 597회다.

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 16 |
| `classification` | 53 |
| `boundary` | 150 |
| `contrast` | 25 |
| `comparison` | 52 |
| `function` | 49 |
| `role` | 50 |
| `process` | 124 |
| `state` | 45 |
| `attribute` | 33 |
| `other` | 0 |

`process`는 시간에 따른 정방향·역방향·순환 경로에, `role`은 운영자·제어기의 처방 반응에, `classification`은 역인과·선택 효과·방향 판정 유형에 사용했다. `boundary`는 상관과 단방향 인과, 원인과 후속 제어 반응의 경계를 모든 레코드에서 명시한다. `other`가 0회이므로 자주 나온 `other_type` 5가지는 해당 없음이다.

## 4. 중복·유사도·보일러플레이트

| 검사 | 결과 |
|---|---:|
| exact primary/text/normalized text 중복 | 0 |
| primary+relation-set 중복 | 0 |
| cross-record 5-word n-gram 반복 | 0 / 2,898 assignments |
| v08 내부 normalized character similarity ≥ 0.80 | 0 pairs |
| v08 내부 최대 character similarity | 0.455285 |
| v08 내부 word-set Jaccard ≥ 0.60 | 0 pairs |
| v08 내부 최대 word-set Jaccard | 0.236842 |
| 기존 Stage2 1,350 records 교차 character similarity ≥ 0.80 | 0 pairs |
| 기존 Stage2 교차 최대 character similarity | 0.492308 |
| 기존 Stage2 교차 word-set Jaccard ≥ 0.60 | 0 pairs |
| 기존 Stage2 교차 최대 word-set Jaccard | 0.175000 |
| generic shape fingerprint | 87종, 단일 최대 10/150 = 6.67% |

최종 lexical 5-gram 반복과 두 fuzzy 기준의 고유사 pair는 내부·기존 Stage2 교차 비교에서 모두 0이다. 원고 압축은 tokenizer 상한을 맞추기 위해 길이가 긴 레코드의 불필요한 수식만 직접 줄였으며, 객체·관계·인과 방향은 유지했다.

## 5. 한국어·token 감사

- exact tokenizer: `tok-ko-en-32768.json`, SHA-256 `3a69001ecc28a5bdf1e951a1036b234c9bdcb847b310252c6d72cfc6c52c48e3`
- 평균: 45.240000 tokens/record(+EOS)
- 최소/최대: 35 / 53
- Stage2 승인 평균: 41.625, 허용범위 ±10% = 37.4625~45.7875 — file mean PASS
- text 문자 길이: 최소 70, 평균 90.613, 최대 103
- hard grammar finding: 0
- 조사 휴리스틱 warning: 6

6개 warning 행을 직접 읽었다. `효과와`, `결과와`, `차이가` 같은 정상 단어 내부 부분문자열을 조사 의심 패턴으로 잡은 false positive이며, 은/는·이/가·을/를·와/과 결합 오류는 없었다.

## 6. 해시와 최종 판정

- source SHA-256: `a74c5888981bb1e22ea24fab4371d5829ba24baa914f629aaba2494876924d67`
- corpus SHA-256: `cbe738bdcf18bd9f408d61b14b303262d86a33527fd99ca11f476830de06ff97`
- resume checkpoint SHA-256: `e10fb9e4373a0abc58c64ace48212245d97673ea6e279e1c206d455efc86226c`
- central ledger SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`

`--require-complete --check-only` 감사에서 source 1·corpus 1, missing 0, structural PASS, direct-authoring debt 0을 확인했다. 전체 부분 감사도 43 source/corpus pairs·6,450 records에서 구조·exact/normalized 중복·train/validation exact leakage·5-word n-gram 반복·hard grammar·manual-review debt 모두 0으로 PASS했다. Stage1·저밀도·held-out·기존 Stage2~10 pilot과 v02~v07은 수정하지 않았다.

다음 예약은 `S2-A01-T-009`, `stage2_(11)causal_structure_high_density_train_v09.json`, ID `S2-CSH-01201 ~ S2-CSH-01350`, family `도시 상수도 정수·배수 운영 — 개입 전후 결과와 자연 변동 구분`이다.
