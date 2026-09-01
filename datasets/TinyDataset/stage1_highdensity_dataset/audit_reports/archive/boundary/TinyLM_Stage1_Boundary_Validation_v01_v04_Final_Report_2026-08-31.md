# Stage1 (4) Boundary Validation v01~v04 최종 생성·감사 보고서

- 작성·감사일: 2026-08-31
- 대상: Stage1 (4) 개념 경계·반례 high-density validation
- 결과: **v01~v04, 600 records 확정**
- 설계 분량: 사용자 지정 약 36K
- 실제 분량: `text` 48,932자, `[0-9A-Za-z가-힣]+` 기준 11,646개 분리 단위
- 실제 tokenizer 측정: 미수행. tokenizer가 지정되지 않았으므로 설계 36K와 정규식 분리 단위를 같은 수치로 취급하지 않는다.

## 1. 범위와 분리 해석

이번 작업은 고밀도 작업지침서와 데이터셋 설계서, Boundary train v01~v31만을 생성 기준으로 삼았다. 저밀도 데이터와 held-out은 문장 source, schema 근거, concept 후보, 중복·유사도 비교 기준에서 제외했다. 사용자가 validation 설명에 함께 적은 “기능·용도·목적”은 앞선 Function 요청에서 복사된 표현으로 해석하고, 명시된 Stage1 (4) Boundary의 개념 경계·반례 능력을 대상으로 작성했다.

Boundary train 4,650개에는 13개 통제 relation 이름이 모두 등장한다. 따라서 `unseen_relation: true`는 통제 어휘 밖 이름을 추가한다는 뜻이 아니라, **train에서 보지 못한 정렬 relation-set 조합**을 사용하는 compositional unseen slice로 구현했다.

```text
전체 validation: 600 records = train 4,650 records의 12.90%
unseen_relation=true: 72 / 600 = 12.00%
unseen_relation=false: 528 / 600 = 88.00%
파일별 true/false: 18 / 132 = 12.00% / 88.00%
true 고유 relation-set: 12개, 전부 Boundary train 미관측
false relation-set: 전부 Boundary train 관측
train 미관측 개별 relation label: 0개
```

## 2. 확정 파일·누적 표

| version | 파일 | ID 범위 | records | true/false | concept family | text 문자/분리 단위 | SHA-256 |
|---|---|---|---:|---:|---|---:|---|
| v01 | `stage1_(4)boundary_high_density_val_v01.json` | S1-BNV-0001~0150 | 150 | 18/132 | 고고학·문화유산·박물관 수집·해석·보존 경계 | 13,120 / 3,122 | `a61585e24263a191c432300c7bab6566198e2190e92c640b04b4cbe36dc92bda` |
| v02 | `stage1_(4)boundary_high_density_val_v02.json` | S1-BNV-0151~0300 | 150 | 18/132 | 항공운항·공항·항공교통·비행안전 경계 | 11,832 / 2,793 | `255611dcc98cc08ee8ff3c7389c1876a80837a3121131370064a3471f59ba486` |
| v03 | `stage1_(4)boundary_high_density_val_v03.json` | S1-BNV-0301~0450 | 150 | 18/132 | 해양항해·선박운항·항만작업·해상안전 경계 | 11,867 / 2,853 | `5fb8a80b9ba996b02ac7890513bebf453dde3219a731f63c4066d0cbc6cc1df0` |
| v04 | `stage1_(4)boundary_high_density_val_v04.json` | S1-BNV-0451~0600 | 150 | 18/132 | 심리·인지·행동·상담·심리측정 경계 | 12,113 / 2,878 | `a7e308c35389e4487e2bbc476d92f5009a611b51d331ff1f5d69ad3717e6430a` |
| 합계 | 4 files | S1-BNV-0001~0600 | 600 | 72/528 | 4개 신규 family | 48,932 / 11,646 | — |

목표 600개를 모두 생성했으므로 잔여 record와 잔여 파일은 각각 0이다. 모든 파일은 `type: boundary_packet`, `split: val`이며 한 record에 primary concept 하나와 boolean `unseen_relation`을 가진다.

## 3. 일반화 slice relation-set

| train 미관측 정렬 relation-set | true records |
|---|---:|
| `attribute,boundary,classification,process` | 7 |
| `attribute,boundary,function,state` | 2 |
| `boundary,classification,contrast,other` | 8 |
| `boundary,classification,other,role` | 10 |
| `boundary,classification,part_of,state` | 7 |
| `boundary,classification,role,state` | 8 |
| `boundary,comparison,other,state` | 7 |
| `boundary,comparison,process,state` | 1 |
| `boundary,contrast,function,state` | 4 |
| `boundary,contrast,process,state` | 6 |
| `boundary,function,process,state` | 8 |
| `boundary,part_of,process,role` | 4 |
| 합계 | 72 |

위 12개 조합은 모두 Boundary train의 51개 정렬 relation-set에 없었다. relation 이름 자체는 13개 통제 어휘 안에 있고 train에도 관측되어 V1~V3와 통제 어휘 규정을 함께 만족한다.

## 4. Relations 전체·버전별 분포

| relation | v01 | v02 | v03 | v04 | 전체 |
|---|---:|---:|---:|---:|---:|
| `is_a` | 0 | 0 | 0 | 0 | 0 |
| `subclass_of` | 0 | 0 | 0 | 0 | 0 |
| `part_of` | 8 | 15 | 13 | 3 | 39 |
| `classification` | 53 | 49 | 47 | 37 | 186 |
| `boundary` | 150 | 150 | 150 | 150 | 600 |
| `contrast` | 15 | 33 | 38 | 87 | 173 |
| `comparison` | 12 | 10 | 14 | 11 | 47 |
| `function` | 21 | 34 | 35 | 31 | 121 |
| `role` | 5 | 21 | 28 | 7 | 61 |
| `process` | 33 | 41 | 29 | 37 | 140 |
| `state` | 94 | 77 | 70 | 67 | 308 |
| `attribute` | 9 | 18 | 19 | 20 | 66 |
| `other` | 68 | 20 | 25 | 18 | 131 |

`boundary`는 600/600에 포함된다. `is_a`와 `subclass_of`는 이번 네 family의 문장 의미에 계층 label을 억지로 붙이지 않아 0이며, R2의 보수적 labeling 원칙에 따른 결과다. 모든 record는 서로 다른 relation 2~5개를 사용하고 record 내부 중복은 0이다.

## 5. `other` 편집 유형 상위 5개

| 순위 | 편집 유형 | 횟수 | 대표 concept |
|---:|---|---:|---|
| 1 | 증거·추론 범위 (`evidence_inference_scope`) | 63 | `작가서명과진위증명`, `동일주형과동일제작자`, `출토지와원산지`, `구입영수증과진위`, `매장연대와유물연대` |
| 2 | 규범·권한 범위 (`normative_authority_scope`) | 41 | `소장기록과소유권`, `반출허가와적법소유`, `출처표시와소유권표시`, `선의취득과적법반출`, `부식제거와역사흔적삭제` |
| 3 | 표현–지시대상 간극 (`representation_referent_gap`) | 11 | `색맞춤과원색복원`, `재건축과원건물정체성`, `시대재현과역사사실`, `삼차원스캔과원형`, `등록번호와유물정체성` |
| 4 | 문맥·관례 의존 (`context_convention_dependence`) | 10 | `분류명과실제용도`, `유물명과통용명`, `전시주제와시대분류`, `번역명과원어개념`, `종교물과미술품` |
| 5 | 필요·충분 논리 (`necessary_sufficient_logic`) | 6 | `양식유사성과동시대성`, `대형건물과권력중심`, `한유적과한문화`, `유사토기와동일집단`, `활주로침범판정` |

이 다섯 값은 source 편집 원장과 감사 보고에만 쓰며 JSON의 relation 이름으로 노출하지 않았다.

## 6. 구조·직렬화·source 감사

| 감사 항목 | 결과 |
|---|---:|
| JSON parse / UTF-8 decode 오류 | 0 |
| `\uXXXX` Hangul escape 파일 | 0 |
| top-level metadata/schema 오류 | 0 |
| record key/type/split 오류 | 0 |
| record_count/range/version/family 오류 | 0 |
| ID 형식·전역 연속·중복 오류 | 0 |
| source 4개 파일 행 수·열 오류 | 0 |
| source↔JSON concept/relation/unseen/text 불일치 | 0 |
| 빈 text/concept 또는 primary concept literal 누락 | 0 |
| 통제 어휘 밖 relation | 0 |
| relation 수 2~5 위반·record 내부 중복 | 0 |
| `boundary` 필수 relation 누락 | 0 |
| unseen 선언·train 실측 불일치 | 0 |
| 제어문자·비정상 문자 후보 | 0 |

문장 길이는 최소 66자, 중앙값 81자, 평균 81.553자, 최대 111자다. 600개 모두 두 문장 구조로 작성했으나 동일한 도입부 4어절과 5어절 보일러플레이트가 남지 않도록 표현과 판정 근거를 개별화했다.

## 7. 중복·보일러플레이트·split 누출

| 감사 항목 | 결과 |
|---|---:|
| validation 내부 exact ID 중복 | 0 |
| validation 내부 primary concept 중복 | 0 |
| validation 내부 exact text 중복 | 0 |
| validation 내부 concept–relation-set 중복 | 0 |
| validation 내부 반복 5어절 | 0 |
| validation 내부 반복 4어절 도입부 | 0 |
| Boundary train exact primary concept 교집합 | 0 |
| Boundary train exact text 교집합 | 0 |
| Boundary train concept–relation-set 교집합 | 0 |
| Boundary train 공통 5어절 | 0 |
| 기존 고밀도 전체 exact concept/text/concept–relation-set 교집합 | 0 / 0 / 0 |
| 기존 고밀도 전체 공통 5어절 | 0 |

기존 고밀도 전체 비교는 `stage1_highdensity_dataset`의 기존 train/validation JSON 21,100 records를 대상으로 했으며, 이번 Boundary validation 자체는 reference에서 제외했다. 다른 밀도와 held-out은 비교 대상에 넣지 않았다.

## 8. 유사도와 직접 검토

문자 3~5-gram TF-IDF cosine을 동일한 기존 고밀도 corpus IDF 공간에서 계산했다.

```text
validation 내부 최대: 0.265277
Boundary train–validation 최대: 0.207517
기존 고밀도 전체–validation 최대: 0.212943
```

내부 상위 pair를 문장 단위로 직접 확인했다.

| cosine | pair | 검토 결과 |
|---:|---|---|
| 0.265277 | `습관과성향` / `습관형성과목표행동` | 안정된 개인차와 단서 기반 자동화·목표 조절을 각각 판정하므로 교육 축이 다름 |
| 0.252016 | `조난과긴급상태` / `조난호출과긴급호출` | 항공 운항 상태와 해상 통신 호출 등급을 분리하는 서로 다른 전문 맥락 |
| 0.233797 | `운항규정위반판단` / `통항규칙위반판정` | 항공 운항 규정과 해상 충돌예방 규칙을 각 관할·예외 기준으로 판정 |
| 0.230941 | `대기속도와지상속도` / `대지속력과대수속력` | 공기 기준과 물 기준이라는 도메인 전이 pair이며 객체와 측정 기준이 다름 |
| 0.222611 | `운항가능기상창` / `기상호전대기창` | 항공기 운항 최저치와 선박 작업 풍속·파고 기준을 각각 다룸 |

최종 Boundary train 교차 최고 pair는 `무쾌감과무관심` 대 `정치적중립과무관심` 0.207517이다. 전자는 쾌감 능력과 관심·동기의 심리 상태를 비교하고 후자는 공적 역할의 중립성과 정치 참여 동기를 비교하므로 객체와 판정 목적이 다르다. 전체 고밀도 최고 pair는 `자기효능감과자존감` 대 Attribute train의 `자기효능감` 0.212943이며, validation은 두 심리 개념의 경계를 판정하고 reference는 한 속성의 정도를 설명하므로 단순 paraphrase가 아니다.

## 9. 조사·문장 품질 검토

- Primary concept 직후 받침별 `은/는`, `이/가`, `을/를`, `과/와`, `으로/로` 오류: 0건
- 문장 전체 기계 조사 후보: 5 records
- 사람 검토 뒤 실제 조사 오류: 0건

기계 후보는 `전문가`에서 어휘의 마지막 `가`를 조사로 오인한 1건과 `붙잡는`, `넘겨받는`, `보고받는`, `평가받는`에서 활용 어미를 조사로 오인한 4건이었다. 모두 문맥상 올바른 형태다. 보일러플레이트성 반복, 비문, 조사 불량의 다수 반복은 확인되지 않았다.

## 10. 1차 감사 이후 수정 이력

1. 내부 반복 5어절 6개와 Boundary train 공통 5어절 2개를 source 문장에서 직접 재작성해 모두 제거했다.
2. 기존 다른 고밀도 train에서 재사용된 primary concept 4개를 `스트레스회복탄력성`, `문항내적일관성`, `심리구성타당도근거`, `심리척도측정오차`로 다시 설계했다.
3. 1차 교차 상위 pair에서 train 교육 객체가 실질적으로 겹친 문항을 다음과 같이 바꿨다.
   - `조류와해류구분` → `조석류와취송류`
   - `무작위배정과무선표집` → `개별무작위화와군집무작위화`
   - `상관해석과인과설명` → `기제설명과통계예측`
   - `맹검과기만` → `조건은폐와불완전고지`
4. `항공기수색단계`/`수색단계분류`, `재현비행시험경계`/`재현조종시험한계` 등 내부 상위 유사 pair의 판정 근거와 문장 구성을 분리했다.
5. 매 수정 뒤 4개 JSON을 전부 다시 패키징하고 구조·분리·유사도 감사를 처음부터 재실행했다.

## 11. 보호 무결성·작업 경계

| 항목 | 결과 |
|---|---:|
| 시작 보호 파일 | 141 |
| 종료 보호 파일 | 141 |
| SHA-256 일치 | 141/141 |
| 변경 보호 파일 | 0 |
| 누락 보호 파일 | 0 |
| 새로 끼어든 보호 pattern 파일 | 0 |
| Identity train/validation 수정 | 없음 |
| 다른 밀도 데이터 수정·참조 | 없음 |
| 작업 전 unrelated 변경 정리·수정 | 없음 |
| `git diff --check` | PASS |

보호 범위에는 Identity·Attribute·Function train/validation, Stage2 Attribute 확정 파일, Boundary train v01~v31이 포함된다. 작업 전 존재하던 외부 `smoketest_logs`·`test_result`의 untracked 로그는 건드리지 않았다.

## 12. 정본 산출물

```text
val/stage1_(4)boundary_high_density_val_v01.json ... v04.json
tools/boundary_validation_sources/v01.tsv ... v04.tsv
tools/build_boundary_validation.py
tools/audit_boundary_validation.py
TinyLM_Stage1_Boundary_Validation_v01_v04_Audit_2026-08-31.json
TinyLM_Stage1_Boundary_Validation_v01_v04_Final_Report_2026-08-31.md
TinyLM_Stage1_Stage7_Dataset_Design_Spec.md §9~§13
```

이 네 validation 파일은 전수 감사 통과 뒤 설계 원장에서 `확정·수정 금지`로 전환했다.
