# TinyLM Stage2 causal_structure train v05 직접 작성 감사

- 감사일: 2026-09-02 KST
- 판정: **PASS**
- reservation: `S2-A01-T-005`
- family: `스마트 온실 관수·환경제어 — 다중 원인의 충분성·기여 범위`
- corpus: `stage2_highdensity_dataset/train/stage2_(11)causal_structure_high_density_train_v05.json`
- source: `stage2_highdensity_dataset/sources/train/stage2_(11)causal_structure_high_density_train_v05.source.jsonl`

## 1. 작성·포장 경계

150개의 primary concept, `text`, `relations`를 record별로 직접 작성했다. 자동 semantic-composition, 문자열 조합 concept 생성, 명사 치환 template, relation round-robin은 사용하지 않았다. 자동화는 JSONL parse, ID 부여, corpus 포장, tokenizer·중복·문법·유사도 감사에만 사용했다.

원고는 스마트 온실의 수분·열·습도·병해·광합성·양액·생산·에너지·제어 사례에서 필요조건과 충분조건, 공동·대체 원인, 직렬 병목, 포화·상쇄·상호작용, 반사실 기여, 설명 몫의 하한·상한을 구분한다. checkpoint는 `source_authoring_method: direct_model_authoring`, manual-review debt 0을 기록한다.

## 2. 구조·직렬화

| 검사 | 결과 |
|---|---:|
| source rows / corpus records | 150 / 150 |
| primary unique / text unique | 150 / 150 |
| ID first / last | `S2-CSH-00601` / `S2-CSH-00750` |
| source↔corpus projection 오류 | 0 |
| JSON/JSONL parse 오류 | 0 |
| 통제어휘 밖 relation | 0 |
| record 내부 relation 중복 | 0 |
| relation cardinality | 4개: 150 records |
| 고유 relation-set / 단일 최대 빈도 | 47 / 8 records |
| `other_type` 불일치 | 0 |

## 3. Relations 분포

총 relation 배정은 600회다.

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 56 |
| `classification` | 55 |
| `boundary` | 150 |
| `contrast` | 29 |
| `comparison` | 96 |
| `function` | 34 |
| `role` | 15 |
| `process` | 64 |
| `state` | 47 |
| `attribute` | 54 |
| `other` | 0 |

`boundary`는 필요·충분·유일 원인과 단순 동행의 경계를 매 record에서 명시하므로 150회다. `comparison`, `part_of`, `classification`은 기여 크기, 공동 원인 구성, 원인 유형을 실제로 기술한 문장에만 붙였다. `other`가 0회이므로 자주 나온 `other_type` 5가지는 해당 없음이다.

## 4. 중복·유사도·보일러플레이트

| 검사 | 결과 |
|---|---:|
| exact primary/text/normalized text 중복 | 0 |
| primary+relation-set 중복 | 0 |
| cross-record 5-word n-gram 반복 | 0 / 2,799 assignments |
| v05 내부 normalized character similarity ≥ 0.80 | 0 pairs |
| v05 내부 최대 character similarity | 0.556522 |
| v05 내부 word-set Jaccard ≥ 0.60 | 0 pairs |
| v05 내부 최대 word-set Jaccard | 0.264706 |
| 기존 Stage2 1,050 records 교차 character similarity ≥ 0.80 | 0 pairs |
| 기존 Stage2 교차 최대 character similarity | 0.396552 |
| 기존 Stage2 교차 word-set Jaccard ≥ 0.60 | 0 pairs |
| 기존 Stage2 교차 최대 word-set Jaccard | 0.200000 |
| generic shape fingerprint | 80종, 단일 최대 10/150 = 6.67% |

초기 감사에서 두 record가 공유한 5-word n-gram 1종을 발견해 한 문장을 직접 고쳐 재감사했다. 최종 lexical 5-gram 반복과 두 fuzzy 기준의 고유사 pair는 내부·기존 Stage2 교차 비교에서 모두 0이다.

## 5. 한국어·token 감사

- exact tokenizer: `tok-ko-en-32768.json`, SHA-256 `3a69001ecc28a5bdf1e951a1036b234c9bdcb847b310252c6d72cfc6c52c48e3`
- 평균: 41.966667 tokens/record(+EOS)
- 최소/최대: 36 / 48
- Stage2 승인 평균: 41.625, 허용범위 ±10% = 37.4625~45.7875 — file mean PASS
- text 문자 길이: 최소 76, 평균 85.113, 최대 99
- hard grammar finding: 0
- 조사 휴리스틱 warning: 11

warning은 `차이가`, `효과와`, `환기가` 등에 포함된 `이가`·`과와` 부분문자열을 탐지한 false positive였다. 11개 경고 행을 모두 직접 읽어 조사 결합 오류가 아님을 확인했다.

## 6. 해시와 최종 판정

- source SHA-256: `a56d13b66864e266f36625f5eda0809de24875ab630558a0cdaaf9a1f25285eb`
- corpus SHA-256: `2136848cc541e3511d2ce8443bfd85c43a745bc720d8ddb1fc7932bb9ab6add9`
- resume checkpoint SHA-256: `274b6cb74598ab7d12c2f268f9e5ef9f23ca8c8766d95b22e68ccb4b79e2e83e`
- central ledger SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`

`--require-complete --check-only` 감사에서 source 1·corpus 1, missing 0, structural PASS, direct-authoring debt 0을 확인했다. 전체 부분 감사도 40 source/corpus pairs·6,000 records에서 구조·exact/normalized 중복·train/validation exact leakage·5-word n-gram 반복·hard grammar·manual-review debt 모두 0으로 PASS했다. Stage1·저밀도·held-out·기존 Stage2~10 pilot과 v02~v04는 수정하지 않았다.
