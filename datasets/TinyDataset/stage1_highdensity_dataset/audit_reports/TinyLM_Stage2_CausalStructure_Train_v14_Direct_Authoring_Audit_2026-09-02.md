# TinyLM Stage2 causal_structure train v14 직접 작성 감사

- 감사일: 2026-09-02 KST
- 판정: **PASS**
- reservation: `S2-A01-T-014`
- family: `클라우드 서비스 부하·장애 대응 — 개입 전후 결과와 자연 변동 구분`
- corpus: `stage2_highdensity_dataset/train/stage2_(11)causal_structure_high_density_train_v14.json`
- source: `stage2_highdensity_dataset/sources/train/stage2_(11)causal_structure_high_density_train_v14.source.jsonl`

## 1. 작성·포장 경계

150개의 primary concept, `text`, `relations`를 record별로 직접 작성했다. 자동 semantic-composition, 명사 치환 template, relation round-robin은 사용하지 않았다. 자동화는 JSONL parse, source 계약 검사, ID·고정 metadata 부여, tokenizer·중복·문법·유사도 감사에만 사용했다.

원고는 자동 확장·캐시·배포·데이터베이스·큐·저장소·네트워크·보안·관측·복구 개입의 전후 결과를 같은 시간대의 자연 부하, 주기, 외부 사건 및 구성 변화와 분리한다. 후반부는 휴일·요일·월말·기상·공급자 점검·JIT·콜드 스타트·계측 지연처럼 전후 비교를 교란하는 자연 변동을 다룬다.

초안 단계에서 예약량을 넘겨 작성된 56행은 corpus 포장 전에 제외해 T014를 정확히 150행으로 맞췄다. 제외 행은 어떤 다른 예약에도 자동 전용하지 않았고 canonical corpus에는 포함되지 않았다. source check 뒤 corpus를 포장했으며 누적 교차 5-word n-gram 반복은 처음부터 0건이었다.

## 2. 구조·직렬화

| 검사 | 결과 |
|---|---:|
| source rows / corpus records | 150 / 150 |
| primary unique / text unique | 150 / 150 |
| ID first / last | `S2-CSH-01951` / `S2-CSH-02100` |
| source↔corpus projection 오류 | 0 |
| JSON/JSONL parse 오류 | 0 |
| primary 본문 literal 누락 | 0 |
| 통제어휘 밖 relation | 0 |
| record 내부 relation 중복 | 0 |
| relation cardinality | 4개: 150 records |
| 고유 relation-set / 단일 최대 빈도 | 36 / 22 records |
| `other_type` 불일치 | 0 |

## 3. Relations 분포

총 relation 배정은 600회다.

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 18 |
| `classification` | 62 |
| `boundary` | 150 |
| `contrast` | 14 |
| `comparison` | 131 |
| `function` | 43 |
| `role` | 3 |
| `process` | 71 |
| `state` | 41 |
| `attribute` | 67 |
| `other` | 0 |

`comparison`은 동일 조건의 전후·통제군 차이를, `process`는 설정 적용과 결과 발현의 시간 경로를, `classification`은 자연 주기·외부 교란·실제 노출 집단을 구분하는 판정을 나타낸다. `boundary`는 단순 전후 차이와 개입 효과의 경계를 명시하므로 모든 레코드에 부여했다. `other`가 0회이므로 자주 나온 `other_type` 5가지는 해당 없음이다.

## 4. 중복·유사도·보일러플레이트

| 검사 | 결과 |
|---|---:|
| exact primary/text/normalized text 중복 | 0 |
| primary+relation-set 중복 | 0 |
| cross-record 5-word n-gram 반복 | 0 / 3,098 assignments |
| v14 내부 normalized character similarity ≥ 0.80 | 0 pairs |
| v14 내부 최대 character similarity | 0.549223 |
| v14 내부 word-set Jaccard ≥ 0.60 | 0 pairs |
| v14 내부 최대 word-set Jaccard | 0.216216 |
| 기존 Stage2 train 2,250 records 교차 character similarity ≥ 0.80 | 0 pairs |
| 기존 Stage2 train 교차 최대 character similarity | 0.473373 |
| 기존 Stage2 train 교차 word-set Jaccard ≥ 0.60 | 0 pairs |
| 기존 Stage2 train 교차 최대 word-set Jaccard | 0.159091 |
| generic shape fingerprint | 39종, 단일 최대 17/150 = 11.33% |

lexical 5-gram과 두 fuzzy 기준의 고유사 pair는 내부·기존 Stage2 train 교차 비교에서 모두 0이다. generic shape 최대군은 primary를 첫머리에 두는 두 문장 형식의 어절 수가 같은 행을 묶은 표면 지문이며, 실제 5-gram 반복·문자 고유사·단어집합 고유사는 없어 보일러플레이트 오류로 판정하지 않았다.

## 5. 한국어·token 감사

- exact tokenizer: `tok-ko-en-32768.json`, SHA-256 `3a69001ecc28a5bdf1e951a1036b234c9bdcb847b310252c6d72cfc6c52c48e3`
- 평균: 44.800000 tokens/record(+EOS)
- 최소/최대: 38 / 52
- Stage2 승인 평균: 41.625, 허용범위 ±10% = 37.4625~45.7875 — file mean PASS
- text 문자 길이: 최소 82, 평균 94.327, 최대 108
- hard grammar finding: 0
- 조사 휴리스틱 warning: 18

18개 warning 행을 직접 읽었다. 모두 `효과와` 내부의 `과와`를 조사 의심 패턴으로 잡은 false positive였고 실제 조사 불일치는 없다. 포장 전 `중복 리더은`, `동시 처리은` 두 표현은 각각 `중복 리더는`, `동시 처리는`으로 직접 교정했다.

## 6. 해시와 최종 판정

- source SHA-256: `fda7e4a3c5d13a13f0a219bf8514a2446701b4579e046762240f8aa64e0722ae`
- corpus SHA-256: `dff92faf208bc2d7f50c5930079604818c8ec9e56a4dbfddfb11a17f64dc9d31`
- resume checkpoint SHA-256: `1cec4e35867258be1d153be6256bd829069485a22129e41e080d8d4f08265451`
- central ledger SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`

`--require-complete --check-only` 감사에서 source 1·corpus 1, missing 0, structural PASS, direct-authoring debt 0을 확인했다. 전체 부분 감사도 49 source/corpus pairs·7,350 records에서 구조·exact/normalized 중복·train/validation exact leakage·5-word n-gram 반복·hard grammar·manual-review debt 모두 0으로 PASS했다. Stage1·저밀도·held-out·기존 Stage2~10 pilot과 v02~v13은 수정하지 않았다.

다음 예약은 `S2-A01-T-015`, `stage2_(11)causal_structure_high_density_train_v15.json`, ID `S2-CSH-02101 ~ S2-CSH-02250`, family `클라우드 서비스 부하·장애 대응 — 다중 원인의 충분성·기여 범위`다.
