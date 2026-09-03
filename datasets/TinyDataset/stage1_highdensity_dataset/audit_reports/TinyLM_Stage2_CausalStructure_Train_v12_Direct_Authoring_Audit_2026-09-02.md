# TinyLM Stage2 causal_structure train v12 직접 작성 감사

- 감사일: 2026-09-02 KST
- 판정: **PASS**
- reservation: `S2-A01-T-012`
- family: `클라우드 서비스 부하·장애 대응 — 공통 원인과 거짓 상관 통제`
- corpus: `stage2_highdensity_dataset/train/stage2_(11)causal_structure_high_density_train_v12.json`
- source: `stage2_highdensity_dataset/sources/train/stage2_(11)causal_structure_high_density_train_v12.source.jsonl`

## 1. 작성·포장 경계

150개의 primary concept, `text`, `relations`를 record별로 직접 작성했다. 자동 semantic-composition, 명사 치환 template, relation round-robin은 사용하지 않았다. 자동화는 JSONL parse, source 계약 검사, ID·고정 metadata 부여, tokenizer·중복·문법·유사도 감사에만 사용했다.

첫 source gate의 tokenizer 평균은 46.046667로 승인 상한 45.7875를 넘어 패키징을 차단했다. 의미·객체·관계는 유지하고 긴 13개 문장의 불필요한 수식을 직접 압축해 평균 45.313333으로 낮춘 뒤 패키징했다. 최초 누적 감사에서 기존 Stage2와 공유한 5-word n-gram `공통 원인이 될 수 있다` 1종을 발견해 해당 문장을 직접 고쳤고, source와 corpus projection 및 checkpoint 해시를 다시 맞춘 뒤 0건을 확인했다. 최종 token 평균은 45.320000이다.

원고는 공유 트래픽·인프라·설정·시간대가 여러 지표를 함께 움직이는 사례, 표본 선택·집계·역인과·반응 정책이 만든 상관 착시, 층화·대조·시차·개입·위약·민감도 검사를 다룬다.

## 2. 구조·직렬화

| 검사 | 결과 |
|---|---:|
| source rows / corpus records | 150 / 150 |
| primary unique / text unique | 150 / 150 |
| ID first / last | `S2-CSH-01651` / `S2-CSH-01800` |
| source↔corpus projection 오류 | 0 |
| JSON/JSONL parse 오류 | 0 |
| primary 본문 literal 누락 | 0 |
| 통제어휘 밖 relation | 0 |
| record 내부 relation 중복 | 0 |
| relation cardinality | 4개: 150 records |
| 고유 relation-set / 단일 최대 빈도 | 38 / 24 records |
| `other_type` 불일치 | 0 |

## 3. Relations 분포

총 relation 배정은 600회다.

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 50 |
| `classification` | 123 |
| `boundary` | 150 |
| `contrast` | 30 |
| `comparison` | 77 |
| `function` | 7 |
| `role` | 15 |
| `process` | 82 |
| `state` | 20 |
| `attribute` | 46 |
| `other` | 0 |

`classification`은 직접 인과·공통 원인·역인과·선택 편향을 판정하는 축이고, `process`는 공통 선행 사건과 피드백의 시간 방향을, `comparison`은 층화·대조·위약 결과를 나타낸다. `boundary`는 높은 상관과 직접 인과를 혼동하지 않도록 모든 레코드에 부여했다. `other`가 0회이므로 자주 나온 `other_type` 5가지는 해당 없음이다.

## 4. 중복·유사도·보일러플레이트

| 검사 | 결과 |
|---|---:|
| exact primary/text/normalized text 중복 | 0 |
| primary+relation-set 중복 | 0 |
| cross-record 5-word n-gram 반복 | 0 / 3,244 assignments |
| v12 내부 normalized character similarity ≥ 0.80 | 0 pairs |
| v12 내부 최대 character similarity | 0.481013 |
| v12 내부 word-set Jaccard ≥ 0.60 | 0 pairs |
| v12 내부 최대 word-set Jaccard | 0.261905 |
| 기존 Stage2 train 1,950 records 교차 character similarity ≥ 0.80 | 0 pairs |
| 기존 Stage2 train 교차 최대 character similarity | 0.642336 |
| 기존 Stage2 train 교차 word-set Jaccard ≥ 0.60 | 0 pairs |
| 기존 Stage2 train 교차 최대 word-set Jaccard | 0.270270 |
| generic shape fingerprint | 65종, 단일 최대 8/150 = 5.33% |

초기 교차 5-word 반복 1종을 수정한 뒤 lexical 5-gram과 두 fuzzy 기준의 고유사 pair는 내부·기존 Stage2 train 교차 비교에서 모두 0이다. 최대 character similarity도 0.80 임계보다 낮고, exact·normalized 중복이나 primary+relation-set 중복은 없다.

## 5. 한국어·token 감사

- exact tokenizer: `tok-ko-en-32768.json`, SHA-256 `3a69001ecc28a5bdf1e951a1036b234c9bdcb847b310252c6d72cfc6c52c48e3`
- 평균: 45.320000 tokens/record(+EOS)
- 최소/최대: 37 / 51
- Stage2 승인 평균: 41.625, 허용범위 ±10% = 37.4625~45.7875 — file mean PASS
- text 문자 길이: 최소 71, 평균 97.533, 최대 116
- hard grammar finding: 0
- 조사 휴리스틱 warning: 1

warning 행을 직접 읽었다. `캐시 효과와 요청 종류`의 정상 단어 `효과와` 내부를 조사 의심 패턴으로 탐지한 false positive이며, 실제 조사 불일치는 없다.

## 6. 해시와 최종 판정

- source SHA-256: `aa367da776f5d970923da7f61a27aaf1193e88d86e3dbed22ce1b3cce99da5ad`
- corpus SHA-256: `2391026cadf9be5d15795970b72382586a99485c40a67550a287b176bb230e49`
- resume checkpoint SHA-256: `9b6736fa4839229cde762aa89a46ac6780536717320ec87c96b263390ad2563b`
- central ledger SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`

`--require-complete --check-only` 감사에서 source 1·corpus 1, missing 0, structural PASS, direct-authoring debt 0을 확인했다. 전체 부분 감사도 47 source/corpus pairs·7,050 records에서 구조·exact/normalized 중복·train/validation exact leakage·5-word n-gram 반복·hard grammar·manual-review debt 모두 0으로 PASS했다. Stage1·저밀도·held-out·기존 Stage2~10 pilot과 v02~v11은 수정하지 않았다.

다음 예약은 `S2-A01-T-013`, `stage2_(11)causal_structure_high_density_train_v13.json`, ID `S2-CSH-01801 ~ S2-CSH-01950`, family `클라우드 서비스 부하·장애 대응 — 원인 방향·피드백·역인과 판정`이다.
