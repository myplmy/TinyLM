# TinyLM Stage2 causal_structure train v24 직접 작성 감사

- 감사일: 2026-09-02 KST
- 판정: **PASS**
- reservation: `S2-A01-T-024`
- family: `하천 저수지 수위·방류 관리 — 개입 전후 결과와 자연 변동 구분`
- corpus: `stage2_highdensity_dataset/train/stage2_(11)causal_structure_high_density_train_v24.json`
- source: `stage2_highdensity_dataset/sources/train/stage2_(11)causal_structure_high_density_train_v24.source.jsonl`

## 1. 작성·포장 경계

150개의 primary concept, `text`, `relations`를 record별로 직접 작성했다. 자동 semantic-composition, 명사 치환 template, relation round-robin은 사용하지 않았다. 자동화는 JSONL parse, source 계약 검사, ID·고정 metadata 부여, tokenizer·중복·문법·유사도 감사에만 사용했다.

원고는 수문·펌프·취수·준설·수질처리·생태복원·계측·정책 개입 전후의 결과를 강우, 계절, 기온, 조석, 초기수위, 사건세기 같은 자연 변동과 분리한다. 이어 짝짓기, 합성대조, 차분, 중단·불연속·사건시간 분석, 위약·음성대조·강건성·민감도 검사와 간섭·선취·회귀평균·결측·후처치 조정 오류를 감사한다.

source gate는 최초 150행에서 JSONL·primary literal·relations·tokenizer 계약을 모두 통과했다. file audit와 전체 partial audit에서도 반복 5-word n-gram이 발견되지 않아 사후 문장 수정은 없었다.

## 2. 구조·직렬화

| 검사 | 결과 |
|---|---:|
| source rows / corpus records | 150 / 150 |
| primary unique / text unique | 150 / 150 |
| ID first / last | `S2-CSH-03451` / `S2-CSH-03600` |
| source↔corpus projection 오류 | 0 |
| JSON/JSONL parse 오류 | 0 |
| primary 본문 literal 누락 | 0 |
| 통제어휘 밖 relation | 0 |
| record 내부 relation 중복 | 0 |
| relation cardinality | 4개: 150 records |
| 고유 relation-set / 단일 최대 빈도 | 37 / 14 records |
| `other_type` 불일치 | 0 |

## 3. Relations 분포

총 relation 배정은 600회다.

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 21 |
| `classification` | 70 |
| `boundary` | 150 |
| `contrast` | 19 |
| `comparison` | 132 |
| `function` | 28 |
| `role` | 33 |
| `process` | 56 |
| `state` | 44 |
| `attribute` | 47 |
| `other` | 0 |

`comparison`은 전후·대조·짝짓기·강건성 검사를, `classification`은 개입·자연변동·편향·설계 지위를, `process`는 즉시·지연·잔류 효과의 시간 경로를 나타낸다. `boundary`는 단순 전후 차이와 개입효과, 처치 후 매개와 사전 교란을 혼동하지 않도록 모든 record에 부여했다. `other`가 0회이므로 자주 나온 `other_type` 5가지는 해당 없음이다.

## 4. 중복·유사도·보일러플레이트

| 검사 | 결과 |
|---|---:|
| exact primary/text/normalized text 중복 | 0 |
| primary+relation-set 중복 | 0 |
| v24 내부 cross-record 5-word n-gram 반복 | 0 / 2,304 assignments |
| 현행 전체 59파일 cross-record 5-word n-gram 반복 | 0 / 163,106 assignments |
| v24 내부 normalized character similarity ≥ 0.80 | 0 pairs |
| v24 내부 최대 character similarity | 0.532258 |
| v24 내부 word-set Jaccard ≥ 0.60 | 0 pairs |
| v24 내부 최대 word-set Jaccard | 0.258065 |
| 기존 Stage2 train 3,750 records 교차 character similarity ≥ 0.80 | 0 pairs |
| 기존 Stage2 train 교차 최대 character similarity | 0.480620 |
| 기존 Stage2 train 교차 word-set Jaccard ≥ 0.60 | 0 pairs |
| 기존 Stage2 train 교차 최대 word-set Jaccard | 0.216216 |
| generic shape fingerprint | 88종, 단일 최대 11/150 = 7.33% |

lexical 5-gram, 문자 유사도, 단어집합 Jaccard에서 내부·기존 Stage2 train 교차 검토선을 넘은 pair가 없다. generic shape의 최대 점유는 7.33%이며 의미 문장 복제나 명사 치환 보일러플레이트 증거는 발견되지 않았다.

## 5. 한국어·token 감사

- exact tokenizer: `tok-ko-en-32768.json`, SHA-256 `3a69001ecc28a5bdf1e951a1036b234c9bdcb847b310252c6d72cfc6c52c48e3`
- 최종 평균: 42.906667 tokens/record(+EOS)
- 최종 최소/최대: 35 / 50
- Stage2 승인 평균: 41.625, 허용범위 ±10% = 37.4625~45.7875 — file mean PASS
- text 문자 길이: 최소 72, 평균 80.780, 최대 95
- hard grammar finding: 0
- 조사 휴리스틱 warning: 54

54개 warning 위치를 전수 읽었다. `효과와`, `결과와`, `차이가`처럼 개입효과 비교 문장에 정상적으로 쓰인 단어 내부를 보수적으로 잡은 false positive이며 실제 조사 불일치는 없다.

## 6. 해시와 최종 판정

- source SHA-256: `78dc0d16450c6dd66ce507f0e48ea2087c2a346edadc48fd40226f31303bf185`
- corpus SHA-256: `a6f338dd6b386e3e000462a15a21938b2163798ca783fa0b97fe8798e9890e82`
- resume checkpoint SHA-256: `82b3457a11cde8e7414fb7be33065d9ba74153409d9fef3be770a626d113b00d`
- central ledger SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`

`--require-complete --check-only` 감사에서 source 1·corpus 1, missing 0, structural PASS, direct-authoring debt 0을 확인했다. 전체 부분 감사도 59 source/corpus pairs·8,850 records에서 구조·exact/normalized 중복·train/validation exact leakage·5-word n-gram 반복·hard grammar·manual-review debt 모두 0으로 PASS했다. Stage2 누적 4,050 records의 exact tokenizer 평균은 42.904198(+EOS)으로 gate PASS다. 보호 대상 변경은 없다.

다음 예약은 `S2-A01-T-025`, `stage2_(11)causal_structure_high_density_train_v25.json`, ID `S2-CSH-03601 ~ S2-CSH-03750`, family `하천 저수지 수위·방류 관리 — 다중 원인의 충분성·기여 범위`다.
