# TinyLM Stage2 causal_structure train v21 직접 작성 감사

- 감사일: 2026-09-02 KST
- 판정: **PASS**
- reservation: `S2-A01-T-021`
- family: `하천 저수지 수위·방류 관리 — 직접 원인·매개 경로·배경 조건 분리`
- corpus: `stage2_highdensity_dataset/train/stage2_(11)causal_structure_high_density_train_v21.json`
- source: `stage2_highdensity_dataset/sources/train/stage2_(11)causal_structure_high_density_train_v21.source.jsonl`

## 1. 작성·포장 경계

150개의 primary concept, `text`, `relations`를 record별로 직접 작성했다. 자동 semantic-composition, 명사 치환 template, relation round-robin은 사용하지 않았다. 자동화는 JSONL parse, source 계약 검사, ID·고정 metadata 부여, tokenizer·중복·문법·유사도 감사에만 사용했다.

원고는 강우·상류 방류·취수·증발·수문 개도·발전 운전이 수위와 방류량에 주는 직접 효과를 먼저 다룬다. 이어 토양포화·표면유출·하도저류·수두차·운영 결정 같은 매개 경로, 초기수위·계절수요·예보·설비상태 같은 배경 조건을 분리하고, 총효과·직접효과·매개효과의 중복 집계와 관측 편향을 막는 감사 절차를 배치했다.

최초 직접 원고는 의미 후보 162행으로 작성됐으나 source gate가 요구하는 150행을 넘어 포장을 차단했다. 앞 150행으로 교육축과 감사 절차가 닫히는 것을 확인하고 후행 보충 후보 12행은 canonical 원고에서 제외했다. 최초 file audit에서 두 record가 공유한 5-word n-gram 2종을 발견해 수질 경보 경로의 primary와 문장을 직접 재서술하고 source·corpus·checkpoint 해시를 함께 갱신했다.

## 2. 구조·직렬화

| 검사 | 결과 |
|---|---:|
| source rows / corpus records | 150 / 150 |
| primary unique / text unique | 150 / 150 |
| ID first / last | `S2-CSH-03001` / `S2-CSH-03150` |
| source↔corpus projection 오류 | 0 |
| JSON/JSONL parse 오류 | 0 |
| primary 본문 literal 누락 | 0 |
| 통제어휘 밖 relation | 0 |
| record 내부 relation 중복 | 0 |
| relation cardinality | 4개: 150 records |
| 고유 relation-set / 단일 최대 빈도 | 52 / 9 records |
| `other_type` 불일치 | 0 |

## 3. Relations 분포

총 relation 배정은 600회다.

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 41 |
| `classification` | 82 |
| `boundary` | 150 |
| `contrast` | 25 |
| `comparison` | 46 |
| `function` | 41 |
| `role` | 26 |
| `process` | 77 |
| `state` | 56 |
| `attribute` | 56 |
| `other` | 0 |

`process`는 물과 운영 신호가 중간 단계를 거쳐 결과에 이르는 경로를, `classification`은 직접 원인·매개·배경·관측 편향의 지위를, `part_of`는 총효과 안의 경로 구성분을 나타낸다. `boundary`는 원인과 조건, 직접효과와 매개효과, 물리 변화와 측정 변화를 혼동하지 않도록 모든 record에 부여했다. `other`가 0회이므로 자주 나온 `other_type` 5가지는 해당 없음이다.

## 4. 중복·유사도·보일러플레이트

| 검사 | 결과 |
|---|---:|
| exact primary/text/normalized text 중복 | 0 |
| primary+relation-set 중복 | 0 |
| v21 내부 cross-record 5-word n-gram 반복 | 0 / 2,657 assignments |
| 현행 전체 56파일 cross-record 5-word n-gram 반복 | 0 / 155,606 assignments |
| v21 내부 normalized character similarity ≥ 0.80 | 0 pairs |
| v21 내부 최대 character similarity | 0.496000 |
| v21 내부 word-set Jaccard ≥ 0.60 | 0 pairs |
| v21 내부 최대 word-set Jaccard | 0.235294 |
| 기존 Stage2 train 3,300 records 교차 character similarity ≥ 0.80 | 0 pairs |
| 기존 Stage2 train 교차 최대 character similarity | 0.478632 |
| 기존 Stage2 train 교차 word-set Jaccard ≥ 0.60 | 0 pairs |
| 기존 Stage2 train 교차 최대 word-set Jaccard | 0.190476 |
| generic shape fingerprint | 65종, 단일 최대 11/150 = 7.33% |

초기 반복 n-gram 2종을 직접 고친 뒤 lexical 5-gram, 문자 유사도, 단어집합 Jaccard에서 내부·기존 Stage2 train 교차 검토선을 넘은 pair가 없다. generic shape의 최대 점유는 7.33%이며 의미 문장 복제나 명사 치환 보일러플레이트 증거는 발견되지 않았다.

## 5. 한국어·token 감사

- exact tokenizer: `tok-ko-en-32768.json`, SHA-256 `3a69001ecc28a5bdf1e951a1036b234c9bdcb847b310252c6d72cfc6c52c48e3`
- 최종 평균: 43.000000 tokens/record(+EOS)
- 최종 최소/최대: 35 / 53
- Stage2 승인 평균: 41.625, 허용범위 ±10% = 37.4625~45.7875 — file mean PASS
- text 문자 길이: 최소 71, 평균 83.593, 최대 94
- hard grammar finding: 0
- 조사 휴리스틱 warning: 13

13개 warning 위치를 전수 읽었다. `물높이가`, `효과와`, `이동이 관측`처럼 정상 단어 내부 또는 어절 경계를 보수적으로 잡은 false positive이며 실제 조사 불일치는 없다.

## 6. 해시와 최종 판정

- source SHA-256: `9a1bde93b7143ba4d1a81cb4500b4ecb5eccbb84d6772b4b527fb4be3a7ba605`
- corpus SHA-256: `23431d014783906a1d00c077d48d707feec70964e15ca96c904de2556a95f2bf`
- resume checkpoint SHA-256: `d541cc21573b033c1858d666758590d254b31f3b6902ac92a23a83c2665ab880`
- central ledger SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`

`--require-complete --check-only` 감사에서 source 1·corpus 1, missing 0, structural PASS, direct-authoring debt 0을 확인했다. 전체 부분 감사도 56 source/corpus pairs·8,400 records에서 구조·exact/normalized 중복·train/validation exact leakage·5-word n-gram 반복·hard grammar·manual-review debt 모두 0으로 PASS했다. Stage2 누적 3,600 records의 exact tokenizer 평균은 42.817778(+EOS)으로 gate PASS다. 보호 대상 변경은 없다.

다음 예약은 `S2-A01-T-022`, `stage2_(11)causal_structure_high_density_train_v22.json`, ID `S2-CSH-03151 ~ S2-CSH-03300`, family `하천 저수지 수위·방류 관리 — 공통 원인과 거짓 상관 통제`다.
