# TinyLM Stage2 causal_structure train v02 직접 작성 감사

- 감사일: 2026-09-02 KST
- 판정: **PASS**
- reservation: `S2-A01-T-002`
- family: `스마트 온실 관수·환경제어 — 공통 원인과 거짓 상관 통제`
- corpus: `stage2_highdensity_dataset/train/stage2_(11)causal_structure_high_density_train_v02.json`
- source: `stage2_highdensity_dataset/sources/train/stage2_(11)causal_structure_high_density_train_v02.source.jsonl`

## 1. 작성·포장 경계

150개의 primary concept, `text`, `relations`를 record별로 직접 작성했다. 문자열 조합, 명사 치환 template, relation round-robin, semantic-composition generator를 사용하지 않았다. 자동화는 JSONL parse, ID 부여, corpus JSON 포장, tokenizer·중복·문법 감사에만 사용했다.

자동 초안 provenance는 0행이며 generator manual-review debt도 0이다. 직접 작성 source가 존재하는 상태에서 packager가 `S2-CSH-00151 ~ S2-CSH-00300`을 부여했고 기존 파일은 덮어쓰지 않았다.

## 2. 구조·직렬화

| 검사 | 결과 |
|---|---:|
| source rows / corpus records | 150 / 150 |
| primary unique / text unique | 150 / 150 |
| ID first / last | `S2-CSH-00151` / `S2-CSH-00300` |
| source↔corpus projection 오류 | 0 |
| JSON/JSONL parse 오류 | 0 |
| 통제어휘 밖 relation | 0 |
| record 내부 relation 중복 | 0 |
| relation cardinality | 3개: 27 records, 4개: 123 records |
| `other_type` 불일치 | 0 |

## 3. Relations 분포

총 relation 배정은 573회다.

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 1 |
| `classification` | 28 |
| `boundary` | 150 |
| `contrast` | 16 |
| `comparison` | 107 |
| `function` | 29 |
| `role` | 9 |
| `process` | 95 |
| `state` | 58 |
| `attribute` | 80 |
| `other` | 0 |

이 family는 모든 record가 관찰 상관과 인과의 경계를 판정하므로 `boundary` 150회가 의미상 필수다. 모든 relation을 균등하게 채우지 않았으며, `is_a`·`subclass_of`처럼 문장이 뒷받침하지 않는 label은 넣지 않았다.

`other`가 0회이므로 자주 나온 `other_type` 5가지는 해당 없음이다.

## 4. 중복·유사도·보일러플레이트

| 검사 | 결과 |
|---|---:|
| exact primary/text/normalized text 중복 | 0 |
| cross-record 5-word n-gram 반복 | 0 / 2,998 assignments |
| pairwise normalized character similarity ≥ 0.80 | 0 pairs |
| pairwise word-set Jaccard ≥ 0.60 | 0 pairs |
| 최대 character similarity | 0.5041 |
| 최대 word-set Jaccard | 0.2941 |
| generic shape fingerprint | 60종, 단일 최대 10/150 = 6.67% |

generic fingerprint는 어절 수와 문장부호 형태만 남긴 거친 경고 지표다. lexical 5-gram 반복 0과 pairwise 유사도 결과를 함께 보면 명사만 바꾼 동일 문장 template의 증거는 없다.

## 5. 한국어·token 감사

- exact tokenizer: `tok-ko-en-32768.json`, SHA-256 `3a69001ecc28a5bdf1e951a1036b234c9bdcb847b310252c6d72cfc6c52c48e3`
- 평균: 45.206667 tokens/record(+EOS)
- 최소/최대: 38 / 53
- Stage2 승인 평균: 41.625, 허용범위 ±10% = 37.4625~45.7875 — PASS
- hard grammar finding: 0
- 조사 휴리스틱 warning: 10

warning 10건은 `효과와`, `차이가`, `역인과를` 안의 `과와`·`이가` 부분문자열을 탐지한 false positive였다. 해당 10행을 직접 읽어 조사 결합 오류가 아님을 확인했다.

## 6. 해시와 최종 판정

- source SHA-256: `6f42ea7f6aa8454e8e493c8da62bbc173a1b22b4312a3057cd30d0c27c22462b`
- corpus SHA-256: `fc79cf4a8f517af10c911e1b6d8d88eb6c070a99fc3a846d435c750f43aa41f0`
- central ledger SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`
- resume checkpoint SHA-256: `422cdaa61b3aaf5998f357c018d890873c49015c0723d04db99685dcd2a72bcf`

checkpoint의 completed entry는 `source_authoring_method: direct_model_authoring`과 manual-review debt 0을 명시한다. 상단 generator 필드는 packager가 가진 격리 초안 기능을 식별할 뿐 이 source의 저자 방식을 뜻하지 않는다.

`--require-complete --check-only` 감사에서 source 1·corpus 1, missing 0, structural PASS, direct-authoring debt 0을 확인했다. Stage1·저밀도·held-out·기존 Stage2~10 pilot은 수정하지 않았다.
