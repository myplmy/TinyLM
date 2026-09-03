# TinyLM Stage2 causal_structure train v13 직접 작성 감사

- 감사일: 2026-09-02 KST
- 판정: **PASS**
- reservation: `S2-A01-T-013`
- family: `클라우드 서비스 부하·장애 대응 — 원인 방향·피드백·역인과 판정`
- corpus: `stage2_highdensity_dataset/train/stage2_(11)causal_structure_high_density_train_v13.json`
- source: `stage2_highdensity_dataset/sources/train/stage2_(11)causal_structure_high_density_train_v13.source.jsonl`

## 1. 작성·포장 경계

150개의 primary concept, `text`, `relations`를 record별로 직접 작성했다. 자동 semantic-composition, 명사 치환 template, relation round-robin은 사용하지 않았다. 자동화는 JSONL parse, source 계약 검사, ID·고정 metadata 부여, tokenizer·중복·문법·유사도 감사에만 사용했다.

원고는 요청·자원·오류·재시도·확장·복구의 선후 방향, 양성·음성 피드백, 정책 반응에서 생기는 역인과를 다룬다. 후반부는 고해상도 시간선, 개입·롤백·재도입, 고정 용량·재시도 중단·장애 주입과 증거 등급을 다룬다.

최초 누적 감사에서 기존 Stage2와 공유한 5-word n-gram `집계 결과가 늦어 사용자가 원시` 1종을 발견했다. v13 해당 문장을 직접 고치고 source·corpus projection 및 checkpoint 해시를 다시 맞춘 뒤 반복 0건을 확인했다.

## 2. 구조·직렬화

| 검사 | 결과 |
|---|---:|
| source rows / corpus records | 150 / 150 |
| primary unique / text unique | 150 / 150 |
| ID first / last | `S2-CSH-01801` / `S2-CSH-01950` |
| source↔corpus projection 오류 | 0 |
| JSON/JSONL parse 오류 | 0 |
| primary 본문 literal 누락 | 0 |
| 통제어휘 밖 relation | 0 |
| record 내부 relation 중복 | 0 |
| relation cardinality | 4개: 150 records |
| 고유 relation-set / 단일 최대 빈도 | 32 / 14 records |
| `other_type` 불일치 | 0 |

## 3. Relations 분포

총 relation 배정은 600회다.

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 48 |
| `classification` | 90 |
| `boundary` | 150 |
| `contrast` | 26 |
| `comparison` | 59 |
| `function` | 36 |
| `role` | 18 |
| `process` | 124 |
| `state` | 34 |
| `attribute` | 15 |
| `other` | 0 |

`process`는 원인→결과 선후와 순환 간선을, `classification`은 촉발·반응·증폭·역인과 판정을, `function`은 백오프·차단기·확장 같은 안정화 정책을 나타낸다. `boundary`는 동시 상관, 예측 선행, 반응 정책을 검증된 인과 방향과 혼동하지 않도록 모든 레코드에 부여했다. `other`가 0회이므로 자주 나온 `other_type` 5가지는 해당 없음이다.

## 4. 중복·유사도·보일러플레이트

| 검사 | 결과 |
|---|---:|
| exact primary/text/normalized text 중복 | 0 |
| primary+relation-set 중복 | 0 |
| cross-record 5-word n-gram 반복 | 0 / 3,002 assignments |
| v13 내부 normalized character similarity ≥ 0.80 | 0 pairs |
| v13 내부 최대 character similarity | 0.553191 |
| v13 내부 word-set Jaccard ≥ 0.60 | 0 pairs |
| v13 내부 최대 word-set Jaccard | 0.236842 |
| 기존 Stage2 train 2,100 records 교차 character similarity ≥ 0.80 | 0 pairs |
| 기존 Stage2 train 교차 최대 character similarity | 0.642336 |
| 기존 Stage2 train 교차 word-set Jaccard ≥ 0.60 | 0 pairs |
| 기존 Stage2 train 교차 최대 word-set Jaccard | 0.382353 |
| generic shape fingerprint | 63종, 단일 최대 13/150 = 8.67% |

초기 교차 5-word 반복 1종을 수정한 뒤 lexical 5-gram과 두 fuzzy 기준의 고유사 pair는 내부·기존 Stage2 train 교차 비교에서 모두 0이다. exact·normalized 중복과 primary+relation-set 중복도 없다.

## 5. 한국어·token 감사

- exact tokenizer: `tok-ko-en-32768.json`, SHA-256 `3a69001ecc28a5bdf1e951a1036b234c9bdcb847b310252c6d72cfc6c52c48e3`
- 평균: 44.913333 tokens/record(+EOS)
- 최소/최대: 37 / 52
- Stage2 승인 평균: 41.625, 허용범위 ±10% = 37.4625~45.7875 — file mean PASS
- text 문자 길이: 최소 83, 평균 93.413, 최대 108
- hard grammar finding: 0
- 조사 휴리스틱 warning: 6

6개 warning 행을 직접 읽었다. `결과와`, `효과와`, `초과와`, `차이가` 같은 정상 어휘 내부를 조사 의심 패턴으로 탐지한 false positive이며 실제 조사 불일치는 없다.

## 6. 해시와 최종 판정

- source SHA-256: `e3e6f977f8ddafdc8f481651fdd7f302bad7792732a3c04ddc3882f435df6347`
- corpus SHA-256: `7210e0cc22b0a9cb5d475e787659f6cd144e9c188f55fe54b1be61c97c02e180`
- resume checkpoint SHA-256: `0bc6219c0937535e2a7d4b1037fa097d251b75c96e825c097c4e2416f2e170b7`
- central ledger SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`

`--require-complete --check-only` 감사에서 source 1·corpus 1, missing 0, structural PASS, direct-authoring debt 0을 확인했다. 전체 부분 감사도 48 source/corpus pairs·7,200 records에서 구조·exact/normalized 중복·train/validation exact leakage·5-word n-gram 반복·hard grammar·manual-review debt 모두 0으로 PASS했다. Stage1·저밀도·held-out·기존 Stage2~10 pilot과 v02~v12는 수정하지 않았다.

다음 예약은 `S2-A01-T-014`, `stage2_(11)causal_structure_high_density_train_v14.json`, ID `S2-CSH-01951 ~ S2-CSH-02100`, family `클라우드 서비스 부하·장애 대응 — 개입 전후 결과와 자연 변동 구분`이다.
