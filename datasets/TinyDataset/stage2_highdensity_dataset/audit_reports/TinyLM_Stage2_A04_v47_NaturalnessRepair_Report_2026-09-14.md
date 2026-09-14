# TinyLM Stage2 A04 v47 자연성 직접 재서술 및 재감사 보고서

## 범위와 변경 경계

- 대상: `stage2_(14)state_transition_high_density_train_v47.source.jsonl` 1개, 150행.
- 수정 전 SHA-256: `8808D78B556B3D672A02D1F240381BD15E249E00A6E36CBC7CBEC0CF725ED4ED`
- 수정 후 SHA-256: `89DE49705E24050C0ED4E94291941C3341EED45DC8CE04C1BC8E0180CAB77CB6`
- 전기버스 차고의 충전·배차·고전압 안전·정비·기상·재난 대응 개념군 150행을 한 행씩 읽고, 각 locator의 `primary`와 `text`만 직접 재서술했다. 행 순서와 `relations` 배열은 보존했다.
- A05·다른 Stage2 영역, package train/validation, registry, manifest, 중앙 원장, 공용 감사기, GPU·모델·학습, Git은 수정하지 않았다.

## 재서술과 후속 교정

- 원문의 `전기버스 X 안정/이탈`과 식별자·시각 보존 문형을 차고 전력 사용량 점검, 출차 전 배터리 잔량 확인, 충전기 부족으로 배차 조정, 고전압 작업 중지, 차고 침수 대비처럼 현장 업무에서 쓰는 명사구로 바꿨다.
- 각 text에는 무엇을 관찰하는지, 어떤 위험 또는 조건이 생기는지, 누가 무엇을 조치하는지가 이해되도록 썼다. 단순한 기록 보존이나 순서 변경만으로 끝나는 설명은 제거했다.
- 수정 전 `primary+은/는` 시작은 150/150으로 diversity HOLD였다. 설명의 뜻을 유지하면서 관찰 사실·작업자·조건으로 시작하는 문장을 개별 재서술해 44/150(29.33%)으로 낮췄다.
- 첫 전체 독립 구조 감사에서 v45 98행과 `비상 전원 부족` primary 정확 중복 1건을 발견했다. v47 138행만 `차고 비상 전력 부족`으로 구체화했고, 해당 text도 같은 개념으로 직접 수정했다.
- 전역 치환·템플릿 복사·suffix 번호 부여·source 전체 재직렬화는 사용하지 않았다.

## v47 파일 단위 결과

| 항목 | 결과 |
|---|---:|
| records | 150 |
| JSONL parse·BOM·빈 primary/text | 0 / 0 / 0 |
| primary literal 누락 | 0 |
| exact primary 중복 / exact text 중복 | 0 / 0 |
| relations 개수·내부중복·통제어휘 오류 | 0 / 0 / 0 |
| 자연성 warning | 0행 / 0건 |
| 직접 수정 대상 / ChatGPT·사용자 검토 대기 | 0 / 0 / 0 |
| `primary+은/는` 시작 | 44 / 150 (29.33%) — 파일 기준 범위 내 |
| tokens+EOS / 평균 / 최소 / 최대 | 6,136 / 40.91 / 34 / 53 |

### relations 분포

| relation | 횟수 |
|---|---:|
| is_a | 0 |
| subclass_of | 0 |
| part_of | 0 |
| classification | 29 |
| boundary | 74 |
| contrast | 0 |
| comparison | 34 |
| function | 73 |
| role | 15 |
| process | 150 |
| state | 150 |
| attribute | 75 |
| other | 0 |

`other`가 없으므로 v47의 상위 `other_type`은 없다.

## 독립·전체 재감사

- 독립 구조 감사(A04 69파일, 10,350 records): `PASS`; BOM·공백행·JSON·schema·150행 규칙·primary literal·통제어휘·relations cardinality·내부중복·제어문자·exact/normalized duplicate·기존 Stage2 source 겹침·validation unseen relation set 충돌은 모두 0건이다.
- 독립 TF-IDF cosine: 최대 `0.658651093`, 임계치 `0.72` 이상 0쌍.
- 독립 word-set Jaccard: 최대 `0.576923077`, 임계치 `0.60` 이상 0쌍.
- 독립 조사 감사: hard pattern·인접 중복어·primary 조사 후보·번호가 붙은 primary는 모두 0건이다.
- A04 전체 자연성 warning은 0행 / 0건이다.

### 토큰 평균 해석

- v47 평균은 `40.91`로 공용 source 감사기의 파일 평균 하한 `37.4625`를 통과했고, 현재 A04 관측 파일 평균 범위 `38.37–46.58` 안에 있다.
- 공용 source 감사기의 고정 `files_passing` 계산은 `37.4625–45.7875`을 쓰므로, 기존 v32 평균 `46.58` 하나를 범위 밖으로 세어 68/69로 표시한다. 이는 v47 수정 실패가 아니라 기존 범위 정의 불일치이며, 공용 감사기·v32는 이번 허용범위 밖이어서 수정하지 않았다.

### 전체 문형 다양성 상태

- A04 전체 `primary+은/는` 시작: 2,537 / 10,350 = `24.51%`, 전체 비율은 `WITHIN_PROVISIONAL_RANGE`다.
- 파일별 `HOLD_REWRITE_DIVERSITY`는 18파일(v48–v57, v59–v64, v68–v69)에 남아 있다. ChatGPT 검토 대기 21건 중 HARD 대상은 18건이며, 사용자 검토 대기는 0건이다.
- 이 문형 gate는 구조 `PASS`와 별개다. 따라서 v47 파일은 통과했지만 A04 전체 자연성 완료 판정은 아직 보류한다.

## 산출물과 다음 지점

- `machine/TinyLM_Stage2_A04_ReviewerAssist_v47_PreDirectReview_2026-09-14.json` — 수정 전 diversity HOLD 증거
- `machine/TinyLM_Stage2_A04_ReviewerAssist_v47_PostDirectReview_r1_2026-09-14.json` — 전면 직접 재서술 뒤 파일 단위 결과
- `machine/TinyLM_Stage2_A04_ReviewerAssist_v47_PostDirectReview_r2_2026-09-14.json` — 문형 비율 교정 뒤 파일 단위 결과
- `machine/TinyLM_Stage2_A04_ReviewerAssist_v47_PostDirectReview_r4_2026-09-14.json` — cross-file primary 중복 해소 뒤 최종 파일 단위 결과
- `machine/TinyLM_Stage2_A04_SourceAudit_AfterV47DirectReview_r1_2026-09-14.json` — 전면 직접 재서술 뒤 token 결과
- `machine/TinyLM_Stage2_A04_SourceAudit_AfterV47DirectReview_r4_2026-09-14.json` — 최종 token gate 결과
- `machine/TinyLM_Stage2_A04_StructureIndependent_AfterV47DirectReview_r1_2026-09-14.json` — cross-file duplicate 발견 증거
- `machine/TinyLM_Stage2_A04_StructureIndependent_AfterV47DirectReview_r2_2026-09-14.json` — 최종 구조 PASS
- `machine/TinyLM_Stage2_A04_SimilarityIndependent_AfterV47DirectReview_r2_2026-09-14.json`
- `machine/TinyLM_Stage2_A04_ReviewerAssist_AfterV47DirectReview_r2_2026-09-14.json`

다음 직접 작업 대상은 v48이다. 이 보고서는 source 정적 감사 결과(`STATIC_ONLY`)이며 package 승격, registry 동기화, 모델 학습·평가, GPU 실행, Git staging/commit/push는 수행하지 않았다.
