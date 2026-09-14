# TinyLM Stage2 A04 v40 자연성 직접 재서술 및 재감사 보고서

## 범위와 변경 경계

- 대상: `stage2_(14)state_transition_high_density_train_v40.source.jsonl` 1개 파일, 150 records.
- 1–150행의 `primary`와 `text`를 한 행씩 읽고 직접 재서술했다. 숫자 접미사, 대시형 표식, 절단 어근, 임의 합성어를 쓰지 않았고 `relations` 배열과 행 순서는 바꾸지 않았다.
- 다른 A04 source, 다른 교육영역, package train/val, registry, manifest, 중앙 원장, 공용 감사기, 체크포인트는 수정하지 않았다.
- 수정 전 SHA-256: `01FF44AC9EE3D6D11822FD13D05B84F26B890967DD35431663A0825FF58122BD`.
- 최종 SHA-256: `545C081649262EB699AFBFC4DA179D79072377F259311427BCEAC33FC42D4A56`.

## 직접 수정 내용

- 기상·지형·통신·저장장치·계통·정비 상황을 실제 조건, 담당자의 판단·조치, 결과가 보이는 일상적인 한국어 문장으로 다시 썼다.
- `primary+은/는`으로 일괄 시작하던 v40의 150행을 서로 다른 문장 도입부로 바꾸었다.
- 재독 중 뜻이 어긋난 표현은 locator별로 고쳤다. 예를 들어 원격 감시를 유지한다고 하면서 본문은 현장 전환을 설명하던 항목은 ‘침수로 인한 중계기 감시 중단’으로, 불명확한 복구·기록 표현은 실제 점검·승인·조치가 드러나는 표현으로 바로잡았다.
- 토큰 평균 상한을 넘은 첫 재서술본은 전역 축약하지 않았다. 긴 primary와 중복 정의가 있는 개별 행만 두 문장으로 줄인 뒤 다시 읽어 자연스럽지 않은 조사·연결어를 복원했다.

## v40 파일 단위 결과

| 항목 | 수정 전 | 최종 |
|---|---:|---:|
| records | 150 | 150 |
| `primary+은/는` 도입 | 150 / 150 (100%) | 0 / 150 (0%) |
| reviewer hard source errors | — | 0 |
| 자연성 warning records / assignments | — | 0 / 0 |
| ChatGPT review queue / user queue | — | 0 / 0 |
| tokens plus EOS | — | 6,819 |
| file token mean | — | 45.46 |
| record token min–max | — | 29–66 |

v40의 평균 45.46은 정본 범위 `37.4625–45.7875` 안이다. 중간 r2 감사에서 primary literal 누락 1건과 v39와의 exact primary 중복 1건을 각각 발견했으며, locator 48과 31을 직접 고친 뒤 r3 최종 감사에서 모두 0건으로 해소했다.

## relations 분포

| relation | count |
|---|---:|
| is_a | 0 |
| subclass_of | 0 |
| part_of | 22 |
| classification | 40 |
| boundary | 54 |
| contrast | 20 |
| comparison | 20 |
| function | 53 |
| role | 16 |
| process | 150 |
| state | 150 |
| attribute | 75 |
| other | 0 |

`other` 레코드는 없으므로 상위 `other_type` 5개도 없다.

## A04 전체 독립 재감사

- 구조·정합성: 69 files / 10,350 records, 오류 0, `PASS`.
- TF-IDF cosine: 최대 `0.661816021`, 임계값 `0.72` 이상 pair 0.
- word-set Jaccard: 최대 `0.576923077`, 임계값 `0.60` 이상 pair 0.
- 조사 감사: hard pattern 0, 인접 중복어 0, primary 조사 후보 0.
- 자연성 warning: 0 records / 0 assignments.
- 정본 token gate: A04 전체는 68 / 69 files가 범위 안이다. 범위를 벗어난 것은 기존 v32 평균 `46.58`이며, v40은 통과했다.

## 남은 A04 범위

이번 v40 완료 뒤 전체 `primary+은/는` 비율은 `3,423 / 10,350 = 33.0725%`로 `REVIEW_DIVERSITY`다. v41–v57, v59–v64, v68–v69의 25개 파일은 파일별 45% 초과 `HOLD_REWRITE_DIVERSITY`로 남아 있다. v31은 44.67%의 `REVIEW_DIVERSITY`다.

따라서 이번 결과는 **v40 파일 단위 구조·토큰·자연성 advisory PASS**이지 A04 전체 완료 선언이 아니다. 다음 직접 재서술 대상은 v41이다. 검증 증거 수준은 `STATIC_ONLY`이며 package 승격, 모델 학습, 모델 품질 평가는 수행하지 않았다.

## 최종 감사 산출물

- `audit_reports/machine/TinyLM_Stage2_A04_ReviewerAssist_v40_Final_r3_2026-09-14.json`
- `audit_reports/machine/TinyLM_Stage2_A04_SourceAudit_AfterV40Final_r3_2026-09-14.json`
- `audit_reports/machine/TinyLM_Stage2_A04_Independent_Structure_AfterV40Final_r3_2026-09-14.json`
- `audit_reports/machine/TinyLM_Stage2_A04_Independent_Similarity_AfterV40Final_r3_2026-09-14.json`
- `audit_reports/machine/TinyLM_Stage2_A04_ReviewerAssist_AfterV40Final_r3_2026-09-14.json`
