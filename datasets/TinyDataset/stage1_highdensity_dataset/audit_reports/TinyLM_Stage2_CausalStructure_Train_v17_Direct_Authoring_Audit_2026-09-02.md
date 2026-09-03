# TinyLM Stage2 causal_structure train v17 직접 작성 감사

- 감사일: 2026-09-02 KST
- 판정: **PASS**
- reservation: `S2-A01-T-017`
- family: `철도 운행 간격·환승 조정 — 공통 원인과 거짓 상관 통제`
- corpus: `stage2_highdensity_dataset/train/stage2_(11)causal_structure_high_density_train_v17.json`
- source: `stage2_highdensity_dataset/sources/train/stage2_(11)causal_structure_high_density_train_v17.source.jsonl`

## 1. 작성·포장 경계

150개의 primary concept, `text`, `relations`를 record별로 직접 작성했다. 자동 semantic-composition, 명사 치환 template, relation round-robin은 사용하지 않았다. 자동화는 JSONL parse, source 계약 검사, ID·고정 metadata 부여, tokenizer·중복·문법·유사도 감사에만 사용했다.

원고는 철도 지연과 환승 결과를 함께 움직이는 수요·달력·기상·시설·관제·차량·인력 요인을 구분한다. 후반부에는 집계·결측·선택·충돌 변수 편향, 층화·매칭·고정효과·부정 대조·위약 검정·자연실험·차이의 차이·인과 그래프와 잔여 교란 보고를 배치했다.

최초 포장 감사에서 두 primary의 공통 말미가 만든 파일 내부 5-gram 1종과 v12 문장의 표현과 겹친 누적 5-gram 1종을 발견했다. 한 primary 및 본문과 다른 본문을 직접 재서술하고 source·corpus·체크포인트 해시를 함께 갱신했다. 최종 파일 내부와 전체 누적 반복은 모두 0건이다.

## 2. 구조·직렬화

| 검사 | 결과 |
|---|---:|
| source rows / corpus records | 150 / 150 |
| primary unique / text unique | 150 / 150 |
| ID first / last | `S2-CSH-02401` / `S2-CSH-02550` |
| source↔corpus projection 오류 | 0 |
| JSON/JSONL parse 오류 | 0 |
| primary 본문 literal 누락 | 0 |
| 통제어휘 밖 relation | 0 |
| record 내부 relation 중복 | 0 |
| relation cardinality | 4개: 150 records |
| 고유 relation-set / 단일 최대 빈도 | 56 / 9 records |
| `other_type` 불일치 | 0 |

## 3. Relations 분포

총 relation 배정은 600회다.

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 35 |
| `classification` | 84 |
| `boundary` | 150 |
| `contrast` | 38 |
| `comparison` | 73 |
| `function` | 38 |
| `role` | 27 |
| `process` | 50 |
| `state` | 49 |
| `attribute` | 56 |
| `other` | 0 |

`classification`은 공통 원인·교란·선택·충돌 변수와 검증 방법의 역할을, `comparison`과 `contrast`는 층화 전후·대조군·역전·인과와 상관의 차이를 나타낸다. `boundary`는 공변동을 직접 인과로 바꾸지 않도록 모든 레코드에 부여했다. `other`가 0회이므로 자주 나온 `other_type` 5가지는 해당 없음이다.

## 4. 중복·유사도·보일러플레이트

| 검사 | 결과 |
|---|---:|
| exact primary/text/normalized text 중복 | 0 |
| primary+relation-set 중복 | 0 |
| v17 내부 cross-record 5-word n-gram 반복 | 0 / 3,261 assignments |
| 현행 전체 52파일 cross-record 5-word n-gram 반복 | 0 / 144,646 assignments |
| v17 내부 normalized character similarity ≥ 0.80 | 0 pairs |
| v17 내부 최대 character similarity | 0.431655 |
| v17 내부 word-set Jaccard ≥ 0.60 | 0 pairs |
| v17 내부 최대 word-set Jaccard | 0.200000 |
| 기존 Stage2 train 2,700 records 교차 character similarity ≥ 0.80 | 0 pairs |
| 기존 Stage2 train 교차 최대 character similarity | 0.437956 |
| 기존 Stage2 train 교차 word-set Jaccard ≥ 0.60 | 0 pairs |
| 기존 Stage2 train 교차 최대 word-set Jaccard | 0.184211 |
| generic shape fingerprint | 61종, 단일 최대 9/150 = 6.00% |

최초 탐지 2종을 직접 수정한 뒤 lexical 5-gram, 문자 유사도, 단어집합 Jaccard에서 내부·기존 Stage2 train 교차 검토선을 넘은 pair가 없다. generic shape 최대 비율도 낮으며 의미 문장 복제나 명사 치환 보일러플레이트 증거는 발견되지 않았다.

## 5. 한국어·token 감사

- exact tokenizer: `tok-ko-en-32768.json`, SHA-256 `3a69001ecc28a5bdf1e951a1036b234c9bdcb847b310252c6d72cfc6c52c48e3`
- 평균: 45.733333 tokens/record(+EOS)
- 최소/최대: 38 / 54
- Stage2 승인 평균: 41.625, 허용범위 ±10% = 37.4625~45.7875 — file mean PASS
- text 문자 길이: 최소 87, 평균 96.707, 최대 108
- hard grammar finding: 0
- 조사 휴리스틱 warning: 4

4개 warning 행을 직접 읽었다. 모두 정상 단어 `효과와` 내부의 부분문자열을 조사 의심 패턴으로 잡은 false positive이며 실제 조사 불일치는 없다.

## 6. 해시와 최종 판정

- source SHA-256: `56df9cf1f9131acc345582aad8cdd8556bccaedf8ad3e67da729ea9f9ff91980`
- corpus SHA-256: `9080211e8cfd5428366dbe6d198b13d8ae71a18ee2fdf4dc8ab421317da9aa2c`
- resume checkpoint SHA-256: `44d886e41b14354f47b1afa60041cabc88c0d98731a30d2007500451fdc48af0`
- central ledger SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`

`--require-complete --check-only` 감사에서 source 1·corpus 1, missing 0, structural PASS, direct-authoring debt 0을 확인했다. 전체 부분 감사도 52 source/corpus pairs·7,800 records에서 구조·exact/normalized 중복·train/validation exact leakage·5-word n-gram 반복·hard grammar·manual-review debt 모두 0으로 PASS했다. Stage2 누적 3,000 records의 exact tokenizer 평균은 42.993333(+EOS)으로 gate PASS다. 보호 대상 변경은 없다.

다음 예약은 `S2-A01-T-018`, `stage2_(11)causal_structure_high_density_train_v18.json`, ID `S2-CSH-02551 ~ S2-CSH-02700`, family `철도 운행 간격·환승 조정 — 원인 방향·피드백·역인과 판정`이다.
