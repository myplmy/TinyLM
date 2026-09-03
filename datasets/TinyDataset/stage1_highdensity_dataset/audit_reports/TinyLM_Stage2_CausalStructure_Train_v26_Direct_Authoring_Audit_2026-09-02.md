# TinyLM Stage2 causal_structure train v26 직접 작성 감사

- 감사일: 2026-09-02 KST
- 판정: **PASS**
- reservation: `S2-A01-T-026`
- family: `식품 냉장 유통·품질 유지 — 직접 원인·매개 경로·배경 조건 분리`
- corpus: `stage2_highdensity_dataset/train/stage2_(11)causal_structure_high_density_train_v26.json`
- source: `stage2_highdensity_dataset/sources/train/stage2_(11)causal_structure_high_density_train_v26.source.jsonl`

## 1. 작성·포장 경계

150개의 primary concept, `text`, `relations`를 record별로 직접 작성했다. 자동 semantic-composition, 명사 치환 template, relation round-robin은 사용하지 않았다. 자동화는 JSONL parse, source 계약 검사, ID·고정 metadata 부여, tokenizer·중복·문법·유사도 감사에만 사용했다.

원고는 냉장·냉동 유통에서 열유입, 냉각기능, 포장, 미생물, 수분, 산화, 숙성, 동결손상, 물류취급, 계측·개입 분석을 다룬다. 각 사례에서 직접 원인, 상류·하류 매개, 출발상태·환경·제품특성 같은 배경 조건과 측정·선택 오류를 분리했다.

직접 작성 초안은 의미 후보 156행이었다. 150행 계약에 맞춰 추적 라벨, 골판지 강도, 습도조절제, 관능 역치, 아이스크림 공기혼입, 운송 고도차처럼 핵심 축과 중복되거나 품질 인과의 중심성이 낮은 6행을 제외했다. source gate가 포착한 primary literal 1건을 바로잡고 어색한 primary 1건도 의미를 보존해 직접 고친 뒤 150행 구조·tokenizer gate를 통과했다. package 이후에는 5-word n-gram 반복이 없어 사후 문장 수정이 없었다.

## 2. 구조·직렬화

| 검사 | 결과 |
|---|---:|
| source rows / corpus records | 150 / 150 |
| primary unique / text unique | 150 / 150 |
| ID first / last | `S2-CSH-03751` / `S2-CSH-03900` |
| source↔corpus projection 오류 | 0 |
| JSON/JSONL parse 오류 | 0 |
| primary 본문 literal 누락 | 0 |
| 통제어휘 밖 relation | 0 |
| record 내부 relation 중복 | 0 |
| relation cardinality | 4개: 150 records |
| 고유 relation-set / 단일 최대 빈도 | 53 / 11 records |
| `other_type` 불일치 | 0 |

## 3. Relations 분포

총 relation 배정은 600회다.

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 36 |
| `classification` | 76 |
| `boundary` | 150 |
| `contrast` | 34 |
| `comparison` | 53 |
| `function` | 41 |
| `role` | 31 |
| `process` | 81 |
| `state` | 43 |
| `attribute` | 55 |
| `other` | 0 |

`process`는 열전달·증식·산화·숙성·동결손상의 시간 경로를, `classification`은 직접 원인·매개·배경·측정오류의 지위를, `attribute`와 `state`는 온도·습도·기체·초기품질 조건을 나타낸다. `boundary`는 원인과 지표, 매개와 결과, 설비효과와 외부 배경을 혼동하지 않도록 모든 record에 부여했다. `other`가 0회이므로 자주 나온 `other_type` 5가지는 해당 없음이다.

## 4. 중복·유사도·보일러플레이트

| 검사 | 결과 |
|---|---:|
| exact primary/text/normalized text 중복 | 0 |
| primary+relation-set 중복 | 0 |
| v26 내부 cross-record 5-word n-gram 반복 | 0 / 2,552 assignments |
| 현행 전체 61파일 cross-record 5-word n-gram 반복 | 0 / 167,947 assignments |
| v26 내부 normalized character similarity ≥ 0.80 | 0 pairs |
| v26 내부 최대 character similarity | 0.432000 |
| v26 내부 word-set Jaccard ≥ 0.60 | 0 pairs |
| v26 내부 최대 word-set Jaccard | 0.171429 |
| 기존 Stage2 train 4,050 records 교차 character similarity ≥ 0.80 | 0 pairs |
| 기존 Stage2 train 교차 최대 character similarity | 0.565217 |
| 기존 Stage2 train 교차 word-set Jaccard ≥ 0.60 | 0 pairs |
| 기존 Stage2 train 교차 최대 word-set Jaccard | 0.179487 |
| generic shape fingerprint | 51종, 단일 최대 10/150 = 6.67% |

lexical 5-gram, 문자 유사도, 단어집합 Jaccard에서 내부·기존 Stage2 train 교차 검토선을 넘은 pair가 없다. generic shape 최대 점유는 6.67%이며 의미 문장 복제나 명사 치환 보일러플레이트 증거는 발견되지 않았다.

## 5. 한국어·token 감사

- exact tokenizer: `tok-ko-en-32768.json`, SHA-256 `3a69001ecc28a5bdf1e951a1036b234c9bdcb847b310252c6d72cfc6c52c48e3`
- 최종 평균: 44.480000 tokens/record(+EOS)
- 최종 최소/최대: 38 / 51
- Stage2 승인 평균: 41.625, 허용범위 ±10% = 37.4625~45.7875 — file mean PASS
- text 문자 길이: 최소 78, 평균 85.580, 최대 95
- hard grammar finding: 0
- 조사 휴리스틱 warning: 10

10개 warning 위치를 전수 읽었다. `효과와`, `결과와`, `차이가`, `냉장기가`처럼 정상 단어 내부를 보수적으로 잡은 false positive이며 실제 조사 불일치는 없다.

## 6. 해시와 최종 판정

- source SHA-256: `fcf4c91f998cc4296974ccb4b3f21ea11dfe6861bd3d4e1cc1845345a0c3c8b2`
- corpus SHA-256: `b117d5948fe944371f543be8b9c7c2f111df97f4d772db6cfa95a660a0731eaa`
- resume checkpoint SHA-256: `9a3bc196eaff7a9290791cd86a8942c00b36f89b7e25a12e5abb58b1b229bc4d`
- central ledger SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`

`--require-complete --check-only` 감사에서 source 1·corpus 1, missing 0, structural PASS, direct-authoring debt 0을 확인했다. 전체 부분 감사도 61 source/corpus pairs·9,150 records에서 구조·exact/normalized 중복·train/validation exact leakage·5-word n-gram 반복·hard grammar·manual-review debt 모두 0으로 PASS했다. Stage2 누적 4,350 records의 exact tokenizer 평균은 43.008046(+EOS)으로 gate PASS다. 보호 대상 변경은 없다.

다음 예약은 `S2-A01-T-027`, `stage2_(11)causal_structure_high_density_train_v27.json`, ID `S2-CSH-03901 ~ S2-CSH-04050`, family `식품 냉장 유통·품질 유지 — 공통 원인과 거짓 상관 통제`다.
