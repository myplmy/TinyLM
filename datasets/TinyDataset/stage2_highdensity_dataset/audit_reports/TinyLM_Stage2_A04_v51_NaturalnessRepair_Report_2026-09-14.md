# TinyLM Stage2 A04 v51 자연성 직접 재서술 및 재감사 보고서

## 범위와 변경 경계

- 대상: `stage2_(14)state_transition_high_density_train_v51.source.jsonl` 1개, 150행.
- 수정 전 SHA-256: `BFC4135AF7B5A2C3F0E3B9FEC40031E4BEDAEB07CBDF7422BD525CC5EA1CB306`
- 수정 후 SHA-256: `C84F89D5DD95523BB191E54D45521B6E4A76FC7685AB984B393879B18C48B514`
- 축사 환기·사육 환경·질병 의심 관찰·격리·회복·인계 상태 전이 150행을 한 행씩 읽고, 각 locator의 `primary`와 `text`를 직접 재서술했다. 행 순서와 `relations` 배열은 보존했다.
- A05·다른 Stage2 영역, package train/validation, registry, manifest, 중앙 원장, 공용 감사기, GPU·모델·학습, Git은 수정하지 않았다.

## 재서술과 직접 교정

- 숫자·표식·절단 어근 없이 `사육동 환기 점검`, `초기 증상 개체 확인`, `격리 중 개체 경과 관찰`, `재검사 뒤 격리 해제`처럼 실제 사육 관리에서 이해할 수 있는 명사구로 바꿨다.
- 각 text에 관찰 대상, 조건, 관리자의 판단·조치, 뒤따르는 상태를 드러냈다. 기록 시각이나 변경 순서만 나열하는 불투명한 문장은 남기지 않았다.
- 수정 전 `primary+은/는` 시작은 140/150(93.33%)으로 diversity HOLD였다. 전 행을 다른 문형으로 직접 재서술해 최종 0/150(0.00%)으로 낮췄다.
- 1차 재감사에서 `관찰 종료 뒤 사육동 이동`과 `재검사 뒤 격리 해제`, `초기 증상 개체 확인`과 `격리 중 개체 경과 관찰`의 word-set Jaccard 초과 2쌍을 발견했다. 각각 이동 승인·재검사 해제, 초기 확인·경과 관찰의 실제 역할이 드러나도록 네 행을 다시 썼다.
- 전체 reviewer-assist가 v49의 `냉각 제어값 계산`과 v51의 이전 환기 제어 설명이 같은 문장 골격을 쓴 신호를 추가로 발견했다. v51:81만 `축사 환기 온도 조절`로 직접 고쳐, 동물의 호흡 상태·바깥 기온을 보고 팬 세기를 조절하는 독립 상황으로 분리했다.
- 전역 치환, 템플릿 대량 치환, suffix 번호 부여, source 전체 재직렬화는 사용하지 않았다.

## v51 파일 단위 결과

| 항목 | 결과 |
|---|---:|
| records | 150 |
| JSONL parse·BOM·빈 primary/text | 0 / 0 / 0 |
| primary literal 누락 | 0 |
| exact primary 중복 / exact text 중복 | 0 / 0 |
| relations 개수·내부중복·통제어휘 오류 | 0 / 0 / 0 |
| 자연성 warning | 0행 / 0건 |
| 직접 수정 대상 / ChatGPT·사용자 검토 대기 | 0 / 0 / 0 |
| `primary+은/는` 시작 | 0 / 150 (0.00%) — 파일 기준 범위 내 |
| tokens+EOS / 평균 / 최소 / 최대 | 5,656 / 37.71 / 30 / 50 |

### relations 분포

| relation | 횟수 |
|---|---:|
| is_a | 0 |
| subclass_of | 0 |
| part_of | 12 |
| classification | 50 |
| boundary | 41 |
| contrast | 0 |
| comparison | 39 |
| function | 67 |
| role | 36 |
| process | 150 |
| state | 150 |
| attribute | 55 |
| other | 0 |

`other`가 없으므로 v51의 상위 `other_type`은 없다.

## 독립·전체 재감사

- 독립 구조 감사(A04 69파일, 10,350 records): `PASS`; BOM·공백행·JSON·schema·150행 규칙·primary literal·통제어휘·relations cardinality·내부중복·제어문자·exact/normalized duplicate·기존 Stage2 source 겹침·validation unseen relation set 충돌은 모두 0건이다.
- 독립 TF-IDF cosine: 최대 `0.658302223`, 임계치 `0.72` 이상 0쌍.
- 독립 word-set Jaccard: 최대 `0.576923077`, 임계치 `0.60` 이상 0쌍.
- 독립 조사 감사: hard pattern·인접 중복어·primary 조사 후보·번호가 붙은 primary는 모두 0건이다.
- A04 전체 자연성 warning은 0행 / 0건이다.
- source 감사의 5어절 반복 표시는 A04 전체에서 452유형·985 할당으로 남는다. 이는 n-gram 빈도 신호이며, 독립 TF-IDF/Jaccard 임계치 초과와 별개의 advisory 수치다.

### 토큰 평균과 전체 문형 다양성 상태

- v51 평균은 `37.71`로 공용 source 감사기의 파일 평균 하한 `37.4625`를 통과했다.
- A04 전역 token 평균은 `42.66`이다. 공용 감사기는 기존 v32 평균 `46.58`을 고정 상한 `45.7875` 밖으로 세어 `files_passing=68/69`로 표시한다. v32와 공용 감사기 범위 정의는 이번 v51 허용 범위 밖이므로 수정하지 않았다.
- A04 전체 `primary+은/는` 시작은 2,028/10,350=`19.59%`로 전체 비율은 `WITHIN_PROVISIONAL_RANGE`다.
- 파일별 `HOLD_REWRITE_DIVERSITY`는 14파일(v52–v57, v59–v64, v68–v69)에 남아 있고, v31은 67/150(44.67%)의 `REVIEW_DIVERSITY`다. ChatGPT 검토 대기 17건 중 HARD 대상은 14건이며, 사용자 검토 대기는 0건이다.
- v58 내부와 v49/v50 사이에는 같은 relations 묶음의 유사도 advisory 2건이 남아 있다. 이들은 v51 외 locator이므로 이번 파일 수정 범위에는 포함하지 않았으며, 해당 파일 작업 차례에 행별 판단으로 처리한다.
- 이 문형·유사도 advisory는 구조 `PASS`와 별개다. 따라서 v51 파일은 통과했지만 A04 전체 자연성 완료 판정은 아직 보류한다.

## 산출물과 다음 지점

- `machine/TinyLM_Stage2_A04_ReviewerAssist_v51_PreDirectReview_2026-09-14.json` — 수정 전 diversity HOLD 증거
- `machine/TinyLM_Stage2_A04_ReviewerAssist_v51_FinalDirectReview_2026-09-14.json` — 최종 파일 단위 결과
- `machine/TinyLM_Stage2_A04_SourceAudit_v51_FinalDirectReview_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_IndependentStructure_Final_v51_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_IndependentSimilarity_Final_v51_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_ReviewerAssist_Global_Post_v51_2026-09-14.json`

다음 직접 작업 대상은 v52이다. 이 보고서는 source 정적 감사 결과(`STATIC_ONLY`)이며 package 승격, registry 동기화, 모델 학습·평가, GPU 실행, Git staging/commit/push는 수행하지 않았다.
