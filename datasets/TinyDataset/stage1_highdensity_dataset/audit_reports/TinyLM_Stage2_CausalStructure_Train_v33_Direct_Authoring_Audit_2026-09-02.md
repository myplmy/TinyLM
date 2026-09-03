# TinyLM Stage2 causal_structure train v33 직접 작성 감사

- 감사일: 2026-09-02 KST
- 판정: **PASS**
- reservation: `S2-A01-T-033`
- family: `온라인 학습 진도·피드백 운영 — 원인 방향·피드백·역인과 판정`
- corpus: `stage2_highdensity_dataset/train/stage2_(11)causal_structure_high_density_train_v33.json`
- source: `stage2_highdensity_dataset/sources/train/stage2_(11)causal_structure_high_density_train_v33.source.jsonl`

## 1. 작성·포장 경계

150개의 primary concept, `text`, `relations`를 record별로 직접 작성했다. 자동 semantic-composition, 명사 치환 template, relation round-robin은 사용하지 않았다. 자동화는 JSONL parse, source 계약 검사, ID·고정 metadata 부여, tokenizer·중복·문법·유사도 감사에만 사용했다.

원고는 낮은 성취·느린 진도·오답·이탈 위험이 피드백·상담·보충배정을 촉발하는 역배정과, 알림·해설·접근성 기능이 이후 행동을 바꾸는 순방향을 분리한다. 동기·진도, 질문·응답, 추천·클릭, 오류·난도조정의 양·음 피드백 고리를 시간축으로 펼치고, 교차지연·무작위 개입·순차 배포·임계치·음수시차로 방향을 판별하는 사례도 포함했다.

첫 source gate에서 73번째 record의 primary literal 누락 1건을 차단했다. 해당 본문을 직접 고친 뒤 150행은 평균 39.073333(+EOS)으로 구조·token gate를 통과했다. 포장 전 source-only 단일·전체 감사에서 exact/normalized 중복과 5-word 반복 0을 확인했고 package 뒤 추가 수정은 없었다.

## 2. 구조·직렬화

| 검사 | 결과 |
|---|---:|
| source rows / corpus records | 150 / 150 |
| primary unique / text unique | 150 / 150 |
| ID first / last | `S2-CSH-04801` / `S2-CSH-04950` |
| source↔corpus projection 오류 | 0 |
| JSON/JSONL parse 오류 | 0 |
| primary 본문 literal 누락 | 0 |
| 통제어휘 밖 relation | 0 |
| record 내부 relation 중복 | 0 |
| relation cardinality | 4개: 150 records |
| 고유 relation-set / 단일 최대 빈도 | 43 / 9 records |
| `other_type` 불일치 | 0 |

## 3. Relations 분포

총 relation 배정은 600회다.

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 28 |
| `classification` | 94 |
| `boundary` | 112 |
| `contrast` | 38 |
| `comparison` | 51 |
| `function` | 57 |
| `role` | 29 |
| `process` | 132 |
| `state` | 50 |
| `attribute` | 9 |
| `other` | 0 |

`process`는 선행·후행, 되먹임과 지연경로를, `classification`은 순방향·역배정·강화·안정화·미확정 판정을 담는다. `boundary`와 `contrast`는 동시상관과 방향근거, 순방향과 역인과의 경계를, `comparison`은 시차·개입·집단 차이를 나타낸다. `function`과 `role`은 플랫폼 반응규칙 및 교사·상담자 역할을, `state`는 동기·불안·피로·위험상태를 뒷받침한다. `other`가 0회이므로 자주 나온 `other_type` 5가지는 해당 없음이다.

## 4. 중복·유사도·보일러플레이트

| 검사 | 결과 |
|---|---:|
| exact primary/text/normalized text 중복 | 0 |
| primary+relation-set 중복 | 0 |
| v33 내부 cross-record 5-word n-gram 반복 | 0 / 2,014 assignments |
| 현행 전체 68파일 cross-record 5-word n-gram 반복 | 0 / 183,387 assignments |
| v33 내부 normalized character similarity ≥ 0.80 | 0 pairs |
| v33 내부 최대 character similarity | 0.448276 |
| v33 내부 word-set Jaccard ≥ 0.60 | 0 pairs |
| v33 내부 최대 word-set Jaccard | 0.208333 |
| 기존 Stage2 train 5,100 records 교차 character similarity ≥ 0.80 | 0 pairs |
| 기존 Stage2 train 교차 최대 character similarity | 0.529915 |
| 기존 Stage2 train 교차 word-set Jaccard ≥ 0.60 | 0 pairs |
| 기존 Stage2 train 교차 최대 word-set Jaccard | 0.200000 |
| generic shape fingerprint | 45종, 단일 최대 22/150 = 14.67% |

최종 lexical 5-gram, 문자 유사도, 단어집합 Jaccard에서 내부·기존 Stage2 train 교차 검토선을 넘은 pair가 없다. 한 문장으로 완결한 피드백 고리 설명이 많아 generic shape 최대 점유는 14.67%지만, lexical boilerplate 반복은 0이고 임계 15% 아래다.

## 5. 한국어·token 감사

- exact tokenizer: `tok-ko-en-32768.json`, SHA-256 `3a69001ecc28a5bdf1e951a1036b234c9bdcb847b310252c6d72cfc6c52c48e3`
- 최종 평균: 39.073333 tokens/record(+EOS)
- 최종 최소/최대: 31 / 49
- Stage2 승인 평균: 41.625, 허용범위 ±10% = 37.4625~45.7875 — file mean PASS
- text 문자 길이: 최소 57, 평균 73.300, 최대 88
- hard grammar finding: 0
- 조사 휴리스틱 warning: 10

10개 warning 위치를 전수 읽었다. `피드백이`, `설명이`, `문항해설이`, `차이가`, `효과와`, `동기와`처럼 정상 단어 내부를 보수적으로 잡은 false positive이며 실제 조사 불일치는 없다.

## 6. 해시와 최종 판정

- source SHA-256: `f6a963aeb3817805318c5f025cef0a6fb17b126c5a60d00a63b12967a5c800f2`
- corpus SHA-256: `5273373412e2db52700fd58d728ac8548f1d641e4416d5b5c07da1d4dbeb7ecd`
- resume checkpoint SHA-256: `e1f4574a1765e2fd4d7ddb42eb38942a0604dfd1b88d55189d088aa6c5682b52`
- central ledger SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`

`--require-complete --check-only` 감사에서 source 1·corpus 1, missing 0, structural PASS, direct-authoring debt 0을 확인했다. 전체 부분 감사도 68 source/corpus pairs·10,200 records에서 구조·exact/normalized 중복·train/validation exact leakage·5-word n-gram 반복·hard grammar·manual-review debt 모두 0으로 PASS했다. Stage2 누적 5,400 records(현행 validation 포함)의 exact tokenizer 평균은 42.884444(+EOS)으로 gate PASS다. 보호 대상 변경은 없다.

다음 예약은 `S2-A01-T-034`, `stage2_(11)causal_structure_high_density_train_v34.json`, ID `S2-CSH-04951 ~ S2-CSH-05100`, family `온라인 학습 진도·피드백 운영 — 개입 전후 결과와 자연 변동 구분`이다.
