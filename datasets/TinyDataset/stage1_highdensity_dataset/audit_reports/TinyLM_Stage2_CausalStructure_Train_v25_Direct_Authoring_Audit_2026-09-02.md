# TinyLM Stage2 causal_structure train v25 직접 작성 감사

- 감사일: 2026-09-02 KST
- 판정: **PASS**
- reservation: `S2-A01-T-025`
- family: `하천 저수지 수위·방류 관리 — 다중 원인의 충분성·기여 범위`
- corpus: `stage2_highdensity_dataset/train/stage2_(11)causal_structure_high_density_train_v25.json`
- source: `stage2_highdensity_dataset/sources/train/stage2_(11)causal_structure_high_density_train_v25.source.jsonl`

## 1. 작성·포장 경계

150개의 primary concept, `text`, `relations`를 record별로 직접 작성했다. 자동 semantic-composition, 명사 치환 template, relation round-robin은 사용하지 않았다. 자동화는 JSONL parse, source 계약 검사, ID·고정 metadata 부여, tokenizer·중복·문법·유사도 감사에만 사용했다.

원고는 저수지·하천의 홍수, 가뭄, 수질, 생태, 방류 운영에서 하나의 결과를 만드는 필요조건·충분조건·공동원인·대체경로·상호작용을 구분한다. 이어 총효과와 직접·매개·공동 기여, 한계기여와 평균기여, 설명범위와 잔여오차, 기여 배분의 가정·불확실성·재현성까지 다룬다.

최초 직접 작성 원고는 148행이어서 source gate가 `expected 150, got 148`로 쓰기 전에 차단했다. 누락된 공동기여 배분 감사와 미관측 대체경로 처리 원칙 2개를 직접 보충해 150행 구조·tokenizer gate를 통과시켰다. 최초 package 감사에서 `몫을 어느 한 원인에 전부` 5-word n-gram 1종이 2개 record에 반복되어, 공분산 배분 record의 표현을 의미를 보존한 별도 문장으로 직접 다시 썼다. source·corpus와 checkpoint SHA를 함께 갱신한 뒤 file/full audit에서 반복 0을 확인했다.

## 2. 구조·직렬화

| 검사 | 결과 |
|---|---:|
| source rows / corpus records | 150 / 150 |
| primary unique / text unique | 150 / 150 |
| ID first / last | `S2-CSH-03601` / `S2-CSH-03750` |
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
| `part_of` | 56 |
| `classification` | 74 |
| `boundary` | 150 |
| `contrast` | 20 |
| `comparison` | 95 |
| `function` | 34 |
| `role` | 27 |
| `process` | 49 |
| `state` | 49 |
| `attribute` | 46 |
| `other` | 0 |

`comparison`은 원인별·경로별·조건별 기여 크기를, `part_of`는 전체 효과와 직접·매개·공동 몫의 포함 관계를, `classification`은 필요·충분·촉진·차단 조건과 배분 지위를 나타낸다. `boundary`는 원인 존재와 충분성, 설명력과 인과 기여, 상관 몫과 공동 기여를 혼동하지 않도록 모든 record에 부여했다. `other`가 0회이므로 자주 나온 `other_type` 5가지는 해당 없음이다.

## 4. 중복·유사도·보일러플레이트

| 검사 | 결과 |
|---|---:|
| exact primary/text/normalized text 중복 | 0 |
| primary+relation-set 중복 | 0 |
| v25 내부 cross-record 5-word n-gram 반복 | 0 / 2,289 assignments |
| 현행 전체 60파일 cross-record 5-word n-gram 반복 | 0 / 165,395 assignments |
| v25 내부 normalized character similarity ≥ 0.80 | 0 pairs |
| v25 내부 최대 character similarity | 0.504202 |
| v25 내부 word-set Jaccard ≥ 0.60 | 0 pairs |
| v25 내부 최대 word-set Jaccard | 0.250000 |
| 기존 Stage2 train 3,900 records 교차 character similarity ≥ 0.80 | 0 pairs |
| 기존 Stage2 train 교차 최대 character similarity | 0.496000 |
| 기존 Stage2 train 교차 word-set Jaccard ≥ 0.60 | 0 pairs |
| 기존 Stage2 train 교차 최대 word-set Jaccard | 0.222222 |
| generic shape fingerprint | 80종, 단일 최대 9/150 = 6.00% |

lexical 5-gram, 문자 유사도, 단어집합 Jaccard에서 내부·기존 Stage2 train 교차 검토선을 넘은 pair가 없다. 최초 5-word 반복은 직접 수정해 제거했고 generic shape 최대 점유는 6.00%다. 의미 문장 복제나 명사 치환 보일러플레이트 증거는 발견되지 않았다.

## 5. 한국어·token 감사

- exact tokenizer: `tok-ko-en-32768.json`, SHA-256 `3a69001ecc28a5bdf1e951a1036b234c9bdcb847b310252c6d72cfc6c52c48e3`
- 최종 평균: 44.340000 tokens/record(+EOS)
- 최종 최소/최대: 36 / 54
- Stage2 승인 평균: 41.625, 허용범위 ±10% = 37.4625~45.7875 — file mean PASS
- text 문자 길이: 최소 73, 평균 82.260, 최대 101
- hard grammar finding: 0
- 조사 휴리스틱 warning: 8

8개 warning 위치를 전수 읽었다. `높이가`, `효과와`, `결과와`, `차이가`처럼 정상 단어 내부를 보수적으로 잡은 false positive이며 실제 조사 불일치는 없다.

## 6. 해시와 최종 판정

- source SHA-256: `cd8b96647046c5c9bef162e3e2a49b8ebb2baa8c3c67cfe6b5cf47d46eae15ab`
- corpus SHA-256: `0c6beecd2bee862b7843af49998410804d51ed6e7096f8d6e716c9a195f8cdc9`
- resume checkpoint SHA-256: `c89cc3b32c5ae06e27cff0471df69552691543184ade7cb6f0bc01806cb6f18d`
- central ledger SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`

`--require-complete --check-only` 감사에서 source 1·corpus 1, missing 0, structural PASS, direct-authoring debt 0을 확인했다. 전체 부분 감사도 60 source/corpus pairs·9,000 records에서 구조·exact/normalized 중복·train/validation exact leakage·5-word n-gram 반복·hard grammar·manual-review debt 모두 0으로 PASS했다. Stage2 누적 4,200 records의 exact tokenizer 평균은 42.955476(+EOS)으로 gate PASS다. 보호 대상 변경은 없다.

다음 예약은 `S2-A01-T-026`, `stage2_(11)causal_structure_high_density_train_v26.json`, ID `S2-CSH-03751 ~ S2-CSH-03900`, family `식품 냉장 유통·품질 유지 — 직접 원인·매개 경로·배경 조건 분리`다.
