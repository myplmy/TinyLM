# TinyLM Stage2 A04 v41 자연성 직접 재서술 및 재감사 보고서

## 범위와 변경 경계

- 대상: `stage2_(14)state_transition_high_density_train_v41.source.jsonl` 1개, 150행.
- 수정 전 SHA-256: `038F652D35DB1F5CB371588885DE0608A34C261703ECD6B688367BAF316C0F56`
- 수정 후 SHA-256: `2CECD5B35C1D527C27C6151F1C73BA40A770CF777CD80F9BBBAD745136478122`
- 1행부터 150행까지를 직접 읽고, 각 행의 `primary`와 `text`만 locator 단위로 재서술했다. 행 순서와 `relations`는 보존했다.
- A05·다른 Stage2 영역, package train/validation, registry, manifest, 중앙 원장, 공용 감사기, GPU·모델·학습, Git은 수정하지 않았다.

## 재서술 기준

- 붙여 쓴 임의 합성어와 기록형 “보존·변경 변수” 문장을 자연스러운 명사구와 설명문으로 바꿨다.
- 각 설명문에는 관찰 조건, 판단 또는 조치 주체, 후속 결과가 드러나도록 했다.
- 숫자 접미사, 대시 제목, 절단 어근, 일괄 치환, 템플릿 복사는 사용하지 않았다.
- 전수 재독해 중 명확한 오류만 다시 직접 고쳤다. 예: `활주로를 열지 결정한다`를 `활주로를 열지 말지를 결정한다`로 고쳤고, 녹은 물 배수·배수로 결빙·관제 지연 표현을 문법과 뜻에 맞게 다듬었다.

## v41 파일 단위 결과

| 항목 | 결과 |
|---|---:|
| records | 150 |
| UTF-8 BOM | 없음 (첫 3바이트 `123,34,112`) |
| JSONL parse·빈 primary/text | 0 |
| primary literal 누락 | 0 |
| exact primary 중복 / exact text 중복 | 0 / 0 |
| relations 개수·내부중복·통제어휘 오류 | 0 / 0 / 0 |
| 자연성 warning | 0행 / 0건 |
| 직접 수정 대상 / 사용자 검토 대기 | 0 / 0 |
| `primary+은/는` 시작 | 28 / 150 (18.67%) — 파일 기준 범위 내 |
| tokens+EOS / 평균 / 최소 / 최대 | 6,056 / 40.37 / 32 / 54 |
| 현재 A04 파일 평균 허용범위 | 38.37–46.58 — 통과 |

### relations 분포

| relation | 횟수 |
|---|---:|
| is_a | 0 |
| subclass_of | 0 |
| part_of | 38 |
| classification | 50 |
| boundary | 32 |
| contrast | 6 |
| comparison | 27 |
| function | 47 |
| role | 24 |
| process | 150 |
| state | 150 |
| attribute | 76 |
| other | 0 |

`other`가 없으므로 v41의 상위 `other_type`은 없다.

## 독립·전체 재감사

### 독립 구조 감사

- 범위: A04 source 69파일, 10,350 records.
- 판정: `PASS`.
- BOM·공백행·JSON·schema·150행 규칙·primary literal·통제어휘·relations cardinality·내부중복·제어문자·exact/normalized duplicate·기존 Stage2 source 겹침·validation unseen relation set 충돌은 모두 0건이다.
- 산출물: `machine/TinyLM_Stage2_A04_Independent_Structure_AfterV41Final_r1_2026-09-14.json`.

### 독립 유사도·조사 감사

- 문자 3–5그램 TF-IDF cosine: 최대 `0.661383664`, 임계치 `0.72` 이상 0쌍.
- word-set Jaccard: 최대 `0.576923077`, 임계치 `0.60` 이상 0쌍.
- 두 최대 쌍은 각각 기존 v60 내/사이 행이며 v41 행은 아니다. 임계치를 넘지 않아 이 작업 범위에서는 수정하지 않았다.
- hard 조사 패턴, 인접 중복어, primary 조사 후보는 모두 0건이다.
- 산출물: `machine/TinyLM_Stage2_A04_Independent_Similarity_AfterV41Final_r1_2026-09-14.json`.

### 전체 자연성 reviewer 결과

- A04 전체 `primary+은/는` 시작은 3,301 / 10,350 = `31.8937%`로 `REVIEW_DIVERSITY`다.
- 자연성 어색표현 warning은 0행 / 0건이지만, 문형 다양성은 별도 gate이므로 이를 자연성 완료로 해석하지 않는다.
- ChatGPT 검토 대기 28건 중 HARD 다양성 대상은 24파일이다: v42–v57, v59–v64, v68–v69. 나머지 4건은 전체 비율·v31·유사도 그룹의 AI 검토 항목이다.
- 사용자 검토 대기는 0건이다.
- 산출물: `machine/TinyLM_Stage2_A04_ReviewerAssist_AfterV41Final_r1_2026-09-14.json`.

## 판정과 다음 지점

- v41 파일: 구조와 파일 단위 자연성·다양성 gate `PASS` (`STATIC_ONLY`).
- A04 전체: 구조 `PASS`, 유사도·조사 gate `PASS`; 그러나 24개 파일의 HARD diversity 재서술이 남아 있으므로 A04 전체 자연성 완료 판정은 보류한다.
- 다음 직접 작업 대상은 v42이며, 동일하게 사전 SHA-256과 사전 reviewer 결과를 기록한 뒤 150행을 개별 검토한다.

## 실행하지 않은 범위

이 보고서는 source 정적 감사 결과다. package 승격, registry 동기화, 모델 학습·평가, GPU 실행, Git staging/commit/push는 수행하지 않았다.
