# TinyLM Stage2 A04 v39 자연성 직접 재서술·재감사 보고서

- 대상: `stage2_(14)state_transition_high_density_train_v39.source.jsonl` 150행
- 범위: A04 source의 `primary`·`text`만 locator별 직접 수정. 행 순서·행 수·`relations` 값과 순서는 보존했다.
- 제외: 다른 A04 version, 다른 교육영역, package train/val, manifest, registry, 공용 감사기, 중앙 원장, GPU·모델·Git.
- 증거 수준: `STATIC_ONLY` — source 구조·문장 감사 결과이며 package·학습·모델 품질 판정은 포함하지 않는다.

## 수정 전 판정

| 항목 | 값 |
| --- | --- |
| 수정 전 source SHA-256 | `594C7120F1872309D63DB5F03410FA01C7C0F23A29610BA1D197AA7ED78FA59F` |
| 행 수 | 150 |
| `primary+은/는` 시작 | 150/150 (100.00%), `HOLD_REWRITE_DIVERSITY` |
| reviewer hard 구조 오류 | 0 |
| 자연성 warning | 0 (문형 집중은 별도 diversity HOLD) |
| 사전 reviewer JSON SHA-256 | `DFD28F726C273028514914B5B6AB2C27DB4471DFB975C66507F7997BA555033D` |

원문은 `태양광 희박운량 출력변동원인`, `태양광 기상자료 결측전이`처럼 조사 없이 명사 조각을 붙인 primary와, `primary은/는`으로 시작하는 같은 설명 문형을 반복했다. 태양광 운전·보호·복구의 교육 의미는 유지하되, 사람이 사용하는 상태·점검·조치 언어로 풀어야 했다.

## 직접 재서술 및 token 보정

- 1–150행을 25행 단위로 직접 읽고, 구름·모듈·인버터·계통보호·저장장치·정비·화재·복구의 조건과 결과를 각각 확인했다.
- primary를 `얇은 구름에 따른 태양광 출력 변동`, `인버터 절연 저하에 따른 출력 차단`, `강풍 때 태양광 추적기 잠금`, `저장 충전과 계통 공급의 우선순위 충돌`, `태양광 설비 정상화 판단`처럼 자연한 명사구로 직접 바꿨다.
- text는 관찰 조건, 판단 또는 조치, 다음 상태가 드러나는 짧은 설명문으로 다시 썼고 primary literal을 문장 안에 보존했다.
- 첫 재서술 뒤 평균 token이 36.6333으로 파일 하한 37.4625에 못 미쳤다. 1–25행을 다시 읽어 계통 제한 확인, 제어 조정, 재가동 전 검사처럼 각 행의 실제 후속 판단·조치를 보강했다. 전역 접미사 추가나 템플릿 대량 치환은 사용하지 않았다.

## 최종 파일 단위 감사

| 항목 | 결과 |
| --- | --- |
| 최종 source SHA-256 | `7BCDDCB2D6F0F321BAC1EEC744AB9C9E4DD7C9E40705618877307F96BFCBA88B` |
| JSONL·UTF-8·150행·공백행·제어문자 | PASS |
| primary/text 비어 있음·primary literal 누락 | 0 / 0 |
| exact primary/text 중복 | 0 / 0 |
| 통제 relations·행당 2–5개·행내 중복 | PASS / 150행 모두 4개 / 0 |
| `primary+은/는` 시작 | 0/150 (0.00%), `WITHIN_PROVISIONAL_RANGE` |
| hard 구조 오류·자연성 warning·검토 queue | 0 / 0 / 0 |
| tokenizer tokens(+EOS) | 5,755, 평균 38.3667, 최소 29, 최대 53 |
| v39 post-token reviewer JSON SHA-256 | `465E85DE66FBAC65D488FB5CB6605FB57F1ADCE55EDE47D6983442D2B10D6296` |
| canonical source audit JSON SHA-256 | `F8A5AE37CD83BD6B4D387A09450188688998902797D337DE9D29BC20AF6980A5` |

### relations 분포

| relation | 횟수 |
| --- | ---: |
| is_a | 0 |
| subclass_of | 0 |
| part_of | 21 |
| classification | 46 |
| boundary | 43 |
| contrast | 19 |
| comparison | 25 |
| function | 49 |
| role | 10 |
| process | 150 |
| state | 150 |
| attribute | 87 |
| other | 0 |

`other`는 없으므로 상위 유형도 없다.

## A04 전체 재감사 영향

- 독립 구조 감사: 69 files, 10,350 records, 오류 전 항목 0, `PASS`. source set SHA-256은 `21DA19CD36420607049C88F5EDBC5E0BCB0CC4EE6755000CFE65478E1D8B834D`이다.
- 독립 similarity/조사 감사: char 3–5 TF-IDF 임계치 이상 0, 최고 0.661889495 (기준 0.72); word-set Jaccard 임계치 이상 0, 최고 0.576923077 (기준 0.60); hard 조사 후보 0, primary 조사 후보 0이다.
- A04 source 감사: v39 token은 평균 38.3667로 파일 범위 37.4625–45.7875 안이다. 다만 아직 v32 1개 파일이 상한을 넘으므로 전체 token gate는 68/69다. 이는 v39가 만든 오류가 아니라 기존 v32 항목이다.
- A04 reviewer 전체: `primary+은/는` 3,573/10,350 = 34.5217%로 영역 수준 `REVIEW_DIVERSITY`이다. v40–v69 중 26개 파일이 아직 개별 `HOLD_REWRITE_DIVERSITY`이며, reviewer 전체 JSON SHA-256은 `5B963B1A35EB2D0763616603DD5F7437E215859E02B8B1F52A089459FA29437F`이다.

## 판정

- **v39 구조·유사도·조사·token·자연성 diversity: PASS.**
- **A04 전체 자연성: HOLD 지속.** v39 통과는 나머지 26개 HOLD 파일의 통과를 뜻하지 않는다. 다음 대상은 v40이며 같은 locator별 직접 독해·재서술과 파일 단위 재감사를 적용한다.
