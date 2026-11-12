# expanded_train:458994 정제 판정

- 원문: `/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_native_proofs_v1/pages/page_017/inputs/expanded_train_458994_original.txt` — SHA-256 `0604D0E7D4FFD6DCD28FFC443AEA18C0A54F5AF76F977C603178D2191C5F481F`
- 후보/준비 입력: `/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_native_proofs_v1/pages/page_017/inputs/expanded_train_458994_candidate.txt` — SHA-256 `D8349CB9DA1C740D454192E72123247765266B06A1C2737C87608F919CC48754`
- 자기 초기 후보 사본: `/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_hangul/remaining_field_title_page_017_counter_v1/expanded_train_458994_initial_candidate_v1.txt` — 후보와 수정 전 `cmp --silent` 일치 확인.
- 최종 출력: `/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_hangul/remaining_field_title_page_017_counter_v1/expanded_train_458994_task004_v1.txt`
- 판정: 한자 기관명은 보존하고 제목의 빈 쉼표 구분자를 정리했다. 원문에서 `구조대의 명칭·위치 및 관할구역` 아래에 표나 항목이 없어 해당 빈 표제를 본문에서 분리했다. 후보가 제거한 빈 `각주`와 `외부 링크` 표제도 반영했다. 설치 근거·소관 사무·연혁·조직·항공기 기종과 식별번호·배치/폐기 연도·사건사고 및 같이 보기 항목은 보존했다. 표의 값을 추정하거나 외부 사실 검증은 하지 않았다.
- 검토: batch-v1 원문 1/1 part에서 EOF를 확인하고 후보 diff를 대조했다. 최종 본문 전문·후보 대비 전체 diff를 확인했으며 최종 EOF는 LF(`0a`)다.
