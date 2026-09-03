# TinyLM Stage2 causal_structure train v30 직접 작성 감사

- 감사일: 2026-09-02 KST
- 판정: **PASS**
- reservation: `S2-A01-T-030`
- family: `식품 냉장 유통·품질 유지 — 다중 원인의 충분성·기여 범위`
- corpus: `stage2_highdensity_dataset/train/stage2_(11)causal_structure_high_density_train_v30.json`
- source: `stage2_highdensity_dataset/sources/train/stage2_(11)causal_structure_high_density_train_v30.source.jsonl`

## 1. 작성·포장 경계

150개의 primary concept, `text`, `relations`를 record별로 직접 작성했다. 자동 semantic-composition, 명사 치환 template, relation round-robin은 사용하지 않았다. 자동화는 JSONL parse, source 계약 검사, ID·고정 metadata 부여, tokenizer·중복·문법·유사도 감사에만 사용했다.

원고는 냉장유통 품질손실의 여러 충분경로, 필요·불충분 조건, 개별 원인의 기여, 상승·보완·대체·중복 작용, 문턱·포화, 원인제거와 예방가능 범위, 개별·집단 귀속, 매개경로, 중복계산과 배분규칙, 측정오차·결측·간섭이 만드는 기여범위를 구분한다. 단일 주원인 대신 고온증식·누설산화·초기오염·물리손상 경로를 각각 판정하도록 구성했다.

첫 작성분은 148행으로 계수되어 패키징 전에 중단했고, 구성원인 제거 뒤 남는 충분경로와 모든 경로 폐쇄의 예방상한 2행을 직접 보충했다. 완성 source는 최초 평균 40.800000(+EOS)으로 구조·token gate를 통과했다. package 뒤 파일·전체 감사에서 반복 5-word n-gram은 발견되지 않아 source·corpus 추가 수정은 없었다.

## 2. 구조·직렬화

| 검사 | 결과 |
|---|---:|
| source rows / corpus records | 150 / 150 |
| primary unique / text unique | 150 / 150 |
| ID first / last | `S2-CSH-04351` / `S2-CSH-04500` |
| source↔corpus projection 오류 | 0 |
| JSON/JSONL parse 오류 | 0 |
| primary 본문 literal 누락 | 0 |
| 통제어휘 밖 relation | 0 |
| record 내부 relation 중복 | 0 |
| relation cardinality | 3개: 31 records, 4개: 119 records |
| 고유 relation-set / 단일 최대 빈도 | 48 / 11 records |
| `other_type` 불일치 | 0 |

## 3. Relations 분포

총 relation 배정은 569회다.

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 31 |
| `classification` | 92 |
| `boundary` | 150 |
| `contrast` | 51 |
| `comparison` | 73 |
| `function` | 39 |
| `role` | 15 |
| `process` | 72 |
| `state` | 15 |
| `attribute` | 31 |
| `other` | 0 |

`classification`은 필요·충분·대체·중복·귀속·배분규칙의 판정 지위를, `comparison`은 원인 제거 전후와 조건별 한계기여를, `process`와 `part_of`는 충분경로와 매개경로의 시간·구성 관계를 나타낸다. `boundary`는 모든 record에서 원인성분과 충분조건, 개별효과와 집단기여, 기여판정과 책임판정의 경계를 명시한다. `other`가 0회이므로 자주 나온 `other_type` 5가지는 해당 없음이다.

## 4. 중복·유사도·보일러플레이트

| 검사 | 결과 |
|---|---:|
| exact primary/text/normalized text 중복 | 0 |
| primary+relation-set 중복 | 0 |
| v30 내부 cross-record 5-word n-gram 반복 | 0 / 2,099 assignments |
| 현행 전체 65파일 cross-record 5-word n-gram 반복 | 0 / 177,158 assignments |
| v30 내부 normalized character similarity ≥ 0.80 | 0 pairs |
| v30 내부 최대 character similarity | 0.422764 |
| v30 내부 word-set Jaccard ≥ 0.60 | 0 pairs |
| v30 내부 최대 word-set Jaccard | 0.176471 |
| 기존 Stage2 train 4,650 records 교차 character similarity ≥ 0.80 | 0 pairs |
| 기존 Stage2 train 교차 최대 character similarity | 0.573643 |
| 기존 Stage2 train 교차 word-set Jaccard ≥ 0.60 | 0 pairs |
| 기존 Stage2 train 교차 최대 word-set Jaccard | 0.242424 |
| generic shape fingerprint | 59종, 단일 최대 12/150 = 8.00% |

최종 lexical 5-gram, 문자 유사도, 단어집합 Jaccard에서 내부·기존 Stage2 train 교차 검토선을 넘은 pair가 없다. generic shape 최대 점유는 8.00%이며 명사 치환 보일러플레이트 증거는 발견되지 않았다.

## 5. 한국어·token 감사

- exact tokenizer: `tok-ko-en-32768.json`, SHA-256 `3a69001ecc28a5bdf1e951a1036b234c9bdcb847b310252c6d72cfc6c52c48e3`
- 최종 평균: 40.800000 tokens/record(+EOS)
- 최종 최소/최대: 32 / 48
- Stage2 승인 평균: 41.625, 허용범위 ±10% = 37.4625~45.7875 — file mean PASS
- text 문자 길이: 최소 61, 평균 75.167, 최대 91
- hard grammar finding: 0
- 조사 휴리스틱 warning: 15

15개 warning 위치를 전수 읽었다. `차이가`, `효과와`, `냉각이`, `할인이`, `과적이`, `오염이`처럼 정상 단어 내부를 보수적으로 잡은 false positive이며 실제 조사 불일치는 없다.

## 6. 해시와 최종 판정

- source SHA-256: `71fe37bddb31e6f746e71b5d3cc96de778585288426a694555747f4e39a1f950`
- corpus SHA-256: `08dafd39ccb6b522453574328163e0f5ba1e093123189b6a19e3450cf4ba10b7`
- resume checkpoint SHA-256: `6309703f9d4e1cb8b8be37f68295bdb18cbb06a5516cfd781812630885c33a51`
- central ledger SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`

`--require-complete --check-only` 감사에서 source 1·corpus 1, missing 0, structural PASS, direct-authoring debt 0을 확인했다. 전체 부분 감사도 65 source/corpus pairs·9,750 records에서 구조·exact/normalized 중복·train/validation exact leakage·5-word n-gram 반복·hard grammar·manual-review debt 모두 0으로 PASS했다. Stage2 누적 4,950 records(현행 validation 포함)의 exact tokenizer 평균은 43.052323(+EOS)으로 gate PASS다. 보호 대상 변경은 없다.

다음 예약은 `S2-A01-T-031`, `stage2_(11)causal_structure_high_density_train_v31.json`, ID `S2-CSH-04501 ~ S2-CSH-04650`, family `온라인 학습 진도·피드백 운영 — 직접 원인·매개 경로·배경 조건 분리`다.
