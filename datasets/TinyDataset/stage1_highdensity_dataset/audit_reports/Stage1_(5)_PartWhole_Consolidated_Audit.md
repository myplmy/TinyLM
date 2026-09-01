# Stage1 (5) 부분–전체 통합 감사 보고서

- 최종 판정: **PASS**
- 통합일: 2026-09-01
- 범위: train v01~v23와 validation v01~v03
- 정본: 고밀도 생성 지침서와 설계서. 저밀도 및 held-out/evaluation 자료는 생성·분리·유사도 비교 근거에서 제외했다.
- 기계 판독 근거: [`TinyLM_Stage1_PartWhole_Train_v01_v23_Final_Audit_2026-08-31.json`](machine/TinyLM_Stage1_PartWhole_Train_v01_v23_Final_Audit_2026-08-31.json), [`TinyLM_Stage1_5_10_Validation_Final_Audit_2026-09-01.json`](machine/TinyLM_Stage1_5_10_Validation_Final_Audit_2026-09-01.json), [`TinyLM_Stage1_5_10_Validation_Protected_Baseline_Comparison_2026-09-01.json`](machine/TinyLM_Stage1_5_10_Validation_Protected_Baseline_Comparison_2026-09-01.json)

## 1. 통합 범위와 최종 산출물

| split | 파일 | records | ID 범위 | 문자 수 | 단어 단위 | 판정 |
|---|---:|---:|---|---:|---:|---|
| train | 23 | 3,450 | `S1-PWH-0001 ~ S1-PWH-3450` | 309,841 | 67,889 | PASS |
| validation | 3 | 450 | `S1-PWV-0001 ~ S1-PWV-0450` | 36,250 | 8,456 | PASS |

과거 진행 중간 감사는 삭제하지 않고 아래 archive로 이관했다. 현재 판단에는 이 통합 보고서와 machine 최종 감사만 사용한다.

- archive: [`archive/partwhole/`](archive/partwhole/), 27개 역사 자료

## 2. train concept family 원장

| version | ID 범위 | concept family | 파일 |
|---|---|---|---|
| v01 | `S1-PWH-0001 ~ S1-PWH-0150` | 인체 기관계·기관·조직·세포의 구성 계층 | `stage1_(5)partwhole_high_density_train_v01.json` |
| v02 | `S1-PWH-0151 ~ S1-PWH-0300` | 식물 뿌리·줄기·잎·꽃·열매·종자의 구성 | `stage1_(5)partwhole_high_density_train_v02.json` |
| v03 | `S1-PWH-0301 ~ S1-PWH-0450` | 동물 골격·근육·외피·감각기관의 구성 | `stage1_(5)partwhole_high_density_train_v03.json` |
| v04 | `S1-PWH-0451 ~ S1-PWH-0600` | 세포 소기관·막계·분자복합체의 구성 | `stage1_(5)partwhole_high_density_train_v04.json` |
| v05 | `S1-PWH-0601 ~ S1-PWH-0750` | 생태계·먹이망·서식지·물질순환의 구성 | `stage1_(5)partwhole_high_density_train_v05.json` |
| v06 | `S1-PWH-0751 ~ S1-PWH-0900` | 지층·암석·토양단면·유역·하천망의 구성 | `stage1_(5)partwhole_high_density_train_v06.json` |
| v07 | `S1-PWH-0901 ~ S1-PWH-1050` | 은하·항성계·행성계·천체 내부의 구성 | `stage1_(5)partwhole_high_density_train_v07.json` |
| v08 | `S1-PWH-1051 ~ S1-PWH-1200` | 건축 구조·외피·실내·설비의 구성 | `stage1_(5)partwhole_high_density_train_v08.json` |
| v09 | `S1-PWH-1201 ~ S1-PWH-1350` | 도로·교량·터널·상하수도 도시망의 구성 | `stage1_(5)partwhole_high_density_train_v09.json` |
| v10 | `S1-PWH-1351 ~ S1-PWH-1500` | 자동차·철도차량·자전거의 조립 계층 | `stage1_(5)partwhole_high_density_train_v10.json` |
| v11 | `S1-PWH-1501 ~ S1-PWH-1650` | 항공기·헬리콥터·우주선의 조립 계층 | `stage1_(5)partwhole_high_density_train_v11.json` |
| v12 | `S1-PWH-1651 ~ S1-PWH-1800` | 선박·해양플랜트·항만설비의 구성 | `stage1_(5)partwhole_high_density_train_v12.json` |
| v13 | `S1-PWH-1801 ~ S1-PWH-1950` | 기계요소·동력전달·생산라인의 구성 | `stage1_(5)partwhole_high_density_train_v13.json` |
| v14 | `S1-PWH-1951 ~ S1-PWH-2100` | 전기회로·전자기기·전력설비의 구성 | `stage1_(5)partwhole_high_density_train_v14.json` |
| v15 | `S1-PWH-2101 ~ S1-PWH-2250` | 컴퓨터 하드웨어·저장장치·네트워크의 구성 | `stage1_(5)partwhole_high_density_train_v15.json` |
| v16 | `S1-PWH-2251 ~ S1-PWH-2400` | 소프트웨어·코드·데이터·문서의 논리 구성 | `stage1_(5)partwhole_high_density_train_v16.json` |
| v17 | `S1-PWH-2401 ~ S1-PWH-2550` | 담화·문장·구·단어·형태소의 언어 구성 | `stage1_(5)partwhole_high_density_train_v17.json` |
| v18 | `S1-PWH-2551 ~ S1-PWH-2700` | 집합·식·증명·도형의 수학적 구성 | `stage1_(5)partwhole_high_density_train_v18.json` |
| v19 | `S1-PWH-2701 ~ S1-PWH-2850` | 지도·지형구역·행정구역·필지의 공간 계층 | `stage1_(5)partwhole_high_density_train_v19.json` |
| v20 | `S1-PWH-2851 ~ S1-PWH-3000` | 조직·부서·팀·위원회·프로젝트의 구성 | `stage1_(5)partwhole_high_density_train_v20.json` |
| v21 | `S1-PWH-3001 ~ S1-PWH-3150` | 법령·계약·사건기록·증거 묶음의 문서 구성 | `stage1_(5)partwhole_high_density_train_v21.json` |
| v22 | `S1-PWH-3151 ~ S1-PWH-3300` | 회화·조각·음악·공연·영상 작품의 구성 | `stage1_(5)partwhole_high_density_train_v22.json` |
| v23 | `S1-PWH-3301 ~ S1-PWH-3450` | 식재료·조리법·한 끼·포장·생산묶음의 구성 | `stage1_(5)partwhole_high_density_train_v23.json` |

## 3. validation 신규 concept family 원장

| version | ID 범위 | concept family | 파일 |
|---|---|---|---|
| v01 | `S1-PWV-0001 ~ S1-PWV-0150` | 도서관 장서·서지레코드·권호·대출 단위 구성 | `stage1_(5)partwhole_high_density_val_v01.json` |
| v02 | `S1-PWV-0151 ~ S1-PWV-0300` | 의류 패턴·재단 조각·봉제 부품·완제품 구성 | `stage1_(5)partwhole_high_density_val_v02.json` |
| v03 | `S1-PWV-0301 ~ S1-PWV-0450` | 우편물·행낭·운송편·배달구역 물류 구성 | `stage1_(5)partwhole_high_density_val_v03.json` |

각 validation 파일은 150 records이며 `unseen_relation: true` 18개와 false 132개다. 영역 전체 true는 54/450 = 12.00%다. true의 개별 relation label은 train에 모두 존재하고, 정렬 relation-set 조합만 train에 없다.

## 4. relations 통제 어휘 분포

| relation | train | validation |
|---|---:|---:|
| `is_a` | 21 | 0 |
| `subclass_of` | 30 | 0 |
| `part_of` | 3,450 | 450 |
| `classification` | 1,149 | 149 |
| `boundary` | 766 | 76 |
| `contrast` | 218 | 0 |
| `comparison` | 85 | 0 |
| `function` | 2,175 | 370 |
| `role` | 275 | 49 |
| `process` | 907 | 91 |
| `state` | 571 | 85 |
| `attribute` | 286 | 74 |
| `other` | 407 | 60 |

0회인 relation도 누락하지 않고 표시했다. 각 record는 13개 통제 어휘만 사용하며 2~5개, record 내부 중복 0 조건을 통과했다.

## 5. `other` 편집 유형 상위 5개

### train

| 순위 | 편집 유형 | 횟수 | 예시 primary concept |
|---:|---|---:|---|
| 1 | 추상 구획·과정 구조 (`abstract_structure`) | 166 | `종격과기관배치구성`, `복부사분면과장기위치구성`, `꽃과네기관윤생구성`, `일차식물체와새기관구성`, `곤충몸과세체구역구성` |
| 2 | 집합 정체성 (`aggregate_identity`) | 135 | `두콩팥과한쌍구성`, `두폐와한쌍구성`, `두눈과한쌍구성`, `두부신과한쌍구성`, `꽃받침과조각묶음구성` |
| 3 | 물질적 몫 (`material_portion`) | 46 | `혈액과혈장구성`, `잎표피와각피구성`, `비늘줄기와비늘잎구성`, `새부리와각질덮개구성`, `포유류귓바퀴와탄력연골구성` |
| 4 | 구성원·구조부품 경계 (`membership_component_boundary`) | 34 | `손목뼈와여덟뼈구성`, `관모양기관과벽내강구성`, `림프절과겉속구획구성`, `꽃차례와개별꽃구성`, `열매와종자내용구성` |
| 5 | 공통 발생 기원 묶음 (`provenance_grouping`) | 26 | `중추신경계와신경관유래구조구성`, `이차물관부와나이테구성`, `이과와꽃턱유래과육구성`, `다화과와꽃차례유래단위구성`, `종자와외배유구성` |

### validation

| 순위 | 편집 유형 | 횟수 | 예시 primary concept |
|---:|---|---:|---|
| 1 | 기록 범위·단위 (`record_scope`) | 6 | `정부간행물서가와예산백서`, `권위레코드와이형이름`, `분석서지레코드와수록논문`, `학술지레코드와후속표제`, `고서레코드와판심표기` |
| 2 | 컬렉션 소속·묶음 (`collection_membership`) | 5 | `기증문고와기증잡지`, `점자자료모음과점자소설`, `독서회선정도서모음과토론책`, `신문연간철과신년호`, `악보파트세트와누락파트` |
| 3 | 선택적 구성요소 (`optional_component`) | 5 | `블라우스와장식프릴조각`, `후드티와조임끈구멍보강천`, `정장바지와장식비죠`, `패딩점퍼와탈착털장식`, `바지와동전주머니` |
| 4 | 구성원 예외·비소속 (`membership_exception`) | 5 | `배달권역과경계밖오주소`, `배달회차와개인휴대물`, `부재배달건과문앞사물`, `반송처리건과무관한광고지`, `우편물인계건과옆차량화물` |
| 5 | 운반체·내용물 범위 (`carrier_content_scope`) | 4 | `고문서첩과봉투`, `한선반과도서받침대`, `자료상자와완충재`, `도난방지게이트와감지패널` |

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
| 문자 3~5-gram 내부 최대 cosine | 0.342280 | 0.262881 | 검토 완료 |
| 기존 고밀도/train 교차 최대 cosine | 0.324924 | 0.134686 | 검토 완료 |
| validation 유사도 0.72 이상 후보 | — | 내부 0, train 교차 0 | PASS |

validation 문장 길이는 최소 65자, 중앙값 80.0자, 평균 80.556자, 최대 99자다. 전체 validation과 외부 고밀도 36,250 records 사이의 정확 primary/text/primary–relation-set 겹침 및 공통 5어절도 모두 0건이다.

작업 시작 전에 존재한 train/val JSON 242개는 종료 시점에 242/242 SHA-256이 일치했다. 변경·누락은 0건이고 새 validation JSON 13개만 추가되었으므로 identity 및 기존 train/val 정본은 수정되지 않았다.

광역 조사 탐지 후보는 train 33건, validation 5건이었다. 최종 원문 대조에서 validation 후보는 `맞닿는`, `가까이`, `물려받는` 같은 정상 용언·복합어·외래어에 대한 오탐이며 실제 조사 불량은 0건이다. 반복 5어절 초안 후보는 직접 다시 표현한 뒤 최종 0건을 확인했다.

## 7. 확정 결론

Stage1 (5) 부분–전체 train과 validation은 파일 수·레코드 수·ID·family 분리·통제 relation·일반화 slice·중복·유사도·조사 점검을 통과했다. 이 보고서는 동일 교육영역의 종전 파편화 보고서를 대체하는 현재 정본이며, machine JSON과 archive는 각각 재현 가능한 세부 근거와 역사 기록으로 보존한다.
