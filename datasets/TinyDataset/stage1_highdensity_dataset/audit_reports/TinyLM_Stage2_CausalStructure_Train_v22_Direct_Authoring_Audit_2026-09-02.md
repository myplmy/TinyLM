# TinyLM Stage2 causal_structure train v22 직접 작성 감사

- 감사일: 2026-09-02 KST
- 판정: **PASS**
- reservation: `S2-A01-T-022`
- family: `하천 저수지 수위·방류 관리 — 공통 원인과 거짓 상관 통제`
- corpus: `stage2_highdensity_dataset/train/stage2_(11)causal_structure_high_density_train_v22.json`
- source: `stage2_highdensity_dataset/sources/train/stage2_(11)causal_structure_high_density_train_v22.source.jsonl`

## 1. 작성·포장 경계

150개의 primary concept, `text`, `relations`를 record별로 직접 작성했다. 자동 semantic-composition, 명사 치환 template, relation round-robin은 사용하지 않았다. 자동화는 JSONL parse, source 계약 검사, ID·고정 metadata 부여, tokenizer·중복·문법·유사도 감사에만 사용했다.

원고는 기상·유역·지하수·토지이용의 자연 공통 원인, 운영규정·목표수위·공유 설비·측정 보정의 인공 공통 원인을 다룬다. 이어 선택·탐지·누락·예방·적응 편향으로 생긴 거짓 상관을 판정하고, 층화·짝짓기·고정효과·음성 대조·시차·인과그래프·민감도 분석으로 뒷문경로를 감사한다.

source gate는 최초 150행에서 JSONL·primary literal·relations·tokenizer 계약을 모두 통과했다. file audit와 전체 partial audit에서도 반복 5-word n-gram이 발견되지 않아 사후 문장 수정은 없었다.

## 2. 구조·직렬화

| 검사 | 결과 |
|---|---:|
| source rows / corpus records | 150 / 150 |
| primary unique / text unique | 150 / 150 |
| ID first / last | `S2-CSH-03151` / `S2-CSH-03300` |
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
| `part_of` | 25 |
| `classification` | 82 |
| `boundary` | 150 |
| `contrast` | 34 |
| `comparison` | 54 |
| `function` | 26 |
| `role` | 44 |
| `process` | 72 |
| `state` | 61 |
| `attribute` | 52 |
| `other` | 0 |

`classification`은 공통 원인·교란·선택·탐지·누락 편향의 판정을, `process`는 공통 입력이 둘 이상의 결과로 갈라지는 경로를, `comparison`은 층화·짝짓기·대조·조정 전후 검사를 나타낸다. `boundary`는 상관과 인과, 처치와 처치 배정, 물리 변화와 공유 측정오차를 혼동하지 않도록 모든 record에 부여했다. `other`가 0회이므로 자주 나온 `other_type` 5가지는 해당 없음이다.

## 4. 중복·유사도·보일러플레이트

| 검사 | 결과 |
|---|---:|
| exact primary/text/normalized text 중복 | 0 |
| primary+relation-set 중복 | 0 |
| v22 내부 cross-record 5-word n-gram 반복 | 0 / 2,624 assignments |
| 현행 전체 57파일 cross-record 5-word n-gram 반복 | 0 / 158,230 assignments |
| v22 내부 normalized character similarity ≥ 0.80 | 0 pairs |
| v22 내부 최대 character similarity | 0.518519 |
| v22 내부 word-set Jaccard ≥ 0.60 | 0 pairs |
| v22 내부 최대 word-set Jaccard | 0.205882 |
| 기존 Stage2 train 3,450 records 교차 character similarity ≥ 0.80 | 0 pairs |
| 기존 Stage2 train 교차 최대 character similarity | 0.406015 |
| 기존 Stage2 train 교차 word-set Jaccard ≥ 0.60 | 0 pairs |
| 기존 Stage2 train 교차 최대 word-set Jaccard | 0.159091 |
| generic shape fingerprint | 53종, 단일 최대 14/150 = 9.33% |

lexical 5-gram, 문자 유사도, 단어집합 Jaccard에서 내부·기존 Stage2 train 교차 검토선을 넘은 pair가 없다. generic shape의 최대 점유는 9.33%이며 의미 문장 복제나 명사 치환 보일러플레이트 증거는 발견되지 않았다.

## 5. 한국어·token 감사

- exact tokenizer: `tok-ko-en-32768.json`, SHA-256 `3a69001ecc28a5bdf1e951a1036b234c9bdcb847b310252c6d72cfc6c52c48e3`
- 최종 평균: 43.380000 tokens/record(+EOS)
- 최종 최소/최대: 36 / 51
- Stage2 승인 평균: 41.625, 허용범위 ±10% = 37.4625~45.7875 — file mean PASS
- text 문자 길이: 최소 77, 평균 85.900, 최대 95
- hard grammar finding: 0
- 조사 휴리스틱 warning: 6

6개 warning 위치를 전수 읽었다. `효과와`, `차이가`처럼 정상 단어 내부를 보수적으로 잡은 false positive이며 실제 조사 불일치는 없다.

## 6. 해시와 최종 판정

- source SHA-256: `2b9d504d2a52be7d9beb2203651a965ea0cee5d28d65f825d49c497922e6a118`
- corpus SHA-256: `8169c71ce31e3f38b87ab728965093c3d031feac75e30e094506e6a8d969819c`
- resume checkpoint SHA-256: `ccdde9c615fa7bc02816786d87bd3658f0abfcb85b494bda0d1ff474b7cb6428`
- central ledger SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`

`--require-complete --check-only` 감사에서 source 1·corpus 1, missing 0, structural PASS, direct-authoring debt 0을 확인했다. 전체 부분 감사도 57 source/corpus pairs·8,550 records에서 구조·exact/normalized 중복·train/validation exact leakage·5-word n-gram 반복·hard grammar·manual-review debt 모두 0으로 PASS했다. Stage2 누적 3,750 records의 exact tokenizer 평균은 42.840267(+EOS)으로 gate PASS다. 보호 대상 변경은 없다.

다음 예약은 `S2-A01-T-023`, `stage2_(11)causal_structure_high_density_train_v23.json`, ID `S2-CSH-03301 ~ S2-CSH-03450`, family `하천 저수지 수위·방류 관리 — 원인 방향·피드백·역인과 판정`이다.
