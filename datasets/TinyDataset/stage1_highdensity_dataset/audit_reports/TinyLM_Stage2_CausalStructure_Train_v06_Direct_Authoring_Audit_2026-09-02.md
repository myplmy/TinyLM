# TinyLM Stage2 causal_structure train v06 직접 작성 감사

- 감사일: 2026-09-02 KST
- 판정: **PASS**
- reservation: `S2-A01-T-006`
- family: `도시 상수도 정수·배수 운영 — 직접 원인·매개 경로·배경 조건 분리`
- corpus: `stage2_highdensity_dataset/train/stage2_(11)causal_structure_high_density_train_v06.json`
- source: `stage2_highdensity_dataset/sources/train/stage2_(11)causal_structure_high_density_train_v06.source.jsonl`

## 1. 작성·포장 경계

150개의 primary concept, `text`, `relations`를 record별로 직접 작성했다. 자동 semantic-composition, 문자열 조합 concept 생성, 명사 치환 template, relation round-robin은 사용하지 않았다. 자동화는 JSONL parse, ID 부여, corpus 포장, tokenizer·중복·문법·유사도 감사에만 사용했다.

원고는 도시 상수도의 취수·응집·침전·여과·소독·배수지·펌프·관망·계량·비상운영 사례에서 직접 원인, 물리·화학·제어 매개, 지속 배경 조건을 분리한다. 마지막에는 직접·총효과, 특정 경로 기여, 공통 원인, 합류 선택, 측정값 오인을 판정하는 기준을 별도 사례로 다뤘다. checkpoint는 `source_authoring_method: direct_model_authoring`, manual-review debt 0을 기록한다.

## 2. 구조·직렬화

| 검사 | 결과 |
|---|---:|
| source rows / corpus records | 150 / 150 |
| primary unique / text unique | 150 / 150 |
| ID first / last | `S2-CSH-00751` / `S2-CSH-00900` |
| source↔corpus projection 오류 | 0 |
| JSON/JSONL parse 오류 | 0 |
| 통제어휘 밖 relation | 0 |
| record 내부 relation 중복 | 0 |
| relation cardinality | 4개: 150 records |
| 고유 relation-set / 단일 최대 빈도 | 50 / 12 records |
| `other_type` 불일치 | 0 |

## 3. Relations 분포

총 relation 배정은 600회다.

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 49 |
| `classification` | 37 |
| `boundary` | 150 |
| `contrast` | 22 |
| `comparison` | 42 |
| `function` | 42 |
| `role` | 30 |
| `process` | 111 |
| `state` | 58 |
| `attribute` | 59 |
| `other` | 0 |

`process`가 큰 것은 직접 원인에서 중간 상태를 거쳐 결과로 이어지는 매개 경로를 명시한 family 목표와 일치한다. `boundary`는 직접·매개·배경·측정 경계를 각 record에서 판정하므로 150회다. `other`가 0회이므로 자주 나온 `other_type` 5가지는 해당 없음이다.

## 4. 중복·유사도·보일러플레이트

| 검사 | 결과 |
|---|---:|
| exact primary/text/normalized text 중복 | 0 |
| primary+relation-set 중복 | 0 |
| cross-record 5-word n-gram 반복 | 0 / 2,752 assignments |
| v06 내부 normalized character similarity ≥ 0.80 | 0 pairs |
| v06 내부 최대 character similarity | 0.480620 |
| v06 내부 word-set Jaccard ≥ 0.60 | 0 pairs |
| v06 내부 최대 word-set Jaccard | 0.194444 |
| 기존 Stage2 1,200 records 교차 character similarity ≥ 0.80 | 0 pairs |
| 기존 Stage2 교차 최대 character similarity | 0.566929 |
| 기존 Stage2 교차 word-set Jaccard ≥ 0.60 | 0 pairs |
| 기존 Stage2 교차 최대 word-set Jaccard | 0.277778 |
| generic shape fingerprint | 53종, 단일 최대 12/150 = 8.00% |

lexical 5-gram 반복과 두 fuzzy 기준의 고유사 pair는 내부·기존 Stage2 교차 비교에서 모두 0이다. 최대 교차 쌍은 서로 다른 domain에서 결론 적용범위를 제한하는 사례이며 임계값보다 충분히 낮고 객체·경로·교육내용이 다르다.

## 5. 한국어·token 감사

- exact tokenizer: `tok-ko-en-32768.json`, SHA-256 `3a69001ecc28a5bdf1e951a1036b234c9bdcb847b310252c6d72cfc6c52c48e3`
- 평균: 42.706667 tokens/record(+EOS)
- 최소/최대: 34 / 51
- Stage2 승인 평균: 41.625, 허용범위 ±10% = 37.4625~45.7875 — file mean PASS
- text 문자 길이: 최소 74, 평균 85.720, 최대 98
- hard grammar finding: 0
- 조사 휴리스틱 warning: 3

warning은 `경과와의`, `수위가`, `차이가`에 포함된 `과와`·`이가` 부분문자열을 탐지한 false positive였다. 세 경고 행을 모두 직접 읽어 조사 결합 오류가 아님을 확인했다.

## 6. 해시와 최종 판정

- source SHA-256: `5e33e2b7326cdb89f475b4cbbf8bdd43acc875a389cce2bc699df5a68381221e`
- corpus SHA-256: `24cf83987e44e738a3ffbf9b7003e524f04bfd3e0086570670ee9da4e7577fd7`
- resume checkpoint SHA-256: `62c8de911a45dcea25a27369f30f317c78940ca7242e9318249a48ead229067a`
- central ledger SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`

`--require-complete --check-only` 감사에서 source 1·corpus 1, missing 0, structural PASS, direct-authoring debt 0을 확인했다. 전체 부분 감사도 41 source/corpus pairs·6,150 records에서 구조·exact/normalized 중복·train/validation exact leakage·5-word n-gram 반복·hard grammar·manual-review debt 모두 0으로 PASS했다. Stage1·저밀도·held-out·기존 Stage2~10 pilot과 v02~v05는 수정하지 않았다.
