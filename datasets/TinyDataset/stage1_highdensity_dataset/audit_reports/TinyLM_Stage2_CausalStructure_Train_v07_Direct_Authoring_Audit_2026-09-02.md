# TinyLM Stage2 causal_structure train v07 직접 작성 감사

- 감사일: 2026-09-02 KST
- 판정: **PASS**
- reservation: `S2-A01-T-007`
- family: `도시 상수도 정수·배수 운영 — 공통 원인과 거짓 상관 통제`
- corpus: `stage2_highdensity_dataset/train/stage2_(11)causal_structure_high_density_train_v07.json`
- source: `stage2_highdensity_dataset/sources/train/stage2_(11)causal_structure_high_density_train_v07.source.jsonl`

## 1. 작성·포장 경계

150개의 primary concept, `text`, `relations`를 record별로 직접 작성했다. 자동 semantic-composition, 문자열 조합 concept 생성, 명사 치환 template, relation round-robin은 사용하지 않았다. 자동화는 JSONL parse, ID 부여, corpus 포장, tokenizer·중복·문법·유사도 감사에만 사용했다.

원고는 상수도 취수·처리·소독·송배수·수요·관망·계측·정비·재난 자료에서 날씨, 원수 상태, 수요, 표고, 설비 노후, 대응 행동, 측정 방법, 표본 선택이 두 관측값을 함께 움직이는 공통 원인 사례를 다룬다. 대응 처방의 역인과, 경보기간·취약지 선택, 합류 조건, 공통 측정방법을 별도 경계로 구성했다. checkpoint는 `source_authoring_method: direct_model_authoring`, manual-review debt 0을 기록한다.

## 2. 구조·직렬화

| 검사 | 결과 |
|---|---:|
| source rows / corpus records | 150 / 150 |
| primary unique / text unique | 150 / 150 |
| ID first / last | `S2-CSH-00901` / `S2-CSH-01050` |
| source↔corpus projection 오류 | 0 |
| JSON/JSONL parse 오류 | 0 |
| 통제어휘 밖 relation | 0 |
| record 내부 relation 중복 | 0 |
| relation cardinality | 4개: 150 records |
| 고유 relation-set / 단일 최대 빈도 | 61 / 10 records |
| `other_type` 불일치 | 0 |

## 3. Relations 분포

총 relation 배정은 600회다.

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 53 |
| `classification` | 53 |
| `boundary` | 150 |
| `contrast` | 32 |
| `comparison` | 64 |
| `function` | 18 |
| `role` | 54 |
| `process` | 75 |
| `state` | 52 |
| `attribute` | 49 |
| `other` | 0 |

`role`은 운영자 대응, 검사·표본 선택, 측정자 효과가 거짓 상관을 만드는 경우에 사용했다. `classification`은 공통 원인·선택 편향·측정 오류의 판정 유형을 명시한 문장에 붙였다. `other`가 0회이므로 자주 나온 `other_type` 5가지는 해당 없음이다.

## 4. 중복·유사도·보일러플레이트

| 검사 | 결과 |
|---|---:|
| exact primary/text/normalized text 중복 | 0 |
| primary+relation-set 중복 | 0 |
| cross-record 5-word n-gram 반복 | 0 / 2,685 assignments |
| v07 내부 normalized character similarity ≥ 0.80 | 0 pairs |
| v07 내부 최대 character similarity | 0.507937 |
| v07 내부 word-set Jaccard ≥ 0.60 | 0 pairs |
| v07 내부 최대 word-set Jaccard | 0.281250 |
| 기존 Stage2 1,350 records 교차 character similarity ≥ 0.80 | 0 pairs |
| 기존 Stage2 교차 최대 character similarity | 0.522388 |
| 기존 Stage2 교차 word-set Jaccard ≥ 0.60 | 0 pairs |
| 기존 Stage2 교차 최대 word-set Jaccard | 0.216216 |
| generic shape fingerprint | 57종, 단일 최대 13/150 = 8.67% |

초기 감사에서 두 영문 `pH` primary 뒤 조사 gate 2건과 5-word n-gram 반복 2종을 발견해 네 문장을 직접 고쳤다. 최종 lexical 5-gram 반복과 두 fuzzy 기준의 고유사 pair는 내부·기존 Stage2 교차 비교에서 모두 0이다.

## 5. 한국어·token 감사

- exact tokenizer: `tok-ko-en-32768.json`, SHA-256 `3a69001ecc28a5bdf1e951a1036b234c9bdcb847b310252c6d72cfc6c52c48e3`
- 평균: 43.240000 tokens/record(+EOS)
- 최소/최대: 37 / 53
- Stage2 승인 평균: 41.625, 허용범위 ±10% = 37.4625~45.7875 — file mean PASS
- text 문자 길이: 최소 69, 평균 85.140, 최대 97
- hard grammar finding: 0
- 조사 휴리스틱 warning: 7

최종 warning은 `결과가`, `높이가`, `차이가`, `효과와` 등에 포함된 `이가`·`과와` 부분문자열을 탐지한 false positive였다. 7개 경고 행을 모두 직접 읽어 조사 결합 오류가 아님을 확인했다.

## 6. 해시와 최종 판정

- source SHA-256: `dbbc550b3bd22bc75bd5ea7a73a6b9cea2632ed78032cf34867770729d77243e`
- corpus SHA-256: `e582739ea181d496b8db1d6a89f784e8ea92b0e0d627b0275f3c516b52f52e92`
- resume checkpoint SHA-256: `5616a83112b3698e4e6ef96ff7cce48da09e2089e2c9b9d9376f37361737b8b5`
- central ledger SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`

`--require-complete --check-only` 감사에서 source 1·corpus 1, missing 0, structural PASS, direct-authoring debt 0을 확인했다. 전체 부분 감사도 42 source/corpus pairs·6,300 records에서 구조·exact/normalized 중복·train/validation exact leakage·5-word n-gram 반복·hard grammar·manual-review debt 모두 0으로 PASS했다. Stage1·저밀도·held-out·기존 Stage2~10 pilot과 v02~v06은 수정하지 않았다.
