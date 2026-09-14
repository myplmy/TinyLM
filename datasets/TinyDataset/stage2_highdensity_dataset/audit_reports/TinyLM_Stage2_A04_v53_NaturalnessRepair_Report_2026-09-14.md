# TinyLM Stage2 A04 v53 자연성 직접 재서술 및 재감사 보고서

## 범위와 변경 경계

- 대상: `stage2_(14)state_transition_high_density_train_v53.source.jsonl` 1개, 150행.
- 수정 전 SHA-256: `9B18422936CD59EF0C823D024DB5069D57FA5523937E92EE0A1AB9FCCD327DDE`
- 수정 후 SHA-256: `C4B894DE5C491210EE0541E35E9960F974AD6044D2A86D8AE371BCF67D25982A`
- 공항 활주로 제설·결빙·마찰·시야·항공기 운항·관제·비상 전원·환경·기록·재난 상태 전이 150행을 한 행씩 읽고, 각 locator의 `primary`와 `text`를 직접 재서술했다. 행 순서와 `relations` 배열은 보존했다.
- A05·다른 Stage2 영역, package train/validation, registry, manifest, 중앙 원장, 공용 감사기, GPU·모델·학습, Git은 수정하지 않았다.

## 재서술과 직접 교정

- `공항 마찰저하`, `공항 운항공백`, `공항 중간확인` 같은 붙여 쓴 내부 표제어를 `공항 활주로 마찰 저하`, `공항 운항 기록 공백 대응`, `공항 제설 중간 확인`처럼 실제 관제·제설 업무에서 뜻이 드러나는 명사구로 바꿨다.
- 각 text에는 적설·결빙·마찰·시야 같은 관찰 대상, 관제사·제설 인력의 판단 조건과 조치, 운항·폐쇄·재개 상태의 결과가 드러나도록 썼다.
- 수정 전 `primary+은/는` 시작은 113/150(75.33%)으로 diversity HOLD였다. 전 행을 다른 문형으로 직접 재서술해 최종 0/150(0.00%)으로 낮췄다.
- 첫 재감사에서 `공항 항공기 회항`, `공항 활주로 잔류 적설` primary가 각각 두 번씩 생긴 것을 발견했다. 결빙 경보에 따른 회항과 마찰 저하에 따른 회항, 가장자리 잔류 적설과 일반 잔류 적설로 실제 조건을 분리해 중복을 해소했다.
- 전역 치환, 템플릿 대량 치환, suffix 번호 부여, source 전체 재직렬화는 사용하지 않았다.

## v53 파일 단위 결과

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
| tokens+EOS / 평균 / 최소 / 최대 | 6,509 / 43.39 / 35 / 51 |

### relations 분포

| relation | 횟수 |
|---|---:|
| is_a | 0 |
| subclass_of | 0 |
| part_of | 10 |
| classification | 45 |
| boundary | 53 |
| contrast | 0 |
| comparison | 32 |
| function | 63 |
| role | 44 |
| process | 150 |
| state | 150 |
| attribute | 53 |
| other | 0 |

`other`가 없으므로 v53의 상위 `other_type`은 없다.

## 독립·전체 재감사

- 독립 구조 감사(A04 69파일, 10,350 records): `PASS`; BOM·공백행·JSON·schema·150행 규칙·primary literal·통제어휘·relations cardinality·내부중복·제어문자·exact/normalized duplicate·기존 Stage2 source 겹침·validation unseen relation set 충돌은 모두 0건이다.
- 독립 TF-IDF cosine: 최대 `0.655943137`, 임계치 `0.72` 이상 0쌍.
- 독립 word-set Jaccard: 최대 `0.576923077`, 임계치 `0.60` 이상 0쌍.
- 독립 조사 감사: hard pattern·인접 중복어·primary 조사 후보·번호가 붙은 primary는 모두 0건이다.
- A04 전체 자연성 warning은 0행 / 0건이다.
- source 감사의 5어절 반복 표시는 A04 전체에서 487유형·1,056 할당으로 남는다. 이는 n-gram 빈도 신호이며, 독립 TF-IDF/Jaccard 임계치 초과와 별개의 advisory 수치다.

### 토큰 평균과 전체 문형 다양성 상태

- v53 평균은 `43.39`로 공용 source 감사기의 파일 평균 허용 범위 `37.4625–45.7875` 안이다.
- A04 전역 token 평균은 `42.70`이다. 공용 감사기는 기존 v32 평균 `46.58`을 고정 상한 `45.7875` 밖으로 세어 `files_passing=68/69`로 표시한다. v32와 공용 감사기 범위 정의는 이번 v53 허용 범위 밖이므로 수정하지 않았다.
- A04 전체 `primary+은/는` 시작은 1,812/10,350=`17.51%`로 전체 비율은 `WITHIN_PROVISIONAL_RANGE`다.
- 파일별 `HOLD_REWRITE_DIVERSITY`는 12파일(v54–v57, v59–v64, v68–v69)에 남아 있고, v31은 67/150(44.67%)의 `REVIEW_DIVERSITY`다. ChatGPT 검토 대기 15건 중 HARD 대상은 12건이며, 사용자 검토 대기는 0건이다.
- v58 내부와 v49/v50 사이에는 같은 relations 묶음의 유사도 advisory 2건이 남아 있다. 이들은 v53 외 locator이므로 이번 파일 수정 범위에는 포함하지 않았으며, 해당 파일 작업 차례에 행별 판단으로 처리한다.
- 이 문형·유사도 advisory는 구조 `PASS`와 별개다. 따라서 v53 파일은 통과했지만 A04 전체 자연성 완료 판정은 아직 보류한다.

## 산출물과 다음 지점

- `machine/TinyLM_Stage2_A04_ReviewerAssist_v53_PreDirectReview_2026-09-14.json` — 수정 전 diversity HOLD 증거
- `machine/TinyLM_Stage2_A04_ReviewerAssist_v53_FinalDirectReview_2026-09-14.json` — 최종 파일 단위 결과
- `machine/TinyLM_Stage2_A04_SourceAudit_v53_FinalDirectReview_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_IndependentStructure_Final_v53_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_IndependentSimilarity_Final_v53_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_ReviewerAssist_Global_Post_v53_2026-09-14.json`

다음 직접 작업 대상은 v54이다. 이 보고서는 source 정적 감사 결과(`STATIC_ONLY`)이며 package 승격, registry 동기화, 모델 학습·평가, GPU 실행, Git staging/commit/push는 수행하지 않았다.
