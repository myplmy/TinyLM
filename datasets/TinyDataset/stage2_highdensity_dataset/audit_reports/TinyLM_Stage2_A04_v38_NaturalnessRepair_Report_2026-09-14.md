# TinyLM Stage2 A04 v38 자연성 직접 재서술·재감사 보고서

- 대상: `stage2_(14)state_transition_high_density_train_v38.source.jsonl` 150행
- 범위: A04 source의 `primary`·`text`만 locator별 직접 수정. 행 순서·행 수·`relations` 값과 순서는 보존했다.
- 제외: 다른 A04 version, 다른 교육영역, package train/val, manifest, registry, 공용 감사기, 중앙 원장, GPU·모델·Git.
- 증거 수준: `STATIC_ONLY` — source 구조·문장 감사 결과이며 package·학습·모델 품질 판정은 포함하지 않는다.

## 수정 전 판정

| 항목 | 값 |
| --- | --- |
| 수정 전 source SHA-256 | `EFC03543EEFD90C57F94B15FA71C79B2E47568622190392917C69CDE5167D87F` |
| 행 수 | 150 |
| `primary+은/는` 시작 | 150/150 (100.00%), `HOLD_REWRITE_DIVERSITY` |
| reviewer hard 구조 오류 | 0 |
| 자연성 warning | 0 (문형 집중은 별도 diversity HOLD) |
| 사전 reviewer JSON SHA-256 | `B1FD5E2A935A8B5EFD5F1617219AA977DC01B7BD987C6A19CDC487573C820B46` |

원문은 `피드백지연`, `피드백전이`, `피드백관계망`처럼 작성 표식을 붙인 primary와 `primary은/는` 도입 문형을 전 행에 반복했다. 피드백·상호작용이라는 교육 의미는 유지하되, 사람이 이해 가능한 상태·판단·조치의 언어로 풀어야 했다.

## 직접 재서술 및 token 교정

- 1–150행을 25행 단위로 직접 읽고, 피드백 관계가 뜻하는 원인 → 반응 → 결과를 확인했다.
- primary를 `취수 펌프 지연 악순환`, `수온 회복과 염도 보정의 충돌`, `병원체 검사 지연과 격리 판단`, `전력 복구 장비 재가동 순서`, `재가동 뒤 정상화 관찰`처럼 자연한 명사구로 바꿨다.
- text는 조건, 판단/조치, 다음 상태가 이해되도록 두 문장으로 직접 썼고 primary literal을 문장 안에 유지했다.
- 첫 재서술 뒤 평균 token이 46.313으로 파일 상한 45.7875를 넘었다. 가장 긴 25 locator를 재독해해 중복 수식어만 줄였고, 관계 의미·relations·행 순서는 바꾸지 않았다.
- 전역 치환, 접미사 번호, 템플릿 대량 치환, 전체 재직렬화는 사용하지 않았다.

## 최종 파일 단위 감사

| 항목 | 결과 |
| --- | --- |
| 최종 source SHA-256 | `E7B6D31AA770706522501F7AF5495AA16C8979F33FDAC0E8536035396D180F4E` |
| JSONL·UTF-8·150행·공백행·제어문자 | PASS |
| primary/text 비어 있음·primary literal 누락 | 0 / 0 |
| exact primary/text 중복 | 0 / 0 |
| 통제 relations·행당 2–5개·행내 중복 | PASS / 150행 모두 4개 / 0 |
| `primary+은/는` 시작 | 0/150 (0.00%), `WITHIN_PROVISIONAL_RANGE` |
| hard 구조 오류·자연성 warning·검토 queue | 0 / 0 / 0 |
| tokenizer tokens(+EOS) | 6,769, 평균 45.1267, 최소 35, 최대 54 |
| v38 post-token reviewer JSON SHA-256 | `9DAB9BE6D7047D4D325E7F67FFAEF1B99F9C3F2F589414A1A0C6FCD2995EBB78` |

### relations 분포

| relation | 횟수 |
| --- | ---: |
| is_a | 0 |
| subclass_of | 0 |
| part_of | 38 |
| classification | 36 |
| boundary | 28 |
| contrast | 6 |
| comparison | 32 |
| function | 68 |
| role | 18 |
| process | 150 |
| state | 150 |
| attribute | 74 |
| other | 0 |

`other`는 없으므로 상위 유형도 없다.

## A04 전체 재감사 영향

- 독립 구조 감사: 69 files, 10,350 records, 오류 전 항목 0, `PASS`. source set SHA-256은 `B6226B17D6A7274936DF1D763DF5C1DF67AE49E2685E7AFBDE99CE2C6A01919B`이다.
- 독립 similarity/조사 감사: char 3–5 TF-IDF 임계치 이상 0, 최고 0.662047 (기준 0.72); word-set Jaccard 임계치 이상 0, 최고 0.576923 (기준 0.60); hard 조사 후보 0, primary 조사 후보 0이다.
- A04 source 감사: v38 token은 평균 45.1267로 gate 안이다. canonical source audit JSON SHA-256은 `31FD7CCB2BA8727E4E1FCC1D23DDB8616AB21BEB9F7807639BA223588E2AAD88`이다.
- A04 reviewer 전체: `primary+은/는` 3,723/10,350 = 35.9710%로 영역 수준 `REVIEW_DIVERSITY`이다. v39–v69 중 27개 파일이 아직 개별 `HOLD_REWRITE_DIVERSITY`이며, reviewer 전체 JSON SHA-256은 `6A819EB60B0BF7736A146A6CB904549968344DC0EC38AA65EF39A5C70F46C751`이다.

## 판정

- **v38 구조·유사도·조사·token·자연성 diversity: PASS.**
- **A04 전체 자연성: HOLD 지속.** v38 통과는 나머지 27개 HOLD 파일의 통과를 뜻하지 않는다. 다음 대상은 v39이며 같은 locator별 직접 독해·재서술과 파일 단위 재감사를 적용한다.
