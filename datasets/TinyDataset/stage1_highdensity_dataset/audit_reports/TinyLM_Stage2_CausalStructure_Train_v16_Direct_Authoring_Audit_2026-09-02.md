# TinyLM Stage2 causal_structure train v16 직접 작성 감사

- 감사일: 2026-09-02 KST
- 판정: **PASS**
- reservation: `S2-A01-T-016`
- family: `철도 운행 간격·환승 조정 — 직접 원인·매개 경로·배경 조건 분리`
- corpus: `stage2_highdensity_dataset/train/stage2_(11)causal_structure_high_density_train_v16.json`
- source: `stage2_highdensity_dataset/sources/train/stage2_(11)causal_structure_high_density_train_v16.source.jsonl`

## 1. 작성·포장 경계

150개의 primary concept, `text`, `relations`를 record별로 직접 작성했다. 자동 semantic-composition, 명사 치환 template, relation round-robin은 사용하지 않았다. 자동화는 JSONL parse, source 계약 검사, ID·고정 metadata 부여, tokenizer·중복·문법·유사도 감사에만 사용했다.

원고는 신호·분기기·출입문·승강장·차량·전력·선로 사건이 출발과 환승 지연으로 이어지는 직접·매개 경로를 다룬다. 시간표 여유, 회차 시간, 승객 밀도, 우회선과 예비 편성은 지속 배경이나 완충 조건으로 분리했고, 후반부에는 시간선 정렬, 반사실 비교, 공통 원인 통제, 기여 분해와 재현 가능한 감사 기록을 배치했다.

최초 포장 뒤 파일 내부에서 `실제 출발 지연은 문 닫힘` 5-gram 1종이 두 레코드에 겹쳤다. 한 레코드의 결과 표현을 직접 다시 써 파일 내부 반복을 제거했다. 이어 전체 누적 감사에서 v11의 최종 기록과 v16의 최종 기록 사이에 `사건 시간선, 직접 원인, 매개 경로, 배경 조건` 열거가 겹쳐 파생 5-gram 4종이 발견됐다. v16 문장을 `발생 순서와 촉발 요인, 중간 과정, 지속 조건`으로 직접 재서술한 뒤 source와 corpus 및 체크포인트 해시를 함께 갱신했다.

## 2. 구조·직렬화

| 검사 | 결과 |
|---|---:|
| source rows / corpus records | 150 / 150 |
| primary unique / text unique | 150 / 150 |
| ID first / last | `S2-CSH-02251` / `S2-CSH-02400` |
| source↔corpus projection 오류 | 0 |
| JSON/JSONL parse 오류 | 0 |
| primary 본문 literal 누락 | 0 |
| 통제어휘 밖 relation | 0 |
| record 내부 relation 중복 | 0 |
| relation cardinality | 4개: 150 records |
| 고유 relation-set / 단일 최대 빈도 | 40 / 18 records |
| `other_type` 불일치 | 0 |

## 3. Relations 분포

총 relation 배정은 600회다.

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 43 |
| `classification` | 127 |
| `boundary` | 150 |
| `contrast` | 23 |
| `comparison` | 30 |
| `function` | 43 |
| `role` | 29 |
| `process` | 63 |
| `state` | 61 |
| `attribute` | 31 |
| `other` | 0 |

`classification`은 직접 원인·매개 사건·배경 조건·완충 조건의 인과 역할을, `process`와 `part_of`는 사건 전달 경로와 운행 계통의 구성 관계를 나타낸다. `boundary`는 시간적 선행, 상관, 직접 원인과 배경 취약성을 혼동하지 않도록 모든 레코드에 부여했다. `other`가 0회이므로 자주 나온 `other_type` 5가지는 해당 없음이다.

## 4. 중복·유사도·보일러플레이트

| 검사 | 결과 |
|---|---:|
| exact primary/text/normalized text 중복 | 0 |
| primary+relation-set 중복 | 0 |
| v16 내부 cross-record 5-word n-gram 반복 | 0 / 2,759 assignments |
| 현행 전체 51파일 cross-record 5-word n-gram 반복 | 0 / 141,385 assignments |
| v16 내부 normalized character similarity ≥ 0.80 | 0 pairs |
| v16 내부 최대 character similarity | 0.537815 |
| v16 내부 word-set Jaccard ≥ 0.60 | 0 pairs |
| v16 내부 최대 word-set Jaccard | 0.277778 |
| 기존 Stage2 train 2,550 records 교차 character similarity ≥ 0.80 | 0 pairs |
| 기존 Stage2 train 교차 최대 character similarity | 0.647482 |
| 기존 Stage2 train 교차 word-set Jaccard ≥ 0.60 | 0 pairs |
| 기존 Stage2 train 교차 최대 word-set Jaccard | 0.333333 |
| generic shape fingerprint | 65종, 단일 최대 14/150 = 9.33% |

최초 탐지된 파일 내부 1종과 누적 교차 4종은 모두 직접 재작성으로 제거했다. 최종 lexical 5-gram, 문자 유사도, 단어집합 Jaccard에서 내부·기존 Stage2 train 교차 검토선을 넘은 pair가 없다. generic shape 최대 비율은 문장 길이·구두점 형태만 추상화한 휴리스틱 값이며, 대응 문장을 직접 대조했을 때 의미 문장 복제나 명사 치환 보일러플레이트 증거는 발견되지 않았다.

## 5. 한국어·token 감사

- exact tokenizer: `tok-ko-en-32768.json`, SHA-256 `3a69001ecc28a5bdf1e951a1036b234c9bdcb847b310252c6d72cfc6c52c48e3`
- 평균: 40.033333 tokens/record(+EOS)
- 최소/최대: 34 / 48
- Stage2 승인 평균: 41.625, 허용범위 ±10% = 37.4625~45.7875 — file mean PASS
- text 문자 길이: 최소 75, 평균 83.627, 최대 101
- hard grammar finding: 0
- 조사 휴리스틱 warning: 3

3개 warning 행을 직접 읽었다. 모두 `효과와`의 정상 단어 내부를 조사 의심 패턴으로 잡은 false positive이며 실제 `은/는`, `이/가`, `을/를`, `과/와` 불일치는 없다.

## 6. 해시와 최종 판정

- source SHA-256: `3f3deb0f0f2ef2f474f49e4daec1632465e372d0c11f5c177279def2dbba3076`
- corpus SHA-256: `12b428040b7dea14e858f41df2ca588265a315e87550e74dac78d955f9128598`
- resume checkpoint SHA-256: `ca4e469a89bdd6df48ca6bd320b88977d61409dc5328509a84a4709f7117f9be`
- central ledger SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`

`--require-complete --check-only` 감사에서 source 1·corpus 1, missing 0, structural PASS, direct-authoring debt 0을 확인했다. 전체 부분 감사도 51 source/corpus pairs·7,650 records에서 구조·exact/normalized 중복·train/validation exact leakage·5-word n-gram 반복·hard grammar·manual-review debt 모두 0으로 PASS했다. Stage2 누적 2,850 records의 exact tokenizer 평균은 42.849123(+EOS)으로 gate PASS다. Stage1·저밀도·held-out·기존 Stage2~10 pilot과 v02~v15는 수정하지 않았다.

다음 예약은 `S2-A01-T-017`, `stage2_(11)causal_structure_high_density_train_v17.json`, ID `S2-CSH-02401 ~ S2-CSH-02550`, family `철도 운행 간격·환승 조정 — 공통 원인과 거짓 상관 통제`다.
