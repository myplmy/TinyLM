# TinyLM Stage2 causal_structure train v03 직접 작성 감사

- 감사일: 2026-09-02 KST
- 판정: **PASS**
- reservation: `S2-A01-T-003`
- family: `스마트 온실 관수·환경제어 — 원인 방향·피드백·역인과 판정`
- corpus: `stage2_highdensity_dataset/train/stage2_(11)causal_structure_high_density_train_v03.json`
- source: `stage2_highdensity_dataset/sources/train/stage2_(11)causal_structure_high_density_train_v03.source.jsonl`

## 1. 작성·포장 경계

150개의 primary concept, `text`, `relations`를 record별로 직접 작성했다. 자동 semantic-composition, 문자열 조합 concept 생성, 명사 치환 template, relation round-robin은 사용하지 않았다. 자동화는 JSONL parse, ID 부여, corpus 포장, tokenizer·중복·문법·유사도 감사에만 사용했다.

원고는 관수·환기·난방·차광·양액 제어에서 원인 방향, 센서·장치 지연, 작물 상태가 처방을 부르는 역인과, 음·양의 피드백과 폐루프 검증을 서로 다른 사례로 다룬다. checkpoint는 `source_authoring_method: direct_model_authoring`, manual-review debt 0을 기록한다.

## 2. 구조·직렬화

| 검사 | 결과 |
|---|---:|
| source rows / corpus records | 150 / 150 |
| primary unique / text unique | 150 / 150 |
| ID first / last | `S2-CSH-00301` / `S2-CSH-00450` |
| source↔corpus projection 오류 | 0 |
| JSON/JSONL parse 오류 | 0 |
| 통제어휘 밖 relation | 0 |
| record 내부 relation 중복 | 0 |
| relation cardinality | 4개: 150 records |
| 고유 relation-set / 단일 최대 빈도 | 45 / 15 records |
| `other_type` 불일치 | 0 |

## 3. Relations 분포

총 relation 배정은 600회다.

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 15 |
| `classification` | 35 |
| `boundary` | 147 |
| `contrast` | 17 |
| `comparison` | 72 |
| `function` | 64 |
| `role` | 32 |
| `process` | 126 |
| `state` | 46 |
| `attribute` | 46 |
| `other` | 0 |

`boundary`와 `process`가 큰 것은 같은 두 변수의 입력 방향과 후행 결과 방향을 분리하고 시간에 따른 폐루프를 기술하는 family 목표와 일치한다. 문장이 뒷받침하지 않는 `is_a`·`subclass_of`는 넣지 않았다. `other`가 0회이므로 자주 나온 `other_type` 5가지는 해당 없음이다.

## 4. 중복·유사도·보일러플레이트

| 검사 | 결과 |
|---|---:|
| exact primary/text/normalized text 중복 | 0 |
| primary+relation-set 중복 | 0 |
| cross-record 5-word n-gram 반복 | 0 / 2,924 assignments |
| v03 내부 normalized character similarity ≥ 0.80 | 0 pairs |
| v03 내부 최대 character similarity | 0.400000 |
| v03 내부 word-set Jaccard ≥ 0.60 | 0 pairs |
| v03 내부 최대 word-set Jaccard | 0.205128 |
| 기존 Stage2 750 records 교차 character similarity ≥ 0.80 | 0 pairs |
| 기존 Stage2 교차 최대 character similarity | 0.357724 |
| 기존 Stage2 교차 word-set Jaccard ≥ 0.60 | 0 pairs |
| 기존 Stage2 교차 최대 word-set Jaccard | 0.216216 |
| generic shape fingerprint | 59종, 단일 최대 10/150 = 6.67% |

동일한 relation 개수는 schema 위반이 아니며, relation-set은 45종이고 최다 조합도 15/150이다. lexical 5-gram 반복과 fuzzy 고유사 pair가 모두 0이므로 명사만 바꾼 보일러플레이트 증거는 없다.

## 5. 한국어·token 감사

- exact tokenizer: `tok-ko-en-32768.json`, SHA-256 `3a69001ecc28a5bdf1e951a1036b234c9bdcb847b310252c6d72cfc6c52c48e3`
- 평균: 44.006667 tokens/record(+EOS)
- 최소/최대: 34 / 54
- Stage2 승인 평균: 41.625, 허용범위 ±10% = 37.4625~45.7875 — file mean PASS
- text 문자 길이: 최소 78, 평균 88.167, 최대 99
- hard grammar finding: 0
- 조사 휴리스틱 warning: 11

warning은 `곰팡이가`, `차이가`, `효과와`, `처방과` 등에 포함된 `이가`·`과와` 부분문자열을 탐지한 false positive였다. 경고 행을 직접 읽어 조사 결합 오류가 아님을 확인했다.

## 6. 해시와 최종 판정

- source SHA-256: `5f9204f90df46126f884b22b6438363d095e545439a8afaac2410fa750f97b6e`
- corpus SHA-256: `27178ea8e46f638b94b0bc86dc92855cf87d6df3899367f77a21cf6d55a7172f`
- resume checkpoint SHA-256: `97d3df219623ca1c2ebbea4a3444bf85beb49ec898fbb05349377c39e23dc550`
- central ledger SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`

`--require-complete --check-only` 감사에서 source 1·corpus 1, missing 0, structural PASS, direct-authoring debt 0을 확인했다. Stage1·저밀도·held-out·기존 Stage2~10 pilot과 v02는 수정하지 않았다.
