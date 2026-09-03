# TinyLM Stage2 causal_structure train v31 직접 작성 감사

- 감사일: 2026-09-02 KST
- 판정: **PASS**
- reservation: `S2-A01-T-031`
- family: `온라인 학습 진도·피드백 운영 — 직접 원인·매개 경로·배경 조건 분리`
- corpus: `stage2_highdensity_dataset/train/stage2_(11)causal_structure_high_density_train_v31.json`
- source: `stage2_highdensity_dataset/sources/train/stage2_(11)causal_structure_high_density_train_v31.source.jsonl`

## 1. 작성·포장 경계

150개의 primary concept, `text`, `relations`를 record별로 직접 작성했다. 자동 semantic-composition, 명사 치환 template, relation round-robin은 사용하지 않았다. 자동화는 JSONL parse, source 계약 검사, ID·고정 metadata 부여, tokenizer·중복·문법·유사도 감사에만 사용했다.

원고는 온라인 학습에서 피드백·알림·힌트·자막·개인화·접근성 기능의 직접 원인, 접속·오류인식·자기효능감·인지부하·학습행동의 매개경로, 선수지식·기기·통신·근무·돌봄·교사부담·과목난이도의 배경조건을 분리한다. 자기선택·역배정·공통원인과 부정적 매개, 개입·층화·자연실험·시간순서로 경로를 확인하는 사례도 포함했다.

첫 작성분은 147행으로 계수되어 패키징 전에 중단했고, 매개–결과 추가혼입, 배경조건별 직접효과, 경로 전체 반사실 3행을 직접 보충했다. 완성 source는 최초 평균 38.340000(+EOS)으로 구조·token gate를 통과했다. package 뒤 파일·전체 감사에서 반복 5-word n-gram은 발견되지 않아 source·corpus 추가 수정은 없었다.

## 2. 구조·직렬화

| 검사 | 결과 |
|---|---:|
| source rows / corpus records | 150 / 150 |
| primary unique / text unique | 150 / 150 |
| ID first / last | `S2-CSH-04501` / `S2-CSH-04650` |
| source↔corpus projection 오류 | 0 |
| JSON/JSONL parse 오류 | 0 |
| primary 본문 literal 누락 | 0 |
| 통제어휘 밖 relation | 0 |
| record 내부 relation 중복 | 0 |
| relation cardinality | 3개: 13 records, 4개: 137 records |
| 고유 relation-set / 단일 최대 빈도 | 54 / 12 records |
| `other_type` 불일치 | 0 |

## 3. Relations 분포

총 relation 배정은 587회다.

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 29 |
| `classification` | 90 |
| `boundary` | 150 |
| `contrast` | 37 |
| `comparison` | 44 |
| `function` | 61 |
| `role` | 24 |
| `process` | 74 |
| `state` | 52 |
| `attribute` | 26 |
| `other` | 0 |

`classification`은 직접·매개·배경, 자기선택·역배정·공통원인의 판정 지위를, `process`와 `part_of`는 기능 노출부터 행동·인지·성취로 이어지는 경로를 나타낸다. `function`과 `role`은 플랫폼 기능과 교사·동료 개입의 작동을, `state`는 동기·불안·자기효능감·환경조건을 담는다. `boundary`는 모든 record에서 노출과 매개, 원인효과와 배경혼입의 경계를 명시한다. `other`가 0회이므로 자주 나온 `other_type` 5가지는 해당 없음이다.

## 4. 중복·유사도·보일러플레이트

| 검사 | 결과 |
|---|---:|
| exact primary/text/normalized text 중복 | 0 |
| primary+relation-set 중복 | 0 |
| v31 내부 cross-record 5-word n-gram 반복 | 0 / 1,882 assignments |
| 현행 전체 66파일 cross-record 5-word n-gram 반복 | 0 / 179,040 assignments |
| v31 내부 normalized character similarity ≥ 0.80 | 0 pairs |
| v31 내부 최대 character similarity | 0.482143 |
| v31 내부 word-set Jaccard ≥ 0.60 | 0 pairs |
| v31 내부 최대 word-set Jaccard | 0.225806 |
| 기존 Stage2 train 4,800 records 교차 character similarity ≥ 0.80 | 0 pairs |
| 기존 Stage2 train 교차 최대 character similarity | 0.446602 |
| 기존 Stage2 train 교차 word-set Jaccard ≥ 0.60 | 0 pairs |
| 기존 Stage2 train 교차 최대 word-set Jaccard | 0.200000 |
| generic shape fingerprint | 37종, 단일 최대 15/150 = 10.00% |

최종 lexical 5-gram, 문자 유사도, 단어집합 Jaccard에서 내부·기존 Stage2 train 교차 검토선을 넘은 pair가 없다. generic shape 최대 점유는 10.00%이고 lexical boilerplate 증거는 발견되지 않았다.

## 5. 한국어·token 감사

- exact tokenizer: `tok-ko-en-32768.json`, SHA-256 `3a69001ecc28a5bdf1e951a1036b234c9bdcb847b310252c6d72cfc6c52c48e3`
- 최종 평균: 38.340000 tokens/record(+EOS)
- 최종 최소/최대: 29 / 47
- Stage2 승인 평균: 41.625, 허용범위 ±10% = 37.4625~45.7875 — file mean PASS
- text 문자 길이: 최소 60, 평균 72.887, 최대 87
- hard grammar finding: 0
- 조사 휴리스틱 warning: 24

24개 warning 위치를 전수 읽었다. `효과와`, `기능과`, `시간대차이가`, `과목난이도가`, `알림이`, `피드백이`처럼 정상 단어 내부를 보수적으로 잡은 false positive이며 실제 조사 불일치는 없다.

## 6. 해시와 최종 판정

- source SHA-256: `d42955065815f5c12ae9517e7d4007da96a7a1e73bb366afc2c3c2a8ac84df09`
- corpus SHA-256: `2157d1de7ded2150ed0ab4f0a713a56f8e58caf6a9650ef3ec003e0bbe17b54f`
- resume checkpoint SHA-256: `9334e31ac556173cef97c28067ba3769dca996a8ea1731f0f242b3c3f6c60b76`
- central ledger SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`

`--require-complete --check-only` 감사에서 source 1·corpus 1, missing 0, structural PASS, direct-authoring debt 0을 확인했다. 전체 부분 감사도 66 source/corpus pairs·9,900 records에서 구조·exact/normalized 중복·train/validation exact leakage·5-word n-gram 반복·hard grammar·manual-review debt 모두 0으로 PASS했다. Stage2 누적 5,100 records(현행 validation 포함)의 exact tokenizer 평균은 42.913725(+EOS)으로 gate PASS다. 보호 대상 변경은 없다.

다음 예약은 `S2-A01-T-032`, `stage2_(11)causal_structure_high_density_train_v32.json`, ID `S2-CSH-04651 ~ S2-CSH-04800`, family `온라인 학습 진도·피드백 운영 — 공통 원인과 거짓 상관 통제`다.
