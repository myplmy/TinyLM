# TinyLM Stage2 causal_structure train v19 직접 작성 감사

- 감사일: 2026-09-02 KST
- 판정: **PASS**
- reservation: `S2-A01-T-019`
- family: `철도 운행 간격·환승 조정 — 개입 전후 결과와 자연 변동 구분`
- corpus: `stage2_highdensity_dataset/train/stage2_(11)causal_structure_high_density_train_v19.json`
- source: `stage2_highdensity_dataset/sources/train/stage2_(11)causal_structure_high_density_train_v19.source.jsonl`

## 1. 작성·포장 경계

150개의 primary concept, `text`, `relations`를 record별로 직접 작성했다. 자동 semantic-composition, 명사 치환 template, relation round-robin은 사용하지 않았다. 자동화는 JSONL parse, source 계약 검사, ID·고정 metadata 부여, tokenizer·중복·문법·유사도 감사에만 사용했다.

원고는 철도 운영 개입의 전후 결과에서 계절·행사·기상·수요 구성·상하류 장애·관측 체계 변화가 만든 자연 변동을 분리한다. 전반부에는 구체적인 신호·시간표·안내·설비·인력 개입의 결과를, 중반부에는 기준선 오염과 동시 충격을, 후반부에는 무작위 배정·교차전환·중단 시계열·차이의 차이·부정 대조·민감도·파급효과와 재현성 보고를 배치했다.

초기 source 계약 검사에서 primary literal 누락 71건과 기존 v09와 같은 primary 1건을 발견했다. 각 문장을 의미에 맞게 직접 고쳐 primary를 자연스럽게 포함시켰고, 중복 primary는 `개입 초기 반짝효과와 장기 유지효과의 분리`로 새로 작성했다. 수정 뒤 source gate와 tokenizer gate를 통과한 상태에서 corpus를 포장했다.

## 2. 구조·직렬화

| 검사 | 결과 |
|---|---:|
| source rows / corpus records | 150 / 150 |
| primary unique / text unique | 150 / 150 |
| ID first / last | `S2-CSH-02701` / `S2-CSH-02850` |
| source↔corpus projection 오류 | 0 |
| JSON/JSONL parse 오류 | 0 |
| primary 본문 literal 누락 | 0 |
| 통제어휘 밖 relation | 0 |
| record 내부 relation 중복 | 0 |
| relation cardinality | 4개: 150 records |
| 고유 relation-set / 단일 최대 빈도 | 38 / 20 records |
| `other_type` 불일치 | 0 |

## 3. Relations 분포

총 relation 배정은 600회다.

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 32 |
| `classification` | 81 |
| `boundary` | 150 |
| `contrast` | 25 |
| `comparison` | 118 |
| `function` | 42 |
| `role` | 14 |
| `process` | 39 |
| `state` | 40 |
| `attribute` | 59 |
| `other` | 0 |

`comparison`은 개입 전후·처리군/대조군·기준선/반사실의 차이를, `classification`은 관측 변화·자연 변동·개입 효과의 판정 위치를 나타낸다. `boundary`는 시간상 뒤따른 변화나 측정 변화가 곧 개입의 인과 효과라는 오인을 막기 위해 모든 레코드에 부여했다. `other`가 0회이므로 자주 나온 `other_type` 5가지는 해당 없음이다.

## 4. 중복·유사도·보일러플레이트

| 검사 | 결과 |
|---|---:|
| exact primary/text/normalized text 중복 | 0 |
| primary+relation-set 중복 | 0 |
| v19 내부 cross-record 5-word n-gram 반복 | 0 / 2,486 assignments |
| 현행 전체 54파일 cross-record 5-word n-gram 반복 | 0 / 150,214 assignments |
| v19 내부 normalized character similarity ≥ 0.80 | 0 pairs |
| v19 내부 최대 character similarity | 0.406504 |
| v19 내부 word-set Jaccard ≥ 0.60 | 0 pairs |
| v19 내부 최대 word-set Jaccard | 0.205882 |
| 기존 Stage2 train 3,000 records 교차 character similarity ≥ 0.80 | 0 pairs |
| 기존 Stage2 train 교차 최대 character similarity | 0.606061 |
| 기존 Stage2 train 교차 word-set Jaccard ≥ 0.60 | 0 pairs |
| 기존 Stage2 train 교차 최대 word-set Jaccard | 0.228571 |
| generic shape fingerprint | 70종, 단일 최대 9/150 = 6.00% |

lexical 5-gram, 문자 유사도, 단어집합 Jaccard에서 내부·기존 Stage2 train 교차 검토선을 넘은 pair가 없다. generic shape의 최대 점유도 6%이며 의미 문장 복제, 명사 치환 보일러플레이트 또는 특정 문장 골격의 지배 증거는 발견되지 않았다.

## 5. 한국어·token 감사

- exact tokenizer: `tok-ko-en-32768.json`, SHA-256 `3a69001ecc28a5bdf1e951a1036b234c9bdcb847b310252c6d72cfc6c52c48e3`
- 최종 평균: 38.600000 tokens/record(+EOS)
- 최종 최소/최대: 30 / 46
- Stage2 승인 평균: 41.625, 허용범위 ±10% = 37.4625~45.7875 — file mean PASS
- text 문자 길이: 최소 64, 평균 77.753, 최대 94
- hard grammar finding: 0
- 조사 휴리스틱 warning: 17

17개 warning 위치를 전수 읽었다. `결함과`, `결과와`, `효과와`, `차이가`, `열차가`, `변화에서는` 같은 정상 단어 내부를 `과와` 또는 `이가` 의심 패턴으로 잡은 false positive이며 실제 조사 불일치는 없다.

## 6. 해시와 최종 판정

- source SHA-256: `cc84ef79ba66e6e650911abb6ca3d951fea58193f896eb35e8da287d869bb08d`
- corpus SHA-256: `fdd213f72baf3d34da9f1fb11d6bb3ad62cfb3de8e99b3c0b088cbc10f3f5f52`
- resume checkpoint SHA-256: `42cc4b74ae1cfcacfe002fac198c04e789c5562d70e81009680fb7758b405280`
- central ledger SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`

`--require-complete --check-only` 감사에서 source 1·corpus 1, missing 0, structural PASS, direct-authoring debt 0을 확인했다. 전체 부분 감사도 54 source/corpus pairs·8,100 records에서 구조·exact/normalized 중복·train/validation exact leakage·5-word n-gram 반복·hard grammar·manual-review debt 모두 0으로 PASS했다. Stage2 누적 3,300 records의 exact tokenizer 평균은 42.908485(+EOS)으로 gate PASS다. 보호 대상 변경은 없다.

다음 예약은 `S2-A01-T-020`, `stage2_(11)causal_structure_high_density_train_v20.json`, ID `S2-CSH-02851 ~ S2-CSH-03000`, family `철도 운행 간격·환승 조정 — 다중 원인의 충분성·기여 범위`다.
