# expanded_train:96670 TASK018 편집 범위 사고 기록

- 비선택 출력: /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/legacy_review/remaining_field_title_page_007_counter_v1/expanded_train_96670_revised_task018_v1.txt
- 선택 출력: /home/uranus/tinyLM/data_cache/p106b_hold_resolution_v1_20261027_goalc/agents/legacy_review/remaining_field_title_page_007_counter_v1/expanded_train_96670_revised_task018_v2.txt
- 원인: v1의 sed 주소 범위에서 끝 제목을 정확히 고정하지 않았다. 실제 입력의 ‘의사 간호사’ 제목에는 후행 공백이 있어 범위가 끝나지 않았고, 그 뒤부터 문서 끝까지 삭제되었다.
- 대응: v1을 덮거나 삭제하지 않았다. candidate를 새 v2로 무변경 복사한 뒤 실제 후보의 고정 행 범위와 각 정확 문자열만 편집해 한국/미국 사례, 판례, 서지, 말미 분류를 보존했다. 선택 출력 v2와 candidate의 전체 diff/EOF를 확인하고 review_018.md에서 v2만 선택했다.
- 기존 original/candidate 및 다른 확정 출력은 변경하지 않았다.
- 재발 방지: 이후에는 범위 삭제식 sed를 사용하지 않는다. 새 복사본에서 apply_patch로 정확한 문맥을 앵커링해 최소 편집하고, 앵커가 불일치하면 변경하지 않은 채 검토한다.
