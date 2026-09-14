# TinyLM Stage2 A04 v32 자연성 직접 수정·재감사 보고서

## 범위와 경계

- 대상: `sources/train/stage2_(14)state_transition_high_density_train_v32.source.jsonl` 한 파일(150행)만.
- 수정: 각 행을 직접 읽고 `primary`와 `text`의 명백한 비문·불투명 합성어만 좁게 재서술했다. 관계 배열, 행 순서, 파일명은 유지했다.
- 제외: A04의 다른 source, A05·A06 등 다른 영역, package train/val, manifest, checkpoint, 중앙 원장, 공용 감사기, GPU·학습·Git.

## 직접 검토 결과

`복원 센서`, `복원 토양`, `복원 지하수`처럼 맥락 연결이 빠진 합성어는 행별 의미에 따라 `복원 현장`, `복원지`, `복원용`, `복원 사업`, `복원 대상`으로 고쳤다. 상태·행동의 조건과 결과가 읽히지 않는 문장은 구체적인 관찰·판단·조치가 드러나도록 재서술했다. 숫자 접미사, 대시 qualifier, 절단 어근을 primary에 넣지 않았다.

5어절 반복이 남은 locator는 같은 표현을 전역 치환하지 않고 각 문맥에 맞춰 다시 썼다. 예를 들어 포획 대기는 관찰 기록, 식재 이력은 표찰·사진·작업자 기록, 사업 인계는 실제 권한 시험처럼 서로 다른 근거를 사용했다.

## 수정 전후 해시

| 구분 | SHA-256 |
| --- | --- |
| 이번 자연성 정리 착수 시 source | `45B47B127270E1D338A0A25A4F17E36613C42AFA0504A413A0FBB2CC132BF0DF` |
| 최종 source | `29E1E27B5F56C5AA02B076B4D0CCE8B86D328C0D3CD295DA668C09BCDD27275F` |
| 최종 reviewer-assist 보고서 | `3A806EE16BFF042D6836230A650529558ADCD27BE580B9DF8EF1448719E4487B` |

## 파일 단위 최종 재감사

구조 감사는 150행, UTF-8 BOM 없음, 공백행·JSON·schema·제어문자·빈 primary/text·primary literal 누락·관계 어휘 위반·관계 수 위반·관계 중복·primary/text 중복·숫자 primary·대시 primary 모두 0건이었다.

`primary+은/는` 문장 시작은 0/150(0%)이며, reviewer-assist 경고·대시 primary·직접 수정 queue·ChatGPT 검토 queue·사용자 검토 queue도 모두 0건이다. 독립 5어절 반복은 0종·0회다.

동일 관계 조합 안의 유사도는 임계치 초과 0쌍이었다. 최대값은 raw word-Jaccard 0.325, raw char 3–5 TF-IDF cosine 0.243603053, primary masking word-Jaccard 0.342857143, primary masking char 3–5 TF-IDF cosine 0.267849163이다.

## relations 분포

| relation | 횟수 |
| --- | ---: |
| is_a | 0 |
| subclass_of | 0 |
| part_of | 20 |
| classification | 37 |
| boundary | 150 |
| contrast | 0 |
| comparison | 16 |
| function | 38 |
| role | 15 |
| process | 150 |
| state | 150 |
| attribute | 24 |
| other | 0 |

`other` 행이 없으므로 상위 유형 5개는 해당 없다.

## 판정

- 파일 구조: **PASS**
- v32 자연성·다양성: **PASS**
- A04 영역 전체 자연성: **아직 HOLD** — v33~v69 등의 미수정 HOLD 파일이 남아 있으며, 이 보고서는 v32 하나의 PASS를 영역 전체 완료로 승격하지 않는다.

최종 기계 보고서: `machine/TinyLM_Stage2_A04_ReviewerAssist_v32_FinalAfterPrimaryNormalization_2026-09-14.json`.
