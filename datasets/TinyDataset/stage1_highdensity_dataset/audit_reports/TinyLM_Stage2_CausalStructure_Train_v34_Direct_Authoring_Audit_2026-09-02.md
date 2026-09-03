# TinyLM Stage2 causal_structure train v34 직접 작성 감사

- 감사일: 2026-09-02 KST
- 판정: **PASS**
- reservation: `S2-A01-T-034`
- family: `온라인 학습 진도·피드백 운영 — 개입 전후 결과와 자연 변동 구분`
- corpus: `stage2_highdensity_dataset/train/stage2_(11)causal_structure_high_density_train_v34.json`
- source: `stage2_highdensity_dataset/sources/train/stage2_(11)causal_structure_high_density_train_v34.source.jsonl`

## 1. 작성·포장 경계

150개의 primary concept, `text`, `relations`를 record별로 직접 작성했다. 자동 semantic-composition, 명사 치환 template, relation round-robin은 사용하지 않았다. 자동화는 JSONL parse, source 계약 검사, ID·고정 metadata 부여, tokenizer·중복·문법·유사도 감사에만 사용했다.

원고는 온라인 학습 개편 전부터 존재한 추세, 평균회귀, 요일·학사일정 계절성, 반복검사 숙련, 코호트 구성 교체, 동시 정책·계측 변경을 단순 전후효과와 분리한다. 무작위배정, 단계도입 차이의 차이, 중단시계열, 위약시점·음성대조, 지연·잔류·세척·감쇠, 학생·교사·플랫폼 간섭, 선택적 이탈과 지속성 검사를 서로 다른 판별 사례로 배치했다.

완성한 150행은 최초 source gate에서 평균 41.953333(+EOS), known grammar 0, primary literal 누락 0으로 통과했다. 포장 전 source-only 전체 감사에서도 exact/normalized 중복과 누적 5-word 반복이 0이었고 package 뒤 원고 수정은 없었다.

## 2. 구조·직렬화

| 검사 | 결과 |
|---|---:|
| source rows / corpus records | 150 / 150 |
| primary unique / text unique | 150 / 150 |
| ID first / last | `S2-CSH-04951` / `S2-CSH-05100` |
| source↔corpus projection 오류 | 0 |
| JSON/JSONL parse 오류 | 0 |
| primary 본문 literal 누락 | 0 |
| 통제어휘 밖 relation | 0 |
| record 내부 relation 중복 | 0 |
| relation cardinality | 4개: 150 records |
| 고유 relation-set / 단일 최대 빈도 | 56 / 9 records |
| `other_type` 불일치 | 0 |

## 3. Relations 분포

총 relation 배정은 600회다.

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 27 |
| `classification` | 80 |
| `boundary` | 120 |
| `contrast` | 22 |
| `comparison` | 88 |
| `function` | 60 |
| `role` | 12 |
| `process` | 94 |
| `state` | 37 |
| `attribute` | 60 |
| `other` | 0 |

`process`와 `state`는 자연 추세·평균회귀·계절성·지연·잔류·감쇠의 시간 양상을, `comparison`과 `attribute`는 기준선·집단·기간·측정값 차이를 담는다. `boundary`, `classification`, `contrast`는 자연 변동·동시 변화·계측 변화와 개입 효과의 판정 경계를 표시한다. `function`, `part_of`, `role`은 배정·보정·반증검사의 기능, 군집·연결망의 구성, 교사·상담 인력의 개입 경로를 뒷받침한다. `other`가 0회이므로 자주 나온 `other_type` 5가지는 해당 없음이다.

## 4. 중복·유사도·보일러플레이트

| 검사 | 결과 |
|---|---:|
| exact primary/text/normalized text 중복 | 0 |
| primary+relation-set 중복 | 0 |
| v34 내부 cross-record 5-word n-gram 반복 | 0 / 2,604 assignments |
| 현행 전체 69파일 cross-record 5-word n-gram 반복 | 0 / 185,991 assignments |
| v34 내부 normalized character similarity ≥ 0.80 | 0 pairs |
| v34 내부 최대 character similarity | 0.352941 |
| v34 내부 word-set Jaccard ≥ 0.60 | 0 pairs |
| v34 내부 최대 word-set Jaccard | 0.142857 |
| 기존 Stage2 train 5,250 records 교차 character similarity ≥ 0.80 | 0 pairs |
| 기존 Stage2 train 교차 최대 character similarity | 0.446281 |
| 기존 Stage2 train 교차 word-set Jaccard ≥ 0.60 | 0 pairs |
| 기존 Stage2 train 교차 최대 word-set Jaccard | 0.176471 |
| generic shape fingerprint | 41종, 단일 최대 13/150 = 8.67% |

lexical 5-gram, 문자 유사도, 단어집합 Jaccard에서 내부·기존 Stage2 train 교차 검토선을 넘은 pair가 없다. 두 문장 설명 틀 안에서도 문장 길이와 논증 순서를 달리해 generic shape 단일 점유가 8.67%에 머물렀고, 반복 보일러플레이트는 검출되지 않았다.

## 5. 한국어·token 감사

- exact tokenizer: `tok-ko-en-32768.json`, SHA-256 `3a69001ecc28a5bdf1e951a1036b234c9bdcb847b310252c6d72cfc6c52c48e3`
- 최종 평균: 41.953333 tokens/record(+EOS)
- 최종 최소/최대: 35 / 53
- Stage2 승인 평균: 41.625, 허용범위 ±10% = 37.4625~45.7875 — file mean PASS
- text 문자 길이: 최소 77, 평균 84.480, 최대 93
- hard grammar finding: 0
- 조사 휴리스틱 warning: 19

19개 warning 위치를 전수 읽었다. `효과와`, `차이가`, `학습효과와`, `변화와`, `결과와`, `학생이`, `분석법이`처럼 정상 단어와 조사 경계를 넓게 잡은 보수적 substring false positive이며 실제 조사 불일치는 없다.

## 6. 해시와 최종 판정

- source SHA-256: `33d384b7064e754a5ab0d7c0e9d2a3bf1ef908d01b81989c0bed92aefa8acf79`
- corpus SHA-256: `20cf2f5f11e3de8f810c7c2c068908a7cc46d356913bce4ff19d21c5263dfcec`
- resume checkpoint SHA-256: `22e7d71987a5998022b458a20aee7e0086ff381b6caa6f5e622b1c9d0357ce84`
- central ledger SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`

`--require-complete --check-only` 감사에서 source 1·corpus 1, missing 0, structural PASS, direct-authoring debt 0을 확인했다. 전체 부분 감사도 69 source/corpus pairs·10,350 records에서 구조·exact/normalized 중복·train/validation exact leakage·5-word n-gram 반복·hard grammar·manual-review debt 모두 0으로 PASS했다. Stage2 누적 5,550 records(현행 validation 포함)의 exact tokenizer 평균은 42.859279(+EOS)으로 gate PASS다. 중앙 원장과 9개 manifest의 read-only projection 검증도 PASS했고 보호 대상 변경은 없다.

다음 예약은 `S2-A01-T-035`, `stage2_(11)causal_structure_high_density_train_v35.json`, ID `S2-CSH-05101 ~ S2-CSH-05250`, family `온라인 학습 진도·피드백 운영 — 다중 원인의 충분성·기여 범위`다.
