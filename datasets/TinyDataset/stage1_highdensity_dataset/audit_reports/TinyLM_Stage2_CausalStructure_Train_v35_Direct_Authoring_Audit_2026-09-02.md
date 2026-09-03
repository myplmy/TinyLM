# TinyLM Stage2 causal_structure train v35 직접 작성 감사

- 감사일: 2026-09-02 KST
- 판정: **PASS**
- reservation: `S2-A01-T-035`
- family: `온라인 학습 진도·피드백 운영 — 다중 원인의 충분성·기여 범위`
- corpus: `stage2_highdensity_dataset/train/stage2_(11)causal_structure_high_density_train_v35.json`
- source: `stage2_highdensity_dataset/sources/train/stage2_(11)causal_structure_high_density_train_v35.source.jsonl`

## 1. 작성·포장 경계

150개의 primary concept, `text`, `relations`를 record별로 직접 작성했다. 자동 semantic-composition, 명사 치환 template, relation round-robin은 사용하지 않았다. 자동화는 JSONL parse, source 계약 검사, ID·고정 metadata 부여, tokenizer·중복·문법·유사도 감사에만 사용했다.

원고는 온라인 학습 성과의 필요조건과 충분조건, 결합조건과 대체 가능한 복수 경로, 중복·과잉결정, 제거 반사실과 개인 귀속을 구분한다. 상승·방해 상호작용, 직접·간접·순차·병렬 매개, 실패 병목, 모집단 노출빈도와 기여율, 순서별 공로 배분, 하위집단 이질성, 문턱·포화·상쇄와 식별 불확실성까지 다뤘다.

최초 150행은 구조·token source gate를 통과했으나 포장 전 전체 source-only 감사가 v20과 공유한 `경로가 결과를 유지할 수 있다` 5-word n-gram 1종을 검출했다. v35의 달력·푸시 대체경로 문장을 직접 재서술해 누적 반복을 0으로 만든 뒤 패키징했다. 최종 평균은 43.986667(+EOS)이다.

## 2. 구조·직렬화

| 검사 | 결과 |
|---|---:|
| source rows / corpus records | 150 / 150 |
| primary unique / text unique | 150 / 150 |
| ID first / last | `S2-CSH-05101` / `S2-CSH-05250` |
| source↔corpus projection 오류 | 0 |
| JSON/JSONL parse 오류 | 0 |
| primary 본문 literal 누락 | 0 |
| 통제어휘 밖 relation | 0 |
| record 내부 relation 중복 | 0 |
| relation cardinality | 4개: 150 records |
| 고유 relation-set / 단일 최대 빈도 | 63 / 9 records |
| `other_type` 불일치 | 0 |

## 3. Relations 분포

총 relation 배정은 600회다.

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 63 |
| `classification` | 88 |
| `boundary` | 119 |
| `contrast` | 42 |
| `comparison` | 73 |
| `function` | 74 |
| `role` | 15 |
| `process` | 51 |
| `state` | 30 |
| `attribute` | 45 |
| `other` | 0 |

`part_of`와 `function`은 충분조건 묶음의 구성 및 각 원인의 작동 역할을, `classification`과 `boundary`는 필요·충분·촉발·배경·매개·기여 범위의 경계를 담는다. `comparison`, `contrast`, `attribute`는 제거 전후, 집단·노출빈도·공로·효과크기 차이를, `process`와 `state`는 연쇄·누적·문턱·포화와 학습자 상태를 나타낸다. `role`은 교사·튜터·플랫폼의 몫에만 사용했다. `other`가 0회이므로 자주 나온 `other_type` 5가지는 해당 없음이다.

## 4. 중복·유사도·보일러플레이트

| 검사 | 결과 |
|---|---:|
| exact primary/text/normalized text 중복 | 0 |
| primary+relation-set 중복 | 0 |
| v35 내부 cross-record 5-word n-gram 반복 | 0 / 2,630 assignments |
| 현행 전체 70파일 cross-record 5-word n-gram 반복 | 0 / 188,621 assignments |
| v35 내부 normalized character similarity ≥ 0.80 | 0 pairs |
| v35 내부 최대 character similarity | 0.569231 |
| v35 내부 word-set Jaccard ≥ 0.60 | 0 pairs |
| v35 내부 최대 word-set Jaccard | 0.212121 |
| 기존 Stage2 train 5,400 records 교차 character similarity ≥ 0.80 | 0 pairs |
| 기존 Stage2 train 교차 최대 character similarity | 0.458015 |
| 기존 Stage2 train 교차 word-set Jaccard ≥ 0.60 | 0 pairs |
| 기존 Stage2 train 교차 최대 word-set Jaccard | 0.176471 |
| generic shape fingerprint | 61종, 단일 최대 11/150 = 7.33% |

직접 수정 뒤 lexical 5-gram 반복은 내부·누적 모두 0이며 문자·단어집합 fuzzy 검토선을 넘은 pair도 없다. 내부 최대 character pair는 필요확률과 충분확률의 의도적인 쌍대 개념이지만 0.569231로 기준보다 충분히 낮고, 관계와 반사실 대상이 서로 다르다.

## 5. 한국어·token 감사

- exact tokenizer: `tok-ko-en-32768.json`, SHA-256 `3a69001ecc28a5bdf1e951a1036b234c9bdcb847b310252c6d72cfc6c52c48e3`
- 최종 평균: 43.986667 tokens/record(+EOS)
- 최종 최소/최대: 37 / 54
- Stage2 승인 평균: 41.625, 허용범위 ±10% = 37.4625~45.7875 — file mean PASS
- text 문자 길이: 최소 77, 평균 87.507, 최대 106
- hard grammar finding: 0
- 조사 휴리스틱 warning: 4

4개 warning 위치를 전수 읽었다. `성과와`, `차이가`, `설명과`, `효과와`처럼 정상 단어와 조사 경계를 넓게 잡은 substring false positive이며 실제 조사 불일치는 없다.

## 6. 해시와 최종 판정

- source SHA-256: `7f7e39ecadf0bbb0236d7720b6263033001040a6ff89f6584f02711620f8a45d`
- corpus SHA-256: `41165afb83ae6502b537b98ca91fa48d1eecec716a00069364b9449240a5aeb8`
- resume checkpoint SHA-256: `525f1ce1d201d848fa2aacc2625ac97269a7005cd249423fe6fa55df26124266`
- central ledger SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`

`--require-complete --check-only` 감사에서 source 1·corpus 1, missing 0, structural PASS, direct-authoring debt 0을 확인했다. 전체 부분 감사도 70 source/corpus pairs·10,500 records에서 구조·exact/normalized 중복·train/validation exact leakage·5-word n-gram 반복·hard grammar·manual-review debt 모두 0으로 PASS했다. Stage2 누적 5,700 records(현행 validation 포함)의 exact tokenizer 평균은 42.888947(+EOS)으로 gate PASS다. 중앙 원장과 9개 manifest의 read-only projection 검증도 PASS했고 보호 대상 변경은 없다.

다음 예약은 `S2-A01-T-036`, `stage2_(11)causal_structure_high_density_train_v36.json`, ID `S2-CSH-05251 ~ S2-CSH-05400`, family `생태 복원지 종·서식지 관찰 — 직접 원인·매개 경로·배경 조건 분리`다.
