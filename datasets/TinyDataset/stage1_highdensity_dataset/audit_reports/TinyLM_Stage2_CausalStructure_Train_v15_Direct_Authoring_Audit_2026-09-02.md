# TinyLM Stage2 causal_structure train v15 직접 작성 감사

- 감사일: 2026-09-02 KST
- 판정: **PASS**
- reservation: `S2-A01-T-015`
- family: `클라우드 서비스 부하·장애 대응 — 다중 원인의 충분성·기여 범위`
- corpus: `stage2_highdensity_dataset/train/stage2_(11)causal_structure_high_density_train_v15.json`
- source: `stage2_highdensity_dataset/sources/train/stage2_(11)causal_structure_high_density_train_v15.source.jsonl`

## 1. 작성·포장 경계

150개의 primary concept, `text`, `relations`를 record별로 직접 작성했다. 자동 semantic-composition, 명사 치환 template, relation round-robin은 사용하지 않았다. 자동화는 JSONL parse, source 계약 검사, ID·고정 metadata 부여, tokenizer·중복·문법·유사도 감사에만 사용했다.

원고 전반부는 CPU·메모리·큐·데이터베이스·캐시·네트워크·스트림의 복합 포화와 두 원인의 결합 충분성을, 중반부는 분산 합의·복제·보안·배포·관측·SLO 사고의 대체·공동 원인을 다룬다. 후반부는 촉발·배경·증폭·보호·회복 역할, 필요하지만 불충분한 원인, 충분 원인 집합, 겹치는 기여와 반사실 검증을 다룬다.

첫 source check에서 영문·숫자로 끝난 primary 6건의 조사 판정이 실패했다. primary 끝에 `부하`, `비용`, `오류`, `현상`, `반복`을 직접 보충해 자연스러운 `은/는` 연결을 만들었다. 이후 tokenizer 평균 47.553333(+EOS)이 상한을 넘어 포장을 차단했고, 긴 상위 문장 29건을 의미 손실 없이 직접 압축해 최종 45.220000으로 낮춘 뒤 corpus를 생성했다.

## 2. 구조·직렬화

| 검사 | 결과 |
|---|---:|
| source rows / corpus records | 150 / 150 |
| primary unique / text unique | 150 / 150 |
| ID first / last | `S2-CSH-02101` / `S2-CSH-02250` |
| source↔corpus projection 오류 | 0 |
| JSON/JSONL parse 오류 | 0 |
| primary 본문 literal 누락 | 0 |
| 통제어휘 밖 relation | 0 |
| record 내부 relation 중복 | 0 |
| relation cardinality | 4개: 150 records |
| 고유 relation-set / 단일 최대 빈도 | 41 / 14 records |
| `other_type` 불일치 | 0 |

## 3. Relations 분포

총 relation 배정은 600회다.

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 48 |
| `classification` | 90 |
| `boundary` | 150 |
| `contrast` | 15 |
| `comparison` | 85 |
| `function` | 31 |
| `role` | 5 |
| `process` | 72 |
| `state` | 42 |
| `attribute` | 62 |
| `other` | 0 |

`part_of`는 충분 원인 집합과 직렬·병렬 경로의 구성요소를, `classification`은 촉발·배경·증폭·대체 충분 원인의 역할을, `comparison`은 원인 제거·추가·교차 시험으로 구한 기여 차이를 나타낸다. `boundary`는 필요 조건, 단독 충분성, 공동 충분성, 실제 기여량을 혼동하지 않도록 모든 레코드에 부여했다. `other`가 0회이므로 자주 나온 `other_type` 5가지는 해당 없음이다.

## 4. 중복·유사도·보일러플레이트

| 검사 | 결과 |
|---|---:|
| exact primary/text/normalized text 중복 | 0 |
| primary+relation-set 중복 | 0 |
| cross-record 5-word n-gram 반복 | 0 / 3,008 assignments |
| v15 내부 normalized character similarity ≥ 0.80 | 0 pairs |
| v15 내부 최대 character similarity | 0.546392 |
| v15 내부 word-set Jaccard ≥ 0.60 | 0 pairs |
| v15 내부 최대 word-set Jaccard | 0.209302 |
| 기존 Stage2 train 2,400 records 교차 character similarity ≥ 0.80 | 0 pairs |
| 기존 Stage2 train 교차 최대 character similarity | 0.510638 |
| 기존 Stage2 train 교차 word-set Jaccard ≥ 0.60 | 0 pairs |
| 기존 Stage2 train 교차 최대 word-set Jaccard | 0.200000 |
| generic shape fingerprint | 83종, 단일 최대 7/150 = 4.67% |

lexical 5-gram, 문자 유사도, 단어집합 Jaccard 모두 내부·기존 Stage2 train 교차 검토선을 넘은 pair가 없다. generic shape의 단일 최대 비율도 5% 미만이며 의미 문장 복제나 명사 치환 보일러플레이트 증거는 발견되지 않았다.

## 5. 한국어·token 감사

- exact tokenizer: `tok-ko-en-32768.json`, SHA-256 `3a69001ecc28a5bdf1e951a1036b234c9bdcb847b310252c6d72cfc6c52c48e3`
- 최초 평균: 47.553333 tokens/record(+EOS) — 상한 초과로 차단
- 최종 평균: 45.220000 tokens/record(+EOS)
- 최종 최소/최대: 36 / 54
- Stage2 승인 평균: 41.625, 허용범위 ±10% = 37.4625~45.7875 — final file mean PASS
- text 문자 길이: 최소 64, 평균 92.413, 최대 116
- hard grammar finding: 0
- 조사 휴리스틱 warning: 2

2개 warning 행을 직접 읽었다. `차이가`, `효과와`의 정상 단어 내부를 조사 의심 패턴으로 잡은 false positive이며 실제 조사 불일치는 없다.

## 6. 해시와 최종 판정

- source SHA-256: `ac7638dd5c095ed363f5123b522c63392397318d017e5ffffebe7e035d51577f`
- corpus SHA-256: `52e1098c0cd68dad9deebce79b4bd8c2d5a81a713b4623491fc4006ebda98a2e`
- resume checkpoint SHA-256: `3f2c44b7cc1674edb7987be3cbcb5791f54b12debfc368dcddf73135cc3d9222`
- central ledger SHA-256: `21804692434294b0c80774464c87d9e3d90f58ce93748c32671cf535244e5aa7`

`--require-complete --check-only` 감사에서 source 1·corpus 1, missing 0, structural PASS, direct-authoring debt 0을 확인했다. 전체 부분 감사도 50 source/corpus pairs·7,500 records에서 구조·exact/normalized 중복·train/validation exact leakage·5-word n-gram 반복·hard grammar·manual-review debt 모두 0으로 PASS했다. Stage1·저밀도·held-out·기존 Stage2~10 pilot과 v02~v14는 수정하지 않았다.

다음 예약은 `S2-A01-T-016`, `stage2_(11)causal_structure_high_density_train_v16.json`, ID `S2-CSH-02251 ~ S2-CSH-02400`, family `철도 운행 간격·환승 조정 — 직접 원인·매개 경로·배경 조건 분리`다.
