# Stage1 (6) 상태·상태 변화 통합 감사 보고서

- 최종 판정: **PASS**
- 통합일: 2026-09-01
- 범위: train v01~v23와 validation v01~v03
- 정본: 고밀도 생성 지침서와 설계서. 저밀도 및 held-out/evaluation 자료는 생성·분리·유사도 비교 근거에서 제외했다.
- 기계 판독 근거: [`TinyLM_Stage1_StateChange_Train_v01_v23_Final_Audit_2026-09-01.json`](machine/TinyLM_Stage1_StateChange_Train_v01_v23_Final_Audit_2026-09-01.json), [`TinyLM_Stage1_5_10_Validation_Final_Audit_2026-09-01.json`](machine/TinyLM_Stage1_5_10_Validation_Final_Audit_2026-09-01.json), [`TinyLM_Stage1_5_10_Validation_Protected_Baseline_Comparison_2026-09-01.json`](machine/TinyLM_Stage1_5_10_Validation_Protected_Baseline_Comparison_2026-09-01.json)

## 1. 통합 범위와 최종 산출물

| split | 파일 | records | ID 범위 | 문자 수 | 단어 단위 | 판정 |
|---|---:|---:|---|---:|---:|---|
| train | 23 | 3,450 | `S1-SCH-0001 ~ S1-SCH-3450` | 280,214 | 65,489 | PASS |
| validation | 3 | 450 | `S1-SCV-0001 ~ S1-SCV-0450` | 34,439 | 7,622 | PASS |

과거 진행 중간 감사는 삭제하지 않고 아래 archive로 이관했다. 현재 판단에는 이 통합 보고서와 machine 최종 감사만 사용한다.

- archive: [`archive/statechange/`](archive/statechange/), 6개 역사 자료

## 2. train concept family 원장

| version | ID 범위 | concept family | 파일 |
|---|---|---|---|
| v01 | `S1-SCH-0001 ~ S1-SCH-0150` | 물질 상·용해·결정화·응고·기화 상태 전이 | `stage1_(6)statechange_high_density_train_v01.json` |
| v02 | `S1-SCH-0151 ~ S1-SCH-0300` | 온도·열평형·가열·냉각·열저장 상태 변화 | `stage1_(6)statechange_high_density_train_v02.json` |
| v03 | `S1-SCH-0301 ~ S1-SCH-0450` | 화학 반응·농도·산염기·산화환원 상태 변화 | `stage1_(6)statechange_high_density_train_v03.json` |
| v04 | `S1-SCH-0451 ~ S1-SCH-0600` | 운동·정지·진동·변형·파손·마모 상태 변화 | `stage1_(6)statechange_high_density_train_v04.json` |
| v05 | `S1-SCH-0601 ~ S1-SCH-0750` | 전기회로 전원·충전·스위칭·고장·복구 상태 | `stage1_(6)statechange_high_density_train_v05.json` |
| v06 | `S1-SCH-0751 ~ S1-SCH-0900` | 운영체제 프로세스·작업·자원 잠금 생명주기 | `stage1_(6)statechange_high_density_train_v06.json` |
| v07 | `S1-SCH-0901 ~ S1-SCH-1050` | 데이터·문서·버전·승인·보관 생명주기 | `stage1_(6)statechange_high_density_train_v07.json` |
| v08 | `S1-SCH-1051 ~ S1-SCH-1200` | 네트워크 연결·세션·동기화·장애 상태 전이 | `stage1_(6)statechange_high_density_train_v08.json` |
| v09 | `S1-SCH-1201 ~ S1-SCH-1350` | 기기 전원모드·배터리·충전·열제한 상태 변화 | `stage1_(6)statechange_high_density_train_v09.json` |
| v10 | `S1-SCH-1351 ~ S1-SCH-1500` | 건물 점유·출입·방재·보안 운용 상태 변화 | `stage1_(6)statechange_high_density_train_v10.json` |
| v11 | `S1-SCH-1501 ~ S1-SCH-1650` | 차량·열차·항공기·선박 운항 단계와 상태 전이 | `stage1_(6)statechange_high_density_train_v11.json` |
| v12 | `S1-SCH-1651 ~ S1-SCH-1800` | 주문·포장·운송·인도·반품 물류 상태 변화 | `stage1_(6)statechange_high_density_train_v12.json` |
| v13 | `S1-SCH-1801 ~ S1-SCH-1950` | 제조 공정품·설비·품질 판정 상태 변화 | `stage1_(6)statechange_high_density_train_v13.json` |
| v14 | `S1-SCH-1951 ~ S1-SCH-2100` | 식품 조리·발효·숙성·저장·변질 상태 변화 | `stage1_(6)statechange_high_density_train_v14.json` |
| v15 | `S1-SCH-2101 ~ S1-SCH-2250` | 식물 발아·생장·개화·결실·휴면·스트레스 변화 | `stage1_(6)statechange_high_density_train_v15.json` |
| v16 | `S1-SCH-2251 ~ S1-SCH-2400` | 동물 활동·섭식·이동·번식·휴식 행동 상태 | `stage1_(6)statechange_high_density_train_v16.json` |
| v17 | `S1-SCH-2401 ~ S1-SCH-2550` | 사람 수면·각성·운동·피로·회복의 일반 생리 상태 | `stage1_(6)statechange_high_density_train_v17.json` |
| v18 | `S1-SCH-2551 ~ S1-SCH-2700` | 대기·구름·전선·강수·폭풍의 발달과 소멸 | `stage1_(6)statechange_high_density_train_v18.json` |
| v19 | `S1-SCH-2701 ~ S1-SCH-2850` | 하천·호수·지하수·홍수·가뭄 수문 상태 변화 | `stage1_(6)statechange_high_density_train_v19.json` |
| v20 | `S1-SCH-2851 ~ S1-SCH-3000` | 풍화·침식·퇴적·사면·지각변형 상태 변화 | `stage1_(6)statechange_high_density_train_v20.json` |
| v21 | `S1-SCH-3001 ~ S1-SCH-3150` | 회의·협업·프로젝트·결정·갈등 상태 변화 | `stage1_(6)statechange_high_density_train_v21.json` |
| v22 | `S1-SCH-3151 ~ S1-SCH-3300` | 계좌·거래·청구·계약·심사 상태 생명주기 | `stage1_(6)statechange_high_density_train_v22.json` |
| v23 | `S1-SCH-3301 ~ S1-SCH-3450` | 학습·주의·기억·정서·과제진행 상태 변화 | `stage1_(6)statechange_high_density_train_v23.json` |

## 3. validation 신규 concept family 원장

| version | ID 범위 | concept family | 파일 |
|---|---|---|---|
| v01 | `S1-SCV-0001 ~ S1-SCV-0150` | 박물관 유물 보존처리·안정화·복원·수장 상태 변화 | `stage1_(6)statechange_high_density_val_v01.json` |
| v02 | `S1-SCV-0151 ~ S1-SCV-0300` | 공연 제작·연습·무대전환·개막·철거 상태 변화 | `stage1_(6)statechange_high_density_val_v02.json` |
| v03 | `S1-SCV-0301 ~ S1-SCV-0450` | 법원 사건 접수·배당·심리·판결·종결 상태 변화 | `stage1_(6)statechange_high_density_val_v03.json` |

각 validation 파일은 150 records이며 `unseen_relation: true` 18개와 false 132개다. 영역 전체 true는 54/450 = 12.00%다. true의 개별 relation label은 train에 모두 존재하고, 정렬 relation-set 조합만 train에 없다.

## 4. relations 통제 어휘 분포

| relation | train | validation |
|---|---:|---:|
| `is_a` | 0 | 0 |
| `subclass_of` | 0 | 0 |
| `part_of` | 13 | 0 |
| `classification` | 454 | 84 |
| `boundary` | 820 | 75 |
| `contrast` | 467 | 75 |
| `comparison` | 92 | 15 |
| `function` | 827 | 90 |
| `role` | 206 | 45 |
| `process` | 3,450 | 450 |
| `state` | 3,450 | 450 |
| `attribute` | 374 | 75 |
| `other` | 198 | 45 |

0회인 relation도 누락하지 않고 표시했다. 각 record는 13개 통제 어휘만 사용하며 2~5개, record 내부 중복 0 조건을 통과했다.

## 5. `other` 편집 유형 상위 5개

### train

| 순위 | 편집 유형 | 횟수 | 예시 primary concept |
|---:|---|---:|---|
| 1 | 잠재 상태와 관측 상태 (`latent_observed_state`) | 121 | `설탕시럽의냉각고화와유리상`, `용해평형과고체잔류상태`, `결정성판정과회절무늬변화`, `과냉각물의준안정액체상태`, `상평형도판독과현재상태추정` |
| 2 | 전이 촉발 조건 (`transition_trigger`) | 44 | `고액전이판정과잠열구간`, `과포화용액의유도시간`, `과열액체의급격한비등`, `핵생성장벽과상전이지연`, `스피노달분해의조성분리` |
| 3 | 생명주기 상태 (`lifecycle_status`) | 25 | `의약품결정다형의상전이`, `준안정상과안정상전환`, `냉장창고상한온도일시이탈`, `암반축열공의온도전선이동`, `보트의엔진정지후표류전환` |
| 4 | 회복·열화 (`recovery_degradation`) | 5 | `세포내수분의동결과해동손상`, `냉장택배상자개봉후온도복귀실패`, `피로하중제거후잔류손상상태`, `식물의스트레스회복미확정`, `피로후수행회복미확정` |
| 5 | 가역성 범위 (`reversibility_scope`) | 3 | `열경화성수지의경화와비가역고화`, `상변태히스테리시스와가열냉각경로`, `완성품의편차허용검토중` |

### validation

| 순위 | 편집 유형 | 횟수 | 예시 primary concept |
|---:|---|---:|---|
| 1 | 측정 한계 (`measurement_limit`) | 4 | `안료박락미상에서접촉검사전이`, `가죽경화미상에서굴곡관찰전이`, `오염성분미상에서분석의뢰전이`, `직물염료미확인에서세척중지전이` |
| 2 | 관찰·모니터링 불확실성 (`monitoring_uncertainty`) | 3 | `청동표면가루미상에서격리관찰전이`, `전시환경미상에서데이터로거가동전이`, `대여품상태미확인에서긴급사진요청전이` |
| 3 | 출처·이력 검토 (`provenance_review`) | 2 | `출처미확인에서검토필요전이`, `과거수리미상에서기록대조전이` |
| 4 | 목록·재고 예외 (`inventory_exception`) | 2 | `반입목록불일치에서재대조전이`, `위치미확인에서분실의심전이` |
| 5 | 복원 가설 (`reconstruction_hypothesis`) | 2 | `결손형태미상에서가상복원검토전이`, `회화결손색미상에서중성톤전이` |

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
| 문자 3~5-gram 내부 최대 cosine | 0.356120 | 0.267992 | 검토 완료 |
| 기존 고밀도/train 교차 최대 cosine | 0.299638 | 0.144340 | 검토 완료 |
| validation 유사도 0.72 이상 후보 | — | 내부 0, train 교차 0 | PASS |

validation 문장 길이는 최소 64자, 중앙값 76.0자, 평균 76.531자, 최대 102자다. 전체 validation과 외부 고밀도 36,250 records 사이의 정확 primary/text/primary–relation-set 겹침 및 공통 5어절도 모두 0건이다.

작업 시작 전에 존재한 train/val JSON 242개는 종료 시점에 242/242 SHA-256이 일치했다. 변경·누락은 0건이고 새 validation JSON 13개만 추가되었으므로 identity 및 기존 train/val 정본은 수정되지 않았다.

광역 조사 탐지 후보는 train 44건, validation 1건이었다. 최종 원문 대조에서 validation 후보는 `맞닿는`, `가까이`, `물려받는` 같은 정상 용언·복합어·외래어에 대한 오탐이며 실제 조사 불량은 0건이다. 반복 5어절 초안 후보는 직접 다시 표현한 뒤 최종 0건을 확인했다.

## 7. 확정 결론

Stage1 (6) 상태·상태 변화 train과 validation은 파일 수·레코드 수·ID·family 분리·통제 relation·일반화 slice·중복·유사도·조사 점검을 통과했다. 이 보고서는 동일 교육영역의 종전 파편화 보고서를 대체하는 현재 정본이며, machine JSON과 archive는 각각 재현 가능한 세부 근거와 역사 기록으로 보존한다.
