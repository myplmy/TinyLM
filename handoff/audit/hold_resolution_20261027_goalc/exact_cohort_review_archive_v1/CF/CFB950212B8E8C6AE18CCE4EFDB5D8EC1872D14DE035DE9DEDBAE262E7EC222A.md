# TASK_060 독립 판독 — 교정본 v3

기존 `review_060.md`와 `review_060_v2.md`를 보존한다. v3는 지정 입력의 추가 중재를 반영한다.

| ID | 판정 | 실제 판독 범위 | 출력 | 구체 근거 |
|---|---|---|---|---|
| expanded_train:466532 | REVISE_TEXT | 지정 original·candidate 전문, packet 0001의 original/candidate/full diff를 BEGIN/END와 EOF까지 판독; 새 본문 diff와 EOF 확인 | expanded_train_466532_conflicting_birth_year_fields_held_preserving_month_day_20261103_v1.txt | 리드 1959년과 `1969년 출생` 분류가 상충한다. 두 연도만 원형 보류하고 실제 월일 9월 2일, 생존 분류, 사업·공연·포커·우주여행 서술을 보존했다. |
| expanded_train:467794 | REVISE_TEXT | 지정 original·candidate 전문, packet 0001의 original/candidate/full diff를 BEGIN/END와 EOF까지 판독; 새 본문 diff와 EOF 확인 | expanded_train_467794_conflicting_birth_year_fields_held_preserving_month_day_20261103_v1.txt | 리드 1985년과 `1979년 출생` 분류가 상충한다. 두 연도만 원형 보류하고 11월 1일, 피사 및 선수 경력·팀 등급은 유지했다. |
| expanded_train:47363 | ACCEPT_CANDIDATE | 지정 original·candidate 전문, packets 0001→0004의 연속 original/candidate/full diff를 순서대로 논리 END와 각 EOF까지 판독 | expanded_train_47363_candidate.txt | 리드·본문·분류의 출생연도는 모두 1394년이고, 사망연도 1462년 및 리드의 양력/음력 병기와 본문 명시 69세가 유지된다. 명시 14세와 각종 연혁을 재계산하거나 변경하지 않았으며 후보 변경은 빈 각주 표제 제거뿐이다. |
| expanded_train:474114 | REVISE_TEXT | 지정 original·candidate 전문, packet 0001의 original/candidate/full diff를 BEGIN/END와 EOF까지 판독; 새 본문 diff와 EOF 확인 | expanded_train_474114_conflicting_birth_year_fields_held_preserving_month_day_time_20261103_v1.txt | 리드 1868년, 생애 본문 1859년, 분류 1863년이 상충해 세 연도만 원형 보류했다. 두 곳의 2월 8일, 리드 오전 8시 30분, 저지시티, 사망일 대안 11월 10일 또는 12일, 명시 15개월 및 기타 서술은 보존했다. |
| expanded_train:475293 | REVISE_TEXT | 지정 original·candidate 전문, packet 0001의 original/candidate/full diff를 BEGIN/END와 EOF까지 판독; 새 본문 diff와 EOF 확인 | expanded_train_475293_attributed_birth_alternative_preserved_classification_held_bracket_removed_20261103_v1.txt | 리드 `1921년 12월 21일`과 안동권씨 족보에 귀속된 `1922년생` 대안은 역할을 유지해 보존하고, 무귀속 단정 분류 `1918년 출생`만 원형 보류했다. 12월 21일, 이름·생애·정치활동을 보존하고 부친 행의 고립 `]`만 정리했다. 보류 근거: `hold_475293_unqualified_birth_classification_1918_20261103_v1.md`. |
