# expanded_train:479560 정제 근거

- 원문: `/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_native_proofs_v1/pages/page_017/inputs/expanded_train_479560_original.txt`
- 원문 SHA-256: `9E5FD1C1CE72B7DFCFA9B6794F891CB45635BC53D4C2515333F2876AE539AA41`
- 후보: `/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/remaining_field_title_native_proofs_v1/pages/page_017/inputs/expanded_train_479560_candidate.txt`
- 후보 SHA-256: `92B9F387926DA18561AF463461F762FCDBB3A4AAEED3B285133BAA6E46BEDC3E`
- 판독: 고정 batch reader pair 1/1, 원문·후보 전문과 diff EOF 확인.
- 정제 및 HOLD 경계: 후보에서 내용 없는 각주 표제가 이미 빠져 있어 정확 candidate를 입력으로 선택했다. 제목의 “UL”은 보존하고 그 뒤의 값 없는 `, ;` 구분자와 괄호만 제거했다. 8개 단과대학, 1911년 설립, 13세기 대학의 역사, 2013년 통합 정보를 유지했다. 추가된 정보나 미상 값은 없다.
- 최종 TXT 준비: 정확 candidate 경로를 입력으로 선택했다. 자기 출력 미존재·비심볼릭 링크 확인, 단일 `cp --`, 수정 전 `cmp --silent` 종료 0.
- 최종 TXT: `/home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/context_hangul/remaining_field_title_page_017_counter_v1/expanded_train_479560_task018_v1.txt`
- 검수: 수정 후 최종 TXT 전문과 candidate 대비 전체 diff 및 EOF를 확인했다.
