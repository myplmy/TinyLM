# TinyLM Stage2 causal_structure train v28 직접 작성 감사

- 감사일: 2026-09-02 KST
- 판정: **PASS**
- reservation: `S2-A01-T-028`
- family: `식품 냉장 유통·품질 유지 — 원인 방향·피드백·역인과 판정`
- corpus: `stage2_highdensity_dataset/train/stage2_(11)causal_structure_high_density_train_v28.json`
- source: `stage2_highdensity_dataset/sources/train/stage2_(11)causal_structure_high_density_train_v28.source.jsonl`

## 1. 작성·포장 경계

150개의 primary concept, `text`, `relations`를 record별로 직접 작성했다. 자동 semantic-composition, 명사 치환 template, relation round-robin은 사용하지 않았다. 자동화는 JSONL parse, source 계약 검사, ID·고정 metadata 부여, tokenizer·중복·문법·유사도 감사에만 사용했다.

원고는 식품 냉장 유통에서 원인과 결과의 시간 방향, 복원·증폭 피드백, 제어반응이 만드는 역인과, 반응지연·진동·이력효과, 개입과 대조, 상호인과, 공통원인·선택편향·매개변수 통제 오류를 구분한다. 압축기·서모스탯·환기·습도·포장·미생물·재고·검사·경보의 실제 경로를 사용해 단순 상관을 원인 방향으로 확정하지 않도록 구성했다.

첫 작성분은 148행으로 계수되어 패키징 전에 중단했고, 이력효과와 예측제어 2행을 직접 보충해 150행을 맞췄다. 완성 원고의 최초 tokenizer 평균은 46.973333(+EOS)으로 상한을 넘었다. 의미를 유지한 직접 압축을 두 차례 수행해 최종 평균 45.486667로 source gate를 통과했다. package 뒤 파일·전체 감사에서 반복 5-word n-gram은 발견되지 않아 source·corpus 추가 수정은 없었다.

## 2. 구조·직렬화

| 검사 | 결과 |
|---|---:|
| source rows / corpus records | 150 / 150 |
| primary unique / text unique | 150 / 150 |
| ID first / last | `S2-CSH-04051` / `S2-CSH-04200` |
| source↔corpus projection 오류 | 0 |
| JSON/JSONL parse 오류 | 0 |
| primary 본문 literal 누락 | 0 |
| 통제어휘 밖 relation | 0 |
| record 내부 relation 중복 | 0 |
| relation cardinality | 3개: 3 records, 4개: 147 records |
| 고유 relation-set / 단일 최대 빈도 | 34 / 14 records |
| `other_type` 불일치 | 0 |

## 3. Relations 분포

총 relation 배정은 597회다.

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 23 |
| `classification` | 71 |
| `boundary` | 150 |
| `contrast` | 42 |
| `comparison` | 37 |
| `function` | 46 |
| `role` | 23 |
| `process` | 142 |
| `state` | 37 |
| `attribute` | 26 |
| `other` | 0 |

`process`는 시간 방향·지연·되먹임·개입 경로를, `function`은 제어장치와 운영조치의 작동을, `classification`은 역인과·공통원인·선택·매개통제의 판정 지위를 나타낸다. `boundary`는 모든 record에서 상관과 인과, 선행과 반응, 총효과와 통제 후 효과의 경계를 명시한다. `other`가 0회이므로 자주 나온 `other_type` 5가지는 해당 없음이다.

## 4. 중복·유사도·보일러플레이트

| 검사 | 결과 |
|---|---:|
| exact primary/text/normalized text 중복 | 0 |
| primary+relation-set 중복 | 0 |
| v28 내부 cross-record 5-word n-gram 반복 | 0 / 2,392 assignments |
| 현행 전체 63파일 cross-record 5-word n-gram 반복 | 0 / 172,780 assignments |
| v28 내부 normalized character similarity ≥ 0.80 | 0 pairs |
| v28 내부 최대 character similarity | 0.409836 |
| v28 내부 word-set Jaccard ≥ 0.60 | 0 pairs |
| v28 내부 최대 word-set Jaccard | 0.193548 |
| 기존 Stage2 train 4,350 records 교차 character similarity ≥ 0.80 | 0 pairs |
| 기존 Stage2 train 교차 최대 character similarity | 0.551181 |
| 기존 Stage2 train 교차 word-set Jaccard ≥ 0.60 | 0 pairs |
| 기존 Stage2 train 교차 최대 word-set Jaccard | 0.218750 |
| generic shape fingerprint | 73종, 단일 최대 7/150 = 4.67% |

최종 lexical 5-gram, 문자 유사도, 단어집합 Jaccard에서 내부·기존 Stage2 train 교차 검토선을 넘은 pair가 없다. generic shape 최대 점유는 4.67%이며 명사 치환 보일러플레이트 증거는 발견되지 않았다.

## 5. 한국어·token 감사

- exact tokenizer: `tok-ko-en-32768.json`, SHA-256 `3a69001ecc28a5bdf1e951a1036b234c9bdcb847b310252c6d72cfc6c52c48e3`
- 최종 평균: 45.486667 tokens/record(+EOS)
- 최종 최소/최대: 37 / 49
- Stage2 승인 평균: 41.625, 허용범위 ±10% = 37.4625~45.7875 — file mean PASS
- text 문자 길이: 최소 67, 평균 84.747, 최대 103
- hard grammar finding: 0
- 조사 휴리스틱 warning: 5

5개 warning 위치를 전수 읽었다. `차이가`, `교육효과와`, `대조군과 차이가`, `인과와`처럼 정상 단어 내부를 보수적으로 잡은 false positive이며 실제 조사 불일치는 없다.

## 6. 해시와 최종 판정

- source SHA-256: `161a050288bb42a38e19e91d53684c83ab171731d25a4d37ef6a447d29995fcb`
- corpus SHA-256: `42ff611cd60b0b5c43ee6116c3548110c4116391dfd7582160d7681eafc7e5de`
- resume checkpoint SHA-256: `4ebb08ce9e8535c02e6d2294ae2911335246707c291b94cd4e7112b85232788f`
- central ledger SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`

`--require-complete --check-only` 감사에서 source 1·corpus 1, missing 0, structural PASS, direct-authoring debt 0을 확인했다. 전체 부분 감사도 63 source/corpus pairs·9,450 records에서 구조·exact/normalized 중복·train/validation exact leakage·5-word n-gram 반복·hard grammar·manual-review debt 모두 0으로 PASS했다. Stage2 누적 4,650 records(현행 validation 포함)의 exact tokenizer 평균은 43.168387(+EOS)으로 gate PASS다. 중앙 reservation·manifest read-only 재검증도 4,370파일, 655,500레코드, relation-focus·분할·ID·family 중복 오류 0으로 PASS했고 보호 대상 변경은 없다.

다음 예약은 `S2-A01-T-029`, `stage2_(11)causal_structure_high_density_train_v29.json`, ID `S2-CSH-04201 ~ S2-CSH-04350`, family `식품 냉장 유통·품질 유지 — 개입 전후 결과와 자연 변동 구분`이다.
