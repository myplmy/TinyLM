# TinyLM Stage2 causal_structure train v20 직접 작성 감사

- 감사일: 2026-09-02 KST
- 판정: **PASS**
- reservation: `S2-A01-T-020`
- family: `철도 운행 간격·환승 조정 — 다중 원인의 충분성·기여 범위`
- corpus: `stage2_highdensity_dataset/train/stage2_(11)causal_structure_high_density_train_v20.json`
- source: `stage2_highdensity_dataset/sources/train/stage2_(11)causal_structure_high_density_train_v20.source.jsonl`

## 1. 작성·포장 경계

150개의 primary concept, `text`, `relations`를 record별로 직접 작성했다. 자동 semantic-composition, 명사 치환 template, relation round-robin은 사용하지 않았다. 자동화는 JSONL parse, source 계약 검사, ID·고정 metadata 부여, tokenizer·중복·문법·유사도 감사에만 사용했다.

원고는 철도 장애·지연·환승 실패를 만드는 공동 충분조건, 최소 충분 집합, 대체 경로와 중복 원인을 먼저 다룬다. 이어 결과 발생확률·지연분·승객시간·네트워크 전파분의 기여를 분해하고, 비선형 임계·시너지·상쇄, 시간·공간·승객군·운행상태별 적용범위, 최소성·대체경로·중복배분·측정편향 감사를 배치했다.

최초 직접 원고는 의미 후보 171행으로 작성됐으나 source gate가 요구하는 150행을 넘어 포장을 차단했다. 앞 150행만으로 교육축과 감사 절차가 닫히는 것을 확인하고 중복 성격의 후행 감사 후보 21행은 canonical 원고에서 제외했다. 최초 file audit에서 반복 5-word n-gram 1종을 발견해 135번 문장을 직접 재서술하고 source·corpus·checkpoint 해시를 함께 갱신했다.

## 2. 구조·직렬화

| 검사 | 결과 |
|---|---:|
| source rows / corpus records | 150 / 150 |
| primary unique / text unique | 150 / 150 |
| ID first / last | `S2-CSH-02851` / `S2-CSH-03000` |
| source↔corpus projection 오류 | 0 |
| JSON/JSONL parse 오류 | 0 |
| primary 본문 literal 누락 | 0 |
| 통제어휘 밖 relation | 0 |
| record 내부 relation 중복 | 0 |
| relation cardinality | 4개: 150 records |
| 고유 relation-set / 단일 최대 빈도 | 58 / 11 records |
| `other_type` 불일치 | 0 |

## 3. Relations 분포

총 relation 배정은 600회다.

| relation | 횟수 |
|---|---:|
| `is_a` | 1 |
| `subclass_of` | 0 |
| `part_of` | 48 |
| `classification` | 69 |
| `boundary` | 150 |
| `contrast` | 48 |
| `comparison` | 81 |
| `function` | 33 |
| `role` | 23 |
| `process` | 36 |
| `state` | 42 |
| `attribute` | 69 |
| `other` | 0 |

`part_of`는 충분 원인 집합 안의 구성 기여를, `comparison`은 원인 제거 반사실과 기여량 차이를, `classification`은 필요·충분·대체·상호작용·적용범위 판정을 나타낸다. `boundary`는 단독 원인과 원인 집합, 빈도와 인과 기여, 기여도와 책임 귀속을 혼동하지 않도록 모든 레코드에 부여했다. `other`가 0회이므로 자주 나온 `other_type` 5가지는 해당 없음이다.

## 4. 중복·유사도·보일러플레이트

| 검사 | 결과 |
|---|---:|
| exact primary/text/normalized text 중복 | 0 |
| primary+relation-set 중복 | 0 |
| v20 내부 cross-record 5-word n-gram 반복 | 0 / 2,735 assignments |
| 현행 전체 55파일 cross-record 5-word n-gram 반복 | 0 / 152,949 assignments |
| v20 내부 normalized character similarity ≥ 0.80 | 0 pairs |
| v20 내부 최대 character similarity | 0.495726 |
| v20 내부 word-set Jaccard ≥ 0.60 | 0 pairs |
| v20 내부 최대 word-set Jaccard | 0.256410 |
| 기존 Stage2 train 3,150 records 교차 character similarity ≥ 0.80 | 0 pairs |
| 기존 Stage2 train 교차 최대 character similarity | 0.507937 |
| 기존 Stage2 train 교차 word-set Jaccard ≥ 0.60 | 0 pairs |
| 기존 Stage2 train 교차 최대 word-set Jaccard | 0.250000 |
| generic shape fingerprint | 69종, 단일 최대 11/150 = 7.33% |

초기 반복 n-gram 1종을 직접 고친 뒤 lexical 5-gram, 문자 유사도, 단어집합 Jaccard에서 내부·기존 Stage2 train 교차 검토선을 넘은 pair가 없다. generic shape의 최대 점유는 7.33%이며 의미 문장 복제나 명사 치환 보일러플레이트 증거는 발견되지 않았다.

## 5. 한국어·token 감사

- exact tokenizer: `tok-ko-en-32768.json`, SHA-256 `3a69001ecc28a5bdf1e951a1036b234c9bdcb847b310252c6d72cfc6c52c48e3`
- 최종 평균: 40.640000 tokens/record(+EOS)
- 최종 최소/최대: 34 / 48
- Stage2 승인 평균: 41.625, 허용범위 ±10% = 37.4625~45.7875 — file mean PASS
- text 문자 길이: 최소 74, 평균 83.667, 최대 97
- hard grammar finding: 0
- 조사 휴리스틱 warning: 5

5개 warning 위치를 전수 읽었다. `차이가`, `결과와`, `효과와`처럼 정상 단어 또는 primary 말미와 뒤 조사 경계를 보수적으로 잡은 false positive이며 실제 조사 불일치는 없다.

## 6. 해시와 최종 판정

- source SHA-256: `b97e0b664e2dee060a0bffc81d953ef0e343eae7e1b2569ea59c356ea6ed3a30`
- corpus SHA-256: `6d8871a3539b8e30f8c1523a17f84bc5cf0a44a729a57dfc93ce9be8693aecd6`
- resume checkpoint SHA-256: `35dbf8830e746ae36acf68c5507c3c8c790b1288d1b2a9cc4599b5fea9afa75d`
- central ledger SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`

`--require-complete --check-only` 감사에서 source 1·corpus 1, missing 0, structural PASS, direct-authoring debt 0을 확인했다. 전체 부분 감사도 55 source/corpus pairs·8,250 records에서 구조·exact/normalized 중복·train/validation exact leakage·5-word n-gram 반복·hard grammar·manual-review debt 모두 0으로 PASS했다. Stage2 누적 3,450 records의 exact tokenizer 평균은 42.809855(+EOS)으로 gate PASS다. 보호 대상 변경은 없다.

다음 예약은 `S2-A01-T-021`, `stage2_(11)causal_structure_high_density_train_v21.json`, ID `S2-CSH-03001 ~ S2-CSH-03150`, family `하천 저수지 수위·방류 관리 — 직접 원인·매개 경로·배경 조건 분리`다.
