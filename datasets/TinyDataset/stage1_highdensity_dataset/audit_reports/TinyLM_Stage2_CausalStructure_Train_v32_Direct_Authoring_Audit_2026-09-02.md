# TinyLM Stage2 causal_structure train v32 직접 작성 감사

- 감사일: 2026-09-02 KST
- 판정: **PASS**
- reservation: `S2-A01-T-032`
- family: `온라인 학습 진도·피드백 운영 — 공통 원인과 거짓 상관 통제`
- corpus: `stage2_highdensity_dataset/train/stage2_(11)causal_structure_high_density_train_v32.json`
- source: `stage2_highdensity_dataset/sources/train/stage2_(11)causal_structure_high_density_train_v32.source.jsonl`

## 1. 작성·포장 경계

150개의 primary concept, `text`, `relations`를 record별로 직접 작성했다. 자동 semantic-composition, 명사 치환 template, relation round-robin은 사용하지 않았다. 자동화는 JSONL parse, source 계약 검사, ID·고정 metadata 부여, tokenizer·중복·문법·유사도 감사에만 사용했다.

원고는 온라인 학습에서 선수지식·가용시간·기기·회선·동기·강좌난도 같은 공통원인, 위험대상 지원·맞춤해설·재응시의 역배정과 자기선택, 로그 누락·집계경계·생존자 표본의 측정편향을 구분한다. 완료자·합격자·참여자에 조건화해 열리는 충돌경로와 층화·매칭·무작위화·음성대조·위약검사로 거짓 상관을 점검하는 사례도 포함했다.

첫 직접 작성 150행의 tokenizer 평균은 49.173333(+EOS)으로 상한을 넘어 source gate가 차단했다. 의미와 relations를 유지하면서 가장 긴 후행 설명을 두 차례 직접 압축해 최종 평균 45.700000으로 낮췄다. 포장 전 source-only 단일·전체 감사에서 exact/normalized 중복과 5-word 반복이 0임을 확인했다. package 뒤 추가 수정은 없었다.

## 2. 구조·직렬화

| 검사 | 결과 |
|---|---:|
| source rows / corpus records | 150 / 150 |
| primary unique / text unique | 150 / 150 |
| ID first / last | `S2-CSH-04651` / `S2-CSH-04800` |
| source↔corpus projection 오류 | 0 |
| JSON/JSONL parse 오류 | 0 |
| primary 본문 literal 누락 | 0 |
| 통제어휘 밖 relation | 0 |
| record 내부 relation 중복 | 0 |
| relation cardinality | 4개: 150 records |
| 고유 relation-set / 단일 최대 빈도 | 52 / 10 records |
| `other_type` 불일치 | 0 |

## 3. Relations 분포

총 relation 배정은 600회다.

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 18 |
| `classification` | 90 |
| `boundary` | 150 |
| `contrast` | 54 |
| `comparison` | 57 |
| `function` | 40 |
| `role` | 32 |
| `process` | 63 |
| `state` | 58 |
| `attribute` | 38 |
| `other` | 0 |

`classification`은 공통원인·자기선택·역배정·측정편향·충돌조건의 판정 지위를, `comparison`과 `contrast`는 층화 전후 및 단순 상관과 원인효과의 차이를 담는다. `process`와 `part_of`는 시간·집계·경로 구조를, `function`과 `role`은 플랫폼 기능과 교사·상담자 개입을, `state`와 `attribute`는 동기·환경·난도·기기 조건을 나타낸다. `boundary`는 150개 모두에서 상관과 인과 또는 선택표본과 모집단의 경계를 뒷받침한다. `other`가 0회이므로 자주 나온 `other_type` 5가지는 해당 없음이다.

## 4. 중복·유사도·보일러플레이트

| 검사 | 결과 |
|---|---:|
| exact primary/text/normalized text 중복 | 0 |
| primary+relation-set 중복 | 0 |
| v32 내부 cross-record 5-word n-gram 반복 | 0 / 2,333 assignments |
| 현행 전체 67파일 cross-record 5-word n-gram 반복 | 0 / 181,373 assignments |
| v32 내부 normalized character similarity ≥ 0.80 | 0 pairs |
| v32 내부 최대 character similarity | 0.407080 |
| v32 내부 word-set Jaccard ≥ 0.60 | 0 pairs |
| v32 내부 최대 word-set Jaccard | 0.214286 |
| 기존 Stage2 train 4,950 records 교차 character similarity ≥ 0.80 | 0 pairs |
| 기존 Stage2 train 교차 최대 character similarity | 0.430556 |
| 기존 Stage2 train 교차 word-set Jaccard ≥ 0.60 | 0 pairs |
| 기존 Stage2 train 교차 최대 word-set Jaccard | 0.171429 |
| generic shape fingerprint | 47종, 단일 최대 10/150 = 6.67% |

최종 lexical 5-gram, 문자 유사도, 단어집합 Jaccard에서 내부·기존 Stage2 train 교차 검토선을 넘은 pair가 없다. 짧게 압축한 문장도 primary와 원인 판정 근거를 유지했고, generic shape 최대 점유는 6.67%다.

## 5. 한국어·token 감사

- exact tokenizer: `tok-ko-en-32768.json`, SHA-256 `3a69001ecc28a5bdf1e951a1036b234c9bdcb847b310252c6d72cfc6c52c48e3`
- 최종 평균: 45.700000 tokens/record(+EOS)
- 최종 최소/최대: 37 / 50
- Stage2 승인 평균: 41.625, 허용범위 ±10% = 37.4625~45.7875 — file mean PASS
- text 문자 길이: 최소 65, 평균 86.573, 최대 102
- hard grammar finding: 0
- 조사 휴리스틱 warning: 21

21개 warning 위치를 전수 읽었다. `기기성능이`, `수강인원이`, `시간대차이가`, `시험지버전난도가`, `단원주제가`, `효과와`, `자원효과와`, `기능효과와`처럼 정상 단어 내부를 보수적으로 잡은 false positive이며 실제 조사 불일치는 없다.

## 6. 해시와 최종 판정

- source SHA-256: `09c653990c8da6e0b9f4e08dd6cbec3389d5c8c234b50faefb56f6002d5dc9d4`
- corpus SHA-256: `1513b3e14d523a5a2c83bdbf507008adfd302830a34cde8ad65fdde603220de6`
- resume checkpoint SHA-256: `a767d22edcb97d39771f86f1feb38018687a9d086941436f8b2f5e448f1e2713`
- central ledger SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`

`--require-complete --check-only` 감사에서 source 1·corpus 1, missing 0, structural PASS, direct-authoring debt 0을 확인했다. 전체 부분 감사도 67 source/corpus pairs·10,050 records에서 구조·exact/normalized 중복·train/validation exact leakage·5-word n-gram 반복·hard grammar·manual-review debt 모두 0으로 PASS했다. Stage2 누적 5,250 records(현행 validation 포함)의 exact tokenizer 평균은 42.993333(+EOS)으로 gate PASS다. 보호 대상 변경은 없다.

다음 예약은 `S2-A01-T-033`, `stage2_(11)causal_structure_high_density_train_v33.json`, ID `S2-CSH-04801 ~ S2-CSH-04950`, family `온라인 학습 진도·피드백 운영 — 원인 방향·피드백·역인과 판정`이다.
