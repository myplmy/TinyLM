# Stage1 (10) 타입·부정·불확실성 통합 감사 보고서

- 최종 판정: **PASS**
- 통합일: 2026-09-01
- 범위: train v01~v09와 validation v01~v01
- 정본: 고밀도 생성 지침서와 설계서. 저밀도 및 held-out/evaluation 자료는 생성·분리·유사도 비교 근거에서 제외했다.
- 기계 판독 근거: [`TinyLM_Stage1_TypeUncertainty_Train_v01_v09_Final_Audit_2026-09-01.json`](machine/TinyLM_Stage1_TypeUncertainty_Train_v01_v09_Final_Audit_2026-09-01.json), [`TinyLM_Stage1_5_10_Validation_Final_Audit_2026-09-01.json`](machine/TinyLM_Stage1_5_10_Validation_Final_Audit_2026-09-01.json), [`TinyLM_Stage1_5_10_Validation_Protected_Baseline_Comparison_2026-09-01.json`](machine/TinyLM_Stage1_5_10_Validation_Protected_Baseline_Comparison_2026-09-01.json)

## 1. 통합 범위와 최종 산출물

| split | 파일 | records | ID 범위 | 문자 수 | 단어 단위 | 판정 |
|---|---:|---:|---|---:|---:|---|
| train | 9 | 1,350 | `S1-TUH-0001 ~ S1-TUH-1350` | 100,895 | 22,940 | PASS |
| validation | 1 | 150 | `S1-TUV-0001 ~ S1-TUV-0150` | 14,046 | 3,282 | PASS |

과거 진행 중간 감사는 삭제하지 않고 아래 archive로 이관했다. 현재 판단에는 이 통합 보고서와 machine 최종 감사만 사용한다.

- archive: [`archive/type_uncertainty/`](archive/type_uncertainty/), 8개 역사 자료

## 2. train concept family 원장

| version | ID 범위 | concept family | 파일 |
|---|---|---|---|
| v01 | `S1-TUH-0001 ~ S1-TUH-0150` | 클래스·인스턴스·토큰·식별자·메타타입 구분 | `stage1_(10)type_uncertainty_high_density_train_v01.json` |
| v02 | `S1-TUH-0151 ~ S1-TUH-0300` | Entity·Attribute·Quantity·Relation·State·Action 타입 구분 | `stage1_(10)type_uncertainty_high_density_train_v02.json` |
| v03 | `S1-TUH-0301 ~ S1-TUH-0450` | 한국어 명제 부정·부분 부정·양화·범위 해석 | `stage1_(10)type_uncertainty_high_density_train_v03.json` |
| v04 | `S1-TUH-0451 ~ S1-TUH-0600` | 부재·비존재·빈값·0·삭제·접근불가 구분 | `stage1_(10)type_uncertainty_high_density_train_v04.json` |
| v05 | `S1-TUH-0601 ~ S1-TUH-0750` | 미관측·미측정·미기록·미응답·알수없음 구분 | `stage1_(10)type_uncertainty_high_density_train_v05.json` |
| v06 | `S1-TUH-0751 ~ S1-TUH-0900` | 가능성·확률·확신·추정·증거 강도의 구분 | `stage1_(10)type_uncertainty_high_density_train_v06.json` |
| v07 | `S1-TUH-0901 ~ S1-TUH-1050` | 상충·불완전·모호·오래된 출처의 불확실성 통합 | `stage1_(10)type_uncertainty_high_density_train_v07.json` |
| v08 | `S1-TUH-1051 ~ S1-TUH-1200` | 센서·검사·탐지의 양성·음성·오탐·미탐·검출한계 | `stage1_(10)type_uncertainty_high_density_train_v08.json` |
| v09 | `S1-TUH-1201 ~ S1-TUH-1350` | 계획·예측·가정·시뮬레이션·반사실과 실제 사건 구분 | `stage1_(10)type_uncertainty_high_density_train_v09.json` |

## 3. validation 신규 concept family 원장

| version | ID 범위 | concept family | 파일 |
|---|---|---|---|
| v01 | `S1-TUV-0001 ~ S1-TUV-0150` | 역사연구 사료·증언·연대추정·번역·복원가설 불확실성 판정 | `stage1_(10)type_uncertainty_high_density_val_v01.json` |

각 validation 파일은 150 records이며 `unseen_relation: true` 18개와 false 132개다. 영역 전체 true는 18/150 = 12.00%다. true의 개별 relation label은 train에 모두 존재하고, 정렬 relation-set 조합만 train에 없다.

## 4. relations 통제 어휘 분포

| relation | train | validation |
|---|---:|---:|
| `is_a` | 0 | 0 |
| `subclass_of` | 0 | 0 |
| `part_of` | 17 | 4 |
| `classification` | 486 | 65 |
| `boundary` | 1,350 | 150 |
| `contrast` | 1 | 0 |
| `comparison` | 144 | 34 |
| `function` | 3 | 7 |
| `role` | 31 | 12 |
| `process` | 217 | 30 |
| `state` | 1,136 | 98 |
| `attribute` | 361 | 36 |
| `other` | 1,350 | 150 |

0회인 relation도 누락하지 않고 표시했다. 각 record는 13개 통제 어휘만 사용하며 2~5개, record 내부 중복 0 조건을 통과했다.

## 5. `other` 편집 유형 상위 5개

### train

| 순위 | 편집 유형 | 횟수 | 예시 primary concept |
|---:|---|---:|---|
| 1 | 메타타입·지시 층위 (`metatype_reference`) | 270 | `클래스인스턴스층위구분`, `유형사례포함방향판정`, `동물클래스표현구분`, `고양이사례지시판정`, `토큰타입반복구분` |
| 2 | 부정 범위 (`negation_scope`) | 270 | `클래스포함부정범위`, `인스턴스동일성부정판정`, `모든사례부정범위판정`, `일부사례비해당판정`, `유일인스턴스부정해석` |
| 3 | 부재·비존재 (`absence_nonexistence`) | 270 | `무인스턴스클래스판정`, `삭제인스턴스식별자잔존판정`, `미할당식별자상태판정`, `빈문자열값부재구분`, `널값필드비존재구분` |
| 4 | 미상·미관측 (`unknown_unobserved`) | 270 | `미분류인스턴스타입판정`, `식별자대상미조회판정`, `토큰타입미해석판정`, `스키마버전미기록판정`, `별칭대상모호판정` |
| 5 | 불확실성·증거 강도 (`uncertainty_evidence`) | 270 | `인스턴스타입후보판정`, `식별자일치확률판정`, `스키마타입추정신뢰판정`, `별칭연결개연성판정`, `클래스경계추정판정` |

### validation

| 순위 | 편집 유형 | 횟수 | 예시 primary concept |
|---:|---|---:|---|
| 1 | 사료 유형·참조 단위 (`source_type_reference`) | 30 | `왕실일기원본사본구분`, `비문탁본과석면판독차이`, `구술증언과동시대문서위상`, `지방지초간본과증보판계통`, `관보기사와신문재전재관계` |
| 2 | 부정 범위 (`negation_scope`) | 30 | `칙령에서금지하지않은행위`, `조약문일부지역비적용`, `목격자가보지못한행렬`, `회의불참과정책반대구분`, `세금미납과면제기록차이` |
| 3 | 기록의 공백·침묵 (`absence_silence`) | 30 | `재난연도세입장부공백`, `실록에누락된지방반란`, `항만일지없는밀수추정`, `묘역에서발견되지않은부장품`, `노동자명부의여성공란` |
| 4 | 연대 구간·시간 추정 (`chronology_uncertainty`) | 30 | `간지표기와서기연도환산`, `탄소연대측정오차구간`, `왕재위년과즉위식연도차이`, `나이기록의세는나이환산`, `화산재층과유적건립순서` |
| 5 | 가설·증거 강도 (`hypothesis_evidence`) | 30 | `소실성문지붕형태복원안`, `익명서한작성자후보판정`, `파손비석결락문구보충`, `고대도로추정노선연결`, `침몰선적재항구추정` |

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
| 문자 3~5-gram 내부 최대 cosine | 0.392918 | 0.099034 | 검토 완료 |
| 기존 고밀도/train 교차 최대 cosine | 0.289830 | 0.130310 | 검토 완료 |
| validation 유사도 0.72 이상 후보 | — | 내부 0, train 교차 0 | PASS |

validation 문장 길이는 최소 82자, 중앙값 93.0자, 평균 93.640자, 최대 112자다. 전체 validation과 외부 고밀도 36,250 records 사이의 정확 primary/text/primary–relation-set 겹침 및 공통 5어절도 모두 0건이다.

작업 시작 전에 존재한 train/val JSON 242개는 종료 시점에 242/242 SHA-256이 일치했다. 변경·누락은 0건이고 새 validation JSON 13개만 추가되었으므로 identity 및 기존 train/val 정본은 수정되지 않았다.

광역 조사 탐지 후보는 train 9건, validation 1건이었다. 최종 원문 대조에서 validation 후보는 `맞닿는`, `가까이`, `물려받는` 같은 정상 용언·복합어·외래어에 대한 오탐이며 실제 조사 불량은 0건이다. 반복 5어절 초안 후보는 직접 다시 표현한 뒤 최종 0건을 확인했다.

## 7. 확정 결론

Stage1 (10) 타입·부정·불확실성 train과 validation은 파일 수·레코드 수·ID·family 분리·통제 relation·일반화 slice·중복·유사도·조사 점검을 통과했다. 이 보고서는 동일 교육영역의 종전 파편화 보고서를 대체하는 현재 정본이며, machine JSON과 archive는 각각 재현 가능한 세부 근거와 역사 기록으로 보존한다.
