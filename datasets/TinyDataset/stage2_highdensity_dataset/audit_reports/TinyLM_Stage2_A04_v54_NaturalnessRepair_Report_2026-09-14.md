# TinyLM Stage2 A04 v54 자연성 직접 재서술 및 재감사 보고서

## 범위와 변경 경계

- 대상: `stage2_(14)state_transition_high_density_train_v54.source.jsonl` 1개, 150행.
- 수정 전 SHA-256: `DFEF1C7DA8837BEEFB68957F4B537D66CDB5D42D549F540A5871BE0C2523790E`
- 수정 후 SHA-256: `85086CFAFC3BF38210D8F4E1739BC089C1E68F32A0E665722901433CCE36BEBF`
- 클린룸 입실·청정도·웨이퍼 세정·식각·증착·노광·현상·수율·가스·초순수·필터·센서·경보·복구·비상 대응·보류 로트 상태 전이 150행을 한 행씩 직접 읽고 `primary`와 `text`를 재서술했다.
- 행 순서와 `relations` 배열은 보존했다. A05·다른 Stage2 영역, package train/validation, registry, manifest, 중앙 원장, 공용 감사기, GPU·모델·학습, Git은 수정하지 않았다.

## 직접 재서술과 후속 의미 교정

- 붙여 쓴 내부 표제어를 `클린룸 증착 공정 투입`, `클린룸 공기 필터 누설 대응`, `클린룸 수율 판정 보류`, `클린룸 비상 오염 재발 대응`처럼 관찰 대상과 업무 의미가 드러나는 명사구로 바꿨다.
- 각 text에는 관찰 대상(입자 수·차압·온도·수율·웨이퍼 표면 등), 판단 조건, 담당자의 조치, 공정·격리·생산 재개의 결과가 이해되도록 썼다. 기록자·시각·순서만 나열하는 설명은 상태나 조치가 드러나도록 교체했다.
- 수정 전 `primary+은/는` 시작은 144/150(96.00%)으로 `HOLD_REWRITE_DIVERSITY`였다. 전 행을 문형별로 직접 재서술해 최종 0/150(0.00%)으로 낮췄다.
- 전수 재독 뒤 `현장에서 보기 어려운 값`, `일반 생산 인계`, `재발 오염 재확인`처럼 실제 현장 설명으로 읽기에 어색하거나 의미가 흐린 9행(64·65·108·110·131·135·137·139·146)을 추가로 직접 보정했다.
- 전역 치환, 템플릿 대량 치환, suffix 번호 부여, source 전체 재직렬화는 사용하지 않았다.

## v54 파일 단위 결과

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
| tokens+EOS / 평균 / 최소 / 최대 | 6,543 / 43.62 / 32 / 54 |

v54 평균 43.62는 공용 source 감사기의 파일 평균 허용 범위 37.4625–45.7875 안이다.

### relations 분포

| relation | 횟수 |
|---|---:|
| is_a | 0 |
| subclass_of | 0 |
| part_of | 13 |
| classification | 46 |
| boundary | 52 |
| contrast | 0 |
| comparison | 35 |
| function | 64 |
| role | 37 |
| process | 150 |
| state | 150 |
| attribute | 53 |
| other | 0 |

`other`가 없으므로 v54의 `other_type` 상위 유형은 없다.

## 독립·전체 재감사

- 독립 구조 감사(A04 69파일, 10,350 records): `PASS`; BOM·공백행·JSON·schema·150행 규칙·primary literal·통제어휘·relations cardinality·내부중복·제어문자·exact/normalized duplicate·기존 Stage2 source 겹침·validation unseen relation set 충돌은 모두 0건이다.
- 독립 TF-IDF cosine: 최대 `0.655982098`, 임계치 `0.72` 이상 0쌍.
- 독립 word-set Jaccard: 최대 `0.576923077`, 임계치 `0.60` 이상 0쌍.
- 독립 조사 감사: hard pattern·인접 중복어·primary 조사 후보·번호가 붙은 primary는 모두 0건이다.
- A04 전체 source 감사: 69파일 / 10,350행 / 442,141 tokens+EOS / 평균 42.72. 5어절 반복은 504유형·1,092할당으로 남으며 n-gram 빈도 신호일 뿐 독립 TF-IDF/Jaccard 임계치 초과와는 별개다.
- `files_passing=68/69`는 이번 v54가 아니라 기존 v32 평균 46.58이 상한 45.7875 밖인 결과다. v32와 공용 감사기 범위 정의는 이번 v54 수정 범위 밖이므로 바꾸지 않았다.

### 전체 문형 다양성 상태

- A04 전체 `primary+은/는` 시작은 1,668/10,350=`16.12%`로 전체 비율은 `WITHIN_PROVISIONAL_RANGE`다.
- 파일별 `HOLD_REWRITE_DIVERSITY`는 11파일(v55–v57, v59–v64, v68–v69)에 남아 있다. v31은 67/150(44.67%)의 `REVIEW_DIVERSITY`다.
- reviewer-assist의 ChatGPT 검토 대기는 14건이며, 위 11개 HARD diversity 대상, v31 REVIEW, relations 묶음 기반 유사도 advisory 2건으로 구성된다. 사용자 검토 대기는 0건이다.
- 따라서 v54 파일은 구조·자연성·유사도 gate를 통과했지만 A04 전체 자연성 완료 판정은 아직 보류한다.

## 산출물과 다음 지점

- `machine/TinyLM_Stage2_A04_ReviewerAssist_v54_PreDirectReview_2026-09-14.json` — 수정 전 diversity HOLD 증거
- `machine/TinyLM_Stage2_A04_ReviewerAssist_v54_FinalDirectReview_2026-09-14.json` — 최종 파일 단위 결과
- `machine/TinyLM_Stage2_A04_SourceAudit_v54_FinalDirectReview_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_IndependentStructure_Final_v54_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_IndependentSimilarity_Final_v54_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_ReviewerAssist_Global_Post_v54_2026-09-14.json`

다음 직접 작업 대상은 v55이다. 이 보고서는 source 정적 감사 결과(`STATIC_ONLY`)이며 package 승격, registry 동기화, 모델 학습·평가, GPU 실행, Git staging/commit/push는 수행하지 않았다.
