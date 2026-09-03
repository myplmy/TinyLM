# TinyLM Stage2 causal_structure train v36 직접 작성 감사

- 감사일: 2026-09-02 KST
- 판정: **PASS**
- reservation: `S2-A01-T-036`
- family: `생태 복원지 종·서식지 관찰 — 직접 원인·매개 경로·배경 조건 분리`
- corpus: `stage2_highdensity_dataset/train/stage2_(11)causal_structure_high_density_train_v36.json`
- source: `stage2_highdensity_dataset/sources/train/stage2_(11)causal_structure_high_density_train_v36.source.jsonl`

## 1. 작성·포장 경계

150개의 primary concept, `text`, `relations`를 record별로 직접 작성했다. 자동 semantic-composition, 명사 치환 template, relation round-robin은 사용하지 않았다. 자동화는 JSONL parse, source 계약 검사, ID·고정 metadata 부여, tokenizer·중복·문법·유사도 감사에만 사용했다.

원고는 생태 복원지의 수문·식재·외래종·수분자·토양·교란·연결성·관측·기후·관리·오염·먹이망·질병 현상에서 직접 원인, 중간 매개, 사전 배경조건을 구분한다. 제외구·짝지은 대조구·전후 대조·조작·음성대조·시간순서·용량반응과 인과도를 통해 경로를 판별하고, 상쇄·선택왜곡·효과수정·공간 파급·미측정 잔여까지 포함했다.

완성한 150행은 최초 source gate에서 평균 44.840000(+EOS), known grammar 0, primary literal 누락 0으로 통과했다. 포장 전 source-only 전체 감사에서도 exact/normalized 중복과 누적 5-word 반복이 0이었고 package 뒤 원고 수정은 없었다.

## 2. 구조·직렬화

| 검사 | 결과 |
|---|---:|
| source rows / corpus records | 150 / 150 |
| primary unique / text unique | 150 / 150 |
| ID first / last | `S2-CSH-05251` / `S2-CSH-05400` |
| source↔corpus projection 오류 | 0 |
| JSON/JSONL parse 오류 | 0 |
| primary 본문 literal 누락 | 0 |
| 통제어휘 밖 relation | 0 |
| record 내부 relation 중복 | 0 |
| relation cardinality | 4개: 150 records |
| 고유 relation-set / 단일 최대 빈도 | 47 / 14 records |
| `other_type` 불일치 | 0 |

## 3. Relations 분포

총 relation 배정은 600회다.

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 59 |
| `classification` | 83 |
| `boundary` | 131 |
| `contrast` | 38 |
| `comparison` | 33 |
| `function` | 56 |
| `role` | 7 |
| `process` | 109 |
| `state` | 33 |
| `attribute` | 51 |
| `other` | 0 |

`process`와 `part_of`는 수문·영양·분산·먹이망·질병의 매개 사슬을, `classification`과 `boundary`는 직접·매개·배경·측정 경로의 구획을 담는다. `attribute`, `state`, `comparison`은 수분·온도·토양·검출 조건과 처리·대조 차이를 표시한다. `function`, `role`, `contrast`는 복원 조치·생태 매개자의 역할과 반대 효과를 의미가 지지할 때만 사용했다. `other`가 0회이므로 자주 나온 `other_type` 5가지는 해당 없음이다.

## 4. 중복·유사도·보일러플레이트

| 검사 | 결과 |
|---|---:|
| exact primary/text/normalized text 중복 | 0 |
| primary+relation-set 중복 | 0 |
| v36 내부 cross-record 5-word n-gram 반복 | 0 / 2,594 assignments |
| 현행 전체 71파일 cross-record 5-word n-gram 반복 | 0 / 191,215 assignments |
| v36 내부 normalized character similarity ≥ 0.80 | 0 pairs |
| v36 내부 최대 character similarity | 0.421053 |
| v36 내부 word-set Jaccard ≥ 0.60 | 0 pairs |
| v36 내부 최대 word-set Jaccard | 0.216216 |
| 기존 Stage2 train 5,550 records 교차 character similarity ≥ 0.80 | 0 pairs |
| 기존 Stage2 train 교차 최대 character similarity | 0.626866 |
| 기존 Stage2 train 교차 word-set Jaccard ≥ 0.60 | 0 pairs |
| 기존 Stage2 train 교차 최대 word-set Jaccard | 0.343750 |
| generic shape fingerprint | 43종, 단일 최대 14/150 = 9.33% |

lexical 5-gram, 문자 유사도, 단어집합 Jaccard에서 내부·기존 Stage2 train 교차 검토선을 넘은 pair가 없다. 교차 최대 pair는 음성대조의 공통 평가 논리를 서로 다른 온라인 학습·생태 객체에 적용한 사례지만 0.80/0.60 기준보다 낮고 객체·관계 경로가 분명히 다르다.

## 5. 한국어·token 감사

- exact tokenizer: `tok-ko-en-32768.json`, SHA-256 `3a69001ecc28a5bdf1e951a1036b234c9bdcb847b310252c6d72cfc6c52c48e3`
- 최종 평균: 44.840000 tokens/record(+EOS)
- 최종 최소/최대: 37 / 54
- Stage2 승인 평균: 41.625, 허용범위 ±10% = 37.4625~45.7875 — file mean PASS
- text 문자 길이: 최소 74, 평균 85.187, 최대 109
- hard grammar finding: 0
- 조사 휴리스틱 warning: 15

15개 warning 위치를 전수 읽었다. `식물이`, `먹이가`, `기름막이`, `곰팡이가`, `인과도를`, `먹이와`처럼 정상 명사·조사 경계를 넓게 잡은 substring false positive이며 실제 조사 불일치는 없다.

## 6. 해시와 최종 판정

- source SHA-256: `d14f52964bd55c3ef51323306196e5800460fb16e077c2207681d6e29728497f`
- corpus SHA-256: `a4488274e3c3549ebb1ecb8ec24569bede167d5f6db09f6c7e85f22f55e5a044`
- resume checkpoint SHA-256: `1be2aaef659cc64df61bfb6368660758f872a1a66d0ddb850eb0e3b7f3c58442`
- central ledger SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`

`--require-complete --check-only` 감사에서 source 1·corpus 1, missing 0, structural PASS, direct-authoring debt 0을 확인했다. 전체 부분 감사도 71 source/corpus pairs·10,650 records에서 구조·exact/normalized 중복·train/validation exact leakage·5-word n-gram 반복·hard grammar·manual-review debt 모두 0으로 PASS했다. Stage2 누적 5,850 records(현행 validation 포함)의 exact tokenizer 평균은 42.938974(+EOS)으로 gate PASS다. 중앙 원장과 9개 manifest의 read-only projection 검증도 PASS했고 보호 대상 변경은 없다.

다음 예약은 `S2-A01-T-037`, `stage2_(11)causal_structure_high_density_train_v37.json`, ID `S2-CSH-05401 ~ S2-CSH-05550`, family `생태 복원지 종·서식지 관찰 — 공통 원인과 거짓 상관 통제`다.
