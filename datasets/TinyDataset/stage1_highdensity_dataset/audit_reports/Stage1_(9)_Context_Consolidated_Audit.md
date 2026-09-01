# Stage1 (9) 문맥 통합 통합 감사 보고서

- 최종 판정: **PASS**
- 통합일: 2026-09-01
- 범위: train v01~v12와 validation v01~v02
- 정본: 고밀도 생성 지침서와 설계서. 저밀도 및 held-out/evaluation 자료는 생성·분리·유사도 비교 근거에서 제외했다.
- 기계 판독 근거: [`TinyLM_Stage1_Context_Train_v01_v12_Final_Audit_2026-09-01.json`](machine/TinyLM_Stage1_Context_Train_v01_v12_Final_Audit_2026-09-01.json), [`TinyLM_Stage1_5_10_Validation_Final_Audit_2026-09-01.json`](machine/TinyLM_Stage1_5_10_Validation_Final_Audit_2026-09-01.json), [`TinyLM_Stage1_5_10_Validation_Protected_Baseline_Comparison_2026-09-01.json`](machine/TinyLM_Stage1_5_10_Validation_Protected_Baseline_Comparison_2026-09-01.json)

## 1. 통합 범위와 최종 산출물

| split | 파일 | records | ID 범위 | 문자 수 | 단어 단위 | 판정 |
|---|---:|---:|---|---:|---:|---|
| train | 12 | 1,800 | `S1-CTH-0001 ~ S1-CTH-1800` | 140,702 | 29,367 | PASS |
| validation | 2 | 300 | `S1-CTV-0001 ~ S1-CTV-0300` | 23,890 | 4,858 | PASS |

과거 진행 중간 감사는 삭제하지 않고 아래 archive로 이관했다. 현재 판단에는 이 통합 보고서와 machine 최종 감사만 사용한다.

- archive: [`archive/context/`](archive/context/), 11개 역사 자료

## 2. train concept family 원장

| version | ID 범위 | concept family | 파일 |
|---|---|---|---|
| v01 | `S1-CTH-0001 ~ S1-CTH-0150` | 가정의 준비·정리·세탁·수리 일상 상황 | `stage1_(9)context_high_density_train_v01.json` |
| v02 | `S1-CTH-0151 ~ S1-CTH-0300` | 주방의 재료 준비·조리·보관·제공 상황 | `stage1_(9)context_high_density_train_v02.json` |
| v03 | `S1-CTH-0301 ~ S1-CTH-0450` | 교실의 설명·질문·과제·피드백·평가 상황 | `stage1_(9)context_high_density_train_v03.json` |
| v04 | `S1-CTH-0451 ~ S1-CTH-0600` | 진료·예약·검사·결과 안내·추적관리 상황 | `stage1_(9)context_high_density_train_v04.json` |
| v05 | `S1-CTH-0601 ~ S1-CTH-0750` | 작업장의 주문·재료·기계·검사·재작업 상황 | `stage1_(9)context_high_density_train_v05.json` |
| v06 | `S1-CTH-0751 ~ S1-CTH-0900` | 상점의 재고·주문·결제·교환·고객응대 상황 | `stage1_(9)context_high_density_train_v06.json` |
| v07 | `S1-CTH-0901 ~ S1-CTH-1050` | 창고·배송의 입고·분류·상차·이동·인도 상황 | `stage1_(9)context_high_density_train_v07.json` |
| v08 | `S1-CTH-1051 ~ S1-CTH-1200` | 대중교통의 승차·환승·지연·우회·도착 상황 | `stage1_(9)context_high_density_train_v08.json` |
| v09 | `S1-CTH-1201 ~ S1-CTH-1350` | 건물 경보·대피·신고·구조·복구 상황 | `stage1_(9)context_high_density_train_v09.json` |
| v10 | `S1-CTH-1351 ~ S1-CTH-1500` | 환경 현장조사의 지점·센서·시료·기상·기록 상황 | `stage1_(9)context_high_density_train_v10.json` |
| v11 | `S1-CTH-1501 ~ S1-CTH-1650` | 협업 소프트웨어의 이슈·변경·검토·시험·배포 상황 | `stage1_(9)context_high_density_train_v11.json` |
| v12 | `S1-CTH-1651 ~ S1-CTH-1800` | 공공행정의 신청·서류·심사·보완·결정 상황 | `stage1_(9)context_high_density_train_v12.json` |

## 3. validation 신규 concept family 원장

| version | ID 범위 | concept family | 파일 |
|---|---|---|---|
| v01 | `S1-CTV-0001 ~ S1-CTV-0150` | 영화 촬영 현장의 장면·배우·소품·카메라·촬영순서 상황 | `stage1_(9)context_high_density_val_v01.json` |
| v02 | `S1-CTV-0151 ~ S1-CTV-0300` | 선거 투표소의 유권자·명부·투표용지·투표함·참관 상황 | `stage1_(9)context_high_density_val_v02.json` |

각 validation 파일은 150 records이며 `unseen_relation: true` 18개와 false 132개다. 영역 전체 true는 36/300 = 12.00%다. true의 개별 relation label은 train에 모두 존재하고, 정렬 relation-set 조합만 train에 없다.

## 4. relations 통제 어휘 분포

| relation | train | validation |
|---|---:|---:|
| `is_a` | 0 | 0 |
| `subclass_of` | 0 | 0 |
| `part_of` | 145 | 0 |
| `classification` | 334 | 51 |
| `boundary` | 815 | 120 |
| `contrast` | 160 | 0 |
| `comparison` | 93 | 10 |
| `function` | 611 | 90 |
| `role` | 533 | 120 |
| `process` | 954 | 190 |
| `state` | 1,519 | 300 |
| `attribute` | 236 | 55 |
| `other` | 1,800 | 300 |

0회인 relation도 누락하지 않고 표시했다. 각 record는 13개 통제 어휘만 사용하며 2~5개, record 내부 중복 0 조건을 통과했다.

## 5. `other` 편집 유형 상위 5개

### train

| 순위 | 편집 유형 | 횟수 | 예시 primary concept |
|---:|---|---:|---|
| 1 | 인과 맥락 (`causal_context`) | 360 | `가정세탁분류추적상황`, `현관열쇠이동추적상황`, `거실우편물정리추적상황`, `아이방장난감회수상황`, `책상도서반납추적상황` |
| 2 | 역할 조정 (`role_coordination`) | 360 | `거실청소분담조정상황`, `세탁널기역할조정상황`, `침대조립협업상황`, `이사상자표기분담상황`, `욕실누수점검협업상황` |
| 3 | 시간 의존 (`temporal_dependency`) | 360 | `세탁전얼룩처리순서상황`, `빨래건조수납순서상황`, `냉장고성에제거순서상황`, `벽페인트보수순서상황`, `실리콘욕실보수순서상황` |
| 4 | 자원 제약 (`resource_constraint`) | 360 | `청소도구한대공유상황`, `건조대공간부족상황`, `세탁세제잔량제약상황`, `수리나사수량부족상황`, `욕실청소시간제약상황` |
| 5 | 지시 대상 복원 (`reference_resolution`) | 360 | `세탁물지시대상복원상황`, `공구대명사복원상황`, `냉장용기참조복원상황`, `열쇠소유자참조상황`, `수건위치지시복원상황` |

### validation

| 순위 | 편집 유형 | 횟수 | 예시 primary concept |
|---:|---|---:|---|
| 1 | 인과 맥락 (`causal_context`) | 60 | `비내리는장면의우산교체결정`, `배우목소리잡음으로인한재녹음`, `소품잔파손뒤클로즈업취소`, `카메라배터리경고와테이크중단`, `창밖빛변화로인한노출수정` |
| 2 | 역할 조정 (`role_coordination`) | 60 | `콜시트확인과배우호출조율`, `연출자의장면설명과배우질문`, `촬영감독과조명감독노출협의`, `스크립터와의상팀상태인계`, `소품팀과배우소품사용확인` |
| 3 | 시간 의존 (`temporal_dependency`) | 60 | `새벽장면의해뜰전촬영순서`, `분장상처단계와이야기시간순서`, `비연속촬영과의상변화순서`, `점심휴식뒤조명재설정`, `배우도착전대역리허설순서` |
| 4 | 자원 제약 (`resource_constraint`) | 60 | `한대카메라로두각도촬영배치`, `예비렌즈부족과우선장면선택`, `배우가능시간과장면묶음촬영`, `세트공간제약과카메라동선축소`, `조명전력한계와등기구감축` |
| 5 | 지시 대상 복원 (`reference_resolution`) | 60 | `그배우지시와대역구분`, `그잔지시와예비소품구분`, `왼쪽문지시와배우시점해석`, `그다음컷지시와편집순서복원`, `이쪽조명지시와세트방향구분` |

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
| 문자 3~5-gram 내부 최대 cosine | 0.359749 | 0.260654 | 검토 완료 |
| 기존 고밀도/train 교차 최대 cosine | 0.184556 | 0.101915 | 검토 완료 |
| validation 유사도 0.72 이상 후보 | — | 내부 0, train 교차 0 | PASS |

validation 문장 길이는 최소 60자, 중앙값 79.0자, 평균 79.633자, 최대 103자다. 전체 validation과 외부 고밀도 36,250 records 사이의 정확 primary/text/primary–relation-set 겹침 및 공통 5어절도 모두 0건이다.

작업 시작 전에 존재한 train/val JSON 242개는 종료 시점에 242/242 SHA-256이 일치했다. 변경·누락은 0건이고 새 validation JSON 13개만 추가되었으므로 identity 및 기존 train/val 정본은 수정되지 않았다.

광역 조사 탐지 후보는 train 3건, validation 4건이었다. 최종 원문 대조에서 validation 후보는 `맞닿는`, `가까이`, `물려받는` 같은 정상 용언·복합어·외래어에 대한 오탐이며 실제 조사 불량은 0건이다. 반복 5어절 초안 후보는 직접 다시 표현한 뒤 최종 0건을 확인했다.

## 7. 확정 결론

Stage1 (9) 문맥 통합 train과 validation은 파일 수·레코드 수·ID·family 분리·통제 relation·일반화 slice·중복·유사도·조사 점검을 통과했다. 이 보고서는 동일 교육영역의 종전 파편화 보고서를 대체하는 현재 정본이며, machine JSON과 archive는 각각 재현 가능한 세부 근거와 역사 기록으로 보존한다.
