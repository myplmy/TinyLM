# TinyLM Stage2 causal_structure train v27 직접 작성 감사

- 감사일: 2026-09-02 KST
- 판정: **PASS**
- reservation: `S2-A01-T-027`
- family: `식품 냉장 유통·품질 유지 — 공통 원인과 거짓 상관 통제`
- corpus: `stage2_highdensity_dataset/train/stage2_(11)causal_structure_high_density_train_v27.json`
- source: `stage2_highdensity_dataset/sources/train/stage2_(11)causal_structure_high_density_train_v27.source.jsonl`

## 1. 작성·포장 경계

150개의 primary concept, `text`, `relations`를 record별로 직접 작성했다. 자동 semantic-composition, 명사 치환 template, relation round-robin은 사용하지 않았다. 자동화는 JSONL parse, source 계약 검사, ID·고정 metadata 부여, tokenizer·중복·문법·유사도 감사에만 사용했다.

원고는 냉장유통에서 계절·노선·품목·초기품질·장비·운영·선별·감시·측정이 노출과 결과를 함께 바꾸는 공통 원인을 다룬다. 역인과, 충돌변수 조건화, 표본선택, 검열·결측, 집계·시간추세, 계측 공통오류를 거짓 상관의 원천으로 구별하고, 매칭·층화·고정효과·시차도입·음성대조·위약·민감도·잔차 감사로 통제 가능성을 검토한다.

최초 150행 source는 구조계약을 만족했지만 tokenizer 평균이 46.906667(+EOS)로 상한을 넘었다. 의미를 유지한 직접 압축을 두 차례 수행해 source gate 평균 45.453333으로 통과했다. package 후 전체 감사에서 v07과 공유한 `시간이 어긋나 결과가 원인보다 먼저` 5-word n-gram 1종을 발견해, v27 로거시계 record를 시각 기준 차이와 공통축 재정렬 설명으로 직접 다시 썼다. source·corpus·checkpoint SHA를 동기화한 최종 평균은 45.500000이고 누적 반복은 0이다.

## 2. 구조·직렬화

| 검사 | 결과 |
|---|---:|
| source rows / corpus records | 150 / 150 |
| primary unique / text unique | 150 / 150 |
| ID first / last | `S2-CSH-03901` / `S2-CSH-04050` |
| source↔corpus projection 오류 | 0 |
| JSON/JSONL parse 오류 | 0 |
| primary 본문 literal 누락 | 0 |
| 통제어휘 밖 relation | 0 |
| record 내부 relation 중복 | 0 |
| relation cardinality | 4개: 150 records |
| 고유 relation-set / 단일 최대 빈도 | 32 / 19 records |
| `other_type` 불일치 | 0 |

## 3. Relations 분포

총 relation 배정은 600회다.

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 42 |
| `classification` | 142 |
| `boundary` | 150 |
| `contrast` | 54 |
| `comparison` | 82 |
| `function` | 21 |
| `role` | 19 |
| `process` | 38 |
| `state` | 24 |
| `attribute` | 28 |
| `other` | 0 |

`classification`은 공통원인·역인과·충돌변수·선택·측정편향과 통제설계의 지위를, `comparison`은 층화·매칭·대조·통제 전후 차이를, `contrast`는 상관과 인과 및 측정착시와 실제 변화를 구별한다. `boundary`는 단순 연관을 원인으로 확정하지 않도록 모든 record에 부여했다. `other`가 0회이므로 자주 나온 `other_type` 5가지는 해당 없음이다.

## 4. 중복·유사도·보일러플레이트

| 검사 | 결과 |
|---|---:|
| exact primary/text/normalized text 중복 | 0 |
| primary+relation-set 중복 | 0 |
| v27 내부 cross-record 5-word n-gram 반복 | 0 / 2,441 assignments |
| 현행 전체 62파일 cross-record 5-word n-gram 반복 | 0 / 170,388 assignments |
| v27 내부 normalized character similarity ≥ 0.80 | 0 pairs |
| v27 내부 최대 character similarity | 0.458015 |
| v27 내부 word-set Jaccard ≥ 0.60 | 0 pairs |
| v27 내부 최대 word-set Jaccard | 0.162162 |
| 기존 Stage2 train 4,200 records 교차 character similarity ≥ 0.80 | 0 pairs |
| 기존 Stage2 train 교차 최대 character similarity | 0.564885 |
| 기존 Stage2 train 교차 word-set Jaccard ≥ 0.60 | 0 pairs |
| 기존 Stage2 train 교차 최대 word-set Jaccard | 0.250000 |
| generic shape fingerprint | 62종, 단일 최대 11/150 = 7.33% |

최초 누적 5-word 반복 1종은 직접 수정해 제거했다. 최종 lexical 5-gram, 문자 유사도, 단어집합 Jaccard에서 내부·기존 Stage2 train 교차 검토선을 넘은 pair가 없다. generic shape 최대 점유는 7.33%이며 명사 치환 보일러플레이트 증거는 발견되지 않았다.

## 5. 한국어·token 감사

- exact tokenizer: `tok-ko-en-32768.json`, SHA-256 `3a69001ecc28a5bdf1e951a1036b234c9bdcb847b310252c6d72cfc6c52c48e3`
- 최종 평균: 45.500000 tokens/record(+EOS)
- 최종 최소/최대: 30 / 55
- Stage2 승인 평균: 41.625, 허용범위 ±10% = 37.4625~45.7875 — file mean PASS
- text 문자 길이: 최소 59, 평균 85.833, 최대 98
- hard grammar finding: 0
- 조사 휴리스틱 warning: 11

11개 warning 위치를 전수 읽었다. `차이가`, `결과와`, `효과와`, `나이가`처럼 정상 단어 내부를 보수적으로 잡은 false positive이며 실제 조사 불일치는 없다.

## 6. 해시와 최종 판정

- source SHA-256: `b2ed66372f52c592b5a7a8d8e096fd81e4bb8afcd75f782e91a32cea0cfabc12`
- corpus SHA-256: `d5f901130c2d504760990afda58fd9583f26db7b2097fbcd3b2f59c507dd6e7a`
- resume checkpoint SHA-256: `fbe4ac3182ae685e3a860c5fd4015f83ace6d741234dbe8801cde9a077b54dad`
- central ledger SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`

`--require-complete --check-only` 감사에서 source 1·corpus 1, missing 0, structural PASS, direct-authoring debt 0을 확인했다. 전체 부분 감사도 62 source/corpus pairs·9,300 records에서 구조·exact/normalized 중복·train/validation exact leakage·5-word n-gram 반복·hard grammar·manual-review debt 모두 0으로 PASS했다. Stage2 누적 4,500 records의 exact tokenizer 평균은 43.091111(+EOS)으로 gate PASS다. 보호 대상 변경은 없다.

다음 예약은 `S2-A01-T-028`, `stage2_(11)causal_structure_high_density_train_v28.json`, ID `S2-CSH-04051 ~ S2-CSH-04200`, family `식품 냉장 유통·품질 유지 — 원인 방향·피드백·역인과 판정`이다.
