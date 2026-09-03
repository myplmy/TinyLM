# TinyLM Stage2 causal_structure train v18 직접 작성 감사

- 감사일: 2026-09-02 KST
- 판정: **PASS**
- reservation: `S2-A01-T-018`
- family: `철도 운행 간격·환승 조정 — 원인 방향·피드백·역인과 판정`
- corpus: `stage2_highdensity_dataset/train/stage2_(11)causal_structure_high_density_train_v18.json`
- source: `stage2_highdensity_dataset/sources/train/stage2_(11)causal_structure_high_density_train_v18.source.jsonl`

## 1. 작성·포장 경계

150개의 primary concept, `text`, `relations`를 record별로 직접 작성했다. 자동 semantic-composition, 명사 치환 template, relation round-robin은 사용하지 않았다. 자동화는 JSONL parse, source 계약 검사, ID·고정 metadata 부여, tokenizer·중복·문법·유사도 감사에만 사용했다.

원고는 신호·속도·출입문·혼잡·정차·간격·회차·전력·기상 사건의 순방향과 운영 대응에서 생기는 역인과를 구분한다. 중반부에는 간격–혼잡–정차, 안내–문의, 장애–예비자원, 정비–고장의 양·음 피드백을 배치했고, 후반부에는 시각 정렬, 교차시차, 선택 개입, 상·하류 비대칭, 충격 감쇠, 순환 그래프와 방향 불확실성 보고를 다룬다.

최초 source gate에서 v13과 동일한 primary 1건을 발견해 해당 개념과 본문을 직접 다시 썼다. 이어 tokenizer 평균 46.880000(+EOS)이 Stage2 상한을 넘어 포장을 차단했고, 긴 문장 28건을 의미 손실 없이 직접 압축해 45.520000으로 낮춘 뒤 corpus를 생성했다.

## 2. 구조·직렬화

| 검사 | 결과 |
|---|---:|
| source rows / corpus records | 150 / 150 |
| primary unique / text unique | 150 / 150 |
| ID first / last | `S2-CSH-02551` / `S2-CSH-02700` |
| source↔corpus projection 오류 | 0 |
| JSON/JSONL parse 오류 | 0 |
| primary 본문 literal 누락 | 0 |
| 통제어휘 밖 relation | 0 |
| record 내부 relation 중복 | 0 |
| relation cardinality | 4개: 150 records |
| 고유 relation-set / 단일 최대 빈도 | 54 / 11 records |
| `other_type` 불일치 | 0 |

## 3. Relations 분포

총 relation 배정은 600회다.

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 39 |
| `classification` | 70 |
| `boundary` | 150 |
| `contrast` | 38 |
| `comparison` | 62 |
| `function` | 45 |
| `role` | 26 |
| `process` | 100 |
| `state` | 39 |
| `attribute` | 31 |
| `other` | 0 |

`process`는 사건 선후·전파·되먹임의 시간 경로를, `classification`과 `contrast`는 순방향·역인과·양방향·공통 원인·내생 대응의 판정 차이를 나타낸다. `boundary`는 시간적 선행만으로 방향을 확정하거나 대응 조치를 최초 원인으로 오인하지 않도록 모든 레코드에 부여했다. `other`가 0회이므로 자주 나온 `other_type` 5가지는 해당 없음이다.

## 4. 중복·유사도·보일러플레이트

| 검사 | 결과 |
|---|---:|
| exact primary/text/normalized text 중복 | 0 |
| primary+relation-set 중복 | 0 |
| v18 내부 cross-record 5-word n-gram 반복 | 0 / 3,082 assignments |
| 현행 전체 53파일 cross-record 5-word n-gram 반복 | 0 / 147,728 assignments |
| v18 내부 normalized character similarity ≥ 0.80 | 0 pairs |
| v18 내부 최대 character similarity | 0.423729 |
| v18 내부 word-set Jaccard ≥ 0.60 | 0 pairs |
| v18 내부 최대 word-set Jaccard | 0.184211 |
| 기존 Stage2 train 2,850 records 교차 character similarity ≥ 0.80 | 0 pairs |
| 기존 Stage2 train 교차 최대 character similarity | 0.554745 |
| 기존 Stage2 train 교차 word-set Jaccard ≥ 0.60 | 0 pairs |
| 기존 Stage2 train 교차 최대 word-set Jaccard | 0.289474 |
| generic shape fingerprint | 89종, 단일 최대 6/150 = 4.00% |

lexical 5-gram, 문자 유사도, 단어집합 Jaccard에서 내부·기존 Stage2 train 교차 검토선을 넘은 pair가 없다. generic shape도 분산되어 있으며 의미 문장 복제나 명사 치환 보일러플레이트 증거는 발견되지 않았다.

## 5. 한국어·token 감사

- exact tokenizer: `tok-ko-en-32768.json`, SHA-256 `3a69001ecc28a5bdf1e951a1036b234c9bdcb847b310252c6d72cfc6c52c48e3`
- 최초 평균: 46.880000 tokens/record(+EOS) — 상한 초과로 차단
- 최종 평균: 45.520000 tokens/record(+EOS)
- 최종 최소/최대: 38 / 50
- Stage2 승인 평균: 41.625, 허용범위 ±10% = 37.4625~45.7875 — final file mean PASS
- text 문자 길이: 최소 76, 평균 93.473, 최대 106
- hard grammar finding: 0
- 조사 휴리스틱 warning: 11

11개 warning 위치를 전수 읽었다. `결과와`, `차이가`, `효과와`의 정상 단어 내부를 `과와` 또는 `이가` 의심 패턴으로 잡은 false positive이며 실제 조사 불일치는 없다.

## 6. 해시와 최종 판정

- source SHA-256: `725da8e85c7753d417c9ddf9cbe0b6f00bd6c08d4b372d3f88eba3490d6e12e3`
- corpus SHA-256: `736e64ec76d8458fb61f43782340478dd05fac7faedabe11c470fe8796c625cb`
- resume checkpoint SHA-256: `b495479cafe66545254b0e30f0582a8ebde02b9b8389274cdf7e850a75c88999`
- central ledger SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`

`--require-complete --check-only` 감사에서 source 1·corpus 1, missing 0, structural PASS, direct-authoring debt 0을 확인했다. 전체 부분 감사도 53 source/corpus pairs·7,950 records에서 구조·exact/normalized 중복·train/validation exact leakage·5-word n-gram 반복·hard grammar·manual-review debt 모두 0으로 PASS했다. Stage2 누적 3,150 records의 exact tokenizer 평균은 43.113651(+EOS)으로 gate PASS다. 보호 대상 변경은 없다.

다음 예약은 `S2-A01-T-019`, `stage2_(11)causal_structure_high_density_train_v19.json`, ID `S2-CSH-02701 ~ S2-CSH-02850`, family `철도 운행 간격·환승 조정 — 개입 전후 결과와 자연 변동 구분`이다.
