# Stage1 (8) 비교·대조 통합 감사 보고서

- 최종 판정: **PASS**
- 통합일: 2026-09-01
- 범위: train v01~v14와 validation v01~v02
- 정본: 고밀도 생성 지침서와 설계서. 저밀도 및 held-out/evaluation 자료는 생성·분리·유사도 비교 근거에서 제외했다.
- 기계 판독 근거: [`TinyLM_Stage1_Comparison_Train_v01_v14_Final_Audit_2026-09-01.json`](machine/TinyLM_Stage1_Comparison_Train_v01_v14_Final_Audit_2026-09-01.json), [`TinyLM_Stage1_5_10_Validation_Final_Audit_2026-09-01.json`](machine/TinyLM_Stage1_5_10_Validation_Final_Audit_2026-09-01.json), [`TinyLM_Stage1_5_10_Validation_Protected_Baseline_Comparison_2026-09-01.json`](machine/TinyLM_Stage1_5_10_Validation_Protected_Baseline_Comparison_2026-09-01.json)

## 1. 통합 범위와 최종 산출물

| split | 파일 | records | ID 범위 | 문자 수 | 단어 단위 | 판정 |
|---|---:|---:|---|---:|---:|---|
| train | 14 | 2,100 | `S1-COH-0001 ~ S1-COH-2100` | 168,771 | 39,297 | PASS |
| validation | 2 | 300 | `S1-COV-0001 ~ S1-COV-0300` | 22,660 | 5,206 | PASS |

과거 진행 중간 감사는 삭제하지 않고 아래 archive로 이관했다. 현재 판단에는 이 통합 보고서와 machine 최종 감사만 사용한다.

- archive: [`archive/comparison/`](archive/comparison/), 13개 역사 자료

## 2. train concept family 원장

| version | ID 범위 | concept family | 파일 |
|---|---|---|---|
| v01 | `S1-COH-0001 ~ S1-COH-0150` | 길이·면적·부피·질량·밀도의 기준화 비교 | `stage1_(8)comparison_high_density_train_v01.json` |
| v02 | `S1-COH-0151 ~ S1-COH-0300` | 시각·기간·속도·빈도·지연의 시간 비교 | `stage1_(8)comparison_high_density_train_v02.json` |
| v03 | `S1-COH-0301 ~ S1-COH-0450` | 온도·열량·에너지·동력·효율의 비교 | `stage1_(8)comparison_high_density_train_v03.json` |
| v04 | `S1-COH-0451 ~ S1-COH-0600` | 재료 강도·강성·연성·인성·내구성의 비교 | `stage1_(8)comparison_high_density_train_v04.json` |
| v05 | `S1-COH-0601 ~ S1-COH-0750` | 생물 형태·성장·대사·생리 지표의 비교 | `stage1_(8)comparison_high_density_train_v05.json` |
| v06 | `S1-COH-0751 ~ S1-COH-0900` | 생태 개체수·밀도·다양성·생산성의 비교 | `stage1_(8)comparison_high_density_train_v06.json` |
| v07 | `S1-COH-0901 ~ S1-COH-1050` | 통계 분포·중심·산포·비율·위험의 비교 | `stage1_(8)comparison_high_density_train_v07.json` |
| v08 | `S1-COH-1051 ~ S1-COH-1200` | 측정법·센서·검사의 정확도·정밀도 비교 | `stage1_(8)comparison_high_density_train_v08.json` |
| v09 | `S1-COH-1201 ~ S1-COH-1350` | 알고리즘·시스템의 시간·메모리·확장성 비교 | `stage1_(8)comparison_high_density_train_v09.json` |
| v10 | `S1-COH-1351 ~ S1-COH-1500` | 제품·도구의 기능·사용성·비용·유지보수 비교 | `stage1_(8)comparison_high_density_train_v10.json` |
| v11 | `S1-COH-1501 ~ S1-COH-1650` | 교통수단의 속도·용량·안전·에너지 비교 | `stage1_(8)comparison_high_density_train_v11.json` |
| v12 | `S1-COH-1651 ~ S1-COH-1800` | 언어·문서의 명료성·격식·응집성·정보밀도 대조 | `stage1_(8)comparison_high_density_train_v12.json` |
| v13 | `S1-COH-1801 ~ S1-COH-1950` | 정책·서비스의 도달률·효과·형평·비용 대조 | `stage1_(8)comparison_high_density_train_v13.json` |
| v14 | `S1-COH-1951 ~ S1-COH-2100` | 의사결정 대안의 효용·위험·가역성·제약 비교 | `stage1_(8)comparison_high_density_train_v14.json` |

## 3. validation 신규 concept family 원장

| version | ID 범위 | concept family | 파일 |
|---|---|---|---|
| v01 | `S1-COV-0001 ~ S1-COV-0150` | 음악 연주·녹음의 음높이·음량·템포·균형 비교 | `stage1_(8)comparison_high_density_val_v01.json` |
| v02 | `S1-COV-0151 ~ S1-COV-0300` | 농산물 경매·품질등급·가격·수율·보관성 비교 | `stage1_(8)comparison_high_density_val_v02.json` |

각 validation 파일은 150 records이며 `unseen_relation: true` 18개와 false 132개다. 영역 전체 true는 36/300 = 12.00%다. true의 개별 relation label은 train에 모두 존재하고, 정렬 relation-set 조합만 train에 없다.

## 4. relations 통제 어휘 분포

| relation | train | validation |
|---|---:|---:|
| `is_a` | 0 | 0 |
| `subclass_of` | 0 | 0 |
| `part_of` | 4 | 0 |
| `classification` | 198 | 38 |
| `boundary` | 354 | 74 |
| `contrast` | 449 | 78 |
| `comparison` | 1,701 | 228 |
| `function` | 303 | 48 |
| `role` | 60 | 2 |
| `process` | 270 | 40 |
| `state` | 452 | 68 |
| `attribute` | 409 | 60 |
| `other` | 2,100 | 300 |

0회인 relation도 누락하지 않고 표시했다. 각 record는 13개 통제 어휘만 사용하며 2~5개, record 내부 중복 0 조건을 통과했다.

## 5. `other` 편집 유형 상위 5개

### train

| 순위 | 편집 유형 | 횟수 | 예시 primary concept |
|---:|---|---:|---|
| 1 | 다차원 순위 (`multidimensional_order`) | 420 | `미터로통일한두막대길이차`, `킬로미터로환산한두도로거리비`, `밀리미터눈금의판두께순위`, `센티미터로맞춘상자세변길이비교`, `제곱미터로통일한두방바닥면적` |
| 2 | 질적 절충·대조 (`qualitative_tradeoff`) | 420 | `길이와면적의차원대조`, `면적과부피의척도대조`, `질량과무게의개념대조`, `질량과밀도의판정대조`, `부피와용량의사용대조` |
| 3 | 기준 정규화 (`baseline_normalization`) | 420 | `초기길이당신장량비교`, `원래면적당손상면적비율`, `전체부피당빈공간비교`, `단위면적당도료질량비교`, `단위길이당케이블질량비교` |
| 4 | 상황 의존 순위 (`context_dependent_ranking`) | 420 | `같은둘레원과정사각형의면적절충`, `같은부피구와정육면체의표면적절충`, `긴상자와정육면체상자의포장효율`, `넓고얕은용기와좁고깊은용기`, `두꺼운판과넓은얇은판의질량절충` |
| 5 | 불확실성 구간 (`uncertainty_interval`) | 420 | `두줄자측정길이의오차구간비교`, `레이저와줄자거리측정의불확도대조`, `반복두께측정평균의신뢰범위`, `불규칙면적추정의격자오차`, `지도축척거리의반올림범위` |

### validation

| 순위 | 편집 유형 | 횟수 | 예시 primary concept |
|---:|---|---:|---|
| 1 | 참조 기준 정규화 (`reference_normalization`) | 60 | `두바이올린음높이센트차이`, `피아노와오보에기준라주파수`, `가수원음과반음올린키`, `현악기개방현과누른음정`, `합창소프라노와테너동일음이름` |
| 2 | 다차원 순위 (`multidimensional_ranking`) | 60 | `플루트와클라리넷평균음량`, `바이올린과비올라피크음량`, `보컬과반주명료도우위`, `드럼과베이스저역에너지`, `피아노와하프어택선명도` |
| 3 | 상황 의존 순위 (`context_dependent_rank`) | 60 | `야외공연과실내공연보컬명료도`, `작은클럽과큰홀드럼크기감`, `헤드폰과스피커저역균형`, `자동차와스튜디오믹스번역성`, `리허설실과본공연장템포안정감` |
| 4 | 불확실성 구간 (`uncertainty_interval`) | 60 | `두테이크평균템포신뢰구간`, `피치추적기와수동측정오차범위`, `음량계두대교정오차`, `관객석음량표본과전체좌석추정`, `리버브시간측정구간차이` |
| 5 | 질적 대조 (`qualitative_contrast`) | 60 | `레가토와스타카토연결감`, `밝은음색과큰음량경계`, `빠른템포와조밀한리듬대조`, `높은음과날카로운음색경계`, `모노와좁은스테레오대조` |

편집 유형은 source 감사용 분류이며 JSON `relations`에는 통제 어휘 `other`만 기록된다.

## 6. 무결성·분리·문장 품질 감사

| 점검 | train | validation | 판정 |
|---|---:|---:|---|
| JSON/UTF-8/schema/metadata/relation/source 대응 오류 | 0 | 0 | PASS |
| ID·primary concept·정확 문장·primary–relation-set 내부 중복 | 0 | 0 | PASS |
| 대응 train과 validation의 정확 concept/text/object–relation-set 겹침 | — | 0 | PASS |
| 내부 반복 5어절 | 0 | 0 | PASS |
| 대응 train–validation 반복 5어절 | — | 0 | PASS |
| primary concept 직결 조사 오류 | 0 | 0 | PASS |
| 문자 3~5-gram 내부 최대 cosine | 0.324903 | 0.222778 | 검토 완료 |
| 기존 고밀도/train 교차 최대 cosine | 0.418577 | 0.174069 | 검토 완료 |
| validation 유사도 0.72 이상 후보 | — | 내부 0, train 교차 0 | PASS |

validation 문장 길이는 최소 62자, 중앙값 75.0자, 평균 75.533자, 최대 91자다. 전체 validation과 외부 고밀도 36,250 records 사이의 정확 primary/text/primary–relation-set 겹침 및 공통 5어절도 모두 0건이다.

작업 시작 전에 존재한 train/val JSON 242개는 종료 시점에 242/242 SHA-256이 일치했다. 변경·누락은 0건이고 새 validation JSON 13개만 추가되었으므로 identity 및 기존 train/val 정본은 수정되지 않았다.

광역 조사 탐지 후보는 train 8건, validation 1건이었다. 최종 원문 대조에서 validation 후보는 `맞닿는`, `가까이`, `물려받는` 같은 정상 용언·복합어·외래어에 대한 오탐이며 실제 조사 불량은 0건이다. 반복 5어절 초안 후보는 직접 다시 표현한 뒤 최종 0건을 확인했다.

## 7. 확정 결론

Stage1 (8) 비교·대조 train과 validation은 파일 수·레코드 수·ID·family 분리·통제 relation·일반화 slice·중복·유사도·조사 점검을 통과했다. 이 보고서는 동일 교육영역의 종전 파편화 보고서를 대체하는 현재 정본이며, machine JSON과 archive는 각각 재현 가능한 세부 근거와 역사 기록으로 보존한다.
