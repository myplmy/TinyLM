# TinyLM Stage2 A04 v52 자연성 직접 재서술 및 재감사 보고서

## 범위와 변경 경계

- 대상: `stage2_(14)state_transition_high_density_train_v52.source.jsonl` 1개, 150행.
- 수정 전 SHA-256: `A7A601A035C346CD5ECAFDE7F980BD503473D0EC0BE9509EFF7592C9266F5D8A`
- 수정 후 SHA-256: `75150388D19C855A2961D3BC4A685424F701585C41BA1101D5142C8509CF32ED`
- 터널 배수·교통 통제·환기·전원·차수문·센서·복구·재난·통행 재개 상태 전이 150행을 한 행씩 읽고, 각 locator의 `primary`와 `text`를 직접 재서술했다. 행 순서와 `relations` 배열은 보존했다.
- A05·다른 Stage2 영역, package train/validation, registry, manifest, 중앙 원장, 공용 감사기, GPU·모델·학습, Git은 수정하지 않았다.

## 재서술과 직접 교정

- `터널 배수대기`, `터널 중간확인`, `터널 통행완전`처럼 붙여 쓴 임의 합성어를 `터널 배수 대기`, `터널 배수 중간 확인`, `터널 전체 차로 통행 복귀`처럼 실제 운영 상황을 가리키는 명사구로 바꿨다.
- 각 text는 물높이·가스·시야·전원·차수문처럼 무엇을 관찰하는지, 어떤 조건에서 운전자·관제자·순찰자가 무엇을 판단하거나 조치하는지, 그 결과 어떤 상태로 바뀌는지가 읽히도록 썼다.
- 수정 전 `primary+은/는` 시작은 103/150(68.67%)으로 diversity HOLD였다. 전 행을 다른 문형으로 직접 재서술해 최종 0/150(0.00%)으로 낮췄다.
- 배수 단계와 통행 복구 단계를 단순한 기록 보존 문구로 설명하지 않았다. 예를 들어 기록이 누락됐을 때에는 현장 자료를 확인하고, 수위가 다시 오를 때에는 통행 복구를 중단하는 실제 판단을 명시했다.
- 전역 치환, 템플릿 대량 치환, suffix 번호 부여, source 전체 재직렬화는 사용하지 않았다.

## v52 파일 단위 결과

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
| tokens+EOS / 평균 / 최소 / 최대 | 6,501 / 43.34 / 32 / 53 |

### relations 분포

| relation | 횟수 |
|---|---:|
| is_a | 0 |
| subclass_of | 0 |
| part_of | 10 |
| classification | 48 |
| boundary | 52 |
| contrast | 0 |
| comparison | 40 |
| function | 61 |
| role | 37 |
| process | 150 |
| state | 150 |
| attribute | 52 |
| other | 0 |

`other`가 없으므로 v52의 상위 `other_type`은 없다.

## 독립·전체 재감사

- 독립 구조 감사(A04 69파일, 10,350 records): `PASS`; BOM·공백행·JSON·schema·150행 규칙·primary literal·통제어휘·relations cardinality·내부중복·제어문자·exact/normalized duplicate·기존 Stage2 source 겹침·validation unseen relation set 충돌은 모두 0건이다.
- 독립 TF-IDF cosine: 최대 `0.658009418`, 임계치 `0.72` 이상 0쌍.
- 독립 word-set Jaccard: 최대 `0.576923077`, 임계치 `0.60` 이상 0쌍.
- 독립 조사 감사: hard pattern·인접 중복어·primary 조사 후보·번호가 붙은 primary는 모두 0건이다.
- A04 전체 자연성 warning은 0행 / 0건이다.
- source 감사의 5어절 반복 표시는 A04 전체에서 455유형·992 할당으로 남는다. 이는 n-gram 빈도 신호이며, 독립 TF-IDF/Jaccard 임계치 초과와 별개의 advisory 수치다.

### 토큰 평균과 전체 문형 다양성 상태

- v52 평균은 `43.34`로 공용 source 감사기의 파일 평균 허용 범위 `37.4625–45.7875` 안이다.
- A04 전역 token 평균은 `42.67`이다. 공용 감사기는 기존 v32 평균 `46.58`을 고정 상한 `45.7875` 밖으로 세어 `files_passing=68/69`로 표시한다. v32와 공용 감사기 범위 정의는 이번 v52 허용 범위 밖이므로 수정하지 않았다.
- A04 전체 `primary+은/는` 시작은 1,925/10,350=`18.60%`로 전체 비율은 `WITHIN_PROVISIONAL_RANGE`다.
- 파일별 `HOLD_REWRITE_DIVERSITY`는 13파일(v53–v57, v59–v64, v68–v69)에 남아 있고, v31은 67/150(44.67%)의 `REVIEW_DIVERSITY`다. ChatGPT 검토 대기 16건 중 HARD 대상은 13건이며, 사용자 검토 대기는 0건이다.
- v58 내부와 v49/v50 사이에는 같은 relations 묶음의 유사도 advisory 2건이 남아 있다. 이들은 v52 외 locator이므로 이번 파일 수정 범위에는 포함하지 않았으며, 해당 파일 작업 차례에 행별 판단으로 처리한다.
- 이 문형·유사도 advisory는 구조 `PASS`와 별개다. 따라서 v52 파일은 통과했지만 A04 전체 자연성 완료 판정은 아직 보류한다.

## 산출물과 다음 지점

- `machine/TinyLM_Stage2_A04_ReviewerAssist_v52_PreDirectReview_2026-09-14.json` — 수정 전 diversity HOLD 증거
- `machine/TinyLM_Stage2_A04_ReviewerAssist_v52_FinalDirectReview_2026-09-14.json` — 최종 파일 단위 결과
- `machine/TinyLM_Stage2_A04_SourceAudit_v52_FinalDirectReview_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_IndependentStructure_Final_v52_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_IndependentSimilarity_Final_v52_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_ReviewerAssist_Global_Post_v52_2026-09-14.json`

다음 직접 작업 대상은 v53이다. 이 보고서는 source 정적 감사 결과(`STATIC_ONLY`)이며 package 승격, registry 동기화, 모델 학습·평가, GPU 실행, Git staging/commit/push는 수행하지 않았다.
