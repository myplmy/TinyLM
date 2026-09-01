# Stage1 (7) 공간 관계 통합 감사 보고서

- 최종 판정: **PASS**
- 통합일: 2026-09-01
- 범위: train v01~v16와 validation v01~v02
- 정본: 고밀도 생성 지침서와 설계서. 저밀도 및 held-out/evaluation 자료는 생성·분리·유사도 비교 근거에서 제외했다.
- 기계 판독 근거: [`TinyLM_Stage1_Spatial_Train_v01_v16_Final_Audit_2026-09-01.json`](machine/TinyLM_Stage1_Spatial_Train_v01_v16_Final_Audit_2026-09-01.json), [`TinyLM_Stage1_5_10_Validation_Final_Audit_2026-09-01.json`](machine/TinyLM_Stage1_5_10_Validation_Final_Audit_2026-09-01.json), [`TinyLM_Stage1_5_10_Validation_Protected_Baseline_Comparison_2026-09-01.json`](machine/TinyLM_Stage1_5_10_Validation_Protected_Baseline_Comparison_2026-09-01.json)

## 1. 통합 범위와 최종 산출물

| split | 파일 | records | ID 범위 | 문자 수 | 단어 단위 | 판정 |
|---|---:|---:|---|---:|---:|---|
| train | 16 | 2,400 | `S1-SPH-0001 ~ S1-SPH-2400` | 177,176 | 40,435 | PASS |
| validation | 2 | 300 | `S1-SPV-0001 ~ S1-SPV-0300` | 22,753 | 5,211 | PASS |

과거 진행 중간 감사는 삭제하지 않고 아래 archive로 이관했다. 현재 판단에는 이 통합 보고서와 machine 최종 감사만 사용한다.

- archive: [`archive/spatial/`](archive/spatial/), 9개 역사 자료

## 2. train concept family 원장

| version | ID 범위 | concept family | 파일 |
|---|---|---|---|
| v01 | `S1-SPH-0001 ~ S1-SPH-0150` | 가정 실내 물체·가구·용기의 배치 관계 | `stage1_(7)spatial_high_density_train_v01.json` |
| v02 | `S1-SPH-0151 ~ S1-SPH-0300` | 건물 층·방·복도·계단·출입구의 공간 위상 | `stage1_(7)spatial_high_density_train_v02.json` |
| v03 | `S1-SPH-0301 ~ S1-SPH-0450` | 도시 블록·도로·교차로·공원·시설의 배치 | `stage1_(7)spatial_high_density_train_v03.json` |
| v04 | `S1-SPH-0451 ~ S1-SPH-0600` | 도로 차량·차로·교차로·진출입의 상대 위치 | `stage1_(7)spatial_high_density_train_v04.json` |
| v05 | `S1-SPH-0601 ~ S1-SPH-0750` | 철도역·승강장·선로·분기기·차량의 배치 | `stage1_(7)spatial_high_density_train_v05.json` |
| v06 | `S1-SPH-0751 ~ S1-SPH-0900` | 공항 활주로·유도로·계류장·게이트 공간 관계 | `stage1_(7)spatial_high_density_train_v06.json` |
| v07 | `S1-SPH-0901 ~ S1-SPH-1050` | 항만·선박·선석·항로·정박지 공간 관계 | `stage1_(7)spatial_high_density_train_v07.json` |
| v08 | `S1-SPH-1051 ~ S1-SPH-1200` | 산지·하천·유역·해안·섬의 지리 공간 관계 | `stage1_(7)spatial_high_density_train_v08.json` |
| v09 | `S1-SPH-1201 ~ S1-SPH-1350` | 지도 좌표·축척·방위·투영·기준계 관계 | `stage1_(7)spatial_high_density_train_v09.json` |
| v10 | `S1-SPH-1351 ~ S1-SPH-1500` | 천구·궤도·행성·위성·관측자의 상대 위치 | `stage1_(7)spatial_high_density_train_v10.json` |
| v11 | `S1-SPH-1501 ~ S1-SPH-1650` | 인체 자세·해부 방향·기관의 상대 위치 | `stage1_(7)spatial_high_density_train_v11.json` |
| v12 | `S1-SPH-1651 ~ S1-SPH-1800` | 생물 서식지·둥지·영역·군집의 미소공간 | `stage1_(7)spatial_high_density_train_v12.json` |
| v13 | `S1-SPH-1801 ~ S1-SPH-1950` | 분자·결정·세포·조직의 미시 공간 배열 | `stage1_(7)spatial_high_density_train_v13.json` |
| v14 | `S1-SPH-1951 ~ S1-SPH-2100` | 공장 작업셀·생산선·창고·적치의 공간 배치 | `stage1_(7)spatial_high_density_train_v14.json` |
| v15 | `S1-SPH-2101 ~ S1-SPH-2250` | 메모리 주소·파일 경로·네트워크 위상의 논리 공간 | `stage1_(7)spatial_high_density_train_v15.json` |
| v16 | `S1-SPH-2251 ~ S1-SPH-2400` | 화면·페이지·도표·영상 레이어의 시각 배치 | `stage1_(7)spatial_high_density_train_v16.json` |

## 3. validation 신규 concept family 원장

| version | ID 범위 | concept family | 파일 |
|---|---|---|---|
| v01 | `S1-SPV-0001 ~ S1-SPV-0150` | 스포츠 경기장·코트·선수·공·판정구역 공간 관계 | `stage1_(7)spatial_high_density_val_v01.json` |
| v02 | `S1-SPV-0151 ~ S1-SPV-0300` | 지하광산 갱도·작업면·환기구·운반로 공간 관계 | `stage1_(7)spatial_high_density_val_v02.json` |

각 validation 파일은 150 records이며 `unseen_relation: true` 18개와 false 132개다. 영역 전체 true는 36/300 = 12.00%다. true의 개별 relation label은 train에 모두 존재하고, 정렬 relation-set 조합만 train에 없다.

## 4. relations 통제 어휘 분포

| relation | train | validation |
|---|---:|---:|
| `is_a` | 0 | 0 |
| `subclass_of` | 0 | 0 |
| `part_of` | 169 | 0 |
| `classification` | 532 | 83 |
| `boundary` | 1,183 | 203 |
| `contrast` | 147 | 0 |
| `comparison` | 294 | 17 |
| `function` | 618 | 86 |
| `role` | 234 | 10 |
| `process` | 475 | 87 |
| `state` | 697 | 93 |
| `attribute` | 451 | 57 |
| `other` | 2,400 | 300 |

0회인 relation도 누락하지 않고 표시했다. 각 record는 13개 통제 어휘만 사용하며 2~5개, record 내부 중복 0 조건을 통과했다.

## 5. `other` 편집 유형 상위 5개

### train

| 순위 | 편집 유형 | 횟수 | 예시 primary concept |
|---:|---|---:|---|
| 1 | 포함·위치 (`containment_location`) | 480 | `서랍안쪽의수저통`, `찬장내부의찻잔묶음`, `냉장고문칸의소스병`, `상자바깥의포장끈`, `바구니속의빨랫감` |
| 2 | 방향·순서 (`directional_order`) | 480 | `식탁아래의발받침`, `책장위의보관상자`, `소파앞의낮은탁자`, `침대뒤벽의협탁조명`, `냉장고왼쪽의틈새장` |
| 3 | 인접·연결 (`adjacency_connectivity`) | 480 | `상판에닿은컵받침`, `벽에붙은케이블클립`, `소파와탁자사이통로`, `나란히놓인두식탁의접경면`, `겹쳐놓은쟁반의접촉층` |
| 4 | 거리·근접 (`distance_proximity`) | 480 | `소파와텔레비전의시청거리`, `식탁의자사이의착석간격`, `침대와벽의청소틈`, `냉장고후면의방열간격`, `책장선반의칸높이여유` |
| 5 | 기준계·투영 (`reference_frame_projection`) | 480 | `거울속화분의좌우반전위치`, `소파에앉은사람기준의오른팔탁자`, `문을향한로봇기준의왼쪽벽`, `천장도면에투영된식탁중심`, `방문안쪽에서본경첩방향` |

### validation

| 순위 | 편집 유형 | 횟수 | 예시 primary concept |
|---:|---|---:|---|
| 1 | 포함·위치 (`containment_location`) | 60 | `축구공과터치라인안쪽위치`, `축구공과골라인바깥위치`, `축구선수와페널티구역내위치`, `축구반칙과페널티구역경계위치`, `골키퍼손과페널티구역밖위치` |
| 2 | 방향·순서 (`directional_order`) | 60 | `축구공격방향과상대골대쪽`, `축구수비선과최후방수비수순서`, `축구공과공격수앞뒤관계`, `축구윙어와터치라인쪽방향`, `축구수비수와골대사이방향` |
| 3 | 인접·연결 (`adjacency_connectivity`) | 60 | `축구공과선수발접촉관계`, `축구선수와어깨접촉관계`, `축구공과골포스트접촉관계`, `축구화스터드와잔디접촉관계`, `축구수비벽과선수간인접배치` |
| 4 | 거리·근접 (`distance_proximity`) | 60 | `축구프리킥공과수비벽거리`, `축구페널티킥공과골키퍼거리`, `축구선수간마킹거리`, `축구공과터치라인최단거리`, `축구골키퍼와수비선간격` |
| 5 | 기준계·투영 (`reference_frame_projection`) | 60 | `축구중계화면좌측과팀공격좌측`, `축구선수시점앞쪽과경기장북쪽`, `축구오프사이드선과화면세로선`, `축구공위치와잔디투영점`, `축구골라인과가상수직판정면` |

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
| 문자 3~5-gram 내부 최대 cosine | 0.348472 | 0.314553 | 검토 완료 |
| 기존 고밀도/train 교차 최대 cosine | 0.220711 | 0.184022 | 검토 완료 |
| validation 유사도 0.72 이상 후보 | — | 내부 0, train 교차 0 | PASS |

validation 문장 길이는 최소 60자, 중앙값 75.0자, 평균 75.843자, 최대 98자다. 전체 validation과 외부 고밀도 36,250 records 사이의 정확 primary/text/primary–relation-set 겹침 및 공통 5어절도 모두 0건이다.

작업 시작 전에 존재한 train/val JSON 242개는 종료 시점에 242/242 SHA-256이 일치했다. 변경·누락은 0건이고 새 validation JSON 13개만 추가되었으므로 identity 및 기존 train/val 정본은 수정되지 않았다.

광역 조사 탐지 후보는 train 47건, validation 13건이었다. 최종 원문 대조에서 validation 후보는 `맞닿는`, `가까이`, `물려받는` 같은 정상 용언·복합어·외래어에 대한 오탐이며 실제 조사 불량은 0건이다. 반복 5어절 초안 후보는 직접 다시 표현한 뒤 최종 0건을 확인했다.

## 7. 확정 결론

Stage1 (7) 공간 관계 train과 validation은 파일 수·레코드 수·ID·family 분리·통제 relation·일반화 slice·중복·유사도·조사 점검을 통과했다. 이 보고서는 동일 교육영역의 종전 파편화 보고서를 대체하는 현재 정본이며, machine JSON과 archive는 각각 재현 가능한 세부 근거와 역사 기록으로 보존한다.
