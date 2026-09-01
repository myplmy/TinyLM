# Stage1 (5)~(10) 교차영역 통합 감사

최종 판정: **PASS**. 아래 여섯 교육영역 보고서가 현재 사람용 정본이며, 과거 진행 보고서는 `archive/`, 상세 수치는 `machine/`에 보존한다.

| 영역 | train | validation | unseen slice | validation 문자 | 판정 | 통합 보고서 |
|---|---:|---:|---:|---:|---|---|
| (5) 부분–전체 | 23 files / 3,450 | 3 files / 450 | 54 (12.00%) | 36,250 | PASS | [Stage1_(5)_PartWhole_Consolidated_Audit.md](Stage1_(5)_PartWhole_Consolidated_Audit.md) |
| (6) 상태·상태 변화 | 23 files / 3,450 | 3 files / 450 | 54 (12.00%) | 34,439 | PASS | [Stage1_(6)_StateChange_Consolidated_Audit.md](Stage1_(6)_StateChange_Consolidated_Audit.md) |
| (7) 공간 관계 | 16 files / 2,400 | 2 files / 300 | 36 (12.00%) | 22,753 | PASS | [Stage1_(7)_Spatial_Consolidated_Audit.md](Stage1_(7)_Spatial_Consolidated_Audit.md) |
| (8) 비교·대조 | 14 files / 2,100 | 2 files / 300 | 36 (12.00%) | 22,660 | PASS | [Stage1_(8)_Comparison_Consolidated_Audit.md](Stage1_(8)_Comparison_Consolidated_Audit.md) |
| (9) 문맥 통합 | 12 files / 1,800 | 2 files / 300 | 36 (12.00%) | 23,890 | PASS | [Stage1_(9)_Context_Consolidated_Audit.md](Stage1_(9)_Context_Consolidated_Audit.md) |
| (10) 타입·부정·불확실성 | 9 files / 1,350 | 1 files / 150 | 18 (12.00%) | 14,046 | PASS | [Stage1_(10)_TypeUncertainty_Consolidated_Audit.md](Stage1_(10)_TypeUncertainty_Consolidated_Audit.md) |

총 validation은 13 files / 1,950 records이며 unseen relation-set slice는 234/1,950 = 12.00%다. 외부 고밀도 36,250 records와의 정확 primary/text/primary–relation-set 및 공통 5어절은 모두 0건이다. validation 전체 내부 최대 유사도는 0.311151, 0.72 이상 후보는 0건이다.

작업 전 존재한 train/val JSON은 종료 시점 SHA-256 대조에서 242/242 일치했고 변경·누락 0건이다. 새로 추가된 파일은 요청 범위의 validation JSON 13개뿐이다.

## validation relations 전체 분포

| relation | 횟수 |
|---|---:|
| `is_a` | 0 |
| `subclass_of` | 0 |
| `part_of` | 454 |
| `classification` | 470 |
| `boundary` | 698 |
| `contrast` | 153 |
| `comparison` | 304 |
| `function` | 691 |
| `role` | 238 |
| `process` | 888 |
| `state` | 1,094 |
| `attribute` | 357 |
| `other` | 1,155 |

## 보관 구조

- `machine/`: 영역별 train 최종 감사 JSON 6개, validation 통합 최종 감사 JSON 1개, 보호 기준선 해시 비교 JSON 1개
- `archive/<area>/`: 생성 중간 progress 감사와 보고서 74개
- `archive/cross_area/`: 종전 train 교차영역 보고서 1개
- 현재 폴더: 영역별 통합 보고서 6개, 이 교차영역 보고서, `README.md`
