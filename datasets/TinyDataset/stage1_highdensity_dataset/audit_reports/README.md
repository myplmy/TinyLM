# Stage1 고밀도 데이터셋 감사보고서 인덱스

동일 교육영역의 train·validation 감사 결과를 한 파일로 합친 현재 정본이다. 진행 중간 산출물은 삭제하지 않고 `archive/`로 옮겼으며, 대용량 JSON 근거는 `machine/`에 분리했다. Identity는 2026-09-01 사용자 승인에 따라 원본 `relations`를 보존한 채 `relations_controlled`를 추가한 별도 감사가 정본이다.

- [Stage1 (1) Identity 관계 통제 감사](Stage1_(1)_Identity_Relation_Control_Audit.md)
- [Stage1 (2) 속성·정도·변이](Stage1_(2)_Attribute_Consolidated_Audit.md)
- [Stage1 (3) 기능·용도·목적](Stage1_(3)_Function_Consolidated_Audit.md)
- [Stage1 (4) 개념 경계·반례](Stage1_(4)_Boundary_Consolidated_Audit.md)
- [Stage1 전체 retrospective naturalness 추가 감사 (2026-09-11)](Stage1_HighDensity_Retrospective_Naturalness_Audit_2026-09-11.md)
- [교차영역 통합 감사](Stage1_(5-10)_CrossArea_Consolidated_Audit.md)
- [Stage1 (5) 부분–전체](Stage1_(5)_PartWhole_Consolidated_Audit.md)
- [Stage1 (6) 상태·상태 변화](Stage1_(6)_StateChange_Consolidated_Audit.md)
- [Stage1 (7) 공간 관계](Stage1_(7)_Spatial_Consolidated_Audit.md)
- [Stage1 (8) 비교·대조](Stage1_(8)_Comparison_Consolidated_Audit.md)
- [Stage1 (9) 문맥 통합](Stage1_(9)_Context_Consolidated_Audit.md)
- [Stage1 (10) 타입·부정·불확실성](Stage1_(10)_TypeUncertainty_Consolidated_Audit.md)
- [Stage2~10 생성 준비 기계 감사](machine/TinyLM_Stage2_10_Preparation_Audit_2026-09-01.json)
- [Stage2~10·Identity 최종 보호 비교](machine/TinyLM_Stage2_10_Identity_Final_Protection_Comparison_2026-09-01.json)
- [machine 최종 감사](machine/)
- [과거 progress archive](archive/)

`machine/attribute/`, `machine/function/`, `machine/boundary/`에는 각 교육영역의 최신 train·validation JSON 감사가 있다. `archive/attribute/`, `archive/function/`, `archive/boundary/`에는 교정 전·진행 중·과거 사람용 보고서와 handoff 이관 판정을 보존한다.

사람이 확인할 때는 이 폴더의 통합 Markdown만 보면 되며, 수치 재검증이나 과거 경과 추적이 필요할 때에만 하위 폴더를 사용한다.
