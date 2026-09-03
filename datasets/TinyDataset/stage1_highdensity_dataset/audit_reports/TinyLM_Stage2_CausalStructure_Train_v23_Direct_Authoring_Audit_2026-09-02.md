# TinyLM Stage2 causal_structure train v23 직접 작성 감사

- 감사일: 2026-09-02 KST
- 판정: **PASS**
- reservation: `S2-A01-T-023`
- family: `하천 저수지 수위·방류 관리 — 원인 방향·피드백·역인과 판정`
- corpus: `stage2_highdensity_dataset/train/stage2_(11)causal_structure_high_density_train_v23.json`
- source: `stage2_highdensity_dataset/sources/train/stage2_(11)causal_structure_high_density_train_v23.source.jsonl`

## 1. 작성·포장 경계

150개의 primary concept, `text`, `relations`를 record별로 직접 작성했다. 자동 semantic-composition, 명사 치환 template, relation round-robin은 사용하지 않았다. 자동화는 JSONL parse, source 계약 검사, ID·고정 metadata 부여, tokenizer·중복·문법·유사도 감사에만 사용했다.

원고는 강우·유입·수위·수문·방류의 물리 방향, 예보·명령·처치 배정의 운영 방향을 먼저 구분한다. 다음으로 목표수위 제어, 연계댐, 수질·생태 대응의 양·음 피드백과 역인과를 다루고, 시차·개입·자연실험·수지·추적자·동시방정식·불변성 검사 및 폐루프 식별 편향 감사를 배치했다.

source gate는 최초 150행에서 JSONL·primary literal·relations·tokenizer 계약을 모두 통과했다. file audit와 전체 partial audit에서도 반복 5-word n-gram이 발견되지 않아 사후 문장 수정은 없었다.

## 2. 구조·직렬화

| 검사 | 결과 |
|---|---:|
| source rows / corpus records | 150 / 150 |
| primary unique / text unique | 150 / 150 |
| ID first / last | `S2-CSH-03301` / `S2-CSH-03450` |
| source↔corpus projection 오류 | 0 |
| JSON/JSONL parse 오류 | 0 |
| primary 본문 literal 누락 | 0 |
| 통제어휘 밖 relation | 0 |
| record 내부 relation 중복 | 0 |
| relation cardinality | 4개: 150 records |
| 고유 relation-set / 단일 최대 빈도 | 46 / 9 records |
| `other_type` 불일치 | 0 |

## 3. Relations 분포

총 relation 배정은 600회다.

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 19 |
| `classification` | 50 |
| `boundary` | 150 |
| `contrast` | 38 |
| `comparison` | 63 |
| `function` | 36 |
| `role` | 44 |
| `process` | 102 |
| `state` | 61 |
| `attribute` | 37 |
| `other` | 0 |

`process`는 물리 전달과 폐루프의 시간 방향을, `comparison`은 시차·개입·대조·전후 검사를, `role`은 예보·운영자·정책 신호가 행동을 배정하는 방향을 나타낸다. `boundary`는 선행성과 인과, 매개와 피드백, 처치와 역인과를 혼동하지 않도록 모든 record에 부여했다. `other`가 0회이므로 자주 나온 `other_type` 5가지는 해당 없음이다.

## 4. 중복·유사도·보일러플레이트

| 검사 | 결과 |
|---|---:|
| exact primary/text/normalized text 중복 | 0 |
| primary+relation-set 중복 | 0 |
| v23 내부 cross-record 5-word n-gram 반복 | 0 / 2,572 assignments |
| 현행 전체 58파일 cross-record 5-word n-gram 반복 | 0 / 160,802 assignments |
| v23 내부 normalized character similarity ≥ 0.80 | 0 pairs |
| v23 내부 최대 character similarity | 0.519084 |
| v23 내부 word-set Jaccard ≥ 0.60 | 0 pairs |
| v23 내부 최대 word-set Jaccard | 0.323529 |
| 기존 Stage2 train 3,600 records 교차 character similarity ≥ 0.80 | 0 pairs |
| 기존 Stage2 train 교차 최대 character similarity | 0.471545 |
| 기존 Stage2 train 교차 word-set Jaccard ≥ 0.60 | 0 pairs |
| 기존 Stage2 train 교차 최대 word-set Jaccard | 0.205128 |
| generic shape fingerprint | 70종, 단일 최대 9/150 = 6.00% |

lexical 5-gram, 문자 유사도, 단어집합 Jaccard에서 내부·기존 Stage2 train 교차 검토선을 넘은 pair가 없다. generic shape의 최대 점유는 6.00%이며 의미 문장 복제나 명사 치환 보일러플레이트 증거는 발견되지 않았다.

## 5. 한국어·token 감사

- exact tokenizer: `tok-ko-en-32768.json`, SHA-256 `3a69001ecc28a5bdf1e951a1036b234c9bdcb847b310252c6d72cfc6c52c48e3`
- 최종 평균: 44.500000 tokens/record(+EOS)
- 최종 최소/최대: 38 / 51
- Stage2 승인 평균: 41.625, 허용범위 ±10% = 37.4625~45.7875 — file mean PASS
- text 문자 길이: 최소 78, 평균 86.413, 최대 96
- hard grammar finding: 0
- 조사 휴리스틱 warning: 7

7개 warning 위치를 전수 읽었다. `물높이가`, `효과와`, `차이가`처럼 정상 단어 내부를 보수적으로 잡은 false positive이며 실제 조사 불일치는 없다.

## 6. 해시와 최종 판정

- source SHA-256: `a21165fc7c00d039748ec7280a0a264c56196d086e04ef60e4f1a73ddf919750`
- corpus SHA-256: `9b586ddd77ef320a4cc2ef5f81f499b0c6af3c4b560b8ee4104987d67fd577ee`
- resume checkpoint SHA-256: `f718a6094a1dc02022820a6663e8d93b1ff8ddb5ef66cc682cf576694ccae600`
- central ledger SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`

`--require-complete --check-only` 감사에서 source 1·corpus 1, missing 0, structural PASS, direct-authoring debt 0을 확인했다. 전체 부분 감사도 58 source/corpus pairs·8,700 records에서 구조·exact/normalized 중복·train/validation exact leakage·5-word n-gram 반복·hard grammar·manual-review debt 모두 0으로 PASS했다. Stage2 누적 3,900 records의 exact tokenizer 평균은 42.904103(+EOS)으로 gate PASS다. 보호 대상 변경은 없다.

다음 예약은 `S2-A01-T-024`, `stage2_(11)causal_structure_high_density_train_v24.json`, ID `S2-CSH-03451 ~ S2-CSH-03600`, family `하천 저수지 수위·방류 관리 — 개입 전후 결과와 자연 변동 구분`이다.
