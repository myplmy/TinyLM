# TinyLM Stage2 causal_structure train v11 직접 작성 감사

- 감사일: 2026-09-02 KST
- 판정: **PASS**
- reservation: `S2-A01-T-011`
- family: `클라우드 서비스 부하·장애 대응 — 직접 원인·매개 경로·배경 조건 분리`
- corpus: `stage2_highdensity_dataset/train/stage2_(11)causal_structure_high_density_train_v11.json`
- source: `stage2_highdensity_dataset/sources/train/stage2_(11)causal_structure_high_density_train_v11.source.jsonl`

## 1. 작성·포장 경계

150개의 primary concept, `text`, `relations`를 record별로 직접 작성했다. 자동 semantic-composition, 명사 치환 template, relation round-robin은 사용하지 않았다. 자동화는 JSONL parse, source 계약 검사, ID·고정 metadata 부여, tokenizer·중복·문법·유사도 감사에만 사용했다.

원고는 클라우드 서비스의 자원 고갈·설정·네트워크·의존성 실패 같은 직접 원인, 큐·재시도·캐시·복제·복구가 전달하는 매개 경로, 용량·시간대·운영 문맥의 배경 조건을 구분한다. 후반부는 시간선, 롤백, 카나리, 대조 엔드포인트, 추적, 반사실과 증거 강도별 원인 보고를 다룬다.

## 2. 구조·직렬화

| 검사 | 결과 |
|---|---:|
| source rows / corpus records | 150 / 150 |
| primary unique / text unique | 150 / 150 |
| ID first / last | `S2-CSH-01501` / `S2-CSH-01650` |
| source↔corpus projection 오류 | 0 |
| JSON/JSONL parse 오류 | 0 |
| primary 본문 literal 누락 | 0 |
| 통제어휘 밖 relation | 0 |
| record 내부 relation 중복 | 0 |
| relation cardinality | 4개: 150 records |
| 고유 relation-set / 단일 최대 빈도 | 44 / 10 records |
| `other_type` 불일치 | 0 |

## 3. Relations 분포

총 relation 배정은 600회다.

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 51 |
| `classification` | 81 |
| `boundary` | 150 |
| `contrast` | 43 |
| `comparison` | 56 |
| `function` | 19 |
| `role` | 14 |
| `process` | 94 |
| `state` | 59 |
| `attribute` | 33 |
| `other` | 0 |

`process`는 직접 원인이 매개 사건을 거쳐 결과로 전달되는 순서를, `classification`은 직접·매개·배경·증거 수준의 판정을, `part_of`는 다단계 경로의 구성 요소를 나타낸다. `boundary`는 징후·복구·책임·취약 조건과 직접 원인을 혼동하지 않도록 모든 레코드에 부여했다. `other`가 0회이므로 자주 나온 `other_type` 5가지는 해당 없음이다.

## 4. 중복·유사도·보일러플레이트

| 검사 | 결과 |
|---|---:|
| exact primary/text/normalized text 중복 | 0 |
| primary+relation-set 중복 | 0 |
| cross-record 5-word n-gram 반복 | 0 / 3,156 assignments |
| v11 내부 normalized character similarity ≥ 0.80 | 0 pairs |
| v11 내부 최대 character similarity | 0.402685 |
| v11 내부 word-set Jaccard ≥ 0.60 | 0 pairs |
| v11 내부 최대 word-set Jaccard | 0.190476 |
| 기존 Stage2 train 1,800 records 교차 character similarity ≥ 0.80 | 0 pairs |
| 기존 Stage2 train 교차 최대 character similarity | 0.384000 |
| 기존 Stage2 train 교차 word-set Jaccard ≥ 0.60 | 0 pairs |
| 기존 Stage2 train 교차 최대 word-set Jaccard | 0.190476 |
| generic shape fingerprint | 72종, 단일 최대 10/150 = 6.67% |

lexical 5-gram과 두 fuzzy 기준의 고유사 pair는 내부·기존 Stage2 train 교차 비교에서 모두 0이다. 최대값도 차단 임계보다 충분히 낮고, exact·normalized 중복이나 primary+relation-set 중복은 없다.

## 5. 한국어·token 감사

- exact tokenizer: `tok-ko-en-32768.json`, SHA-256 `3a69001ecc28a5bdf1e951a1036b234c9bdcb847b310252c6d72cfc6c52c48e3`
- 평균: 45.386667 tokens/record(+EOS)
- 최소/최대: 38 / 55
- Stage2 승인 평균: 41.625, 허용범위 ±10% = 37.4625~45.7875 — file mean PASS
- text 문자 길이: 최소 83, 평균 96.693, 최대 113
- hard grammar finding: 0
- 조사 휴리스틱 warning: 6

6개 warning 행을 직접 읽었다. `초과와`, `차이가`, `결과와`, `효과와` 같은 정상 어휘 내부를 조사 의심 패턴으로 탐지한 false positive이며, 실제 은/는·이/가·을/를·와/과 불일치는 없다.

## 6. 해시와 최종 판정

- source SHA-256: `a94340dd36ceb3c9afd80ff2acbb15477b87becbef28d482732591079d5fb4e3`
- corpus SHA-256: `0a374e29f01ce5bb821902f83b7e4efb2b144acd8bc2c18a584c140167c9cbb0`
- resume checkpoint SHA-256: `d8ee5f23ac631daf9ea0d893a4e09ac7b2bc4e99744300350b2891686999b58c`
- central ledger SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`

`--require-complete --check-only` 감사에서 source 1·corpus 1, missing 0, structural PASS, direct-authoring debt 0을 확인했다. 전체 부분 감사도 46 source/corpus pairs·6,900 records에서 구조·exact/normalized 중복·train/validation exact leakage·5-word n-gram 반복·hard grammar·manual-review debt 모두 0으로 PASS했다. Stage1·저밀도·held-out·기존 Stage2~10 pilot과 v02~v10은 수정하지 않았다.

다음 예약은 `S2-A01-T-012`, `stage2_(11)causal_structure_high_density_train_v12.json`, ID `S2-CSH-01651 ~ S2-CSH-01800`, family `클라우드 서비스 부하·장애 대응 — 공통 원인과 거짓 상관 통제`다.
