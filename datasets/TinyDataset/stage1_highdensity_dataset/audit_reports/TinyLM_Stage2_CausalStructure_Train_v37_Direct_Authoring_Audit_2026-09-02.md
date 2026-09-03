# TinyLM Stage2 causal_structure train v37 직접 작성 감사

- 감사일: 2026-09-02 KST
- 판정: **PASS**
- reservation: `S2-A01-T-037`
- family: `생태 복원지 종·서식지 관찰 — 공통 원인과 거짓 상관 통제`
- corpus: `stage2_highdensity_dataset/train/stage2_(11)causal_structure_high_density_train_v37.json`
- source: `stage2_highdensity_dataset/sources/train/stage2_(11)causal_structure_high_density_train_v37.source.jsonl`

## 1. 작성·포장 경계

150개의 primary concept, `text`, `relations`를 record별로 직접 작성했다. 자동 semantic-composition, 명사 치환 template, relation round-robin은 사용하지 않았다. 자동화는 JSONL parse, source 계약 검사, ID·고정 metadata 부여, tokenizer·중복·문법·유사도 감사에만 사용했다.

원고는 생태 지표의 동행을 강우·기온·토양·면적·연결성·먹이·오염·지리역사 같은 공통 원인과, 관리대상 선정·조건부 표본·조사 노력·검출·계측 변화가 만든 거짓 상관으로 구분한다. 짝짓기·층화·지점 고정효과·무작위배정·자연실험·음성대조·위약시점·인과도·가중·민감도·공간 및 시간 의존 감사도 포함했다.

최초 150행은 구조·token source gate를 통과했으나 포장 전 전체 source-only 감사가 내부 2종과 기존 v07·v34 교차 2종, 총 4개의 5-word n-gram 반복을 검출했다. 동행 설명, 상관 결론, 자기상관을 담은 v37 세 문장을 직접 재서술해 반복을 0으로 만든 뒤 패키징했다. 최종 평균은 45.306667(+EOS)이다.

## 2. 구조·직렬화

| 검사 | 결과 |
|---|---:|
| source rows / corpus records | 150 / 150 |
| primary unique / text unique | 150 / 150 |
| ID first / last | `S2-CSH-05401` / `S2-CSH-05550` |
| source↔corpus projection 오류 | 0 |
| JSON/JSONL parse 오류 | 0 |
| primary 본문 literal 누락 | 0 |
| 통제어휘 밖 relation | 0 |
| record 내부 relation 중복 | 0 |
| relation cardinality | 4개: 150 records |
| 고유 relation-set / 단일 최대 빈도 | 48 / 9 records |
| `other_type` 불일치 | 0 |

## 3. Relations 분포

총 relation 배정은 600회다.

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 46 |
| `classification` | 107 |
| `boundary` | 145 |
| `contrast` | 29 |
| `comparison` | 52 |
| `function` | 45 |
| `role` | 19 |
| `process` | 66 |
| `state` | 23 |
| `attribute` | 68 |
| `other` | 0 |

`classification`과 `boundary`는 공통 원인·선택·검출·측정 교란과 직접 경로의 구획을 중심으로 사용했다. `attribute`, `process`, `part_of`는 기상·공간·먹이·오염·역사 조건과 시간·영양단계 경로를, `comparison`, `contrast`, `function`은 처리·대조·층별 역전·반증과 통제법을 담는다. `role`과 `state`는 조사자·봉사자·관리자의 선택 역할과 사전 환경 상태에 한정했다. `other`가 0회이므로 자주 나온 `other_type` 5가지는 해당 없음이다.

## 4. 중복·유사도·보일러플레이트

| 검사 | 결과 |
|---|---:|
| exact primary/text/normalized text 중복 | 0 |
| primary+relation-set 중복 | 0 |
| v37 내부 cross-record 5-word n-gram 반복 | 0 / 2,756 assignments |
| 현행 전체 72파일 cross-record 5-word n-gram 반복 | 0 / 193,971 assignments |
| v37 내부 normalized character similarity ≥ 0.80 | 0 pairs |
| v37 내부 최대 character similarity | 0.468085 |
| v37 내부 word-set Jaccard ≥ 0.60 | 0 pairs |
| v37 내부 최대 word-set Jaccard | 0.230769 |
| 기존 Stage2 train 5,700 records 교차 character similarity ≥ 0.80 | 0 pairs |
| 기존 Stage2 train 교차 최대 character similarity | 0.586466 |
| 기존 Stage2 train 교차 word-set Jaccard ≥ 0.60 | 0 pairs |
| 기존 Stage2 train 교차 최대 word-set Jaccard | 0.281250 |
| generic shape fingerprint | 54종, 단일 최대 14/150 = 9.33% |

직접 수정 뒤 lexical 5-gram 반복은 내부·누적 모두 0이며 문자·단어집합 fuzzy 검토선을 넘은 pair도 없다. 생태 공통 원인의 대상·측정·선택 경로를 달리해 generic shape의 단일 점유도 10% 아래다.

## 5. 한국어·token 감사

- exact tokenizer: `tok-ko-en-32768.json`, SHA-256 `3a69001ecc28a5bdf1e951a1036b234c9bdcb847b310252c6d72cfc6c52c48e3`
- 최종 평균: 45.306667 tokens/record(+EOS)
- 최종 최소/최대: 37 / 54
- Stage2 승인 평균: 41.625, 허용범위 ±10% = 37.4625~45.7875 — file mean PASS
- text 문자 길이: 최소 78, 평균 90.027, 최대 102
- hard grammar finding: 0
- 조사 휴리스틱 warning: 7

7개 warning 위치를 전수 읽었다. 모두 `염도가`, `식생높이가`, `물고기와`, `웅덩이가`, `사건이`, `짝지은`, `종자원` 주변의 정상 조사·단어 내부를 보수적으로 잡은 false positive이며 실제 조사 불일치는 없다.

## 6. 해시와 최종 판정

- source SHA-256: `be00d8b2c075a68e8877975a65801558ed136120ed83c56f2f208c47f90e7169`
- corpus SHA-256: `83f057da9861d8940112b4fcd02e6838d46f10a70929cf53af6dbf7512d180d2`
- resume checkpoint SHA-256: `36c3ed3e6d384370bc828f2b95eaa2aeba05c6957d6bbcf8aec8343533ac6dc9`
- central ledger SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`

`--require-complete --check-only` 감사에서 source 1·corpus 1, missing 0, structural PASS, direct-authoring debt 0을 확인했다. 전체 부분 감사도 72 source/corpus pairs·10,800 records에서 구조·exact/normalized 중복·train/validation exact leakage·5-word n-gram 반복·hard grammar·manual-review debt 모두 0으로 PASS했다. Stage2 누적 6,000 records(현행 validation 포함)의 exact tokenizer 평균은 42.998167(+EOS)으로 gate PASS다. 중앙 원장과 9개 manifest의 read-only projection 검증도 PASS했고 보호 대상 변경은 없다.

다음 예약은 `S2-A01-T-038`, `stage2_(11)causal_structure_high_density_train_v38.json`, ID `S2-CSH-05551 ~ S2-CSH-05700`, family `생태 복원지 종·서식지 관찰 — 원인 방향·피드백·역인과 판정`이다.
