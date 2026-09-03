# TinyLM Stage2 causal_structure train v10 직접 작성 감사

- 감사일: 2026-09-02 KST
- 판정: **PASS**
- reservation: `S2-A01-T-010`
- family: `도시 상수도 정수·배수 운영 — 다중 원인의 충분성·기여 범위`
- corpus: `stage2_highdensity_dataset/train/stage2_(11)causal_structure_high_density_train_v10.json`
- source: `stage2_highdensity_dataset/sources/train/stage2_(11)causal_structure_high_density_train_v10.source.jsonl`

## 1. 작성·포장 경계

150개의 primary concept, `text`, `relations`를 record별로 직접 작성했다. 자동 semantic-composition, 명사 치환 template, relation round-robin은 사용하지 않았다. 자동화는 JSONL parse, source 계약 검사, ID·고정 metadata 부여, tokenizer·중복·문법·유사도 감사에만 사용했다.

PC 중단 뒤 확인한 source는 133행이었다. 기존 133행을 보존하고 누락된 17행을 같은 의미축에서 직접 작성해 150행을 완성했다. 원고는 복합 원인, 필요·충분 조건, 독립·상호작용 기여, 매개 경로, 누락 원인, 잔차, 조건부·누적 기여와 기여 구간의 해석 경계를 다룬다.

## 2. 구조·직렬화

| 검사 | 결과 |
|---|---:|
| source rows / corpus records | 150 / 150 |
| primary unique / text unique | 150 / 150 |
| ID first / last | `S2-CSH-01351` / `S2-CSH-01500` |
| source↔corpus projection 오류 | 0 |
| JSON/JSONL parse 오류 | 0 |
| primary 본문 literal 누락 | 0 |
| 통제어휘 밖 relation | 0 |
| record 내부 relation 중복 | 0 |
| relation cardinality | 3개: 4 records, 4개: 146 records |
| 고유 relation-set / 단일 최대 빈도 | 46 / 12 records |
| `other_type` 불일치 | 0 |

## 3. Relations 분포

총 relation 배정은 596회다.

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 77 |
| `classification` | 90 |
| `boundary` | 150 |
| `contrast` | 21 |
| `comparison` | 73 |
| `function` | 22 |
| `role` | 21 |
| `process` | 42 |
| `state` | 43 |
| `attribute` | 57 |
| `other` | 0 |

`part_of`는 여러 원인의 공동 구성과 전체 기여 중 부분 몫을, `classification`은 필요·충분·독립·상호작용 기여의 판정을, `comparison`은 원인별 크기와 범위 비교를 나타낸다. `boundary`는 원인의 존재, 충분성, 기여율, 책임 배분을 혼동하지 않도록 모든 레코드에 부여했다. `other`가 0회이므로 자주 나온 `other_type` 5가지는 해당 없음이다.

## 4. 중복·유사도·보일러플레이트

| 검사 | 결과 |
|---|---:|
| exact primary/text/normalized text 중복 | 0 |
| primary+relation-set 중복 | 0 |
| cross-record 5-word n-gram 반복 | 0 / 2,603 assignments |
| v10 내부 normalized character similarity ≥ 0.80 | 0 pairs |
| v10 내부 최대 character similarity | 0.525424 |
| v10 내부 word-set Jaccard ≥ 0.60 | 0 pairs |
| v10 내부 최대 word-set Jaccard | 0.235294 |
| 기존 Stage2 train 1,650 records 교차 character similarity ≥ 0.80 | 0 pairs |
| 기존 Stage2 train 교차 최대 character similarity | 0.564516 |
| 기존 Stage2 train 교차 word-set Jaccard ≥ 0.60 | 0 pairs |
| 기존 Stage2 train 교차 최대 word-set Jaccard | 0.290323 |
| generic shape fingerprint | 117종, 단일 최대 5/150 = 3.33% |

lexical 5-gram과 두 fuzzy 기준의 고유사 pair는 내부·기존 Stage2 train 교차 비교에서 모두 0이다. 최대값도 차단 임계보다 충분히 낮고, exact·normalized 중복이나 primary+relation-set 중복은 없다.

## 5. 한국어·token 감사

- exact tokenizer: `tok-ko-en-32768.json`, SHA-256 `3a69001ecc28a5bdf1e951a1036b234c9bdcb847b310252c6d72cfc6c52c48e3`
- 평균: 42.106667 tokens/record(+EOS)
- 최소/최대: 33 / 52
- Stage2 승인 평균: 41.625, 허용범위 ±10% = 37.4625~45.7875 — file mean PASS
- text 문자 길이: 최소 67, 평균 82.280, 최대 104
- hard grammar finding: 0
- 조사 휴리스틱 warning: 2

2개 warning 행을 직접 읽었다. `다중 원인의 합산 효과와 상호작용`, `요인설계로 분리한 주효과와 상호작용`의 정상 단어 `효과와` 내부를 조사 의심 패턴으로 탐지한 false positive이며, 실제 은/는·이/가·을/를·와/과 불일치는 없다.

## 6. 해시와 최종 판정

- source SHA-256: `f38ff62c040d9340dfe2fdcecbdf59b0c56478a83cda4ca9319b3bc236a12bed`
- corpus SHA-256: `63657393a92706c8e7ff1a0b7c6a58d51219664f015ba382176d6cc935faec13`
- resume checkpoint SHA-256: `f1f78e7ce5d98ffc008bebe936eabe5a43787d9231834b55829f140792d5d97e`
- central ledger SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`

`--require-complete --check-only` 감사에서 source 1·corpus 1, missing 0, structural PASS, direct-authoring debt 0을 확인했다. 전체 부분 감사도 45 source/corpus pairs·6,750 records에서 구조·exact/normalized 중복·train/validation exact leakage·5-word n-gram 반복·hard grammar·manual-review debt 모두 0으로 PASS했다. Stage1·저밀도·held-out·기존 Stage2~10 pilot과 v02~v09는 수정하지 않았다.

다음 예약은 `S2-A01-T-011`, `stage2_(11)causal_structure_high_density_train_v11.json`, ID `S2-CSH-01501 ~ S2-CSH-01650`, family `클라우드 서비스 부하·장애 대응 — 직접 원인·매개 경로·배경 조건 분리`다.
