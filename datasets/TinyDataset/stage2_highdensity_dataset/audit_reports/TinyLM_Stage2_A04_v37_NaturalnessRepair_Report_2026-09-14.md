# TinyLM Stage2 A04 v37 자연성 직접 재서술·재감사 보고서

- 대상: `stage2_(14)state_transition_high_density_train_v37.source.jsonl` 150행
- 범위: A04 source의 `primary`·`text`만 locator별 직접 수정. 행 순서·행 수·`relations` 값과 순서는 보존했다.
- 제외: 다른 A04 version, 다른 교육영역, package train/val, manifest, registry, 공용 감사기, 중앙 원장, GPU·모델·Git.
- 증거 수준: `STATIC_ONLY` — source 구조·문장 감사 결과이며, package·학습·모델 품질 판정은 수행하지 않았다.

## 수정 전 판정

| 항목 | 값 |
| --- | --- |
| 수정 전 source SHA-256 | `02945B471BFCA7CB57A221FE8097F0149D79077DE275246B7219D4873CC60403` |
| 행 수 | 150 |
| `primary+은/는` 시작 | 150/150 (100.00%), `HOLD_REWRITE_DIVERSITY` |
| reviewer hard 구조 오류 | 0 |
| 자연성 warning | 0 (문형 집중은 별도 diversity HOLD) |
| 사전 reviewer JSON SHA-256 | `6B506E0E9FBBC8CBE67236497950DD31AAA9CEFE59E0C1A3B5C6576C23CAB8A6` |

원문은 `취수펌프기동 지연연쇄`, `조석취수창 의존전이`처럼 명사·동사 조각을 붙인 primary와 같은 `primary은/는 …` 도입 문형을 150행 모두 반복했다. 구조 오류가 없더라도 일상 한국어 개념어와 설명문으로는 부적합하다고 판단했다.

## 직접 재서술 방식

- 1–150행을 25행씩 다시 읽고, 행별 원래 의미와 relations를 대조했다.
- `지연연쇄`, `의존전이`, `준비의존` 같은 작성 표식을 실제 작업·상태 명사구로 바꿨다. 예: `취수 펌프 가동 지연`, `격리 수조 준비 대기`, `정전 뒤 비상 전원 전환 지연`, `출하 로트 마감 지연`.
- text는 조건 → 판단/조치 → 결과가 드러나는 두 문장으로 직접 썼고, primary literal은 문장 안에 보존했다.
- 숫자 접미사, 대시형 제목, 전역 치환, 템플릿 대량 치환, 전체 재직렬화는 사용하지 않았다.

## 수정 후 파일 단위 감사

| 항목 | 결과 |
| --- | --- |
| 수정 후 source SHA-256 | `7EC4D2AD69871F19717A9C055111F1222A53BD9B9D360FAEE00C0D3D304C4763` |
| JSONL·UTF-8·150행·공백행·제어문자 | PASS |
| primary/text 비어 있음·primary literal 누락 | 0 / 0 |
| exact primary/text 중복 | 0 / 0 |
| 통제 relations·행당 2–5개·행내 중복 | PASS / 150행 모두 4개 / 0 |
| `primary+은/는` 시작 | 0/150 (0.00%), `WITHIN_PROVISIONAL_RANGE` |
| hard 구조 오류·자연성 warning·검토 queue | 0 / 0 / 0 |
| tokenizer tokens(+EOS) | 6,792, 평균 45.280, 최소 35, 최대 53 |
| post reviewer JSON SHA-256 | `3D3C1A95C75DB64CC5CB5C4745ECDC7E1E1C7DDE95AFE7E0B6A04DCBD5A7ECA7` |

### relations 분포

| relation | 횟수 |
| --- | ---: |
| is_a | 0 |
| subclass_of | 0 |
| part_of | 53 |
| classification | 31 |
| boundary | 37 |
| contrast | 0 |
| comparison | 32 |
| function | 68 |
| role | 46 |
| process | 150 |
| state | 150 |
| attribute | 33 |
| other | 0 |

`other`는 없으므로 상위 유형도 없다.

## A04 전체 재감사 영향

- 독립 구조 감사: 69 files, 10,350 records, 오류 전 항목 0, `PASS`. source set SHA-256은 `D6560FFAB9D9C11F95DE86D026497DBD36AFEE7C0ABD3EA869BCCCB2BFF753D0`이다.
- 독립 similarity/조사 감사: char 3–5 TF-IDF 임계치 이상 0, 최고 0.661969 (기준 0.72); word-set Jaccard 임계치 이상 0, 최고 0.576923 (기준 0.60); hard 조사 후보 0, primary 조사 후보 0이다.
- A04 source 감사: 447,839 tokens(+EOS), 평균 43.2695; v37은 평균 45.280으로 파일 token gate 안이다. canonical source audit JSON SHA-256은 `67D4584E66BDC6F3ED380B9FAC0B370E54F98104092EA9C083014C99F1245BC8`이다.
- A04 reviewer 전체: `primary+은/는` 3,873/10,350 = 37.4203%로 영역 수준 `REVIEW_DIVERSITY`이다. v38–v69 중 28개 파일이 아직 개별 `HOLD_REWRITE_DIVERSITY`이며, reviewer 전체 JSON SHA-256은 `CBB7A4E3037EC25ED00BF9007520261457972B2D62735ED81367A6F155C71815`이다.

## 판정

- **v37 구조·유사도·조사·자연성 diversity: PASS.**
- **A04 전체 자연성: HOLD 지속.** v37 통과는 나머지 28개 HOLD 파일의 자연성 통과를 뜻하지 않는다. 다음 대상은 v38이며, 같은 locator별 직접 독해·재서술과 파일 단위 재감사를 적용한다.
