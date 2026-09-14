# TinyLM Stage2 A04 v50 자연성 직접 재서술 및 재감사 보고서

## 범위와 변경 경계

- 대상: `stage2_(14)state_transition_high_density_train_v50.source.jsonl` 1개, 150행.
- 수정 전 SHA-256: `890D4032B588A1E91350BB85221910DB5AC8E8E62FA9D03650715856C24B60C6`
- 수정 후 SHA-256: `B8950016F89CBC6CDC2651749B75D485D6891A041895CC5D702BB77D09C02D42`
- 항만의 하역·야드·게이트·통관·접안·안전·냉동 컨테이너·위험물·복구 운영 상태 전이 150행을 한 행씩 읽고, 각 locator의 `primary`와 `text`만 직접 재서술했다. 행 순서와 `relations` 배열은 보존했다.
- A05·다른 Stage2 영역, package train/validation, registry, manifest, 중앙 원장, 공용 감사기, GPU·모델·학습, Git은 수정하지 않았다.

## 재서술과 직접 교정

- 붙여쓴 내부 표제어를 `크레인 하역 작업 대기`, `컨테이너 하역 시작`, `위험물 누출 경보`, `비상 하역 장비 기동`, `안전 재개 조건 확인`처럼 항만 운영자가 이해할 수 있는 명사구로 바꿨다.
- 각 text에는 실제 관찰 대상, 위험 또는 판단 조건, 운전자·운영자·검사자의 조치, 후속 확인이 드러나게 썼다. 작업 순서나 시각 보존만 나열하는 문장은 제거했다.
- 수정 전 `primary+은/는` 시작은 125/150(83.33%)으로 diversity HOLD였다. 전 행을 다른 문형으로 직접 재서술해 최종 0/150(0.00%)으로 낮췄다.
- 1차 재감사에서 primary 중복 6건, word-set Jaccard 임계 초과 2쌍, token 평균 36.83을 발견했다. v50 내부 중복 2쌍은 `야드 슬롯 앞 운반 차량 대기`와 `자율 운반 차량 호출 대기`, `반출 서류와 차량 확인 대기`와 `반출 서류 검사 대기`로 실제 상태를 구분했다. v49와 겹친 4개 primary는 항만 고유 맥락으로 다시 썼고, `혼잡 경보 원인 확인`도 실제 대기열·장비·게이트를 함께 보는 `혼잡 경보 대응 판단`으로 재서술했다.
- token 하한을 넘기기 위해 20개 locator의 상황·판단·조치를 개별 보강했다. 전역 치환, 템플릿 대량 치환, suffix 번호 부여, source 전체 재직렬화는 사용하지 않았다.

## v50 파일 단위 결과

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
| tokens+EOS / 평균 / 최소 / 최대 | 5,704 / 38.03 / 29 / 50 |

### relations 분포

| relation | 횟수 |
|---|---:|
| is_a | 0 |
| subclass_of | 0 |
| part_of | 14 |
| classification | 49 |
| boundary | 45 |
| contrast | 0 |
| comparison | 38 |
| function | 69 |
| role | 36 |
| process | 150 |
| state | 150 |
| attribute | 49 |
| other | 0 |

`other`가 없으므로 v50의 상위 `other_type`은 없다.

## 독립·전체 재감사

- 독립 구조 감사(A04 69파일, 10,350 records): `PASS`; BOM·공백행·JSON·schema·150행 규칙·primary literal·통제어휘·relations cardinality·내부중복·제어문자·exact/normalized duplicate·기존 Stage2 source 겹침·validation unseen relation set 충돌은 모두 0건이다.
- 독립 TF-IDF cosine: 최대 `0.658366307`, 임계치 `0.72` 이상 0쌍.
- 독립 word-set Jaccard: 최대 `0.576923077`, 임계치 `0.60` 이상 0쌍.
- 독립 조사 감사: hard pattern·인접 중복어·primary 조사 후보·번호가 붙은 primary는 모두 0건이다.
- A04 전체 자연성 warning은 0행 / 0건이다.
- source 감사의 5어절 반복 표시는 A04 전체에서 438유형·956 할당으로 남는다. 이는 n-gram 빈도 신호이며, 독립 TF-IDF/Jaccard 임계치 초과와 별개의 advisory 수치다. v50 최종 유사도 gate는 통과했다.

### 토큰 평균 해석

- v50 평균은 `38.03`으로 공용 source 감사기의 파일 평균 하한 `37.4625`를 통과했다.
- A04 전역 token 평균은 `42.72`이다. 공용 감사기는 기존 v32 평균 `46.58`을 고정 상한 `45.7875` 밖으로 세어 `files_passing=68/69`로 표시한다. v32와 공용 감사기 범위 정의는 이번 v50 허용 범위 밖이므로 수정하지 않았다.

### 전체 문형 다양성 상태

- A04 전체 `primary+은/는` 시작: 2,168 / 10,350 = `20.95%`, 전체 비율은 `WITHIN_PROVISIONAL_RANGE`다.
- 파일별 `HOLD_REWRITE_DIVERSITY`는 15파일(v51–v57, v59–v64, v68–v69)에 남아 있다. v31은 67/150(45.00%)의 `REVIEW_DIVERSITY`다. ChatGPT 검토 대기 18건 중 HARD 대상은 15건이며, 사용자 검토 대기는 0건이다.
- 이 문형 gate는 구조 `PASS`와 별개다. 따라서 v50 파일은 통과했지만 A04 전체 자연성 완료 판정은 아직 보류한다.

## 산출물과 다음 지점

- `machine/TinyLM_Stage2_A04_ReviewerAssist_v50_PreDirectReview_2026-09-14.json` — 수정 전 diversity HOLD 증거
- `machine/TinyLM_Stage2_A04_ReviewerAssist_v50_PostDirectReview_2026-09-14.json` — 1차 재서술 및 실패 감지 결과
- `machine/TinyLM_Stage2_A04_ReviewerAssist_v50_FinalDirectReview_2026-09-14.json` — 중복·유사도·token 교정 뒤 최종 파일 단위 결과
- `machine/TinyLM_Stage2_A04_SourceAudit_v50_FinalDirectReview_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_IndependentStructure_Final_v50_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_IndependentSimilarity_Final_v50_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_ReviewerAssist_Global_Post_v50_2026-09-14.json`

다음 직접 작업 대상은 v51이다. 이 보고서는 source 정적 감사 결과(`STATIC_ONLY`)이며 package 승격, registry 동기화, 모델 학습·평가, GPU 실행, Git staging/commit/push는 수행하지 않았다.
